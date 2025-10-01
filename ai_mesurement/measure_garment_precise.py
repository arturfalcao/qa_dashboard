#!/usr/bin/env python3
"""
Precise Garment Measurement System V4
Enhanced accuracy with improved boundary detection and noise filtering
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from ruler_detection_smart import SmartRulerDetector


class PreciseGarmentMeasurer:
    """High-precision measurement system with improved accuracy"""

    def __init__(self, ruler_length_cm: float = 31.0, debug: bool = False):
        self.ruler_length_cm = ruler_length_cm
        self.debug = debug
        self.ruler_detector = SmartRulerDetector(known_length_cm=ruler_length_cm, debug=debug)

    def measure(self, image_path: str) -> Dict:
        """Main measurement pipeline with enhanced precision"""

        print(f"\n{'='*70}")
        print(f"🎯 PRECISE GARMENT MEASUREMENT SYSTEM V4")
        print(f"{'='*70}\n")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Cannot load image: {image_path}")

        print(f"📸 Image: {image.shape[1]}x{image.shape[0]} pixels\n")

        # Step 1: Ruler calibration
        print("📏 STEP 1: RULER CALIBRATION")
        print("-" * 40)
        ruler_info = self.ruler_detector.detect_ruler(image)
        pixels_per_cm = ruler_info['pixels_per_cm']
        ruler_bbox = ruler_info['bbox']

        print(f"✅ Ruler detected: {pixels_per_cm:.2f} pixels/cm")
        print(f"   Position: x={ruler_bbox[0]}, y={ruler_bbox[1]}")
        print(f"   Confidence: {ruler_info.get('confidence', 0):.1%}\n")

        # Step 2: Precise segmentation
        print("👕 STEP 2: PRECISE SEGMENTATION")
        print("-" * 40)
        mask = self._segment_garment_precise(image, ruler_bbox)

        # Step 3: Clean and refine mask
        print("🧹 STEP 3: MASK REFINEMENT")
        print("-" * 40)
        refined_mask = self._refine_mask(mask)

        # Step 4: Accurate measurements
        print("📐 STEP 4: PRECISE MEASUREMENTS")
        print("-" * 40)
        measurements = self._measure_precise(refined_mask, pixels_per_cm)

        # Step 5: Validation and correction
        print("✨ STEP 5: VALIDATION")
        print("-" * 40)
        validated_measurements = self._validate_measurements(measurements, image.shape)

        # Generate visualization
        if self.debug:
            self._create_debug_visualization(
                image, mask, refined_mask, validated_measurements, ruler_bbox
            )

        # Print results
        self._print_results(validated_measurements)

        return validated_measurements

    def _segment_garment_precise(self, image: np.ndarray, ruler_bbox: Tuple) -> np.ndarray:
        """Precise garment segmentation with multiple methods"""

        # Create initial mask excluding ruler
        h, w = image.shape[:2]
        initial_mask = np.ones((h, w), dtype=np.uint8) * 255
        rx, ry, rw, rh = ruler_bbox
        initial_mask[ry:ry+rh, rx:rx+rw] = 0

        # Method 1: Color-based segmentation with HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # For beige/tan colors
        lower_beige = np.array([10, 20, 100])
        upper_beige = np.array([25, 150, 255])
        color_mask = cv2.inRange(hsv, lower_beige, upper_beige)

        # Apply initial mask
        color_mask = cv2.bitwise_and(color_mask, initial_mask)

        # Method 2: Edge-based segmentation
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)

        # Dilate edges to create regions
        kernel = np.ones((5,5), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=2)

        # Find contours from edges
        contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create edge-based mask
        edge_mask = np.zeros((h, w), dtype=np.uint8)
        if contours:
            # Find largest contour (likely the garment)
            largest_contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(edge_mask, [largest_contour], -1, 255, -1)

        # Combine masks with weighted average
        combined_mask = cv2.addWeighted(color_mask, 0.6, edge_mask, 0.4, 0)
        combined_mask = (combined_mask > 127).astype(np.uint8) * 255

        print(f"✅ Segmentation complete")
        print(f"   Color pixels: {np.sum(color_mask > 0):,}")
        print(f"   Edge pixels: {np.sum(edge_mask > 0):,}")
        print(f"   Combined pixels: {np.sum(combined_mask > 0):,}")

        return combined_mask

    def _refine_mask(self, mask: np.ndarray) -> np.ndarray:
        """Refine mask with morphological operations and noise removal"""

        # Remove small noise with opening
        kernel_small = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=2)

        # Close small gaps
        kernel_medium = np.ones((5,5), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_medium, iterations=1)

        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)

        # Keep only the largest component (excluding background)
        if num_labels > 1:
            # Find largest non-background component
            largest_label = 1
            largest_area = stats[1, cv2.CC_STAT_AREA]

            for i in range(2, num_labels):
                if stats[i, cv2.CC_STAT_AREA] > largest_area:
                    largest_area = stats[i, cv2.CC_STAT_AREA]
                    largest_label = i

            # Create refined mask with only largest component
            refined_mask = (labels == largest_label).astype(np.uint8) * 255

            print(f"✅ Mask refined")
            print(f"   Components found: {num_labels - 1}")
            print(f"   Largest component: {largest_area:,} pixels")
            print(f"   Noise removed: {np.sum(cleaned > 0) - largest_area:,} pixels")
        else:
            refined_mask = cleaned
            print(f"✅ Mask refined (single component)")

        # Final smoothing with median filter
        refined_mask = cv2.medianBlur(refined_mask, 5)

        return refined_mask

    def _measure_precise(self, mask: np.ndarray, pixels_per_cm: float) -> Dict:
        """Precise measurement using contour analysis"""

        # Find contour of refined mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No garment contour found")

        # Get the main contour
        contour = max(contours, key=cv2.contourArea)

        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Find extreme points using percentile to avoid outliers
        points = contour.reshape(-1, 2)

        # Height measurement (vertical)
        y_coords = points[:, 1]
        # Use 5th and 95th percentile to avoid outliers
        top_y = int(np.percentile(y_coords, 1))  # 1st percentile for top
        bottom_y = int(np.percentile(y_coords, 99))  # 99th percentile for bottom

        # Find actual points at these heights
        top_points = points[y_coords <= top_y + 5]
        if len(top_points) > 0:
            top_point = top_points[np.argmin(top_points[:, 1])]
        else:
            top_point = points[np.argmin(y_coords)]

        bottom_points = points[y_coords >= bottom_y - 5]
        if len(bottom_points) > 0:
            bottom_point = bottom_points[np.argmax(bottom_points[:, 1])]
        else:
            bottom_point = points[np.argmax(y_coords)]

        # Width measurement (horizontal)
        x_coords = points[:, 0]
        left_x = int(np.percentile(x_coords, 1))
        right_x = int(np.percentile(x_coords, 99))

        # Find actual points at these widths
        left_points = points[x_coords <= left_x + 5]
        if len(left_points) > 0:
            left_point = left_points[np.argmin(left_points[:, 0])]
        else:
            left_point = points[np.argmin(x_coords)]

        right_points = points[x_coords >= right_x - 5]
        if len(right_points) > 0:
            right_point = right_points[np.argmax(right_points[:, 0])]
        else:
            right_point = points[np.argmax(x_coords)]

        # Calculate measurements
        height_px = bottom_point[1] - top_point[1]
        width_px = right_point[0] - left_point[0]

        height_cm = height_px / pixels_per_cm
        width_cm = width_px / pixels_per_cm

        # Area calculation
        area_px = cv2.contourArea(contour)
        area_cm2 = area_px / (pixels_per_cm ** 2)

        # Perimeter
        perimeter_px = cv2.arcLength(contour, True)
        perimeter_cm = perimeter_px / pixels_per_cm

        measurements = {
            'height_cm': height_cm,
            'width_cm': width_cm,
            'area_cm2': area_cm2,
            'perimeter_cm': perimeter_cm,
            'height_px': height_px,
            'width_px': width_px,
            'pixels_per_cm': pixels_per_cm,
            'extreme_points': {
                'top': tuple(top_point.tolist()),
                'bottom': tuple(bottom_point.tolist()),
                'left': tuple(left_point.tolist()),
                'right': tuple(right_point.tolist())
            },
            'bbox': {'x': x, 'y': y, 'w': w, 'h': h},
            'bbox_height_cm': h / pixels_per_cm,
            'bbox_width_cm': w / pixels_per_cm
        }

        print(f"✅ Measurements calculated")
        print(f"   Height: {height_px:.0f} px = {height_cm:.2f} cm")
        print(f"   Width: {width_px:.0f} px = {width_cm:.2f} cm")
        print(f"   Using percentile-based extremes (outlier resistant)")

        return measurements

    def _validate_measurements(self, measurements: Dict, image_shape: Tuple) -> Dict:
        """Validate and potentially correct measurements"""

        height_cm = measurements['height_cm']
        width_cm = measurements['width_cm']

        # Check if measurements are reasonable for a garment
        warnings = []

        if height_cm < 20 or height_cm > 100:
            warnings.append(f"Height {height_cm:.1f}cm may be incorrect")

        if width_cm < 20 or width_cm > 80:
            warnings.append(f"Width {width_cm:.1f}cm may be incorrect")

        aspect_ratio = width_cm / height_cm
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            warnings.append(f"Aspect ratio {aspect_ratio:.2f} is unusual")

        # Check if extreme points make sense
        points = measurements['extreme_points']
        if points['top'][1] >= points['bottom'][1]:
            warnings.append("Top/bottom points inverted")

        if points['left'][0] >= points['right'][0]:
            warnings.append("Left/right points inverted")

        measurements['validation'] = {
            'passed': len(warnings) == 0,
            'warnings': warnings,
            'aspect_ratio': aspect_ratio
        }

        if warnings:
            print(f"⚠️  Validation warnings:")
            for w in warnings:
                print(f"   - {w}")
        else:
            print(f"✅ All measurements validated successfully")

        return measurements

    def _print_results(self, measurements: Dict):
        """Print final measurement results"""

        print(f"\n{'='*70}")
        print(f"📊 MEASUREMENT RESULTS")
        print(f"{'='*70}\n")

        print(f"📏 DIMENSIONS:")
        print(f"   Height: {measurements['height_cm']:.2f} cm ({measurements['height_cm']/2.54:.1f} inches)")
        print(f"   Width:  {measurements['width_cm']:.2f} cm ({measurements['width_cm']/2.54:.1f} inches)")
        print(f"   Area:   {measurements['area_cm2']:.0f} cm²")

        print(f"\n📐 BOUNDING BOX:")
        print(f"   Height: {measurements['bbox_height_cm']:.2f} cm")
        print(f"   Width:  {measurements['bbox_width_cm']:.2f} cm")

        print(f"\n🎯 EXTREME POINTS:")
        for name, point in measurements['extreme_points'].items():
            print(f"   {name.capitalize():8} ({point[0]:4d}, {point[1]:4d})")

        print(f"\n📊 METRICS:")
        print(f"   Scale: {measurements['pixels_per_cm']:.2f} pixels/cm")
        print(f"   Aspect Ratio: {measurements['validation']['aspect_ratio']:.2f}")

        if not measurements['validation']['passed']:
            print(f"\n⚠️  WARNINGS:")
            for warning in measurements['validation']['warnings']:
                print(f"   - {warning}")

        # Save JSON report
        report = {
            'height_cm': measurements['height_cm'],
            'width_cm': measurements['width_cm'],
            'area_cm2': measurements['area_cm2'],
            'perimeter_cm': measurements['perimeter_cm'],
            'pixels_per_cm': measurements['pixels_per_cm'],
            'aspect_ratio': measurements['validation']['aspect_ratio'],
            'validation_passed': measurements['validation']['passed'],
            'warnings': measurements['validation']['warnings']
        }

        with open('precise_measurement_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Report saved to: precise_measurement_report.json")
        print(f"{'='*70}\n")

    def _create_debug_visualization(self, image: np.ndarray, original_mask: np.ndarray,
                                   refined_mask: np.ndarray, measurements: Dict,
                                   ruler_bbox: Tuple):
        """Create comprehensive debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))

        # 1. Original image
        ax = axes[0, 0]
        ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax.set_title('Original Image', fontweight='bold')
        ax.axis('off')

        # 2. Original mask
        ax = axes[0, 1]
        ax.imshow(original_mask, cmap='gray')
        ax.set_title('Initial Segmentation', fontweight='bold')
        ax.axis('off')

        # 3. Refined mask
        ax = axes[0, 2]
        ax.imshow(refined_mask, cmap='gray')
        ax.set_title('Refined Mask (Cleaned)', fontweight='bold')
        ax.axis('off')

        # 4. Measurement overlay
        ax = axes[1, 0]
        overlay = image.copy()

        # Draw measurement lines
        pts = measurements['extreme_points']
        cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 0), 3)
        cv2.line(overlay, pts['left'], pts['right'], (255, 0, 0), 3)

        # Draw points
        for point in pts.values():
            cv2.circle(overlay, point, 8, (255, 255, 0), -1)

        # Add text
        cv2.putText(overlay, f"H: {measurements['height_cm']:.1f}cm",
                   (pts['top'][0]+20, (pts['top'][1]+pts['bottom'][1])//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(overlay, f"W: {measurements['width_cm']:.1f}cm",
                   ((pts['left'][0]+pts['right'][0])//2, pts['left'][1]-20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax.set_title('Precise Measurements', fontweight='bold')
        ax.axis('off')

        # 5. Contour visualization
        ax = axes[1, 1]
        contour_img = np.zeros_like(image)
        contours, _ = cv2.findContours(refined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(contour_img, contours, -1, (0, 255, 0), 2)

        # Draw bounding box
        bbox = measurements['bbox']
        cv2.rectangle(contour_img, (bbox['x'], bbox['y']),
                     (bbox['x']+bbox['w'], bbox['y']+bbox['h']),
                     (255, 0, 0), 2)

        ax.imshow(cv2.cvtColor(contour_img, cv2.COLOR_BGR2RGB))
        ax.set_title('Contour & Bounding Box', fontweight='bold')
        ax.axis('off')

        # 6. Ruler location
        ax = axes[1, 2]
        ruler_img = image.copy()
        rx, ry, rw, rh = ruler_bbox
        cv2.rectangle(ruler_img, (rx, ry), (rx+rw, ry+rh), (0, 255, 0), 3)
        cv2.putText(ruler_img, "31cm Ruler", (rx, ry-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        ax.imshow(cv2.cvtColor(ruler_img, cv2.COLOR_BGR2RGB))
        ax.set_title('Ruler Detection', fontweight='bold')
        ax.axis('off')

        plt.suptitle(f'Precise Measurement Debug - H:{measurements["height_cm"]:.1f}cm W:{measurements["width_cm"]:.1f}cm',
                    fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('debug_precise_measurement.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"📊 Debug visualization saved: debug_precise_measurement.png")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Precise Garment Measurement System V4')
    parser.add_argument('--image', '-i', required=True, help='Path to garment image')
    parser.add_argument('--ruler-length', '-r', type=float, default=31.0,
                       help='Known ruler length in cm (default: 31.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug visualizations')

    args = parser.parse_args()

    try:
        measurer = PreciseGarmentMeasurer(
            ruler_length_cm=args.ruler_length,
            debug=args.debug
        )

        measurements = measurer.measure(args.image)

        print("✅ Measurement completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())