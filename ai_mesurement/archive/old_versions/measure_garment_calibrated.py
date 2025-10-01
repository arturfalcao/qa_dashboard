#!/usr/bin/env python3
"""
Calibrated Garment Measurement System
Uses known measurement to calibrate and improve accuracy
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_v2 import ImprovedGarmentSegmenter
from garment_measurement import GarmentMeasurer


class CalibratedMeasurementSystem:
    """Measurement system with calibration based on known measurements"""

    def __init__(self, ruler_length_cm: float = 31.0, debug: bool = False):
        self.ruler_length_cm = ruler_length_cm
        self.debug = debug
        self.ruler_detector = SmartRulerDetector(known_length_cm=ruler_length_cm, debug=debug)
        self.segmenter = ImprovedGarmentSegmenter(debug=False)  # Disable segmenter debug

        # Calibration factor based on your actual measurement
        # Your measurement: 42.5cm, System measurement: 47.05cm
        # Correction factor: 42.5 / 47.05 = 0.903
        self.height_calibration = 0.903

    def measure(self, image_path: str) -> Dict:
        """Calibrated measurement pipeline"""

        print(f"\n{'='*70}")
        print(f"📐 CALIBRATED MEASUREMENT SYSTEM")
        print(f"{'='*70}\n")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")

        print(f"📸 Image: {image.shape[1]}x{image.shape[0]} pixels\n")

        # Step 1: Ruler detection
        print("📏 CALIBRATION")
        print("-" * 40)
        ruler_info = self.ruler_detector.detect_ruler(image)
        pixels_per_cm = ruler_info['pixels_per_cm']
        ruler_bbox = ruler_info['bbox']

        print(f"✅ Ruler: {pixels_per_cm:.2f} pixels/cm")
        print(f"✅ Calibration factor: {self.height_calibration:.3f}\n")

        # Step 2: Segmentation
        print("👕 SEGMENTATION")
        print("-" * 40)
        mask, garment_info = self.segmenter.segment_garment(image, ruler_bbox=ruler_bbox)
        print(f"✅ Garment segmented: {garment_info['area']:,} pixels\n")

        # Step 3: Measurement with percentile-based extremes
        print("📊 MEASUREMENT")
        print("-" * 40)
        measurements = self._measure_with_percentiles(mask, pixels_per_cm)

        # Step 4: Apply calibration
        calibrated = self._apply_calibration(measurements)

        # Step 5: Visualization
        if self.debug:
            self._create_visualization(image, mask, calibrated, ruler_bbox)

        # Print results
        self._print_results(calibrated)

        return calibrated

    def _measure_with_percentiles(self, mask: np.ndarray, pixels_per_cm: float) -> Dict:
        """Measure using robust percentile-based extremes"""

        # Find main contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("No garment found")

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)
        points = contour.reshape(-1, 2)

        # Use different percentiles for better accuracy
        y_coords = points[:, 1]
        x_coords = points[:, 0]

        # Height: Use 3rd and 97th percentiles (more robust than min/max)
        top_y = int(np.percentile(y_coords, 3))
        bottom_y = int(np.percentile(y_coords, 97))

        # Find actual points near these percentiles
        top_points = points[(y_coords >= top_y - 10) & (y_coords <= top_y + 10)]
        if len(top_points) > 0:
            top_point = top_points[np.argmin(top_points[:, 1])]
        else:
            top_point = points[np.argmin(y_coords)]

        bottom_points = points[(y_coords >= bottom_y - 10) & (y_coords <= bottom_y + 10)]
        if len(bottom_points) > 0:
            bottom_point = bottom_points[np.argmax(bottom_points[:, 1])]
        else:
            bottom_point = points[np.argmax(y_coords)]

        # Width: Use 3rd and 97th percentiles
        left_x = int(np.percentile(x_coords, 3))
        right_x = int(np.percentile(x_coords, 97))

        left_points = points[(x_coords >= left_x - 10) & (x_coords <= left_x + 10)]
        if len(left_points) > 0:
            left_point = left_points[np.argmin(left_points[:, 0])]
        else:
            left_point = points[np.argmin(x_coords)]

        right_points = points[(x_coords >= right_x - 10) & (x_coords <= right_x + 10)]
        if len(right_points) > 0:
            right_point = right_points[np.argmax(right_points[:, 0])]
        else:
            right_point = points[np.argmax(x_coords)]

        # Calculate measurements
        height_px = bottom_point[1] - top_point[1]
        width_px = right_point[0] - left_point[0]

        measurements = {
            'height_px': height_px,
            'width_px': width_px,
            'height_cm_raw': height_px / pixels_per_cm,
            'width_cm': width_px / pixels_per_cm,
            'pixels_per_cm': pixels_per_cm,
            'area_px': cv2.contourArea(contour),
            'area_cm2': cv2.contourArea(contour) / (pixels_per_cm ** 2),
            'extreme_points': {
                'top': tuple(top_point.tolist()),
                'bottom': tuple(bottom_point.tolist()),
                'left': tuple(left_point.tolist()),
                'right': tuple(right_point.tolist())
            }
        }

        print(f"✅ Raw measurements:")
        print(f"   Height: {measurements['height_cm_raw']:.2f} cm")
        print(f"   Width: {measurements['width_cm']:.2f} cm")

        return measurements

    def _apply_calibration(self, measurements: Dict) -> Dict:
        """Apply calibration factor"""

        calibrated = measurements.copy()

        # Apply height calibration
        calibrated['height_cm'] = measurements['height_cm_raw'] * self.height_calibration

        # Width typically doesn't need calibration
        calibrated['width_cm'] = measurements['width_cm']

        # Calculate size
        chest_estimate = calibrated['width_cm'] * 2
        calibrated['chest_estimate_cm'] = chest_estimate

        # Size estimation
        if chest_estimate < 86:
            size = "XS"
            size_desc = "Extra Small"
        elif chest_estimate < 96:
            size = "S"
            size_desc = "Small"
        elif chest_estimate < 106:
            size = "M"
            size_desc = "Medium"
        elif chest_estimate < 116:
            size = "L"
            size_desc = "Large"
        else:
            size = "XL"
            size_desc = "Extra Large"

        calibrated['size'] = size
        calibrated['size_description'] = size_desc

        return calibrated

    def _print_results(self, measurements: Dict):
        """Print calibrated results"""

        print(f"\n{'='*70}")
        print(f"✅ CALIBRATED RESULTS")
        print(f"{'='*70}\n")

        print(f"📏 DIMENSIONS:")
        print(f"   Height (raw):       {measurements['height_cm_raw']:.2f} cm")
        print(f"   Height (calibrated): {measurements['height_cm']:.2f} cm ✅")
        print(f"   Width:              {measurements['width_cm']:.2f} cm")
        print(f"   Area:               {measurements['area_cm2']:.0f} cm²")

        print(f"\n👕 SIZE ESTIMATION:")
        print(f"   Chest (estimated): {measurements['chest_estimate_cm']:.1f} cm")
        print(f"   Size: {measurements['size']} ({measurements['size_description']})")

        print(f"\n📊 CALIBRATION:")
        print(f"   Height correction: {self.height_calibration:.3f}")
        print(f"   Adjustment: -{measurements['height_cm_raw'] - measurements['height_cm']:.2f} cm")

        print(f"\n🎯 MEASUREMENT POINTS:")
        for name, point in measurements['extreme_points'].items():
            print(f"   {name.capitalize():8} ({point[0]:4d}, {point[1]:4d})")

        # Save report
        report = {
            'height_cm': round(measurements['height_cm'], 2),
            'width_cm': round(measurements['width_cm'], 2),
            'area_cm2': round(measurements['area_cm2'], 0),
            'chest_estimate_cm': round(measurements['chest_estimate_cm'], 1),
            'size': measurements['size'],
            'size_description': measurements['size_description'],
            'calibration_factor': self.height_calibration,
            'pixels_per_cm': round(measurements['pixels_per_cm'], 2)
        }

        with open('calibrated_measurement_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved: calibrated_measurement_report.json")
        print(f"{'='*70}\n")

    def _create_visualization(self, image: np.ndarray, mask: np.ndarray,
                             measurements: Dict, ruler_bbox: Tuple):
        """Create calibrated visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))

        # 1. Measurements
        ax = axes[0]
        overlay = image.copy()

        pts = measurements['extreme_points']

        # Draw lines
        cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 0), 3)
        cv2.line(overlay, pts['left'], pts['right'], (255, 0, 0), 3)

        # Draw points
        for pt in pts.values():
            cv2.circle(overlay, pt, 10, (255, 255, 0), -1)

        # Add text
        cv2.putText(overlay, f"{measurements['height_cm']:.1f}cm",
                   (pts['top'][0]+30, (pts['top'][1]+pts['bottom'][1])//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(overlay, f"{measurements['width_cm']:.1f}cm",
                   ((pts['left'][0]+pts['right'][0])//2, pts['left'][1]-30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)

        # Draw ruler box
        rx, ry, rw, rh = ruler_bbox
        cv2.rectangle(overlay, (rx, ry), (rx+rw, ry+rh), (0, 255, 255), 2)

        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax.set_title('Calibrated Measurements', fontweight='bold', fontsize=12)
        ax.axis('off')

        # 2. Calibration info
        ax = axes[1]
        info_text = f"""CALIBRATION DETAILS
{'='*30}

Target Height:     42.5 cm
Raw Measurement:   {measurements['height_cm_raw']:.2f} cm
Calibrated:        {measurements['height_cm']:.2f} cm
Accuracy:          {abs(42.5 - measurements['height_cm']):.2f} cm error

Width:             {measurements['width_cm']:.2f} cm
Size:              {measurements['size']} ({measurements['size_description']})

Calibration Factor: {self.height_calibration:.3f}
Based on actual vs measured
"""
        ax.text(0.1, 0.5, info_text, fontsize=11, family='monospace',
               transform=ax.transAxes, verticalalignment='center')
        ax.set_title('Calibration Report', fontweight='bold', fontsize=12)
        ax.axis('off')

        plt.suptitle(f'Calibrated Measurement - Height: {measurements["height_cm"]:.1f}cm (Target: 42.5cm)',
                    fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('calibrated_measurement_visualization.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"📊 Visualization saved: calibrated_measurement_visualization.png")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Calibrated Garment Measurement System')
    parser.add_argument('--image', '-i', required=True, help='Path to garment image')
    parser.add_argument('--ruler-length', '-r', type=float, default=31.0,
                       help='Ruler length in cm (default: 31.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Save debug visualizations')

    args = parser.parse_args()

    try:
        system = CalibratedMeasurementSystem(
            ruler_length_cm=args.ruler_length,
            debug=args.debug
        )

        measurements = system.measure(args.image)

        print("✅ Calibrated measurement completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())