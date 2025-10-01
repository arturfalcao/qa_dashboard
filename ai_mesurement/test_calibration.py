#!/usr/bin/env python3
"""Test and compare calibration methods"""

import cv2
import numpy as np
from pathlib import Path

def manual_ruler_calibration(image_path: str, ruler_length_cm: float = 31.0):
    """
    Manually measure the ruler in the image to get accurate calibration
    This requires visual inspection of the ruler
    """

    print(f"\n{'='*60}")
    print(f"MANUAL CALIBRATION: {Path(image_path).name}")
    print('='*60)

    image = cv2.imread(image_path)
    if image is None:
        return None

    h, w = image.shape[:2]
    print(f"Image size: {w}x{h} pixels")

    # For ant.jpg - based on visual inspection, the ruler is approximately:
    # Located at x~900-950, extending vertically for about 1350 pixels
    if 'ant' in image_path.lower():
        ruler_length_px = 1350  # Approximate from visual inspection
        pixels_per_cm = ruler_length_px / ruler_length_cm
        print(f"✅ Manual calibration for ant.jpg:")
        print(f"   Ruler length: ~{ruler_length_px} pixels")
        print(f"   Scale: {pixels_per_cm:.2f} pixels/cm")
        return pixels_per_cm

    # For semburaco.jpg - need to visually inspect
    elif 'semburaco' in image_path.lower():
        # This would need manual inspection
        print("⚠️  Need manual inspection for semburaco.jpg")
        print("   Please measure the ruler pixels manually")
        return None

    return None

def test_measurement_with_scale(image_path: str, pixels_per_cm: float):
    """Test what measurements would be with a given scale"""

    print(f"\n📏 MEASUREMENT PREVIEW with {pixels_per_cm:.1f} px/cm:")

    # Example widths in pixels (hypothetical)
    test_widths = {
        'Chest (1000px)': 1000,
        'Chest (2000px)': 2000,
        'Chest (3000px)': 3000,
        'Chest (4000px)': 4000,
        'Waist (1500px)': 1500,
        'Waist (2500px)': 2500,
        'Hem (1200px)': 1200,
        'Hem (2000px)': 2000,
    }

    for name, width_px in test_widths.items():
        width_cm = width_px / pixels_per_cm
        print(f"   {name}: {width_cm:.1f} cm")

if __name__ == "__main__":
    # Test ant.jpg
    ant_scale = manual_ruler_calibration("../test_images_mesurements/ant.jpg")
    if ant_scale:
        test_measurement_with_scale("../test_images_mesurements/ant.jpg", ant_scale)

        print("\n🔍 COMPARISON WITH EXPECTED:")
        print("   Expected: Chest=110cm, Waist=70cm, Hem=57cm")
        print(f"   To get 110cm chest, need: {110 * ant_scale:.0f} pixels width")
        print(f"   To get 70cm waist, need: {70 * ant_scale:.0f} pixels width")
        print(f"   To get 57cm hem, need: {57 * ant_scale:.0f} pixels width")