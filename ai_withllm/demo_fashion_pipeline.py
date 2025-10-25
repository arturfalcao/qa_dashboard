#!/usr/bin/env python3
"""
Demo script for Fashion Analysis Pipeline

This script demonstrates the complete fashion analysis pipeline:
1. Landmark detection using HRNet
2. Background removal
3. Combined visualization
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_sample_image():
    """Download a sample fashion image if no input is provided"""
    import urllib.request

    sample_url = "https://image.hm.com/assets/hm/ij/kl/002dc6d1/3000017-1.jpg"
    sample_path = "sample_fashion.jpg"

    if not os.path.exists(sample_path):
        logger.info(f"Downloading sample image from {sample_url}...")
        try:
            urllib.request.urlretrieve(sample_url, sample_path)
            logger.info(f"Sample image saved to {sample_path}")
        except Exception as e:
            logger.error(f"Failed to download sample image: {e}")
            return None

    return sample_path

def run_demo(image_path=None, output_dir="demo_output"):
    """
    Run the fashion analysis pipeline demo

    Args:
        image_path: Path to input image (if None, uses sample)
        output_dir: Directory to save outputs
    """
    # Import pipeline
    try:
        from fashion_pipeline import FashionAnalysisPipeline
    except ImportError as e:
        logger.error(f"Failed to import FashionAnalysisPipeline: {e}")
        logger.error("Make sure all dependencies are installed")
        return False

    # Use sample image if none provided
    if image_path is None:
        image_path = download_sample_image()
        if image_path is None:
            logger.error("No input image available")
            return False

    # Check if image exists
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return False

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("FASHION ANALYSIS PIPELINE DEMO")
    logger.info("=" * 60)

    # Initialize pipeline
    logger.info("\nInitializing pipeline components...")

    # Check for model file
    model_path = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"
    if not os.path.exists(model_path):
        logger.warning(f"Model file not found at {model_path}")
        logger.info("The pipeline will run but landmark detection may not work properly")
        logger.info("Please ensure the HRNet model is in the models/ directory")

    # Initialize with appropriate device
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
    except ImportError:
        device = "cpu"
        logger.warning("PyTorch not installed - using CPU mode")

    pipeline = FashionAnalysisPipeline(
        model_path=model_path,
        bg_model="u2net_cloth_seg",  # Optimized for clothing
        device=device
    )

    # Process image
    logger.info(f"\nProcessing image: {image_path}")
    logger.info("-" * 40)

    results = pipeline.process_image(
        image_path,
        output_dir=output_dir,
        visualize=True,
        remove_background=True,
        detect_landmarks=True,
        confidence_threshold=0.3
    )

    if results['success']:
        logger.info("\n✓ Processing completed successfully!")

        # Display results summary
        logger.info("\nResults Summary:")
        logger.info("-" * 40)

        if results.get('landmarks'):
            landmarks = results['landmarks']
            logger.info(f"• Detected landmarks: {landmarks['num_detected']}")
            logger.info(f"• Garment category: {landmarks['category']}")
            logger.info(f"• Confidence scores: min={min(c for c in landmarks['confidences'] if c > 0):.3f}, "
                       f"max={max(landmarks['confidences']):.3f}")

        logger.info(f"• Background removed: {'Yes' if results.get('no_background') is not None else 'No'}")
        logger.info(f"• Output directory: {output_dir}")

        # List generated files
        logger.info("\nGenerated files:")
        output_files = list(Path(output_dir).glob(f"{Path(image_path).stem}*"))
        for file in output_files:
            logger.info(f"  • {file.name}")

        # Display images if possible
        display_results = input("\nWould you like to display the results? (y/n): ").lower() == 'y'

        if display_results:
            logger.info("\nDisplaying results (press any key to continue)...")

            # Original with landmarks
            if 'landmark_visualization' in results and results['landmark_visualization'] is not None:
                cv2.imshow("Original with Landmarks", cv2.resize(
                    results['landmark_visualization'],
                    (800, 600),
                    interpolation=cv2.INTER_LINEAR
                ))
                cv2.waitKey(0)

            # White background with landmarks
            if 'clean_landmark_visualization' in results and results['clean_landmark_visualization'] is not None:
                cv2.imshow("Clean with Landmarks", cv2.resize(
                    results['clean_landmark_visualization'],
                    (800, 600),
                    interpolation=cv2.INTER_LINEAR
                ))
                cv2.waitKey(0)

            # Final composite (transparent background with landmarks)
            if 'final_composite' in results and results['final_composite'] is not None:
                composite = results['final_composite']

                # Create checkerboard background for visualization
                if len(composite.shape) == 3 and composite.shape[2] == 4:
                    h, w = composite.shape[:2]
                    checker = np.zeros((h, w, 3), dtype=np.uint8)
                    checker[::40, ::40] = 200
                    checker[20::40, 20::40] = 200

                    rgb = composite[:, :, :3]
                    alpha = composite[:, :, 3:4] / 255.0
                    display = (rgb * alpha + checker * (1 - alpha)).astype(np.uint8)
                else:
                    display = composite

                cv2.imshow("Final Composite", cv2.resize(
                    cv2.cvtColor(display, cv2.COLOR_RGB2BGR),
                    (800, 600),
                    interpolation=cv2.INTER_LINEAR
                ))
                cv2.waitKey(0)

            cv2.destroyAllWindows()

        logger.info("\n" + "=" * 60)
        logger.info("Demo completed successfully!")
        logger.info("=" * 60)
        return True

    else:
        logger.error("Processing failed!")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Fashion Analysis Pipeline Demo")
    parser.add_argument("--image", help="Input image path (uses sample if not provided)")
    parser.add_argument("--output", default="demo_output", help="Output directory")

    args = parser.parse_args()

    # Check dependencies
    logger.info("Checking dependencies...")

    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'torch': 'torch torchvision',
        'rembg': 'rembg[gpu]'  # or rembg for CPU only
    }

    missing_packages = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.warning("Missing required packages:")
        for package in missing_packages:
            logger.warning(f"  • {package}")
        logger.info("\nInstall missing packages with:")
        logger.info(f"  pip install {' '.join(missing_packages)}")

        if 'torch' in ' '.join(missing_packages):
            logger.info("\nFor PyTorch, visit: https://pytorch.org/get-started/locally/")

    # Run demo
    success = run_demo(args.image, args.output)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()