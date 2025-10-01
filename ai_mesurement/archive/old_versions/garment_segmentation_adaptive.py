#!/usr/bin/env python3
"""
Adaptive Garment Segmentation for Any Color/Type
Handles various apparel colors and types automatically
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class AdaptiveGarmentSegmenter:
    """
    Adaptive segmentation that works with any garment color
    Uses multiple strategies to detect garments regardless of color
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    def segment_garment(self, image: np.ndarray, ruler_bbox: Optional[Tuple] = None) -> Tuple[np.ndarray, dict]:
        """
        Segment garment from image using adaptive color detection

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
            initial_mask[ry:ry+rh, rx:rx+rw] = 0

        # Try multiple segmentation strategies
        strategies = [
            ('adaptive_color', self._segment_adaptive_color),
            ('edge_based', self._segment_edge_based),
            ('grabcut', self._segment_grabcut_adaptive),
        ]

        best_mask = None
        best_score = 0
        best_method = None

        for method_name, method in strategies:
            try:
                mask = method(image, initial_mask)

                if mask is not None:
                    score = self._evaluate_mask(mask, image)

                    if score > best_score:
                        best_score = score
                        best_mask = mask
                        best_method = method_name

                    if self.debug:
                        print(f"   Method {method_name}: score={score:.3f}")

            except Exception as e:
                if self.debug:
                    print(f"   Method {method_name} failed: {e}")

        if best_mask is None:
            # Fallback to simple thresholding
            best_mask = self._segment_fallback(image, initial_mask)
            best_method = 'fallback'

        # Clean up mask
        best_mask = self._clean_mask(best_mask)

        # Calculate info
        area = np.sum(best_mask > 0)
        info = {
            'area': float(area),
            'method': best_method,
            'score': best_score
        }

        if self.debug:
            print(f"✅ Best segmentation: {best_method} (score: {best_score:.3f})")

        return best_mask, info

    def _segment_adaptive_color(self, image: np.ndarray, initial_mask: np.ndarray) -> np.ndarray:
        """
        Adaptive color segmentation that learns garment color from center region
        Works with any color garment
        """
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Sample center region (likely to be garment)
        center_y, center_x = h // 2, w // 2
        sample_size = min(h, w) // 4

        # Get sample region
        sample_region = hsv[
            center_y - sample_size:center_y + sample_size,
            center_x - sample_size:center_x + sample_size
        ]

        # Calculate color statistics from center
        sample_pixels = sample_region.reshape(-1, 3)

        # Use percentiles for robustness
        lower_percentile = 15
        upper_percentile = 85

        h_low = np.percentile(sample_pixels[:, 0], lower_percentile)
        h_high = np.percentile(sample_pixels[:, 0], upper_percentile)
        s_low = np.percentile(sample_pixels[:, 1], lower_percentile)
        s_high = np.percentile(sample_pixels[:, 1], upper_percentile)
        v_low = np.percentile(sample_pixels[:, 2], lower_percentile)
        v_high = np.percentile(sample_pixels[:, 2], upper_percentile)

        # Expand ranges slightly for better coverage
        h_expansion = 15
        s_expansion = 40
        v_expansion = 40

        lower = np.array([
            max(0, h_low - h_expansion),
            max(0, s_low - s_expansion),
            max(0, v_low - v_expansion)
        ], dtype=np.uint8)

        upper = np.array([
            min(179, h_high + h_expansion),
            min(255, s_high + s_expansion),
            min(255, v_high + v_expansion)
        ], dtype=np.uint8)

        # Create mask
        mask = cv2.inRange(hsv, lower, upper)

        # Apply initial mask
        mask = cv2.bitwise_and(mask, initial_mask)

        return mask

    def _segment_edge_based(self, image: np.ndarray, initial_mask: np.ndarray) -> np.ndarray:
        """
        Edge-based segmentation using Canny edge detection
        Good for garments with clear boundaries
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Adaptive edge detection
        median_val = np.median(filtered)
        sigma = 0.33
        lower_threshold = int(max(0, (1.0 - sigma) * median_val))
        upper_threshold = int(min(255, (1.0 + sigma) * median_val))

        edges = cv2.Canny(filtered, lower_threshold, upper_threshold)

        # Dilate edges to close gaps
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create mask from largest contour
        mask = np.zeros_like(gray)
        if contours:
            # Sort by area and take largest
            largest_contour = max(contours, key=cv2.contourArea)

            # Fill the contour
            cv2.drawContours(mask, [largest_contour], -1, 255, -1)

        # Apply initial mask
        mask = cv2.bitwise_and(mask, initial_mask)

        return mask

    def _segment_grabcut_adaptive(self, image: np.ndarray, initial_mask: np.ndarray) -> np.ndarray:
        """
        GrabCut segmentation with automatic initialization
        Works well for complex patterns
        """
        h, w = image.shape[:2]

        # Create initial rectangle (center 70% of image)
        margin_x = int(w * 0.15)
        margin_y = int(h * 0.15)
        rect = (margin_x, margin_y, w - 2*margin_x, h - 2*margin_y)

        # Initialize mask for GrabCut
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[:] = cv2.GC_PR_BGD  # Probably background

        # Set rectangle area as probably foreground
        mask[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]] = cv2.GC_PR_FGD

        # Apply initial mask constraints
        mask[initial_mask == 0] = cv2.GC_BGD  # Definite background

        # Run GrabCut
        bgd_model = np.zeros((1, 65), dtype=np.float64)
        fgd_model = np.zeros((1, 65), dtype=np.float64)

        try:
            cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

            # Extract foreground
            result_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

            return result_mask

        except Exception:
            return None

    def _segment_fallback(self, image: np.ndarray, initial_mask: np.ndarray) -> np.ndarray:
        """
        Simple fallback segmentation using Otsu thresholding
        Last resort when other methods fail
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Otsu thresholding
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Apply initial mask
        mask = cv2.bitwise_and(mask, initial_mask)

        return mask

    def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Clean up mask with morphological operations
        """
        # Remove small noise
        kernel_small = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=2)

        # Close gaps
        kernel_medium = np.ones((5, 5), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_medium, iterations=1)

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)

        # Keep only largest component
        if num_labels > 1:
            # Find largest non-background component
            largest_label = 1
            largest_area = stats[1, cv2.CC_STAT_AREA] if num_labels > 1 else 0

            for i in range(2, num_labels):
                if stats[i, cv2.CC_STAT_AREA] > largest_area:
                    largest_area = stats[i, cv2.CC_STAT_AREA]
                    largest_label = i

            # Create clean mask with only largest component
            cleaned = (labels == largest_label).astype(np.uint8) * 255

        return cleaned

    def _evaluate_mask(self, mask: np.ndarray, image: np.ndarray) -> float:
        """
        Evaluate mask quality
        """
        h, w = image.shape[:2]
        total_pixels = h * w

        # Calculate area
        area = np.sum(mask > 0)
        area_ratio = area / total_pixels

        # Good masks should have reasonable area (10% to 70% of image)
        if area_ratio < 0.1 or area_ratio > 0.7:
            return 0.0

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Should have one main contour
        if len(contours) > 5:  # Too fragmented
            return 0.2

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)

        # Calculate solidity (area / convex hull area)
        hull = cv2.convexHull(largest_contour)
        hull_area = cv2.contourArea(hull)

        if hull_area > 0:
            solidity = cv2.contourArea(largest_contour) / hull_area
        else:
            solidity = 0

        # Calculate compactness
        perimeter = cv2.arcLength(largest_contour, True)
        if perimeter > 0:
            compactness = 4 * np.pi * area / (perimeter * perimeter)
        else:
            compactness = 0

        # Combine scores
        score = (
            area_ratio * 0.3 +  # Reasonable size
            solidity * 0.3 +    # Not too irregular
            compactness * 0.2 + # Relatively compact
            (1.0 if len(contours) == 1 else 0.5) * 0.2  # Single object preferred
        )

        return score