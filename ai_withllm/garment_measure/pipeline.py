#!/usr/bin/env python3
"""
Main pipeline orchestrator for garment measurement system.
Integrates all modules for end-to-end processing.
"""

import cv2
import numpy as np
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

from .calibration_tool import CalibrationTool
from .segmentation import GarmentSegmenter
from .classifier import GarmentClassifier
from .landmarks import LandmarkDetector
from .measurement import MeasurementCalculator
from .overlay import OverlayGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Pipeline:
    """
    Main pipeline for automated garment measurement.
    """

    def __init__(self, calibration_path: str,
                 use_sam: bool = False,
                 sam_checkpoint: Optional[str] = None,
                 use_clip: bool = False,
                 kp_model_path: Optional[str] = None,
                 output_dir: Optional[str] = None):
        """
        Initialize measurement pipeline.

        Args:
            calibration_path: Path to calibration JSON
            use_sam: Whether to use SAM for segmentation
            sam_checkpoint: Path to SAM model
            use_clip: Whether to use CLIP for classification
            kp_model_path: Path to keypoint detection model
            output_dir: Directory for saving results
        """
        self.output_dir = Path(output_dir) if output_dir else Path('.')
        self.output_dir.mkdir(exist_ok=True)

        # Initialize modules
        logger.info("Initializing pipeline modules...")

        # Calibration
        self.calibration = CalibrationTool(calibration_path)
        if self.calibration.pixel_to_mm is None:
            logger.warning("Calibration not complete. Run calibration first.")

        # Segmentation
        self.segmenter = GarmentSegmenter(use_sam, sam_checkpoint)

        # Classification
        self.classifier = GarmentClassifier(use_clip=use_clip)

        # Landmark detection
        self.landmark_detector = LandmarkDetector(
            model_path=kp_model_path
        )

        # Measurement calculator
        self.calculator = MeasurementCalculator(
            pixel_to_mm=self.calibration.pixel_to_mm or 1.0,
            rect_rms_mm=self.calibration.rect_rms_mm or 0.5
        )

        # Overlay generator
        self.overlay_gen = OverlayGenerator()

        logger.info("Pipeline initialized successfully")

    def calibrate_from_image(self, calibration_image_path: str,
                            save_config: bool = True) -> Dict[str, Any]:
        """
        Perform calibration from an image with ArUco markers.

        Args:
            calibration_image_path: Path to calibration image
            save_config: Whether to save calibration config

        Returns:
            Calibration results
        """
        logger.info(f"Calibrating from {calibration_image_path}")

        image = cv2.imread(calibration_image_path)
        if image is None:
            return {'success': False, 'error': 'Could not load calibration image'}

        # Compute calibration
        result = self.calibration.compute_homography(
            image,
            'calibration.json' if save_config else None
        )

        if result['success']:
            # Update calculator with new scale
            self.calculator.pixel_to_mm = self.calibration.pixel_to_mm
            self.calculator.rect_rms_mm = self.calibration.rect_rms_mm

            logger.info(f"Calibration successful: {result['ppm']:.2f} ppm")
        else:
            logger.error(f"Calibration failed: {result['error']}")

        return result

    def process_image(self, image_path: str,
                     garment_type: Optional[str] = None,
                     rectify: bool = True,
                     save_results: bool = True) -> Dict[str, Any]:
        """
        Process a garment image end-to-end.

        Args:
            image_path: Path to garment image
            garment_type: Optional override for garment type
            rectify: Whether to rectify image using calibration
            save_results: Whether to save output files

        Returns:
            Dictionary with results including measurements, overlay path, etc.
        """
        start_time = time.time()
        logger.info(f"Processing {image_path}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return {'ok': False, 'error': 'Could not load image'}

        results = {
            'ok': True,
            'image_path': image_path,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            # Step 0: Image quality gates
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            p5, p95 = np.percentile(gray, [5, 95])

            results['quality_metrics'] = {
                'laplacian_variance': float(laplacian_var),
                'percentile_5': float(p5),
                'percentile_95': float(p95)
            }

            # Fail fast if image quality is poor
            if laplacian_var < 120:
                return {'ok': False, 'error': 'Image too blurry', 'quality_metrics': results['quality_metrics']}
            if p5 < 10 or p95 > 245:
                return {'ok': False, 'error': 'Poor exposure/contrast', 'quality_metrics': results['quality_metrics']}

            # Step 1: Detect ArUco markers for scale verification
            markers = self.calibration.detect_aruco_markers(image)
            results['num_markers'] = len(markers)

            if len(markers) < 4:
                logger.warning(f"Only {len(markers)} ArUco markers detected")

            # Verify scale accuracy with detected markers
            if markers:
                scale_check = self.calibration.verify_scale_with_marker(image)
                if scale_check.get('success'):
                    results['scale_verification'] = {
                        'avg_deviation_mm': scale_check['avg_deviation_mm'],
                        'max_deviation_mm': scale_check['max_deviation_mm']
                    }
                    if scale_check['max_deviation_mm'] > 0.5:
                        logger.warning(f"Scale deviation exceeds 0.5mm threshold: {scale_check['max_deviation_mm']:.2f} mm")

            # Step 2: Rectify if calibration available and requested
            if rectify and self.calibration.homography is not None:
                logger.info("Rectifying image...")
                rectified = self.calibration.rectify_image(image)
                if rectified is not None:
                    processing_image = rectified
                    results['rectified'] = True
                    # IMPORTANT: Rectified canvas is metric (1 px = 1 mm)
                    # Temporarily store original scale and use metric scale
                    self._original_pixel_to_mm = self.calculator.pixel_to_mm
                    self.calculator.pixel_to_mm = 1.0

                    # Post-rectification scale verification
                    rect_markers = self.calibration.detect_aruco_markers(processing_image)
                    if all(i in rect_markers for i in (0, 1, 2, 3)):
                        # Get marker centers for scale check
                        TL = np.mean(rect_markers[0], axis=0)
                        TR = np.mean(rect_markers[1], axis=0)
                        BL = np.mean(rect_markers[3], axis=0)
                        BR = np.mean(rect_markers[2], axis=0)

                        # Measure distances
                        top_width = np.linalg.norm(TR - TL)
                        bottom_width = np.linalg.norm(BR - BL)
                        expected_width = self.calibration.bench_dimensions_mm['width']

                        results['scale_check_mm'] = {
                            'top': float(top_width),
                            'bottom': float(bottom_width),
                            'expected': float(expected_width)
                        }

                        # Warn if scale drift > 2mm
                        if abs(top_width - expected_width) > 2.0 or abs(bottom_width - expected_width) > 2.0:
                            results.setdefault('warnings', []).append(
                                f'Scale drift detected: top={top_width:.1f}mm, bottom={bottom_width:.1f}mm, expected={expected_width:.1f}mm'
                            )
                            logger.warning("Scale drift > ±2mm detected, re-calibration recommended")
                else:
                    processing_image = image
                    results['rectified'] = False
            else:
                processing_image = image
                results['rectified'] = False

            # Step 3: Segment garment
            logger.info("Segmenting garment...")
            mask, seg_info = self.segmenter.segment(processing_image)
            results['segmentation'] = seg_info

            # Quality check on segmentation
            if not seg_info.get('quality_checks', {}).get('area_ok', False):
                logger.warning("Segmentation area outside expected range")
                results['warnings'] = results.get('warnings', [])
                results['warnings'].append('Segmentation area unusual')

            # Step 4: Classify garment type
            if garment_type is None:
                logger.info("Classifying garment type...")
                garment_type, confidence, class_info = self.classifier.classify(
                    processing_image, mask
                )
                results['garment_type'] = garment_type
                results['classification_confidence'] = confidence
                results['classification_info'] = class_info

                if confidence < 0.5:
                    logger.warning(f"Low classification confidence: {confidence:.2f}")
            else:
                results['garment_type'] = garment_type
                results['garment_type_override'] = True

            # Step 5: Detect landmarks
            logger.info(f"Detecting landmarks for {garment_type}...")
            landmarks = self.landmark_detector.detect(
                processing_image, mask, garment_type
            )

            # Refine landmarks
            landmarks = self.landmark_detector.refine_landmarks(
                landmarks, processing_image, mask
            )

            results['num_landmarks'] = len(landmarks)
            results['landmarks'] = {k: (v[0], v[1], v[2]) for k, v in landmarks.items()}

            # Transform landmarks back to original image if rectified
            if results.get('rectified') and self.calibration.homography is not None:
                # Convert landmarks back to original coordinates for display
                original_landmarks = {}
                for name, (x, y, conf) in landmarks.items():
                    orig_point = self.calibration.inverse_rectify_points(
                        np.array([[x, y]])
                    )[0]
                    original_landmarks[name] = (orig_point[0], orig_point[1], conf)
            else:
                original_landmarks = landmarks

            # Step 6: Calculate measurements
            logger.info("Calculating measurements...")

            # Get measurement definitions for this garment type
            from .measurement import MeasurementCalculator
            definitions = MeasurementCalculator.MEASUREMENT_DEFINITIONS.get(
                garment_type, {}
            )

            measurements = self.calculator.calculate_measurements(
                landmarks, garment_type, rectified=results.get('rectified', False)
            )
            results['measurements_mm'] = measurements

            # Step 7: Estimate uncertainty
            uncertainties = self.calculator.estimate_uncertainty(
                landmarks, measurements, mask
            )
            results['uncertainty_ci95_mm'] = uncertainties

            # Step 8: Validate measurements
            validation = self.calculator.validate_measurements(
                measurements, garment_type
            )
            results['validation'] = validation

            if not validation['valid']:
                logger.warning(f"Measurement validation failed: {validation}")

            # Step 9: Create overlay visualization
            logger.info("Creating visualization overlay...")
            overlay = self.overlay_gen.create_overlay(
                image,  # Use original image for overlay
                original_landmarks,
                measurements,
                definitions,
                uncertainties,
                self.calculator.pixel_to_mm,
                garment_type,
                mask if not results.get('rectified') else None
            )
            results['overlay_bgr'] = overlay

            # Step 10: Save results if requested
            if save_results:
                base_name = Path(image_path).stem

                # Save overlay
                overlay_path = self.output_dir / f"{base_name}_overlay.jpg"
                cv2.imwrite(str(overlay_path), overlay)
                results['overlay_path'] = str(overlay_path)

                # Save JSON results
                json_path = self.output_dir / f"{base_name}_results.json"
                json_results = {
                    k: v for k, v in results.items()
                    if k not in ['overlay_bgr']  # Don't save image data
                }
                # Convert numpy values to native Python types
                json_results = self._make_json_serializable(json_results)

                with open(json_path, 'w') as f:
                    json.dump(json_results, f, indent=2)
                results['json_path'] = str(json_path)

                logger.info(f"Results saved to {json_path}")

            # Restore original scale if we modified it
            if hasattr(self, '_original_pixel_to_mm'):
                self.calculator.pixel_to_mm = self._original_pixel_to_mm
                delattr(self, '_original_pixel_to_mm')

            # Processing time
            results['processing_time_s'] = time.time() - start_time
            logger.info(f"Processing completed in {results['processing_time_s']:.2f}s")

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results['ok'] = False
            results['error'] = str(e)

            # Always restore original scale if we modified it
            if hasattr(self, '_original_pixel_to_mm'):
                self.calculator.pixel_to_mm = self._original_pixel_to_mm
                delattr(self, '_original_pixel_to_mm')

        return results

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_json_serializable(v) for v in obj)
        else:
            return obj

    def batch_process(self, image_paths: list,
                     parallel: bool = False) -> list:
        """
        Process multiple images.

        Args:
            image_paths: List of image paths
            parallel: Whether to process in parallel (requires multiprocessing)

        Returns:
            List of results
        """
        results = []

        if parallel:
            # TODO: Implement parallel processing with multiprocessing
            logger.warning("Parallel processing not yet implemented, using sequential")

        for path in image_paths:
            logger.info(f"Processing {len(results)+1}/{len(image_paths)}: {path}")
            result = self.process_image(path)
            results.append(result)

        return results

    def validate_setup(self) -> Dict[str, bool]:
        """
        Validate that the pipeline is properly configured.

        Returns:
            Dictionary of validation checks
        """
        checks = {
            'calibration_loaded': self.calibration.pixel_to_mm is not None,
            'calibration_homography': self.calibration.homography is not None,
            'sam_available': self.segmenter.use_sam and self.segmenter.sam is not None,
            'clip_available': self.classifier.use_clip and self.classifier.clip_model is not None,
            'hrnet_available': self.landmark_detector.use_hrnet and self.landmark_detector.model is not None,
        }

        all_ok = checks['calibration_loaded']  # Minimum requirement

        if all_ok:
            logger.info("Pipeline validation passed")
        else:
            logger.warning(f"Pipeline validation issues: {checks}")

        return checks


def main():
    """Command-line interface for the pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description='Garment Measurement Pipeline')
    parser.add_argument('--calibrate', help='Calibration image with ArUco markers')
    parser.add_argument('--image', help='Garment image to process')
    parser.add_argument('--batch', help='Directory of images to process')
    parser.add_argument('--calibration', default='calibration.json',
                       help='Calibration config file')
    parser.add_argument('--type', help='Override garment type')
    parser.add_argument('--sam', help='Path to SAM checkpoint')
    parser.add_argument('--hrnet', help='Path to HRNet model')
    parser.add_argument('--clip', action='store_true', help='Use CLIP for classification')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--no-rectify', action='store_true', help='Skip rectification')
    args = parser.parse_args()

    # Initialize pipeline
    pipeline = Pipeline(
        calibration_path=args.calibration,
        use_sam=(args.sam is not None),
        sam_checkpoint=args.sam,
        use_clip=args.clip,
        kp_model_path=args.hrnet,
        output_dir=args.output
    )

    # Validate setup
    validation = pipeline.validate_setup()
    print("Pipeline validation:")
    for check, status in validation.items():
        print(f"  {check}: {'✓' if status else '✗'}")

    # Calibrate if requested
    if args.calibrate:
        print(f"\nCalibrating from {args.calibrate}...")
        cal_result = pipeline.calibrate_from_image(args.calibrate)
        if cal_result['success']:
            print(f"✓ Calibration successful!")
            print(f"  Scale: {cal_result['ppm']:.2f} pixels/mm")
            print(f"  Error: {cal_result['rect_rms_mm']:.2f} mm")
        else:
            print(f"✗ Calibration failed: {cal_result['error']}")
            return

    # Process single image
    if args.image:
        print(f"\nProcessing {args.image}...")
        result = pipeline.process_image(
            args.image,
            garment_type=args.type,
            rectify=not args.no_rectify
        )

        if result['ok']:
            print(f"✓ Processing successful!")
            print(f"  Garment type: {result.get('garment_type')}")
            print(f"  Landmarks detected: {result.get('num_landmarks')}")
            print("\n  Measurements:")
            for name, value in result.get('measurements_mm', {}).items():
                uncertainty = result.get('uncertainty_ci95_mm', {}).get(name, 0)
                print(f"    {name}: {value:.1f} ± {uncertainty:.1f} mm")

            if 'overlay_path' in result:
                print(f"\n  Overlay saved to: {result['overlay_path']}")
            if 'json_path' in result:
                print(f"  Results saved to: {result['json_path']}")
        else:
            print(f"✗ Processing failed: {result.get('error')}")

    # Batch processing
    if args.batch:
        from pathlib import Path
        image_files = list(Path(args.batch).glob('*.jpg')) + \
                     list(Path(args.batch).glob('*.png'))

        if image_files:
            print(f"\nBatch processing {len(image_files)} images...")
            results = pipeline.batch_process([str(f) for f in image_files])

            successful = sum(1 for r in results if r['ok'])
            print(f"\nBatch complete: {successful}/{len(results)} successful")
        else:
            print(f"No images found in {args.batch}")


if __name__ == '__main__':
    main()