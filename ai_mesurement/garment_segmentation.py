"""
Garment Segmentation Module
Removes background and isolates apparel from images
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class GarmentSegmenter:
    """Segment garment from background using color-based and contour methods"""

    def __init__(self, debug: bool = False):
        self.debug = debug

    def segment_by_color(
        self,
        image: np.ndarray,
        background_color_range: Optional[Tuple[np.ndarray, np.ndarray]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Segment garment from background using color-based segmentation

        Args:
            image: Input BGR image
            background_color_range: Optional (lower_hsv, upper_hsv) for background color

        Returns:
            mask: Binary mask where garment is white (255)
            segmented: Image with background removed
        """
        # Convert to HSV for better color segmentation
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        if background_color_range is None:
            # Auto-detect background color (assume it's the most common color in corners)
            background_color_range = self._detect_background_color(hsv)

        lower_bg, upper_bg = background_color_range

        # Create mask for background
        bg_mask = cv2.inRange(hsv, lower_bg, upper_bg)

        # Invert to get foreground (garment + ruler + hand)
        fg_mask = cv2.bitwise_not(bg_mask)

        # Apply morphological operations to clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Fill holes
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            cv2.drawContours(fg_mask, [contour], -1, 255, -1)

        # Apply mask to image
        segmented = cv2.bitwise_and(image, image, mask=fg_mask)

        if self.debug:
            self._show_debug(image, bg_mask, fg_mask, segmented)

        return fg_mask, segmented

    def _detect_background_color(self, hsv: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Auto-detect background color from image corners

        Args:
            hsv: Image in HSV color space

        Returns:
            (lower_bound, upper_bound) for background color in HSV
        """
        h, w = hsv.shape[:2]
        corner_size = 50

        # Sample corners
        corners = [
            hsv[0:corner_size, 0:corner_size],  # Top-left
            hsv[0:corner_size, w-corner_size:w],  # Top-right
            hsv[h-corner_size:h, 0:corner_size],  # Bottom-left
            hsv[h-corner_size:h, w-corner_size:w]  # Bottom-right
        ]

        # Get median color from all corners
        corner_pixels = np.vstack([corner.reshape(-1, 3) for corner in corners])
        median_color = np.median(corner_pixels, axis=0).astype(np.uint8)

        # Define range around median color
        # Wider range for turquoise/cyan backgrounds
        h_range = 15  # Hue tolerance
        s_range = 60  # Saturation tolerance
        v_range = 60  # Value tolerance

        lower_bound = np.array([
            max(0, median_color[0] - h_range),
            max(0, median_color[1] - s_range),
            max(0, median_color[2] - v_range)
        ])

        upper_bound = np.array([
            min(179, median_color[0] + h_range),
            min(255, median_color[1] + s_range),
            min(255, median_color[2] + v_range)
        ])

        return lower_bound, upper_bound

    def isolate_garment(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        min_area_ratio: float = 0.05
    ) -> Tuple[np.ndarray, dict]:
        """
        Isolate the main garment from the mask (exclude ruler, hands, etc.)

        Args:
            image: Original BGR image
            mask: Binary mask with all foreground objects
            min_area_ratio: Minimum contour area as ratio of image area

        Returns:
            garment_mask: Binary mask with only the garment
            garment_info: Dictionary with garment contour and bounding box
        """
        # Find all contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No contours found in mask")

        # Filter contours by area and shape
        image_area = image.shape[0] * image.shape[1]
        min_area = image_area * min_area_ratio

        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            # Check aspect ratio to exclude ruler (very elongated)
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / max(min(w, h), 1)

            # Garments typically have aspect ratio < 3
            # Rulers are much more elongated (aspect_ratio > 5)
            if aspect_ratio < 4:
                valid_contours.append((contour, area))

        if not valid_contours:
            # If no valid contours, use the largest one
            largest_contour = max(contours, key=cv2.contourArea)
            valid_contours = [(largest_contour, cv2.contourArea(largest_contour))]

        # Sort by area and take the largest (should be the garment)
        valid_contours.sort(key=lambda x: x[1], reverse=True)
        garment_contour = valid_contours[0][0]

        # Create mask with only garment
        garment_mask = np.zeros_like(mask)
        cv2.drawContours(garment_mask, [garment_contour], -1, 255, -1)

        # Get bounding box
        x, y, w, h = cv2.boundingRect(garment_contour)

        garment_info = {
            'contour': garment_contour,
            'bbox': (x, y, w, h),
            'area': cv2.contourArea(garment_contour)
        }

        return garment_mask, garment_info

    def _show_debug(self, original, bg_mask, fg_mask, segmented):
        """Show debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        axes[0, 0].imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('Original Image')
        axes[0, 0].axis('off')

        axes[0, 1].imshow(bg_mask, cmap='gray')
        axes[0, 1].set_title('Background Mask')
        axes[0, 1].axis('off')

        axes[1, 0].imshow(fg_mask, cmap='gray')
        axes[1, 0].set_title('Foreground Mask')
        axes[1, 0].axis('off')

        axes[1, 1].imshow(cv2.cvtColor(segmented, cv2.COLOR_BGR2RGB))
        axes[1, 1].set_title('Segmented Result')
        axes[1, 1].axis('off')

        plt.tight_layout()
        plt.savefig('debug_segmentation.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("✅ Debug visualization saved to debug_segmentation.png")
