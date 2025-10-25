#!/usr/bin/env python3
"""
Unified Fashion Analysis Pipeline

Combines multiple state-of-the-art fashion AI models:
- SVIP-Lab HRNet for precise landmark detection (294 keypoints)
- Fashionpedia for semantic segmentation and attributes
- Background removal for clean garment isolation
- Comprehensive measurement extraction
"""

import os
import cv2
import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import argparse
from datetime import datetime

# Import our integrated modules
from sviplab_hrnet_integration import SVIPLabFashionDetector
from fashionpedia_integration import FashionpediaIntegration
from hrnet_landmark_detector import FashionLandmarkDetector
from fashion_pipeline import FashionAnalysisPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UnifiedFashionPipeline:
    """
    Unified pipeline combining multiple fashion analysis models
    """

    def __init__(self,
                 sviplab_model_path: str = 'models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
                 fashionpedia_config: Optional[str] = None,
                 device: str = 'cpu',
                 enable_background_removal: bool = True):
        """
        Initialize unified pipeline with all components

        Args:
            sviplab_model_path: Path to SVIP-Lab HRNet model
            fashionpedia_config: Optional Fashionpedia configuration
            device: Computing device ('cuda' or 'cpu')
            enable_background_removal: Whether to remove background
        """
        self.device = device
        self.enable_bg_removal = enable_background_removal

        # Initialize SVIP-Lab HRNet detector
        logger.info("Initializing SVIP-Lab HRNet detector...")
        self.sviplab_detector = SVIPLabFashionDetector(
            model_path=sviplab_model_path,
            device=device
        )

        # Initialize Fashionpedia integration
        logger.info("Initializing Fashionpedia integration...")
        self.fashionpedia = FashionpediaIntegration()

        # Initialize basic fashion pipeline for background removal
        if enable_background_removal:
            logger.info("Initializing background removal pipeline...")
            self.fashion_pipeline = FashionAnalysisPipeline()

        # Initialize HRNet landmark detector for additional landmarks
        logger.info("Initializing standard HRNet detector...")
        self.hrnet_detector = FashionLandmarkDetector(
            model_path=sviplab_model_path,  # Use same model
            device=device
        )

        logger.info("Unified Fashion Pipeline initialized successfully")

    def analyze_garment(self,
                       image_path: str,
                       output_dir: str = 'unified_output',
                       save_intermediate: bool = True) -> Dict[str, Any]:
        """
        Comprehensive garment analysis using all available models

        Args:
            image_path: Path to input image
            output_dir: Directory for output files
            save_intermediate: Save intermediate processing steps

        Returns:
            Dictionary with complete analysis results
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        original_image = image.copy()
        results = {
            'timestamp': timestamp,
            'input_image': image_path,
            'image_dimensions': {
                'width': image.shape[1],
                'height': image.shape[0]
            }
        }

        # Step 1: Background Removal (if enabled, use fashion pipeline)
        if self.enable_bg_removal:
            logger.info("Processing with fashion pipeline for background removal...")
            try:
                fashion_result = self.fashion_pipeline.process_image(
                    image_path,
                    output_dir=None,  # Don't save intermediate files
                    visualize=False,
                    remove_background=True,
                    detect_landmarks=False  # We'll use SVIP-Lab for landmarks
                )

                if fashion_result.get('white_background') is not None:
                    # Convert RGB to BGR for OpenCV
                    clean_image = cv2.cvtColor(fashion_result['white_background'], cv2.COLOR_RGB2BGR)
                    results['background_removed'] = True

                    if save_intermediate:
                        output_path = os.path.join(output_dir, f'{timestamp}_no_background.png')
                        cv2.imwrite(output_path, clean_image)
                        results['background_removed_path'] = output_path
                else:
                    clean_image = image
                    results['background_removed'] = False
            except Exception as e:
                logger.warning(f"Background removal failed: {e}")
                clean_image = image
                results['background_removed'] = False
        else:
            clean_image = image

        # Step 2: SVIP-Lab HRNet Detection (Primary)
        logger.info("Detecting fashion landmarks with SVIP-Lab HRNet...")
        sviplab_result = self.sviplab_detector.detect_landmarks(clean_image)
        results['sviplab'] = {
            'category': sviplab_result['category'],
            'num_landmarks': sviplab_result['num_detected'],
            'total_possible': len(sviplab_result['landmarks']),
            'confidence_mean': float(np.mean([c for c in sviplab_result['confidences'] if c > 0]))
        }

        # Extract measurements from SVIP-Lab landmarks
        measurements = self.sviplab_detector.extract_measurements(sviplab_result)
        results['measurements_pixels'] = measurements

        # Visualize SVIP-Lab results
        if save_intermediate:
            vis_sviplab = self.sviplab_detector.visualize_landmarks(
                clean_image, sviplab_result, show_confidence=True, show_labels=True
            )
            output_path = os.path.join(output_dir, f'{timestamp}_sviplab_landmarks.jpg')
            cv2.imwrite(output_path, vis_sviplab)
            results['sviplab_visualization'] = output_path

        # Step 3: Fashionpedia Analysis
        logger.info("Analyzing with Fashionpedia...")
        fashionpedia_result = self.fashionpedia.process_image_with_fashionpedia(
            clean_image,
            use_segmentation=True,
            detect_attributes=True
        )

        results['fashionpedia'] = {
            'categories': fashionpedia_result.get('categories', []),
            'attributes': fashionpedia_result.get('attributes', {}),
            'measurement_zones': fashionpedia_result.get('measurement_zones', [])
        }

        # Step 4: Standard HRNet Detection (Supplementary)
        logger.info("Detecting additional landmarks with standard HRNet...")
        hrnet_result = self.hrnet_detector.detect_landmarks(clean_image)

        if hrnet_result and 'keypoints' in hrnet_result:
            keypoints = hrnet_result['keypoints'][0] if len(hrnet_result['keypoints']) > 0 else []
            results['hrnet_standard'] = {
                'num_landmarks': len(keypoints),
                'landmark_labels': hrnet_result.get('landmark_labels', {})
            }

        # Step 5: Measurement Calculation
        logger.info("Calculating final measurements...")
        final_measurements = self._calculate_unified_measurements(
            sviplab_result,
            fashionpedia_result,
            hrnet_result,
            image.shape
        )
        results['final_measurements'] = final_measurements

        # Step 6: Generate Comprehensive Report
        if save_intermediate:
            report_image = self._create_unified_report(
                original_image,
                clean_image,
                results,
                output_dir,
                timestamp
            )
            results['report_path'] = report_image

        # Save JSON results
        json_path = os.path.join(output_dir, f'{timestamp}_analysis.json')
        with open(json_path, 'w') as f:
            # Convert numpy arrays to lists for JSON serialization
            json_results = self._prepare_for_json(results)
            json.dump(json_results, f, indent=2)
        results['json_path'] = json_path

        logger.info(f"Analysis complete. Results saved to {output_dir}")
        return results

    def _calculate_unified_measurements(self,
                                       sviplab_result: Dict,
                                       fashionpedia_result: Dict,
                                       hrnet_result: Dict,
                                       image_shape: Tuple) -> Dict:
        """
        Calculate unified measurements from all detections
        """
        measurements = {}

        # Start with SVIP-Lab measurements (most accurate for fashion)
        svip_measurements = self.sviplab_detector.extract_measurements(sviplab_result)
        for key, value in svip_measurements.items():
            measurements[f'sviplab_{key}'] = value

        # Add pixel to cm conversion if calibration markers detected
        if 'calibration_markers' in fashionpedia_result:
            # Assume 10cm calibration marker (standard)
            pixel_per_cm = self._estimate_pixel_per_cm(fashionpedia_result['calibration_markers'])
            if pixel_per_cm:
                for key, value in svip_measurements.items():
                    measurements[f'{key}_cm'] = value / pixel_per_cm

        # Add garment-specific measurements based on category
        category = sviplab_result.get('category', 'unknown')
        if category in ['shirt', 'vest', 'long_sleeved_shirt', 'short_sleeved_shirt']:
            measurements['garment_type'] = 'top'
            measurements['has_sleeves'] = category != 'vest'
        elif category in ['trousers', 'shorts', 'skirt']:
            measurements['garment_type'] = 'bottom'
            measurements['is_long'] = category == 'trousers'
        elif 'dress' in category:
            measurements['garment_type'] = 'dress'

        return measurements

    def _estimate_pixel_per_cm(self, markers: List) -> Optional[float]:
        """
        Estimate pixel per cm ratio from calibration markers
        """
        # Simplified estimation - would need actual marker detection
        # This is a placeholder for actual calibration logic
        return None  # Return None if no calibration available

    def _create_unified_report(self,
                              original_image: np.ndarray,
                              processed_image: np.ndarray,
                              results: Dict,
                              output_dir: str,
                              timestamp: str) -> str:
        """
        Create comprehensive visual report
        """
        # Create a multi-panel report
        h, w = original_image.shape[:2]

        # Ensure processed image matches original dimensions
        if processed_image.shape[:2] != (h, w):
            processed_image = cv2.resize(processed_image, (w, h))

        # Create 2x2 grid
        report = np.ones((h * 2 + 100, w * 2 + 30, 3), dtype=np.uint8) * 255

        # Panel 1: Original image
        report[10:h+10, 10:w+10] = original_image
        cv2.putText(report, "Original", (15, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Panel 2: Processed image
        report[10:h+10, w+20:w*2+20] = processed_image
        cv2.putText(report, "Background Removed", (w+25, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Panel 3: SVIP-Lab landmarks
        if 'sviplab_visualization' in results:
            vis_img = cv2.imread(results['sviplab_visualization'])
            if vis_img is not None:
                vis_img = cv2.resize(vis_img, (w, h))
                report[h+60:h*2+60, 10:w+10] = vis_img
        cv2.putText(report, f"SVIP-Lab: {results['sviplab']['category']}",
                   (15, h*2+85), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # Panel 4: Measurements
        measure_panel = np.ones((h, w, 3), dtype=np.uint8) * 245
        y_offset = 50

        cv2.putText(measure_panel, "Measurements", (20, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        for key, value in results.get('measurements_pixels', {}).items():
            text = f"{key}: {value:.1f}px"
            cv2.putText(measure_panel, text, (20, y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
            y_offset += 30

        report[h+60:h*2+60, w+20:w*2+20] = measure_panel

        # Save report
        output_path = os.path.join(output_dir, f'{timestamp}_unified_report.jpg')
        cv2.imwrite(output_path, report)

        return output_path

    def _prepare_for_json(self, obj: Any) -> Any:
        """
        Recursively convert numpy arrays to lists for JSON serialization
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        else:
            return obj


