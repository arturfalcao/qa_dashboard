#!/usr/bin/env python3
"""
Lens Distortion Correction Module
Corrects fisheye/barrel distortion from camera lenses
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class LensCorrector:
    """
    Corrects lens distortion (fisheye/barrel effect) in images
    """

    def __init__(self, correction_strength: float = 0.5, debug: bool = False):
        """
        Initialize lens corrector

        Args:
            correction_strength: Distortion correction strength (0-1)
                                0 = no correction
                                0.5 = moderate correction (default)
                                1.0 = strong correction
            debug: Show before/after comparison
        """
        self.correction_strength = correction_strength
        self.debug = debug

    def correct_distortion(self, image: np.ndarray,
                          auto_detect: bool = True) -> Tuple[np.ndarray, dict]:
        """
        Correct lens distortion in image

        Args:
            image: Input image
            auto_detect: Automatically detect distortion level

        Returns:
            corrected_image: Distortion-corrected image
            correction_info: Dictionary with correction parameters
        """

        h, w = image.shape[:2]

        if self.debug:
            print(f"\n🔍 Lens Distortion Correction")
            print(f"   Image size: {w}x{h}")
            print(f"   Correction strength: {self.correction_strength}")

        # Method 1: Simple radial distortion correction
        if auto_detect:
            # Estimate distortion from image characteristics
            distortion_params = self._estimate_distortion(image)
        else:
            # Use preset distortion parameters
            distortion_params = self._get_default_params(self.correction_strength)

        # Apply correction
        corrected = self._apply_correction(image, distortion_params)

        # Calculate correction metrics
        correction_info = {
            'method': 'radial_correction',
            'strength': self.correction_strength,
            'parameters': distortion_params,
            'center_preserved': True,
            'edge_correction': self._calculate_edge_correction(image, corrected)
        }

        if self.debug:
            print(f"   ✅ Correction applied")
            print(f"   Edge correction: {correction_info['edge_correction']:.1%}")
            self._save_comparison(image, corrected)

        return corrected, correction_info

    def _estimate_distortion(self, image: np.ndarray) -> dict:
        """
        Estimate distortion parameters from image

        Uses edge detection to find straight lines that appear curved
        """

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)

        # Analyze line curvature
        if lines is not None and len(lines) > 0:
            # Check how much lines deviate from straight
            curvature = self._analyze_line_curvature(lines, image.shape)

            # Estimate distortion based on curvature
            k1 = -curvature * self.correction_strength * 0.00001
            k2 = k1 * 0.1  # Secondary distortion coefficient
        else:
            # Default mild correction
            k1 = -0.000005 * self.correction_strength
            k2 = k1 * 0.1

        return {
            'k1': k1,
            'k2': k2,
            'p1': 0.0,  # Tangential distortion (usually 0 for phones)
            'p2': 0.0
        }

    def _get_default_params(self, strength: float) -> dict:
        """Get default distortion parameters based on strength"""

        # Typical values for phone cameras
        base_k1 = -0.00001  # Primary radial distortion

        return {
            'k1': base_k1 * strength,
            'k2': base_k1 * strength * 0.1,
            'p1': 0.0,
            'p2': 0.0
        }

    def _apply_correction(self, image: np.ndarray, params: dict) -> np.ndarray:
        """Apply lens distortion correction"""

        h, w = image.shape[:2]

        # Camera matrix (assuming image center as principal point)
        focal_length = w  # Approximate focal length
        cx, cy = w / 2, h / 2

        camera_matrix = np.array([
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1]
        ], dtype=np.float32)

        # Distortion coefficients
        dist_coeffs = np.array([
            params['k1'],  # k1 - radial distortion
            params['k2'],  # k2 - radial distortion
            params['p1'],  # p1 - tangential distortion
            params['p2'],  # p2 - tangential distortion
            0              # k3 - radial distortion (usually 0)
        ], dtype=np.float32)

        # Get optimal new camera matrix
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs, (w, h), 0, (w, h)
        )

        # Undistort
        corrected = cv2.undistort(image, camera_matrix, dist_coeffs, None, new_camera_matrix)

        # Crop to valid region if needed
        if roi != (0, 0, 0, 0):
            x, y, w_roi, h_roi = roi
            if w_roi > 0 and h_roi > 0:
                # Optionally crop to valid region
                # For measurements, we want to keep full image
                pass

        return corrected

    def _analyze_line_curvature(self, lines: np.ndarray, shape: Tuple) -> float:
        """Analyze how curved the detected lines are"""

        h, w = shape[:2]
        center_x, center_y = w / 2, h / 2

        total_deviation = 0
        line_count = 0

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate distance from center
            dist1 = np.sqrt((x1 - center_x)**2 + (y1 - center_y)**2)
            dist2 = np.sqrt((x2 - center_x)**2 + (y2 - center_y)**2)

            # Lines further from center show more distortion
            avg_dist = (dist1 + dist2) / 2
            max_dist = np.sqrt(center_x**2 + center_y**2)

            # Weight by distance from center
            weight = avg_dist / max_dist

            # Estimate curvature (simplified)
            line_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            if line_length > 50:  # Only consider longer lines
                # Check if line is mostly horizontal or vertical
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1))
                if angle < np.pi/6 or angle > 5*np.pi/6:  # Horizontal
                    deviation = abs(y2 - y1) / line_length
                elif np.pi/3 < angle < 2*np.pi/3:  # Vertical
                    deviation = abs(x2 - x1) / line_length
                else:
                    continue

                total_deviation += deviation * weight
                line_count += 1

        if line_count > 0:
            avg_deviation = total_deviation / line_count
            # Convert to curvature estimate (0-100 scale)
            curvature = min(100, avg_deviation * 200)
        else:
            curvature = 10  # Default mild curvature

        return curvature

    def _calculate_edge_correction(self, original: np.ndarray,
                                  corrected: np.ndarray) -> float:
        """Calculate how much correction was applied at edges"""

        h, w = original.shape[:2]

        # Sample points at edges
        edge_points = [
            (10, h//2),      # Left edge
            (w-10, h//2),    # Right edge
            (w//2, 10),      # Top edge
            (w//2, h-10)     # Bottom edge
        ]

        # Calculate average pixel displacement
        total_displacement = 0
        for x, y in edge_points:
            # Compare pixel neighborhoods
            if 5 < x < w-5 and 5 < y < h-5:
                orig_patch = original[y-5:y+5, x-5:x+5]
                corr_patch = corrected[y-5:y+5, x-5:x+5]

                if orig_patch.shape == corr_patch.shape:
                    diff = np.mean(np.abs(orig_patch.astype(float) - corr_patch.astype(float)))
                    total_displacement += diff

        avg_displacement = total_displacement / (len(edge_points) * 255)  # Normalize to 0-1

        return avg_displacement

    def _save_comparison(self, original: np.ndarray, corrected: np.ndarray):
        """Save before/after comparison for debugging"""

        h, w = original.shape[:2]

        # Create side-by-side comparison
        comparison = np.hstack([original, corrected])

        # Add grid overlay to show distortion
        grid_original = self._draw_grid(original.copy())
        grid_corrected = self._draw_grid(corrected.copy())
        grid_comparison = np.hstack([grid_original, grid_corrected])

        # Save comparisons
        cv2.imwrite('lens_correction_comparison.png', comparison)
        cv2.imwrite('lens_correction_grid.png', grid_comparison)

        print(f"   📊 Comparison saved: lens_correction_comparison.png")
        print(f"   📊 Grid comparison saved: lens_correction_grid.png")

    def _draw_grid(self, image: np.ndarray, grid_size: int = 50) -> np.ndarray:
        """Draw grid on image to visualize distortion"""

        h, w = image.shape[:2]
        color = (0, 255, 0)  # Green grid

        # Draw vertical lines
        for x in range(0, w, grid_size):
            cv2.line(image, (x, 0), (x, h), color, 1)

        # Draw horizontal lines
        for y in range(0, h, grid_size):
            cv2.line(image, (0, y), (w, y), color, 1)

        return image


class AdaptiveLensCorrector(LensCorrector):
    """
    Advanced lens corrector that adapts to different camera types
    """

    # Known camera distortion profiles
    CAMERA_PROFILES = {
        'phone_wide': {'k1': -0.00002, 'k2': 0.000001},
        'phone_normal': {'k1': -0.00001, 'k2': 0.0000005},
        'phone_telephoto': {'k1': -0.000005, 'k2': 0.0000001},
        'webcam': {'k1': -0.00003, 'k2': 0.000002},
        'dslr': {'k1': -0.000001, 'k2': 0.00000005}
    }

    def detect_camera_type(self, image: np.ndarray, metadata: Optional[dict] = None) -> str:
        """
        Detect camera type from image characteristics

        Args:
            image: Input image
            metadata: Optional EXIF or metadata

        Returns:
            Camera type string
        """

        h, w = image.shape[:2]
        aspect_ratio = w / h

        # Check for typical phone camera characteristics
        if 3000 < w < 5000 and 2000 < h < 4000:
            # Likely phone camera
            # Check for wide angle distortion indicators
            distortion_level = self._estimate_distortion_level(image)

            if distortion_level > 30:
                return 'phone_wide'
            elif distortion_level > 15:
                return 'phone_normal'
            else:
                return 'phone_telephoto'

        elif w < 2000 and h < 2000:
            # Likely webcam
            return 'webcam'
        else:
            # Likely DSLR or high-end camera
            return 'dslr'

    def _estimate_distortion_level(self, image: np.ndarray) -> float:
        """Estimate distortion level (0-100 scale)"""

        # Use parent class method
        params = self._estimate_distortion(image)

        # Convert to 0-100 scale
        distortion_level = abs(params['k1']) * 1000000

        return min(100, distortion_level)