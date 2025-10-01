#!/usr/bin/env python3
"""
Fast detection of the real hole from prova.png
Focus on dark spot detection
"""

import cv2
import numpy as np


def find_hole_fast():
    """Quick detection of real holes"""

    print("\n🎯 FAST HOLE DETECTION")
    print("="*60)

    # Load images
    ant = cv2.imread("../test_images_mesurements/ant.jpg")
    prova = cv2.imread("../test_images_mesurements/prova.png")

    if ant is None or prova is None:
        print("❌ Cannot load images")
        return

    # Analyze prova.png
    prova_gray = cv2.cvtColor(prova, cv2.COLOR_BGR2GRAY)

    # Get hole characteristics from prova.png
    # The hole is the dark center part
    h, w = prova_gray.shape
    center_region = prova_gray[h//3:2*h//3, w//3:2*w//3]
    hole_intensity = np.mean(center_region)
    print(f"Reference hole avg intensity: {hole_intensity:.1f}")

    # Search in ant.jpg for similar dark regions
    ant_gray = cv2.cvtColor(ant, cv2.COLOR_BGR2GRAY)

    # Downscale for faster processing
    scale = 0.5
    ant_small = cv2.resize(ant_gray, None, fx=scale, fy=scale)

    # Apply blur to reduce noise
    blurred = cv2.GaussianBlur(ant_small, (5, 5), 0)

    # Find dark spots (holes are darker than fabric)
    # Use adaptive threshold for better results
    threshold = 50  # Lower threshold to catch the hole
    _, dark_mask = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY_INV)

    # Clean up
    kernel = np.ones((3, 3), np.uint8)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)

    # Find contours
    contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter and sort by area
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)

        # Look for reasonable hole sizes
        if 20 < area < 2000:  # Lower minimum to catch smaller holes
            x, y, w, h = cv2.boundingRect(contour)

            # Check aspect ratio (holes are roughly circular)
            if h > 0:
                aspect = float(w) / h
                if 0.4 < aspect < 2.5:  # More lenient aspect ratio
                    # Scale back to original coordinates
                    orig_x = int(x / scale)
                    orig_y = int(y / scale)
                    orig_w = int(w / scale)
                    orig_h = int(h / scale)

                    # Skip if too close to image edges (likely not holes)
                    if orig_y < 100 or orig_y > ant_gray.shape[0] - 100:
                        continue
                    if orig_x < 50 or orig_x > ant_gray.shape[1] - 50:
                        continue

                    # Get average intensity
                    roi = ant_gray[orig_y:orig_y+orig_h, orig_x:orig_x+orig_w]
                    if roi.size > 0:
                        avg_intensity = np.mean(roi)

                        candidates.append({
                            'bbox': (orig_x, orig_y, orig_w, orig_h),
                            'area': area * (1/scale**2),
                            'intensity': avg_intensity,
                            'aspect': aspect
                        })

    # Sort by darkness (most likely to be holes)
    candidates.sort(key=lambda x: x['intensity'])

    print(f"\n✅ Found {len(candidates)} hole candidates")

    # Also search specifically in knee area (common hole location)
    print("\n🔍 Checking knee area specifically...")
    h, w = ant_gray.shape
    knee_y_start = int(h * 0.55)  # Knee area is around 55-75% down
    knee_y_end = int(h * 0.75)

    knee_candidates = [c for c in candidates
                       if knee_y_start < c['bbox'][1] < knee_y_end]

    if knee_candidates:
        print(f"   Found {len(knee_candidates)} candidates in knee area!")
    else:
        print("   No holes found in knee area")

    # Show top 10
    print("\nTop 10 darkest spots (most likely holes):")
    print("-" * 60)
    print(f"{'#':<3} {'Position':<20} {'Size':<15} {'Darkness':<10}")
    print("-" * 60)

    for i, c in enumerate(candidates[:10]):
        x, y, w, h = c['bbox']
        center = (x + w//2, y + h//2)
        print(f"{i+1:<3} ({center[0]:4}, {center[1]:4})     "
              f"{w:3}x{h:3} px     {c['intensity']:5.1f}")

    # Save visualization
    if candidates:
        result = ant.copy()

        # Draw top 10 candidates
        for i, c in enumerate(candidates[:10]):
            x, y, w, h = c['bbox']

            # Color code by rank (redder = more likely)
            color_intensity = int(255 - (i * 20))
            color = (0, color_intensity, 255)

            cv2.rectangle(result, (x, y), (x+w, y+h), color, 2)
            cv2.putText(result, f"#{i+1}", (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imwrite("holes_found_fast.png", result)
        print(f"\n📸 Result saved: holes_found_fast.png")

        # Also create a zoomed view of top candidate
        if candidates:
            top = candidates[0]
            x, y, w, h = top['bbox']

            # Add padding
            pad = 50
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(ant.shape[1], x + w + pad)
            y2 = min(ant.shape[0], y + h + pad)

            zoom = ant[y1:y2, x1:x2]
            cv2.imwrite("top_hole_zoom.png", zoom)
            print(f"📸 Top candidate zoom saved: top_hole_zoom.png")

    print("\n" + "="*60)


if __name__ == "__main__":
    find_hole_fast()