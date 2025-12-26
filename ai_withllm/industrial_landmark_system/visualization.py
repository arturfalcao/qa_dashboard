"""
Visualization Module for Industrial Landmark Detection

Provides comprehensive visualization tools for:
1. Landmark detection results
2. Measurement overlays
3. Skeleton connections
4. Confidence heatmaps
5. QC reports

Designed for both debugging and production QC reporting.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import logging

from .landmark_schemas import (
    LandmarkSchema,
    get_schema_for_category,
    get_skeleton_connections,
    SemanticGroup,
)
from .measurement_engine import MeasurementReport, SingleMeasurement, MeasurementStatus
from .hrnet_detector import DetectionResult

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    """Configuration for visualization"""
    # Colors (BGR format)
    landmark_color: Tuple[int, int, int] = (0, 255, 0)  # Green
    skeleton_color: Tuple[int, int, int] = (255, 255, 0)  # Cyan
    measurement_color: Tuple[int, int, int] = (0, 200, 255)  # Orange
    text_color: Tuple[int, int, int] = (255, 255, 255)  # White
    pass_color: Tuple[int, int, int] = (0, 255, 0)  # Green
    fail_color: Tuple[int, int, int] = (0, 0, 255)  # Red
    warning_color: Tuple[int, int, int] = (0, 165, 255)  # Orange

    # Sizes
    landmark_radius: int = 6
    skeleton_thickness: int = 2
    measurement_thickness: int = 2
    font_scale: float = 0.5
    font_thickness: int = 1

    # Display options
    show_landmark_ids: bool = True
    show_landmark_names: bool = False
    show_confidence: bool = True
    show_skeleton: bool = True
    show_measurements: bool = True
    confidence_threshold: float = 0.3

    # Semantic group colors
    group_colors: Dict[str, Tuple[int, int, int]] = None

    def __post_init__(self):
        if self.group_colors is None:
            self.group_colors = {
                SemanticGroup.COLLAR.value: (255, 100, 100),     # Light red
                SemanticGroup.SHOULDER.value: (100, 255, 100),   # Light green
                SemanticGroup.SLEEVE.value: (100, 100, 255),     # Light blue
                SemanticGroup.BODY.value: (255, 255, 100),       # Light cyan
                SemanticGroup.HEM.value: (255, 100, 255),        # Light magenta
                SemanticGroup.WAIST.value: (100, 255, 255),      # Yellow
                SemanticGroup.CROTCH.value: (200, 200, 100),     # Light blue-green
                SemanticGroup.LEG.value: (150, 150, 255),        # Light purple
                SemanticGroup.HOOD.value: (255, 200, 100),       # Light orange
                SemanticGroup.POCKET.value: (100, 200, 200),     # Teal
                SemanticGroup.CUFF.value: (200, 100, 200),       # Purple
            }


class LandmarkVisualizer:
    """
    Visualizes landmark detection results.
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def draw_landmarks(
        self,
        image: np.ndarray,
        landmarks: List[Optional[Tuple[float, float]]],
        confidences: List[float],
        category: str,
        schema: Optional[LandmarkSchema] = None,
    ) -> np.ndarray:
        """
        Draw landmarks on image.

        Args:
            image: BGR image (H, W, 3)
            landmarks: List of (x, y) or None
            confidences: Confidence scores
            category: Garment category
            schema: Optional landmark schema for labeling

        Returns:
            Annotated image
        """
        result = image.copy()

        if schema is None:
            schema = get_schema_for_category(category)

        for i, (landmark, conf) in enumerate(zip(landmarks, confidences)):
            if landmark is None or conf < self.config.confidence_threshold:
                continue

            x, y = int(round(landmark[0])), int(round(landmark[1]))

            # Get color based on semantic group if schema available
            if schema and i in schema.landmarks:
                lm_def = schema.landmarks[i]
                group_key = lm_def.semantic_group.value
                color = self.config.group_colors.get(
                    group_key, self.config.landmark_color
                )
            else:
                color = self.config.landmark_color

            # Adjust color intensity based on confidence
            color = tuple(int(c * (0.5 + conf * 0.5)) for c in color)

            # Draw landmark
            cv2.circle(result, (x, y), self.config.landmark_radius, color, -1)
            cv2.circle(result, (x, y), self.config.landmark_radius + 2, (255, 255, 255), 1)

            # Draw ID or name
            if self.config.show_landmark_ids:
                label = str(i)
                if schema and i in schema.landmarks and self.config.show_landmark_names:
                    label = schema.landmarks[i].name[:10]

                if self.config.show_confidence:
                    label += f" ({conf:.0%})"

                # Position text
                text_x = x + self.config.landmark_radius + 5
                text_y = y + 3

                # Background for text
                (w, h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX,
                    self.config.font_scale * 0.8, 1
                )
                cv2.rectangle(
                    result,
                    (text_x - 2, text_y - h - 2),
                    (text_x + w + 2, text_y + 4),
                    (0, 0, 0), -1
                )
                cv2.putText(
                    result, label, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self.config.font_scale * 0.8,
                    (255, 255, 255), 1, cv2.LINE_AA
                )

        return result

    def draw_skeleton(
        self,
        image: np.ndarray,
        landmarks: List[Optional[Tuple[float, float]]],
        confidences: List[float],
        category: str,
        schema: Optional[LandmarkSchema] = None,
    ) -> np.ndarray:
        """
        Draw skeleton connections between landmarks.
        """
        result = image.copy()

        if schema is None:
            schema = get_schema_for_category(category)

        if schema is None:
            return result

        for idx1, idx2 in schema.skeleton:
            if idx1 >= len(landmarks) or idx2 >= len(landmarks):
                continue

            lm1, lm2 = landmarks[idx1], landmarks[idx2]
            conf1 = confidences[idx1] if idx1 < len(confidences) else 0
            conf2 = confidences[idx2] if idx2 < len(confidences) else 0

            if lm1 is None or lm2 is None:
                continue
            if conf1 < self.config.confidence_threshold or conf2 < self.config.confidence_threshold:
                continue

            p1 = (int(round(lm1[0])), int(round(lm1[1])))
            p2 = (int(round(lm2[0])), int(round(lm2[1])))

            # Adjust color based on confidence
            avg_conf = (conf1 + conf2) / 2
            color = tuple(int(c * (0.3 + avg_conf * 0.7)) for c in self.config.skeleton_color)

            cv2.line(result, p1, p2, color, self.config.skeleton_thickness, cv2.LINE_AA)

        return result


