#!/usr/bin/env python3
"""
Measurement Visualization Module
Creates annotated images showing all measurements
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Tuple, List
from garment_classifier import GarmentType


class MeasurementVisualizer:
    """
    Creates professional annotated measurement visualizations
    """

    # Color scheme for different measurement types
    COLORS = {
        'length': (0, 255, 0),  # Green
        'width': (255, 0, 0),   # Blue (BGR)
        'special': (255, 255, 0),  # Cyan
        'annotation': (0, 255, 255),  # Yellow
        'ruler': (255, 0, 255)  # Magenta
    }

    def __init__(self):
        """Initialize visualizer"""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.thickness = 2
        self.arrow_length = 15

    def create_annotated_image(self,
                              image: np.ndarray,
                              mask: np.ndarray,
                              measurements: Dict,
                              garment_type: GarmentType,
                              pixels_per_cm: float,
                              ruler_bbox: Tuple = None,
                              save_path: str = 'annotated_measurements.png') -> np.ndarray:
        """
        Create comprehensive annotated measurement image

        Args:
            image: Original image
            mask: Segmentation mask
            measurements: Dictionary of measurements
            garment_type: Type of garment
            pixels_per_cm: Scale factor
            ruler_bbox: Ruler bounding box (x, y, w, h)
            save_path: Path to save the annotated image

        Returns:
            Annotated image
        """
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 10))

        # Main annotated image (left side)
        ax_main = plt.subplot(1, 2, 1)

        # Create annotated image
        annotated = self._draw_measurements(
            image.copy(), mask, measurements, garment_type, pixels_per_cm
        )

        # Draw ruler location if provided
        if ruler_bbox:
            annotated = self._draw_ruler(annotated, ruler_bbox, pixels_per_cm)

        # Show annotated image
        ax_main.imshow(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        ax_main.set_title(f'{garment_type.value.upper()} - Annotated Measurements',
                         fontsize=14, fontweight='bold')
        ax_main.axis('off')

        # Measurement details panel (right side)
        ax_details = plt.subplot(1, 2, 2)
        ax_details.axis('off')

        # Create measurement summary
        details_text = self._create_measurement_summary(
            measurements, garment_type, pixels_per_cm
        )

        # Add text with formatting
        ax_details.text(0.05, 0.95, details_text,
                       transform=ax_details.transAxes,
                       fontsize=11,
                       fontfamily='monospace',
                       verticalalignment='top',
                       bbox=dict(boxstyle='round',
                               facecolor='lightgray',
                               alpha=0.8,
                               pad=1))

        # Add color legend
        legend_y = 0.3
        legend_items = [
            ('Length/Height', 'green'),
            ('Width/Circumference', 'blue'),
            ('Special (Inseam/Rise)', 'cyan'),
            ('Ruler', 'magenta')
        ]

        ax_details.text(0.05, legend_y, '📏 MEASUREMENT LEGEND:',
                       transform=ax_details.transAxes,
                       fontsize=12, fontweight='bold')

        for i, (label, color) in enumerate(legend_items):
            y_pos = legend_y - 0.05 * (i + 1)

            # Draw color box
            rect = patches.Rectangle((0.05, y_pos - 0.02), 0.03, 0.03,
                                    linewidth=1,
                                    edgecolor='black',
                                    facecolor=color,
                                    transform=ax_details.transAxes)
            ax_details.add_patch(rect)

            # Add label
            ax_details.text(0.1, y_pos, label,
                          transform=ax_details.transAxes,
                          fontsize=10)

        # Main title
        plt.suptitle('🤖 INTELLIGENT GARMENT MEASUREMENT SYSTEM',
                    fontsize=16, fontweight='bold')

        # Save figure
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')

        print(f"✅ Annotated measurement image saved: {save_path}")

        # Also save just the annotated image without the panel
        cv2.imwrite(save_path.replace('.png', '_overlay.png'), annotated)

        plt.close()

        return annotated

    def _draw_measurements(self,
                          image: np.ndarray,
                          mask: np.ndarray,
                          measurements: Dict,
                          garment_type: GarmentType,
                          pixels_per_cm: float) -> np.ndarray:
        """Draw measurement annotations on image"""

        # Get contour for reference
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image

        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)

        # Draw based on garment type
        if garment_type == GarmentType.TROUSERS:
            image = self._annotate_trousers(image, mask, measurements, x, y, w, h, pixels_per_cm)
        elif garment_type == GarmentType.SHIRT:
            image = self._annotate_shirt(image, mask, measurements, x, y, w, h, pixels_per_cm)
        elif garment_type == GarmentType.DRESS:
            image = self._annotate_dress(image, mask, measurements, x, y, w, h, pixels_per_cm)
        else:
            image = self._annotate_basic(image, mask, measurements, x, y, w, h, pixels_per_cm)

        return image

    def _annotate_trousers(self, image: np.ndarray, mask: np.ndarray,
                          measurements: Dict, x: int, y: int, w: int, h: int,
                          pixels_per_cm: float) -> np.ndarray:
        """Annotate trouser measurements"""

        # Length measurement (left side)
        cv2.line(image, (x - 30, y), (x - 30, y + h), self.COLORS['length'], 2)
        cv2.line(image, (x - 40, y), (x - 20, y), self.COLORS['length'], 2)  # Top arrow
        cv2.line(image, (x - 40, y + h), (x - 20, y + h), self.COLORS['length'], 2)  # Bottom arrow

        # Add length label
        if 'length_cm' in measurements:
            label = f"{measurements['length_cm']:.1f}cm"
            self._add_label(image, (x - 100, y + h//2), label, self.COLORS['length'])

        # Waist width (top)
        waist_y = y + int(h * 0.05)
        waist_widths = []
        waist_row = mask[waist_y, x:x+w]
        nonzero = np.nonzero(waist_row)[0]
        if len(nonzero) > 0:
            waist_left = x + nonzero[0]
            waist_right = x + nonzero[-1]
            cv2.line(image, (waist_left, waist_y), (waist_right, waist_y), self.COLORS['width'], 2)
            cv2.circle(image, (waist_left, waist_y), 4, self.COLORS['width'], -1)
            cv2.circle(image, (waist_right, waist_y), 4, self.COLORS['width'], -1)

            if 'waist_width_cm' in measurements:
                label = f"Waist: {measurements['waist_width_cm']:.1f}cm"
                self._add_label(image, ((waist_left + waist_right)//2, waist_y - 20),
                              label, self.COLORS['width'])

        # Hip width
        hip_y = y + int(h * 0.25)
        hip_row = mask[hip_y, x:x+w]
        nonzero = np.nonzero(hip_row)[0]
        if len(nonzero) > 0:
            hip_left = x + nonzero[0]
            hip_right = x + nonzero[-1]
            cv2.line(image, (hip_left, hip_y), (hip_right, hip_y), self.COLORS['width'], 2)
            cv2.circle(image, (hip_left, hip_y), 4, self.COLORS['width'], -1)
            cv2.circle(image, (hip_right, hip_y), 4, self.COLORS['width'], -1)

            if 'hip_width_cm' in measurements:
                label = f"Hip: {measurements['hip_width_cm']:.1f}cm"
                self._add_label(image, ((hip_left + hip_right)//2, hip_y + 25),
                              label, self.COLORS['width'])

        # Inseam (if detected)
        if 'inseam_cm' in measurements and 'rise_cm' in measurements:
            # Find crotch point approximately
            crotch_y = y + int(measurements['rise_cm'] * pixels_per_cm)

            # Draw inseam line (right side)
            cv2.line(image, (x + w + 30, crotch_y), (x + w + 30, y + h),
                    self.COLORS['special'], 2)
            cv2.line(image, (x + w + 20, crotch_y), (x + w + 40, crotch_y),
                    self.COLORS['special'], 2)
            cv2.line(image, (x + w + 20, y + h), (x + w + 40, y + h),
                    self.COLORS['special'], 2)

            label = f"Inseam: {measurements['inseam_cm']:.1f}cm"
            self._add_label(image, (x + w + 50, crotch_y + (y + h - crotch_y)//2),
                          label, self.COLORS['special'])

        # Hem width
        hem_y = y + int(h * 0.95)
        hem_row = mask[hem_y, x:x+w]
        nonzero = np.nonzero(hem_row)[0]
        if len(nonzero) > 0:
            hem_left = x + nonzero[0]
            hem_right = x + nonzero[-1]
            cv2.line(image, (hem_left, hem_y), (hem_right, hem_y), self.COLORS['width'], 2)
            cv2.circle(image, (hem_left, hem_y), 4, self.COLORS['width'], -1)
            cv2.circle(image, (hem_right, hem_y), 4, self.COLORS['width'], -1)

            if 'hem_width_cm' in measurements:
                label = f"Hem: {measurements['hem_width_cm']:.1f}cm"
                self._add_label(image, ((hem_left + hem_right)//2, hem_y + 25),
                              label, self.COLORS['width'])

        return image

    def _annotate_shirt(self, image: np.ndarray, mask: np.ndarray,
                       measurements: Dict, x: int, y: int, w: int, h: int,
                       pixels_per_cm: float) -> np.ndarray:
        """Annotate shirt measurements"""

        # Length measurement
        cv2.line(image, (x - 30, y), (x - 30, y + h), self.COLORS['length'], 2)
        cv2.line(image, (x - 40, y), (x - 20, y), self.COLORS['length'], 2)
        cv2.line(image, (x - 40, y + h), (x - 20, y + h), self.COLORS['length'], 2)

        if 'length_cm' in measurements:
            label = f"{measurements['length_cm']:.1f}cm"
            self._add_label(image, (x - 100, y + h//2), label, self.COLORS['length'])

        # Chest width
        chest_y = y + int(h * 0.3)
        chest_row = mask[chest_y, x:x+w]
        nonzero = np.nonzero(chest_row)[0]
        if len(nonzero) > 0:
            chest_left = x + nonzero[0]
            chest_right = x + nonzero[-1]
            cv2.line(image, (chest_left, chest_y), (chest_right, chest_y), self.COLORS['width'], 2)
            cv2.circle(image, (chest_left, chest_y), 4, self.COLORS['width'], -1)
            cv2.circle(image, (chest_right, chest_y), 4, self.COLORS['width'], -1)

            if 'chest_width_cm' in measurements:
                label = f"Chest: {measurements['chest_width_cm']:.1f}cm"
                self._add_label(image, ((chest_left + chest_right)//2, chest_y - 20),
                              label, self.COLORS['width'])

        # Waist width
        waist_y = y + int(h * 0.5)
        waist_row = mask[waist_y, x:x+w]
        nonzero = np.nonzero(waist_row)[0]
        if len(nonzero) > 0:
            waist_left = x + nonzero[0]
            waist_right = x + nonzero[-1]
            cv2.line(image, (waist_left, waist_y), (waist_right, waist_y), self.COLORS['width'], 2)

            if 'waist_width_cm' in measurements:
                label = f"Waist: {measurements['waist_width_cm']:.1f}cm"
                self._add_label(image, ((waist_left + waist_right)//2, waist_y + 25),
                              label, self.COLORS['width'])

        return image

    def _annotate_dress(self, image: np.ndarray, mask: np.ndarray,
                       measurements: Dict, x: int, y: int, w: int, h: int,
                       pixels_per_cm: float) -> np.ndarray:
        """Annotate dress measurements"""

        # Similar to shirt but with bust/waist/hip measurements
        return self._annotate_shirt(image, mask, measurements, x, y, w, h, pixels_per_cm)

    def _annotate_basic(self, image: np.ndarray, mask: np.ndarray,
                       measurements: Dict, x: int, y: int, w: int, h: int,
                       pixels_per_cm: float) -> np.ndarray:
        """Basic annotation for unknown garments"""

        # Height
        cv2.line(image, (x - 30, y), (x - 30, y + h), self.COLORS['length'], 2)
        if 'height_cm' in measurements:
            label = f"Height: {measurements['height_cm']:.1f}cm"
            self._add_label(image, (x - 100, y + h//2), label, self.COLORS['length'])

        # Width
        cv2.line(image, (x, y - 30), (x + w, y - 30), self.COLORS['width'], 2)
        if 'width_cm' in measurements:
            label = f"Width: {measurements['width_cm']:.1f}cm"
            self._add_label(image, (x + w//2, y - 50), label, self.COLORS['width'])

        return image

    def _draw_ruler(self, image: np.ndarray, ruler_bbox: Tuple, pixels_per_cm: float) -> np.ndarray:
        """Draw ruler annotation"""

        x, y, w, h = ruler_bbox

        # Draw ruler rectangle
        cv2.rectangle(image, (x, y), (x + w, y + h), self.COLORS['ruler'], 2)

        # Add ruler label
        label = f"31cm Ruler ({pixels_per_cm:.1f}px/cm)"
        self._add_label(image, (x + w//2, y - 10), label, self.COLORS['ruler'])

        return image

    def _add_label(self, image: np.ndarray, position: Tuple[int, int],
                   text: str, color: Tuple[int, int, int]):
        """Add text label with background"""

        # Get text size
        (text_width, text_height), _ = cv2.getTextSize(
            text, self.font, self.font_scale, self.thickness
        )

        # Draw background rectangle
        padding = 5
        cv2.rectangle(image,
                     (position[0] - padding, position[1] - text_height - padding),
                     (position[0] + text_width + padding, position[1] + padding),
                     (255, 255, 255),  # White background
                     -1)

        # Draw text
        cv2.putText(image, text, position, self.font,
                   self.font_scale, color, self.thickness)

    def _create_measurement_summary(self, measurements: Dict,
                                   garment_type: GarmentType,
                                   pixels_per_cm: float) -> str:
        """Create formatted measurement summary text"""

        summary = f"""
