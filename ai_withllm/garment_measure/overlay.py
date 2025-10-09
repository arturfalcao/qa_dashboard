#!/usr/bin/env python3
"""
Overlay visualization module for measurement results.
Creates annotated images with landmarks and measurement lines.
"""

import cv2
import numpy as np
from typing import Dict, Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class OverlayGenerator:
    """
    Generates visual overlays for measurement visualization.
    """

    def __init__(self):
        """Initialize overlay generator with default styles."""
        # Color scheme
        self.colors = {
            'landmark': (0, 255, 0),      # Green
            'measurement': (255, 0, 0),    # Blue
            'text': (255, 255, 255),       # White
            'text_bg': (0, 0, 0),          # Black
            'scale_bar': (0, 255, 255),    # Yellow
            'confidence_high': (0, 255, 0), # Green
            'confidence_mid': (255, 255, 0), # Cyan
            'confidence_low': (0, 0, 255),   # Red
        }

        # Drawing parameters
        self.landmark_radius = 5
        self.line_thickness = 2
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.5
        self.font_thickness = 1

    def create_overlay(self, image: np.ndarray,
                      landmarks: Dict[str, Tuple[float, float, float]],
                      measurements: Dict[str, float],
                      measurement_definitions: Dict[str, Tuple[str, str]],
                      uncertainties: Optional[Dict[str, float]] = None,
                      pixel_to_mm: float = 1.0,
                      garment_type: str = '',
                      mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Create complete measurement overlay.

        Args:
            image: Original image
            landmarks: Dictionary of landmark positions
            measurements: Dictionary of measurements in mm
            measurement_definitions: Definition of which landmarks form measurements
            uncertainties: Optional measurement uncertainties
            pixel_to_mm: Scale factor for scale bar
            garment_type: Type of garment for title
            mask: Optional segmentation mask to show

        Returns:
            Annotated image
        """
        # Start with copy of original
        overlay = image.copy()

        # Optionally show mask as semi-transparent overlay
        if mask is not None:
            mask_overlay = np.zeros_like(overlay)
            mask_overlay[mask > 0] = [0, 100, 0]  # Dark green
            overlay = cv2.addWeighted(overlay, 0.9, mask_overlay, 0.1, 0)

        # Draw measurement lines
        overlay = self.draw_measurement_lines(overlay, landmarks, measurement_definitions,
                                             measurements, uncertainties)

        # Draw landmarks
        overlay = self.draw_landmarks(overlay, landmarks)

        # Add measurement labels
        overlay = self.add_measurement_labels(overlay, measurements, uncertainties)

        # Add scale bar
        overlay = self.add_scale_bar(overlay, pixel_to_mm)

        # Add title
        if garment_type:
            overlay = self.add_title(overlay, f"Garment Type: {garment_type.title()}")

        # Add legend
        overlay = self.add_legend(overlay)

        return overlay

    def draw_landmarks(self, image: np.ndarray,
                      landmarks: Dict[str, Tuple[float, float, float]]) -> np.ndarray:
        """
        Draw landmarks with confidence-based coloring.

        Args:
            image: Image to draw on
            landmarks: Dictionary of landmark positions with confidence

        Returns:
            Image with landmarks drawn
        """
        for name, (x, y, conf) in landmarks.items():
            # Choose color based on confidence
            if conf > 0.8:
                color = self.colors['confidence_high']
            elif conf > 0.6:
                color = self.colors['confidence_mid']
            else:
                color = self.colors['confidence_low']

            # Draw circle
            cv2.circle(image, (int(x), int(y)), self.landmark_radius,
                      color, -1)

            # Draw white border for visibility
            cv2.circle(image, (int(x), int(y)), self.landmark_radius + 1,
                      (255, 255, 255), 1)

            # Add small label
            label = name.split('_')[0][:3]  # Abbreviated name
            self.add_text_with_background(image, label,
                                         (int(x) + 8, int(y) - 5),
                                         scale=0.3)

        return image

    def draw_measurement_lines(self, image: np.ndarray,
                               landmarks: Dict[str, Tuple[float, float, float]],
                               definitions: Dict[str, Tuple[str, str]],
                               measurements: Dict[str, float],
                               uncertainties: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Draw measurement lines between landmarks.

        Args:
            image: Image to draw on
            landmarks: Dictionary of landmark positions
            definitions: Measurement definitions (point pairs)
            measurements: Measurement values in mm
            uncertainties: Optional uncertainties

        Returns:
            Image with measurement lines
        """
        for measure_name, (point1_name, point2_name) in definitions.items():
            if point1_name in landmarks and point2_name in landmarks:
                pt1 = (int(landmarks[point1_name][0]), int(landmarks[point1_name][1]))
                pt2 = (int(landmarks[point2_name][0]), int(landmarks[point2_name][1]))

                # Draw line
                cv2.line(image, pt1, pt2, self.colors['measurement'],
                        self.line_thickness)

                # Draw arrow ends
                self.draw_arrow_end(image, pt1, pt2, self.colors['measurement'])
                self.draw_arrow_end(image, pt2, pt1, self.colors['measurement'])

                # Add measurement value at midpoint
                if measure_name in measurements:
                    mid_x = (pt1[0] + pt2[0]) // 2
                    mid_y = (pt1[1] + pt2[1]) // 2

                    value = measurements[measure_name]
                    if uncertainties and measure_name in uncertainties:
                        label = f"{value:.0f}±{uncertainties[measure_name]:.0f}mm"
                    else:
                        label = f"{value:.0f}mm"

                    self.add_text_with_background(image, label,
                                                 (mid_x, mid_y - 10))

        return image

    def draw_arrow_end(self, image: np.ndarray, pt1: Tuple[int, int],
                      pt2: Tuple[int, int], color: Tuple[int, int, int]) -> None:
        """Draw arrow end at pt1 pointing away from pt2."""
        # Calculate arrow direction
        dx = pt1[0] - pt2[0]
        dy = pt1[1] - pt2[1]
        length = np.sqrt(dx**2 + dy**2)

        if length > 0:
            # Normalize and scale
            dx = dx / length * 8
            dy = dy / length * 8

            # Calculate arrow points
            perp_dx = -dy * 0.5
            perp_dy = dx * 0.5

            arrow_pt1 = (int(pt1[0] - dx + perp_dx),
                        int(pt1[1] - dy + perp_dy))
            arrow_pt2 = (int(pt1[0] - dx - perp_dx),
                        int(pt1[1] - dy - perp_dy))

            # Draw arrow
            cv2.line(image, pt1, arrow_pt1, color, self.line_thickness)
            cv2.line(image, pt1, arrow_pt2, color, self.line_thickness)

    def add_measurement_labels(self, image: np.ndarray,
                              measurements: Dict[str, float],
                              uncertainties: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Add measurement summary panel.

        Args:
            image: Image to annotate
            measurements: Dictionary of measurements in mm
            uncertainties: Optional uncertainties

        Returns:
            Annotated image
        """
        # Create semi-transparent panel
        panel_height = 30 + len(measurements) * 25
        panel_width = 250
        panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
        panel[:] = (20, 20, 20)  # Dark gray

        # Add measurements
        y_offset = 25
        for name, value in measurements.items():
            if uncertainties and name in uncertainties:
                text = f"{name}: {value:.1f} ± {uncertainties[name]:.1f} mm"
            else:
                text = f"{name}: {value:.1f} mm"

            cv2.putText(panel, text, (10, y_offset),
                       self.font, 0.5, (255, 255, 255), 1)
            y_offset += 25

        # Overlay panel on image
        x_pos = image.shape[1] - panel_width - 10
        y_pos = 10

        # Ensure panel fits
        if y_pos + panel_height <= image.shape[0]:
            roi = image[y_pos:y_pos+panel_height, x_pos:x_pos+panel_width]
            result = cv2.addWeighted(roi, 0.3, panel, 0.7, 0)
            image[y_pos:y_pos+panel_height, x_pos:x_pos+panel_width] = result

        return image

    def add_scale_bar(self, image: np.ndarray, pixel_to_mm: float) -> np.ndarray:
        """
        Add a 100mm scale bar for reference.

        Args:
            image: Image to annotate
            pixel_to_mm: Conversion factor

        Returns:
            Annotated image
        """
        # Calculate scale bar length for 100mm
        scale_mm = 100
        scale_px = int(scale_mm / pixel_to_mm)

        # Position at bottom left
        x_start = 20
        y_pos = image.shape[0] - 40
        x_end = x_start + scale_px

        # Draw scale bar
        cv2.line(image, (x_start, y_pos), (x_end, y_pos),
                self.colors['scale_bar'], 3)

        # Add end marks
        cv2.line(image, (x_start, y_pos - 5), (x_start, y_pos + 5),
                self.colors['scale_bar'], 3)
        cv2.line(image, (x_end, y_pos - 5), (x_end, y_pos + 5),
                self.colors['scale_bar'], 3)

        # Add label
        self.add_text_with_background(image, f"{scale_mm} mm",
                                     (x_start + scale_px // 2 - 20, y_pos - 10))

        # Add scale factor
        scale_text = f"Scale: 1 px = {pixel_to_mm:.3f} mm"
        self.add_text_with_background(image, scale_text,
                                     (x_start, y_pos + 20), scale=0.4)

        return image

    def add_title(self, image: np.ndarray, title: str) -> np.ndarray:
        """Add title to top of image."""
        # Create title bar
        title_height = 40
        title_bar = np.zeros((title_height, image.shape[1], 3), dtype=np.uint8)
        title_bar[:] = (40, 40, 40)  # Dark gray

        # Add title text
        text_size = cv2.getTextSize(title, self.font, 0.8, 2)[0]
        text_x = (image.shape[1] - text_size[0]) // 2
        text_y = (title_height + text_size[1]) // 2

        cv2.putText(title_bar, title, (text_x, text_y),
                   self.font, 0.8, (255, 255, 255), 2)

        # Add timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(title_bar, timestamp, (10, 30),
                   self.font, 0.4, (200, 200, 200), 1)

        # Combine
        result = np.vstack([title_bar, image])
        return result

    def add_legend(self, image: np.ndarray) -> np.ndarray:
        """Add legend for confidence colors."""
        legend_items = [
            ("High Conf (>0.8)", self.colors['confidence_high']),
            ("Mid Conf (0.6-0.8)", self.colors['confidence_mid']),
            ("Low Conf (<0.6)", self.colors['confidence_low'])
        ]

        y_offset = 60
        for label, color in legend_items:
            # Draw colored circle
            cv2.circle(image, (20, y_offset), 5, color, -1)

            # Add label
            cv2.putText(image, label, (35, y_offset + 5),
                       self.font, 0.4, (255, 255, 255), 1)
            y_offset += 20

        return image

    def add_text_with_background(self, image: np.ndarray, text: str,
                                position: Tuple[int, int],
                                scale: float = 0.5) -> None:
        """Add text with dark background for visibility."""
        # Get text size
        text_size = cv2.getTextSize(text, self.font, scale, self.font_thickness)[0]

        # Draw background rectangle
        x, y = position
        padding = 3
        cv2.rectangle(image,
                     (x - padding, y - text_size[1] - padding),
                     (x + text_size[0] + padding, y + padding),
                     self.colors['text_bg'], -1)

        # Draw text
        cv2.putText(image, text, position,
                   self.font, scale, self.colors['text'], self.font_thickness)

    def create_comparison_overlay(self, image: np.ndarray,
                                 manual_measurements: Dict[str, float],
                                 auto_measurements: Dict[str, float],
                                 uncertainties: Optional[Dict[str, float]] = None) -> np.ndarray:
        """
        Create overlay comparing manual vs automated measurements.

        Args:
            image: Original image
            manual_measurements: Manual reference measurements
            auto_measurements: Automated measurements
            uncertainties: Optional uncertainties

        Returns:
            Comparison overlay image
        """
        overlay = image.copy()

        # Create comparison panel
        panel_height = 30 + len(auto_measurements) * 30
        panel_width = 400
        panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
        panel[:] = (20, 20, 20)

        # Header
        cv2.putText(panel, "Measurement Comparison", (10, 20),
                   self.font, 0.6, (255, 255, 255), 1)

        # Measurements
        y_offset = 50
        for name in auto_measurements:
            auto_val = auto_measurements[name]
            manual_val = manual_measurements.get(name, 0)
            diff = auto_val - manual_val

            # Color based on difference
            if abs(diff) < 2:  # Within 2mm
                color = (0, 255, 0)  # Green
            elif abs(diff) < 5:  # Within 5mm
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red

            text = f"{name}: Auto={auto_val:.0f} Manual={manual_val:.0f} Δ={diff:+.0f}mm"
            cv2.putText(panel, text, (10, y_offset),
                       self.font, 0.45, color, 1)
            y_offset += 30

        # Overlay panel
        if 10 + panel_height <= overlay.shape[0]:
            roi = overlay[10:10+panel_height, 10:10+panel_width]
            result = cv2.addWeighted(roi, 0.2, panel, 0.8, 0)
            overlay[10:10+panel_height, 10:10+panel_width] = result

        return overlay


def main():
    """Test overlay generation."""
    # Create test image
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    image[:] = (50, 50, 50)  # Dark gray background

    # Test data
    landmarks = {
        'left_armpit': (200, 250, 0.85),
        'right_armpit': (400, 250, 0.82),
        'neck_center': (300, 150, 0.90),
        'bottom_hem_center': (300, 450, 0.88)
    }

    measurements = {
        'chest': 200.0,
        'hps_length': 300.0
    }

    definitions = {
        'chest': ('left_armpit', 'right_armpit'),
        'hps_length': ('neck_center', 'bottom_hem_center')
    }

    uncertainties = {
        'chest': 1.5,
        'hps_length': 2.0
    }

    # Generate overlay
    generator = OverlayGenerator()
    overlay = generator.create_overlay(
        image, landmarks, measurements, definitions,
        uncertainties, pixel_to_mm=1.0, garment_type='tshirt'
    )

    # Save result
    cv2.imwrite('test_overlay.jpg', overlay)
    print("Saved test overlay to test_overlay.jpg")


if __name__ == '__main__':
    main()