class MeasurementVisualizer:
    """
    Visualizes measurement results on images.
    """

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def draw_measurements(
        self,
        image: np.ndarray,
        report: MeasurementReport,
        show_values: bool = True,
        highlight_failures: bool = True,
    ) -> np.ndarray:
        """
        Draw measurement lines and values on image.

        Args:
            image: BGR image
            report: MeasurementReport with computed measurements
            show_values: Show measurement values
            highlight_failures: Highlight failed measurements

        Returns:
            Annotated image
        """
        result = image.copy()

        for measurement in report.measurements.values():
            if len(measurement.landmark_positions) < 2:
                continue

            # Get line color based on status
            if measurement.status == MeasurementStatus.PASS:
                color = self.config.pass_color
            elif measurement.status == MeasurementStatus.FAIL:
                color = self.config.fail_color
            elif measurement.status == MeasurementStatus.WARNING:
                color = self.config.warning_color
            else:
                color = self.config.measurement_color

            # Draw line between landmarks
            positions = measurement.landmark_positions
            p1 = (int(round(positions[0][0])), int(round(positions[0][1])))

            for i in range(1, len(positions)):
                p2 = (int(round(positions[i][0])), int(round(positions[i][1])))
                cv2.line(result, p1, p2, color, self.config.measurement_thickness, cv2.LINE_AA)
                p1 = p2

            # Draw end markers
            for pos in positions:
                pt = (int(round(pos[0])), int(round(pos[1])))
                cv2.circle(result, pt, 4, color, -1)

            if show_values:
                # Calculate midpoint for label
                if len(positions) == 2:
                    mid_x = int((positions[0][0] + positions[1][0]) / 2)
                    mid_y = int((positions[0][1] + positions[1][1]) / 2)
                else:
                    mid_x = int(np.mean([p[0] for p in positions]))
                    mid_y = int(np.mean([p[1] for p in positions]))

                # Create label
                if measurement.value_mm is not None:
                    label = f"{measurement.name}: {measurement.value_mm:.1f}mm"
                else:
                    label = f"{measurement.name}: {measurement.value_px:.0f}px"

                # Draw label with background
                (w, h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX,
                    self.config.font_scale, 1
                )

                # Offset to avoid overlapping with line
                text_x = mid_x - w // 2
                text_y = mid_y - 10

                cv2.rectangle(
                    result,
                    (text_x - 3, text_y - h - 3),
                    (text_x + w + 3, text_y + 5),
                    (0, 0, 0), -1
                )
                cv2.putText(
                    result, label, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self.config.font_scale,
                    color, 1, cv2.LINE_AA
                )

        return result

    def create_measurement_table(
        self,
        report: MeasurementReport,
        width: int = 400,
        row_height: int = 30,
    ) -> np.ndarray:
        """
        Create a measurement summary table as an image.
        """
        # Calculate dimensions
        num_rows = len(report.measurements) + 2  # Header + footer
        height = num_rows * row_height + 20

        # Create table image
        table = np.ones((height, width, 3), dtype=np.uint8) * 40  # Dark gray

        # Header
        cv2.putText(
            table, f"Measurements - {report.category.upper()}",
            (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (255, 255, 255), 2, cv2.LINE_AA
        )

        # Column headers
        y = row_height + 20
        cv2.putText(table, "Measurement", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(table, "Value", (200, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(table, "Status", (300, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Draw separator
        y += 10
        cv2.line(table, (10, y), (width - 10, y), (100, 100, 100), 1)

        # Measurements
        for m in report.measurements.values():
            y += row_height

            # Name
            name = m.name[:20] if len(m.name) > 20 else m.name
            cv2.putText(table, name, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            # Value
            if m.value_mm is not None:
                value_str = f"{m.value_mm:.1f} mm"
            else:
                value_str = f"{m.value_px:.0f} px"
            cv2.putText(table, value_str, (200, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            # Status with color
            status_color = {
                MeasurementStatus.PASS: self.config.pass_color,
                MeasurementStatus.FAIL: self.config.fail_color,
                MeasurementStatus.WARNING: self.config.warning_color,
                MeasurementStatus.NOT_MEASURED: (128, 128, 128),
            }.get(m.status, (128, 128, 128))

            cv2.putText(table, m.status.value.upper(), (300, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)

        # Footer with summary
        y += row_height + 10
        cv2.line(table, (10, y - 10), (width - 10, y - 10), (100, 100, 100), 1)

        status_color = {
            MeasurementStatus.PASS: self.config.pass_color,
            MeasurementStatus.FAIL: self.config.fail_color,
            MeasurementStatus.WARNING: self.config.warning_color,
        }.get(report.overall_status, (128, 128, 128))

        cv2.putText(
            table,
            f"Overall: {report.overall_status.value.upper()} | Confidence: {report.total_confidence:.0%}",
            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1
        )

        return table


class DebugVisualizer:
    """
    Debug visualization tools for development.
    """

    @staticmethod
    def draw_heatmaps(
        image: np.ndarray,
        heatmaps: np.ndarray,
        alpha: float = 0.5,
        colormap: int = cv2.COLORMAP_JET,
    ) -> np.ndarray:
        """
        Overlay heatmaps on image.

        Args:
            image: BGR image
            heatmaps: (N, H, W) heatmaps
            alpha: Blending alpha
            colormap: OpenCV colormap

        Returns:
            Image with heatmap overlay
        """
        h, w = image.shape[:2]

        # Sum all heatmaps
        combined = np.max(heatmaps, axis=0)

        # Normalize to 0-255
        combined = (combined - combined.min()) / (combined.max() - combined.min() + 1e-8)
        combined = (combined * 255).astype(np.uint8)

        # Resize to image size
        combined = cv2.resize(combined, (w, h))

        # Apply colormap
        colored = cv2.applyColorMap(combined, colormap)

        # Blend with image
        result = cv2.addWeighted(image, 1 - alpha, colored, alpha, 0)

        return result

    @staticmethod
    def draw_grid(
        image: np.ndarray,
        grid_size: int = 50,
        color: Tuple[int, int, int] = (100, 100, 100),
    ) -> np.ndarray:
        """
        Draw a grid overlay for spatial reference.
        """
        result = image.copy()
        h, w = image.shape[:2]

        # Vertical lines
        for x in range(0, w, grid_size):
            cv2.line(result, (x, 0), (x, h), color, 1)

        # Horizontal lines
        for y in range(0, h, grid_size):
            cv2.line(result, (0, y), (w, y), color, 1)

        return result

    @staticmethod
    def create_confidence_chart(
        confidences: List[float],
        width: int = 600,
        height: int = 200,
    ) -> np.ndarray:
        """
        Create a bar chart of landmark confidences.
        """
        chart = np.ones((height, width, 3), dtype=np.uint8) * 255

        if not confidences:
            return chart

        n = len(confidences)
        bar_width = max(1, width // n)
        max_bar_height = height - 40

        for i, conf in enumerate(confidences):
            x = i * bar_width
            bar_height = int(conf * max_bar_height)

            # Color based on confidence
            if conf > 0.5:
                color = (0, 200, 0)
            elif conf > 0.3:
                color = (0, 165, 255)
            else:
                color = (0, 0, 200)

            cv2.rectangle(
                chart,
                (x, height - 20 - bar_height),
                (x + bar_width - 1, height - 20),
                color, -1
            )

        # X-axis
        cv2.line(chart, (0, height - 20), (width, height - 20), (0, 0, 0), 1)

        # Label
        cv2.putText(
            chart, "Landmark Confidences",
            (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (0, 0, 0), 1
        )

        return chart


def visualize_detection(
    image: np.ndarray,
    detection: DetectionResult,
    config: Optional[VisualizationConfig] = None,
) -> np.ndarray:
    """
    Convenience function to visualize detection results.
    """
    config = config or VisualizationConfig()
    landmark_viz = LandmarkVisualizer(config)

    result = image.copy()

    # Draw skeleton first (under landmarks)
    if config.show_skeleton:
        result = landmark_viz.draw_skeleton(
            result,
            detection.landmarks,
            detection.confidences,
            detection.category,
        )

    # Draw landmarks
    result = landmark_viz.draw_landmarks(
        result,
        detection.landmarks,
        detection.confidences,
        detection.category,
    )

    # Add header info
    info = f"Category: {detection.category} | Time: {detection.inference_time_ms:.0f}ms"
    cv2.putText(
        result, info,
        (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
        0.8, (0, 255, 0), 2, cv2.LINE_AA
    )

    return result


def visualize_measurements(
    image: np.ndarray,
    report: MeasurementReport,
    config: Optional[VisualizationConfig] = None,
) -> np.ndarray:
    """
    Convenience function to visualize measurements.
    """
    config = config or VisualizationConfig()
    measurement_viz = MeasurementVisualizer(config)

    result = measurement_viz.draw_measurements(image, report)

    return result


def create_full_report(
    image: np.ndarray,
    detection: DetectionResult,
    report: MeasurementReport,
    config: Optional[VisualizationConfig] = None,
) -> np.ndarray:
    """
    Create a full visual report combining detection and measurements.
    """
    config = config or VisualizationConfig()

    # Visualize detection
    annotated = visualize_detection(image, detection, config)

    # Add measurements
    annotated = visualize_measurements(annotated, report, config)

    # Create measurement table
    measurement_viz = MeasurementVisualizer(config)
    table = measurement_viz.create_measurement_table(report)

    # Combine image and table
    h1, w1 = annotated.shape[:2]
    h2, w2 = table.shape[:2]

    # Resize table to match image height
    scale = h1 / h2
    new_w2 = int(w2 * scale)
    table_resized = cv2.resize(table, (new_w2, h1))

    # Concatenate horizontally
    combined = np.hstack([annotated, table_resized])

    return combined
