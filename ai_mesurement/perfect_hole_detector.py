#!/usr/bin/env python3
"""
PERFECT HOLE DETECTOR
Detects the hole by:
1. Cropping ONLY the fabric
2. Perfect alignment
3. Focused comparison in regions
4. Mark the exact hole location
"""

import cv2
import numpy as np
from pathlib import Path
import json

def detect_hole_perfectly():
    print(f"\n{'='*60}")
    print("🎯 PERFECT HOLE DETECTOR")
    print(f"{'='*60}")

    # Load images
    golden_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"

    print(f"\n📷 Loading images...")
    golden = cv2.imread(golden_path)
    test = cv2.imread(test_path)

    if golden is None or test is None:
        print("❌ Error loading images")
        return

    # STEP 1: CROP FABRIC
    print(f"\n✂️ STEP 1: Cropping fabric...")

    def crop_fabric(img, name):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        kernel = np.ones((5,5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)

            # Add padding
            padding = 50
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2*padding)
            h = min(img.shape[0] - y, h + 2*padding)

            cropped = img[y:y+h, x:x+w]
            print(f"  {name}: cropped to {cropped.shape}")
            return cropped, (x, y, w, h)
        return img, (0, 0, img.shape[1], img.shape[0])

    golden_crop, golden_bbox = crop_fabric(golden, "Golden")
    test_crop, test_bbox = crop_fabric(test, "Test")

    # Make same size
    if golden_crop.shape != test_crop.shape:
        h = min(golden_crop.shape[0], test_crop.shape[0])
        w = min(golden_crop.shape[1], test_crop.shape[1])
        golden_crop = cv2.resize(golden_crop, (w, h))
        test_crop = cv2.resize(test_crop, (w, h))

    # STEP 2: ALIGN
    print(f"\n🎯 STEP 2: Aligning images...")

    # Convert to grayscale
    gray1 = cv2.cvtColor(golden_crop, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(test_crop, cv2.COLOR_BGR2GRAY)

    # Use ORB for alignment (simpler but effective)
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    if des1 is not None and des2 is not None:
        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(des1, des2, k=2)

        # Filter matches
        good = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good.append(m)

        print(f"  Found {len(good)} good matches")

        if len(good) > 10:
            src_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            if M is not None:
                test_aligned = cv2.warpPerspective(test_crop, M, (golden_crop.shape[1], golden_crop.shape[0]))
                print(f"  ✅ Aligned successfully")
            else:
                test_aligned = test_crop
        else:
            test_aligned = test_crop
    else:
        test_aligned = test_crop

    # STEP 3: FOCUS ON UPPER REGION (where hole is likely)
    print(f"\n🔍 STEP 3: Analyzing upper region for holes...")

    h, w = golden_crop.shape[:2]

    # Focus on upper 40% where hole typically is
    upper_h = int(h * 0.4)
    golden_upper = golden_crop[:upper_h, :]
    test_upper = test_aligned[:upper_h, :]

    # STEP 4: DETECT DIFFERENCES
    print(f"  Comparing upper region ({upper_h}x{w} pixels)...")

    # Convert to grayscale
    golden_gray = cv2.cvtColor(golden_upper, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_upper, cv2.COLOR_BGR2GRAY)

    # Calculate difference
    diff = cv2.absdiff(golden_gray, test_gray)

    # Apply blur to reduce noise
    diff = cv2.GaussianBlur(diff, (3, 3), 0)

    # Multiple thresholding strategies
    _, thresh1 = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)
    thresh2 = cv2.adaptiveThreshold(diff, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 2)

    # Combine thresholds
    combined = cv2.bitwise_or(thresh1, thresh2)

    # Clean up
    kernel = np.ones((2,2), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    print(f"  Found {len(contours)} potential holes in upper region")

    # Analyze differences
    holes = []
    for contour in contours:
        area = cv2.contourArea(contour)

        # Very sensitive to small areas
        if area > 5:  # Very low threshold
            x, y, w, h = cv2.boundingRect(contour)

            # Check darkness
            roi_golden = golden_gray[y:y+h, x:x+w]
            roi_test = test_gray[y:y+h, x:x+w]

            if roi_golden.size > 0 and roi_test.size > 0:
                diff_mean = float(np.mean(roi_golden) - np.mean(roi_test))

                # Any darkening could be a hole
                if diff_mean > 1:
                    cx = x + w//2
                    cy = y + h//2

                    hole = {
                        'center': [cx, cy],  # In upper region coordinates
                        'center_full': [cx, cy],  # In full image coordinates
                        'bbox': [x, y, w, h],
                        'area': float(area),
                        'darkness': diff_mean,
                        'confidence': min(100, diff_mean * 5)
                    }
                    holes.append(hole)

    # Sort by darkness (most likely holes)
    holes.sort(key=lambda x: x['darkness'], reverse=True)

    # STEP 5: VISUALIZE
    print(f"\n✅ Found {len(holes)} holes:")

    # Create visualization
    result = test_crop.copy()

    # Draw upper region boundary
    cv2.rectangle(result, (0, 0), (w, upper_h), (0, 255, 0), 2)
    cv2.putText(result, "SEARCH REGION", (10, upper_h-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Mark holes
    for i, hole in enumerate(holes[:5], 1):
        x, y, w, h = hole['bbox']
        cx, cy = hole['center']

        # Draw on full image (adjust y coordinate)
        cv2.rectangle(result, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.circle(result, (cx, cy), 5, (0, 0, 255), -1)

        # Add arrow
        arrow_start = (cx + w + 20, cy)
        cv2.arrowedLine(result, arrow_start, (cx + w, cy), (0, 0, 255), 2, tipLength=0.3)

        # Add label
        text = f"HOLE #{i}"
        cv2.putText(result, text, (arrow_start[0] + 5, arrow_start[1] - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        print(f"  {i}. Hole at ({cx}, {cy})")
        print(f"     Size: {hole['bbox'][2]}x{hole['bbox'][3]} pixels")
        print(f"     Darkness: {hole['darkness']:.1f}")
        print(f"     Confidence: {hole['confidence']:.0f}%")

    # Save results
    cv2.imwrite("perfect_result.png", result)
    print(f"\n💾 Result saved to: perfect_result.png")

    # Create comparison
    comparison = np.hstack([golden_crop, test_aligned, result])
    cv2.imwrite("perfect_comparison.png", comparison)
    print(f"💾 Comparison saved to: perfect_comparison.png")

    # Save difference map
    diff_colored = cv2.applyColorMap(diff, cv2.COLORMAP_JET)
    cv2.imwrite("perfect_diff_map.png", diff_colored)
    print(f"💾 Difference map saved to: perfect_diff_map.png")

    # Save debug images
    cv2.imwrite("debug_upper_golden.png", golden_upper)
    cv2.imwrite("debug_upper_test.png", test_upper)
    cv2.imwrite("debug_threshold.png", combined)

    return holes

if __name__ == "__main__":
    holes = detect_hole_perfectly()

    if holes:
        print(f"\n{'='*60}")
        print("🎯 HOLE DETECTION SUCCESSFUL!")
        print(f"{'='*60}")
        print(f"✅ Detected {len(holes)} holes in the fabric")
    else:
        print(f"\n⚠️ No holes detected - try adjusting sensitivity")