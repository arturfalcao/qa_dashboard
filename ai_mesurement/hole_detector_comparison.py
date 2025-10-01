#!/usr/bin/env python3
"""
Hole Detection by Image Comparison
Detects holes/defects by comparing a defective image with a reference (non-defective) image
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class HoleDetectorComparison:
    def __init__(self):
        self.debug = True

    def align_images(self, img1, img2):
        """Align two images using feature matching"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Detect ORB features
        orb = cv2.ORB_create(5000)
        kp1, des1 = orb.detectAndCompute(gray1, None)
        kp2, des2 = orb.detectAndCompute(gray2, None)

        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        # Use top matches for homography
        if len(matches) > 10:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)

            # Find homography
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            # Warp img1 to align with img2
            h, w = img2.shape[:2]
            aligned = cv2.warpPerspective(img1, M, (w, h))

            return aligned

        return img1

    def detect_hole_by_comparison(self, reference_path, defective_path, output_path=None):
        """
        Detect holes by comparing reference (good) image with defective image

        Args:
            reference_path: Path to image without defects
            defective_path: Path to image with defects
            output_path: Optional path to save visualization
        """
        print(f"\n{'='*60}")
        print("HOLE DETECTION BY IMAGE COMPARISON")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        reference = cv2.imread(str(reference_path))
        defective = cv2.imread(str(defective_path))

        if reference is None or defective is None:
            print("❌ Error: Could not load images")
            return None

        print(f"  Reference: {reference.shape[:2]} pixels")
        print(f"  Defective: {defective.shape[:2]} pixels")

        # Resize if needed (to match dimensions)
        if reference.shape != defective.shape:
            print("\n🔄 Resizing images to match dimensions...")
            height = min(reference.shape[0], defective.shape[0])
            width = min(reference.shape[1], defective.shape[1])
            reference = cv2.resize(reference, (width, height))
            defective = cv2.resize(defective, (width, height))

        # Align images
        print("\n🎯 Aligning images...")
        aligned_reference = self.align_images(reference, defective)

        # Convert to Lab color space for better comparison
        ref_lab = cv2.cvtColor(aligned_reference, cv2.COLOR_BGR2Lab)
        def_lab = cv2.cvtColor(defective, cv2.COLOR_BGR2Lab)

        # Compute difference
        print("\n🔍 Computing image difference...")
        diff = cv2.absdiff(ref_lab, def_lab)

        # Convert difference to grayscale
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_Lab2BGR)
        diff_gray = cv2.cvtColor(diff_gray, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        diff_blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)

        # Adaptive thresholding
        _, thresh = cv2.threshold(diff_blur, 30, 255, cv2.THRESH_BINARY)

        # Morphological operations to clean up
        kernel = np.ones((5,5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by area
        min_area = 50  # Minimum area for a defect
        holes = []

        print(f"\n📊 Found {len(contours)} potential defects")

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate additional properties
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0

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
                    'confidence': min(1.0, area / 500)  # Confidence based on size
                }
                holes.append(hole)

        # Sort by area (largest first)
        holes.sort(key=lambda x: x['area'], reverse=True)

        print(f"\n✅ Detected {len(holes)} holes/defects:")
        for i, hole in enumerate(holes[:5], 1):  # Show top 5
            print(f"  {i}. Area: {hole['area']:.0f}px², "
                  f"Location: ({hole['center'][0]}, {hole['center'][1]}), "
                  f"Confidence: {hole['confidence']:.2%}")

        # Create visualization
        result_img = defective.copy()
        overlay = defective.copy()

        for hole in holes:
            x, y, w, h = hole['bbox']
            cx, cy = hole['center']
            confidence = hole['confidence']

            # Color based on confidence
            if confidence > 0.7:
                color = (0, 0, 255)  # Red for high confidence
            elif confidence > 0.4:
                color = (0, 165, 255)  # Orange for medium
            else:
                color = (0, 255, 255)  # Yellow for low

            # Draw rectangle and center point
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 2)
            cv2.circle(overlay, (cx, cy), 5, color, -1)

            # Add text
            text = f"Hole {confidence:.0%}"
            cv2.putText(overlay, text, (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Blend overlay
        cv2.addWeighted(overlay, 0.7, result_img, 0.3, 0, result_img)

        # Save visualization if requested
        if output_path:
            # Create side-by-side comparison
            h, w = defective.shape[:2]
            comparison = np.zeros((h, w*3, 3), dtype=np.uint8)

            # Reference | Defective | Result
            comparison[:, :w] = aligned_reference
            comparison[:, w:w*2] = defective
            comparison[:, w*2:] = result_img

            # Add labels
            cv2.putText(comparison, "Reference (No Hole)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(comparison, "Defective (With Hole)", (w+10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(comparison, "Detected Holes", (w*2+10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            cv2.imwrite(str(output_path), comparison)
            print(f"\n💾 Visualization saved to: {output_path}")

            # Also save just the result
            result_only_path = str(output_path).replace('.', '_result.')
            cv2.imwrite(result_only_path, result_img)
            print(f"💾 Result only saved to: {result_only_path}")

            # Save debug images if enabled
            if self.debug:
                debug_dir = Path(output_path).parent
                cv2.imwrite(str(debug_dir / "debug_diff.png"), diff_gray)
                cv2.imwrite(str(debug_dir / "debug_thresh.png"), thresh)
                print(f"🐛 Debug images saved to {debug_dir}")

        # Prepare result
        result = {
            'timestamp': datetime.now().isoformat(),
            'reference_image': str(reference_path),
            'defective_image': str(defective_path),
            'holes_detected': len(holes),
            'holes': holes[:10],  # Return top 10 holes
            'image_size': list(defective.shape[:2]),
            'total_defect_area': sum(h['area'] for h in holes)
        }

        return result


def main():
    """Test the hole detector with the provided images"""
    detector = HoleDetectorComparison()

    # Paths to images
    reference_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg")
    defective_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg")
    output_path = Path("/home/celso/projects/qa_dashboard/ai_mesurement/hole_comparison_result.png")

    # Detect holes
    result = detector.detect_hole_by_comparison(
        reference_path,
        defective_path,
        output_path
    )

    if result:
        # Save JSON report
        report_path = output_path.with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📄 Report saved to: {report_path}")

        print(f"\n{'='*60}")
        print("DETECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"✅ Found {result['holes_detected']} holes")
        print(f"📏 Total defect area: {result['total_defect_area']:.0f} pixels²")

        if result['holes']:
            main_hole = result['holes'][0]
            print(f"\n🎯 Main hole location:")
            print(f"   Center: ({main_hole['center'][0]}, {main_hole['center'][1]})")
            print(f"   Size: {main_hole['bbox'][2]}x{main_hole['bbox'][3]} pixels")
            print(f"   Area: {main_hole['area']:.0f} pixels²")
            print(f"   Confidence: {main_hole['confidence']:.1%}")


if __name__ == "__main__":
    main()