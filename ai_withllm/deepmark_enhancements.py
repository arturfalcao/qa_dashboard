#!/usr/bin/env python3
"""
DeepMark++ Post-Processing Enhancements

Implements the post-processing techniques from the DeepMark++ paper
(2nd place, DeepFashion2 Challenge 2020):

1. Heatmap smoothing using Gaussian kernels
2. Keypoint location refinement through position blending
3. Distance-based keypoint rescoring with anatomical constraints

Paper: https://ar5iv.labs.arxiv.org/html/2006.00710
"""

import numpy as np
import cv2
from scipy.ndimage import gaussian_filter, maximum_filter
from typing import Tuple, List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepMarkEnhancements:
    """
    Post-processing enhancements from DeepMark++ paper
    """

    def __init__(self,
                 gaussian_kernel_size: float = 2.0,
                 refinement_window: int = 5,
                 distance_penalty_weight: float = 0.05):
        """
        Initialize DeepMark++ enhancements

        Args:
            gaussian_kernel_size: Sigma for Gaussian smoothing
            refinement_window: Window size for sub-pixel refinement
            distance_penalty_weight: Weight for distance-based penalty
        """
        self.gaussian_kernel_size = gaussian_kernel_size
        self.refinement_window = refinement_window
        self.distance_penalty_weight = distance_penalty_weight

        # Anatomical constraints for different garment types
        self.anatomical_constraints = self._define_anatomical_constraints()

        logger.info("DeepMark++ enhancements initialized")
        logger.info(f"  Gaussian kernel: σ={gaussian_kernel_size}")
        logger.info(f"  Refinement window: {refinement_window}x{refinement_window}")
        logger.info(f"  Distance penalty: {distance_penalty_weight}")

    def _define_anatomical_constraints(self) -> Dict:
        """
        Define anatomical constraints for keypoint relationships
        Based on typical garment proportions
        """
        return {
            'upper_body': {
                'shoulder_width_range': (0.2, 0.8),  # 20-80% of image width
                'chest_below_shoulder': True,
                'hem_below_chest': True,
                'max_shoulder_to_hem_ratio': 3.0
            },
            'lower_body': {
                'waist_width_range': (0.15, 0.7),
                'hem_wider_than_waist': True,  # For flared pants
                'max_waist_to_hem_ratio': 2.5
            }
        }

    def apply_heatmap_smoothing(self, heatmaps: np.ndarray) -> np.ndarray:
        """
        Apply Gaussian smoothing to heatmaps

        Reduces noise and improves peak detection stability
        DeepMark++ Technique #2

        Args:
            heatmaps: Raw heatmaps from model (C, H, W)

        Returns:
            Smoothed heatmaps (C, H, W)
        """
        smoothed = np.zeros_like(heatmaps)

        for i in range(heatmaps.shape[0]):
            # Apply Gaussian filter to each heatmap channel
            smoothed[i] = gaussian_filter(
                heatmaps[i],
                sigma=self.gaussian_kernel_size,
                mode='constant'
            )

        return smoothed

    def refine_keypoint_location(self,
                                 heatmap: np.ndarray,
                                 peak_y: int,
                                 peak_x: int) -> Tuple[float, float, float]:
        """
        Refine keypoint location using sub-pixel position blending

        DeepMark++ Technique #3: Keypoint Location Refinement
        Uses weighted average of values around the peak for sub-pixel accuracy

        Args:
            heatmap: Single heatmap channel (H, W)
            peak_y: Peak y-coordinate (integer)
            peak_x: Peak x-coordinate (integer)

        Returns:
            (refined_x, refined_y, refined_confidence)
        """
        h, w = heatmap.shape
        window = self.refinement_window

        # Extract window around peak
        y_min = max(0, peak_y - window // 2)
        y_max = min(h, peak_y + window // 2 + 1)
        x_min = max(0, peak_x - window // 2)
        x_max = min(w, peak_x + window // 2 + 1)

        window_region = heatmap[y_min:y_max, x_min:x_max]

        if window_region.size == 0:
            return float(peak_x), float(peak_y), float(heatmap[peak_y, peak_x])

        # Compute weighted center using activation values as weights
        weights = np.maximum(window_region, 0)  # Only positive values
        total_weight = np.sum(weights)

        if total_weight < 1e-6:
            return float(peak_x), float(peak_y), float(heatmap[peak_y, peak_x])

        # Calculate weighted average position
        y_coords, x_coords = np.meshgrid(
            np.arange(y_min, y_max),
            np.arange(x_min, x_max),
            indexing='ij'
        )

        refined_y = np.sum(y_coords * weights) / total_weight
        refined_x = np.sum(x_coords * weights) / total_weight

        # Refined confidence is the weighted average
        refined_conf = np.sum(window_region * weights) / total_weight

        return refined_x, refined_y, refined_conf

    def apply_distance_based_rescoring(self,
                                       landmarks: List[Optional[Tuple[float, float]]],
                                       confidences: List[float],
                                       category: str,
                                       image_shape: Tuple[int, int]) -> List[float]:
        """
        Apply distance-based rescoring to filter anatomically impossible keypoints

        DeepMark++ Technique #4: Distance-based penalty for outliers

        Args:
            landmarks: List of (x, y) landmark positions
            confidences: List of confidence scores
            category: Detected garment category
            image_shape: (height, width) of image

        Returns:
            Rescored confidences
        """
        rescored = confidences.copy()
        img_height, img_width = image_shape

        # Extract valid landmarks
        valid_landmarks = [(i, lm, conf) for i, (lm, conf) in enumerate(zip(landmarks, confidences))
                          if lm is not None and conf > 0.3]

        if len(valid_landmarks) < 3:
            return rescored  # Not enough landmarks for meaningful rescoring

        # Calculate centroid of valid landmarks
        centroid_x = np.mean([lm[0] for _, lm, _ in valid_landmarks])
        centroid_y = np.mean([lm[1] for _, lm, _ in valid_landmarks])

        # Calculate mean distance from centroid
        distances = [np.sqrt((lm[0] - centroid_x)**2 + (lm[1] - centroid_y)**2)
                    for _, lm, _ in valid_landmarks]
        mean_distance = np.mean(distances)
        std_distance = np.std(distances) if len(distances) > 1 else mean_distance

        # Apply penalties to outliers
        for idx, lm, conf in valid_landmarks:
            distance = np.sqrt((lm[0] - centroid_x)**2 + (lm[1] - centroid_y)**2)

            # Penalize landmarks that are > 3 standard deviations from mean
            if std_distance > 0:
                z_score = abs(distance - mean_distance) / std_distance

                if z_score > 3.0:  # Outlier
                    penalty = self.distance_penalty_weight * z_score
                    rescored[idx] = max(0.0, conf - penalty)

        # Apply category-specific anatomical constraints
        rescored = self._apply_anatomical_constraints(
            landmarks, rescored, category, (img_width, img_height)
        )

        return rescored

    def _apply_anatomical_constraints(self,
                                     landmarks: List[Optional[Tuple[float, float]]],
                                     confidences: List[float],
                                     category: str,
                                     image_size: Tuple[int, int]) -> List[float]:
        """
        Apply category-specific anatomical constraints

        Args:
            landmarks: Landmark positions
            confidences: Current confidences
            category: Garment category
            image_size: (width, height) of image

        Returns:
            Confidence scores after applying constraints
        """
        img_width, img_height = image_size
        rescored = confidences.copy()

        # Category-specific constraint checks
        if 'shirt' in category or 'outwear' in category or 'vest' in category:
            # Upper body constraints
            # Check shoulder width relative to image width
            constraints = self.anatomical_constraints['upper_body']

            # Find shoulder landmarks (typically in first 15 keypoints)
            shoulder_landmarks = [(i, lm) for i, lm in enumerate(landmarks[:15])
                                 if lm is not None and confidences[i] > 0.3]

            if len(shoulder_landmarks) >= 2:
                # Check if shoulder width is reasonable
                x_coords = [lm[0] for _, lm in shoulder_landmarks]
                shoulder_width = max(x_coords) - min(x_coords)
                relative_width = shoulder_width / img_width

                min_width, max_width = constraints['shoulder_width_range']

                # Penalize if shoulder width is unreasonable
                if relative_width < min_width or relative_width > max_width:
                    for i, _ in shoulder_landmarks:
                        rescored[i] *= 0.7  # Reduce confidence

        elif category in ['trousers', 'shorts']:
            # Lower body constraints
            constraints = self.anatomical_constraints['lower_body']

            # Similar checks for waist landmarks
            waist_landmarks = [(i, lm) for i, lm in enumerate(landmarks[158:182], start=158)
                              if lm is not None and confidences[i] > 0.3]

            if len(waist_landmarks) >= 2:
                x_coords = [lm[0] for _, lm in waist_landmarks]
                waist_width = max(x_coords) - min(x_coords)
                relative_width = waist_width / img_width

                min_width, max_width = constraints['waist_width_range']

                if relative_width < min_width or relative_width > max_width:
                    for i, _ in waist_landmarks:
                        rescored[i] *= 0.7

        return rescored

    def process_heatmaps_enhanced(self,
                                  heatmaps: np.ndarray,
                                  confidence_threshold: float,
                                  scale_x: float,
                                  scale_y: float,
                                  image_shape: Tuple[int, int],
                                  category: str = 'unknown') -> Tuple[List, List]:
        """
        Complete enhanced heatmap processing pipeline

        Combines all DeepMark++ techniques:
        1. Heatmap smoothing
        2. NMS
        3. Sub-pixel refinement
        4. Distance-based rescoring

        Args:
            heatmaps: Raw model output (C, H, W)
            confidence_threshold: Minimum confidence
            scale_x: X scaling factor to original image
            scale_y: Y scaling factor to original image
            image_shape: (height, width) of original image
            category: Detected garment category

        Returns:
            (landmarks, confidences) after all enhancements
        """
        # Step 1: Apply Gaussian smoothing
        smoothed_heatmaps = self.apply_heatmap_smoothing(heatmaps)

        # Step 2: Extract landmarks with refinement
        landmarks = []
        confidences = []

        for i in range(smoothed_heatmaps.shape[0]):
            heatmap = smoothed_heatmaps[i]

            # Apply NMS to find peak
            max_filtered = maximum_filter(heatmap, size=3)
            suppressed = np.where(heatmap == max_filtered, heatmap, 0)

            # Find peak
            max_val = np.max(suppressed)

            if max_val > confidence_threshold:
                # Get integer peak location
                max_loc = np.unravel_index(np.argmax(suppressed), suppressed.shape)
                peak_y, peak_x = max_loc

                # Step 3: Sub-pixel refinement
                refined_x, refined_y, refined_conf = self.refine_keypoint_location(
                    heatmap, peak_y, peak_x
                )

                # Scale to original image size
                x_orig = refined_x * 4 * scale_x  # 4x because heatmap is 1/4 of input
                y_orig = refined_y * 4 * scale_y

                landmarks.append((float(x_orig), float(y_orig)))
                confidences.append(float(refined_conf))
            else:
                landmarks.append(None)
                confidences.append(0.0)

        # Step 4: Distance-based rescoring
        rescored_confidences = self.apply_distance_based_rescoring(
            landmarks, confidences, category, image_shape
        )

        return landmarks, rescored_confidences


def create_enhanced_detector():
    """
    Factory function to create detector with DeepMark++ enhancements
    """
    return DeepMarkEnhancements(
        gaussian_kernel_size=2.0,
        refinement_window=5,
        distance_penalty_weight=0.1
    )
