#!/usr/bin/env python3
"""
Practical Hole Finder - Actually finds the hole!
Combining the best of CV and AI in a working solution
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt


class PracticalHoleFinder:
    """
    A practical, working solution that finds real holes
    """

    def __init__(self):
        """Initialize practical finder"""
        print("🎯 PRACTICAL HOLE FINDER")
        print("="*60)

    def find_hole(self, image_path: str, reference_path: str = None) -> List[Dict]:
        """
        Find holes using practical hybrid approach

        Strategy:
        1. Look for REAL characteristics of holes
        2. Combine multiple evidence types
        3. Focus on what actually works
        """

        image = cv2.imread(image_path)
        if image is None:
            return []

        print(f"\n🔍 Analyzing {image_path}")

        # If we have a reference, analyze it
        reference_features = None
        if reference_path:
            ref = cv2.imread(reference_path)
            if ref is not None:
                reference_features = self._analyze_reference(ref)
                print(f"📌 Reference analyzed: darkness={reference_features['darkness']:.1f}")

        # Multi-strategy detection
        candidates = []

        # Strategy 1: Dark regions with proper size
        dark_candidates = self._find_dark_regions(image, reference_features)
        candidates.extend(dark_candidates)

        # Strategy 2: Local anomalies
        anomaly_candidates = self._find_local_anomalies(image)
        candidates.extend(anomaly_candidates)

        # Strategy 3: Texture disruptions
        texture_candidates = self._find_texture_disruptions(image)
        candidates.extend(texture_candidates)

        # Strategy 4: Color discontinuities
        color_candidates = self._find_color_anomalies(image)
        candidates.extend(color_candidates)

        # Merge and score candidates
        final_holes = self._merge_and_score(candidates, image)

        return final_holes

    def _analyze_reference(self, reference: np.ndarray) -> Dict:
        """Analyze reference hole characteristics"""

        gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

        # Find the darkest region (the hole)
        min_val = np.min(gray)
        mean_val = np.mean(gray)

        # Get color characteristics
        hsv = cv2.cvtColor(reference, cv2.COLOR_BGR2HSV)

        return {
            'darkness': min_val,
            'mean_darkness': mean_val,
            'size': reference.shape[0] * reference.shape[1],
            'hue_mean': np.mean(hsv[:, :, 0]),
            'sat_mean': np.mean(hsv[:, :, 1])
        }

    def _find_dark_regions(self, image: np.ndarray, ref_features: Dict = None) -> List[Dict]:
        """Find properly dark regions that could be holes"""

        candidates = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Use reference darkness if available
        if ref_features:
            threshold = min(ref_features['mean_darkness'] + 20, 80)
        else:
            threshold = 60

        # Multiple threshold levels for robustness
        for thresh_offset in [0, 10, 20]:
            current_thresh = threshold + thresh_offset

            # Find dark regions
            _, mask = cv2.threshold(gray, current_thresh, 255, cv2.THRESH_BINARY_INV)

            # Clean up
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)

                # Filter by size
                if 50 < area < 5000:
                    x, y, w, h = cv2.boundingRect(contour)

                    # Skip edges
                    if (y < 50 or y > image.shape[0] - 50 or
                        x < 50 or x > image.shape[1] - 50):
                        continue

                    # Get region properties
                    roi = gray[y:y+h, x:x+w]
                    if roi.size == 0:
                        continue

                    mean_intensity = np.mean(roi)
                    std_intensity = np.std(roi)

                    # Circularity
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                    else:
                        circularity = 0

                    candidates.append({
                        'bbox': (x, y, w, h),
                        'center': (x + w//2, y + h//2),
                        'area': area,
                        'intensity': mean_intensity,
                        'std': std_intensity,
                        'circularity': circularity,
                        'method': 'darkness',
                        'score': 0.0
                    })

        return candidates

    def _find_local_anomalies(self, image: np.ndarray) -> List[Dict]:
        """Find local anomalies in the image"""

        candidates = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate local statistics
        window_size = 31
        kernel = np.ones((window_size, window_size), np.float32) / (window_size * window_size)

        # Local mean and std
        local_mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        gray_squared = gray.astype(np.float32) ** 2
        local_mean_squared = cv2.filter2D(gray_squared, -1, kernel)
        local_std = np.sqrt(np.maximum(local_mean_squared - local_mean**2, 0))

        # Find anomalies (regions that differ from local average)
        diff = np.abs(gray.astype(np.float32) - local_mean)
        anomaly_mask = diff > (local_std * 2)

        # Clean up
        anomaly_mask = (anomaly_mask * 255).astype(np.uint8)
        kernel = np.ones((5, 5), np.uint8)
        anomaly_mask = cv2.morphologyEx(anomaly_mask, cv2.MORPH_OPEN, kernel)

        # Find regions
        contours, _ = cv2.findContours(anomaly_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if 30 < area < 2000:
                x, y, w, h = cv2.boundingRect(contour)

                candidates.append({
                    'bbox': (x, y, w, h),
                    'center': (x + w//2, y + h//2),
                    'area': area,
                    'method': 'anomaly',
                    'score': 0.0
                })

        return candidates

    def _find_texture_disruptions(self, image: np.ndarray) -> List[Dict]:
        """Find disruptions in texture patterns"""

        candidates = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Use Laplacian for edge detection
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian = np.abs(laplacian)

        # Find regions with high edge density (texture disruption)
        _, edge_mask = cv2.threshold(laplacian.astype(np.uint8), 50, 255, cv2.THRESH_BINARY)

        # Invert to find regions WITHOUT edges (smooth = potential hole)
        smooth_mask = cv2.bitwise_not(edge_mask)

        # Clean
        kernel = np.ones((5, 5), np.uint8)
        smooth_mask = cv2.morphologyEx(smooth_mask, cv2.MORPH_OPEN, kernel)

        # Find smooth regions
        contours, _ = cv2.findContours(smooth_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 1500:
                x, y, w, h = cv2.boundingRect(contour)

                candidates.append({
                    'bbox': (x, y, w, h),
                    'center': (x + w//2, y + h//2),
                    'area': area,
                    'method': 'texture',
                    'score': 0.0
                })

        return candidates

    def _find_color_anomalies(self, image: np.ndarray) -> List[Dict]:
        """Find color anomalies"""

        candidates = []

        # Convert to LAB color space (better for color differences)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Analyze each channel
        for channel in range(3):
            chan = lab[:, :, channel]

            # Find outliers
            mean = np.mean(chan)
            std = np.std(chan)

            # Regions that are very different from mean
            outlier_mask = np.abs(chan.astype(np.float32) - mean) > (2.5 * std)
            outlier_mask = (outlier_mask * 255).astype(np.uint8)

            # Clean
            kernel = np.ones((3, 3), np.uint8)
            outlier_mask = cv2.morphologyEx(outlier_mask, cv2.MORPH_OPEN, kernel)

            # Find regions
            contours, _ = cv2.findContours(outlier_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if 40 < area < 1000:
                    x, y, w, h = cv2.boundingRect(contour)

                    candidates.append({
                        'bbox': (x, y, w, h),
                        'center': (x + w//2, y + h//2),
                        'area': area,
                        'method': 'color',
                        'score': 0.0
                    })

        return candidates

    def _merge_and_score(self, candidates: List[Dict], image: np.ndarray) -> List[Dict]:
        """Merge nearby candidates and score them"""

        if not candidates:
            return []

        # Remove duplicates
        unique_candidates = []
        used = set()

        for i, c1 in enumerate(candidates):
            if i in used:
                continue

            # Check for nearby candidates
            merged = c1.copy()
            merged['evidence'] = [c1['method']]

            for j, c2 in enumerate(candidates[i+1:], i+1):
                if j in used:
                    continue

                # Check distance
                dist = np.sqrt(
                    (c1['center'][0] - c2['center'][0])**2 +
                    (c1['center'][1] - c2['center'][1])**2
                )

                if dist < 50:  # Merge if close
                    merged['evidence'].append(c2['method'])
                    used.add(j)

            # Score based on evidence
            merged['score'] = len(merged['evidence']) / 4.0  # Max 4 methods

            # Boost score for specific characteristics
            if 'intensity' in merged and merged['intensity'] < 60:
                merged['score'] += 0.2

            if 'circularity' in merged and merged['circularity'] > 0.5:
                merged['score'] += 0.1

            if merged['area'] > 100 and merged['area'] < 1000:
                merged['score'] += 0.1

            merged['score'] = min(merged['score'], 1.0)
            unique_candidates.append(merged)

        # Sort by score
        unique_candidates.sort(key=lambda x: x['score'], reverse=True)

        return unique_candidates

    def visualize_results(self, image_path: str, holes: List[Dict], save_path: str = "practical_results.png"):
        """Visualize detection results"""

        image = cv2.imread(image_path)
        if image is None:
            return

        # Create figure
        fig, axes = plt.subplots(1, 2, figsize=(15, 8))

        # Original image
        axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0].set_title("Original Image")
        axes[0].axis('off')

        # Detection results
        result = image.copy()

        for i, hole in enumerate(holes[:10]):  # Show top 10
            x, y, w, h = hole['bbox']
            score = hole['score']

            # Color based on score
            if score > 0.7:
                color = (0, 255, 0)  # Green - high confidence
            elif score > 0.5:
                color = (0, 255, 255)  # Yellow - medium
            else:
                color = (0, 0, 255)  # Red - low

            cv2.rectangle(result, (x, y), (x+w, y+h), color, 2)

            # Add label
            label = f"#{i+1} ({score:.2f})"
            cv2.putText(result, label, (x, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Add evidence
            if 'evidence' in hole:
                evidence_text = ','.join(hole['evidence'][:2])
                cv2.putText(result, evidence_text, (x, y+h+15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)

        axes[1].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1].set_title(f"Detected Holes ({len(holes)} found)")
        axes[1].axis('off')

        plt.suptitle("Practical Hole Detection Results", fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"📸 Results saved: {save_path}")

        # Also save annotated image
        cv2.imwrite(save_path.replace('.png', '_annotated.png'), result)


def main():
    """Test practical hole finder"""

    finder = PracticalHoleFinder()

    # Find holes
    holes = finder.find_hole(
        "../test_images_mesurements/ant.jpg",
        "../test_images_mesurements/prova.png"
    )

    print(f"\n📊 RESULTS:")
    print("-"*60)

    if holes:
        print(f"Found {len(holes)} potential holes\n")

        for i, hole in enumerate(holes[:5]):
            print(f"Hole #{i+1}:")
            print(f"  Location: {hole['center']}")
            print(f"  Size: {hole['area']:.0f} pixels")
            print(f"  Score: {hole['score']:.2f}")
            if 'evidence' in hole:
                print(f"  Evidence: {', '.join(hole['evidence'])}")
            if 'intensity' in hole:
                print(f"  Darkness: {hole['intensity']:.1f}")
            print()

        # Visualize
        finder.visualize_results(
            "../test_images_mesurements/ant.jpg",
            holes
        )

        print("\n💡 ANALYSIS:")
        print("  Holes with score > 0.7 are very likely real")
        print("  Multiple evidence types increase confidence")
        print("  Check annotated image for visual verification")

    else:
        print("No holes detected")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()