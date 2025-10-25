#!/usr/bin/env python3
"""
Generate structural heatmaps of garments to identify natural keypoint locations.
Uses edge detection, corner detection, and contour analysis to find measurement points.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from scipy import signal, ndimage
from skimage import feature
import matplotlib.pyplot as plt


class GarmentStructuralHeatmap:
    """Generate heatmaps based on garment structural features to identify keypoints."""

    def __init__(self):
        """Initialize the structural heatmap generator."""
        self.debug = True

    def extract_garment_mask(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract the garment from background."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Use multiple thresholding methods
        _, binary1 = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        _, binary2 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Combine masks
        mask = cv2.bitwise_or(binary1, binary2)

        # Clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Fill holes
        mask = ndimage.binary_fill_holes(mask).astype(np.uint8) * 255

        # Get largest contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            clean_mask = np.zeros_like(mask)
            cv2.drawContours(clean_mask, [largest], -1, 255, -1)
            return clean_mask, largest

        return mask, np.array([])

    def generate_edge_heatmap(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Generate heatmap based on edge strength."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply mask
        masked = cv2.bitwise_and(gray, gray, mask=mask)

        # Multiple edge detection methods
        edges_canny = cv2.Canny(masked, 50, 150)
        edges_sobel_x = cv2.Sobel(masked, cv2.CV_64F, 1, 0, ksize=3)
        edges_sobel_y = cv2.Sobel(masked, cv2.CV_64F, 0, 1, ksize=3)
        edges_sobel = np.sqrt(edges_sobel_x**2 + edges_sobel_y**2)

        # Normalize and combine
        edges_sobel = (edges_sobel / edges_sobel.max() * 255).astype(np.uint8) if edges_sobel.max() > 0 else edges_sobel.astype(np.uint8)
        combined_edges = cv2.addWeighted(edges_canny, 0.5, edges_sobel, 0.5, 0)

        # Apply Gaussian blur to create heatmap effect
        edge_heatmap = cv2.GaussianBlur(combined_edges.astype(np.float32), (31, 31), 10)

        # Normalize
        if edge_heatmap.max() > 0:
            edge_heatmap = edge_heatmap / edge_heatmap.max()

        return edge_heatmap

    def generate_corner_heatmap(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Generate heatmap based on corner detection."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply mask
        masked = cv2.bitwise_and(gray, gray, mask=mask)

        # Harris corner detection
        corners_harris = cv2.cornerHarris(masked, blockSize=5, ksize=3, k=0.04)
        corners_harris = cv2.dilate(corners_harris, None)

        # Shi-Tomasi corner detection
        corners_st = cv2.goodFeaturesToTrack(masked, maxCorners=200, qualityLevel=0.01,
                                             minDistance=20, mask=mask)

        # Create heatmap from corners
        corner_heatmap = np.zeros_like(gray, dtype=np.float32)

        # Add Harris corners
        corner_heatmap += corners_harris / (corners_harris.max() + 1e-8)

        # Add Shi-Tomasi corners as points
        if corners_st is not None:
            for corner in corners_st:
                x, y = corner.ravel().astype(int)
                cv2.circle(corner_heatmap, (x, y), 20, 1.0, -1)

        # Blur to create heatmap effect
        corner_heatmap = cv2.GaussianBlur(corner_heatmap, (41, 41), 15)

        # Normalize
        if corner_heatmap.max() > 0:
            corner_heatmap = corner_heatmap / corner_heatmap.max()

        return corner_heatmap

    def generate_contour_extrema_heatmap(self, contour: np.ndarray, image_shape: Tuple) -> np.ndarray:
        """Generate heatmap from contour extreme points."""
        h, w = image_shape[:2]
        extrema_heatmap = np.zeros((h, w), dtype=np.float32)

        if len(contour) == 0:
            return extrema_heatmap

        points = contour.reshape(-1, 2)

        # Find extreme points
        top_point = points[np.argmin(points[:, 1])]
        bottom_point = points[np.argmax(points[:, 1])]
        left_point = points[np.argmin(points[:, 0])]
        right_point = points[np.argmax(points[:, 0])]

        # Find convexity defects (concave regions like armpits)
        hull = cv2.convexHull(contour, returnPoints=False)
        if len(hull) > 3 and len(contour) > 3:
            try:
                defects = cv2.convexityDefects(contour, hull)
                if defects is not None:
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        if d > 10000:  # Significant defect
                            far = tuple(contour[f][0])
                            cv2.circle(extrema_heatmap, far, 40, 1.0, -1)
            except:
                pass

        # Add extreme points
        for point in [top_point, bottom_point, left_point, right_point]:
            cv2.circle(extrema_heatmap, tuple(point), 50, 1.0, -1)

        # Find corners along contour (high curvature points)
        if len(points) > 10:
            # Calculate curvature
            curvature = self.calculate_curvature(points)
            high_curvature_idx = np.where(curvature > np.percentile(curvature, 90))[0]

            for idx in high_curvature_idx:
                cv2.circle(extrema_heatmap, tuple(points[idx]), 30, 0.8, -1)

        # Blur to create heatmap
        extrema_heatmap = cv2.GaussianBlur(extrema_heatmap, (51, 51), 20)

        # Normalize
        if extrema_heatmap.max() > 0:
            extrema_heatmap = extrema_heatmap / extrema_heatmap.max()

        return extrema_heatmap

    def calculate_curvature(self, points: np.ndarray) -> np.ndarray:
        """Calculate curvature along contour points."""
        # Smooth the contour first
        if len(points) < 5:
            return np.zeros(len(points))

        # Calculate derivatives
        dx = np.gradient(points[:, 0])
        dy = np.gradient(points[:, 1])
        ddx = np.gradient(dx)
        ddy = np.gradient(dy)

        # Curvature formula
        curvature = np.abs(dx * ddy - dy * ddx) / (dx**2 + dy**2)**1.5

        # Handle nan/inf
        curvature = np.nan_to_num(curvature, nan=0, posinf=0, neginf=0)

        return curvature

    def generate_skeleton_heatmap(self, mask: np.ndarray) -> np.ndarray:
        """Generate heatmap from morphological skeleton (medial axis)."""
        # Compute skeleton
        skeleton = cv2.ximgproc.thinning(mask, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)

        # Find endpoints and junction points
        skeleton_heatmap = skeleton.astype(np.float32) / 255

        # Enhance endpoints and junctions
        kernel = np.array([[1, 1, 1],
                          [1, 10, 1],
                          [1, 1, 1]], dtype=np.float32)

        neighbor_count = cv2.filter2D(skeleton_heatmap, -1, kernel / 10)

        # Endpoints have only 1 neighbor, junctions have 3+ neighbors
        endpoints = (neighbor_count > 0.9) & (neighbor_count < 1.2)
        junctions = neighbor_count > 2.8

        # Add weight to endpoints and junctions
        skeleton_heatmap[endpoints] = 2.0
        skeleton_heatmap[junctions] = 1.5

        # Blur to create heatmap
        skeleton_heatmap = cv2.GaussianBlur(skeleton_heatmap, (41, 41), 15)

        # Normalize
        if skeleton_heatmap.max() > 0:
            skeleton_heatmap = skeleton_heatmap / skeleton_heatmap.max()

        return skeleton_heatmap

    def generate_combined_structural_heatmap(self, image: np.ndarray) -> Dict:
        """Generate comprehensive structural heatmap combining all methods."""
        h, w = image.shape[:2]

        # Extract garment mask and contour
        mask, contour = self.extract_garment_mask(image)

        # Generate individual heatmaps
        print("Generating edge heatmap...")
        edge_heat = self.generate_edge_heatmap(image, mask)

        print("Generating corner heatmap...")
        corner_heat = self.generate_corner_heatmap(image, mask)

        print("Generating contour extrema heatmap...")
        extrema_heat = self.generate_contour_extrema_heatmap(contour, (h, w))

        print("Generating skeleton heatmap...")
        skeleton_heat = self.generate_skeleton_heatmap(mask)

        # Combine heatmaps with weights
        combined_heat = (
            edge_heat * 0.3 +
            corner_heat * 0.3 +
            extrema_heat * 0.25 +
            skeleton_heat * 0.15
        )

        # Enhance peaks
        combined_heat = combined_heat ** 1.5

        # Normalize
        if combined_heat.max() > 0:
            combined_heat = combined_heat / combined_heat.max()

        # Apply mask to remove background
        combined_heat = combined_heat * (mask / 255)

        # Find peaks (potential keypoints)
        keypoints = self.find_keypoints_from_heatmap(combined_heat, mask)

        return {
            'combined_heatmap': combined_heat,
            'edge_heatmap': edge_heat,
            'corner_heatmap': corner_heat,
            'extrema_heatmap': extrema_heat,
            'skeleton_heatmap': skeleton_heat,
            'keypoints': keypoints,
            'mask': mask,
            'contour': contour
        }

    def find_keypoints_from_heatmap(self, heatmap: np.ndarray, mask: np.ndarray,
                                    threshold: float = 0.3, min_distance: int = 30) -> List[Dict]:
        """Extract keypoint locations from heatmap peaks."""
        # Find local maxima
        from scipy.ndimage import maximum_filter

        # Apply threshold
        heatmap_thresh = heatmap.copy()
        heatmap_thresh[heatmap < threshold] = 0

        # Find local maxima
        local_maxima = (maximum_filter(heatmap_thresh, size=min_distance) == heatmap_thresh)
        local_maxima = local_maxima & (heatmap_thresh > 0) & (mask > 0)

        # Get coordinates of maxima
        peaks_y, peaks_x = np.where(local_maxima)

        # Sort by strength
        peak_values = heatmap_thresh[peaks_y, peaks_x]
        sorted_idx = np.argsort(peak_values)[::-1]

        keypoints = []
        for i in sorted_idx[:50]:  # Take top 50 keypoints
            keypoints.append({
                'position': (int(peaks_x[i]), int(peaks_y[i])),
                'strength': float(peak_values[i]),
                'rank': len(keypoints) + 1
            })

        return keypoints

    def visualize_structural_heatmap(self, image_path: str, output_dir: str = "structural_heatmap"):
        """Generate and visualize structural heatmap."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        print(f"Analyzing garment structure for {image_path}...")

        # Generate structural heatmaps
        results = self.generate_combined_structural_heatmap(image)

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(image_path).stem

        # Create comprehensive visualization
        fig, axes = plt.subplots(2, 4, figsize=(20, 10))

        # Original image
        axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('Original Image', fontsize=12, fontweight='bold')
        axes[0, 0].axis('off')

        # Edge heatmap
        axes[0, 1].imshow(results['edge_heatmap'], cmap='hot')
        axes[0, 1].set_title('Edge Detection Heatmap', fontsize=12, fontweight='bold')
        axes[0, 1].axis('off')

        # Corner heatmap
        axes[0, 2].imshow(results['corner_heatmap'], cmap='hot')
        axes[0, 2].set_title('Corner Detection Heatmap', fontsize=12, fontweight='bold')
        axes[0, 2].axis('off')

        # Extrema heatmap
        axes[0, 3].imshow(results['extrema_heatmap'], cmap='hot')
        axes[0, 3].set_title('Contour Extrema Heatmap', fontsize=12, fontweight='bold')
        axes[0, 3].axis('off')

        # Skeleton heatmap
        axes[1, 0].imshow(results['skeleton_heatmap'], cmap='hot')
        axes[1, 0].set_title('Skeleton/Medial Axis Heatmap', fontsize=12, fontweight='bold')
        axes[1, 0].axis('off')

        # Combined heatmap
        axes[1, 1].imshow(results['combined_heatmap'], cmap='jet')
        axes[1, 1].set_title('Combined Structural Heatmap', fontsize=12, fontweight='bold')
        axes[1, 1].axis('off')

        # Heatmap overlay on image
        overlay = image.copy()
        heatmap_colored = plt.cm.jet(results['combined_heatmap'])[:, :, :3]
        heatmap_bgr = (heatmap_colored * 255).astype(np.uint8)
        heatmap_bgr = cv2.cvtColor(heatmap_bgr, cv2.COLOR_RGB2BGR)
        overlay = cv2.addWeighted(overlay, 0.5, heatmap_bgr, 0.5, 0)
        axes[1, 2].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        axes[1, 2].set_title('Heatmap Overlay', fontsize=12, fontweight='bold')
        axes[1, 2].axis('off')

        # Detected keypoints
        keypoint_vis = image.copy()
        for kp in results['keypoints'][:20]:  # Show top 20 keypoints
            pos = kp['position']
            strength = kp['strength']
            color = (int(255 * (1 - strength)), int(255 * strength), 0)
            cv2.circle(keypoint_vis, pos, 8, color, -1)
            cv2.circle(keypoint_vis, pos, 10, (0, 0, 0), 2)
            # Add rank number
            cv2.putText(keypoint_vis, str(kp['rank']), (pos[0] + 12, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(keypoint_vis, str(kp['rank']), (pos[0] + 12, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        axes[1, 3].imshow(cv2.cvtColor(keypoint_vis, cv2.COLOR_BGR2RGB))
        axes[1, 3].set_title(f'Top 20 Keypoints Detected', fontsize=12, fontweight='bold')
        axes[1, 3].axis('off')

        # Main title
        fig.suptitle(f'Garment Structural Analysis - {base_name.upper()}',
                    fontsize=16, fontweight='bold')

        # Save figure
        plt.tight_layout()
        analysis_path = output_dir / f"{base_name}_structural_analysis.png"
        plt.savefig(analysis_path, dpi=150, bbox_inches='tight')
        print(f"Saved structural analysis to {analysis_path}")

        # Save individual heatmap
        heatmap_path = output_dir / f"{base_name}_structural_heatmap.jpg"
        heatmap_vis = (results['combined_heatmap'] * 255).astype(np.uint8)
        heatmap_colored = cv2.applyColorMap(heatmap_vis, cv2.COLORMAP_JET)
        cv2.imwrite(str(heatmap_path), heatmap_colored)
        print(f"Saved structural heatmap to {heatmap_path}")

        # Save overlay
        overlay_path = output_dir / f"{base_name}_heatmap_overlay.jpg"
        cv2.imwrite(str(overlay_path), overlay)
        print(f"Saved heatmap overlay to {overlay_path}")

        # Save keypoints
        keypoints_path = output_dir / f"{base_name}_keypoints.jpg"
        cv2.imwrite(str(keypoints_path), keypoint_vis)
        print(f"Saved keypoints visualization to {keypoints_path}")

        # Save keypoints data
        keypoints_json = output_dir / f"{base_name}_keypoints.json"
        keypoints_data = {
            'total_keypoints': len(results['keypoints']),
            'keypoints': results['keypoints'][:50],  # Save top 50
            'image_shape': image.shape[:2]
        }
        with open(keypoints_json, 'w') as f:
            json.dump(keypoints_data, f, indent=2)
        print(f"Saved keypoints data to {keypoints_json}")

        # Print summary
        print(f"\nKEYPOINT DETECTION SUMMARY:")
        print(f"  Total keypoints found: {len(results['keypoints'])}")
        print(f"  Top 10 keypoint locations:")
        for kp in results['keypoints'][:10]:
            print(f"    {kp['rank']}. Position: {kp['position']}, Strength: {kp['strength']:.3f}")

        return {
            'analysis_image': str(analysis_path),
            'heatmap': str(heatmap_path),
            'overlay': str(overlay_path),
            'keypoints': keypoints_data
        }


def main():
    """Generate structural heatmap for garment images."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='structural_heatmap', help='Output directory')
    args = parser.parse_args()

    # Initialize generator
    print("Initializing Garment Structural Heatmap Generator...")
    generator = GarmentStructuralHeatmap()

    # Generate heatmap
    results = generator.visualize_structural_heatmap(args.image_path, args.output_dir)

    print("\n" + "="*60)
    print("STRUCTURAL HEATMAP GENERATION COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()