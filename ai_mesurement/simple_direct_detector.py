#!/usr/bin/env python3
"""
SIMPLE AND DIRECT HOLE DETECTOR
1. Crop fabric only
2. Align perfectly
3. Compare directly
4. Find holes
"""

import cv2
import numpy as np
from pathlib import Path
import json

class SimpleDirectDetector:
    def __init__(self):
        self.debug = True

    def crop_fabric_only(self, img):
        """
        CROP APENAS O TECIDO - remove tudo o resto
        """
        print(f"  📐 Cropping fabric from {img.shape}")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Use threshold to separate garment from white background
        # Background is typically very light (> 200)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Clean up with morphology
        kernel = np.ones((5,5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print(f"    ⚠️ No contours found, returning original")
            return img, (0, 0, img.shape[1], img.shape[0])

        # Find the largest contour (the garment)
        largest = max(contours, key=cv2.contourArea)

        # Check if contour is significant (at least 10% of image)
        image_area = img.shape[0] * img.shape[1]
        contour_area = cv2.contourArea(largest)

        if contour_area < image_area * 0.1:
            print(f"    ⚠️ Contour too small ({contour_area} < {image_area*0.1}), returning original")
            return img, (0, 0, img.shape[1], img.shape[0])

        # Get bounding box
        x, y, w, h = cv2.boundingRect(largest)

        # Add small padding
        padding = 50
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(img.shape[1] - x, w + 2*padding)
        h = min(img.shape[0] - y, h + 2*padding)

        # CROP the fabric
        cropped = img[y:y+h, x:x+w]

        print(f"    ✅ Cropped to {cropped.shape} at ({x},{y}) (kept {100*(cropped.size/img.size):.1f}% of image)")

        return cropped, (x, y, w, h)

    def align_images_perfectly(self, img1, img2):
        """
        Alinha as duas imagens PERFEITAMENTE usando SIFT
        """
        print(f"  🎯 Aligning images...")

        # Ensure same size
        if img1.shape != img2.shape:
            # Resize img2 to match img1
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))

        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Use SIFT for best feature detection
        sift = cv2.SIFT_create(nfeatures=10000)  # Many features for perfect alignment

        # Detect keypoints and descriptors
        kp1, des1 = sift.detectAndCompute(gray1, None)
        kp2, des2 = sift.detectAndCompute(gray2, None)

        print(f"    Found {len(kp1)} and {len(kp2)} keypoints")

        if des1 is None or des2 is None or len(des1) < 4 or len(des2) < 4:
            print("    ⚠️ Not enough features, returning original")
            return img2

        # Use FLANN matcher for best matches
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=100)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        # Find matches
        matches = flann.knnMatch(des1, des2, k=2)

        # Filter good matches using Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        print(f"    Found {len(good_matches)} good matches")

        if len(good_matches) < 4:
            print("    ⚠️ Not enough good matches")
            return img2

        # Get matching points
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Find homography
        M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

        if M is None:
            print("    ⚠️ Could not find homography")
            return img2

        # Warp img2 to align with img1
        aligned = cv2.warpPerspective(img2, M, (img1.shape[1], img1.shape[0]))

        print(f"    ✅ Aligned successfully")
        return aligned

    def compare_and_find_holes(self, golden, test):
        """
        Compara diretamente pixel a pixel e encontra buracos
        """
        print(f"  🔍 Comparing images pixel by pixel...")

        # Multiple comparison methods
        differences = []

        # 1. Direct BGR difference
        diff_bgr = cv2.absdiff(golden, test)
        diff_gray = cv2.cvtColor(diff_bgr, cv2.COLOR_BGR2GRAY)
        differences.append(diff_gray)

        # 2. Convert to LAB for perceptual difference
        golden_lab = cv2.cvtColor(golden, cv2.COLOR_BGR2Lab)
        test_lab = cv2.cvtColor(test, cv2.COLOR_BGR2Lab)
        diff_lab = cv2.absdiff(golden_lab, test_lab)
        diff_lab_gray = cv2.cvtColor(diff_lab, cv2.COLOR_Lab2BGR)
        diff_lab_gray = cv2.cvtColor(diff_lab_gray, cv2.COLOR_BGR2GRAY)
        differences.append(diff_lab_gray)

        # Combine all differences
        combined_diff = np.zeros_like(diff_gray, dtype=np.float32)
        for diff in differences:
            combined_diff += diff.astype(np.float32)
        combined_diff = (combined_diff / len(differences)).astype(np.uint8)

        # Apply Gaussian blur to reduce noise
        combined_diff = cv2.GaussianBlur(combined_diff, (5, 5), 0)

        # Multiple threshold levels for better detection
        thresholds = []

        # Low threshold for subtle differences
        _, thresh1 = cv2.threshold(combined_diff, 15, 255, cv2.THRESH_BINARY)
        thresholds.append(thresh1)

        # Adaptive threshold for local variations
        thresh2 = cv2.adaptiveThreshold(combined_diff, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        thresholds.append(thresh2)

        # Otsu's threshold
        _, thresh3 = cv2.threshold(combined_diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresholds.append(thresh3)

        # Combine all thresholds
        binary = np.zeros_like(combined_diff)
        for thresh in thresholds:
            binary = cv2.bitwise_or(binary, thresh)

        # Clean up with morphology - smaller kernel to preserve small holes
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours (potential holes)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        print(f"    Found {len(contours)} differences")

        # Analyze each difference
        holes = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # Lower minimum area to catch small holes
            if 10 < area < 50000:
                x, y, w, h = cv2.boundingRect(contour)

                # Get center
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w//2, y + h//2

                # Check if it's darker (likely a hole)
                golden_roi = cv2.cvtColor(golden[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
                test_roi = cv2.cvtColor(test[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)

                if golden_roi.size > 0 and test_roi.size > 0:
                    brightness_diff = float(np.mean(golden_roi) - np.mean(test_roi))

                    # If test is darker, it's likely a hole (lower threshold)
                    if brightness_diff > 2:
                        hole = {
                            'center': [cx, cy],
                            'bbox': [x, y, w, h],
                            'area': float(area),
                            'brightness_diff': brightness_diff,
                            'confidence': min(100, brightness_diff * 2)
                        }
                        holes.append(hole)

        # Sort by confidence
        holes.sort(key=lambda x: x['confidence'], reverse=True)

        return holes, binary

    def detect(self, golden_path, test_path, output_path=None):
        """
        MAIN DETECTION - Simple and Direct
        """
        print(f"\n{'='*60}")
        print("SIMPLE DIRECT HOLE DETECTOR")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        golden = cv2.imread(str(golden_path))
        test = cv2.imread(str(test_path))

        if golden is None or test is None:
            print("❌ Error loading images")
            return None

        # STEP 1: CROP FABRIC ONLY
        print(f"\n✂️ STEP 1: Cropping fabric only...")
        golden_cropped, golden_bbox = self.crop_fabric_only(golden)
        test_cropped, test_bbox = self.crop_fabric_only(test)

        # Save cropped for debug
        if self.debug:
            cv2.imwrite("debug_golden_cropped.png", golden_cropped)
            cv2.imwrite("debug_test_cropped.png", test_cropped)

        # STEP 2: ALIGN PERFECTLY
        print(f"\n🎯 STEP 2: Aligning cropped images...")
        test_aligned = self.align_images_perfectly(golden_cropped, test_cropped)

        # Save aligned for debug
        if self.debug:
            cv2.imwrite("debug_test_aligned.png", test_aligned)

        # STEP 3: COMPARE DIRECTLY
        print(f"\n🔍 STEP 3: Comparing pixel by pixel...")
        holes, diff_mask = self.compare_and_find_holes(golden_cropped, test_aligned)

        # Save diff for debug
        if self.debug:
            cv2.imwrite("debug_diff_mask.png", diff_mask)

        print(f"\n✅ Found {len(holes)} potential holes")

        # Show results
        for i, hole in enumerate(holes[:5], 1):
            print(f"\n  {i}. HOLE at ({hole['center'][0]}, {hole['center'][1]})")
            print(f"     Size: {hole['bbox'][2]}x{hole['bbox'][3]} pixels")
            print(f"     Area: {hole['area']:.0f} pixels²")
            print(f"     Darker by: {hole['brightness_diff']:.1f} units")
            print(f"     Confidence: {hole['confidence']:.0f}%")

        # Create visualization
        if output_path:
            self.visualize(golden_cropped, test_cropped, test_aligned, holes, diff_mask, output_path)

        return {
            'holes_found': len(holes),
            'holes': holes[:10],
            'golden_crop': golden_bbox,
            'test_crop': test_bbox
        }

    def visualize(self, golden, test, aligned, holes, diff_mask, output_path):
        """
        Create simple visualization
        """
        # Mark holes on aligned image
        marked = aligned.copy()

        for i, hole in enumerate(holes[:10]):
            x, y, w, h = hole['bbox']
            cx, cy = hole['center']

            # Draw rectangle
            cv2.rectangle(marked, (x, y), (x+w, y+h), (0, 0, 255), 2)

            # Draw center
            cv2.circle(marked, (cx, cy), 5, (0, 0, 255), -1)

            # Add text
            text = f"#{i+1}"
            cv2.putText(marked, text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Create comparison grid
        h, w = golden.shape[:2]

        # Make all images same size
        if test.shape != golden.shape:
            test = cv2.resize(test, (w, h))
        if aligned.shape != golden.shape:
            aligned = cv2.resize(aligned, (w, h))
        if marked.shape != golden.shape:
            marked = cv2.resize(marked, (w, h))

        # Create 2x2 grid
        grid = np.zeros((h*2, w*2, 3), dtype=np.uint8)
        grid[:h, :w] = golden  # Golden cropped
        grid[:h, w:] = test    # Test cropped
        grid[h:, :w] = aligned  # Test aligned
        grid[h:, w:] = marked   # Marked holes

        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(grid, "GOLDEN (CROPPED)", (10, 30), font, 0.8, (0, 255, 0), 2)
        cv2.putText(grid, "TEST (CROPPED)", (w+10, 30), font, 0.8, (0, 255, 255), 2)
        cv2.putText(grid, "TEST (ALIGNED)", (10, h+30), font, 0.8, (255, 255, 0), 2)
        cv2.putText(grid, f"HOLES: {len(holes)}", (w+10, h+30), font, 0.8, (0, 0, 255), 2)

        # Save
        cv2.imwrite(str(output_path), grid)
        print(f"\n💾 Result saved to: {output_path}")

        # Save marked only
        marked_path = str(output_path).replace('.png', '_marked.png')
        cv2.imwrite(marked_path, marked)
        print(f"💾 Marked image saved to: {marked_path}")


def main():
    """Run the simple direct detector"""
    detector = SimpleDirectDetector()

    golden = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
    output = "/home/celso/projects/qa_dashboard/ai_mesurement/simple_direct_result.png"

    result = detector.detect(golden, test, output)

    if result and result['holes_found'] > 0:
        print(f"\n{'='*60}")
        print("🎯 DETECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"✅ Found {result['holes_found']} holes")

        # Save JSON report
        with open('simple_direct_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"📄 Report saved to: simple_direct_result.json")

        if result['holes']:
            hole = result['holes'][0]
            print(f"\n📍 Main hole:")
            print(f"   Position: ({hole['center'][0]}, {hole['center'][1]})")
            print(f"   In cropped fabric image")
    else:
        print("\n✅ No holes found - images match!")


if __name__ == "__main__":
    main()