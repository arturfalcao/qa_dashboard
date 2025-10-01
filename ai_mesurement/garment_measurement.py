"""
Garment Measurement Module
Calculate real-world dimensions of garments using calibrated scale
"""

import cv2
import numpy as np
from typing import Dict, Tuple, List


class GarmentMeasurer:
    """Measure garment dimensions using calibrated pixel-to-cm scale"""

    def __init__(self, pixels_per_cm: float, debug: bool = False):
        """
        Args:
            pixels_per_cm: Calibration ratio (pixels per centimeter)
            debug: Enable debug visualizations
        """
        self.pixels_per_cm = pixels_per_cm
        self.debug = debug

    def measure_garment(
        self,
        image: np.ndarray,
        garment_mask: np.ndarray,
        garment_info: Dict
    ) -> Dict:
        """
        Measure garment dimensions

        Args:
            image: Original BGR image
            garment_mask: Binary mask of the garment
            garment_info: Dictionary with garment contour and bbox

        Returns:
            Dictionary with measurements:
                - height_cm: Height (top to bottom)
                - width_cm: Width (left to right)
                - bbox_cm: Bounding box in cm (x, y, w, h)
                - area_cm2: Area in square centimeters
                - extreme_points: Dictionary with top, bottom, left, right points
        """
        contour = garment_info['contour']
        x, y, w, h = garment_info['bbox']

        # Convert bounding box to cm
        height_cm = h / self.pixels_per_cm
        width_cm = w / self.pixels_per_cm

        # Find extreme points
        extreme_points = self._find_extreme_points(contour)

        # Calculate distances between extreme points
        top_to_bottom_px = np.sqrt(
            (extreme_points['bottom'][0] - extreme_points['top'][0])**2 +
            (extreme_points['bottom'][1] - extreme_points['top'][1])**2
        )
        left_to_right_px = np.sqrt(
            (extreme_points['right'][0] - extreme_points['left'][0])**2 +
            (extreme_points['right'][1] - extreme_points['left'][1])**2
        )

        # Convert to cm
        top_to_bottom_cm = top_to_bottom_px / self.pixels_per_cm
        left_to_right_cm = left_to_right_px / self.pixels_per_cm

        # Calculate area
        area_px = cv2.contourArea(contour)
        area_cm2 = area_px / (self.pixels_per_cm ** 2)

        measurements = {
            # Bounding box measurements (axis-aligned)
            'bbox_height_cm': height_cm,
            'bbox_width_cm': width_cm,
            'bbox_cm': (x / self.pixels_per_cm, y / self.pixels_per_cm, width_cm, height_cm),

            # Actual measurements (extreme points)
            'height_cm': top_to_bottom_cm,
            'width_cm': left_to_right_cm,

            # Area
            'area_cm2': area_cm2,

            # Extreme points (for visualization)
            'extreme_points': extreme_points,

            # Pixels per cm (for reference)
            'pixels_per_cm': self.pixels_per_cm
        }

        if self.debug:
            self._show_debug(image, garment_mask, measurements)

        return measurements

    def _find_extreme_points(self, contour: np.ndarray) -> Dict:
        """
        Find extreme points of the garment contour

        Args:
            contour: Garment contour

        Returns:
            Dictionary with top, bottom, left, right extreme points
        """
        # Get extreme points
        leftmost = tuple(contour[contour[:, :, 0].argmin()][0])
        rightmost = tuple(contour[contour[:, :, 0].argmax()][0])
        topmost = tuple(contour[contour[:, :, 1].argmin()][0])
        bottommost = tuple(contour[contour[:, :, 1].argmax()][0])

        return {
            'top': topmost,
            'bottom': bottommost,
            'left': leftmost,
            'right': rightmost
        }

    def measure_specific_dimension(
        self,
        point1: Tuple[int, int],
        point2: Tuple[int, int]
    ) -> float:
        """
        Measure distance between two specific points

        Args:
            point1: First point (x, y) in pixels
            point2: Second point (x, y) in pixels

        Returns:
            Distance in centimeters
        """
        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        distance_px = np.sqrt(dx**2 + dy**2)
        distance_cm = distance_px / self.pixels_per_cm

        return distance_cm

    def _show_debug(self, image, garment_mask, measurements):
        """Show debug visualization with measurements"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Create visualization image
        vis_image = image.copy()

        # Draw garment mask overlay
        mask_overlay = np.zeros_like(vis_image)
        mask_overlay[garment_mask > 0] = [0, 255, 0]
        vis_image = cv2.addWeighted(vis_image, 0.7, mask_overlay, 0.3, 0)

        # Draw extreme points
        points = measurements['extreme_points']
        for name, point in points.items():
            cv2.circle(vis_image, point, 8, (255, 0, 0), -1)
            cv2.putText(
                vis_image,
                name.capitalize(),
                (point[0] + 15, point[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        # Draw measurement lines
        # Height line
        cv2.line(
            vis_image,
            points['top'],
            points['bottom'],
            (0, 255, 255),
            3
        )

        # Width line
        cv2.line(
            vis_image,
            points['left'],
            points['right'],
            (255, 0, 255),
            3
        )

        # Show visualization
        axes[0].imshow(cv2.cvtColor(vis_image, cv2.COLOR_BGR2RGB))
        axes[0].set_title('Measurement Points')
        axes[0].axis('off')

        # Show mask with bounding box
        mask_rgb = cv2.cvtColor(garment_mask, cv2.COLOR_GRAY2RGB)
        x, y, w, h = measurements['bbox_cm']
        x_px = int(x * self.pixels_per_cm)
        y_px = int(y * self.pixels_per_cm)
        w_px = int(w * self.pixels_per_cm)
        h_px = int(h * self.pixels_per_cm)
        cv2.rectangle(mask_rgb, (x_px, y_px), (x_px + w_px, y_px + h_px), (0, 255, 0), 3)

        axes[1].imshow(mask_rgb)
        axes[1].set_title('Garment Mask with BBox')
        axes[1].axis('off')

        # Add text with measurements
        text = f"""
        Measurements:
        Height: {measurements['height_cm']:.2f} cm
        Width: {measurements['width_cm']:.2f} cm
        Area: {measurements['area_cm2']:.2f} cm²
        Scale: {self.pixels_per_cm:.2f} px/cm
        """

        fig.text(0.5, 0.02, text, ha='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.savefig('debug_measurements.png', dpi=150, bbox_inches='tight')
        plt.close()

        print("✅ Debug visualization saved to debug_measurements.png")
        print(f"\n📏 Garment Measurements:")
        print(f"   Height: {measurements['height_cm']:.2f} cm (bbox: {measurements['bbox_height_cm']:.2f} cm)")
        print(f"   Width:  {measurements['width_cm']:.2f} cm (bbox: {measurements['bbox_width_cm']:.2f} cm)")
        print(f"   Area:   {measurements['area_cm2']:.2f} cm²")
