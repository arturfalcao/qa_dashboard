#!/usr/bin/env python3
"""
Generate heatmap visualizations of garment landmark detections.
Shows confidence levels and landmark density across the garment.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# Import the HRNet detector
from hrnet_landmark_detector import FashionLandmarkDetector


class LandmarkHeatmapGenerator:
    """Generate heatmap visualizations of landmark detections."""

    def __init__(self, model_path: str = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"):
        """Initialize the heatmap generator."""
        self.hrnet = FashionLandmarkDetector(model_path, device='cpu')

    def create_gaussian_heatmap(self, image_shape: Tuple, landmarks: List,
                                confidences: List, sigma: float = 20) -> np.ndarray:
        """Create a Gaussian heatmap from landmark positions."""
        h, w = image_shape[:2]
        heatmap = np.zeros((h, w), dtype=np.float32)

        for landmark, confidence in zip(landmarks, confidences):
            if landmark is not None and confidence > 0:
                x, y = landmark
                # Ensure coordinates are within bounds
                if 0 <= x < w and 0 <= y < h:
                    # Create a small Gaussian around this point
                    y_grid, x_grid = np.ogrid[:h, :w]
                    gaussian = np.exp(-((x_grid - x)**2 + (y_grid - y)**2) / (2 * sigma**2))
                    # Weight by confidence
                    heatmap += gaussian * confidence

        # Normalize heatmap
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        return heatmap

    def create_density_heatmap(self, image_shape: Tuple, landmarks: List,
                              grid_size: int = 50) -> np.ndarray:
        """Create a density-based heatmap showing landmark concentration."""
        h, w = image_shape[:2]
        density_map = np.zeros((h, w), dtype=np.float32)

        # Create grid
        grid_h = h // grid_size + 1
        grid_w = w // grid_size + 1
        grid = np.zeros((grid_h, grid_w))

        # Count landmarks in each grid cell
        for landmark in landmarks:
            if landmark is not None:
                x, y = landmark
                grid_x = min(x // grid_size, grid_w - 1)
                grid_y = min(y // grid_size, grid_h - 1)
                grid[grid_y, grid_x] += 1

        # Resize grid to image size with interpolation
        density_map = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)

        # Apply Gaussian smoothing for better visualization
        density_map = gaussian_filter(density_map, sigma=30)

        # Normalize
        if density_map.max() > 0:
            density_map = density_map / density_map.max()

        return density_map

    def create_confidence_regions(self, image_shape: Tuple, landmarks: List,
                                 confidences: List) -> np.ndarray:
        """Create regions showing confidence levels."""
        h, w = image_shape[:2]
        confidence_map = np.zeros((h, w, 3), dtype=np.float32)

        # Group landmarks by confidence levels
        high_conf = []  # > 0.7
        med_conf = []   # 0.4 - 0.7
        low_conf = []   # < 0.4

        for landmark, conf in zip(landmarks, confidences):
            if landmark is not None and conf > 0:
                if conf > 0.7:
                    high_conf.append(landmark)
                elif conf > 0.4:
                    med_conf.append(landmark)
                else:
                    low_conf.append(landmark)

        # Create color-coded regions
        for landmark in high_conf:
            cv2.circle(confidence_map, landmark, 30, (0, 1, 0), -1)  # Green for high
        for landmark in med_conf:
            cv2.circle(confidence_map, landmark, 25, (1, 1, 0), -1)  # Yellow for medium
        for landmark in low_conf:
            cv2.circle(confidence_map, landmark, 20, (1, 0, 0), -1)  # Red for low

        # Apply Gaussian blur for smooth regions
        confidence_map = cv2.GaussianBlur(confidence_map, (51, 51), 15)

        return confidence_map

    def create_body_part_heatmap(self, image_shape: Tuple, landmarks: List,
                                 category: str) -> np.ndarray:
        """Create heatmap showing different body parts/regions."""
        h, w = image_shape[:2]
        part_map = np.zeros((h, w, 3), dtype=np.float32)

        # Define color for each body part region (based on landmark indices)
        part_colors = {
            'collar_neckline': (range(0, 5), (1, 1, 0)),      # Yellow
            'shoulders': (range(5, 15), (0, 0, 1)),           # Blue
            'chest_torso': (range(15, 25), (0, 1, 1)),        # Cyan
            'sleeves': (range(25, 45), (1, 0, 1)),            # Magenta
            'hem_bottom': (range(45, 60), (1, 0.5, 0)),       # Orange
        }

        # Apply colors based on landmark positions
        for part_name, (indices, color) in part_colors.items():
            for idx in indices:
                if idx < len(landmarks) and landmarks[idx] is not None:
                    x, y = landmarks[idx]
                    cv2.circle(part_map, (x, y), 40, color, -1)

        # Smooth the map
        part_map = cv2.GaussianBlur(part_map, (61, 61), 20)

        return part_map

    def generate_heatmap(self, image_path: str, output_dir: str = "heatmap_results"):
        """Generate comprehensive heatmap visualizations."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # Detect landmarks
        print(f"Detecting landmarks for {image_path}...")
        result = self.hrnet.detect_landmarks(image, confidence_threshold=0.1)
        landmarks = result['landmarks']
        confidences = result['confidences']
        category = result['category']

        print(f"Detected {result['num_detected']} landmarks")

        # Create different heatmaps
        print("Creating heatmaps...")

        # 1. Gaussian confidence heatmap
        gaussian_heat = self.create_gaussian_heatmap((h, w), landmarks, confidences, sigma=30)

        # 2. Density heatmap
        density_heat = self.create_density_heatmap((h, w), landmarks, grid_size=50)

        # 3. Confidence regions
        conf_regions = self.create_confidence_regions((h, w), landmarks, confidences)

        # 4. Body part heatmap
        part_heat = self.create_body_part_heatmap((h, w), landmarks, category)

        # Create visualizations
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(image_path).stem

        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))

        # Original image
        axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('Original Image', fontsize=14, fontweight='bold')
        axes[0, 0].axis('off')

        # Gaussian heatmap overlay
        overlay1 = image.copy()
        heatmap_colored = plt.cm.jet(gaussian_heat)[:, :, :3]
        heatmap_bgr = (heatmap_colored * 255).astype(np.uint8)
        heatmap_bgr = cv2.cvtColor(heatmap_bgr, cv2.COLOR_RGB2BGR)
        overlay1 = cv2.addWeighted(overlay1, 0.6, heatmap_bgr, 0.4, 0)
        axes[0, 1].imshow(cv2.cvtColor(overlay1, cv2.COLOR_BGR2RGB))
        axes[0, 1].set_title('Confidence Heatmap', fontsize=14, fontweight='bold')
        axes[0, 1].axis('off')

        # Density heatmap
        axes[0, 2].imshow(density_heat, cmap='hot', interpolation='bilinear')
        axes[0, 2].set_title('Landmark Density', fontsize=14, fontweight='bold')
        axes[0, 2].axis('off')

        # Confidence regions overlay
        overlay2 = image.copy().astype(np.float32) / 255
        overlay2 = overlay2 * 0.5 + conf_regions * 0.5
        overlay2 = np.clip(overlay2, 0, 1)
        axes[1, 0].imshow(overlay2)
        axes[1, 0].set_title('Confidence Regions\n(Green=High, Yellow=Med, Red=Low)',
                           fontsize=14, fontweight='bold')
        axes[1, 0].axis('off')

        # Body part regions
        overlay3 = image.copy().astype(np.float32) / 255
        overlay3 = overlay3 * 0.5 + part_heat * 0.5
        overlay3 = np.clip(overlay3, 0, 1)
        axes[1, 1].imshow(overlay3)
        axes[1, 1].set_title('Body Part Regions', fontsize=14, fontweight='bold')
        axes[1, 1].axis('off')

        # Combined visualization with landmarks
        combined = image.copy()
        # Add heatmap
        heatmap_colored = plt.cm.plasma(gaussian_heat)[:, :, :3]
        heatmap_bgr = (heatmap_colored * 255).astype(np.uint8)
        heatmap_bgr = cv2.cvtColor(heatmap_bgr, cv2.COLOR_RGB2BGR)
        combined = cv2.addWeighted(combined, 0.5, heatmap_bgr, 0.5, 0)

        # Add landmark points
        for landmark, conf in zip(landmarks, confidences):
            if landmark is not None and conf > 0.3:
                color = (0, int(255 * conf), int(255 * (1 - conf)))
                cv2.circle(combined, landmark, 3, color, -1)

        axes[1, 2].imshow(cv2.cvtColor(combined, cv2.COLOR_BGR2RGB))
        axes[1, 2].set_title(f'Combined View\n({result["num_detected"]} landmarks)',
                           fontsize=14, fontweight='bold')
        axes[1, 2].axis('off')

        # Add main title
        fig.suptitle(f'Landmark Detection Heatmap Analysis - {category.upper()}',
                    fontsize=16, fontweight='bold')

        # Save figure
        output_path = output_dir / f"{base_name}_heatmap_analysis.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved heatmap analysis to {output_path}")

        # Save individual heatmaps
        # Save confidence heatmap
        conf_output = output_dir / f"{base_name}_confidence_heatmap.jpg"
        cv2.imwrite(str(conf_output), overlay1)
        print(f"Saved confidence heatmap to {conf_output}")

        # Save density heatmap
        density_output = output_dir / f"{base_name}_density_heatmap.jpg"
        density_vis = (density_heat * 255).astype(np.uint8)
        density_colored = cv2.applyColorMap(density_vis, cv2.COLORMAP_JET)
        cv2.imwrite(str(density_output), density_colored)
        print(f"Saved density heatmap to {density_output}")

        # Create statistics
        stats = {
            'total_landmarks': len(landmarks),
            'detected_landmarks': result['num_detected'],
            'high_confidence': sum(1 for c in confidences if c > 0.7),
            'medium_confidence': sum(1 for c in confidences if 0.4 < c <= 0.7),
            'low_confidence': sum(1 for c in confidences if 0 < c <= 0.4),
            'average_confidence': np.mean([c for c in confidences if c > 0]),
            'category': category
        }

        # Save statistics
        stats_path = output_dir / f"{base_name}_heatmap_stats.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"Saved statistics to {stats_path}")

        return {
            'heatmap_analysis': str(output_path),
            'confidence_heatmap': str(conf_output),
            'density_heatmap': str(density_output),
            'statistics': stats
        }


def main():
    """Generate heatmaps for garment images."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='heatmap_results', help='Output directory')
    args = parser.parse_args()

    # Initialize generator
    print("Initializing Landmark Heatmap Generator...")
    generator = LandmarkHeatmapGenerator()

    # Generate heatmaps
    results = generator.generate_heatmap(args.image_path, args.output_dir)

    print("\n" + "="*60)
    print("HEATMAP GENERATION COMPLETE")
    print("="*60)
    print(f"Statistics:")
    for key, value in results['statistics'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    print("="*60)


if __name__ == '__main__':
    main()