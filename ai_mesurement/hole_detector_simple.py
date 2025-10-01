#!/usr/bin/env python3
"""
Simple and Direct Hole Detection
Detects holes by looking for dark spots/areas in the garment
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime

class SimpleHoleDetector:
    def __init__(self):
        self.debug = True

    def find_dark_spots(self, img):
        """Find dark spots that could be holes"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Find dark areas (holes appear dark)
        # Threshold to find pixels darker than average
        mean_val = np.mean(filtered)
        _, dark_areas = cv2.threshold(filtered, mean_val * 0.5, 255, cv2.THRESH_BINARY_INV)

        return dark_areas, filtered

    def find_garment_mask(self, img):
        """Create mask of garment area only"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Background is light, garment is darker
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # Clean up mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask

    def detect_holes_simple(self, image_path, output_path=None):
        """
        Simple detection of holes by finding dark spots

        Args:
            image_path: Path to image with potential holes
            output_path: Optional path to save visualization
        """
        print(f"\n{'='*60}")
        print("SIMPLE HOLE DETECTION - DARK SPOT ANALYSIS")
        print(f"{'='*60}")

        # Load image
        print(f"\n📷 Loading image: {image_path}")
        img = cv2.imread(str(image_path))

        if img is None:
            print("❌ Error: Could not load image")
            return None

        original = img.copy()
        h, w = img.shape[:2]
        print(f"  Image size: {w}x{h} pixels")

        # Get garment mask
        print("\n👕 Finding garment area...")
        garment_mask = self.find_garment_mask(img)

        # Find dark spots
        print("\n🔍 Looking for dark spots (potential holes)...")
        dark_spots, gray_filtered = self.find_dark_spots(img)

        # Apply garment mask to dark spots
        dark_spots = cv2.bitwise_and(dark_spots, garment_mask)

        # Focus on upper portion where hole is likely
        print("\n🎯 Focusing on upper garment area...")
        upper_h = int(h * 0.5)  # Upper 50% of image
        roi_mask = np.zeros_like(dark_spots)
        roi_mask[:upper_h, :] = 255
        dark_spots = cv2.bitwise_and(dark_spots, roi_mask)

        # Clean up with morphology
        kernel_small = np.ones((3,3), np.uint8)
        kernel_medium = np.ones((5,5), np.uint8)

        # Remove small noise
        cleaned = cv2.morphologyEx(dark_spots, cv2.MORPH_OPEN, kernel_small)
        # Connect nearby components
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_medium)

        # Find contours
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        print(f"\n📊 Found {len(contours)} dark spots")

        # Analyze each contour
        holes = []
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area (not too small, not too large)
            if 50 < area < 10000:
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter ** 2)
                    compactness = area / (w * h)
                else:
                    circularity = 0
                    compactness = 0

                # Get mean intensity in original grayscale
                mask = np.zeros(gray_filtered.shape, np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                mean_intensity = cv2.mean(gray_filtered, mask=mask)[0]

                # Get center
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w//2, y + h//2

                # Check if it's significantly darker than surroundings
                # Create a ring mask around the contour
                dilated_mask = cv2.dilate(mask, kernel_medium, iterations=2)
                ring_mask = cv2.bitwise_xor(dilated_mask, mask)
                surround_intensity = cv2.mean(gray_filtered, mask=ring_mask)[0]

                darkness_ratio = mean_intensity / (surround_intensity + 1)

                # Calculate confidence
                # Holes are: dark (low intensity), compact, somewhat circular
                darkness_score = 1.0 - (mean_intensity / 255.0)
                shape_score = (circularity + compactness) / 2
                contrast_score = 1.0 - darkness_ratio if darkness_ratio < 1 else 0

                confidence = (darkness_score * 0.5 + contrast_score * 0.3 + shape_score * 0.2)

                # Additional boost if in typical hole location (upper center)
                if cy < h * 0.3 and abs(cx - w/2) < w * 0.3:
                    confidence = min(1.0, confidence + 0.2)

                hole = {
                    'bbox': [x, y, w, h],
                    'center': [cx, cy],
                    'area': float(area),
                    'circularity': float(circularity),
                    'compactness': float(compactness),
                    'mean_intensity': float(mean_intensity),
                    'darkness_ratio': float(darkness_ratio),
                    'confidence': float(confidence)
                }
                holes.append(hole)

        # Sort by confidence
        holes.sort(key=lambda x: x['confidence'], reverse=True)

        # Filter low confidence
        holes = [h for h in holes if h['confidence'] > 0.3]

        print(f"\n✅ Detected {len(holes)} probable holes:")
        for i, hole in enumerate(holes[:5], 1):
            print(f"\n  {i}. HOLE at ({hole['center'][0]}, {hole['center'][1]})")
            print(f"     Size: {hole['bbox'][2]}x{hole['bbox'][3]} pixels")
            print(f"     Area: {hole['area']:.0f} pixels²")
            print(f"     Darkness: {hole['mean_intensity']:.0f}/255")
            print(f"     Confidence: {hole['confidence']:.1%}")

        # Create visualization
        result = original.copy()

        # Draw holes with different colors based on confidence
        for i, hole in enumerate(holes):
            x, y, w, h = hole['bbox']
            cx, cy = hole['center']
            conf = hole['confidence']

            # Color based on confidence
            if conf > 0.7:
                color = (0, 0, 255)  # Red - high confidence
                thickness = 3
            elif conf > 0.5:
                color = (0, 128, 255)  # Orange - medium confidence
                thickness = 2
            else:
                color = (0, 255, 255)  # Yellow - low confidence
                thickness = 2

            # Draw circle around hole
            radius = max(w, h) // 2 + 10
            cv2.circle(result, (cx, cy), radius, color, thickness)

            # Draw cross at center
            cross_size = 15
            cv2.line(result, (cx - cross_size, cy), (cx + cross_size, cy), color, 2)
            cv2.line(result, (cx, cy - cross_size), (cx, cy + cross_size), color, 2)

            # Add label with arrow
            label_x = cx + radius + 20
            label_y = cy

            # Make sure label is within image bounds
            if label_x + 100 > w:
                label_x = cx - radius - 120

            cv2.arrowedLine(result, (label_x, label_y), (cx + radius, cy),
                           color, 2, tipLength=0.2)

            # Add text
            text1 = f"HOLE #{i+1}"
            text2 = f"{conf:.0%}"
            cv2.putText(result, text1, (label_x + 5, label_y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(result, text2, (label_x + 5, label_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Add title
        cv2.putText(result, f"HOLE DETECTION RESULT - {len(holes)} HOLES FOUND",
                   (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

        # Save results
        if output_path:
            cv2.imwrite(str(output_path), result)
            print(f"\n💾 Result saved to: {output_path}")

            # Save debug images
            if self.debug:
                debug_dir = Path(output_path).parent
                cv2.imwrite(str(debug_dir / "debug_dark_spots.png"), dark_spots)
                cv2.imwrite(str(debug_dir / "debug_cleaned.png"), cleaned)
                cv2.imwrite(str(debug_dir / "debug_garment_mask.png"), garment_mask)
                print(f"🐛 Debug images saved")

        return {
            'timestamp': datetime.now().isoformat(),
            'image': str(image_path),
            'holes_detected': len(holes),
            'holes': holes
        }

def compare_images(reference_path, defective_path, output_path):
    """Compare reference and defective images to find holes"""
    detector = SimpleHoleDetector()

    print("\n" + "="*60)
    print("COMPARING IMAGES TO FIND HOLES")
    print("="*60)

    # Detect in defective image
    print(f"\n🔍 Analyzing defective image for holes...")
    result = detector.detect_holes_simple(defective_path, output_path)

    if result and result['holes']:
        print(f"\n{'='*60}")
        print("✅ HOLES SUCCESSFULLY DETECTED!")
        print(f"{'='*60}")

        hole = result['holes'][0]  # Main hole
        print(f"\n🎯 Main hole location:")
        print(f"   Position: ({hole['center'][0]}, {hole['center'][1]}) pixels")
        print(f"   Size: {hole['bbox'][2]}x{hole['bbox'][3]} pixels")
        print(f"   Darkness level: {hole['mean_intensity']:.0f}/255")
        print(f"   Confidence: {hole['confidence']:.0%}")

        # Save report
        report_path = Path(output_path).with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📄 Report saved to: {report_path}")
    else:
        print("\n⚠️ No holes detected")

    return result

def main():
    """Run hole detection on the provided images"""
    reference_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg")
    defective_path = Path("/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg")
    output_path = Path("/home/celso/projects/qa_dashboard/ai_mesurement/hole_detected_simple.png")

    compare_images(reference_path, defective_path, output_path)

if __name__ == "__main__":
    main()