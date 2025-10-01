"""
Ruler Detection and Scale Calibration Module
Detects ruler in image and calculates pixels-to-cm conversion ratio
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict


class RulerDetector:
    """Detect ruler and calibrate measurement scale"""

    def __init__(self, known_length_cm: float = 31.0, debug: bool = False):
        """
        Args:
            known_length_cm: Known length of the ruler in centimeters
            debug: Enable debug visualizations
        """
        self.known_length_cm = known_length_cm
        self.debug = debug

    def detect_ruler(
        self,
        image: np.ndarray,
        mask: Optional[np.ndarray] = None,
        color_range: str = 'green'
    ) -> Dict:
        """
        Detect ruler in image and calculate scale

        Args:
            image: Input BGR image
            mask: Optional foreground mask to limit search area
            color_range: Color of the ruler ('green', 'yellow', 'auto')

        Returns:
            Dictionary with ruler info:
                - contour: Ruler contour
                - bbox: Bounding box (x, y, w, h)
                - length_pixels: Length in pixels
                - pixels_per_cm: Conversion ratio
                - orientation: 'vertical' or 'horizontal'
        """
        # Convert to HSV for color-based detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for common ruler colors
        # Expanded ranges to catch rulers with markings and variations
        color_ranges = {
            'green': (np.array([30, 20, 20]), np.array([90, 255, 255])),  # Very wide green range
            'yellow': (np.array([15, 80, 80]), np.array([40, 255, 255])),
        }

        if color_range == 'auto':
            # Try all color ranges
            best_ruler = None
            for color_name, (lower, upper) in color_ranges.items():
                try:
                    ruler = self._detect_ruler_by_color(hsv, lower, upper, mask, image)
                    if ruler and (best_ruler is None or ruler['area'] > best_ruler.get('area', 0)):
                        best_ruler = ruler
                except:
                    continue

            if best_ruler is None:
                raise ValueError("No ruler detected with auto color detection")

            return best_ruler

        else:
            lower, upper = color_ranges.get(color_range, color_ranges['green'])
            return self._detect_ruler_by_color(hsv, lower, upper, mask, image)

    def _detect_ruler_by_color(
        self,
        hsv: np.ndarray,
        lower_bound: np.ndarray,
        upper_bound: np.ndarray,
        mask: Optional[np.ndarray],
        original_image: np.ndarray
    ) -> Dict:
        """Detect ruler using color segmentation"""

        # Create color mask with more tolerant bounds for rulers with markings
        # Expand green range to catch ruler with printed numbers
        lower_expanded = lower_bound.copy()
        upper_expanded = upper_bound.copy()

        # Increase saturation and value tolerance for marked rulers
        lower_expanded[1] = max(0, lower_expanded[1] - 40)  # Lower saturation threshold
        lower_expanded[2] = max(0, lower_expanded[2] - 40)  # Lower value threshold
        upper_expanded[2] = 255  # Accept all values

        ruler_mask = cv2.inRange(hsv, lower_expanded, upper_expanded)

        # If a foreground mask is provided, combine them
        if mask is not None:
            ruler_mask = cv2.bitwise_and(ruler_mask, mask)

        # Simple morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        ruler_mask = cv2.morphologyEx(ruler_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        ruler_mask = cv2.morphologyEx(ruler_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(ruler_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No ruler contours found")

        # Find the most ruler-like contour (elongated shape + large area + position)
        ruler_candidates = []
        image_width = original_image.shape[1]
        image_height = original_image.shape[0]

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # Minimum area threshold
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Calculate elongation (aspect ratio)
            elongation = max(w, h) / max(min(w, h), 1)

            # Rulers are typically very elongated (aspect ratio > 2)
            # Lowered threshold to catch rulers with markings and variations
            if elongation > 2:
                # Spatial scoring: rulers are usually near edges
                # Calculate distance from left edge
                distance_from_left = x / image_width

                # Boost score if near left edge (where ruler typically is)
                position_bonus = 1.0
                if distance_from_left < 0.2:  # Within 20% from left edge
                    position_bonus = 2.0

                # Score based on elongation, area, and position
                score = elongation * np.sqrt(area) * position_bonus

                ruler_candidates.append({
                    'contour': contour,
                    'elongation': elongation,
                    'area': area,
                    'score': score,
                    'bbox': (x, y, w, h),
                    'position': distance_from_left
                })

        if not ruler_candidates:
            raise ValueError("No elongated contour found (ruler should have high aspect ratio > 2)")

        # Sort by score (combination of elongation and area)
        ruler_candidates.sort(key=lambda x: x['score'], reverse=True)
        best_candidate = ruler_candidates[0]
        ruler_contour = best_candidate['contour']

        # Get bounding box
        x, y, w, h = cv2.boundingRect(ruler_contour)

        # Determine orientation
        orientation = 'vertical' if h > w else 'horizontal'

        # Calculate length in pixels using extreme points (more accurate than bbox)
        # Find the two most distant points on the contour
        if len(ruler_contour) > 0:
            # Get extreme points
            leftmost = tuple(ruler_contour[ruler_contour[:, :, 0].argmin()][0])
            rightmost = tuple(ruler_contour[ruler_contour[:, :, 0].argmax()][0])
            topmost = tuple(ruler_contour[ruler_contour[:, :, 1].argmin()][0])
            bottommost = tuple(ruler_contour[ruler_contour[:, :, 1].argmax()][0])

            # Calculate distances
            horizontal_dist = np.sqrt((rightmost[0] - leftmost[0])**2 + (rightmost[1] - leftmost[1])**2)
            vertical_dist = np.sqrt((bottommost[0] - topmost[0])**2 + (bottommost[1] - topmost[1])**2)

            # Use the longer distance as ruler length
            length_pixels = max(horizontal_dist, vertical_dist)
        else:
            # Fallback to bbox
            length_pixels = max(w, h)

        # Calculate pixels per cm
        pixels_per_cm = length_pixels / self.known_length_cm

        ruler_info = {
            'contour': ruler_contour,
            'bbox': (x, y, w, h),
            'length_pixels': length_pixels,
            'pixels_per_cm': pixels_per_cm,
            'orientation': orientation,
            'area': cv2.contourArea(ruler_contour)
        }

        if self.debug:
            self._show_debug(original_image, ruler_mask, ruler_info)

        return ruler_info

    def calibrate_with_manual_points(
        self,
        image: np.ndarray,
        point1: Tuple[int, int],
        point2: Tuple[int, int],
        distance_cm: float
    ) -> float:
        """
        Manual calibration using two points with known distance

        Args:
            image: Input image
            point1: First point (x, y)
            point2: Second point (x, y)
            distance_cm: Known distance between points in cm

        Returns:
            pixels_per_cm: Conversion ratio
        """
        # Calculate pixel distance
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        pixels_distance = np.sqrt(dx**2 + dy**2)

        # Calculate pixels per cm
        pixels_per_cm = pixels_distance / distance_cm

        if self.debug:
            print(f"Manual calibration:")
            print(f"  Point 1: {point1}")
            print(f"  Point 2: {point2}")
            print(f"  Distance: {distance_cm} cm")
            print(f"  Pixels: {pixels_distance:.2f} px")
            print(f"  Scale: {pixels_per_cm:.2f} px/cm")

        return pixels_per_cm

    def _show_debug(self, original, ruler_mask, ruler_info):
        """Show debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Original with ruler bbox
        img_with_bbox = original.copy()
        x, y, w, h = ruler_info['bbox']
        cv2.rectangle(img_with_bbox, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.drawContours(img_with_bbox, [ruler_info['contour']], -1, (255, 0, 0), 2)

        axes[0].imshow(cv2.cvtColor(img_with_bbox, cv2.COLOR_BGR2RGB))
        axes[0].set_title(f"Detected Ruler ({ruler_info['orientation']})")
        axes[0].axis('off')

        # Ruler mask
        axes[1].imshow(ruler_mask, cmap='gray')
        axes[1].set_title(f"Ruler Mask\n{ruler_info['length_pixels']:.0f}px = {self.known_length_cm}cm")
        axes[1].axis('off')

        plt.tight_layout()
        plt.savefig('debug_ruler_detection.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Debug visualization saved to debug_ruler_detection.png")
        print(f"📏 Ruler detected: {ruler_info['length_pixels']:.0f} pixels = {self.known_length_cm} cm")
        print(f"📏 Scale: {ruler_info['pixels_per_cm']:.2f} pixels/cm")