📊 MEASUREMENT SUMMARY
{'='*40}

🏷️ Garment Type: {garment_type.value.upper()}
📏 Scale: {pixels_per_cm:.2f} pixels/cm

{'='*40}
📐 MEASUREMENTS:
"""

        if garment_type == GarmentType.TROUSERS:
            key_measurements = [
                ('length_cm', 'Total Length'),
                ('waist_width_cm', 'Waist Width'),
                ('waist_circumference_cm', 'Waist Circumference'),
                ('hip_width_cm', 'Hip Width'),
                ('thigh_width_cm', 'Thigh Width'),
                ('knee_width_cm', 'Knee Width'),
                ('hem_width_cm', 'Hem Width'),
                ('inseam_cm', 'Inseam'),
                ('rise_cm', 'Rise')
            ]
        elif garment_type == GarmentType.SHIRT:
            key_measurements = [
                ('length_cm', 'Total Length'),
                ('chest_width_cm', 'Chest Width'),
                ('chest_circumference_cm', 'Chest Circumference'),
                ('waist_width_cm', 'Waist Width'),
                ('hem_width_cm', 'Hem Width'),
                ('shoulder_width_cm', 'Shoulder Width')
            ]
        elif garment_type == GarmentType.DRESS:
            key_measurements = [
                ('length_cm', 'Total Length'),
                ('bust_width_cm', 'Bust Width'),
                ('bust_circumference_cm', 'Bust Circumference'),
                ('waist_width_cm', 'Waist Width'),
                ('hip_width_cm', 'Hip Width'),
                ('hem_width_cm', 'Hem Width')
            ]
        else:
            key_measurements = [
                ('height_cm', 'Height'),
                ('width_cm', 'Width'),
                ('area_cm2', 'Area')
            ]

        for key, label in key_measurements:
            if key in measurements:
                value = measurements[key]
                if 'cm2' in key:
                    summary += f"  • {label:20}: {value:8.0f} cm²\n"
                else:
                    summary += f"  • {label:20}: {value:8.1f} cm\n"

        summary += f"""
{'='*40}
✅ Measurement Complete
"""

        return summary