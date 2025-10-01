#!/usr/bin/env python3
"""Debug actual pixel measurements being detected"""

import cv2
import numpy as np
from pathlib import Path
from garment_segmentation_fast import FastGarmentSegmenter
from ruler_detection_smart import SmartRulerDetector

def debug_measurements(image_path: str):
    """Debug what's actually being measured in pixels"""

    print(f"\n{'='*60}")
    print(f"DEBUG MEASUREMENTS: {Path(image_path).name}")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return

    h, w = image.shape[:2]
    print(f"Image size: {w}x{h} pixels")

    # Detect ruler
    detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
    try:
        ruler_info = detector.detect_ruler(image)
        pixels_per_cm = ruler_info['pixels_per_cm']
        print(f"✅ Ruler scale: {pixels_per_cm:.2f} pixels/cm")
    except:
        print("❌ Ruler detection failed")
        return

    # Segment garment
    segmenter = FastGarmentSegmenter(debug=False)
    result = segmenter.segment_garment(image, ruler_bbox=ruler_info.get('bbox'))

    # segment_garment returns (mask, bbox) tuple
    if result is not None and len(result) == 2:
        mask, _ = result
        print(f"✅ Garment segmented")

        # Find bounding box
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)

            print(f"\n📐 GARMENT BOUNDING BOX:")
            print(f"   Position: ({x}, {y})")
            print(f"   Size: {w}x{h} pixels")
            print(f"   In cm: {w/pixels_per_cm:.1f} x {h/pixels_per_cm:.1f} cm")

            # Measure at different heights
            print(f"\n📏 WIDTH MEASUREMENTS AT DIFFERENT HEIGHTS:")

            # Chest region (20-45%)
            chest_start = y + int(h * 0.20)
            chest_end = y + int(h * 0.45)
            chest_widths = []
            for scan_y in range(chest_start, chest_end, 10):
                if scan_y < mask.shape[0]:
                    row = mask[scan_y, x:x+w]
                    nonzero = np.nonzero(row)[0]
                    if len(nonzero) > 0:
                        width_px = nonzero[-1] - nonzero[0]
                        chest_widths.append(width_px)

            if chest_widths:
                max_chest = max(chest_widths)
                avg_chest = np.mean(chest_widths)
                print(f"   Chest region (20-45%):")
                print(f"      Max width: {max_chest:.0f} px = {max_chest/pixels_per_cm:.1f} cm")
                print(f"      Avg width: {avg_chest:.0f} px = {avg_chest/pixels_per_cm:.1f} cm")

            # Waist region (40-60%)
            waist_start = y + int(h * 0.40)
            waist_end = y + int(h * 0.60)
            waist_widths = []
            for scan_y in range(waist_start, waist_end, 10):
                if scan_y < mask.shape[0]:
                    row = mask[scan_y, x:x+w]
                    nonzero = np.nonzero(row)[0]
                    if len(nonzero) > 0:
                        width_px = nonzero[-1] - nonzero[0]
                        waist_widths.append(width_px)

            if waist_widths:
                min_waist = min(waist_widths)
                avg_waist = np.mean(waist_widths)
                print(f"   Waist region (40-60%):")
                print(f"      Min width: {min_waist:.0f} px = {min_waist/pixels_per_cm:.1f} cm")
                print(f"      Avg width: {avg_waist:.0f} px = {avg_waist/pixels_per_cm:.1f} cm")

            # Hem region (93-100%)
            hem_start = y + int(h * 0.93)
            hem_end = y + h
            hem_widths = []
            for scan_y in range(hem_start, min(hem_end, mask.shape[0]), 2):
                row = mask[scan_y, x:x+w]
                nonzero = np.nonzero(row)[0]
                if len(nonzero) > 0:
                    width_px = nonzero[-1] - nonzero[0]
                    hem_widths.append(width_px)

            if hem_widths:
                max_hem = max(hem_widths)
                avg_hem = np.mean(hem_widths)
                print(f"   Hem region (93-100%):")
                print(f"      Max width: {max_hem:.0f} px = {max_hem/pixels_per_cm:.1f} cm")
                print(f"      Avg width: {avg_hem:.0f} px = {avg_hem/pixels_per_cm:.1f} cm")

            # Create visualization
            vis = image.copy()
            cv2.drawContours(vis, [largest], -1, (0, 255, 0), 2)

            # Draw measurement lines
            if chest_widths:
                chest_y = chest_start + len(chest_widths) // 2 * 10
                cv2.line(vis, (x, chest_y), (x+w, chest_y), (255, 0, 0), 2)
                cv2.putText(vis, f"Chest: {max_chest/pixels_per_cm:.1f}cm",
                           (x+w+10, chest_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            if waist_widths:
                waist_y = waist_start + len(waist_widths) // 2 * 10
                cv2.line(vis, (x, waist_y), (x+w, waist_y), (0, 255, 255), 2)
                cv2.putText(vis, f"Waist: {min_waist/pixels_per_cm:.1f}cm",
                           (x+w+10, waist_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            if hem_widths:
                hem_y = hem_start + len(hem_widths) // 2 * 2
                cv2.line(vis, (x, hem_y), (x+w, hem_y), (255, 0, 255), 2)
                cv2.putText(vis, f"Hem: {max_hem/pixels_per_cm:.1f}cm",
                           (x+w+10, hem_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

            # Save debug image
            debug_path = f"debug_measurements_{Path(image_path).stem}.png"
            cv2.imwrite(debug_path, vis)
            print(f"\n💾 Debug visualization saved: {debug_path}")

if __name__ == "__main__":
    debug_measurements("../test_images_mesurements/ant.jpg")