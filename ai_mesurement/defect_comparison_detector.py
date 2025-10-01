#!/usr/bin/env python3
"""
Reference-Based Defect Detection
Compares a defective image with a reference (good) image to identify defects
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass
import matplotlib.pyplot as plt


@dataclass
class Defect:
    """Defect found by comparison"""
    contour: np.ndarray
    center: Tuple[int, int]
    area_px: float
    area_cm2: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float


class ReferenceBasedDefectDetector:
    """
    Detects defects by comparing test image with reference (good) image
    """

    def __init__(self, pixels_per_cm: float = None, debug: bool = False):
        """
        Initialize detector

        Args:
            pixels_per_cm: Scale factor for measurements
            debug: Show debug visualizations
        """
        self.pixels_per_cm = pixels_per_cm
        self.debug = debug

    def detect_defects(self,
                      reference_image: np.ndarray,
                      test_image: np.ndarray,
                      min_defect_area_cm2: float = 0.5) -> List[Defect]:
        """
        Detect defects by comparing test image with reference

        Args:
            reference_image: Good image (without defects)
            test_image: Image to inspect
            min_defect_area_cm2: Minimum defect size in cm²

        Returns:
            List of detected defects
        """
        print("🔍 Reference-Based Defect Detection")
        print("=" * 50)

        # Step 1: Align images (they might be in slightly different positions)
        print("\n1. Aligning images...")
        aligned_test, H = self._align_images(reference_image, test_image)

        if aligned_test is None:
            print("⚠️  Could not align images, using original")
            aligned_test = test_image

        # Step 2: Segment garment from both images
        print("2. Segmenting garments...")
        ref_mask = self._segment_garment(reference_image)
        test_mask = self._segment_garment(aligned_test)

        # Step 3: Compare images to find differences
        print("3. Comparing images...")
        diff_mask = self._compare_images(reference_image, aligned_test, ref_mask)

        if self.debug:
            self._show_debug("Difference Mask", diff_mask)

        # Step 4: Find defect regions
        print("4. Identifying defects...")
        defects = self._find_defects(diff_mask, min_defect_area_cm2)

        print(f"\n✅ Found {len(defects)} defects")
        for i, defect in enumerate(defects):
            print(f"   Defect {i+1}: {defect.area_cm2:.2f} cm² at {defect.center}")

        return defects

    def _align_images(self, reference: np.ndarray, test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Align test image to reference using feature matching

        Returns:
            (aligned_test_image, homography_matrix)
        """
        # Convert to grayscale
        ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        test_gray = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Use ORB for feature detection (fast and robust)
        orb = cv2.ORB_create(5000)

        # Find keypoints and descriptors
        kp1, des1 = orb.detectAndCompute(ref_gray, None)
        kp2, des2 = orb.detectAndCompute(test_gray, None)

        if des1 is None or des2 is None:
            return None, None

        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(des1, des2, k=2)

        # Apply ratio test (Lowe's ratio test)
        good_matches = []
        for m_n in matches:
            if len(m_n) == 2:
                m, n = m_n
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

        if len(good_matches) < 10:
            print(f"   ⚠️  Only {len(good_matches)} good matches found")
            return None, None

        print(f"   ✓ Found {len(good_matches)} matching features")

        # Extract matched keypoints
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Find homography
        H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

        if H is None:
            return None, None

        # Warp test image to align with reference
        height, width = reference.shape[:2]
        aligned = cv2.warpPerspective(test, H, (width, height))

        return aligned, H

    def _segment_garment(self, image: np.ndarray) -> np.ndarray:
        """
        Segment garment from background

        Returns:
            Binary mask of garment
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask for non-white areas (garment)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([255, 30, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)

        # Garment is everything that's NOT white background
        garment_mask = cv2.bitwise_not(white_mask)

        # Clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        garment_mask = cv2.morphologyEx(garment_mask, cv2.MORPH_CLOSE, kernel)
        garment_mask = cv2.morphologyEx(garment_mask, cv2.MORPH_OPEN, kernel)

        return garment_mask

    def _compare_images(self, reference: np.ndarray, test: np.ndarray,
                       mask: np.ndarray) -> np.ndarray:
        """
        Compare two images and return difference mask

        Args:
            reference: Reference (good) image
            test: Test image
            mask: Garment mask to focus comparison

        Returns:
            Binary mask of differences
        """
        # Convert to grayscale
        ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        test_gray = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Compute absolute difference
        diff = cv2.absdiff(ref_gray, test_gray)

        # Apply garment mask (only look at differences on garment)
        diff = cv2.bitwise_and(diff, diff, mask=mask)

        # Threshold to get significant differences
        # Use adaptive threshold to handle lighting variations
        diff_binary = cv2.adaptiveThreshold(
            diff, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, -10
        )

        # Also try simple threshold for strong differences
        _, strong_diff = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # Combine both
        diff_binary = cv2.bitwise_or(diff_binary, strong_diff)

        # Clean up noise
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        diff_binary = cv2.morphologyEx(diff_binary, cv2.MORPH_OPEN, kernel_small)

        # Dilate to connect nearby differences
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        diff_binary = cv2.dilate(diff_binary, kernel_dilate, iterations=1)

        return diff_binary

    def _find_defects(self, diff_mask: np.ndarray, min_area_cm2: float) -> List[Defect]:
        """
        Find defect regions in difference mask

        Args:
            diff_mask: Binary mask of differences
            min_area_cm2: Minimum defect size

        Returns:
            List of defects
        """
        # Find contours
        contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        defects = []
        min_area_px = min_area_cm2 * (self.pixels_per_cm ** 2) if self.pixels_per_cm else 50

        for contour in contours:
            area_px = cv2.contourArea(contour)

            # Filter small noise
            if area_px < min_area_px:
                continue

            # Get properties
            M = cv2.moments(contour)
            if M['m00'] == 0:
                continue

            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            center = (cx, cy)

            x, y, w, h = cv2.boundingRect(contour)
            bbox = (x, y, w, h)

            # Calculate area in cm²
            area_cm2 = area_px / (self.pixels_per_cm ** 2) if self.pixels_per_cm else area_px

            # Confidence based on size and compactness
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                compactness = 4 * np.pi * area_px / (perimeter ** 2)
                confidence = min(0.95, 0.5 + compactness * 0.5)
            else:
                confidence = 0.5

            defect = Defect(
                contour=contour,
                center=center,
                area_px=area_px,
                area_cm2=area_cm2,
                bbox=bbox,
                confidence=confidence
            )

            defects.append(defect)

        # Sort by area (largest first)
        defects.sort(key=lambda d: d.area_px, reverse=True)

        return defects

    def visualize_defects(self,
                         reference_image: np.ndarray,
                         test_image: np.ndarray,
                         defects: List[Defect],
                         save_path: str = 'defect_comparison_result.png'):
        """
        Create visualization showing detected defects

        Args:
            reference_image: Reference (good) image
            test_image: Test image
            defects: List of detected defects
            save_path: Path to save visualization
        """
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # Reference image
        ax = axes[0]
        ax.imshow(cv2.cvtColor(reference_image, cv2.COLOR_BGR2RGB))
        ax.set_title('Reference (Good)', fontsize=14, fontweight='bold')
        ax.axis('off')

        # Test image with defects marked
        ax = axes[1]
        result = test_image.copy()

        for i, defect in enumerate(defects):
            # Draw contour
            cv2.drawContours(result, [defect.contour], -1, (0, 0, 255), 3)

            # Draw bounding box
            x, y, w, h = defect.bbox
            cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)

            # Draw center point
            cv2.circle(result, defect.center, 10, (0, 255, 0), -1)

            # Add label
            label = f"D{i+1}: {defect.area_cm2:.1f}cm²"
            cv2.putText(result, label, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        ax.imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        ax.set_title('Test Image with Defects', fontsize=14, fontweight='bold')
        ax.axis('off')

        # Defect zoom
        ax = axes[2]
        if defects:
            # Show first (largest) defect zoomed in
            defect = defects[0]
            x, y, w, h = defect.bbox

            # Expand bbox for context
            margin = 50
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(test_image.shape[1], x + w + margin)
            y2 = min(test_image.shape[0], y + h + margin)

            zoom = result[y1:y2, x1:x2]
            ax.imshow(cv2.cvtColor(zoom, cv2.COLOR_BGR2RGB))
            ax.set_title(f'Defect Detail: {defect.area_cm2:.2f} cm²',
                        fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No Defects Found',
                   ha='center', va='center', fontsize=16)
        ax.axis('off')

        plt.suptitle('🔍 Reference-Based Defect Detection',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"\n📊 Visualization saved: {save_path}")

    def _show_debug(self, title: str, image: np.ndarray):
        """Show debug image"""
        if not self.debug:
            return

        plt.figure(figsize=(10, 8))
        if len(image.shape) == 2:
            plt.imshow(image, cmap='gray')
        else:
            plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.title(title)
        plt.axis('off')
        plt.show()


def main():
    """Test the detector"""
    import argparse

    parser = argparse.ArgumentParser(description='Reference-Based Defect Detection')
    parser.add_argument('-r', '--reference', required=True,
                       help='Path to reference (good) image')
    parser.add_argument('-t', '--test', required=True,
                       help='Path to test image')
    parser.add_argument('-s', '--scale', type=float, default=None,
                       help='Pixels per cm for measurements')
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Show debug visualizations')
    parser.add_argument('-m', '--min-size', type=float, default=0.3,
                       help='Minimum defect size in cm² (default: 0.3)')

    args = parser.parse_args()

    # Load images
    print(f"Loading reference image: {args.reference}")
    reference = cv2.imread(args.reference)
    if reference is None:
        print(f"❌ Cannot load reference image: {args.reference}")
        return 1

    print(f"Loading test image: {args.test}")
    test = cv2.imread(args.test)
    if test is None:
        print(f"❌ Cannot load test image: {args.test}")
        return 1

    # Detect ruler in reference image if scale not provided
    if args.scale is None:
        print("\n📏 Detecting ruler for scale...")
        try:
            from ruler_detection_smart import SmartRulerDetector
            ruler_detector = SmartRulerDetector(known_length_cm=31.0)
            ruler_info = ruler_detector.detect_ruler(reference)
            pixels_per_cm = ruler_info['pixels_per_cm']
            print(f"   ✓ Scale detected: {pixels_per_cm:.2f} pixels/cm")
        except Exception as e:
            print(f"   ⚠️  Could not detect ruler: {e}")
            print("   Using pixel measurements")
            pixels_per_cm = None
    else:
        pixels_per_cm = args.scale

    # Create detector
    detector = ReferenceBasedDefectDetector(
        pixels_per_cm=pixels_per_cm,
        debug=args.debug
    )

    # Detect defects
    defects = detector.detect_defects(reference, test, min_defect_area_cm2=args.min_size)

    # Visualize results
    detector.visualize_defects(reference, test, defects)

    # Print summary
    print("\n" + "=" * 50)
    print("📊 DETECTION SUMMARY")
    print("=" * 50)
    print(f"Defects found: {len(defects)}")
    for i, defect in enumerate(defects):
        print(f"\nDefect {i+1}:")
        print(f"  Location: {defect.center}")
        print(f"  Area: {defect.area_cm2:.2f} cm²")
        print(f"  Confidence: {defect.confidence:.1%}")

    return 0


if __name__ == '__main__':
    exit(main())
