#!/usr/bin/env python3
"""
Intelligent Garment Measurement System
Automatically detects garment type and applies appropriate measurements
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import modules
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier_improved import ImprovedGarmentClassifier as GarmentClassifier, GarmentType, MeasurementStrategy
from measurement_visualizer_clean import CleanMeasurementVisualizer
from garment_measurement_proper import ProperGarmentMeasurer


@dataclass
class IntelligentMeasurementResult:
    """Result structure for intelligent measurements"""
    garment_type: str
    measurements: Dict[str, float]
    size_estimate: str
    confidence: float
    ruler_confidence: float
    classification_confidence: float
    timestamp: str
    image_path: str


class IntelligentGarmentMeasurement:
    """
    Intelligent measurement system that adapts to garment type
    """

    def __init__(self, ruler_length_cm: float = 31.0, debug: bool = False):
        """
        Initialize intelligent measurement system

        Args:
            ruler_length_cm: Known ruler length
            debug: Enable debug output
        """
        self.ruler_length_cm = ruler_length_cm
        self.debug = debug

        # Initialize components
        self.ruler_detector = SmartRulerDetector(known_length_cm=ruler_length_cm, debug=False)
        self.segmenter = FastGarmentSegmenter(debug=False)
        self.classifier = GarmentClassifier(debug=debug)
        self.visualizer = CleanMeasurementVisualizer()

        # Import lens corrector
        from lens_correction import AdaptiveLensCorrector
        self.lens_corrector = AdaptiveLensCorrector(correction_strength=0.5, debug=debug)

        print(f"🤖 Intelligent Garment Measurement System")
        print(f"   Ruler: {ruler_length_cm}cm")
        print(f"   Auto-detects garment type and measures accordingly\n")

    def measure(self, image_path: str) -> IntelligentMeasurementResult:
        """
        Intelligently measure garment

        Args:
            image_path: Path to garment image

        Returns:
            IntelligentMeasurementResult with type-specific measurements
        """
        print(f"{'='*60}")
        print(f"📸 Analyzing: {Path(image_path).name}")
        print(f"{'='*60}\n")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")

        print(f"Image: {image.shape[1]}x{image.shape[0]} pixels\n")

        # Step 1: Correct lens distortion (fisheye/barrel)
        print("🔧 STEP 1: LENS DISTORTION CORRECTION")
        print("-" * 40)

        # Detect camera type and apply correction
        camera_type = self.lens_corrector.detect_camera_type(image)
        image, correction_info = self.lens_corrector.correct_distortion(image, auto_detect=True)

        print(f"✅ Camera type: {camera_type}")
        print(f"✅ Distortion corrected: {correction_info['edge_correction']:.1%} at edges\n")

        # Step 2: Detect ruler for calibration
        print("📏 STEP 2: RULER CALIBRATION")
        print("-" * 40)
        ruler_info = self.ruler_detector.detect_ruler(image)
        pixels_per_cm = ruler_info['pixels_per_cm']
        ruler_bbox = ruler_info['bbox']
        ruler_confidence = ruler_info.get('confidence', 0.5)

        print(f"✅ Scale: {pixels_per_cm:.2f} pixels/cm")
        print(f"   Confidence: {ruler_confidence:.1%}\n")

        # Step 3: Segment garment
        print("✂️ STEP 3: GARMENT SEGMENTATION")
        print("-" * 40)
        mask, seg_info = self.segmenter.segment_garment(image, ruler_bbox=ruler_bbox)
        print(f"✅ Garment isolated: {seg_info['area']:,.0f} pixels\n")

        # Step 4: Classify garment type
        print("🔍 STEP 4: GARMENT CLASSIFICATION")
        print("-" * 40)
        garment_type, class_confidence, features = self.classifier.classify(mask, image)

        # Get measurement strategy for this garment type
        strategy = MeasurementStrategy.get_measurement_points(garment_type)

        print(f"✅ Type: {garment_type.value.upper()}")
        print(f"   Confidence: {class_confidence:.1%}")
        print(f"   Measurements to take: {', '.join(strategy['measurements'][:3])}...\n")

        # Step 5: Apply type-specific measurements
        print("📐 STEP 5: TYPE-SPECIFIC MEASUREMENTS")
        print("-" * 40)
        measurements = self._measure_by_type(
            mask, image, pixels_per_cm, garment_type, features
        )

        # Step 5: Estimate size
        size_estimate = self._estimate_size(garment_type, measurements)

        # Calculate overall confidence
        overall_confidence = (ruler_confidence * 0.4 +
                            class_confidence * 0.3 +
                            seg_info.get('score', 0.8) * 0.3)

        # Print results
        self._print_results(garment_type, measurements, size_estimate)

        # Create result
        result = IntelligentMeasurementResult(
            garment_type=garment_type.value,
            measurements=measurements,
            size_estimate=size_estimate,
            confidence=overall_confidence,
            ruler_confidence=ruler_confidence,
            classification_confidence=class_confidence,
            timestamp=datetime.now().isoformat(),
            image_path=str(image_path)
        )

        # Save report
        self._save_report(result)

        # Always create clean annotated visualization
        annotated_path = f"clean_annotated_{Path(image_path).stem}.png"
        self.visualizer.create_clean_annotated_image(
            image=image,
            mask=mask,
            measurements=measurements,
            garment_type=garment_type,
            pixels_per_cm=pixels_per_cm,
            save_path=annotated_path
        )

        # Also create simple debug visualization if debug mode
        if self.debug:
            self._create_visualization(image, mask, measurements, garment_type, ruler_bbox)

        return result

    def _measure_by_type(self, mask: np.ndarray, image: np.ndarray,
                        pixels_per_cm: float, garment_type: GarmentType,
                        features: Dict) -> Dict[str, float]:
        """Apply type-specific measurements using proper industry standards"""

        # Use the proper measurement system
        proper_measurer = ProperGarmentMeasurer(pixels_per_cm)
        measurements = proper_measurer.measure_garment(mask, garment_type, image)

        print(f"✅ Proper measurements completed using industry standards")

        return measurements

    def _measure_trousers(self, mask: np.ndarray, contour: np.ndarray,
                         pixels_per_cm: float, x: int, y: int, w: int, h: int) -> Dict:
        """Measure trousers/pants/jeans"""

        measurements = {}

        # Total length (waist to hem)
        measurements['length_cm'] = h / pixels_per_cm

        # Waist width (top 10%)
        waist_region = mask[y:y+int(h*0.1), x:x+w]
        waist_widths = [np.sum(row > 0) for row in waist_region]
        if waist_widths:
            waist_width_px = np.median(waist_widths)
            measurements['waist_width_cm'] = waist_width_px / pixels_per_cm
            # Double for circumference estimate
            measurements['waist_circumference_cm'] = measurements['waist_width_cm'] * 2

        # Hip width (upper third, widest part)
        hip_region = mask[y+int(h*0.15):y+int(h*0.35), x:x+w]
        hip_widths = [np.sum(row > 0) for row in hip_region]
        if hip_widths:
            hip_width_px = np.max(hip_widths)
            measurements['hip_width_cm'] = hip_width_px / pixels_per_cm

        # Thigh width (around 40% down)
        thigh_region = mask[y+int(h*0.35):y+int(h*0.45), x:x+w]
        thigh_widths = [np.sum(row > 0) for row in thigh_region]
        if thigh_widths:
            thigh_width_px = np.median(thigh_widths)
            measurements['thigh_width_cm'] = thigh_width_px / pixels_per_cm

        # Knee width (around 65% down)
        knee_region = mask[y+int(h*0.60):y+int(h*0.70), x:x+w]
        knee_widths = [np.sum(row > 0) for row in knee_region]
        if knee_widths:
            knee_width_px = np.median(knee_widths)
            measurements['knee_width_cm'] = knee_width_px / pixels_per_cm

        # Hem width (bottom 5%)
        hem_region = mask[y+int(h*0.95):y+h, x:x+w]
        hem_widths = [np.sum(row > 0) for row in hem_region]
        if hem_widths:
            hem_width_px = np.median(hem_widths)
            measurements['hem_width_cm'] = hem_width_px / pixels_per_cm

        # Try to detect inseam (crotch point)
        # Look for the point where legs split
        crotch_y = self._find_crotch_point(mask, x, y, w, h)
        if crotch_y:
            inseam_px = (y + h) - crotch_y
            measurements['inseam_cm'] = inseam_px / pixels_per_cm
            rise_px = crotch_y - y
            measurements['rise_cm'] = rise_px / pixels_per_cm

        return measurements

    def _measure_shirt(self, mask: np.ndarray, contour: np.ndarray,
                      pixels_per_cm: float, x: int, y: int, w: int, h: int) -> Dict:
        """Measure shirt/t-shirt/top"""

        measurements = {}

        # Total length
        measurements['length_cm'] = h / pixels_per_cm

        # Chest width (upper third)
        chest_region = mask[y+int(h*0.25):y+int(h*0.35), x:x+w]
        chest_widths = [np.sum(row > 0) for row in chest_region]
        if chest_widths:
            chest_width_px = np.max(chest_widths)
            measurements['chest_width_cm'] = chest_width_px / pixels_per_cm
            measurements['chest_circumference_cm'] = measurements['chest_width_cm'] * 2

        # Waist width (middle)
        waist_region = mask[y+int(h*0.45):y+int(h*0.55), x:x+w]
        waist_widths = [np.sum(row > 0) for row in waist_region]
        if waist_widths:
            waist_width_px = np.median(waist_widths)
            measurements['waist_width_cm'] = waist_width_px / pixels_per_cm

        # Hem width (bottom)
        hem_region = mask[y+int(h*0.90):y+h, x:x+w]
        hem_widths = [np.sum(row > 0) for row in hem_region]
        if hem_widths:
            hem_width_px = np.median(hem_widths)
            measurements['hem_width_cm'] = hem_width_px / pixels_per_cm

        # Shoulder width (if detectable at top)
        shoulder_region = mask[y:y+int(h*0.1), x:x+w]
        if shoulder_region.size > 0:
            shoulder_points = self._find_shoulder_points(shoulder_region)
            if shoulder_points:
                shoulder_width_px = shoulder_points[1] - shoulder_points[0]
                measurements['shoulder_width_cm'] = shoulder_width_px / pixels_per_cm

        return measurements

    def _measure_dress(self, mask: np.ndarray, contour: np.ndarray,
                      pixels_per_cm: float, x: int, y: int, w: int, h: int) -> Dict:
        """Measure dress/skirt"""

        measurements = {}

        # Total length
        measurements['length_cm'] = h / pixels_per_cm

        # Bust width (upper portion)
        bust_region = mask[y+int(h*0.15):y+int(h*0.25), x:x+w]
        bust_widths = [np.sum(row > 0) for row in bust_region]
        if bust_widths:
            bust_width_px = np.max(bust_widths)
            measurements['bust_width_cm'] = bust_width_px / pixels_per_cm
            measurements['bust_circumference_cm'] = measurements['bust_width_cm'] * 2

        # Waist (narrowest point in middle third)
        waist_region = mask[y+int(h*0.35):y+int(h*0.55), x:x+w]
        waist_widths = [np.sum(row > 0) for row in waist_region]
        if waist_widths:
            waist_width_px = np.min(waist_widths)
            measurements['waist_width_cm'] = waist_width_px / pixels_per_cm

        # Hip width (lower third)
        hip_region = mask[y+int(h*0.60):y+int(h*0.75), x:x+w]
        hip_widths = [np.sum(row > 0) for row in hip_region]
        if hip_widths:
            hip_width_px = np.max(hip_widths)
            measurements['hip_width_cm'] = hip_width_px / pixels_per_cm

        # Hem width
        hem_region = mask[y+int(h*0.90):y+h, x:x+w]
        hem_widths = [np.sum(row > 0) for row in hem_region]
        if hem_widths:
            hem_width_px = np.median(hem_widths)
            measurements['hem_width_cm'] = hem_width_px / pixels_per_cm

        return measurements

    def _measure_jacket(self, mask: np.ndarray, contour: np.ndarray,
                       pixels_per_cm: float, x: int, y: int, w: int, h: int) -> Dict:
        """Measure jacket/coat"""

        # Similar to shirt but with potentially different proportions
        return self._measure_shirt(mask, contour, pixels_per_cm, x, y, w, h)

    def _measure_basic(self, mask: np.ndarray, contour: np.ndarray,
                      pixels_per_cm: float, x: int, y: int, w: int, h: int) -> Dict:
        """Basic measurements for unknown garment types"""

        measurements = {
            'height_cm': h / pixels_per_cm,
            'width_cm': w / pixels_per_cm,
            'area_cm2': cv2.contourArea(contour) / (pixels_per_cm ** 2)
        }

        return measurements

    def _find_crotch_point(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[int]:
        """Find crotch point for inseam measurement"""

        # Look for where the gap between legs starts
        # Scan from middle going down
        middle_x = x + w // 2

        for scan_y in range(y + int(h * 0.3), y + int(h * 0.7)):
            # Check for gap in middle
            if scan_y < mask.shape[0] and middle_x < mask.shape[1]:
                if mask[scan_y, middle_x] == 0:  # Found gap
                    # Verify it's really the crotch (gap continues)
                    gap_continues = True
                    for check_y in range(scan_y, min(scan_y + 20, mask.shape[0])):
                        if mask[check_y, middle_x] > 0:
                            gap_continues = False
                            break

                    if gap_continues:
                        return scan_y

        return None

    def _find_shoulder_points(self, shoulder_region: np.ndarray) -> Optional[Tuple[int, int]]:
        """Find shoulder points in top region"""

        if shoulder_region.size == 0:
            return None

        # Find leftmost and rightmost points
        for row in shoulder_region:
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                return (nonzero[0], nonzero[-1])

        return None

    def _estimate_size(self, garment_type: GarmentType, measurements: Dict) -> str:
        """Estimate size based on garment type and measurements"""

        if garment_type == GarmentType.TROUSERS:
            # Use waist circumference for trouser sizing
            if 'waist_circumference_cm' in measurements:
                waist = measurements['waist_circumference_cm']
                if waist < 66:
                    return "24-26 (XS)"
                elif waist < 71:
                    return "27-28 (S)"
                elif waist < 76:
                    return "29-30 (M)"
                elif waist < 81:
                    return "31-32 (L)"
                elif waist < 86:
                    return "33-34 (XL)"
                elif waist < 91:
                    return "35-36 (XXL)"
                else:
                    return "37+ (XXXL)"

        elif garment_type == GarmentType.SHIRT:
            # Use chest circumference for shirt sizing
            if 'chest_circumference_cm' in measurements:
                chest = measurements['chest_circumference_cm']
                if chest < 86:
                    return "XS"
                elif chest < 96:
                    return "S"
                elif chest < 106:
                    return "M"
                elif chest < 116:
                    return "L"
                elif chest < 126:
                    return "XL"
                else:
                    return "XXL+"

        elif garment_type == GarmentType.DRESS:
            # Use bust circumference for dress sizing
            if 'bust_circumference_cm' in measurements:
                bust = measurements['bust_circumference_cm']
                if bust < 82:
                    return "XS (0-2)"
                elif bust < 87:
                    return "S (4-6)"
                elif bust < 92:
                    return "M (8-10)"
                elif bust < 97:
                    return "L (12-14)"
                elif bust < 102:
                    return "XL (16)"
                else:
                    return "XXL+ (18+)"

        return "Unable to estimate"

    def _print_results(self, garment_type: GarmentType, measurements: Dict, size_estimate: str):
        """Print measurement results"""

        print(f"\n{'='*60}")
        print(f"📊 INTELLIGENT MEASUREMENT RESULTS")
        print(f"{'='*60}\n")

        print(f"🏷️ GARMENT TYPE: {garment_type.value.upper()}")
        print(f"📏 SIZE ESTIMATE: {size_estimate}\n")

        print(f"📐 MEASUREMENTS:")

        # Format measurements based on type
        if garment_type == GarmentType.TROUSERS:
            if 'outseam_cm' in measurements:
                print(f"   Outseam (Length): {measurements['outseam_cm']:.1f} cm")
            if 'waist_width_cm' in measurements:
                print(f"   Waist Width: {measurements['waist_width_cm']:.1f} cm")
                print(f"   Waist Circumference (est): {measurements.get('waist_circumference_cm', 0):.1f} cm")
            if 'hip_width_cm' in measurements:
                print(f"   Hip Width: {measurements['hip_width_cm']:.1f} cm")
            if 'inseam_cm' in measurements:
                print(f"   Inseam: {measurements['inseam_cm']:.1f} cm")
            if 'rise_cm' in measurements:
                print(f"   Rise: {measurements['rise_cm']:.1f} cm")
            if 'thigh_width_cm' in measurements:
                print(f"   Thigh Width: {measurements['thigh_width_cm']:.1f} cm")
            if 'knee_width_cm' in measurements:
                print(f"   Knee Width: {measurements['knee_width_cm']:.1f} cm")
            if 'leg_opening_cm' in measurements:
                print(f"   Leg Opening: {measurements['leg_opening_cm']:.1f} cm")

        elif garment_type == GarmentType.SHIRT:
            if 'body_length_cm' in measurements:
                print(f"   Body Length (HPS to hem): {measurements['body_length_cm']:.1f} cm")
            if 'chest_width_cm' in measurements:
                print(f"   Chest Width (1\" below armhole): {measurements['chest_width_cm']:.1f} cm")
                print(f"   Chest Circumference (est): {measurements.get('chest_circumference_cm', 0):.1f} cm")
            if 'waist_width_cm' in measurements:
                print(f"   Waist Width: {measurements['waist_width_cm']:.1f} cm")
            if 'hem_width_cm' in measurements:
                print(f"   Bottom Sweep (Hem): {measurements['hem_width_cm']:.1f} cm")
            if 'shoulder_width_cm' in measurements:
                print(f"   Shoulder Width: {measurements['shoulder_width_cm']:.1f} cm")

        else:
            # Generic output for other types
            for key, value in measurements.items():
                if not key.endswith('_px'):
                    print(f"   {key.replace('_', ' ').title()}: {value:.1f} cm")

        print(f"\n{'='*60}")

    def _save_report(self, result: IntelligentMeasurementResult):
        """Save measurement report"""

        report_dir = Path("measurement_reports")
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intelligent_{result.garment_type}_{timestamp}.json"
        report_path = report_dir / filename

        report_data = asdict(result)
        report_data['system'] = 'IntelligentGarmentMeasurement v1.0'

        # Convert numpy types to Python types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_numpy(item) for item in obj)
            return obj

        report_data = convert_numpy(report_data)

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"📁 Report saved: {report_path}")

    def _create_visualization(self, image: np.ndarray, mask: np.ndarray,
                            measurements: Dict, garment_type: GarmentType,
                            ruler_bbox: Tuple):
        """Create debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))

        # Show original with type
        ax = axes[0]
        ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax.set_title(f'Detected: {garment_type.value.upper()}', fontweight='bold')

        # Draw ruler box
        rx, ry, rw, rh = ruler_bbox
        rect = plt.Rectangle((rx, ry), rw, rh, fill=False, edgecolor='yellow', linewidth=2)
        ax.add_patch(rect)
        ax.axis('off')

        # Show measurements
        ax = axes[1]
        ax.imshow(mask, cmap='gray')

        # Add measurement annotations
        text_str = f"Measurements:\n"
        for i, (key, value) in enumerate(list(measurements.items())[:5]):
            if not key.endswith('_px') and not key.endswith('_points'):
                # Only format numeric values, skip dictionaries (coordinate points)
                if isinstance(value, (int, float)):
                    text_str += f"{key.replace('_cm', '').replace('_', ' ').title()}: {value:.1f} cm\n"

        ax.text(0.02, 0.98, text_str, transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_title('Segmented Garment', fontweight='bold')
        ax.axis('off')

        plt.suptitle(f'Intelligent Measurement - {garment_type.value.upper()}')
        plt.tight_layout()
        plt.savefig('intelligent_measurement_debug.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"📊 Debug visualization saved: intelligent_measurement_debug.png")


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Intelligent Garment Measurement System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The system automatically detects garment type and applies appropriate measurements:

- TROUSERS: length, waist, hip, inseam, hem widths
- SHIRTS: length, chest, waist, shoulder widths
- DRESSES: length, bust, waist, hip, hem widths
- JACKETS: length, chest, shoulder widths

Examples:
  python garment_measurement_intelligent.py -i jeans.jpg
  python garment_measurement_intelligent.py -i shirt.jpg -d
        """
    )

    parser.add_argument('-i', '--image', required=True,
                       help='Path to garment image')
    parser.add_argument('-r', '--ruler', type=float, default=31.0,
                       help='Ruler length in cm (default: 31.0)')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug mode with visualization')

    args = parser.parse_args()

    try:
        # Initialize system
        system = IntelligentGarmentMeasurement(
            ruler_length_cm=args.ruler,
            debug=args.debug
        )

        # Measure
        result = system.measure(args.image)

        print(f"\n✅ Intelligent measurement completed!")
        print(f"   Type: {result.garment_type}")
        print(f"   Size: {result.size_estimate}")
        print(f"   Confidence: {result.confidence:.1%}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())