def main():
    parser = argparse.ArgumentParser(description='Unified Fashion Analysis Pipeline')
    parser.add_argument('--image', type=str, required=True,
                       help='Path to input garment image')
    parser.add_argument('--output', type=str, default='unified_output',
                       help='Output directory for results')
    parser.add_argument('--device', type=str, default='cpu', choices=['cpu', 'cuda'],
                       help='Computing device')
    parser.add_argument('--no-bg-removal', action='store_true',
                       help='Skip background removal')
    parser.add_argument('--sviplab-model', type=str,
                       default='models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
                       help='Path to SVIP-Lab HRNet model')

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = UnifiedFashionPipeline(
        sviplab_model_path=args.sviplab_model,
        device=args.device,
        enable_background_removal=not args.no_bg_removal
    )

    # Analyze garment
    results = pipeline.analyze_garment(
        image_path=args.image,
        output_dir=args.output,
        save_intermediate=True
    )

    # Print summary
    print("\n" + "="*60)
    print("UNIFIED FASHION ANALYSIS RESULTS")
    print("="*60)
    print(f"Image: {args.image}")
    print(f"Garment Category: {results['sviplab']['category']}")
    print(f"Landmarks Detected: {results['sviplab']['num_landmarks']}/{results['sviplab']['total_possible']}")
    print(f"Mean Confidence: {results['sviplab']['confidence_mean']:.3f}")

    print("\nMeasurements (pixels):")
    for key, value in results.get('measurements_pixels', {}).items():
        print(f"  {key}: {value:.1f}")

    if 'fashionpedia' in results:
        print(f"\nFashionpedia Categories: {', '.join(results['fashionpedia']['categories'])}")
        if results['fashionpedia']['attributes']:
            print("Attributes Detected:")
            for attr_type, attr_value in results['fashionpedia']['attributes'].items():
                print(f"  {attr_type}: {attr_value}")

    print(f"\nResults saved to: {args.output}")
    print(f"Report: {results.get('report_path', 'N/A')}")
    print(f"JSON: {results.get('json_path', 'N/A')}")


if __name__ == '__main__':
    main()