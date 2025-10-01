#!/usr/bin/env python3
"""
Refined Hole Detection by Image Comparison
Improved version with better alignment and detection
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class RefinedHoleDetector:
    def __init__(self):
        self.debug = True

    def preprocess_image(self, img):
        """Preprocess image for better comparison"""
        # Apply bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(img, 9, 75, 75)
        return filtered

    def find_garment_region(self, img):
        """Find the main garment region to focus detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply threshold to separate garment from background
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # Find largest contour (the garment)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            return (x, y, w, h)
        return None

    def align_images_sift(self, img1, img2):
        """Better alignment using SIFT features"""
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Use SIFT for better feature detection
        sift = cv2.SIFT_create()
        kp1, des1 = sift.detectAndCompute(gray1, None)
        kp2, des2 = sift.detectAndCompute(gray2, None)

        # FLANN matcher for better matching
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        if des1 is not None and des2 is not None and len(des1) > 10 and len(des2) > 10:
            matches = flann.knnMatch(des1, des2, k=2)

            # Store good matches using Lowe's ratio test
            good = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.7 * n.distance:
                        good.append(m)

            if len(good) > 10:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

                M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                h, w = img2.shape[:2]
                aligned = cv2.warpPerspective(img1, M, (w, h))
                return aligned

        return img1

    def detect_hole_refined(self, reference_path, defective_path, output_path=None):
        """
        Refined hole detection with better precision

        Args:
            reference_path: Path to image without defects
            defective_path: Path to image with defects
            output_path: Optional path to save visualization
        """
        print(f"\n{'='*60}")
        print("REFINED HOLE DETECTION")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        reference = cv2.imread(str(reference_path))
        defective = cv2.imread(str(defective_path))

        if reference is None or defective is None:
            print("❌ Error: Could not load images")
            return None

        # Preprocess images
        print("\n🔧 Preprocessing images...")
        reference = self.preprocess_image(reference)
        defective = self.preprocess_image(defective)

        # Resize to manageable size for processing
        max_dimension = 2000
        h, w = reference.shape[:2]
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            reference = cv2.resize(reference, (new_w, new_h))
            defective = cv2.resize(defective, (new_w, new_h))
            print(f"  Resized to {new_w}x{new_h} for processing")

        # Find garment region
        print("\n👕 Finding garment region...")
        garment_roi = self.find_garment_region(defective)
        if garment_roi:
            x, y, w, h = garment_roi
            print(f"  Garment ROI: ({x},{y}) {w}x{h}")

        # Align images
        print("\n🎯 Aligning images with SIFT...")
        aligned_ref = self.align_images_sift(reference, defective)

        # Compute difference using multiple methods
        print("\n🔍 Computing differences...")

        # Method 1: Direct difference
        diff_bgr = cv2.absdiff(aligned_ref, defective)

        # Method 2: Grayscale difference
        gray_ref = cv2.cvtColor(aligned_ref, cv2.COLOR_BGR2GRAY)
        gray_def = cv2.cvtColor(defective, cv2.COLOR_BGR2GRAY)
        diff_gray = cv2.absdiff(gray_ref, gray_def)

        # Method 3: HSV difference (good for color changes)
        hsv_ref = cv2.cvtColor(aligned_ref, cv2.COLOR_BGR2HSV)
        hsv_def = cv2.cvtColor(defective, cv2.COLOR_BGR2HSV)
        diff_hsv = cv2.absdiff(hsv_ref, hsv_def)
        diff_hsv_gray = cv2.cvtColor(diff_hsv, cv2.COLOR_HSV2BGR)
        diff_hsv_gray = cv2.cvtColor(diff_hsv_gray, cv2.COLOR_BGR2GRAY)

        # Combine differences with weights
        combined_diff = cv2.addWeighted(diff_gray, 0.5, diff_hsv_gray, 0.5, 0)

        # Apply denoising
        combined_diff = cv2.fastNlMeansDenoising(combined_diff, None, 10, 7, 21)

        # Apply multiple threshold levels
        print("\n🎨 Applying multi-level thresholding...")

        # Adaptive threshold
        thresh_adaptive = cv2.adaptiveThreshold(combined_diff, 255,
                                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, 11, 2)

        # Fixed threshold with Otsu
        _, thresh_otsu = cv2.threshold(combined_diff, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Combine thresholds
        combined_thresh = cv2.bitwise_or(thresh_adaptive, thresh_otsu)

        # Morphological operations
        kernel_small = np.ones((3,3), np.uint8)
        kernel_medium = np.ones((5,5), np.uint8)

        # Remove small noise
        cleaned = cv2.morphologyEx(combined_thresh, cv2.MORPH_OPEN, kernel_small)
        # Fill small gaps
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_medium)

        # If we have ROI, mask outside areas
        if garment_roi:
            mask = np.zeros_like(cleaned)
            x, y, w, h = garment_roi
            mask[y:y+h, x:x+w] = 255
            cleaned = cv2.bitwise_and(cleaned, mask)

        # Find contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Analyze contours
        min_area = 100  # Minimum area for a defect
        max_area = (cleaned.shape[0] * cleaned.shape[1]) * 0.1  # Max 10% of image
        holes = []

        print(f"\n📊 Analyzing {len(contours)} potential defects...")

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area
            if min_area < area < max_area:
                # Get properties
                x, y, w, h = cv2.boundingRect(contour)
                perimeter = cv2.arcLength(contour, True)

                # Calculate shape features
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    aspect_ratio = float(w) / h if h > 0 else 0
                else:
                    circularity = 0
                    aspect_ratio = 0

                # Get intensity in difference image
                mask = np.zeros(combined_diff.shape, np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                mean_intensity = cv2.mean(combined_diff, mask=mask)[0]

                # Calculate confidence based on multiple factors
                size_score = min(1.0, area / 5000)
                intensity_score = min(1.0, mean_intensity / 100)
                shape_score = circularity  # Holes tend to be circular

                confidence = (size_score * 0.3 + intensity_score * 0.5 + shape_score * 0.2)

                # Get centroid
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w//2, y + h//2

                hole = {
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area),
                    'perimeter': float(perimeter),
                    'circularity': float(circularity),
                    'aspect_ratio': float(aspect_ratio),
                    'mean_intensity': float(mean_intensity),
                    'confidence': float(confidence)
                }
                holes.append(hole)

        # Sort by confidence
        holes.sort(key=lambda x: x['confidence'], reverse=True)

        # Filter low confidence
        holes = [h for h in holes if h['confidence'] > 0.2]

        print(f"\n✅ Found {len(holes)} probable holes/defects:")
        for i, hole in enumerate(holes[:5], 1):
            print(f"  {i}. Location: ({hole['center'][0]}, {hole['center'][1]})")
            print(f"     Size: {hole['bbox'][2]}x{hole['bbox'][3]} px")
            print(f"     Area: {hole['area']:.0f} px²")
            print(f"     Circularity: {hole['circularity']:.2f}")
            print(f"     Confidence: {hole['confidence']:.1%}")

        # Create visualization
        result_img = defective.copy()
        overlay = defective.copy()

        for i, hole in enumerate(holes):
            x, y, w, h = hole['bbox']
            cx, cy = hole['center']
            confidence = hole['confidence']

            # Color based on confidence
            if confidence > 0.7:
                color = (0, 0, 255)  # Red
            elif confidence > 0.4:
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 255)  # Yellow

            # Draw bounding box
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 2)

            # Draw center cross
            cv2.line(overlay, (cx-10, cy), (cx+10, cy), color, 2)
            cv2.line(overlay, (cx, cy-10), (cx, cy+10), color, 2)

            # Add label
            label = f"Hole #{i+1} ({confidence:.0%})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(overlay, (x, y-label_size[1]-10),
                         (x+label_size[0]+10, y), color, -1)
            cv2.putText(overlay, label, (x+5, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Blend overlay
        cv2.addWeighted(overlay, 0.7, result_img, 0.3, 0, result_img)

        # Save visualization
        if output_path:
            # Create comparison image
            h, w = defective.shape[:2]
            comparison = np.zeros((h*2, w*2, 3), dtype=np.uint8)

            # Top-left: Reference
            comparison[:h, :w] = cv2.resize(aligned_ref, (w, h))
            # Top-right: Defective
            comparison[:h, w:] = defective
            # Bottom-left: Difference visualization
            diff_viz = cv2.cvtColor(combined_diff, cv2.COLOR_GRAY2BGR)
            diff_viz = cv2.applyColorMap(diff_viz, cv2.COLORMAP_JET)
            comparison[h:, :w] = diff_viz
            # Bottom-right: Result
            comparison[h:, w:] = result_img

            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(comparison, "Reference", (10, 30), font, 1, (0, 255, 0), 2)
            cv2.putText(comparison, "Defective", (w+10, 30), font, 1, (0, 0, 255), 2)
            cv2.putText(comparison, "Difference Map", (10, h+30), font, 1, (255, 255, 0), 2)
            cv2.putText(comparison, f"Detected: {len(holes)} holes", (w+10, h+30), font, 1, (255, 0, 255), 2)

            cv2.imwrite(str(output_path), comparison)
            print(f"\n💾 Visualization saved to: {output_path}")

            # Save result only
            result_path = str(output_path).replace('.png', '_result.png')
            cv2.imwrite(result_path, result_img)

            # Save debug images
            if self.debug:
                debug_dir = Path(output_path).parent
                cv2.imwrite(str(debug_dir / "debug_combined_diff.png"), combined_diff)
                cv2.imwrite(str(debug_dir / "debug_threshold.png"), cleaned)

        # Return results
        return {
            'timestamp': datetime.now().isoformat(),
            'holes_detected': len(holes),
            'holes': holes,
            'processing_size': list(defective.shape[:2])
        }


def main():
    """Test the refined hole detector"""
    detector = RefinedHoleDetector()

    # Paths
    reference_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg")
    defective_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg")
    output_path = Path("/home/celso/projects/qa_dashboard/ai_mesurement/hole_refined_result.png")

    # Run detection
    result = detector.detect_hole_refined(
        reference_path,
        defective_path,
        output_path
    )

    if result:
        # Save report
        report_path = output_path.with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'='*60}")
        print("DETECTION COMPLETE!")
        print(f"{'='*60}")

        if result['holes']:
            print(f"\n🎯 Main defect found at:")
            main = result['holes'][0]
            print(f"   Position: ({main['center'][0]}, {main['center'][1]}) pixels")
            print(f"   Bounding box: {main['bbox'][2]}x{main['bbox'][3]} pixels")
            print(f"   Confidence: {main['confidence']:.1%}")


if __name__ == "__main__":
    main()