#!/usr/bin/env python3
"""
Universal Defect Detector - Final Version
Optimized for detecting even the smallest defects by comparing golden vs test images
Works with any apparel type
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class UniversalDefectDetectorFinal:
    """Final version - extremely sensitive defect detection"""

    def __init__(self):
        self.min_defect_area = 20  # Very small minimum area
        self.debug = True

    def detect_defects(self, golden_path, test_path, output_path=None):
        """
        Main detection method - compares golden vs test image

        Args:
            golden_path: Path to reference image (no defects)
            test_path: Path to test image (may have defects)
            output_path: Optional visualization output path

        Returns:
            Dict with detection results
        """
        print(f"\n{'='*60}")
        print("UNIVERSAL DEFECT DETECTOR - FINAL VERSION")
        print(f"{'='*60}")

        # Load images
        print(f"\n📷 Loading images...")
        golden = cv2.imread(str(golden_path))
        test = cv2.imread(str(test_path))

        if golden is None or test is None:
            print("❌ Error loading images")
            return None

        h, w = golden.shape[:2]
        print(f"  Image size: {w}x{h}")

        # Ensure same size
        if golden.shape != test.shape:
            test = cv2.resize(test, (golden.shape[1], golden.shape[0]))

        # Convert to grayscale for initial alignment check
        gray_golden = cv2.cvtColor(golden, cv2.COLOR_BGR2GRAY)
        gray_test = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Simple alignment using template matching for small shifts
        print("\n🎯 Aligning images...")
        aligned_test = self.align_simple(golden, test)

        # Multiple detection strategies
        print("\n🔍 Running multi-strategy defect detection...")

        defects = []

        # Strategy 1: Direct pixel difference
        print("  1️⃣ Direct pixel difference...")
        defects1 = self.detect_by_pixel_diff(golden, aligned_test)
        defects.extend(defects1)

        # Strategy 2: Local texture analysis
        print("  2️⃣ Local texture analysis...")
        defects2 = self.detect_by_texture(golden, aligned_test)
        defects.extend(defects2)

        # Strategy 3: Color channel analysis
        print("  3️⃣ Color channel analysis...")
        defects3 = self.detect_by_color_channels(golden, aligned_test)
        defects.extend(defects3)

        # Strategy 4: Edge-based detection
        print("  4️⃣ Edge-based detection...")
        defects4 = self.detect_by_edges(golden, aligned_test)
        defects.extend(defects4)

        # Remove duplicates
        defects = self.remove_duplicates(defects)

        # Sort by confidence
        defects.sort(key=lambda x: x['confidence'], reverse=True)

        print(f"\n✅ Total defects found: {len(defects)}")

        # Show top defects
        for i, defect in enumerate(defects[:5], 1):
            print(f"\n  {i}. Defect at ({defect['center'][0]}, {defect['center'][1]})")
            print(f"     Method: {defect['method']}")
            print(f"     Size: {defect['bbox'][2]}x{defect['bbox'][3]} pixels")
            print(f"     Confidence: {defect['confidence']:.1%}")

        # Create visualization
        if output_path:
            self.visualize_results(golden, test, aligned_test, defects, output_path)

        # Return results
        return {
            'timestamp': datetime.now().isoformat(),
            'golden_image': str(golden_path),
            'test_image': str(test_path),
            'total_defects': len(defects),
            'defects': defects[:20]  # Top 20
        }

    def align_simple(self, img1, img2):
        """Simple alignment for small shifts"""
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # Find shift using phase correlation
        shift = cv2.phaseCorrelate(np.float32(gray1), np.float32(gray2))[0]

        # Apply shift
        M = np.float32([[1, 0, shift[0]], [0, 1, shift[1]]])
        aligned = cv2.warpAffine(img2, M, (img1.shape[1], img1.shape[0]))

        return aligned

    def detect_by_pixel_diff(self, golden, test):
        """Detection by direct pixel difference"""
        defects = []

        # Multiple color spaces
        # BGR difference
        diff_bgr = cv2.absdiff(golden, test)
        diff_gray = cv2.cvtColor(diff_bgr, cv2.COLOR_BGR2GRAY)

        # Apply very low threshold to catch small differences
        _, binary = cv2.threshold(diff_gray, 15, 255, cv2.THRESH_BINARY)

        # Clean up
        kernel = np.ones((3,3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_defect_area:
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2

                # Calculate mean difference
                mask = np.zeros(diff_gray.shape, np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                mean_diff = cv2.mean(diff_gray, mask=mask)[0]

                confidence = min(1.0, mean_diff / 50)

                defects.append({
                    'method': 'pixel_diff',
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area),
                    'confidence': float(confidence)
                })

        return defects

    def detect_by_texture(self, golden, test):
        """Detection by local texture analysis"""
        defects = []

        # Convert to grayscale
        gray_golden = cv2.cvtColor(golden, cv2.COLOR_BGR2GRAY)
        gray_test = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Divide image into blocks and compare
        block_size = 50
        h, w = gray_golden.shape

        for y in range(0, h - block_size, block_size // 2):
            for x in range(0, w - block_size, block_size // 2):
                # Extract blocks
                block_golden = gray_golden[y:y+block_size, x:x+block_size]
                block_test = gray_test[y:y+block_size, x:x+block_size]

                # Calculate histogram difference
                hist_golden = cv2.calcHist([block_golden], [0], None, [256], [0, 256])
                hist_test = cv2.calcHist([block_test], [0], None, [256], [0, 256])

                # Compare histograms
                diff = cv2.compareHist(hist_golden, hist_test, cv2.HISTCMP_BHATTACHARYYA)

                # If significant difference
                if diff > 0.3:  # Threshold for texture difference
                    confidence = min(1.0, diff)

                    defects.append({
                        'method': 'texture',
                        'bbox': [x, y, block_size, block_size],
                        'center': [x + block_size // 2, y + block_size // 2],
                        'area': float(block_size * block_size),
                        'confidence': float(confidence)
                    })

        return defects

    def detect_by_color_channels(self, golden, test):
        """Detection by analyzing individual color channels"""
        defects = []

        # Split channels
        b_g, g_g, r_g = cv2.split(golden)
        b_t, g_t, r_t = cv2.split(test)

        # Check each channel
        for channel_g, channel_t, channel_name in [(b_g, b_t, 'blue'),
                                                    (g_g, g_t, 'green'),
                                                    (r_g, r_t, 'red')]:
            diff = cv2.absdiff(channel_g, channel_t)

            # Threshold
            _, binary = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)

            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > self.min_defect_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    cx = x + w // 2
                    cy = y + h // 2

                    confidence = min(1.0, area / 1000)

                    defects.append({
                        'method': f'color_{channel_name}',
                        'bbox': [x, y, w, h],
                        'center': [cx, cy],
                        'area': float(area),
                        'confidence': float(confidence)
                    })

        return defects

    def detect_by_edges(self, golden, test):
        """Detection by edge analysis"""
        defects = []

        # Convert to grayscale
        gray_golden = cv2.cvtColor(golden, cv2.COLOR_BGR2GRAY)
        gray_test = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges_golden = cv2.Canny(gray_golden, 30, 100)
        edges_test = cv2.Canny(gray_test, 30, 100)

        # Find edge differences
        edge_diff = cv2.absdiff(edges_golden, edges_test)

        # Dilate to connect nearby edges
        kernel = np.ones((5,5), np.uint8)
        edge_diff = cv2.dilate(edge_diff, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(edge_diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_defect_area * 2:  # Slightly larger threshold for edges
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2

                confidence = min(1.0, area / 500)

                defects.append({
                    'method': 'edge',
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area),
                    'confidence': float(confidence)
                })

        return defects

    def remove_duplicates(self, defects):
        """Remove duplicate detections"""
        unique = []

        for defect in defects:
            is_duplicate = False
            cx, cy = defect['center']

            for existing in unique:
                ex, ey = existing['center']
                dist = np.sqrt((cx - ex)**2 + (cy - ey)**2)

                # If too close, consider duplicate
                if dist < 30:
                    is_duplicate = True
                    # Keep the one with higher confidence
                    if defect['confidence'] > existing['confidence']:
                        unique.remove(existing)
                        is_duplicate = False
                    break

            if not is_duplicate:
                unique.append(defect)

        return unique

    def visualize_results(self, golden, test, aligned, defects, output_path):
        """Create visualization of results"""
        img_h, img_w = test.shape[:2]

        # Mark defects
        marked = test.copy()

        # Draw each defect
        for i, defect in enumerate(defects[:10]):  # Top 10
            x, y, w, h = defect['bbox']
            cx, cy = defect['center']
            method = defect['method']
            conf = defect['confidence']

            # Color by method
            colors = {
                'pixel_diff': (0, 0, 255),      # Red
                'texture': (255, 0, 0),          # Blue
                'edge': (0, 255, 0),             # Green
            }

            color = colors.get(method.split('_')[0], (0, 255, 255))  # Default yellow

            # Draw rectangle
            cv2.rectangle(marked, (x, y), (x+w, y+h), color, 2)

            # Draw center
            cv2.circle(marked, (cx, cy), 3, color, -1)

            # Add text
            text = f"#{i+1} {method} ({conf:.0%})"
            cv2.putText(marked, text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX,
                       0.4, color, 1)

        # Create grid
        grid = np.zeros((img_h*2, img_w*2, 3), dtype=np.uint8)
        grid[:img_h, :img_w] = golden
        grid[:img_h, img_w:] = test
        grid[img_h:, :img_w] = aligned
        grid[img_h:, img_w:] = marked

        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(grid, "GOLDEN IMAGE", (10, 40), font, 1, (0, 255, 0), 2)
        cv2.putText(grid, "TEST IMAGE", (img_w+10, 40), font, 1, (0, 255, 255), 2)
        cv2.putText(grid, "ALIGNED TEST", (10, img_h+40), font, 1, (255, 255, 0), 2)
        cv2.putText(grid, f"DEFECTS: {len(defects)}", (img_w+10, img_h+40), font, 1, (0, 0, 255), 2)

        # Save
        cv2.imwrite(str(output_path), grid)
        print(f"\n💾 Visualization saved to: {output_path}")

        # Save marked only
        marked_path = str(output_path).replace('.png', '_marked.png')
        cv2.imwrite(marked_path, marked)
        print(f"💾 Marked image saved to: {marked_path}")


def main():
    """Test with provided images"""
    detector = UniversalDefectDetectorFinal()

    golden = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
    output = "/home/celso/projects/qa_dashboard/ai_mesurement/universal_final_result.png"

    result = detector.detect_defects(golden, test, output)

    if result:
        # Save report
        report_path = Path(output).with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'='*60}")
        print("🎯 DETECTION COMPLETE!")
        print(f"{'='*60}")
        print(f"✅ Found {result['total_defects']} potential defects")

        if result['defects']:
            defect = result['defects'][0]
            print(f"\n📍 Top defect location:")
            print(f"   Position: ({defect['center'][0]}, {defect['center'][1]})")
            print(f"   Detection method: {defect['method']}")
            print(f"   Confidence: {defect['confidence']:.1%}")


if __name__ == "__main__":
    main()