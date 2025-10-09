#!/usr/bin/env python3
"""
Calibration Tool for ArUco-based scale computation and perspective rectification.
Handles 4-corner ArUco markers to establish pixel-to-mm conversion.
"""

import cv2
import numpy as np
import json
from typing import Dict, Optional, Tuple, List, Any
import logging

logger = logging.getLogger(__name__)


class CalibrationTool:
    """
    Computes homography from 4 ArUco corner markers and derives scale factors.

    Expected marker layout (looking down at bench):
    - ID 0: Top-Left (TL)
    - ID 1: Top-Right (TR)
    - ID 2: Bottom-Right (BR)
    - ID 3: Bottom-Left (BL)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize calibration tool.

        Args:
            config_path: Path to calibration JSON with intrinsics and bench geometry
        """
        self.config = {}
        # Use 6x6_50 for better stability and less false positives
        self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_50)
        self.aruco_params = cv2.aruco.DetectorParameters_create()

        # Default bench dimensions (mm) - normalized to bench_dimensions_mm
        self.bench_dimensions_mm = {'width': 1000.0, 'height': 1500.0}
        self.marker_size_mm = 50.0     # 50mm ArUco markers

        # Corner mapping for each marker (which corner faces bench corner)
        # This mapping should match your physical marker placement
        # Index: 0=top-left, 1=top-right, 2=bottom-right, 3=bottom-left of marker
        self.corner_mapping = {
            0: 2,  # Marker 0 (TL): use its bottom-right corner
            1: 3,  # Marker 1 (TR): use its bottom-left corner
            2: 0,  # Marker 2 (BR): use its top-left corner
            3: 1   # Marker 3 (BL): use its top-right corner
        }

        # Calibration results
        self.homography = None
        self.ppm = None  # pixels per mm
        self.pixel_to_mm = None
        self.rect_rms_mm = None  # rectification RMS error
        self.rect_size = None  # (width, height) of rectified image

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """Load calibration configuration from JSON."""
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

            # Update bench dimensions if provided
            if 'bench_dimensions_mm' in self.config:
                self.bench_dimensions_mm = self.config['bench_dimensions_mm']
            # Legacy support
            elif 'bench_width_mm' in self.config and 'bench_height_mm' in self.config:
                self.bench_dimensions_mm = {
                    'width': self.config['bench_width_mm'],
                    'height': self.config['bench_height_mm']
                }
            if 'marker_size_mm' in self.config:
                self.marker_size_mm = self.config['marker_size_mm']

            # Load pre-computed values if available
            if 'homography' in self.config:
                self.homography = np.array(self.config['homography'])
            if 'ppm' in self.config:
                self.ppm = self.config['ppm']
            if 'pixel_to_mm' in self.config:
                self.pixel_to_mm = self.config['pixel_to_mm']
            if 'rect_rms_mm' in self.config:
                self.rect_rms_mm = self.config['rect_rms_mm']
            if 'rect_size' in self.config:
                self.rect_size = tuple(self.config['rect_size'])

            logger.info(f"Loaded calibration from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")

    def save_config(self, config_path: str) -> None:
        """Save calibration configuration to JSON."""
        self.config.update({
            'bench_dimensions_mm': self.bench_dimensions_mm,
            'marker_size_mm': self.marker_size_mm,
            'homography': self.homography.tolist() if self.homography is not None else None,
            'ppm': self.ppm,
            'pixel_to_mm': self.pixel_to_mm,
            'rect_rms_mm': self.rect_rms_mm,
            'rect_size': list(self.rect_size) if self.rect_size else None
        })

        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"Saved calibration to {config_path}")

    def detect_aruco_markers(self, image: np.ndarray, refine_corners: bool = True) -> Dict[int, np.ndarray]:
        """
        Detect ArUco markers in image with optional sub-pixel refinement.

        Args:
            image: Input image (BGR or grayscale)
            refine_corners: Whether to apply sub-pixel corner refinement

        Returns:
            Dictionary mapping marker ID to corner points (4x2 array)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.aruco_params)

        markers = {}
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                marker_corners = corners[i][0]  # 4x2 array of corner points

                # Apply sub-pixel corner refinement for better accuracy
                if refine_corners:
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
                    marker_corners = cv2.cornerSubPix(
                        gray,
                        marker_corners,
                        (5, 5),  # Half window size
                        (-1, -1),  # No dead zone
                        criteria
                    )

                markers[marker_id] = marker_corners

        return markers

    def compute_homography(self, image: np.ndarray, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute homography from 4 corner ArUco markers.

        Args:
            image: Calibration image with 4 ArUco markers at corners
            save_path: Optional path to save calibration config

        Returns:
            Dictionary with calibration results
        """
        # Detect markers
        markers = self.detect_aruco_markers(image)

        if len(markers) < 4:
            return {
                'success': False,
                'error': f'Found only {len(markers)} markers, need 4',
                'detected_ids': list(markers.keys())
            }

        # Check we have the expected corner markers (IDs 0-3)
        required_ids = [0, 1, 2, 3]
        missing = [id for id in required_ids if id not in markers]
        if missing:
            return {
                'success': False,
                'error': f'Missing marker IDs: {missing}',
                'detected_ids': list(markers.keys())
            }

        # Use specific corner from each marker that faces the bench corner
        # This provides more stable homography than using centers
        src_points = np.array([
            markers[0][self.corner_mapping[0]],  # TL marker's specified corner
            markers[1][self.corner_mapping[1]],  # TR marker's specified corner
            markers[2][self.corner_mapping[2]],  # BR marker's specified corner
            markers[3][self.corner_mapping[3]]   # BL marker's specified corner
        ], dtype=np.float32)

        # Destination points in metric space (1 pixel = 1 mm)
        W = self.bench_dimensions_mm['width']
        H = self.bench_dimensions_mm['height']
        dst_points = np.array([
            [0, 0],     # TL
            [W, 0],     # TR
            [W, H],     # BR
            [0, H]      # BL
        ], dtype=np.float32)

        # Compute homography with higher precision RANSAC threshold
        self.homography, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 3.0)

        # Since rectified canvas is metric (1 px = 1 mm), set scale directly
        self.ppm = 1.0
        self.pixel_to_mm = 1.0

        # Rectified image size (metric canvas)
        self.rect_size = (int(W), int(H))

        # Compute rectification RMS error in mm
        src_transformed = cv2.perspectiveTransform(src_points.reshape(-1, 1, 2), self.homography)
        src_transformed = src_transformed.reshape(-1, 2)
        self.rect_rms_mm = float(np.sqrt(np.mean(np.sum((src_transformed - dst_points)**2, axis=1))))

        # Compute marker centers for reference
        marker_centers = {}
        for id, corners in markers.items():
            marker_centers[id] = np.mean(corners, axis=0)

        # Log calibration quality metrics
        homography_cond = np.linalg.cond(self.homography)
        logger.info(f"Calibration quality: rect_rms_mm={self.rect_rms_mm:.3f}, homography_condition={homography_cond:.1f}")

        if self.rect_rms_mm > 0.7:
            logger.warning(f"High rectification RMS error: {self.rect_rms_mm:.3f} mm (target < 0.7 mm)")
        if homography_cond > 1e4:
            logger.warning(f"Poor homography conditioning: {homography_cond:.1e} (target < 1e4)")

        result = {
            'success': True,
            'ppm': self.ppm,
            'pixel_to_mm': self.pixel_to_mm,
            'rect_rms_mm': self.rect_rms_mm,
            'rect_size': self.rect_size,
            'marker_centers': {k: v.tolist() for k, v in marker_centers.items()},
            'homography_condition': homography_cond
        }

        # Save if requested
        if save_path:
            self.save_config(save_path)

        return result

    def rectify_image(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Apply perspective rectification to image using computed homography.

        Args:
            image: Input image to rectify

        Returns:
            Rectified image or None if homography not computed
        """
        if self.homography is None or self.rect_size is None:
            logger.error("Homography not computed. Run compute_homography first.")
            return None

        rectified = cv2.warpPerspective(image, self.homography, self.rect_size)
        return rectified

    def rectify_points(self, points: np.ndarray) -> np.ndarray:
        """
        Transform points from original image to rectified coordinates.

        Args:
            points: Nx2 array of points in original image

        Returns:
            Nx2 array of points in rectified coordinates
        """
        if self.homography is None:
            logger.error("Homography not computed. Run compute_homography first.")
            return points

        points_reshaped = points.reshape(-1, 1, 2).astype(np.float32)
        rectified = cv2.perspectiveTransform(points_reshaped, self.homography)
        return rectified.reshape(-1, 2)

    def inverse_rectify_points(self, points: np.ndarray) -> np.ndarray:
        """
        Transform points from rectified coordinates back to original image.

        Args:
            points: Nx2 array of points in rectified coordinates

        Returns:
            Nx2 array of points in original image
        """
        if self.homography is None:
            logger.error("Homography not computed. Run compute_homography first.")
            return points

        inv_h = np.linalg.inv(self.homography)
        points_reshaped = points.reshape(-1, 1, 2).astype(np.float32)
        original = cv2.perspectiveTransform(points_reshaped, inv_h)
        return original.reshape(-1, 2)

    def verify_scale_with_marker(self, image: np.ndarray, marker_id: int = None) -> Dict[str, Any]:
        """
        Verify scale accuracy by measuring marker side lengths.

        Args:
            image: Image with ArUco markers
            marker_id: Specific marker ID to check (None = check all visible)

        Returns:
            Dictionary with scale verification results
        """
        markers = self.detect_aruco_markers(image)

        if not markers:
            return {'success': False, 'error': 'No markers detected'}

        results = {}
        all_deviations = []

        # Check specified marker or all markers
        ids_to_check = [marker_id] if marker_id is not None else list(markers.keys())

        for id in ids_to_check:
            if id not in markers:
                continue

            corners = markers[id]

            # Compute side lengths in pixels
            side_lengths_px = [
                np.linalg.norm(corners[0] - corners[1]),  # Top
                np.linalg.norm(corners[1] - corners[2]),  # Right
                np.linalg.norm(corners[2] - corners[3]),  # Bottom
                np.linalg.norm(corners[3] - corners[0])   # Left
            ]

            # Convert to mm using homography if available
            if self.homography is not None:
                # Transform corners to metric space
                corners_metric = cv2.perspectiveTransform(
                    corners.reshape(-1, 1, 2),
                    self.homography
                ).reshape(-1, 2)

                side_lengths_mm = [
                    np.linalg.norm(corners_metric[0] - corners_metric[1]),
                    np.linalg.norm(corners_metric[1] - corners_metric[2]),
                    np.linalg.norm(corners_metric[2] - corners_metric[3]),
                    np.linalg.norm(corners_metric[3] - corners_metric[0])
                ]
            else:
                # Use pixel_to_mm if no homography
                side_lengths_mm = [l * self.pixel_to_mm for l in side_lengths_px]

            # Compare with expected marker size
            expected_mm = self.marker_size_mm
            deviations_mm = [abs(l - expected_mm) for l in side_lengths_mm]
            max_deviation = max(deviations_mm)
            avg_deviation = np.mean(deviations_mm)

            all_deviations.extend(deviations_mm)

            # Log warning if deviation > 0.5 mm
            if max_deviation > 0.5:
                logger.warning(
                    f"Marker {id}: High scale deviation {max_deviation:.2f} mm "
                    f"(measured: {np.mean(side_lengths_mm):.1f} mm, expected: {expected_mm} mm)"
                )

            results[f'marker_{id}'] = {
                'side_lengths_mm': side_lengths_mm,
                'expected_mm': expected_mm,
                'max_deviation_mm': max_deviation,
                'avg_deviation_mm': avg_deviation
            }

        # Overall statistics
        if all_deviations:
            overall_stats = {
                'success': True,
                'max_deviation_mm': max(all_deviations),
                'avg_deviation_mm': np.mean(all_deviations),
                'markers_checked': len(results)
            }

            logger.info(
                f"Scale verification: avg deviation {overall_stats['avg_deviation_mm']:.3f} mm, "
                f"max {overall_stats['max_deviation_mm']:.3f} mm"
            )
        else:
            overall_stats = {'success': False, 'error': 'No markers to verify'}

        return {**overall_stats, **results}

    def get_scale_at_point(self, point: np.ndarray, image_shape: Tuple[int, int]) -> float:
        """
        Get local scale factor at a specific point (handles perspective).

        Args:
            point: (x, y) coordinates in original image
            image_shape: (height, width) of original image

        Returns:
            Local pixel_to_mm scale factor at that point
        """
        if self.homography is None:
            return self.pixel_to_mm if self.pixel_to_mm else 1.0

        # Create a small square around the point
        delta = 10  # pixels
        square = np.array([
            [point[0] - delta, point[1] - delta],
            [point[0] + delta, point[1] - delta],
            [point[0] + delta, point[1] + delta],
            [point[0] - delta, point[1] + delta]
        ], dtype=np.float32)

        # Clip to image bounds
        square[:, 0] = np.clip(square[:, 0], 0, image_shape[1] - 1)
        square[:, 1] = np.clip(square[:, 1], 0, image_shape[0] - 1)

        # Transform to rectified space
        square_rect = self.rectify_points(square)

        # Compute areas
        area_original = cv2.contourArea(square)
        area_rectified = cv2.contourArea(square_rect)

        if area_original > 0:
            # Scale factor is sqrt of area ratio
            scale_factor = np.sqrt(area_rectified / area_original)
            return self.pixel_to_mm / scale_factor

        return self.pixel_to_mm

    def verify_scale_with_marker(self, image: np.ndarray) -> Dict[str, float]:
        """
        Verify scale accuracy by measuring detected marker sizes.

        Args:
            image: Image with ArUco markers

        Returns:
            Dictionary with measured vs expected marker sizes
        """
        markers = self.detect_aruco_markers(image)

        results = {}
        for id, corners in markers.items():
            # Measure each edge of the marker
            edge_lengths_px = [
                np.linalg.norm(corners[1] - corners[0]),  # Top
                np.linalg.norm(corners[2] - corners[1]),  # Right
                np.linalg.norm(corners[3] - corners[2]),  # Bottom
                np.linalg.norm(corners[0] - corners[3])   # Left
            ]

            avg_length_px = np.mean(edge_lengths_px)
            avg_length_mm = avg_length_px * self.pixel_to_mm if self.pixel_to_mm else 0

            results[f'marker_{id}'] = {
                'measured_mm': avg_length_mm,
                'expected_mm': self.marker_size_mm,
                'error_mm': abs(avg_length_mm - self.marker_size_mm),
                'error_percent': abs(avg_length_mm - self.marker_size_mm) / self.marker_size_mm * 100
            }

        return results


def main():
    """Example usage and calibration workflow."""
    import argparse

    parser = argparse.ArgumentParser(description='Calibrate garment measurement system')
    parser.add_argument('--image', required=True, help='Calibration image with 4 ArUco markers')
    parser.add_argument('--config', default='calibration.json', help='Config file path')
    parser.add_argument('--verify', action='store_true', help='Verify calibration with marker measurements')
    args = parser.parse_args()

    # Initialize tool
    tool = CalibrationTool(args.config if os.path.exists(args.config) else None)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Compute calibration
    print("Computing calibration from ArUco markers...")
    result = tool.compute_homography(image, args.config)

    if result['success']:
        print(f"✓ Calibration successful!")
        print(f"  - Scale: {result['ppm']:.3f} pixels/mm")
        print(f"  - Resolution: {result['pixel_to_mm']:.3f} mm/pixel")
        print(f"  - Rectification RMS error: {result['rect_rms_mm']:.2f} mm")
        print(f"  - Homography condition number: {result['homography_condition']:.1f}")

        if args.verify:
            print("\nVerifying with marker measurements...")
            verification = tool.verify_scale_with_marker(image)
            for marker, data in verification.items():
                print(f"  {marker}: {data['measured_mm']:.1f} mm "
                      f"(expected {data['expected_mm']:.1f} mm, "
                      f"error {data['error_percent']:.1f}%)")

        # Save rectified image for inspection
        rectified = tool.rectify_image(image)
        if rectified is not None:
            output_path = args.image.replace('.', '_rectified.')
            cv2.imwrite(output_path, rectified)
            print(f"\nSaved rectified image to {output_path}")
    else:
        print(f"✗ Calibration failed: {result['error']}")
        print(f"  Detected marker IDs: {result['detected_ids']}")


if __name__ == '__main__':
    import os
    main()