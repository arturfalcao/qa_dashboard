#!/usr/bin/env python3
"""
Fast Garment Segmentation - Production Optimized
Prioritizes speed while maintaining accuracy
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class FastGarmentSegmenter:
    """
    Fast segmentation optimized for production use
    Uses only efficient methods
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    def segment_garment(self, image: np.ndarray, ruler_bbox: Optional[Tuple] = None) -> Tuple[np.ndarray, dict]:
        """
        Fast garment segmentation using color-adaptive method

        Args:
            image: Input BGR image
            ruler_bbox: Optional ruler bounding box to exclude (x, y, w, h)

        Returns:
            mask: Binary mask of segmented garment
            info: Dictionary with segmentation info
        """
        h, w = image.shape[:2]

        # Create initial mask excluding ruler
        initial_mask = np.ones((h, w), dtype=np.uint8) * 255
        if ruler_bbox:
            rx, ry, rw, rh = ruler_bbox
            # Ensure bbox is within image bounds
            rx = max(0, rx)
            ry = max(0, ry)
            rw = min(rw, w - rx)
            rh = min(rh, h - ry)
            initial_mask[ry:ry+rh, rx:rx+rw] = 0

        # Use fast adaptive color method
        mask = self._fast_adaptive_color(image, initial_mask)

        # Clean up mask
        mask = self._fast_cleanup(mask)

        # Calculate info
        area = np.sum(mask > 0)
        info = {
            'area': float(area),
            'method': 'fast_adaptive',
            'score': 1.0  # Simplified scoring
        }

        if self.debug:
            print(f"✅ Fast segmentation complete: {area:,} pixels")

        return mask, info

    def _fast_adaptive_color(self, image: np.ndarray, initial_mask: np.ndarray) -> np.ndarray:
        """
        Fast adaptive color segmentation
        """
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Sample center region for garment color
        center_y, center_x = h // 2, w // 2
        sample_size = min(h, w) // 6  # Smaller sample for speed

        y1 = max(0, center_y - sample_size)
        y2 = min(h, center_y + sample_size)
        x1 = max(0, center_x - sample_size)
        x2 = min(w, center_x + sample_size)

        sample_region = hsv[y1:y2, x1:x2]

        # Quick statistics
        sample_pixels = sample_region.reshape(-1, 3)

        # Use median for robustness
        median_hsv = np.median(sample_pixels, axis=0)

        # Create color range
        h_range = 20
        s_range = 60
        v_range = 60

        lower = np.array([
            max(0, median_hsv[0] - h_range),
            max(0, median_hsv[1] - s_range),
            max(0, median_hsv[2] - v_range)
        ], dtype=np.uint8)

        upper = np.array([
            min(179, median_hsv[0] + h_range),
            min(255, median_hsv[1] + s_range),
            min(255, median_hsv[2] + v_range)
        ], dtype=np.uint8)

        # Create mask
        mask = cv2.inRange(hsv, lower, upper)

        # Apply initial mask
        mask = cv2.bitwise_and(mask, initial_mask)

        return mask

    def _fast_cleanup(self, mask: np.ndarray) -> np.ndarray:
        """
        Fast mask cleanup
        """
        # Single morphological operation
        kernel = np.ones((5, 5), np.uint8)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find largest component (fast method)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)

        if num_labels > 1:
            # Find largest component (excluding background at label 0)
            areas = stats[1:, cv2.CC_STAT_AREA]
            if len(areas) > 0:
                largest_label = np.argmax(areas) + 1
                cleaned = (labels == largest_label).astype(np.uint8) * 255

        return cleaned