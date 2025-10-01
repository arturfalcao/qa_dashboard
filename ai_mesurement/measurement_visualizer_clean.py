#!/usr/bin/env python3
"""
Clean Measurement Visualization Module
Creates annotated images with background removed - only fabric with measurements
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, Tuple, List
from garment_classifier_clip import GarmentType
from PIL import Image


class CleanMeasurementVisualizer:
    """
    Creates clean annotated visualizations with only fabric and measurements
    """

    # Color scheme for measurements
    COLORS = {
        'length': (0, 200, 0),  # Green
        'width': (200, 0, 0),   # Blue (BGR)
        'special': (200, 200, 0),  # Cyan
        'annotation': (0, 200, 200),  # Yellow
        'text_bg': (255, 255, 255)  # White for text background
    }

    def __init__(self):
        """Initialize visualizer"""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.8
        self.thickness = 2
        self.line_thickness = 3

    def create_clean_annotated_image(self,
                                     image: np.ndarray,
                                     mask: np.ndarray,
                                     measurements: Dict,
                                     garment_type: GarmentType,
                                     pixels_per_cm: float,
                                     save_path: str = 'clean_annotated.png') -> np.ndarray:
        """
        Create clean annotated image with background removed

        Args:
            image: Original image
            mask: Segmentation mask
            measurements: Dictionary of measurements
            garment_type: Type of garment
            pixels_per_cm: Scale factor
            save_path: Path to save the annotated image

        Returns:
            Clean annotated image with transparent background
        """

        # Step 1: Extract only the garment (remove background)
        garment_only = self._extract_garment(image, mask)

        # Step 2: Create measurement overlay
        measurement_overlay = self._create_measurement_overlay(
            garment_only, mask, measurements, garment_type, pixels_per_cm
        )

        # Step 3: Create final visualization with summary
        self._create_final_visualization(
            measurement_overlay, measurements, garment_type, pixels_per_cm, save_path
        )

        # Step 4: Also save transparent PNG of just garment with measurements
        self._save_transparent_png(measurement_overlay, mask, save_path)

        return measurement_overlay

    def _extract_garment(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Extract only the garment, making background white"""

        # Create white background
        result = np.ones_like(image) * 255

        # Copy only garment pixels
        garment_pixels = mask > 0
        result[garment_pixels] = image[garment_pixels]

        return result

    def _create_measurement_overlay(self,
                                   garment_image: np.ndarray,
                                   mask: np.ndarray,
                                   measurements: Dict,
                                   garment_type: GarmentType,
                                   pixels_per_cm: float) -> np.ndarray:
        """Create measurement annotations directly on garment"""

        # Work on a copy
        annotated = garment_image.copy()

        # Get contour for measurements
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return annotated

        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)

        # Draw measurements based on garment type
        if garment_type == GarmentType.TROUSERS:
            annotated = self._annotate_trousers_clean(
                annotated, mask, measurements, contour, x, y, w, h, pixels_per_cm
            )
        elif garment_type == GarmentType.SHIRT:
            annotated = self._annotate_shirt_clean(
                annotated, mask, measurements, contour, x, y, w, h, pixels_per_cm
            )
        elif garment_type == GarmentType.DRESS:
            annotated = self._annotate_dress_clean(
                annotated, mask, measurements, contour, x, y, w, h, pixels_per_cm
            )
        else:
            annotated = self._annotate_basic_clean(
                annotated, mask, measurements, contour, x, y, w, h, pixels_per_cm
            )

        return annotated

    def _annotate_trousers_clean(self, image: np.ndarray, mask: np.ndarray,
                                 measurements: Dict, contour: np.ndarray,
                                 x: int, y: int, w: int, h: int,
                                 pixels_per_cm: float) -> np.ndarray:
        """Annotate trouser measurements on clean garment using PROPER industry standards"""

        # Extract points from contour
        points = contour.reshape(-1, 2)

        # OUTSEAM (Length) - Vertical line on left side
        if 'outseam_points' in measurements:
            top = measurements['outseam_points']['top']
            bottom = measurements['outseam_points']['bottom']

            # Draw vertical line for outseam
            cv2.line(image, tuple(top), tuple(bottom),
                    self.COLORS['length'], self.line_thickness)

            # Add arrows
            self._draw_arrow(image, tuple(top), 'up', self.COLORS['length'])
            self._draw_arrow(image, tuple(bottom), 'down', self.COLORS['length'])

            # Add label
            if 'outseam_cm' in measurements:
                mid_point = (top[0] - 30, (top[1] + bottom[1])//2)
                self._add_measurement_label(image, mid_point,
                                          f"Outseam: {measurements['outseam_cm']:.1f}cm",
                                          self.COLORS['length'])

        # Waist width - at top of garment
        waist_y = y + int(h * 0.05)
        self._draw_width_measurement(image, mask, waist_y, x, w,
                                    measurements.get('waist_width_cm'),
                                    "Waist", self.COLORS['width'])

        # Hip width - upper third
        hip_y = y + int(h * 0.25)
        self._draw_width_measurement(image, mask, hip_y, x, w,
                                    measurements.get('hip_width_cm'),
                                    "Hip", self.COLORS['width'])

        # Thigh width
        thigh_y = y + int(h * 0.4)
        self._draw_width_measurement(image, mask, thigh_y, x, w,
                                    measurements.get('thigh_width_cm'),
                                    "Thigh", self.COLORS['width'])

        # Knee width
        knee_y = y + int(h * 0.65)
        self._draw_width_measurement(image, mask, knee_y, x, w,
                                    measurements.get('knee_width_cm'),
                                    "Knee", self.COLORS['width'])

        # Hem width
        hem_y = y + int(h * 0.95)
        self._draw_width_measurement(image, mask, hem_y, x, w,
                                    measurements.get('hem_width_cm'),
                                    "Hem", self.COLORS['width'])

        # Inseam if available
        if 'inseam_cm' in measurements and 'rise_cm' in measurements:
            # Find right edge for inseam
            right_points = points[points[:, 0] > x + w * 0.8]
            if len(right_points) > 0:
                crotch_y = y + int(measurements['rise_cm'] * pixels_per_cm)

                # Find point at crotch level
                crotch_points = right_points[np.abs(right_points[:, 1] - crotch_y) < 20]
                if len(crotch_points) > 0:
                    crotch_point = crotch_points[np.argmax(crotch_points[:, 0])]
                    bottom_right = right_points[np.argmax(right_points[:, 1])]

                    # Draw inseam line
                    cv2.line(image, tuple(crotch_point), tuple(bottom_right),
                            self.COLORS['special'], self.line_thickness)

                    # Add label
                    mid_point = ((crotch_point[0] + bottom_right[0])//2 + 30,
                               (crotch_point[1] + bottom_right[1])//2)
                    self._add_measurement_label(image, mid_point,
                                              f"Inseam: {measurements['inseam_cm']:.1f}cm",
                                              self.COLORS['special'])

        return image

    def _annotate_shirt_clean(self, image: np.ndarray, mask: np.ndarray,
                              measurements: Dict, contour: np.ndarray,
                              x: int, y: int, w: int, h: int,
                              pixels_per_cm: float) -> np.ndarray:
        """Annotate shirt measurements on clean garment using PROPER industry standards"""

        # BODY LENGTH - Vertical line from HPS to hem
        if 'body_length_points' in measurements:
            points = measurements['body_length_points']

            # Get top and bottom points
            if 'hps' in points:
                top = points['hps']
                bottom = points['bottom']
            else:
                top = points['top']
                bottom = points['bottom']

            # Draw VERTICAL line (not diagonal!)
            cv2.line(image, tuple(top), tuple(bottom),
                    self.COLORS['length'], self.line_thickness)

            # Add arrows
            self._draw_arrow(image, tuple(top), 'up', self.COLORS['length'])
            self._draw_arrow(image, tuple(bottom), 'down', self.COLORS['length'])

            if 'body_length_cm' in measurements:
                mid_point = (top[0] - 30, (top[1] + bottom[1])//2)
                self._add_measurement_label(image, mid_point,
                                          f"Length: {measurements['body_length_cm']:.1f}cm",
                                          self.COLORS['length'])

        # Chest width
        chest_y = y + int(h * 0.3)
        self._draw_width_measurement(image, mask, chest_y, x, w,
                                    measurements.get('chest_width_cm'),
                                    "Chest", self.COLORS['width'])

        # Waist width
        waist_y = y + int(h * 0.5)
        self._draw_width_measurement(image, mask, waist_y, x, w,
                                    measurements.get('waist_width_cm'),
                                    "Waist", self.COLORS['width'])

        # Hem width
        hem_y = y + int(h * 0.9)
        self._draw_width_measurement(image, mask, hem_y, x, w,
                                    measurements.get('hem_width_cm'),
                                    "Hem", self.COLORS['width'])

        return image

    def _annotate_dress_clean(self, image: np.ndarray, mask: np.ndarray,
                              measurements: Dict, contour: np.ndarray,
                              x: int, y: int, w: int, h: int,
                              pixels_per_cm: float) -> np.ndarray:
        """Annotate dress measurements on clean garment"""

        # Similar to shirt but with bust/waist/hip
        return self._annotate_shirt_clean(image, mask, measurements, contour,
                                         x, y, w, h, pixels_per_cm)

    def _annotate_basic_clean(self, image: np.ndarray, mask: np.ndarray,
                              measurements: Dict, contour: np.ndarray,
                              x: int, y: int, w: int, h: int,
                              pixels_per_cm: float) -> np.ndarray:
        """Basic annotations for unknown garments"""

        points = contour.reshape(-1, 2)

        # Height
        top_point = points[np.argmin(points[:, 1])]
        bottom_point = points[np.argmax(points[:, 1])]

        cv2.line(image, tuple(top_point), tuple(bottom_point),
                self.COLORS['length'], self.line_thickness)

        # Width
        left_point = points[np.argmin(points[:, 0])]
        right_point = points[np.argmax(points[:, 0])]

        cv2.line(image, tuple(left_point), tuple(right_point),
                self.COLORS['width'], self.line_thickness)

        return image

    def _draw_width_measurement(self, image: np.ndarray, mask: np.ndarray,
                                y_pos: int, x_start: int, width: int,
                                measurement_value: float, label: str, color: Tuple):
        """Draw width measurement at specific y position"""

        if y_pos >= mask.shape[0]:
            return

        # Find actual garment edges at this height
        row = mask[y_pos, x_start:x_start+width]
        nonzero = np.nonzero(row)[0]

        if len(nonzero) > 0:
            left_x = x_start + nonzero[0]
            right_x = x_start + nonzero[-1]

            # Draw line
            cv2.line(image, (left_x, y_pos), (right_x, y_pos), color, self.line_thickness)

            # Draw end markers
            cv2.circle(image, (left_x, y_pos), 5, color, -1)
            cv2.circle(image, (right_x, y_pos), 5, color, -1)

            # Add label if measurement available
            if measurement_value:
                mid_x = (left_x + right_x) // 2
                label_text = f"{label}: {measurement_value:.1f}cm"
                self._add_measurement_label(image, (mid_x, y_pos - 10),
                                          label_text, color)

    def _draw_arrow(self, image: np.ndarray, position: Tuple, direction: str, color: Tuple):
        """Draw arrow indicator"""
        x, y = position
        arrow_size = 10

        if direction == 'up':
            cv2.line(image, (x, y), (x-5, y+arrow_size), color, 2)
            cv2.line(image, (x, y), (x+5, y+arrow_size), color, 2)
        elif direction == 'down':
            cv2.line(image, (x, y), (x-5, y-arrow_size), color, 2)
            cv2.line(image, (x, y), (x+5, y-arrow_size), color, 2)
        elif direction == 'left':
            cv2.line(image, (x, y), (x+arrow_size, y-5), color, 2)
            cv2.line(image, (x, y), (x+arrow_size, y+5), color, 2)
        elif direction == 'right':
            cv2.line(image, (x, y), (x-arrow_size, y-5), color, 2)
            cv2.line(image, (x, y), (x-arrow_size, y+5), color, 2)

    def _add_measurement_label(self, image: np.ndarray, position: Tuple[int, int],
                               text: str, color: Tuple[int, int, int]):
        """Add measurement label with semi-transparent background"""

        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(
            text, self.font, self.font_scale, self.thickness
        )

        # Create semi-transparent background
        overlay = image.copy()
        padding = 5
        cv2.rectangle(overlay,
                     (position[0] - padding, position[1] - text_height - padding),
                     (position[0] + text_width + padding, position[1] + padding),
                     (255, 255, 255),  # White background
                     -1)

        # Blend with original (semi-transparent effect)
        cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

        # Draw text
        cv2.putText(image, text, position, self.font,
                   self.font_scale, color, self.thickness)

    def _create_final_visualization(self, annotated_image: np.ndarray,
                                   measurements: Dict, garment_type: GarmentType,
                                   pixels_per_cm: float, save_path: str):
        """Create final visualization with summary panel"""

        fig = plt.figure(figsize=(16, 10))

        # Main annotated image
        ax_main = plt.subplot(1, 2, 1)
        ax_main.imshow(cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB))
        ax_main.set_title(f'{garment_type.value.upper()} - Clean Annotated Measurements',
                         fontsize=14, fontweight='bold')
        ax_main.axis('off')

        # Measurement panel
        ax_details = plt.subplot(1, 2, 2)
        ax_details.axis('off')

        # Create measurement summary
        summary_text = self._create_measurement_summary(measurements, garment_type)

        ax_details.text(0.05, 0.95, summary_text,
                       transform=ax_details.transAxes,
                       fontsize=11,
                       fontfamily='monospace',
                       verticalalignment='top',
                       bbox=dict(boxstyle='round',
                                facecolor='lightgray',
                                alpha=0.9,
                                pad=1))

        # Add legend
        self._add_color_legend(ax_details)

        plt.suptitle('🤖 CLEAN GARMENT MEASUREMENT - FABRIC ONLY',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"✅ Clean annotated image saved: {save_path}")

    def _save_transparent_png(self, annotated_image: np.ndarray, mask: np.ndarray, base_path: str):
        """Save garment with measurements on transparent background"""

        # Convert to RGBA
        b, g, r = cv2.split(annotated_image)

        # Use mask as alpha channel (need to ensure it's binary)
        alpha = (mask > 0).astype(np.uint8) * 255

        # Combine into RGBA image
        rgba_image = cv2.merge([b, g, r, alpha])

        # Save with transparency
        transparent_path = base_path.replace('.png', '_transparent.png')
        cv2.imwrite(transparent_path, rgba_image)

        print(f"✅ Transparent PNG saved: {transparent_path}")

    def _add_color_legend(self, ax):
        """Add color legend to the panel"""

        legend_y = 0.35
        legend_items = [
            ('Length/Height', 'green'),
            ('Width Measurements', 'blue'),
            ('Special (Inseam/Rise)', 'cyan')
        ]

        ax.text(0.05, legend_y, '📏 MEASUREMENT COLORS:',
               transform=ax.transAxes,
               fontsize=12, fontweight='bold')

        for i, (label, color) in enumerate(legend_items):
            y_pos = legend_y - 0.05 * (i + 1)

            rect = patches.Rectangle((0.05, y_pos - 0.02), 0.03, 0.03,
                                    linewidth=1,
                                    edgecolor='black',
                                    facecolor=color,
                                    transform=ax.transAxes)
            ax.add_patch(rect)

            ax.text(0.1, y_pos, label,
                   transform=ax.transAxes,
                   fontsize=10)

    def _create_measurement_summary(self, measurements: Dict, garment_type: GarmentType) -> str:
        """Create formatted measurement summary"""

        summary = f"""
📊 CLEAN MEASUREMENT SUMMARY
{'='*40}

🏷️ Type: {garment_type.value.upper()}
{'='*40}

📐 MEASUREMENTS:
"""

        # List measurements based on type
        if garment_type == GarmentType.TROUSERS:
            measurement_order = [
                ('length_cm', 'Length'),
                ('waist_width_cm', 'Waist'),
                ('hip_width_cm', 'Hip'),
                ('thigh_width_cm', 'Thigh'),
                ('knee_width_cm', 'Knee'),
                ('hem_width_cm', 'Hem'),
                ('inseam_cm', 'Inseam'),
                ('rise_cm', 'Rise')
            ]
        elif garment_type == GarmentType.SHIRT:
            measurement_order = [
                ('length_cm', 'Length'),
                ('chest_width_cm', 'Chest'),
                ('waist_width_cm', 'Waist'),
                ('hem_width_cm', 'Hem')
            ]
        else:
            measurement_order = [(k, k.replace('_cm', '').title()) for k in measurements.keys() if '_cm' in k]

        for key, label in measurement_order:
            if key in measurements:
                value = measurements[key]
                summary += f"  • {label:15}: {value:7.1f} cm\n"

        summary += f"\n{'='*40}\n✅ Background Removed - Fabric Only"

        return summary