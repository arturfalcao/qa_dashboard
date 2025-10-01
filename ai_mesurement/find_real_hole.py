#!/usr/bin/env python3
"""
Find the real hole shown in prova.png within ant.jpg
Adjusted detection for real fabric defects
"""

import cv2
import numpy as np
from pathlib import Path

# Import our detectors
from hole_detection import GarmentHoleDetector
from zero_shot_defect_detector import ZeroShotDefectDetector


def find_specific_hole():
    """Find the real hole from prova.png in ant.jpg"""

    print("\n" + "="*70)
    print("🔍 SEARCHING FOR REAL HOLE (from prova.png)")
    print("="*70)

    # First, let's analyze prova.png to understand the hole
    print("\n📸 Analyzing reference hole (prova.png)...")
    prova = cv2.imread("../test_images_mesurements/prova.png")
    if prova is not None:
        print(f"   Reference image size: {prova.shape[1]}x{prova.shape[0]}")

        # Analyze the hole characteristics
        gray_prova = cv2.cvtColor(prova, cv2.COLOR_BGR2GRAY)

        # Find dark regions (the hole)
        _, thresh = cv2.threshold(gray_prova, 50, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            print(f"   Hole area in reference: ~{area} pixels")

            # Get hole color characteristics
            hole_mask = np.zeros(gray_prova.shape, np.uint8)
            cv2.drawContours(hole_mask, [largest], -1, 255, -1)
            hole_pixels = prova[hole_mask > 0]
            if len(hole_pixels) > 0:
                avg_color = np.mean(hole_pixels, axis=0)
                print(f"   Hole avg color (BGR): {avg_color.astype(int)}")

    print("\n🎯 Now searching in ant.jpg...")

    # Load the main image
    image_path = "../test_images_mesurements/ant.jpg"
    image = cv2.imread(image_path)
    if image is None:
        print("❌ Cannot load ant.jpg")
        return

    print(f"   Image size: {image.shape[1]}x{image.shape[0]}")

    # Method 1: Traditional CV with lower thresholds
    print("\n📊 Method 1: Traditional CV (adjusted for real holes)")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Look for dark spots (holes appear darker)
    # Use adaptive thresholding for better results
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 10
    )

    # Clean up noise
    kernel = np.ones((3,3), np.uint8)
    cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours by size and circularity
    hole_candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)

        # Looking for medium-sized dark regions
        if 100 < area < 5000:  # Adjust based on image scale
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)

                # Holes tend to be somewhat circular
                if circularity > 0.3:
                    x, y, w, h = cv2.boundingRect(contour)

                    # Check if it's actually dark inside
                    roi = gray[y:y+h, x:x+w]
                    if roi.size > 0:
                        avg_intensity = np.mean(roi)

                        # Holes are darker than surrounding fabric
                        if avg_intensity < 100:  # Dark region
                            hole_candidates.append({
                                'contour': contour,
                                'area': area,
                                'circularity': circularity,
                                'intensity': avg_intensity,
                                'center': (x + w//2, y + h//2)
                            })

    print(f"   Found {len(hole_candidates)} potential holes")

    # Sort by likelihood (combination of circularity and darkness)
    hole_candidates.sort(key=lambda x: x['circularity'] * (100 - x['intensity']), reverse=True)

    # Show top candidates
    for i, candidate in enumerate(hole_candidates[:5]):
        print(f"   Candidate {i+1}: area={candidate['area']:.0f}px, "
              f"circ={candidate['circularity']:.2f}, "
              f"intensity={candidate['intensity']:.1f}, "
              f"pos={candidate['center']}")

    # Method 2: Use AI with adjusted parameters
    print("\n📊 Method 2: Zero-shot AI (adjusted confidence)")

    # Create simple mask
    _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    # Try different confidence levels
    for confidence in [0.5, 0.6, 0.7]:
        print(f"\n   Testing with {confidence*100:.0f}% confidence...")

        detector = GarmentHoleDetector(
            pixels_per_cm=50.0,
            min_size='small',  # Lower threshold to catch real hole
            use_ai=True,
            debug=False
        )

        if detector.use_ai:
            detector.ai_detector.set_confidence(confidence)

        holes = detector.detect_holes(image, mask)

        if holes:
            print(f"   ✅ Found {len(holes)} holes!")
            for j, hole in enumerate(holes[:3]):
                print(f"      Hole {j+1}: {hole.type}, "
                      f"{hole.area_cm2:.2f}cm², "
                      f"pos={hole.center}")
            break
        else:
            print(f"   ❌ No holes detected")

    # Method 3: Template matching
    print("\n📊 Method 3: Template Matching with prova.png")

    if prova is not None:
        # Resize template to different scales
        scales = [0.5, 0.75, 1.0, 1.25, 1.5]
        best_match = None
        best_score = 0

        for scale in scales:
            resized = cv2.resize(prova, None, fx=scale, fy=scale)

            # Try template matching
            if resized.shape[0] < image.shape[0] and resized.shape[1] < image.shape[1]:
                result = cv2.matchTemplate(image, resized, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    h, w = resized.shape[:2]
                    best_match = {
                        'score': max_val,
                        'location': max_loc,
                        'size': (w, h),
                        'scale': scale
                    }

        if best_match and best_match['score'] > 0.5:
            print(f"   ✅ Template match found!")
            print(f"      Score: {best_match['score']:.2f}")
            print(f"      Location: {best_match['location']}")
            print(f"      Scale: {best_match['scale']}")

            # Draw on image
            x, y = best_match['location']
            w, h = best_match['size']
            output = image.copy()
            cv2.rectangle(output, (x, y), (x+w, y+h), (0, 255, 0), 3)
            cv2.putText(output, f"HOLE ({best_match['score']:.2f})",
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imwrite("hole_found.png", output)
            print(f"   📸 Result saved to hole_found.png")
        else:
            print(f"   ❌ No good template match (best score: {best_score:.2f})")

    # Save visualization of candidates
    if hole_candidates:
        viz = image.copy()
        for i, candidate in enumerate(hole_candidates[:5]):
            cv2.drawContours(viz, [candidate['contour']], -1, (0, 255, 0), 2)
            cv2.putText(viz, f"#{i+1}", candidate['center'],
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imwrite("hole_candidates.png", viz)
        print(f"\n📸 Candidates visualization saved to hole_candidates.png")

    print("\n" + "="*70)


if __name__ == "__main__":
    find_specific_hole()