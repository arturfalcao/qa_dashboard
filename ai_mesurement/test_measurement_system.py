#!/usr/bin/env python3
"""
Test script for the Garment Measurement System
Includes validation framework and accuracy testing
"""

import cv2
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from garment_measurement_system import (
    GarmentMeasurementSystem, GarmentType,
    CameraCalibration, ImagePreprocessor,
    GarmentSegmentation, LandmarkDetector,
    MeasurementCalculator
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeasurementValidator:
    """Validation framework for measurement accuracy"""

    def __init__(self):
        self.golden_samples = {}
        self.tolerance = 2.0  # ±2mm tolerance
        self.results = []

    def add_golden_sample(self, name: str, measurements: Dict[str, float]):
        """Add a golden sample with known measurements"""
        self.golden_samples[name] = measurements
        logger.info(f"Added golden sample: {name}")

    def validate_measurement(self, measured: float, expected: float,
                           tolerance: float = None) -> Tuple[bool, float]:
        """Validate a single measurement against expected value"""
        if tolerance is None:
            tolerance = self.tolerance

        error = abs(measured - expected)
        passed = error <= tolerance

        return passed, error

    def run_validation(self, system: GarmentMeasurementSystem,
                      image_path: str, sample_name: str) -> Dict:
        """Run validation on a single image"""

        if sample_name not in self.golden_samples:
            logger.error(f"Unknown golden sample: {sample_name}")
            return {}

        expected = self.golden_samples[sample_name]

        # Process image
        results = system.process_image(image_path)
        measured = results["measurements"]

        # Compare measurements
        validation_results = {
            "sample": sample_name,
            "image": image_path,
            "measurements": {}
        }

        for key, expected_value in expected.items():
            if key in measured:
                measured_value = measured[key]["value"]
                passed, error = self.validate_measurement(measured_value, expected_value)

                validation_results["measurements"][key] = {
                    "measured": measured_value,
                    "expected": expected_value,
                    "error": error,
                    "passed": passed
                }

                status = "PASS" if passed else "FAIL"
                logger.info(f"  {key}: {measured_value:.1f}mm (expected: {expected_value:.1f}mm) "
                          f"Error: {error:.1f}mm [{status}]")
            else:
                logger.warning(f"  {key}: Not measured")

        self.results.append(validation_results)
        return validation_results

    def calculate_gage_rr(self, measurements: List[Dict]) -> Dict:
        """Calculate Gage R&R statistics"""

        # Group measurements by sample and operator
        grouped = {}
        for m in measurements:
            key = (m["sample"], m.get("operator", "default"))
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(m["measurements"])

        # Calculate repeatability (within operator variation)
        repeatability_var = 0
        count = 0

        for key, trials in grouped.items():
            if len(trials) > 1:
                # Calculate variance within trials
                for measurement_name in trials[0].keys():
                    values = [t[measurement_name]["measured"] for t in trials
                             if measurement_name in t]
                    if len(values) > 1:
                        var = np.var(values)
                        repeatability_var += var
                        count += 1

        if count > 0:
            repeatability_var /= count

        # Calculate reproducibility (between operator variation)
        # This would require multiple operators - simplified for now

        # Calculate %GRR
        tolerance_range = self.tolerance * 2  # ±2mm = 4mm range
        gage_var = repeatability_var
        gage_6sigma = 6 * np.sqrt(gage_var) if gage_var > 0 else 0
        percent_grr = (gage_6sigma / tolerance_range) * 100 if tolerance_range > 0 else 0

        return {
            "repeatability_variance": repeatability_var,
            "gage_6sigma": gage_6sigma,
            "percent_grr": percent_grr,
            "acceptable": percent_grr < 20  # Industry standard threshold
        }

    def generate_report(self, output_file: str):
        """Generate validation report"""

        report = {
            "summary": {
                "total_samples": len(self.results),
                "passed_samples": 0,
                "failed_samples": 0,
                "average_error": {}
            },
            "details": self.results,
            "gage_rr": self.calculate_gage_rr(self.results) if len(self.results) > 1 else None
        }

        # Calculate summary statistics
        all_errors = {}
        for result in self.results:
            sample_passed = True
            for meas_name, meas_data in result["measurements"].items():
                if meas_name not in all_errors:
                    all_errors[meas_name] = []
                all_errors[meas_name].append(meas_data["error"])
                if not meas_data["passed"]:
                    sample_passed = False

            if sample_passed:
                report["summary"]["passed_samples"] += 1
            else:
                report["summary"]["failed_samples"] += 1

        # Calculate average errors
        for meas_name, errors in all_errors.items():
            report["summary"]["average_error"][meas_name] = {
                "mean": np.mean(errors),
                "std": np.std(errors),
                "max": np.max(errors),
                "min": np.min(errors)
            }

        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Validation report saved to {output_file}")
        return report

class ErrorBudgetAnalyzer:
    """Analyze and track error sources in the measurement system"""

    def __init__(self):
        self.error_sources = {
            "camera_distortion": {"type": "systematic", "estimate_mm": 0.2},
            "homography": {"type": "systematic", "estimate_mm": 0.5},
            "pixel_quantization": {"type": "random", "estimate_mm": 0.3},
            "segmentation": {"type": "random", "estimate_mm": 0.5},
            "contour_smoothing": {"type": "systematic", "estimate_mm": 0.2},
            "landmark_detection": {"type": "random", "estimate_mm": 0.5},
            "garment_placement": {"type": "random", "estimate_mm": 1.0},
            "environmental": {"type": "systematic", "estimate_mm": 0.2}
        }

    def calculate_combined_uncertainty(self) -> float:
        """Calculate combined measurement uncertainty using RSS"""

        total_variance = 0
        for source, data in self.error_sources.items():
            variance = data["estimate_mm"] ** 2
            total_variance += variance

        combined_uncertainty = np.sqrt(total_variance)
        confidence_95 = combined_uncertainty * 2  # Approximate 95% CI

        return confidence_95

    def generate_error_budget_table(self) -> str:
        """Generate error budget table"""

        table = "Error Budget Analysis\n"
        table += "=" * 60 + "\n"
        table += f"{'Source':<25} {'Type':<12} {'Est. ±(mm)':<12} {'Notes'}\n"
        table += "-" * 60 + "\n"

        for source, data in self.error_sources.items():
            table += f"{source:<25} {data['type']:<12} {data['estimate_mm']:<12.1f}\n"

        table += "-" * 60 + "\n"
        combined = self.calculate_combined_uncertainty()
        table += f"Combined (95% CI): ±{combined:.1f} mm\n"
        table += f"Target: ±{2.0:.1f} mm\n"
        table += f"Status: {'PASS' if combined <= 2.0 else 'FAIL'}\n"

        return table

def create_synthetic_test_image(garment_type: str = "shirt",
                               output_file: str = "synthetic_test.png"):
    """Create a synthetic garment image for testing"""

    # Create blank image (1200x800 as per spec)
    img = np.ones((800, 1200, 3), dtype=np.uint8) * 50  # Dark background

    if garment_type == "shirt":
        # Draw a simple shirt shape
        shirt_pts = np.array([
            [400, 150],   # Left shoulder
            [450, 100],   # Left neck
            [550, 100],   # Center neck
            [650, 100],   # Right neck
            [700, 150],   # Right shoulder
            [850, 200],   # Right shoulder tip
            [900, 400],   # Right cuff
            [850, 420],   # Right cuff bottom
            [750, 250],   # Right underarm
            [750, 600],   # Right hem
            [450, 600],   # Left hem
            [450, 250],   # Left underarm
            [350, 420],   # Left cuff bottom
            [300, 400],   # Left cuff
            [350, 200],   # Left shoulder tip
        ], np.int32)

        # Fill shirt with light color
        cv2.fillPoly(img, [shirt_pts], (200, 200, 200))

    elif garment_type == "pants":
        # Draw simple pants shape
        pants_pts = np.array([
            [400, 100],   # Left waist
            [800, 100],   # Right waist
            [800, 350],   # Right hip
            [750, 400],   # Right crotch
            [800, 700],   # Right ankle outer
            [700, 700],   # Right ankle inner
            [650, 400],   # Center crotch
            [600, 700],   # Left ankle inner
            [500, 700],   # Left ankle outer
            [450, 400],   # Left crotch
            [400, 350],   # Left hip
        ], np.int32)

        cv2.fillPoly(img, [pants_pts], (150, 150, 200))

    # Add ArUco markers in corners for calibration
    try:
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    except AttributeError:
        aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
    marker_size = 50

    for i, pos in enumerate([(50, 50), (1100, 50), (1100, 700), (50, 700)]):
        try:
            # Try newer API
            marker = cv2.aruco.generateImageMarker(aruco_dict, i, marker_size)
        except AttributeError:
            # Fall back to older API
            marker = cv2.aruco.drawMarker(aruco_dict, i, marker_size)
        marker_color = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
        x, y = pos
        img[y:y+marker_size, x:x+marker_size] = marker_color

    cv2.imwrite(output_file, img)
    logger.info(f"Created synthetic test image: {output_file}")
    return img

def run_comprehensive_test():
    """Run comprehensive system testing"""

    logger.info("Starting comprehensive measurement system test")

    # Create test directory
    test_dir = Path("test_results")
    test_dir.mkdir(exist_ok=True)

    # Generate default calibration
    from calibration_tool import CalibrationTool
    calib_tool = CalibrationTool()
    calib_file = str(test_dir / "test_calibration.json")
    calib_tool.create_default_calibration(calib_file)

    # Initialize measurement system
    system = GarmentMeasurementSystem(calib_file)

    # Create synthetic test images
    shirt_img = create_synthetic_test_image("shirt", str(test_dir / "test_shirt.png"))
    pants_img = create_synthetic_test_image("pants", str(test_dir / "test_pants.png"))

    # Initialize validator
    validator = MeasurementValidator()

    # Add golden samples (expected measurements in mm)
    validator.add_golden_sample("test_shirt", {
        "chest_width": 350,
        "shoulder_width": 450,
        "hps_length": 500
    })

    validator.add_golden_sample("test_pants", {
        "waist_width": 400,
        "hip_width": 350,
        "outseam": 600
    })

    # Test with existing test image if available
    existing_test = Path("test.jpg")
    if existing_test.exists():
        logger.info("\nTesting with existing image...")
        try:
            results = system.process_image(str(existing_test), str(test_dir))
            logger.info("Successfully processed existing test image")

            # Display results
            print("\n=== Measurements from test.jpg ===")
            for name, data in results["measurements"].items():
                print(f"  {name}: {data['value']:.1f} ± {data['uncertainty']:.1f} mm")

        except Exception as e:
            logger.error(f"Error processing existing image: {e}")

    # Test with synthetic images
    logger.info("\nTesting with synthetic images...")

    try:
        # Process synthetic shirt
        shirt_results = system.process_image(str(test_dir / "test_shirt.png"), str(test_dir))
        logger.info("Synthetic shirt processed successfully")

        # Process synthetic pants
        pants_results = system.process_image(str(test_dir / "test_pants.png"), str(test_dir))
        logger.info("Synthetic pants processed successfully")

    except Exception as e:
        logger.error(f"Error processing synthetic images: {e}")

    # Error budget analysis
    logger.info("\n" + "=" * 60)
    analyzer = ErrorBudgetAnalyzer()
    print(analyzer.generate_error_budget_table())

    # Generate final report
    report_file = str(test_dir / "validation_report.json")
    if len(validator.results) > 0:
        report = validator.generate_report(report_file)
        logger.info(f"\nValidation complete. Report saved to {report_file}")

        # Print summary
        print("\n=== Validation Summary ===")
        print(f"Total samples tested: {report['summary']['total_samples']}")
        print(f"Passed: {report['summary']['passed_samples']}")
        print(f"Failed: {report['summary']['failed_samples']}")

        if report['gage_rr']:
            print(f"\nGage R&R: {report['gage_rr']['percent_grr']:.1f}%")
            print(f"Status: {'Acceptable' if report['gage_rr']['acceptable'] else 'Needs Improvement'}")

    logger.info("\nComprehensive test complete!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Garment Measurement System")
    parser.add_argument("--mode", choices=["quick", "comprehensive", "validate"],
                       default="comprehensive", help="Test mode")
    parser.add_argument("--image", help="Image to test")
    parser.add_argument("--calibration", help="Calibration file to use")
    parser.add_argument("--output", default="test_results", help="Output directory")

    args = parser.parse_args()

    if args.mode == "quick" and args.image:
        # Quick test with single image
        calib_file = args.calibration or "calibration.json"

        # Create default calibration if needed
        if not Path(calib_file).exists():
            from calibration_tool import CalibrationTool
            tool = CalibrationTool()
            tool.create_default_calibration(calib_file)

        system = GarmentMeasurementSystem(calib_file)
        results = system.process_image(args.image, args.output)

        print("\n=== Quick Test Results ===")
        print(f"Garment Type: {results['garment_type']}")
        print("\nMeasurements:")
        for name, data in results['measurements'].items():
            print(f"  {name}: {data['value']:.1f} ± {data['uncertainty']:.1f} mm")

    elif args.mode == "comprehensive":
        run_comprehensive_test()

    elif args.mode == "validate":
        # Validation mode for golden samples
        logger.info("Running validation mode...")
        # This would be expanded with actual golden sample data
        pass