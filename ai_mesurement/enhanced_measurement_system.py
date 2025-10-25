#!/usr/bin/env python3
"""
Enhanced Garment Measurement System with Background Removal

This module extends the garment measurement system with advanced background
removal capabilities using U2-Net model. It provides better segmentation
for challenging images with complex backgrounds.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Union
from PIL import Image

from garment_measurement_system import (
    GarmentMeasurementSystem,
    GarmentType,
    Measurement,
    Landmark
)

try:
    from background_removal import BackgroundRemover
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    logging.warning("Background removal module not available. Install rembg for enhanced segmentation.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedGarmentMeasurementSystem(GarmentMeasurementSystem):
    """
    Enhanced measurement system with optional background removal
    """

    def __init__(
        self,
        calibration_file: Optional[str] = None,
        use_background_removal: bool = False,
        bg_removal_model: str = "u2net_cloth_seg"
    ):
        """
        Initialize enhanced measurement system

        Args:
            calibration_file: Path to calibration JSON file
            use_background_removal: Enable background removal preprocessing
            bg_removal_model: Model for background removal
                - 'u2net': General purpose
                - 'u2net_cloth_seg': Optimized for clothing (recommended)
                - 'u2net_human_seg': For human/clothing
        """
        super().__init__(calibration_file)

        self.use_background_removal = use_background_removal
        self.bg_remover = None

        if use_background_removal:
            if not REMBG_AVAILABLE:
                raise RuntimeError(
                    "Background removal requested but rembg not installed. "
                    "Install with: pip install rembg[gpu]"
                )
            logger.info(f"Initializing background removal with model: {bg_removal_model}")
            self.bg_remover = BackgroundRemover(
                model_name=bg_removal_model,
                use_alpha_matting=True
            )

    def preprocess_with_bg_removal(
        self,
        image: np.ndarray,
        background_color: tuple = (240, 240, 240)
    ) -> np.ndarray:
        """
        Remove background and replace with uniform color

        Args:
            image: Input image
            background_color: RGB color for replacement background

        Returns:
            Image with background removed and replaced
        """
        if not self.bg_remover:
            return image

        logger.info("Applying background removal...")

        # Convert to PIL for rembg
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        # Remove background
        result = self.bg_remover.remove_background(
            image_rgb,
            background_color=background_color
        )

        # Convert back to BGR for OpenCV
        if len(result.shape) == 3 and result.shape[2] == 3:
            result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
        else:
            result_bgr = result

        return result_bgr

    def process_image(
        self,
        image_path: str,
        output_dir: Optional[str] = None,
        save_intermediate: bool = False
    ) -> Dict[str, Any]:
        """
        Process garment image with optional background removal

        Args:
            image_path: Path to input image
            output_dir: Directory for output files
            save_intermediate: Save intermediate processing steps

        Returns:
            Dictionary with measurements and results
        """
        logger.info(f"Processing image: {image_path}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Apply background removal if enabled
        if self.use_background_removal:
            processed_image = self.preprocess_with_bg_removal(image)

            # Save intermediate result if requested
            if save_intermediate and output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                bg_removed_file = output_path / f"{Path(image_path).stem}_bg_removed.png"
                cv2.imwrite(str(bg_removed_file), processed_image)
                logger.info(f"Saved background-removed image: {bg_removed_file}")
        else:
            processed_image = image

        # Create temporary file for processed image
        temp_path = Path(image_path).parent / f"temp_{Path(image_path).name}"
        cv2.imwrite(str(temp_path), processed_image)

        try:
            # Temporarily disable strict quality check for background-removed images
            original_check = self.check_image_quality
            if self.use_background_removal:
                # Override with relaxed check
                self.check_image_quality = lambda img: None

            # Use parent class processing on cleaned image
            results = super().process_image(str(temp_path), output_dir)

            # Restore original check
            self.check_image_quality = original_check

            # Add metadata about background removal
            results['preprocessing'] = {
                'background_removal': self.use_background_removal,
                'model': self.bg_remover.model_name if self.bg_remover else None
            }

            return results

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    def get_improved_mask(
        self,
        image_path: str
    ) -> np.ndarray:
        """
        Get high-quality segmentation mask using background removal

        Args:
            image_path: Path to input image

        Returns:
            Binary mask (0=background, 255=foreground)
        """
        if not self.bg_remover:
            raise RuntimeError("Background removal not initialized")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Get mask using background removal
        mask = self.bg_remover.get_mask(image)

        return mask

    def compare_segmentation_methods(
        self,
        image_path: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, np.ndarray]:
        """
        Compare traditional segmentation vs background removal

        Args:
            image_path: Path to input image
            output_dir: Optional directory to save comparison

        Returns:
            Dictionary with different segmentation results
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        results = {}

        # Method 1: Traditional segmentation (from parent class)
        rectified, gray = self.preprocessor.preprocess(image)
        traditional_mask, _ = self.segmentation.segment(gray)
        results['traditional'] = traditional_mask

        # Method 2: Background removal (if available)
        if self.bg_remover:
            bg_removal_mask = self.bg_remover.get_mask(image)
            results['background_removal'] = bg_removal_mask

            # Method 3: Hybrid (combine both)
            hybrid_mask = cv2.bitwise_and(traditional_mask, bg_removal_mask)
            results['hybrid'] = hybrid_mask

        # Save comparison if requested
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for method_name, mask in results.items():
                mask_file = output_path / f"{Path(image_path).stem}_mask_{method_name}.png"
                cv2.imwrite(str(mask_file), mask)

            # Create side-by-side comparison
            comparison = self._create_comparison_image(image, results)
            comp_file = output_path / f"{Path(image_path).stem}_comparison.png"
            cv2.imwrite(str(comp_file), comparison)
            logger.info(f"Saved comparison: {comp_file}")

        return results

    def _create_comparison_image(
        self,
        original: np.ndarray,
        masks: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """Create side-by-side comparison of segmentation methods"""
        # Resize for display
        h, w = original.shape[:2]
        max_h = 600
        if h > max_h:
            scale = max_h / h
            w = int(w * scale)
            h = max_h
            original = cv2.resize(original, (w, h))

        # Create colored overlays
        overlays = []

        for method_name, mask in masks.items():
            # Resize mask
            mask_resized = cv2.resize(mask, (w, h))

            # Create overlay
            overlay = original.copy()
            overlay[mask_resized > 0] = [0, 255, 0]  # Green overlay
            overlay = cv2.addWeighted(original, 0.7, overlay, 0.3, 0)

            # Add label
            cv2.putText(
                overlay,
                method_name.upper(),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            overlays.append(overlay)

        # Stack horizontally
        comparison = np.hstack(overlays)

        return comparison


def main():
    """Example usage of enhanced measurement system"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Garment Measurement with Background Removal"
    )
    parser.add_argument("image", help="Path to garment image")
    parser.add_argument("--calibration", help="Path to calibration JSON file")
    parser.add_argument("--output", help="Output directory for results")
    parser.add_argument(
        "--bg-removal",
        action="store_true",
        help="Enable background removal preprocessing"
    )
    parser.add_argument(
        "--model",
        default="u2net_cloth_seg",
        choices=["u2net", "u2net_cloth_seg", "u2net_human_seg"],
        help="Background removal model"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare segmentation methods"
    )
    parser.add_argument(
        "--save-intermediate",
        action="store_true",
        help="Save intermediate processing steps"
    )

    args = parser.parse_args()

    # Initialize system
    system = EnhancedGarmentMeasurementSystem(
        calibration_file=args.calibration,
        use_background_removal=args.bg_removal,
        bg_removal_model=args.model
    )

    try:
        if args.compare:
            # Compare segmentation methods
            logger.info("Comparing segmentation methods...")
            results = system.compare_segmentation_methods(
                args.image,
                output_dir=args.output
            )
            print("\n=== SEGMENTATION COMPARISON ===")
            for method, mask in results.items():
                area = np.count_nonzero(mask)
                total = mask.size
                coverage = (area / total) * 100
                print(f"{method}: {coverage:.1f}% coverage")

        else:
            # Process image
            results = system.process_image(
                args.image,
                output_dir=args.output,
                save_intermediate=args.save_intermediate
            )

            # Print results
            print("\n=== MEASUREMENT RESULTS ===")
            print(f"Garment Type: {results['garment_type']}")
            print(f"\nPreprocessing:")
            print(f"  Background Removal: {results['preprocessing']['background_removal']}")
            if results['preprocessing']['model']:
                print(f"  Model: {results['preprocessing']['model']}")

            print("\nMeasurements:")
            for name, data in results['measurements'].items():
                print(f"  {name}: {data['value']:.1f} ± {data['uncertainty']:.1f} mm")

            # Show overlay if no output directory specified
            if not args.output:
                cv2.imshow("Measurement Overlay", results['overlay_image'])
                cv2.waitKey(0)
                cv2.destroyAllWindows()

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise


if __name__ == "__main__":
    main()
