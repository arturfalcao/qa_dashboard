#!/usr/bin/env python3
"""Find the actual ruler in the image"""

import cv2
import numpy as np
from pathlib import Path

def find_wooden_ruler(image_path: str):
    """Find the wooden ruler in the image and calculate correct scale"""

    print(f"\n{'='*60}")
    print(f"FINDING THE ACTUAL RULER")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return

    h, w = image.shape[:2]
    print(f"Image size: {w}x{h} pixels")

    # Convert to HSV for color detection
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Wood/brown color ranges for wooden ruler
    lower_brown1 = np.array([10, 30, 30])
    upper_brown1 = np.array([25, 200, 200])

    lower_brown2 = np.array([5, 50, 50])
    upper_brown2 = np.array([15, 255, 200])

    # Create masks for brown/wood colors
    mask1 = cv2.inRange(hsv, lower_brown1, upper_brown1)
    mask2 = cv2.inRange(hsv, lower_brown2, upper_brown2)
    wood_mask = cv2.bitwise_or(mask1, mask2)

    # Also check for yellowish wood
    lower_yellow = np.array([15, 30, 100])
    upper_yellow = np.array([35, 150, 255])
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Combine masks
    combined_mask = cv2.bitwise_or(wood_mask, yellow_mask)

    # Apply morphology to clean up
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)

    # Find contours
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    print(f"\n🔍 Found {len(contours)} potential ruler regions")

    # Look for elongated rectangular objects (rulers are long and thin)
    ruler_candidates = []

    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < 500:  # Too small
            continue

        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Calculate aspect ratio
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0

        # Rulers are very elongated (aspect ratio > 10)
        if aspect_ratio > 8:
            # Calculate rectangularity (how rectangular vs irregular)
            rect_area = w * h
            rectangularity = area / rect_area if rect_area > 0 else 0

            print(f"   Candidate {i}: {w}x{h} pixels, aspect ratio: {aspect_ratio:.1f}, rectangularity: {rectangularity:.2f}")

            if rectangularity > 0.5:  # Should be mostly rectangular
                ruler_candidates.append({
                    'bbox': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'rectangularity': rectangularity,
                    'length': max(w, h),
                    'width': min(w, h),
                    'orientation': 'horizontal' if w > h else 'vertical'
                })

    if not ruler_candidates:
        print("❌ No ruler-like objects found!")

        # Save debug mask
        cv2.imwrite("debug_ruler_mask.png", combined_mask)
        print("💾 Saved debug_ruler_mask.png for inspection")
        return None

    # Sort by aspect ratio (most ruler-like)
    ruler_candidates.sort(key=lambda x: x['aspect_ratio'], reverse=True)

    # Take the best candidate
    best_ruler = ruler_candidates[0]
    x, y, w, h = best_ruler['bbox']

    print(f"\n✅ FOUND RULER:")
    print(f"   Position: ({x}, {y})")
    print(f"   Size: {w}x{h} pixels")
    print(f"   Orientation: {best_ruler['orientation']}")
    print(f"   Length: {best_ruler['length']} pixels")
    print(f"   Width: {best_ruler['width']} pixels")

    # Calculate pixels per cm
    ruler_length_pixels = best_ruler['length']
    pixels_per_cm = ruler_length_pixels / 31.0

    print(f"\n📏 SCALE CALCULATION:")
    print(f"   Ruler length: {ruler_length_pixels} pixels")
    print(f"   Known length: 31 cm")
    print(f"   Scale: {pixels_per_cm:.2f} pixels/cm")

    # Draw visualization
    vis = image.copy()
    cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 3)
    cv2.putText(vis, f"RULER: 31cm = {ruler_length_pixels}px",
                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(vis, f"Scale: {pixels_per_cm:.2f} px/cm",
                (x, y+h+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Draw length line
    if best_ruler['orientation'] == 'horizontal':
        cv2.line(vis, (x, y+h//2), (x+w, y+h//2), (255, 0, 0), 2)
        cv2.putText(vis, "31 cm", (x+w//2-30, y+h//2-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
    else:
        cv2.line(vis, (x+w//2, y), (x+w//2, y+h), (255, 0, 0), 2)
        cv2.putText(vis, "31 cm", (x+w//2+10, y+h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    cv2.imwrite("ruler_detection_correct.png", vis)
    print(f"💾 Saved ruler_detection_correct.png")

    # Save mask for debugging
    cv2.imwrite("ruler_mask_debug.png", combined_mask)

    return pixels_per_cm

def test_measurements_with_scale(image_path: str, pixels_per_cm: float):
    """Test measurements with the correct scale"""

    print(f"\n{'='*60}")
    print(f"TESTING MEASUREMENTS WITH CORRECT SCALE")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return

    # Simple garment segmentation (just for testing)
    # In real use, this would use your segmentation
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to find dark garment on light background
    _, mask = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)

    # Clean up mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Find garment contour
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return

    # Get largest contour (garment)
    garment = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(garment)

    print(f"\nGarment bounding box: {w}x{h} pixels")
    print(f"In cm: {w/pixels_per_cm:.1f} x {h/pixels_per_cm:.1f} cm")

    # Measure at different heights
    print(f"\n📐 MEASUREMENTS:")

    # Length (height of garment)
    length_cm = h / pixels_per_cm
    print(f"   Length: {length_cm:.1f} cm")

    # Chest (widest point in upper half)
    chest_region = mask[y+int(h*0.2):y+int(h*0.45), x:x+w]
    chest_widths = []
    for row in chest_region:
        nonzero = np.nonzero(row)[0]
        if len(nonzero) > 1:
            width = nonzero[-1] - nonzero[0]
            chest_widths.append(width)

    if chest_widths:
        max_chest_px = max(chest_widths)
        chest_cm = max_chest_px / pixels_per_cm
        print(f"   Chest width: {chest_cm:.1f} cm")

    # Waist (narrowest in middle)
    waist_region = mask[y+int(h*0.4):y+int(h*0.6), x:x+w]
    waist_widths = []
    for row in waist_region:
        nonzero = np.nonzero(row)[0]
        if len(nonzero) > 1:
            width = nonzero[-1] - nonzero[0]
            waist_widths.append(width)

    if waist_widths:
        min_waist_px = min(waist_widths)
        waist_cm = min_waist_px / pixels_per_cm
        print(f"   Waist width: {waist_cm:.1f} cm")

    # Hem (bottom)
    hem_region = mask[y+int(h*0.9):y+h, x:x+w]
    hem_widths = []
    for row in hem_region:
        nonzero = np.nonzero(row)[0]
        if len(nonzero) > 1:
            width = nonzero[-1] - nonzero[0]
            hem_widths.append(width)

    if hem_widths:
        max_hem_px = max(hem_widths)
        hem_cm = max_hem_px / pixels_per_cm
        print(f"   Hem width: {hem_cm:.1f} cm")

if __name__ == "__main__":
    # Find the ruler
    pixels_per_cm = find_wooden_ruler("../test_images_mesurements/ant.jpg")

    if pixels_per_cm:
        # Test measurements with this scale
        test_measurements_with_scale("../test_images_mesurements/ant.jpg", pixels_per_cm)

        print(f"\n{'='*60}")
        print(f"COMPARISON WITH EXPECTED:")
        print(f"   Expected: Length=65.5cm, Chest=110cm, Waist=52cm, Hem=57cm")
        print(f"   To get these measurements, the ruler would need to be:")
        print(f"   For 52cm waist with 1780px width: {1780/52:.1f} pixels/cm")
        print(f"   For 65.5cm length with 2296px height: {2296/65.5:.1f} pixels/cm")
        print(f"   For 110cm chest with 2726px width: {2726/110:.1f} pixels/cm")