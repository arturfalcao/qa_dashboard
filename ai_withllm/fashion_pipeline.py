#!/usr/bin/env python3
"""
Complete Fashion Analysis Pipeline

This module combines HRNet landmark detection with background removal
to create a comprehensive fashion image processing pipeline.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Union
import logging
import sys
import os

# Check if torch is available before importing
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hrnet_landmark_detector import FashionLandmarkDetector
from ai_mesurement.background_removal import BackgroundRemover

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FashionAnalysisPipeline:
    """
    Complete pipeline for fashion image analysis
    Combines landmark detection and background removal
    """

    def __init__(self,
                 model_path: str = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
                 bg_model: str = "u2net_cloth_seg",
                 device: str = None):
        """
        Initialize the fashion analysis pipeline

        Args:
            model_path: Path to HRNet model weights
            bg_model: Background removal model to use
            device: Device for computation ('cuda' or 'cpu')
        """
        logger.info("Initializing Fashion Analysis Pipeline...")

        # Set device if not specified
        if device is None:
            if TORCH_AVAILABLE:
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = "cpu"

        # Initialize landmark detector
        try:
            if TORCH_AVAILABLE:
                self.landmark_detector = FashionLandmarkDetector(model_path, device)
            else:
                logger.warning("PyTorch not available - landmark detection disabled")
                self.landmark_detector = None
            logger.info("Landmark detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize landmark detector: {e}")
            self.landmark_detector = None

        # Initialize background remover
        try:
            self.bg_remover = BackgroundRemover(model_name=bg_model, use_alpha_matting=True)
            logger.info("Background remover initialized")
        except Exception as e:
            logger.error(f"Failed to initialize background remover: {e}")
            self.bg_remover = None

        self.device = device

    def process_image(self,
                     image_path: str,
                     output_dir: Optional[str] = None,
                     visualize: bool = True,
                     remove_background: bool = True,
                     detect_landmarks: bool = True,
                     confidence_threshold: float = 0.3) -> Dict:
        """
        Process a fashion image through the complete pipeline

        Args:
            image_path: Path to input image
            output_dir: Directory to save outputs (if None, returns results only)
            visualize: Whether to create visualization images
            remove_background: Whether to remove background
            detect_landmarks: Whether to detect landmarks
            confidence_threshold: Minimum confidence for landmark detection

        Returns:
            Dictionary containing all processing results
        """
        results = {
            'original_path': image_path,
            'success': False
        }

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Could not load image from {image_path}")
            return results

        original_image = image.copy()
        results['original_shape'] = image.shape

        # Step 1: Detect landmarks on original image
        if detect_landmarks and self.landmark_detector:
            logger.info("Detecting landmarks...")
            landmark_result = self.landmark_detector.detect_landmarks(
                image, confidence_threshold=confidence_threshold
            )
            results['landmarks'] = landmark_result
            logger.info(f"Detected {landmark_result['num_detected']} landmarks")
            logger.info(f"Garment category: {landmark_result['category']}")

            # Create landmark visualization
            if visualize:
                landmark_viz = self.landmark_detector.draw_landmarks(
                    original_image.copy(), landmark_result
                )
                results['landmark_visualization'] = landmark_viz
        else:
            results['landmarks'] = None

        # Step 2: Remove background
        if remove_background and self.bg_remover:
            logger.info("Removing background...")
            no_bg_image = self.bg_remover.remove_background(
                original_image,
                background_color=None  # Keep transparent
            )
            results['no_background'] = no_bg_image

            # Also create white background version
            white_bg_image = self.bg_remover.remove_background(
                original_image,
                background_color=(255, 255, 255)
            )
            results['white_background'] = white_bg_image
            logger.info("Background removed")
        else:
            results['no_background'] = None
            results['white_background'] = None

        # Step 3: Detect landmarks on image without background
        if remove_background and detect_landmarks and results['white_background'] is not None:
            logger.info("Detecting landmarks on clean image...")
            # Convert to BGR for processing
            if len(results['white_background'].shape) == 3:
                clean_image_bgr = cv2.cvtColor(results['white_background'], cv2.COLOR_RGB2BGR)
            else:
                clean_image_bgr = results['white_background']

            clean_landmark_result = self.landmark_detector.detect_landmarks(
                clean_image_bgr, confidence_threshold=confidence_threshold
            )
            results['clean_landmarks'] = clean_landmark_result

            # Create combined visualization
            if visualize:
                clean_landmark_viz = self.landmark_detector.draw_landmarks(
                    clean_image_bgr.copy(), clean_landmark_result
                )
                results['clean_landmark_visualization'] = clean_landmark_viz

        # Step 4: Create final composite image with landmarks overlaid on transparent background
        if all([remove_background, detect_landmarks, visualize,
                results.get('no_background') is not None,
                results.get('landmarks') is not None]):
            logger.info("Creating final composite...")
            composite = self._create_composite(
                results['no_background'],
                results['landmarks']
            )
            results['final_composite'] = composite

        # Save outputs if directory specified
        if output_dir:
            self._save_outputs(results, output_dir, Path(image_path).stem)

        results['success'] = True
        return results

    def _create_composite(self,
                         transparent_image: np.ndarray,
                         landmark_result: Dict) -> np.ndarray:
        """
        Create composite image with landmarks on transparent background

        Args:
            transparent_image: Image with removed background (RGBA)
            landmark_result: Landmark detection results

        Returns:
            Composite image with landmarks drawn
        """
        # Ensure we have RGBA image
        if len(transparent_image.shape) == 3 and transparent_image.shape[2] == 4:
            # Convert RGBA to BGR for drawing
            rgb = transparent_image[:, :, :3]
            alpha = transparent_image[:, :, 3]

            # Draw landmarks on RGB image
            result = self.landmark_detector.draw_landmarks(rgb, landmark_result)

            # Combine with alpha channel
            h, w = result.shape[:2]
            composite = np.zeros((h, w, 4), dtype=np.uint8)
            composite[:, :, :3] = result
            composite[:, :, 3] = alpha

            return composite
        else:
            # No alpha channel, just draw landmarks
            return self.landmark_detector.draw_landmarks(
                transparent_image, landmark_result
            )

    def _save_outputs(self, results: Dict, output_dir: str, base_name: str):
        """Save all pipeline outputs to directory"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save landmark visualization
        if 'landmark_visualization' in results and results['landmark_visualization'] is not None:
            cv2.imwrite(
                str(output_path / f"{base_name}_landmarks.jpg"),
                results['landmark_visualization']
            )

        # Save no background image (PNG for transparency)
        if 'no_background' in results and results['no_background'] is not None:
            # Convert RGB to BGR for OpenCV
            if len(results['no_background'].shape) == 3:
                if results['no_background'].shape[2] == 4:
                    # RGBA - save as PNG
                    rgba_bgr = results['no_background'].copy()
                    rgba_bgr[:, :, :3] = cv2.cvtColor(
                        rgba_bgr[:, :, :3], cv2.COLOR_RGB2BGR
                    )
                    cv2.imwrite(
                        str(output_path / f"{base_name}_no_bg.png"),
                        rgba_bgr
                    )
                else:
                    # RGB
                    cv2.imwrite(
                        str(output_path / f"{base_name}_no_bg.png"),
                        cv2.cvtColor(results['no_background'], cv2.COLOR_RGB2BGR)
                    )

        # Save white background image
        if 'white_background' in results and results['white_background'] is not None:
            cv2.imwrite(
                str(output_path / f"{base_name}_white_bg.jpg"),
                cv2.cvtColor(results['white_background'], cv2.COLOR_RGB2BGR)
            )

        # Save clean landmark visualization
        if 'clean_landmark_visualization' in results and results['clean_landmark_visualization'] is not None:
            cv2.imwrite(
                str(output_path / f"{base_name}_clean_landmarks.jpg"),
                results['clean_landmark_visualization']
            )

        # Save final composite
        if 'final_composite' in results and results['final_composite'] is not None:
            if len(results['final_composite'].shape) == 3 and results['final_composite'].shape[2] == 4:
                # RGBA - save as PNG
                composite_bgr = results['final_composite'].copy()
                composite_bgr[:, :, :3] = cv2.cvtColor(
                    composite_bgr[:, :, :3], cv2.COLOR_RGB2BGR
                )
                cv2.imwrite(
                    str(output_path / f"{base_name}_final.png"),
                    composite_bgr
                )
            else:
                cv2.imwrite(
                    str(output_path / f"{base_name}_final.jpg"),
                    cv2.cvtColor(results['final_composite'], cv2.COLOR_RGB2BGR)
                )

        # Save metadata
        metadata = {
            'image': base_name,
            'landmarks_detected': results['landmarks']['num_detected'] if results.get('landmarks') else 0,
            'category': results['landmarks']['category'] if results.get('landmarks') else None,
            'processed': True
        }

        import json
        with open(output_path / f"{base_name}_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Results saved to {output_path}")

    def batch_process(self,
                     input_dir: str,
                     output_dir: str,
                     pattern: str = "*.jpg",
                     **kwargs):
        """
        Process multiple images in a directory

        Args:
            input_dir: Input directory containing images
            output_dir: Output directory for results
            pattern: File pattern to match
            **kwargs: Additional arguments for process_image
        """
        input_path = Path(input_dir)
        image_files = list(input_path.glob(pattern))

        if not image_files:
            logger.warning(f"No files matching {pattern} found in {input_dir}")
            return

        logger.info(f"Processing {len(image_files)} images...")

        for i, img_file in enumerate(image_files, 1):
            logger.info(f"[{i}/{len(image_files)}] Processing {img_file.name}")
            try:
                self.process_image(
                    str(img_file),
                    output_dir=output_dir,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"Error processing {img_file.name}: {e}")
                continue

        logger.info("Batch processing complete")


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Fashion Analysis Pipeline")
    parser.add_argument("input", help="Input image or directory")
    parser.add_argument("--output", default="output",
                       help="Output directory for results")
    parser.add_argument("--model", default="models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
                       help="Path to HRNet model")
    parser.add_argument("--bg-model", default="u2net_cloth_seg",
                       choices=["u2net", "u2netp", "u2net_human_seg", "u2net_cloth_seg", "silueta"],
                       help="Background removal model")
    parser.add_argument("--batch", action="store_true",
                       help="Process all images in directory")
    parser.add_argument("--no-landmarks", action="store_true",
                       help="Skip landmark detection")
    parser.add_argument("--no-background", action="store_true",
                       help="Skip background removal")
    parser.add_argument("--confidence", type=float, default=0.3,
                       help="Landmark detection confidence threshold")
    parser.add_argument("--device", default=None,
                       help="Device (cuda/cpu)")

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = FashionAnalysisPipeline(
        model_path=args.model,
        bg_model=args.bg_model,
        device=args.device
    )

    # Process
    if args.batch:
        pipeline.batch_process(
            args.input,
            args.output,
            detect_landmarks=not args.no_landmarks,
            remove_background=not args.no_background,
            confidence_threshold=args.confidence
        )
    else:
        result = pipeline.process_image(
            args.input,
            output_dir=args.output,
            detect_landmarks=not args.no_landmarks,
            remove_background=not args.no_background,
            confidence_threshold=args.confidence
        )

        if result['success']:
            print(f"Processing complete. Results saved to {args.output}")
            if result.get('landmarks'):
                print(f"Detected {result['landmarks']['num_detected']} landmarks")
                print(f"Garment category: {result['landmarks']['category']}")
        else:
            print("Processing failed")


if __name__ == "__main__":
    main()