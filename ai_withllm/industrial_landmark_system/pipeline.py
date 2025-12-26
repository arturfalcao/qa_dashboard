"""
Industrial Garment Measurement Pipeline

End-to-end pipeline for garment landmark detection and measurement,
inspired by GarmentIQ and Kim et al. (2022).

The pipeline integrates:
1. Image preprocessing and segmentation
2. HRNet-based landmark detection
3. Measurement calculation with validation
4. Visualization and reporting

Designed for production use on an industrial inspection bench.
"""

import cv2
import numpy as np
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
import logging

from .hrnet_detector import IndustrialHRNetDetector, DetectionResult, create_detector
from .segmentation import IndustrialSegmenter, SegmentationResult, create_segmenter
from .measurement_engine import (
    MeasurementEngine,
    MeasurementReport,
    create_measurement_engine,
)
from .measurement_instructions import (
    MeasurementInstructionSet,
    load_measurement_instructions,
)
from .landmark_schemas import (
    get_schema_for_category,
    map_df2_to_industrial,
)
from .visualization import (
    visualize_detection,
    visualize_measurements,
    create_full_report,
    VisualizationConfig,
    LandmarkVisualizer,
    MeasurementVisualizer,
    DebugVisualizer,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the measurement pipeline"""
    # Model paths
    model_path: Optional[str] = None
    device: str = 'auto'

    # Preprocessing
    use_segmentation: bool = True
    use_deep_segmentation: bool = True
    background_color: Optional[Tuple[int, int, int]] = None

    # Detection
    confidence_threshold: float = 0.1
    use_tta: bool = False
    tta_angles: List[float] = field(default_factory=lambda: [-5, 0, 5])

    # Calibration
    px_per_mm: Optional[float] = None

    # Output
    output_dir: Optional[str] = None
    save_visualizations: bool = True
    save_json: bool = True
    save_debug: bool = False


@dataclass
class PipelineResult:
    """Complete result from the measurement pipeline"""
    # Input
    image_path: str
    image_size: Tuple[int, int]

    # Segmentation
    segmentation: Optional[SegmentationResult]
    segmentation_time_ms: float

    # Detection
    detection: DetectionResult
    detection_time_ms: float

    # Measurements
    measurements: MeasurementReport
    measurement_time_ms: float

    # Overall
    total_time_ms: float
    category: str
    success: bool
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "image_path": self.image_path,
            "image_size": self.image_size,
            "category": self.category,
            "success": self.success,
            "errors": self.errors,
            "timing": {
                "segmentation_ms": self.segmentation_time_ms,
                "detection_ms": self.detection_time_ms,
                "measurement_ms": self.measurement_time_ms,
                "total_ms": self.total_time_ms,
            },
            "detection": {
                "num_landmarks": sum(1 for l in self.detection.landmarks if l is not None),
                "inference_time_ms": self.detection.inference_time_ms,
            },
            "measurements": self.measurements.to_dict(),
        }

    def save_json(self, filepath: Union[str, Path]) -> None:
        """Save result to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class IndustrialMeasurementPipeline:
    """
    Main pipeline for industrial garment measurement.

    Usage:
        pipeline = IndustrialMeasurementPipeline(config)
        result = pipeline.process("garment.jpg")
        print(f"Chest width: {result.measurements.measurements['chest_width'].value_mm}mm")
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline.

        Args:
            config: Pipeline configuration. Uses defaults if None.
        """
        self.config = config or PipelineConfig()

        # Initialize components
        logger.info("Initializing Industrial Measurement Pipeline...")

        # Detector
        self.detector = create_detector(
            model_path=self.config.model_path,
            device=self.config.device,
            confidence_threshold=self.config.confidence_threshold,
            use_tta=self.config.use_tta,
            tta_angles=self.config.tta_angles,
        )

        # Segmenter
        if self.config.use_segmentation:
            self.segmenter = create_segmenter(
                use_deep=self.config.use_deep_segmentation,
                background_color=self.config.background_color,
                device=self.config.device,
            )
        else:
            self.segmenter = None

        # Measurement engine
        self.measurement_engine = create_measurement_engine(
            px_per_mm=self.config.px_per_mm,
        )

        # Visualization
        self.viz_config = VisualizationConfig()
        self.landmark_viz = LandmarkVisualizer(self.viz_config)
        self.measurement_viz = MeasurementVisualizer(self.viz_config)

        logger.info("Pipeline initialized successfully")

    def set_calibration(self, px_per_mm: float) -> None:
        """
        Set the calibration factor for physical measurements.

        Args:
            px_per_mm: Pixels per millimeter
        """
        self.config.px_per_mm = px_per_mm
        self.measurement_engine.set_calibration(px_per_mm)
        logger.info(f"Calibration set: {px_per_mm:.4f} px/mm")

    def process(
        self,
        image: Union[str, Path, np.ndarray],
        category_hint: Optional[str] = None,
        target_measurements: Optional[Dict[str, float]] = None,
        output_prefix: Optional[str] = None,
    ) -> PipelineResult:
        """
        Process a garment image through the full pipeline.

        Args:
            image: Image path or BGR numpy array
            category_hint: Optional category to use instead of auto-detection
            target_measurements: Expected values for QC (measurement_id -> mm)
            output_prefix: Prefix for output files (uses image name if None)

        Returns:
            PipelineResult with all detection and measurement data
        """
        total_start = time.time()
        errors = []

        # Load image
        if isinstance(image, (str, Path)):
            image_path = str(image)
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not load image: {image_path}")
        else:
            image_path = "numpy_array"
            img = image

        h, w = img.shape[:2]
        logger.info(f"Processing image: {image_path} ({w}x{h})")

        # Determine output prefix
        if output_prefix is None and isinstance(image, (str, Path)):
            output_prefix = Path(image).stem

        # Step 1: Segmentation
        seg_start = time.time()
        if self.segmenter is not None:
            try:
                segmentation = self.segmenter.segment(img)
                # Use cropped image for detection if confident
                if segmentation.confidence > 0.5:
                    detection_img = segmentation.cropped_image
                else:
                    detection_img = img
            except Exception as e:
                logger.warning(f"Segmentation failed: {e}")
                errors.append(f"Segmentation error: {str(e)}")
                segmentation = None
                detection_img = img
        else:
            segmentation = None
            detection_img = img
        seg_time = (time.time() - seg_start) * 1000

        # Step 2: Landmark Detection
        det_start = time.time()
        try:
            detection = self.detector.detect(
                detection_img,
                category_hint=category_hint,
                return_heatmaps=self.config.save_debug,
            )

            # Map landmarks back to original image if we used cropped
            if segmentation is not None and segmentation.confidence > 0.5:
                offset_x = segmentation.bbox[0] - 30  # Account for padding
                offset_y = segmentation.bbox[1] - 30
                offset_x = max(0, offset_x)
                offset_y = max(0, offset_y)

                adjusted_landmarks = []
                for lm in detection.landmarks:
                    if lm is not None:
                        adjusted_landmarks.append((lm[0] + offset_x, lm[1] + offset_y))
                    else:
                        adjusted_landmarks.append(None)

                detection = DetectionResult(
                    landmarks=adjusted_landmarks,
                    confidences=detection.confidences,
                    heatmaps=detection.heatmaps,
                    category=detection.category,
                    image_size=(w, h),
                    inference_time_ms=detection.inference_time_ms,
                )
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            errors.append(f"Detection error: {str(e)}")
            detection = DetectionResult(
                landmarks=[],
                confidences=[],
                heatmaps=None,
                category=category_hint or "unknown",
                image_size=(w, h),
                inference_time_ms=0,
            )
        det_time = (time.time() - det_start) * 1000

        # Step 3: Measurement Calculation
        meas_start = time.time()
        try:
            measurements = self.measurement_engine.compute_measurements(
                landmarks=detection.landmarks,
                confidences=detection.confidences,
                category=detection.category,
                image_size=(w, h),
                target_measurements=target_measurements,
            )
        except Exception as e:
            logger.error(f"Measurement failed: {e}")
            errors.append(f"Measurement error: {str(e)}")
            measurements = MeasurementReport(
                category=detection.category,
                measurements={},
                validation_results=[],
                overall_status=MeasurementStatus.NOT_MEASURED,
                total_confidence=0.0,
                critical_pass_count=0,
                critical_fail_count=0,
                warning_count=0,
                px_per_mm=self.config.px_per_mm,
                image_size=(w, h),
            )
        meas_time = (time.time() - meas_start) * 1000

        # Create result
        total_time = (time.time() - total_start) * 1000
        success = len(errors) == 0 and len(detection.landmarks) > 0

        result = PipelineResult(
            image_path=image_path,
            image_size=(w, h),
            segmentation=segmentation,
            segmentation_time_ms=seg_time,
            detection=detection,
            detection_time_ms=det_time,
            measurements=measurements,
            measurement_time_ms=meas_time,
            total_time_ms=total_time,
            category=detection.category,
            success=success,
            errors=errors,
        )

        # Save outputs if configured
        if self.config.output_dir and output_prefix:
            self._save_outputs(img, result, output_prefix)

        logger.info(
            f"Pipeline complete: {detection.category} | "
            f"{sum(1 for l in detection.landmarks if l is not None)} landmarks | "
            f"{total_time:.0f}ms total"
        )

        return result

    def _save_outputs(
        self,
        image: np.ndarray,
        result: PipelineResult,
        prefix: str,
    ) -> None:
        """Save output files"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        if self.config.save_json:
            json_path = output_dir / f"{prefix}_result.json"
            result.save_json(json_path)
            logger.info(f"Saved JSON: {json_path}")

        # Save visualizations
        if self.config.save_visualizations:
            # Detection visualization
            det_vis = visualize_detection(image, result.detection, self.viz_config)
            det_path = output_dir / f"{prefix}_detection.jpg"
            cv2.imwrite(str(det_path), det_vis)

            # Measurement visualization
            meas_vis = visualize_measurements(det_vis, result.measurements, self.viz_config)
            meas_path = output_dir / f"{prefix}_measurements.jpg"
            cv2.imwrite(str(meas_path), meas_vis)

            # Full report
            report_vis = create_full_report(
                image, result.detection, result.measurements, self.viz_config
            )
            report_path = output_dir / f"{prefix}_report.jpg"
            cv2.imwrite(str(report_path), report_vis)

            logger.info(f"Saved visualizations to {output_dir}")

        # Save debug outputs
        if self.config.save_debug and result.detection.heatmaps is not None:
            heatmap_vis = DebugVisualizer.draw_heatmaps(
                image, result.detection.heatmaps
            )
            heatmap_path = output_dir / f"{prefix}_heatmaps.jpg"
            cv2.imwrite(str(heatmap_path), heatmap_vis)

    def process_batch(
        self,
        images: List[Union[str, Path, np.ndarray]],
        category_hint: Optional[str] = None,
    ) -> List[PipelineResult]:
        """
        Process multiple images.

        Args:
            images: List of image paths or arrays
            category_hint: Optional category for all images

        Returns:
            List of PipelineResult
        """
        results = []
        for i, image in enumerate(images):
            logger.info(f"Processing image {i+1}/{len(images)}")
            try:
                result = self.process(image, category_hint=category_hint)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process image {i+1}: {e}")
                # Create error result
                results.append(PipelineResult(
                    image_path=str(image) if isinstance(image, (str, Path)) else f"image_{i}",
                    image_size=(0, 0),
                    segmentation=None,
                    segmentation_time_ms=0,
                    detection=DetectionResult([], [], None, "error", (0, 0), 0),
                    detection_time_ms=0,
                    measurements=MeasurementReport(
                        category="error", measurements={}, validation_results=[],
                        overall_status=MeasurementStatus.NOT_MEASURED,
                        total_confidence=0, critical_pass_count=0,
                        critical_fail_count=0, warning_count=0,
                        px_per_mm=None, image_size=(0, 0),
                    ),
                    measurement_time_ms=0,
                    total_time_ms=0,
                    category="error",
                    success=False,
                    errors=[str(e)],
                ))

        return results


# Import MeasurementStatus for error handling
from .measurement_engine import MeasurementStatus


def create_pipeline(
    model_path: Optional[str] = None,
    px_per_mm: Optional[float] = None,
    use_segmentation: bool = True,
    output_dir: Optional[str] = None,
    device: str = 'auto',
) -> IndustrialMeasurementPipeline:
    """
    Factory function to create a measurement pipeline.

    Args:
        model_path: Path to HRNet model
        px_per_mm: Calibration factor
        use_segmentation: Enable background removal
        output_dir: Directory for output files
        device: 'cuda', 'cpu', or 'auto'

    Returns:
        Configured pipeline
    """
    config = PipelineConfig(
        model_path=model_path,
        device=device,
        px_per_mm=px_per_mm,
        use_segmentation=use_segmentation,
        output_dir=output_dir,
    )

    return IndustrialMeasurementPipeline(config)


# CLI interface
def main():
    """Command-line interface for the pipeline"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Industrial Garment Measurement Pipeline"
    )
    parser.add_argument("image", help="Input image path")
    parser.add_argument("--output", "-o", default="pipeline_output",
                       help="Output directory")
    parser.add_argument("--model", help="HRNet model path")
    parser.add_argument("--category", help="Garment category hint")
    parser.add_argument("--px-per-mm", type=float, help="Calibration factor")
    parser.add_argument("--no-segmentation", action="store_true",
                       help="Disable background segmentation")
    parser.add_argument("--debug", action="store_true",
                       help="Save debug outputs")
    parser.add_argument("--device", default="auto",
                       help="Device (cuda/cpu/auto)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Create config
    config = PipelineConfig(
        model_path=args.model,
        device=args.device,
        px_per_mm=args.px_per_mm,
        use_segmentation=not args.no_segmentation,
        output_dir=args.output,
        save_visualizations=True,
        save_json=True,
        save_debug=args.debug,
    )

    # Create and run pipeline
    pipeline = IndustrialMeasurementPipeline(config)
    result = pipeline.process(args.image, category_hint=args.category)

    # Print summary
    print("\n" + "=" * 60)
    print("MEASUREMENT RESULTS")
    print("=" * 60)
    print(f"Category: {result.category}")
    print(f"Success: {result.success}")
    print(f"Total time: {result.total_time_ms:.0f}ms")
    print(f"Landmarks detected: {sum(1 for l in result.detection.landmarks if l is not None)}")

    print("\nMeasurements:")
    for m in result.measurements.measurements.values():
        if m.value_mm is not None:
            print(f"  {m.name}: {m.value_mm:.1f}mm ({m.status.value})")
        else:
            print(f"  {m.name}: {m.value_px:.0f}px ({m.status.value})")

    print(f"\nOverall status: {result.measurements.overall_status.value}")
    print(f"Output saved to: {args.output}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
