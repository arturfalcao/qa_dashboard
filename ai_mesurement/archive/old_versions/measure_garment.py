#!/usr/bin/env python3
"""
AI-Assisted Garment Measurement System

Automatically measures garment dimensions from photos with ruler reference
"""

import cv2
import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from garment_segmentation import GarmentSegmenter
from ruler_detection import RulerDetector
from garment_measurement import GarmentMeasurer


class GarmentMeasurementSystem:
    """Complete system for AI-assisted garment measurement"""

    def __init__(
        self,
        ruler_length_cm: float = 31.0,
        ruler_color: str = 'green',
        debug: bool = False
    ):
        """
        Args:
            ruler_length_cm: Known length of ruler in centimeters
            ruler_color: Color of the ruler ('green', 'yellow', 'auto')
            debug: Enable debug visualizations and verbose output
        """
        self.ruler_length_cm = ruler_length_cm
        self.ruler_color = ruler_color
        self.debug = debug

        print(f"🔬 AI Garment Measurement System Initialized")
        print(f"   Ruler: {ruler_length_cm} cm ({ruler_color})")
        print(f"   Debug: {'ON' if debug else 'OFF'}")

    def measure_garment_from_image(self, image_path: str) -> Dict:
        """
        Complete measurement pipeline

        Args:
            image_path: Path to image file

        Returns:
            Dictionary with complete measurements and metadata
        """
        print(f"\n📸 Processing image: {image_path}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        print(f"   Image size: {image.shape[1]}x{image.shape[0]} pixels")

        # Step 1: Segment background and isolate foreground
        print(f"\n🎯 Step 1: Segmenting background...")
        segmenter = GarmentSegmenter(debug=self.debug)
        fg_mask, segmented = segmenter.segment_by_color(image)

        # Step 2: Detect ruler and calibrate scale
        print(f"\n📏 Step 2: Detecting ruler and calibrating scale...")
        ruler_detector = RulerDetector(
            known_length_cm=self.ruler_length_cm,
            debug=self.debug
        )

        try:
            ruler_info = ruler_detector.detect_ruler(
                image,
                mask=fg_mask,
                color_range=self.ruler_color
            )
            pixels_per_cm = ruler_info['pixels_per_cm']
            print(f"   ✅ Ruler detected: {ruler_info['length_pixels']:.0f}px = {self.ruler_length_cm}cm")
            print(f"   ✅ Scale calibrated: {pixels_per_cm:.2f} pixels/cm")
        except Exception as e:
            print(f"   ⚠️  Ruler auto-detection failed: {e}")
            print(f"   ℹ️  You may need to manually calibrate or adjust ruler_color parameter")
            raise

        # Step 3: Isolate garment (exclude ruler and hands)
        print(f"\n👕 Step 3: Isolating garment...")
        garment_mask, garment_info = segmenter.isolate_garment(image, fg_mask)
        print(f"   ✅ Garment isolated: {garment_info['area']:.0f} pixels²")

        # Step 4: Measure garment dimensions
        print(f"\n📐 Step 4: Measuring garment...")
        measurer = GarmentMeasurer(pixels_per_cm=pixels_per_cm, debug=self.debug)
        measurements = measurer.measure_garment(image, garment_mask, garment_info)

        print(f"   ✅ Measurements complete!")

        # Compile results
        results = {
            'image_path': image_path,
            'image_size': {
                'width_px': image.shape[1],
                'height_px': image.shape[0]
            },
            'calibration': {
                'ruler_length_cm': self.ruler_length_cm,
                'ruler_length_px': ruler_info['length_pixels'],
                'pixels_per_cm': pixels_per_cm,
                'ruler_orientation': ruler_info['orientation']
            },
            'measurements': {
                'height_cm': round(measurements['height_cm'], 2),
                'width_cm': round(measurements['width_cm'], 2),
                'bbox_height_cm': round(measurements['bbox_height_cm'], 2),
                'bbox_width_cm': round(measurements['bbox_width_cm'], 2),
                'area_cm2': round(measurements['area_cm2'], 2)
            },
            'garment': {
                'area_px': garment_info['area'],
                'bbox_px': garment_info['bbox']
            }
        }

        return results

    def save_results(self, results: Dict, output_path: str):
        """Save measurement results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_path}")

    def print_results(self, results: Dict):
        """Print formatted measurement results"""
        print(f"\n" + "="*60)
        print(f"📊 MEASUREMENT RESULTS")
        print(f"="*60)

        print(f"\n📸 Image: {results['image_path']}")
        print(f"   Size: {results['image_size']['width_px']} x {results['image_size']['height_px']} px")

        print(f"\n📏 Calibration:")
        cal = results['calibration']
        print(f"   Ruler: {cal['ruler_length_px']:.0f} px = {cal['ruler_length_cm']} cm")
        print(f"   Scale: {cal['pixels_per_cm']:.2f} px/cm")
        print(f"   Orientation: {cal['ruler_orientation']}")

        print(f"\n👕 Garment Measurements:")
        m = results['measurements']
        print(f"   Height: {m['height_cm']} cm")
        print(f"   Width:  {m['width_cm']} cm")
        print(f"   Area:   {m['area_cm2']} cm²")

        print(f"\n📦 Bounding Box:")
        print(f"   Height: {m['bbox_height_cm']} cm")
        print(f"   Width:  {m['bbox_width_cm']} cm")

        print(f"\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description='AI-Assisted Garment Measurement System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Measure garment with default 31cm ruler
  python measure_garment.py --image photo.jpg

  # Measure with custom ruler length
  python measure_garment.py --image photo.jpg --ruler-length 30

  # Enable debug mode (saves intermediate visualizations)
  python measure_garment.py --image photo.jpg --debug

  # Auto-detect ruler color
  python measure_garment.py --image photo.jpg --ruler-color auto

  # Save results to JSON
  python measure_garment.py --image photo.jpg --output results.json
        """
    )

    parser.add_argument(
        '--image',
        type=str,
        required=True,
        help='Path to garment image with ruler'
    )

    parser.add_argument(
        '--ruler-length',
        type=float,
        default=31.0,
        help='Length of the ruler in centimeters (default: 31.0)'
    )

    parser.add_argument(
        '--ruler-color',
        type=str,
        choices=['green', 'yellow', 'auto'],
        default='green',
        help='Color of the ruler (default: green)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (saves intermediate visualizations)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file path for results'
    )

    args = parser.parse_args()

    # Validate image exists
    if not Path(args.image).exists():
        print(f"❌ Error: Image file not found: {args.image}")
        sys.exit(1)

    try:
        # Initialize system
        system = GarmentMeasurementSystem(
            ruler_length_cm=args.ruler_length,
            ruler_color=args.ruler_color,
            debug=args.debug
        )

        # Measure garment
        results = system.measure_garment_from_image(args.image)

        # Print results
        system.print_results(results)

        # Save to JSON if requested
        if args.output:
            system.save_results(results, args.output)

        print(f"\n✅ Measurement complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
