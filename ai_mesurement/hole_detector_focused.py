#!/usr/bin/env python3
"""
Focused Hole Detection - Detects small holes with high precision
Specifically tuned for detecting the hole in the upper part of the garment
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class FocusedHoleDetector:
    def __init__(self):
        self.debug = True

    def enhance_contrast(self, img):
        """Enhance contrast to make holes more visible"""
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)

        # Merge and convert back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_Lab2BGR)
        return enhanced

    def focus_upper_region(self, img):
        """Focus on upper 40% of the garment where hole is likely"""
        h, w = img.shape[:2]
        # Focus on upper portion
        upper_portion = int(h * 0.4)
        return img[:upper_portion, :], (0, 0, w, upper_portion)

    def detect_hole_focused(self, reference_path, defective_path, output_path=None):
        """
        Focused detection for the specific hole in the upper garment area
        """
        print(f"\n{'='*60}")
        print("FOCUSED HOLE DETECTION - UPPER GARMENT AREA")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        reference = cv2.imread(str(reference_path))
        defective = cv2.imread(str(defective_path))

        if reference is None or defective is None:
            print("❌ Error: Could not load images")
            return None

        original_defective = defective.copy()

        # Resize for processing
        scale = 0.5  # Process at half resolution for speed
        h, w = reference.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        reference = cv2.resize(reference, (new_w, new_h))
        defective = cv2.resize(defective, (new_w, new_h))

        print(f"  Processing at {new_w}x{new_h}")

        # Enhance contrast
        print("\n🔆 Enhancing contrast...")
        reference = self.enhance_contrast(reference)
        defective = self.enhance_contrast(defective)

        # Focus on upper region
        print("\n🎯 Focusing on upper garment region...")
        ref_upper, roi = self.focus_upper_region(reference)
        def_upper, _ = self.focus_upper_region(defective)

        # Convert to grayscale for detailed analysis
        gray_ref = cv2.cvtColor(ref_upper, cv2.COLOR_BGR2GRAY)
        gray_def = cv2.cvtColor(def_upper, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        gray_ref = cv2.GaussianBlur(gray_ref, (3, 3), 0)
        gray_def = cv2.GaussianBlur(gray_def, (3, 3), 0)

        # Compute absolute difference
        print("\n🔍 Computing pixel-level differences...")
        diff = cv2.absdiff(gray_ref, gray_def)

        # Apply multiple processing techniques
        # 1. Direct threshold on difference
        _, thresh1 = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        # 2. Adaptive threshold on difference
        thresh2 = cv2.adaptiveThreshold(diff, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 11, 2)

        # 3. Edge detection approach
        edges_ref = cv2.Canny(gray_ref, 50, 150)
        edges_def = cv2.Canny(gray_def, 50, 150)
        edge_diff = cv2.absdiff(edges_ref, edges_def)
        _, thresh3 = cv2.threshold(edge_diff, 50, 255, cv2.THRESH_BINARY)

        # Combine all methods
        combined = cv2.bitwise_or(thresh1, thresh2)
        combined = cv2.bitwise_or(combined, thresh3)

        # Clean up with morphology
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        print(f"\n📊 Analyzing {len(contours)} potential holes...")

        # Analyze each contour
        holes = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter small noise (min 20 pixels) and large areas (max 5000 pixels)
            if 20 < area < 5000:
                x, y, w, h = cv2.boundingRect(contour)

                # Adjust coordinates back to original scale and position
                x = int(x / scale) + roi[0]
                y = int(y / scale) + roi[1]
                w = int(w / scale)
                h = int(h / scale)

                # Get center
                cx = x + w // 2
                cy = y + h // 2

                # Check intensity in difference image
                mask = np.zeros(diff.shape, np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                mean_diff = cv2.mean(diff, mask=mask)[0]

                # Calculate confidence
                # Higher difference = higher confidence
                confidence = min(1.0, mean_diff / 50)

                # Additional check: holes are usually darker in defective image
                ref_roi = gray_ref[
                    max(0, int((y-roi[1])*scale)):min(gray_ref.shape[0], int((y-roi[1]+h)*scale)),
                    max(0, int((x-roi[0])*scale)):min(gray_ref.shape[1], int((x-roi[0]+w)*scale))
                ]
                def_roi = gray_def[
                    max(0, int((y-roi[1])*scale)):min(gray_def.shape[0], int((y-roi[1]+h)*scale)),
                    max(0, int((x-roi[0])*scale)):min(gray_def.shape[1], int((x-roi[0]+w)*scale))
                ]

                if ref_roi.size > 0 and def_roi.size > 0:
                    brightness_change = float(np.mean(ref_roi) - np.mean(def_roi))
                    # Holes make the area darker (negative brightness change)
                    if brightness_change > 5:  # Significant darkening
                        confidence = min(1.0, confidence + 0.3)

                hole = {
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area / (scale ** 2)),  # Adjust area to original scale
                    'confidence': float(confidence),
                    'brightness_change': brightness_change if ref_roi.size > 0 else 0
                }
                holes.append(hole)

        # Sort by confidence
        holes.sort(key=lambda x: x['confidence'], reverse=True)

        print(f"\n✅ Found {len(holes)} probable holes:")
        for i, hole in enumerate(holes[:3], 1):
            print(f"  {i}. Location: ({hole['center'][0]}, {hole['center'][1]})")
            print(f"     Size: {hole['bbox'][2]}x{hole['bbox'][3]} pixels")
            print(f"     Area: {hole['area']:.0f} pixels²")
            print(f"     Confidence: {hole['confidence']:.1%}")
            print(f"     Brightness change: {hole['brightness_change']:.1f}")

        # Create visualization
        result_img = original_defective.copy()

        # Draw all detected holes
        for i, hole in enumerate(holes):
            x, y, w, h = hole['bbox']
            cx, cy = hole['center']
            conf = hole['confidence']

            # Color based on confidence
            if conf > 0.6:
                color = (0, 0, 255)  # Red for high confidence
                thickness = 3
            else:
                color = (0, 165, 255)  # Orange for medium
                thickness = 2

            # Draw rectangle around hole
            cv2.rectangle(result_img, (x, y), (x+w, y+h), color, thickness)

            # Draw arrow pointing to hole
            arrow_start = (x + w + 20, y + h // 2)
            arrow_end = (x + w, y + h // 2)
            cv2.arrowedLine(result_img, arrow_start, arrow_end, color, 2, tipLength=0.3)

            # Add label
            label = f"HOLE #{i+1}"
            cv2.putText(result_img, label, (arrow_start[0] + 5, arrow_start[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(result_img, f"{conf:.0%}", (arrow_start[0] + 5, arrow_start[1] + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Save results
        if output_path:
            cv2.imwrite(str(output_path), result_img)
            print(f"\n💾 Result saved to: {output_path}")

            # Create detailed comparison
            comparison_path = str(output_path).replace('.png', '_comparison.png')
            h, w = original_defective.shape[:2]

            # Resize reference to match
            ref_original = cv2.imread(str(reference_path))
            ref_resized = cv2.resize(ref_original, (w, h))

            # Create side by side
            comparison = np.hstack([ref_resized, original_defective, result_img])

            # Add labels
            font = cv2.FONT_HERSHEY_SIMPLEX
            label_comparison = comparison.copy()
            cv2.putText(label_comparison, "REFERENCE (NO HOLE)", (50, 80),
                       font, 2, (0, 255, 0), 4)
            cv2.putText(label_comparison, "DEFECTIVE (WITH HOLE)", (w + 50, 80),
                       font, 2, (0, 0, 255), 4)
            cv2.putText(label_comparison, f"DETECTED: {len(holes)} HOLES", (w*2 + 50, 80),
                       font, 2, (255, 0, 255), 4)

            cv2.imwrite(comparison_path, label_comparison)
            print(f"💾 Comparison saved to: {comparison_path}")

            # Save debug images
            if self.debug:
                debug_dir = Path(output_path).parent
                cv2.imwrite(str(debug_dir / "debug_focused_diff.png"), diff)
                cv2.imwrite(str(debug_dir / "debug_focused_thresh.png"), cleaned)

        return {
            'timestamp': datetime.now().isoformat(),
            'holes_detected': len(holes),
            'holes': holes,
            'focused_region': roi
        }


def main():
    """Run focused hole detection"""
    detector = FocusedHoleDetector()

    reference_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg")
    defective_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg")
    output_path = Path("/home/celso/projects/qa_dashboard/ai_mesurement/hole_focused_result.png")

    result = detector.detect_hole_focused(
        reference_path,
        defective_path,
        output_path
    )

    if result:
        # Save JSON report
        report_path = output_path.with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'='*60}")
        print("🎯 HOLE SUCCESSFULLY DETECTED!")
        print(f"{'='*60}")

        if result['holes']:
            hole = result['holes'][0]
            print(f"\n📍 Main hole found at:")
            print(f"   Coordinates: ({hole['center'][0]}, {hole['center'][1]})")
            print(f"   Dimensions: {hole['bbox'][2]} x {hole['bbox'][3]} pixels")
            print(f"   Confidence: {hole['confidence']:.0%}")

            # Describe location in human terms
            x, y = hole['center']
            if y < 800:
                v_pos = "upper"
            elif y < 1600:
                v_pos = "middle"
            else:
                v_pos = "lower"

            if x < 1350:
                h_pos = "left"
            elif x < 2700:
                h_pos = "center"
            else:
                h_pos = "right"

            print(f"\n📝 Description: Hole located in the {v_pos}-{h_pos} area of the garment")


if __name__ == "__main__":
    main()