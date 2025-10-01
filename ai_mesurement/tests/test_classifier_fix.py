#!/usr/bin/env python3
"""Test and fix classifier for trousers detection"""

import cv2
import numpy as np
from garment_segmentation_fast import FastGarmentSegmenter
from ruler_detection_smart import SmartRulerDetector

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

# Get mask
ruler_detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
ruler_info = ruler_detector.detect_ruler(image)

segmenter = FastGarmentSegmenter(debug=False)
mask, seg_info = segmenter.segment_garment(image, ruler_bbox=ruler_info['bbox'])

# Find contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contour = max(contours, key=cv2.contourArea)
x, y, w, h = cv2.boundingRect(contour)

print("Analyzing garment shape...")
print(f"Bounding box: x={x}, y={y}, w={w}, h={h}")
print(f"Aspect ratio: {w/h:.2f}")

# Check for leg split manually
bottom_third_y = y + int(h * 0.66)
print(f"\nChecking for leg split at y={bottom_third_y}...")

# Look for vertical gap in bottom region
bottom_region = mask[bottom_third_y:y+h, x:x+w]
print(f"Bottom region shape: {bottom_region.shape}")

if bottom_region.size > 0:
    # Check middle column for gap
    middle_x = w // 2
    if middle_x < bottom_region.shape[1]:
        middle_column = bottom_region[:, middle_x]

        # Visualize the middle column
        print(f"\nMiddle column analysis (x={middle_x}):")

        # Look for continuous black pixels (gap)
        gap_start = None
        gap_length = 0
        max_gap = 0

        for i, pixel in enumerate(middle_column):
            if pixel == 0:  # Black pixel (gap)
                if gap_start is None:
                    gap_start = i
                gap_length += 1
            else:  # White pixel (garment)
                if gap_length > max_gap:
                    max_gap = gap_length
                gap_start = None
                gap_length = 0

        if gap_length > max_gap:
            max_gap = gap_length

        print(f"Max gap length: {max_gap} pixels")
        print(f"Total column height: {len(middle_column)} pixels")
        print(f"Gap ratio: {max_gap / len(middle_column):.2%}")

        # Check for leg separation
        # For trousers, we should see the legs as separate regions
        print("\nChecking for separate leg regions...")

        # Get a slice near the bottom
        test_y = bottom_region.shape[0] // 2
        test_row = bottom_region[test_y, :]

        # Find connected regions in this row
        in_region = False
        regions = []
        start = 0

        for i, pixel in enumerate(test_row):
            if pixel > 0 and not in_region:
                # Start of region
                start = i
                in_region = True
            elif pixel == 0 and in_region:
                # End of region
                regions.append((start, i))
                in_region = False

        if in_region:
            regions.append((start, len(test_row)))

        print(f"Found {len(regions)} separate regions in test row")
        if regions:
            for i, (start, end) in enumerate(regions):
                print(f"  Region {i+1}: x={start} to x={end} (width: {end-start})")

        # If we have 2 regions of similar size, it's likely trousers
        if len(regions) == 2:
            width1 = regions[0][1] - regions[0][0]
            width2 = regions[1][1] - regions[1][0]
            ratio = min(width1, width2) / max(width1, width2)
            print(f"\nTwo leg regions detected!")
            print(f"  Left leg width: {width1} pixels")
            print(f"  Right leg width: {width2} pixels")
            print(f"  Similarity ratio: {ratio:.2f}")

            if ratio > 0.5:  # Legs are reasonably similar in size
                print("  ✅ This is likely TROUSERS!")

        # Save visualization
        viz = np.zeros((bottom_region.shape[0], bottom_region.shape[1], 3), dtype=np.uint8)
        viz[:, :, 0] = bottom_region
        viz[:, :, 1] = bottom_region
        viz[:, :, 2] = bottom_region

        # Draw middle line in red
        viz[:, middle_x, :] = [0, 0, 255]

        # Draw test row in green
        if test_y < viz.shape[0]:
            viz[test_y, :, :] = [0, 255, 0]

        cv2.imwrite('leg_split_debug.png', viz)
        print("\nVisualization saved to: leg_split_debug.png")