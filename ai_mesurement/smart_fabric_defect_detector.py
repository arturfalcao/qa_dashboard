#!/usr/bin/env python3
"""
Smart Fabric Defect Detector
Focuses ONLY on the fabric area, ignoring background, ruler, shadows, etc.
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from typing import Tuple, List, Dict, Optional

class SmartFabricDefectDetector:
    """
    Intelligent defect detection that focuses ONLY on fabric
    """

    def __init__(self):
        self.debug = True
        self.min_defect_area = 50

    def segment_garment(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Intelligently segment the garment from background
        Returns: mask and cleaned garment image
        """
        print("  🎯 Segmenting garment from background...")

        # Multiple approaches for robust segmentation
        h, w = img.shape[:2]

        # 1. Color-based segmentation (background is usually white/light)
        # Convert to HSV for better color separation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Background is typically white/light gray
        # Define range for NON-background (i.e., the garment)
        # Lower saturation or very high value usually means background
        lower_bg = np.array([0, 0, 200])  # High value (brightness)
        upper_bg = np.array([180, 30, 255])  # Low saturation

        # Create mask for background
        bg_mask = cv2.inRange(hsv, lower_bg, upper_bg)

        # Invert to get garment mask
        garment_mask = cv2.bitwise_not(bg_mask)

        # 2. Gradient-based approach (garments have texture, background is uniform)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Calculate gradient magnitude
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient = np.sqrt(grad_x**2 + grad_y**2)
        gradient = np.uint8(np.clip(gradient, 0, 255))

        # Threshold gradient (garment has more texture)
        _, gradient_mask = cv2.threshold(gradient, 10, 255, cv2.THRESH_BINARY)

        # 3. Combine both approaches
        combined_mask = cv2.bitwise_or(garment_mask, gradient_mask)

        # 4. Clean up the mask
        # Remove small noise
        kernel_small = np.ones((5,5), np.uint8)
        cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_small)

        # Close gaps
        kernel_large = np.ones((15,15), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_large)

        # 5. Find the largest contour (the main garment)
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Get the largest contour (main garment piece)
            largest_contour = max(contours, key=cv2.contourArea)

            # Create final mask from largest contour
            final_mask = np.zeros_like(cleaned)
            cv2.drawContours(final_mask, [largest_contour], -1, 255, -1)

            # Smooth the contour edges
            final_mask = cv2.GaussianBlur(final_mask, (5, 5), 0)
            _, final_mask = cv2.threshold(final_mask, 128, 255, cv2.THRESH_BINARY)

            # Get bounding box for focusing
            x, y, w, h = cv2.boundingRect(largest_contour)
            print(f"    ✅ Garment found at ({x},{y}) size {w}x{h}")

            # Extract just the garment
            garment_only = cv2.bitwise_and(img, img, mask=final_mask)

            return final_mask, garment_only

        return cleaned, img

    def align_garments(self, golden_mask: np.ndarray, test_mask: np.ndarray,
                      golden_img: np.ndarray, test_img: np.ndarray) -> np.ndarray:
        """
        Align garments based on their masks for better comparison
        """
        print("  🔄 Aligning garments...")

        # Find contours of masks
        golden_contours, _ = cv2.findContours(golden_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        test_contours, _ = cv2.findContours(test_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not golden_contours or not test_contours:
            return test_img

        # Get largest contours
        golden_cnt = max(golden_contours, key=cv2.contourArea)
        test_cnt = max(test_contours, key=cv2.contourArea)

        # Get moments for center of mass
        M_golden = cv2.moments(golden_cnt)
        M_test = cv2.moments(test_cnt)

        if M_golden["m00"] != 0 and M_test["m00"] != 0:
            # Calculate centers
            cx_golden = int(M_golden["m10"] / M_golden["m00"])
            cy_golden = int(M_golden["m01"] / M_golden["m00"])
            cx_test = int(M_test["m10"] / M_test["m00"])
            cy_test = int(M_test["m01"] / M_test["m00"])

            # Calculate translation
            dx = cx_golden - cx_test
            dy = cy_golden - cy_test

            # Apply translation
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            aligned = cv2.warpAffine(test_img, M, (test_img.shape[1], test_img.shape[0]))

            print(f"    ✅ Aligned with offset ({dx}, {dy})")
            return aligned

        return test_img

    def detect_fabric_defects(self, golden_fabric: np.ndarray, test_fabric: np.ndarray,
                             mask: np.ndarray) -> List[Dict]:
        """
        Detect defects ONLY within the fabric area
        """
        print("  🔍 Detecting defects in fabric only...")

        defects = []

        # Ensure same size
        if golden_fabric.shape != test_fabric.shape:
            test_fabric = cv2.resize(test_fabric, (golden_fabric.shape[1], golden_fabric.shape[0]))

        # 1. Convert to multiple color spaces for comprehensive analysis
        # Grayscale
        golden_gray = cv2.cvtColor(golden_fabric, cv2.COLOR_BGR2GRAY)
        test_gray = cv2.cvtColor(test_fabric, cv2.COLOR_BGR2GRAY)

        # LAB (perceptually uniform)
        golden_lab = cv2.cvtColor(golden_fabric, cv2.COLOR_BGR2Lab)
        test_lab = cv2.cvtColor(test_fabric, cv2.COLOR_BGR2Lab)

        # 2. Calculate differences
        # Direct grayscale difference
        diff_gray = cv2.absdiff(golden_gray, test_gray)

        # LAB difference (more sensitive to actual color changes)
        diff_lab = cv2.absdiff(golden_lab, test_lab)
        diff_lab_gray = cv2.cvtColor(diff_lab, cv2.COLOR_Lab2BGR)
        diff_lab_gray = cv2.cvtColor(diff_lab_gray, cv2.COLOR_BGR2GRAY)

        # 3. Combine differences
        combined_diff = cv2.addWeighted(diff_gray, 0.5, diff_lab_gray, 0.5, 0)

        # 4. Apply mask to focus ONLY on fabric
        combined_diff = cv2.bitwise_and(combined_diff, mask)

        # 5. Adaptive thresholding for local defects
        # Use lower threshold to catch subtle defects
        _, binary = cv2.threshold(combined_diff, 25, 255, cv2.THRESH_BINARY)

        # Also use adaptive threshold for local variations
        adaptive = cv2.adaptiveThreshold(combined_diff, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 21, 3)

        # Combine both thresholds
        defect_mask = cv2.bitwise_or(binary, adaptive)

        # 6. Clean up noise
        kernel = np.ones((3,3), np.uint8)
        defect_mask = cv2.morphologyEx(defect_mask, cv2.MORPH_OPEN, kernel)
        defect_mask = cv2.morphologyEx(defect_mask, cv2.MORPH_CLOSE, kernel)

        # 7. Find defect contours
        contours, _ = cv2.findContours(defect_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        print(f"    📊 Found {len(contours)} potential defects in fabric")

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area - exclude too large areas (likely not real defects)
            max_area = (mask.shape[0] * mask.shape[1]) * 0.01  # Max 1% of fabric area
            if self.min_defect_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate center
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w//2, y + h//2

                # Analyze defect characteristics
                # Check if it's a hole (darker in test image)
                golden_roi = golden_gray[y:y+h, x:x+w]
                test_roi = test_gray[y:y+h, x:x+w]

                if golden_roi.size > 0 and test_roi.size > 0:
                    brightness_diff = float(np.mean(golden_roi) - np.mean(test_roi))
                else:
                    brightness_diff = 0

                # Calculate shape metrics
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0

                # Classify defect type
                if brightness_diff > 10:  # Test is darker
                    defect_type = "hole"
                elif brightness_diff < -10:  # Test is lighter
                    defect_type = "stain"
                else:
                    defect_type = "defect"

                # Calculate confidence
                # Higher brightness difference = higher confidence for holes
                confidence = min(1.0, abs(brightness_diff) / 50)

                defect = {
                    'type': defect_type,
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area),
                    'brightness_diff': brightness_diff,
                    'circularity': float(circularity),
                    'confidence': float(confidence)
                }

                defects.append(defect)

        # Sort by confidence
        defects.sort(key=lambda x: x['confidence'], reverse=True)

        return defects

    def detect(self, golden_path: str, test_path: str, output_path: str = None) -> Dict:
        """
        Main detection method - focuses ONLY on fabric defects
        """
        print(f"\n{'='*60}")
        print("🧵 SMART FABRIC DEFECT DETECTOR")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        golden = cv2.imread(str(golden_path))
        test = cv2.imread(str(test_path))

        if golden is None or test is None:
            print("❌ Error loading images")
            return None

        print(f"  Golden: {golden.shape[:2]}")
        print(f"  Test: {test.shape[:2]}")

        # Step 1: Segment garments from background
        print("\n🎯 STEP 1: Extracting fabric from background...")
        golden_mask, golden_fabric = self.segment_garment(golden)
        test_mask, test_fabric = self.segment_garment(test)

        # Step 2: Align garments
        print("\n🔄 STEP 2: Aligning garments...")
        aligned_test = self.align_garments(golden_mask, test_mask, golden, test)
        aligned_test_mask, aligned_test_fabric = self.segment_garment(aligned_test)

        # Step 3: Create intersection mask (only areas present in both)
        print("\n🎯 STEP 3: Creating fabric-only mask...")
        fabric_mask = cv2.bitwise_and(golden_mask, aligned_test_mask)

        # Step 4: Detect defects ONLY in fabric area
        print("\n🔍 STEP 4: Detecting defects in fabric...")
        defects = self.detect_fabric_defects(golden, aligned_test, fabric_mask)

        print(f"\n✅ Found {len(defects)} defects in fabric")

        # Show top defects
        for i, defect in enumerate(defects[:5], 1):
            print(f"\n  {i}. {defect['type'].upper()} at ({defect['center'][0]}, {defect['center'][1]})")
            print(f"     Size: {defect['bbox'][2]}x{defect['bbox'][3]} px")
            print(f"     Brightness diff: {defect['brightness_diff']:.1f}")
            print(f"     Confidence: {defect['confidence']:.1%}")

        # Create visualization
        if output_path:
            self.visualize_results(golden, test, aligned_test, fabric_mask, defects, output_path)

        # Return results
        return {
            'timestamp': datetime.now().isoformat(),
            'golden_image': str(golden_path),
            'test_image': str(test_path),
            'defects_found': len(defects),
            'defects': defects[:20]  # Top 20 defects
        }

    def visualize_results(self, golden, test, aligned, mask, defects, output_path):
        """
        Create visualization showing fabric segmentation and defects
        """
        h, w = test.shape[:2]

        # Ensure all images are same size
        if golden.shape != test.shape:
            golden = cv2.resize(golden, (w, h))
        if aligned.shape != test.shape:
            aligned = cv2.resize(aligned, (w, h))

        # Apply mask to show only fabric
        golden_fabric = cv2.bitwise_and(golden, golden, mask=mask)
        test_fabric = cv2.bitwise_and(aligned, aligned, mask=mask)

        # Mark defects
        marked = test.copy()

        # Draw mask boundary
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(marked, contours, -1, (0, 255, 0), 2)

        # Draw defects
        for i, defect in enumerate(defects[:10]):
            x, y, w, h = defect['bbox']
            cx, cy = defect['center']
            dtype = defect['type']
            conf = defect['confidence']

            # Color by type
            if dtype == "hole":
                color = (0, 0, 255)  # Red for holes
            elif dtype == "stain":
                color = (255, 0, 255)  # Magenta for stains
            else:
                color = (0, 165, 255)  # Orange for other

            # Draw bounding box
            cv2.rectangle(marked, (x, y), (x+w, y+h), color, 2)

            # Draw center point
            cv2.circle(marked, (cx, cy), 5, color, -1)

            # Add label
            label = f"{dtype} #{i+1} ({conf:.0%})"
            cv2.putText(marked, label, (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Create grid - resize all to fit
        grid_h, grid_w = h, w
        grid = np.zeros((grid_h*2, grid_w*2, 3), dtype=np.uint8)

        # Resize all components to fit grid cells
        golden_fabric_resized = cv2.resize(golden_fabric, (grid_w, grid_h))
        test_fabric_resized = cv2.resize(test_fabric, (grid_w, grid_h))
        mask_resized = cv2.resize(mask, (grid_w, grid_h))
        marked_resized = cv2.resize(marked, (grid_w, grid_h))

        grid[:grid_h, :grid_w] = golden_fabric_resized  # Golden fabric only
        grid[:grid_h, grid_w:] = test_fabric_resized    # Test fabric only
        grid[grid_h:, :grid_w] = cv2.cvtColor(mask_resized, cv2.COLOR_GRAY2BGR)  # Mask
        grid[grid_h:, grid_w:] = marked_resized  # Marked defects

        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(grid, "GOLDEN FABRIC", (10, 40), font, 1, (0, 255, 0), 2)
        cv2.putText(grid, "TEST FABRIC", (grid_w+10, 40), font, 1, (0, 255, 255), 2)
        cv2.putText(grid, "FABRIC MASK", (10, grid_h+40), font, 1, (255, 255, 0), 2)
        cv2.putText(grid, f"DEFECTS IN FABRIC: {len(defects)}", (grid_w+10, grid_h+40),
                   font, 1, (0, 0, 255), 2)

        # Save
        cv2.imwrite(str(output_path), grid)
        print(f"\n💾 Visualization saved to: {output_path}")

        # Save marked only
        marked_path = str(output_path).replace('.png', '_marked.png')
        cv2.imwrite(marked_path, marked)
        print(f"💾 Marked image saved to: {marked_path}")

        # Save mask for debugging
        if self.debug:
            mask_path = str(output_path).replace('.png', '_mask.png')
            cv2.imwrite(mask_path, mask)
            print(f"🔍 Fabric mask saved to: {mask_path}")


def main():
    """Test smart fabric defect detector"""

    detector = SmartFabricDefectDetector()

    golden = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
    output = "/home/celso/projects/qa_dashboard/ai_mesurement/smart_fabric_defects.png"

    result = detector.detect(golden, test, output)

    if result:
        # Save report
        report_path = Path(output).with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'='*60}")
        print("✨ SMART DETECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"✅ Found {result['defects_found']} defects IN FABRIC")

        if result['defects']:
            main_defect = result['defects'][0]
            print(f"\n🎯 Main defect:")
            print(f"   Type: {main_defect['type'].upper()}")
            print(f"   Location: ({main_defect['center'][0]}, {main_defect['center'][1]})")
            print(f"   Confidence: {main_defect['confidence']:.0%}")


if __name__ == "__main__":
    main()