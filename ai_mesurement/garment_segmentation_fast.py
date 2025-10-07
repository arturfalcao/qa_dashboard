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
        Improved garment segmentation using multiple methods

        Args:
            image: Input BGR image
            ruler_bbox: Optional ruler bounding box to exclude (x, y, w, h)

        Returns:
            mask: Binary mask of segmented garment
            info: Dictionary with segmentation info
        """
        h, w = image.shape[:2]

        # Try multiple segmentation methods and combine
        methods = []

        # Method 1: Background subtraction (works well for white/gray backgrounds)
        bg_mask = self._segment_by_background(image)
        if bg_mask is not None:
            methods.append(bg_mask)
            if self.debug:
                print(f"   ✓ Background method succeeded")
                cv2.imwrite("seg_background.png", bg_mask)
        elif self.debug:
            print(f"   ✗ Background method failed")

        # Method 2: Edge-based segmentation (good for dark garments)
        edge_mask = self._segment_by_edges(image)
        if edge_mask is not None:
            methods.append(edge_mask)
            if self.debug:
                print(f"   ✓ Edge method succeeded")
                cv2.imwrite("seg_edges.png", edge_mask)
        elif self.debug:
            print(f"   ✗ Edge method failed")

        # Method 3: Improved color-based with multiple samples
        color_mask = self._improved_color_segment(image)
        if color_mask is not None:
            methods.append(color_mask)
            if self.debug:
                print(f"   ✓ Color method succeeded")
                cv2.imwrite("seg_color.png", color_mask)
        elif self.debug:
            print(f"   ✗ Color method failed")

        # Combine all methods
        if len(methods) > 0:
            # Use majority voting
            combined = np.zeros((h, w), dtype=np.float32)
            for mask in methods:
                combined += mask.astype(np.float32) / 255.0

            # Threshold at 50% agreement
            mask = (combined >= len(methods) / 2.0).astype(np.uint8) * 255
        else:
            # Fallback to old method
            initial_mask = np.ones((h, w), dtype=np.uint8) * 255
            if ruler_bbox:
                rx, ry, rw, rh = ruler_bbox
                rx = max(0, rx)
                ry = max(0, ry)
                rw = min(rw, w - rx)
                rh = min(rh, h - ry)
                initial_mask[ry:ry+rh, rx:rx+rw] = 0
            mask = self._fast_adaptive_color(image, initial_mask)

        # Exclude ruler area if provided
        if ruler_bbox:
            rx, ry, rw, rh = ruler_bbox
            rx = max(0, rx)
            ry = max(0, ry)
            rw = min(rw, w - rx)
            rh = min(rh, h - ry)
            mask[ry:ry+rh, rx:rx+rw] = 0

        # Clean up mask
        mask = self._fast_cleanup(mask)

        # Calculate info
        area = np.sum(mask > 0)
        info = {
            'area': float(area),
            'method': 'multi_method',
            'score': 1.0
        }

        if self.debug:
            print(f"✅ Segmentation complete: {area:,} pixels")
            cv2.imwrite("segmentation_debug.png", mask)

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

    def _segment_by_background(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Segment by detecting non-background pixels
        Assumes white/gray background
        """
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Detect background (usually white/light gray)
            # Sample corners for background color
            corner_size = 50
            corners = [
                gray[0:corner_size, 0:corner_size],
                gray[0:corner_size, w-corner_size:w],
                gray[h-corner_size:h, 0:corner_size],
                gray[h-corner_size:h, w-corner_size:w]
            ]

            # Get background intensity
            bg_values = []
            for corner in corners:
                bg_values.extend(corner.flatten())

            bg_median = np.median(bg_values)
            bg_std = np.std(bg_values)

            # Create mask for non-background
            # Focus on center region to avoid edges
            center_region = gray[h//4:3*h//4, w//4:3*w//4]

            if bg_median > 150:  # Light background
                # For light backgrounds, find dark objects
                # Use Otsu's thresholding for automatic threshold selection
                _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                # Also try manual threshold as backup
                threshold = bg_median - max(40, 2*bg_std)
                mask2 = (gray < threshold).astype(np.uint8) * 255

                # Use the one with more pixels in center
                center_pixels1 = np.sum(mask[h//3:2*h//3, w//3:2*w//3] > 0)
                center_pixels2 = np.sum(mask2[h//3:2*h//3, w//3:2*w//3] > 0)

                if center_pixels2 > center_pixels1:
                    mask = mask2
            else:
                # Dark background (rare)
                _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Clean up with morphology
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

            # Fill holes
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(mask, contours, -1, 255, -1)

            return mask
        except Exception as e:
            if self.debug:
                print(f"Background segmentation failed: {e}")
            return None

    def _segment_by_edges(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Edge-based segmentation for dark garments
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply bilateral filter to reduce noise while keeping edges
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)

            # Detect edges
            edges = cv2.Canny(filtered, 30, 100)

            # Close gaps in edges
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

            # Fill enclosed regions
            h, w = closed.shape
            mask = np.zeros((h+2, w+2), np.uint8)
            filled = closed.copy()

            # Flood fill from corners (background)
            cv2.floodFill(filled, mask, (0, 0), 255)
            cv2.floodFill(filled, mask, (w-1, 0), 255)
            cv2.floodFill(filled, mask, (0, h-1), 255)
            cv2.floodFill(filled, mask, (w-1, h-1), 255)

            # Invert to get foreground
            filled_inv = cv2.bitwise_not(filled)

            # Combine with edge mask
            result = cv2.bitwise_or(filled_inv, closed)

            return result
        except Exception as e:
            if self.debug:
                print(f"Edge segmentation failed: {e}")
            return None

    def _improved_color_segment(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Improved color segmentation with multiple sample points
        """
        try:
            h, w = image.shape[:2]
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Sample multiple regions (not just center)
            sample_points = [
                (h//2, w//2),      # Center
                (h//3, w//2),      # Upper middle
                (2*h//3, w//2),    # Lower middle
                (h//2, w//3),      # Left middle
                (h//2, 2*w//3),    # Right middle
            ]

            masks = []
            for cy, cx in sample_points:
                # Sample region around point
                sample_size = min(h, w) // 10
                y1 = max(0, cy - sample_size)
                y2 = min(h, cy + sample_size)
                x1 = max(0, cx - sample_size)
                x2 = min(w, cx + sample_size)

                sample_region = hsv[y1:y2, x1:x2]
                if sample_region.size == 0:
                    continue

                # Get color statistics
                sample_pixels = sample_region.reshape(-1, 3)
                median_hsv = np.median(sample_pixels, axis=0)
                std_hsv = np.std(sample_pixels, axis=0)

                # Adaptive range based on variance
                h_range = max(15, min(30, std_hsv[0] * 2))
                s_range = max(50, min(100, std_hsv[1] * 2))
                v_range = max(50, min(100, std_hsv[2] * 2))

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

                # Create mask for this sample
                mask = cv2.inRange(hsv, lower, upper)
                masks.append(mask)

            if len(masks) == 0:
                return None

            # Combine all masks (union)
            combined = masks[0]
            for mask in masks[1:]:
                combined = cv2.bitwise_or(combined, mask)

            # Morphological operations to fill gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)

            return combined
        except Exception as e:
            if self.debug:
                print(f"Color segmentation failed: {e}")
            return None