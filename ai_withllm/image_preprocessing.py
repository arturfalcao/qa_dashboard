#!/usr/bin/env python3
"""
Image Preprocessing Pipeline for Fashion Landmark Detection

Applies various preprocessing techniques to improve landmark detection confidence:
- Background removal (optional)
- Contrast enhancement
- Noise reduction
- Edge sharpening
- Color normalization
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FashionImagePreprocessor:
    """
    Comprehensive preprocessing pipeline for fashion garment images
    """

    def __init__(self,
                 remove_background: bool = True,
                 enhance_contrast: bool = True,
                 denoise: bool = True,
                 sharpen: bool = True,
                 normalize_colors: bool = True,
                 target_size: Optional[Tuple[int, int]] = None):
        """
        Initialize preprocessing pipeline

        Args:
            remove_background: Remove background using rembg
            enhance_contrast: Apply CLAHE contrast enhancement
            denoise: Apply bilateral filtering for noise reduction
            sharpen: Sharpen edges for better keypoint localization
            normalize_colors: Normalize color distribution
            target_size: Resize to (width, height), None to keep original
        """
        self.remove_background = remove_background
        self.enhance_contrast = enhance_contrast
        self.denoise = denoise
        self.sharpen = sharpen
        self.normalize_colors = normalize_colors
        self.target_size = target_size

        # Import rembg only if needed
        if self.remove_background:
            try:
                from rembg import remove
                self.bg_remover = remove
                logger.info("Background removal enabled (rembg)")
            except ImportError:
                logger.warning("rembg not installed, background removal disabled")
                self.remove_background = False

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply full preprocessing pipeline

        Args:
            image: Input BGR image

        Returns:
            Preprocessed BGR image
        """
        logger.info("Starting preprocessing pipeline...")
        original = image.copy()

        # 1. Background Removal
        if self.remove_background:
            logger.info("  [1/5] Removing background...")
            image = self._remove_background(image)

        # 2. Noise Reduction
        if self.denoise:
            logger.info(f"  [2/5] Denoising image...")
            image = self._denoise(image)

        # 3. Contrast Enhancement
        if self.enhance_contrast:
            logger.info(f"  [3/5] Enhancing contrast...")
            image = self._enhance_contrast(image)

        # 4. Edge Sharpening
        if self.sharpen:
            logger.info(f"  [4/5] Sharpening edges...")
            image = self._sharpen(image)

        # 5. Color Normalization
        if self.normalize_colors:
            logger.info(f"  [5/5] Normalizing colors...")
            image = self._normalize_colors(image)

        # 6. Resize if target size specified
        if self.target_size is not None:
            logger.info(f"  [6/6] Resizing to {self.target_size}...")
            image = cv2.resize(image, self.target_size, interpolation=cv2.INTER_LANCZOS4)

        logger.info("Preprocessing complete!")
        return image

    def _remove_background(self, image: np.ndarray) -> np.ndarray:
        """Remove background using rembg (U2-Net)"""
        from PIL import Image

        # Convert to PIL
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # Remove background
        output_pil = self.bg_remover(pil_image)
        output_rgba = np.array(output_pil)

        # Create white background
        if output_rgba.shape[2] == 4:
            alpha = output_rgba[:, :, 3]
            # Convert back to BGR with white background
            rgb = output_rgba[:, :, :3]
            white_bg = np.ones_like(rgb) * 255

            # Alpha blend
            alpha_3ch = np.stack([alpha, alpha, alpha], axis=2) / 255.0
            result = (rgb * alpha_3ch + white_bg * (1 - alpha_3ch)).astype(np.uint8)

            return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)

        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Apply bilateral filtering for noise reduction
        Preserves edges while smoothing noise
        """
        return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Enhances local contrast without over-amplifying noise
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # Merge and convert back
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Sharpen edges using unsharp masking
        Improves keypoint localization accuracy
        """
        # Create Gaussian blur
        blurred = cv2.GaussianBlur(image, (0, 0), 3.0)

        # Unsharp mask: image + amount * (image - blurred)
        sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

        return sharpened

    def _normalize_colors(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize color distribution
        Standardizes lighting conditions
        """
        # Convert to float
        image_float = image.astype(np.float32) / 255.0

        # Normalize each channel independently
        for i in range(3):
            channel = image_float[:, :, i]
            mean = np.mean(channel)
            std = np.std(channel)

            if std > 0:
                # Normalize to mean=0.5, std=0.15
                normalized = (channel - mean) / std * 0.15 + 0.5
                image_float[:, :, i] = np.clip(normalized, 0, 1)

        # Convert back to uint8
        return (image_float * 255).astype(np.uint8)


def preprocess_image(image_path: str,
                     output_path: Optional[str] = None,
                     remove_background: bool = True,
                     enhance_contrast: bool = True,
                     denoise: bool = True,
                     sharpen: bool = True,
                     normalize_colors: bool = True) -> np.ndarray:
    """
    Convenience function to preprocess a single image

    Args:
        image_path: Path to input image
        output_path: Optional path to save preprocessed image
        remove_background: Remove background
        enhance_contrast: Enhance contrast
        denoise: Reduce noise
        sharpen: Sharpen edges
        normalize_colors: Normalize colors

    Returns:
        Preprocessed image
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Create preprocessor
    preprocessor = FashionImagePreprocessor(
        remove_background=remove_background,
        enhance_contrast=enhance_contrast,
        denoise=denoise,
        sharpen=sharpen,
        normalize_colors=normalize_colors
    )

    # Preprocess
    processed = preprocessor.preprocess(image)

    # Save if output path specified
    if output_path:
        cv2.imwrite(output_path, processed)
        logger.info(f"Saved preprocessed image to: {output_path}")

    return processed


def main():
    """Test preprocessing pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description='Fashion Image Preprocessing')
    parser.add_argument('input', help='Input image path')
    parser.add_argument('--output', '-o', help='Output image path')
    parser.add_argument('--no-bg-removal', action='store_true',
                       help='Disable background removal')
    parser.add_argument('--no-contrast', action='store_true',
                       help='Disable contrast enhancement')
    parser.add_argument('--no-denoise', action='store_true',
                       help='Disable denoising')
    parser.add_argument('--no-sharpen', action='store_true',
                       help='Disable sharpening')
    parser.add_argument('--no-normalize', action='store_true',
                       help='Disable color normalization')

    args = parser.parse_args()

    # Set output path if not specified
    if not args.output:
        from pathlib import Path
        input_path = Path(args.input)
        args.output = str(input_path.parent / f"{input_path.stem}_preprocessed{input_path.suffix}")

    # Preprocess
    processed = preprocess_image(
        args.input,
        args.output,
        remove_background=not args.no_bg_removal,
        enhance_contrast=not args.no_contrast,
        denoise=not args.no_denoise,
        sharpen=not args.no_sharpen,
        normalize_colors=not args.no_normalize
    )

    print(f"\n✓ Preprocessing complete!")
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")
    print(f"  Shape:  {processed.shape}")


if __name__ == '__main__':
    main()
