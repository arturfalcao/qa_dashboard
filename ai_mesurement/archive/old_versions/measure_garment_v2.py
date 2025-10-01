"""
Garment Measurement System V2 - Smart Detection
Integrates smart ruler detection + improved segmentation
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
from typing import Dict

from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_v2 import ImprovedGarmentSegmenter
from garment_measurement import GarmentMeasurer


class GarmentMeasurementSystemV2:
    """
    Complete garment measurement pipeline with smart detection
    """

    def __init__(self, ruler_length_cm: float = 31.0, debug: bool = False):
        self.ruler_length_cm = ruler_length_cm
        self.debug = debug

        # Initialize components
        self.ruler_detector = SmartRulerDetector(
            known_length_cm=ruler_length_cm,
            debug=debug
        )
        self.segmenter = ImprovedGarmentSegmenter(debug=debug)

    def measure_garment_from_image(self, image_path: str) -> Dict:
        """
        Complete measurement pipeline

        Args:
            image_path: Path to garment image with ruler

        Returns:
            Dictionary with measurements and metadata
        """

        print(f"\n{'='*60}")
        print(f"🔬 GARMENT MEASUREMENT SYSTEM V2")
        print(f"{'='*60}\n")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        print(f"📸 Image loaded: {image.shape[1]}x{image.shape[0]} pixels\n")

        # Step 1: Detect ruler and calibrate scale
        print("=" * 60)
        print("STEP 1: RULER DETECTION & CALIBRATION")
        print("=" * 60)

        ruler_info = self.ruler_detector.detect_ruler(image)

        pixels_per_cm = ruler_info['pixels_per_cm']
        ruler_bbox = ruler_info['bbox']

        print(f"\n   📏 Ruler detected:")
        print(f"      Method: {ruler_info['method']}")
        print(f"      Length: {ruler_info['length_pixels']:.0f} pixels = {self.ruler_length_cm} cm")
        print(f"      Scale: {pixels_per_cm:.2f} pixels/cm")
        print(f"      Orientation: {ruler_info['orientation']}")
        print(f"      Confidence: {ruler_info.get('confidence', 0):.2f}")

        # Step 2: Segment garment
        print(f"\n{'='*60}")
        print("STEP 2: GARMENT SEGMENTATION")
        print("=" * 60)

        garment_mask, garment_info = self.segmenter.segment_garment(
            image,
            ruler_bbox=ruler_bbox
        )

        # Step 3: Measure garment
        print(f"\n{'='*60}")
        print("STEP 3: GARMENT MEASUREMENT")
        print("=" * 60)

        measurer = GarmentMeasurer(pixels_per_cm=pixels_per_cm)
        measurements = measurer.measure_garment(
            image,
            garment_mask,
            garment_info
        )

        # Combine results
        result = {
            'image_path': image_path,
            'image_size': {'width': image.shape[1], 'height': image.shape[0]},
            'ruler': ruler_info,
            'garment': garment_info,
            'measurements': measurements
        }

        # Print final results
        self._print_results(result)

        # Save debug visualization if requested
        if self.debug:
            self._save_debug_visualization(image, garment_mask, measurements, result)

        return result

    def _print_results(self, result: Dict):
        """Print measurement results in a nice format"""

        print(f"\n{'='*60}")
        print("📊 FINAL MEASUREMENTS")
        print("=" * 60)

        m = result['measurements']

        print(f"\n   🎯 Dimensions:")
        print(f"      Height (extreme): {m['height_cm']:.2f} cm  ({m['height_cm'] * m['pixels_per_cm']:.0f} px)")
        print(f"      Width (extreme):  {m['width_cm']:.2f} cm  ({m['width_cm'] * m['pixels_per_cm']:.0f} px)")
        print(f"      Height (bbox):    {m['bbox_height_cm']:.2f} cm")
        print(f"      Width (bbox):     {m['bbox_width_cm']:.2f} cm)")
        print(f"      Area:             {m['area_cm2']:.2f} cm²")

        print(f"\n   📐 Measurement Points:")
        for name, point in m['extreme_points'].items():
            print(f"      {name.capitalize():12} ({point[0]:4d}, {point[1]:4d})")

        print(f"\n   📏 Scale:")
        print(f"      {result['ruler']['pixels_per_cm']:.2f} pixels/cm")

        print(f"\n   🎨 Garment Area:")
        print(f"      {result['garment']['area']:.0f} pixels²")

        print(f"\n{'='*60}\n")

    def _save_debug_visualization(self, image: np.ndarray, mask: np.ndarray,
                                   measurements: Dict, result: Dict):
        """Save comprehensive debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # 1. Original with ruler bbox
        ax = axes[0, 0]
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        ax.imshow(img_rgb)

        rx, ry, rw, rh = result['ruler']['bbox']
        rect = plt.Rectangle((rx, ry), rw, rh, fill=False,
                             edgecolor='lime', linewidth=3, label='Ruler')
        ax.add_patch(rect)

        ax.set_title('Original Image + Ruler Detection', fontsize=12, fontweight='bold')
        ax.legend()
        ax.axis('off')

        # 2. Segmentation mask
        ax = axes[0, 1]
        ax.imshow(mask, cmap='gray')
        ax.set_title('Garment Segmentation Mask', fontsize=12, fontweight='bold')
        ax.axis('off')

        # 3. Measurement overlay
        ax = axes[1, 0]
        overlay = image.copy()

        # Draw measurement lines
        pts = measurements['extreme_points']

        # Height (top to bottom)
        cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 0), 3)
        cv2.circle(overlay, pts['top'], 8, (0, 255, 0), -1)
        cv2.circle(overlay, pts['bottom'], 8, (0, 255, 0), -1)

        # Width (left to right)
        cv2.line(overlay, pts['left'], pts['right'], (255, 0, 0), 3)
        cv2.circle(overlay, pts['left'], 8, (255, 0, 0), -1)
        cv2.circle(overlay, pts['right'], 8, (255, 0, 0), -1)

        # Diagonal
        cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 255), 2)

        # Labels
        mid_y = (pts['top'][1] + pts['bottom'][1]) // 2
        mid_x = (pts['left'][0] + pts['right'][0]) // 2

        cv2.putText(overlay, f"{measurements['height_cm']:.1f}cm",
                   (pts['top'][0] + 20, mid_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.putText(overlay, f"{measurements['width_cm']:.1f}cm",
                   (mid_x, pts['left'][1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        ax.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax.set_title('Measurement Points', fontsize=12, fontweight='bold')
        ax.axis('off')

        # 4. Masked garment
        ax = axes[1, 1]
        masked = cv2.bitwise_and(image, image, mask=mask)
        ax.imshow(cv2.cvtColor(masked, cv2.COLOR_BGR2RGB))
        ax.set_title('Isolated Garment', fontsize=12, fontweight='bold')
        ax.axis('off')

        plt.suptitle(f'Garment Measurement Analysis\nHeight: {measurements["height_cm"]:.2f}cm | Width: {measurements["width_cm"]:.2f}cm | Scale: {result["ruler"]["pixels_per_cm"]:.2f}px/cm',
                    fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig('debug_measurements.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✅ Debug visualization saved: debug_measurements.png")


def main():
    parser = argparse.ArgumentParser(
        description='AI-Assisted Garment Measurement System V2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Measure garment with debug output
  python measure_garment_v2.py --image ../test_images_mesurements/anti.jpg --debug

  # Measure with custom ruler length
  python measure_garment_v2.py --image garment.jpg --ruler-length 30.0
        """
    )

    parser.add_argument('--image', '-i', required=True,
                       help='Path to garment image')
    parser.add_argument('--ruler-length', '-r', type=float, default=31.0,
                       help='Known ruler length in cm (default: 31.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug visualizations')

    args = parser.parse_args()

    # Validate image exists
    if not Path(args.image).exists():
        print(f"❌ Error: Image not found: {args.image}")
        return 1

    try:
        # Run measurement
        system = GarmentMeasurementSystemV2(
            ruler_length_cm=args.ruler_length,
            debug=args.debug
        )

        result = system.measure_garment_from_image(args.image)

        print("✅ Measurement completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Error during measurement: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
