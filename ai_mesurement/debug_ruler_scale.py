#!/usr/bin/env python3
"""Debug ruler detection and scale calculation"""

import cv2
import numpy as np
from pathlib import Path
from ruler_detection_smart import SmartRulerDetector
import matplotlib.pyplot as plt

def debug_ruler_detection(image_path: str, known_ruler_cm: float = 31.0):
    """Debug ruler detection for an image"""

    print(f"\n{'='*60}")
    print(f"DEBUGGING: {Path(image_path).name}")
    print(f"Known ruler length: {known_ruler_cm} cm")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    h, w = image.shape[:2]
    print(f"Image size: {w}x{h} pixels")

    # Initialize detector
    detector = SmartRulerDetector(known_length_cm=known_ruler_cm, debug=True)

    try:
        # Detect ruler
        result = detector.detect_ruler(image)

        print(f"\n✅ RULER DETECTED:")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   Pixels per cm: {result['pixels_per_cm']:.2f}")
        print(f"   Confidence: {result.get('confidence', 0):.1%}")
        print(f"   BBox: {result.get('bbox', 'None')}")

        # Calculate what this means for measurements
        print(f"\n📏 SCALE IMPLICATIONS:")
        print(f"   100 pixel width = {100 / result['pixels_per_cm']:.1f} cm")
        print(f"   500 pixel width = {500 / result['pixels_per_cm']:.1f} cm")
        print(f"   1000 pixel width = {1000 / result['pixels_per_cm']:.1f} cm")

        # If bbox exists, calculate actual ruler length in pixels
        if result.get('bbox'):
            x, y, w, h = result['bbox']
            ruler_length_px = max(w, h)  # Ruler could be horizontal or vertical
            print(f"\n📐 RULER VALIDATION:")
            print(f"   Detected ruler bbox: {w}x{h} pixels")
            print(f"   Ruler length in pixels: {ruler_length_px}")
            print(f"   Expected pixels (31cm * scale): {31 * result['pixels_per_cm']:.0f}")
            print(f"   Match ratio: {ruler_length_px / (31 * result['pixels_per_cm']):.2f}")

            # Visualize the detection
            vis = image.copy()
            cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(vis, f"Ruler: {result['pixels_per_cm']:.1f} px/cm",
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Save debug image
            debug_path = f"debug_ruler_{Path(image_path).stem}.png"
            cv2.imwrite(debug_path, vis)
            print(f"\n💾 Debug image saved: {debug_path}")

    except Exception as e:
        print(f"\n❌ RULER DETECTION FAILED: {e}")

        # Try to understand why
        print(f"\n🔍 ANALYZING FAILURE...")

        # Check for yellow/ruler-like colors
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Yellow range
        lower_yellow = np.array([15, 50, 50])
        upper_yellow = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        yellow_pixels = np.sum(yellow_mask > 0)
        yellow_percent = (yellow_pixels / (w * h)) * 100

        print(f"   Yellow pixels: {yellow_percent:.2f}% of image")

        # Check for straight lines
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)

        if lines is not None:
            print(f"   Straight lines detected: {len(lines)}")
        else:
            print(f"   No significant straight lines detected")

if __name__ == "__main__":
    # Test images
    test_images = [
        "../test_images_mesurements/ant.jpg",
        "../test_images_mesurements/prova.png",
    ]

    for img_path in test_images:
        if Path(img_path).exists():
            debug_ruler_detection(img_path)
        else:
            print(f"Skipping {img_path} - file not found")