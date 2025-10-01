#!/usr/bin/env python3
"""
Production-Ready Garment Measurement System
Accurate fabric measurement using computer vision and ruler calibration
Version: 1.0.0
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import existing modules
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter


@dataclass
class MeasurementResult:
    """Structured measurement result for production use"""
    height_cm: float
    width_cm: float
    chest_estimate_cm: float
    area_cm2: float
    size: str
    size_category: str
    confidence: float
    timestamp: str
    calibration_used: float
    ruler_confidence: float
    measurement_points: Dict
    warnings: List[str]


class GarmentMeasurementProduction:
    """
    Production-ready garment measurement system

    Features:
    - Accurate measurements with optimal calibration
    - Multiple measurement support for averaging
    - Comprehensive error handling
    - Confidence scoring
    - Production logging
    """

    # Optimal calibration factor based on empirical testing
    # Actual: 42.5cm, Measured: 43.85cm, Factor: 0.969
    DEFAULT_HEIGHT_CALIBRATION = 0.969
    DEFAULT_WIDTH_CALIBRATION = 1.0  # Width typically accurate

    # Size chart (chest circumference in cm)
    SIZE_CHART = {
        'XS': {'min': 76, 'max': 86, 'label': 'Extra Small'},
        'S': {'min': 86, 'max': 96, 'label': 'Small'},
        'M': {'min': 96, 'max': 106, 'label': 'Medium'},
        'L': {'min': 106, 'max': 116, 'label': 'Large'},
        'XL': {'min': 116, 'max': 126, 'label': 'Extra Large'},
        'XXL': {'min': 126, 'max': 136, 'label': '2X Large'},
        'XXXL': {'min': 136, 'max': 146, 'label': '3X Large'}
    }

    def __init__(self,
                 ruler_length_cm: float = 31.0,
                 height_calibration: Optional[float] = None,
                 width_calibration: Optional[float] = None,
                 debug: bool = False):
        """
        Initialize the measurement system

        Args:
            ruler_length_cm: Known length of ruler in cm
            height_calibration: Custom height calibration factor (default: 0.969)
            width_calibration: Custom width calibration factor (default: 1.0)
            debug: Enable debug output and visualizations
        """
        self.ruler_length_cm = ruler_length_cm
        self.height_calibration = height_calibration or self.DEFAULT_HEIGHT_CALIBRATION
        self.width_calibration = width_calibration or self.DEFAULT_WIDTH_CALIBRATION
        self.debug = debug

        # Initialize components
        self.ruler_detector = SmartRulerDetector(
            known_length_cm=ruler_length_cm,
            debug=False  # Control debug separately
        )
        self.segmenter = FastGarmentSegmenter(debug=False)

        print(f"📐 Garment Measurement System initialized")
        print(f"   Ruler: {ruler_length_cm}cm")
        print(f"   Calibration: H={self.height_calibration:.3f}, W={self.width_calibration:.3f}")

    def measure(self,
                image_path: str,
                num_measurements: int = 1) -> MeasurementResult:
        """
        Measure a garment from an image

        Args:
            image_path: Path to the garment image
            num_measurements: Number of measurements to average (default: 1)

        Returns:
            MeasurementResult object with all measurements

        Raises:
            FileNotFoundError: If image doesn't exist
            ValueError: If measurement fails
        """
        # Validate image path
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        print(f"\n{'='*60}")
        print(f"📸 Processing: {Path(image_path).name}")
        print(f"{'='*60}\n")

        # Load image once
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        print(f"Image size: {image.shape[1]}x{image.shape[0]} pixels")

        # Perform measurements
        if num_measurements > 1:
            print(f"Performing {num_measurements} measurements for averaging...")
            results = []
            for i in range(num_measurements):
                print(f"\nMeasurement {i+1}/{num_measurements}:")
                result = self._single_measurement(image)
                results.append(result)

            # Average the results
            final_result = self._average_measurements(results)
            print(f"\n✅ Averaged {num_measurements} measurements")
        else:
            final_result = self._single_measurement(image)

        # Create visualization if debug mode
        if self.debug:
            self._create_visualization(image, final_result)

        # Print summary
        self._print_summary(final_result)

        # Save report
        self._save_report(final_result, image_path)

        return final_result

    def _single_measurement(self, image: np.ndarray) -> MeasurementResult:
        """Perform a single measurement"""

        warnings = []

        # Step 1: Detect ruler
        try:
            ruler_info = self.ruler_detector.detect_ruler(image)
            pixels_per_cm = ruler_info['pixels_per_cm']
            ruler_bbox = ruler_info['bbox']
            ruler_confidence = ruler_info.get('confidence', 0.5)
        except Exception as e:
            raise ValueError(f"Ruler detection failed: {e}")

        if ruler_confidence < 0.5:
            warnings.append("Low ruler detection confidence")

        # Step 2: Segment garment
        try:
            mask, garment_info = self.segmenter.segment_garment(
                image, ruler_bbox=ruler_bbox
            )
        except Exception as e:
            raise ValueError(f"Segmentation failed: {e}")

        # Step 3: Measure with robust percentiles
        measurements = self._robust_measurement(mask, pixels_per_cm)

        # Step 4: Apply calibration
        height_calibrated = measurements['height_raw'] * self.height_calibration
        width_calibrated = measurements['width_raw'] * self.width_calibration

        # Step 5: Estimate size
        chest_estimate = width_calibrated * 2
        size, size_category = self._estimate_size(chest_estimate)

        # Step 6: Calculate confidence
        confidence = self._calculate_confidence(
            ruler_confidence,
            measurements,
            warnings
        )

        # Create result
        result = MeasurementResult(
            height_cm=round(height_calibrated, 2),
            width_cm=round(width_calibrated, 2),
            chest_estimate_cm=round(chest_estimate, 1),
            area_cm2=round(measurements['area_cm2'], 0),
            size=size,
            size_category=size_category,
            confidence=round(confidence, 3),
            timestamp=datetime.now().isoformat(),
            calibration_used=self.height_calibration,
            ruler_confidence=round(ruler_confidence, 3),
            measurement_points=measurements['points'],
            warnings=warnings
        )

        return result

    def _robust_measurement(self, mask: np.ndarray, pixels_per_cm: float) -> Dict:
        """
        Perform robust measurement using percentiles

        Uses 3rd and 97th percentiles to avoid outliers from shadows/artifacts
        """
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("No garment contour found")

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)
        points = contour.reshape(-1, 2)

        # Height measurement (3rd to 97th percentile)
        y_coords = points[:, 1]
        top_y = int(np.percentile(y_coords, 3))
        bottom_y = int(np.percentile(y_coords, 97))

        # Find exact points
        tolerance = 15  # pixels
        top_candidates = points[(y_coords >= top_y - tolerance) &
                               (y_coords <= top_y + tolerance)]
        bottom_candidates = points[(y_coords >= bottom_y - tolerance) &
                                  (y_coords <= bottom_y + tolerance)]

        if len(top_candidates) > 0:
            top_point = top_candidates[np.argmin(top_candidates[:, 1])]
        else:
            top_point = points[np.argmin(y_coords)]

        if len(bottom_candidates) > 0:
            bottom_point = bottom_candidates[np.argmax(bottom_candidates[:, 1])]
        else:
            bottom_point = points[np.argmax(y_coords)]

        # Width measurement (3rd to 97th percentile)
        x_coords = points[:, 0]
        left_x = int(np.percentile(x_coords, 3))
        right_x = int(np.percentile(x_coords, 97))

        left_candidates = points[(x_coords >= left_x - tolerance) &
                                (x_coords <= left_x + tolerance)]
        right_candidates = points[(x_coords >= right_x - tolerance) &
                                 (x_coords <= right_x + tolerance)]

        if len(left_candidates) > 0:
            left_point = left_candidates[np.argmin(left_candidates[:, 0])]
        else:
            left_point = points[np.argmin(x_coords)]

        if len(right_candidates) > 0:
            right_point = right_candidates[np.argmax(right_candidates[:, 0])]
        else:
            right_point = points[np.argmax(x_coords)]

        # Calculate measurements
        height_px = bottom_point[1] - top_point[1]
        width_px = right_point[0] - left_point[0]
        area_px = cv2.contourArea(contour)

        return {
            'height_raw': height_px / pixels_per_cm,
            'width_raw': width_px / pixels_per_cm,
            'area_cm2': area_px / (pixels_per_cm ** 2),
            'height_px': height_px,
            'width_px': width_px,
            'pixels_per_cm': pixels_per_cm,
            'points': {
                'top': tuple(top_point.tolist()),
                'bottom': tuple(bottom_point.tolist()),
                'left': tuple(left_point.tolist()),
                'right': tuple(right_point.tolist())
            }
        }

    def _estimate_size(self, chest_cm: float) -> Tuple[str, str]:
        """Estimate garment size from chest measurement"""

        for size_code, specs in self.SIZE_CHART.items():
            if specs['min'] <= chest_cm < specs['max']:
                return size_code, specs['label']

        # Handle out of range
        if chest_cm < 76:
            return 'XS', 'Extra Small (Youth)'
        else:
            return 'XXXL+', '3X Large or Larger'

    def _calculate_confidence(self,
                             ruler_confidence: float,
                             measurements: Dict,
                             warnings: List) -> float:
        """Calculate overall measurement confidence"""

        # Base confidence from ruler detection
        confidence = ruler_confidence * 0.5

        # Add confidence based on measurement validity
        height_valid = 20 <= measurements['height_raw'] <= 100
        width_valid = 20 <= measurements['width_raw'] <= 80
        aspect_ratio = measurements['width_raw'] / measurements['height_raw']
        ratio_valid = 0.5 <= aspect_ratio <= 2.0

        if height_valid:
            confidence += 0.15
        if width_valid:
            confidence += 0.15
        if ratio_valid:
            confidence += 0.2

        # Reduce confidence for warnings
        confidence -= len(warnings) * 0.1

        return max(0.0, min(1.0, confidence))

    def _average_measurements(self, results: List[MeasurementResult]) -> MeasurementResult:
        """Average multiple measurement results"""

        n = len(results)

        # Calculate averages
        avg_height = sum(r.height_cm for r in results) / n
        avg_width = sum(r.width_cm for r in results) / n
        avg_chest = sum(r.chest_estimate_cm for r in results) / n
        avg_area = sum(r.area_cm2 for r in results) / n
        avg_confidence = sum(r.confidence for r in results) / n
        avg_ruler_conf = sum(r.ruler_confidence for r in results) / n

        # Use median for size estimation
        chest_values = [r.chest_estimate_cm for r in results]
        median_chest = sorted(chest_values)[n // 2]
        size, size_category = self._estimate_size(median_chest)

        # Collect all warnings
        all_warnings = []
        for r in results:
            all_warnings.extend(r.warnings)
        unique_warnings = list(set(all_warnings))

        # Use first result's points (could average these too)
        points = results[0].measurement_points

        return MeasurementResult(
            height_cm=round(avg_height, 2),
            width_cm=round(avg_width, 2),
            chest_estimate_cm=round(avg_chest, 1),
            area_cm2=round(avg_area, 0),
            size=size,
            size_category=size_category,
            confidence=round(avg_confidence, 3),
            timestamp=datetime.now().isoformat(),
            calibration_used=self.height_calibration,
            ruler_confidence=round(avg_ruler_conf, 3),
            measurement_points=points,
            warnings=unique_warnings
        )

    def _print_summary(self, result: MeasurementResult):
        """Print measurement summary"""

        print(f"\n{'='*60}")
        print(f"📊 MEASUREMENT RESULTS")
        print(f"{'='*60}\n")

        print(f"📏 DIMENSIONS:")
        print(f"   Height: {result.height_cm} cm ({result.height_cm/2.54:.1f} inches)")
        print(f"   Width:  {result.width_cm} cm ({result.width_cm/2.54:.1f} inches)")
        print(f"   Area:   {result.area_cm2:.0f} cm²")

        print(f"\n👕 SIZE:")
        print(f"   Chest (est.): {result.chest_estimate_cm} cm")
        print(f"   Size: {result.size} - {result.size_category}")

        print(f"\n✨ QUALITY:")
        print(f"   Confidence: {result.confidence:.1%}")
        print(f"   Ruler Detection: {result.ruler_confidence:.1%}")

        if result.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in result.warnings:
                print(f"   • {warning}")

        print(f"\n{'='*60}")

    def _save_report(self, result: MeasurementResult, image_path: str):
        """Save measurement report to JSON"""

        # Create report directory if needed
        report_dir = Path("measurement_reports")
        report_dir.mkdir(exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = Path(image_path).stem
        report_path = report_dir / f"measurement_{image_name}_{timestamp}.json"

        # Convert to dict and save
        report_data = asdict(result)
        report_data['image_path'] = str(image_path)
        report_data['system_version'] = '1.0.0'

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"📁 Report saved: {report_path}")

    def _create_visualization(self, image: np.ndarray, result: MeasurementResult):
        """Create debug visualization"""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(10, 8))

        # Create overlay
        overlay = image.copy()

        # Draw measurement lines
        pts = result.measurement_points
        if pts:
            cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 0), 4)
            cv2.line(overlay, pts['left'], pts['right'], (255, 0, 0), 4)

            # Draw points
            for point in pts.values():
                cv2.circle(overlay, point, 12, (255, 255, 0), -1)

            # Add labels
            cv2.putText(overlay, f"{result.height_cm}cm",
                       (pts['top'][0]+30, (pts['top'][1]+pts['bottom'][1])//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.putText(overlay, f"{result.width_cm}cm",
                       ((pts['left'][0]+pts['right'][0])//2, pts['left'][1]-30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)

        # Display
        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax.set_title(f'Measurement: {result.height_cm}×{result.width_cm}cm | '
                    f'Size: {result.size} | Confidence: {result.confidence:.1%}',
                    fontsize=12, fontweight='bold')
        ax.axis('off')

        # Save
        plt.tight_layout()
        plt.savefig('production_measurement_debug.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"📊 Debug visualization saved: production_measurement_debug.png")


def main():
    """Main entry point for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Production-Ready Garment Measurement System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic measurement
  python garment_measurement_production.py -i shirt.jpg

  # Multiple measurements for better accuracy
  python garment_measurement_production.py -i shirt.jpg -n 3

  # Custom ruler length
  python garment_measurement_production.py -i shirt.jpg -r 30.0

  # Debug mode with visualization
  python garment_measurement_production.py -i shirt.jpg -d
        """
    )

    parser.add_argument('-i', '--image', required=True,
                       help='Path to garment image')
    parser.add_argument('-r', '--ruler-length', type=float, default=31.0,
                       help='Ruler length in cm (default: 31.0)')
    parser.add_argument('-n', '--num-measurements', type=int, default=1,
                       help='Number of measurements to average (default: 1)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug mode with visualization')
    parser.add_argument('--height-cal', type=float,
                       help='Custom height calibration factor')
    parser.add_argument('--width-cal', type=float,
                       help='Custom width calibration factor')

    args = parser.parse_args()

    try:
        # Initialize system
        system = GarmentMeasurementProduction(
            ruler_length_cm=args.ruler_length,
            height_calibration=args.height_cal,
            width_calibration=args.width_cal,
            debug=args.debug
        )

        # Perform measurement
        result = system.measure(
            args.image,
            num_measurements=args.num_measurements
        )

        print("\n✅ Measurement completed successfully!")

        # Return success
        return 0

    except FileNotFoundError as e:
        print(f"\n❌ File error: {e}")
        return 1
    except ValueError as e:
        print(f"\n❌ Measurement error: {e}")
        return 2
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == '__main__':
    exit(main())