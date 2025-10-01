#!/usr/bin/env python3
"""
Detect the TRUE hole from prova.png in ant.jpg
Using targeted detection based on visual characteristics
"""

import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from hole_detection import GarmentHoleDetector


def detect_true_hole():
    """Find the actual hole shown in prova.png"""

    print("\n" + "="*70)
    print("🎯 DETECTING TRUE HOLE FROM PROVA.PNG")
    print("="*70)

    # Load both images
    ant = cv2.imread("../test_images_mesurements/ant.jpg")
    prova = cv2.imread("../test_images_mesurements/prova.png")

    if ant is None or prova is None:
        print("❌ Cannot load images")
        return

    print(f"\n📸 Image info:")
    print(f"   ant.jpg: {ant.shape[1]}x{ant.shape[0]} pixels")
    print(f"   prova.png: {prova.shape[1]}x{prova.shape[0]} pixels")

    # Analyze prova.png to understand hole characteristics
    print("\n🔍 Analyzing hole in prova.png...")

    # Convert to grayscale
    prova_gray = cv2.cvtColor(prova, cv2.COLOR_BGR2GRAY)

    # Find the darkest region (the hole)
    # Holes are typically darker than fabric
    mean_val = np.mean(prova_gray)
    std_val = np.std(prova_gray)
    threshold = mean_val - std_val

    _, hole_mask = cv2.threshold(prova_gray, threshold, 255, cv2.THRESH_BINARY_INV)

    # Find contour of the hole
    contours, _ = cv2.findContours(hole_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        hole_contour = max(contours, key=cv2.contourArea)
        hole_area = cv2.contourArea(hole_contour)
        print(f"   Hole characteristics:")
        print(f"   - Area: {hole_area:.0f} pixels")
        print(f"   - Dark threshold: {threshold:.0f}")

    # Now search in ant.jpg
    print("\n🔍 Searching for similar holes in ant.jpg...")

    # Method 1: Color-based detection (holes appear as dark spots)
    ant_gray = cv2.cvtColor(ant, cv2.COLOR_BGR2GRAY)

    # Use multiple detection methods
    detected_regions = []

    # 1. Dark spot detection
    print("\n   Method 1: Dark spot detection")

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(ant_gray, (5, 5), 0)

    # Find dark regions
    _, dark_mask = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY_INV)

    # Clean up with morphology
    kernel = np.ones((5, 5), np.uint8)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, kernel)

    # Find contours
    contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        # Scale the expected area based on image size difference
        scale_factor = ant.shape[0] / prova.shape[0]
        expected_area = hole_area * (scale_factor ** 2)

        # Look for holes of similar size (within 50% range)
        if expected_area * 0.2 < area < expected_area * 5:
            x, y, w, h = cv2.boundingRect(contour)
            center = (x + w//2, y + h//2)

            # Check aspect ratio (holes are roughly circular)
            aspect_ratio = float(w) / h if h > 0 else 0
            if 0.5 < aspect_ratio < 2.0:
                detected_regions.append({
                    'contour': contour,
                    'area': area,
                    'center': center,
                    'bbox': (x, y, w, h),
                    'method': 'dark_spot'
                })

    print(f"      Found {len(detected_regions)} candidates")

    # 2. Local contrast detection (holes have high contrast with surrounding)
    print("\n   Method 2: Local contrast detection")

    # Calculate local standard deviation
    window_size = 21
    pad = window_size // 2
    padded = cv2.copyMakeBorder(blurred, pad, pad, pad, pad, cv2.BORDER_REFLECT)

    local_std = np.zeros_like(ant_gray, dtype=np.float32)
    for i in range(ant_gray.shape[0]):
        for j in range(ant_gray.shape[1]):
            window = padded[i:i+window_size, j:j+window_size]
            local_std[i, j] = np.std(window)

    # Normalize
    local_std = (local_std / local_std.max() * 255).astype(np.uint8)

    # Find high contrast regions
    _, contrast_mask = cv2.threshold(local_std, 100, 255, cv2.THRESH_BINARY)

    # Combine with dark mask
    combined = cv2.bitwise_and(dark_mask, contrast_mask)

    # Find contours in combined mask
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if 500 < area < 10000:  # Reasonable size for a hole
            x, y, w, h = cv2.boundingRect(contour)
            center = (x + w//2, y + h//2)

            # Check if already detected
            is_duplicate = False
            for region in detected_regions:
                dist = np.sqrt((center[0] - region['center'][0])**2 +
                             (center[1] - region['center'][1])**2)
                if dist < 50:
                    is_duplicate = True
                    break

            if not is_duplicate:
                detected_regions.append({
                    'contour': contour,
                    'area': area,
                    'center': center,
                    'bbox': (x, y, w, h),
                    'method': 'contrast'
                })

    print(f"      Total candidates: {len(detected_regions)}")

    # 3. Use AI detector with low confidence
    print("\n   Method 3: AI detection (40% confidence)")

    # Create mask
    _, mask = cv2.threshold(ant_gray, 30, 255, cv2.THRESH_BINARY)

    detector = GarmentHoleDetector(
        pixels_per_cm=50.0,
        min_size='tiny',  # Detect all sizes
        use_ai=True,
        debug=False
    )

    if detector.use_ai:
        detector.ai_detector.set_confidence(0.4)  # Very low confidence

    holes = detector.detect_holes(ant, mask)

    if holes:
        print(f"      AI found {len(holes)} holes")
        for hole in holes:
            detected_regions.append({
                'contour': hole.contour,
                'area': hole.area_pixels,
                'center': hole.center,
                'bbox': hole.bbox,
                'method': 'ai'
            })

    # Visualize all detections
    print(f"\n📊 Total detections: {len(detected_regions)}")

    if detected_regions:
        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Original ant.jpg
        axes[0, 0].imshow(cv2.cvtColor(ant, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title("Original ant.jpg")
        axes[0, 0].axis('off')

        # Reference hole
        axes[0, 1].imshow(cv2.cvtColor(prova, cv2.COLOR_BGR2RGB))
        axes[0, 1].set_title("Reference hole (prova.png)")
        axes[0, 1].axis('off')

        # Dark regions mask
        axes[1, 0].imshow(dark_mask, cmap='gray')
        axes[1, 0].set_title("Dark regions detected")
        axes[1, 0].axis('off')

        # All detections
        result = ant.copy()
        colors = {
            'dark_spot': (0, 255, 0),   # Green
            'contrast': (255, 0, 0),     # Blue
            'ai': (0, 0, 255)            # Red
        }

        for i, region in enumerate(detected_regions):
            color = colors.get(region['method'], (255, 255, 255))
            cv2.drawContours(result, [region['contour']], -1, color, 2)

            # Add label
            cv2.putText(result, f"{i+1}", region['center'],
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        axes[1, 1].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1, 1].set_title(f"All detections ({len(detected_regions)} found)")
        axes[1, 1].axis('off')

        plt.suptitle("Hole Detection Analysis", fontsize=16)
        plt.tight_layout()
        plt.savefig("hole_detection_analysis.png", dpi=150, bbox_inches='tight')
        print(f"   📸 Visualization saved: hole_detection_analysis.png")

        # Also save annotated image
        cv2.imwrite("holes_detected.png", result)
        print(f"   📸 Annotated image saved: holes_detected.png")

        # Print top candidates
        print("\n🎯 Top hole candidates:")
        for i, region in enumerate(detected_regions[:10]):
            print(f"   {i+1}. Method: {region['method']:10} "
                  f"Area: {region['area']:6.0f}px "
                  f"Position: {region['center']}")

    else:
        print("   ❌ No holes detected")

    print("\n" + "="*70)
    print("💡 TIP: The real hole should appear as a dark spot with high local contrast")
    print("     Check hole_detection_analysis.png for visual results")
    print("="*70 + "\n")


if __name__ == "__main__":
    detect_true_hole()