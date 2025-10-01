#!/usr/bin/env python3
"""
Universal Defect Detector
Compares any garment golden image with test image to find defects (holes, stains, tears, etc.)
Works with any type of apparel: shirts, trousers, dresses, jackets, etc.
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class UniversalDefectDetector:
    """
    Universal defect detection system for any type of garment
    """

    def __init__(self, sensitivity: float = 0.7):
        """
        Initialize detector

        Args:
            sensitivity: Detection sensitivity (0.0 to 1.0)
                        Lower = more sensitive (detects smaller defects)
                        Higher = less sensitive (only major defects)
        """
        self.sensitivity = sensitivity
        self.debug = False

    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Enhanced preprocessing for better comparison"""
        # Denoise
        denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

        # Enhance contrast
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)

        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_Lab2BGR)

        return enhanced

    def extract_garment_region(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract the garment from background
        Returns mask and bounding box
        """
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Use multiple thresholding methods
        # Method 1: Otsu thresholding
        _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Method 2: Adaptive threshold
        thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)

        # Combine methods
        mask = cv2.bitwise_or(thresh1, thresh2)

        # Clean up mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find largest contour (the garment)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            # Create clean mask from largest contour
            clean_mask = np.zeros_like(mask)
            cv2.drawContours(clean_mask, [largest], -1, 255, -1)

            # Get bounding box
            x, y, w, h = cv2.boundingRect(largest)
            bbox = (x, y, w, h)

            return clean_mask, bbox

        return mask, (0, 0, img.shape[1], img.shape[0])

    def align_images_robust(self, golden: np.ndarray, test: np.ndarray) -> np.ndarray:
        """
        Robust image alignment using multiple feature detectors
        """
        # Convert to grayscale
        gray_golden = cv2.cvtColor(golden, cv2.COLOR_BGR2GRAY)
        gray_test = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Try SIFT first (best for textured surfaces)
        try:
            sift = cv2.SIFT_create(nfeatures=5000)
            kp1, des1 = sift.detectAndCompute(gray_golden, None)
            kp2, des2 = sift.detectAndCompute(gray_test, None)

            if des1 is not None and des2 is not None and len(des1) > 10:
                # FLANN matcher
                FLANN_INDEX_KDTREE = 1
                index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
                search_params = dict(checks=50)
                flann = cv2.FlannBasedMatcher(index_params, search_params)

                matches = flann.knnMatch(des1, des2, k=2)

                # Filter good matches
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
                    if M is not None:
                        h, w = test.shape[:2]
                        aligned = cv2.warpPerspective(golden, M, (w, h))
                        return aligned
        except:
            pass

        # Fallback: ORB (faster, works for most cases)
        try:
            orb = cv2.ORB_create(nfeatures=5000)
            kp1, des1 = orb.detectAndCompute(gray_golden, None)
            kp2, des2 = orb.detectAndCompute(gray_test, None)

            if des1 is not None and des2 is not None:
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = matcher.match(des1, des2)

                if len(matches) > 10:
                    matches = sorted(matches, key=lambda x: x.distance)
                    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)
                    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)

                    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                    if M is not None:
                        h, w = test.shape[:2]
                        aligned = cv2.warpPerspective(golden, M, (w, h))
                        return aligned
        except:
            pass

        # If alignment fails, return original
        return golden

    def detect_defects_multiscale(self, golden: np.ndarray, test: np.ndarray,
                                  mask: np.ndarray) -> List[Dict]:
        """
        Detect defects using multiple scales and methods
        """
        defects = []

        # Multiple color spaces for comprehensive analysis
        # BGR difference
        diff_bgr = cv2.absdiff(golden, test)
        diff_bgr_gray = cv2.cvtColor(diff_bgr, cv2.COLOR_BGR2GRAY)

        # HSV difference (good for color changes)
        golden_hsv = cv2.cvtColor(golden, cv2.COLOR_BGR2HSV)
        test_hsv = cv2.cvtColor(test, cv2.COLOR_BGR2HSV)
        diff_hsv = cv2.absdiff(golden_hsv, test_hsv)
        diff_hsv_gray = diff_hsv[:,:,2]  # Use Value channel

        # LAB difference (perceptually uniform)
        golden_lab = cv2.cvtColor(golden, cv2.COLOR_BGR2Lab)
        test_lab = cv2.cvtColor(test, cv2.COLOR_BGR2Lab)
        diff_lab = cv2.absdiff(golden_lab, test_lab)
        diff_lab_gray = cv2.cvtColor(diff_lab, cv2.COLOR_Lab2BGR)
        diff_lab_gray = cv2.cvtColor(diff_lab_gray, cv2.COLOR_BGR2GRAY)

        # Combine all differences with weights
        combined_diff = cv2.addWeighted(diff_bgr_gray, 0.3, diff_hsv_gray, 0.3, 0)
        combined_diff = cv2.addWeighted(combined_diff, 1.0, diff_lab_gray, 0.4, 0)

        # Apply mask to focus on garment only
        combined_diff = cv2.bitwise_and(combined_diff, mask)

        # Multi-scale detection
        scales = [1.0, 0.75, 0.5]  # Different scales to detect various defect sizes

        for scale in scales:
            # Resize if needed
            if scale != 1.0:
                scaled_diff = cv2.resize(combined_diff, None, fx=scale, fy=scale)
            else:
                scaled_diff = combined_diff

            # Dynamic thresholding based on sensitivity
            threshold_value = int(255 * (1.0 - self.sensitivity) * 0.3)
            _, thresh = cv2.threshold(scaled_diff, threshold_value, 255, cv2.THRESH_BINARY)

            # Also use adaptive threshold
            adaptive = cv2.adaptiveThreshold(scaled_diff, 255,
                                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)

            # Combine thresholds
            combined_thresh = cv2.bitwise_or(thresh, adaptive)

            # Clean up
            kernel_size = max(3, int(5 * scale))
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            cleaned = cv2.morphologyEx(combined_thresh, cv2.MORPH_OPEN, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

            # Find contours
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Analyze contours
            min_area = 50 * scale * scale  # Adjust minimum area by scale
            max_area = (cleaned.shape[0] * cleaned.shape[1]) * 0.1  # Max 10% of image

            for contour in contours:
                area = cv2.contourArea(contour)

                if min_area < area < max_area:
                    # Get properties
                    x, y, w, h = cv2.boundingRect(contour)

                    # Scale back to original size
                    if scale != 1.0:
                        x, y, w, h = int(x/scale), int(y/scale), int(w/scale), int(h/scale)
                        area = area / (scale * scale)

                    # Calculate shape properties
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0

                    # Get intensity in difference image
                    roi_mask = np.zeros(combined_diff.shape, np.uint8)
                    scaled_contour = contour
                    if scale != 1.0:
                        scaled_contour = (contour / scale).astype(np.int32)
                    cv2.drawContours(roi_mask, [scaled_contour], -1, 255, -1)
                    mean_diff = cv2.mean(combined_diff, mask=roi_mask)[0]

                    # Calculate confidence
                    size_score = min(1.0, area / 5000)
                    intensity_score = min(1.0, mean_diff / 100)

                    confidence = (size_score * 0.4 + intensity_score * 0.6)

                    # Get center
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"] / scale) if scale != 1.0 else int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"] / scale) if scale != 1.0 else int(M["m01"] / M["m00"])
                    else:
                        cx, cy = x + w//2, y + h//2

                    # Classify defect type
                    defect_type = self.classify_defect(circularity, area, mean_diff)

                    defect = {
                        'type': defect_type,
                        'bbox': [x, y, w, h],
                        'center': [cx, cy],
                        'area': float(area),
                        'circularity': float(circularity),
                        'mean_difference': float(mean_diff),
                        'confidence': float(confidence),
                        'scale_detected': scale
                    }

                    # Check if this defect is not a duplicate
                    is_duplicate = False
                    for existing in defects:
                        dist = np.sqrt((existing['center'][0] - cx)**2 +
                                     (existing['center'][1] - cy)**2)
                        if dist < max(w, h) * 0.5:  # Too close to existing defect
                            is_duplicate = True
                            # Keep the one with higher confidence
                            if confidence > existing['confidence']:
                                defects.remove(existing)
                                is_duplicate = False
                            break

                    if not is_duplicate:
                        defects.append(defect)

        # Sort by confidence
        defects.sort(key=lambda x: x['confidence'], reverse=True)

        return defects

    def classify_defect(self, circularity: float, area: float, intensity: float) -> str:
        """
        Classify the type of defect based on characteristics
        """
        if circularity > 0.7 and area < 1000:
            return "hole"
        elif circularity < 0.3 and area > 1000:
            return "tear"
        elif intensity > 50 and area > 500:
            return "stain"
        elif area < 200:
            return "spot"
        else:
            return "defect"

    def detect(self, golden_path: str, test_path: str, output_path: str = None) -> Dict:
        """
        Main detection method

        Args:
            golden_path: Path to reference image (no defects)
            test_path: Path to test image (may have defects)
            output_path: Optional path to save visualization

        Returns:
            Dictionary with detection results
        """
        print(f"\n{'='*60}")
        print("UNIVERSAL DEFECT DETECTION SYSTEM")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        golden = cv2.imread(str(golden_path))
        test = cv2.imread(str(test_path))

        if golden is None or test is None:
            print("❌ Error: Could not load images")
            return None

        print(f"  Golden image: {golden.shape[:2]}")
        print(f"  Test image: {test.shape[:2]}")

        # Resize for processing if too large
        max_dim = 2000
        if max(golden.shape[:2]) > max_dim:
            scale = max_dim / max(golden.shape[:2])
            new_size = (int(golden.shape[1] * scale), int(golden.shape[0] * scale))
            golden = cv2.resize(golden, new_size)
            test = cv2.resize(test, new_size)
            print(f"  Resized to {new_size} for processing")

        # Preprocess
        print("\n🔧 Preprocessing images...")
        golden = self.preprocess_image(golden)
        test = self.preprocess_image(test)

        # Extract garment regions
        print("\n👕 Extracting garment regions...")
        golden_mask, golden_bbox = self.extract_garment_region(golden)
        test_mask, test_bbox = self.extract_garment_region(test)

        # Combine masks
        combined_mask = cv2.bitwise_and(golden_mask, test_mask)

        # Align images
        print("\n🎯 Aligning images...")
        aligned_golden = self.align_images_robust(golden, test)

        # Detect defects
        print(f"\n🔍 Detecting defects (sensitivity: {self.sensitivity})...")
        defects = self.detect_defects_multiscale(aligned_golden, test, combined_mask)

        print(f"\n✅ Found {len(defects)} defects:")
        for i, defect in enumerate(defects[:10], 1):
            print(f"  {i}. {defect['type'].upper()} at ({defect['center'][0]}, {defect['center'][1]})")
            print(f"     Size: {defect['bbox'][2]}x{defect['bbox'][3]} pixels")
            print(f"     Confidence: {defect['confidence']:.1%}")

        # Create visualization
        if output_path:
            self.create_visualization(golden, test, aligned_golden, defects, output_path)

        # Prepare result
        result = {
            'timestamp': datetime.now().isoformat(),
            'golden_image': str(golden_path),
            'test_image': str(test_path),
            'defects_found': len(defects),
            'defects': defects[:20],  # Return top 20 defects
            'sensitivity': self.sensitivity,
            'processing_size': list(test.shape[:2])
        }

        return result

    def create_visualization(self, golden: np.ndarray, test: np.ndarray,
                           aligned: np.ndarray, defects: List[Dict],
                           output_path: str):
        """
        Create comprehensive visualization
        """
        h, w = test.shape[:2]

        # Mark defects on test image
        marked = test.copy()
        overlay = test.copy()

        colors = {
            'hole': (0, 0, 255),      # Red
            'tear': (255, 0, 0),      # Blue
            'stain': (0, 255, 255),   # Yellow
            'spot': (255, 0, 255),    # Magenta
            'defect': (0, 165, 255)   # Orange
        }

        for i, defect in enumerate(defects[:10]):  # Show top 10
            x, y, w, h = defect['bbox']
            cx, cy = defect['center']
            dtype = defect['type']
            conf = defect['confidence']

            color = colors.get(dtype, (0, 165, 255))

            # Draw bounding box
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 2)

            # Draw center marker
            cv2.drawMarker(overlay, (cx, cy), color, cv2.MARKER_CROSS, 20, 2)

            # Add label
            label = f"{dtype.upper()} #{i+1} ({conf:.0%})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]

            # Background for text
            cv2.rectangle(overlay, (x, y-label_size[1]-10),
                        (x+label_size[0]+10, y), color, -1)
            cv2.putText(overlay, label, (x+5, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Blend overlay
        cv2.addWeighted(overlay, 0.7, marked, 0.3, 0, marked)

        # Create comparison grid (2x2)
        grid = np.zeros((h*2, w*2, 3), dtype=np.uint8)

        # Top-left: Golden
        grid[:h, :w] = cv2.resize(golden, (w, h))
        # Top-right: Test
        grid[:h, w:] = test
        # Bottom-left: Aligned golden
        grid[h:, :w] = cv2.resize(aligned, (w, h))
        # Bottom-right: Marked defects
        grid[h:, w:] = marked

        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(grid, "GOLDEN (Reference)", (10, 40), font, 1, (0, 255, 0), 2)
        cv2.putText(grid, "TEST IMAGE", (w+10, 40), font, 1, (0, 255, 255), 2)
        cv2.putText(grid, "ALIGNED GOLDEN", (10, h+40), font, 1, (255, 255, 0), 2)
        cv2.putText(grid, f"DEFECTS DETECTED: {len(defects)}", (w+10, h+40),
                   font, 1, (0, 0, 255), 2)

        # Save visualization
        cv2.imwrite(str(output_path), grid)
        print(f"\n💾 Visualization saved to: {output_path}")

        # Save marked image separately
        marked_path = str(output_path).replace('.', '_marked.')
        cv2.imwrite(marked_path, marked)
        print(f"💾 Marked image saved to: {marked_path}")


def main():
    """Test the universal detector with the provided images"""

    # Initialize detector with medium sensitivity
    detector = UniversalDefectDetector(sensitivity=0.5)

    # Test with trousers
    print("\n" + "="*60)
    print("TESTING WITH TROUSERS")
    print("="*60)

    golden_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
    output_path = "/home/celso/projects/qa_dashboard/ai_mesurement/universal_detection_result.png"

    result = detector.detect(golden_path, test_path, output_path)

    if result:
        # Save report
        report_path = Path(output_path).with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📄 Report saved to: {report_path}")

        print(f"\n{'='*60}")
        print("DETECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"✅ System detected {result['defects_found']} defects")

        if result['defects']:
            main_defect = result['defects'][0]
            print(f"\n🎯 Main defect:")
            print(f"   Type: {main_defect['type'].upper()}")
            print(f"   Location: ({main_defect['center'][0]}, {main_defect['center'][1]})")
            print(f"   Size: {main_defect['bbox'][2]}x{main_defect['bbox'][3]} pixels")
            print(f"   Confidence: {main_defect['confidence']:.1%}")


if __name__ == "__main__":
    main()