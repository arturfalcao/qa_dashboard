#!/usr/bin/env python3
"""
Background Removal Utility for Garment Images

This module provides advanced background removal capabilities using U2-Net model
via the rembg library. It can be used as a preprocessing step before garment
measurement or as a standalone tool for creating clean garment images.

Features:
- U2-Net based segmentation for high-quality results
- Multiple model options (u2net, u2net_human_seg, etc.)
- Alpha matting for refined edges
- Configurable background replacement (transparent, white, custom color)
- Batch processing support
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union, Tuple
import logging
from PIL import Image
from rembg import remove, new_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundRemover:
    """
    Advanced background removal for garment images using U2-Net model
    """

    def __init__(self, model_name: str = "u2net", use_alpha_matting: bool = True):
        """
        Initialize the background remover

        Args:
            model_name: Model to use. Options:
                - 'u2net': General purpose (default)
                - 'u2netp': Lightweight version
                - 'u2net_human_seg': Optimized for human/clothing
                - 'u2net_cloth_seg': Specifically for cloth segmentation
                - 'silueta': Alternative cloth model
            use_alpha_matting: Enable alpha matting for smoother edges
        """
        self.model_name = model_name
        self.use_alpha_matting = use_alpha_matting

        # Initialize rembg session for better performance
        logger.info(f"Initializing rembg session with model: {model_name}")
        self.session = new_session(model_name)
        logger.info("Background removal session ready")

    def remove_background(
        self,
        image: Union[str, np.ndarray, Image.Image],
        output_path: Optional[str] = None,
        background_color: Optional[Tuple[int, int, int]] = None,
        alpha_matting_foreground_threshold: int = 240,
        alpha_matting_background_threshold: int = 10,
        alpha_matting_erode_size: int = 10
    ) -> np.ndarray:
        """
        Remove background from an image

        Args:
            image: Input image (file path, numpy array, or PIL Image)
            output_path: Optional path to save the result
            background_color: RGB tuple for background (None=transparent, (255,255,255)=white)
            alpha_matting_foreground_threshold: Threshold for foreground (0-255)
            alpha_matting_background_threshold: Threshold for background (0-255)
            alpha_matting_erode_size: Erosion size for matting

        Returns:
            Image with background removed (RGBA if transparent, RGB if colored background)
        """
        # Load image
        if isinstance(image, str):
            pil_image = Image.open(image)
        elif isinstance(image, np.ndarray):
            # Convert BGR to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            pil_image = Image.fromarray(image_rgb)
        elif isinstance(image, Image.Image):
            pil_image = image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

        logger.info(f"Processing image of size: {pil_image.size}")

        # Remove background using rembg
        kwargs = {
            'session': self.session,
        }

        if self.use_alpha_matting:
            kwargs.update({
                'alpha_matting': True,
                'alpha_matting_foreground_threshold': alpha_matting_foreground_threshold,
                'alpha_matting_background_threshold': alpha_matting_background_threshold,
                'alpha_matting_erode_size': alpha_matting_erode_size
            })

        # Process image
        output_pil = remove(pil_image, **kwargs)

        # Convert to numpy array
        output_array = np.array(output_pil)

        # Handle background color
        if background_color is not None:
            # Create colored background
            if len(output_array.shape) == 3 and output_array.shape[2] == 4:
                # Has alpha channel
                rgb = output_array[:, :, :3]
                alpha = output_array[:, :, 3:4] / 255.0

                # Create background
                bg = np.full_like(rgb, background_color)

                # Blend
                result = (rgb * alpha + bg * (1 - alpha)).astype(np.uint8)
            else:
                result = output_array
        else:
            # Keep transparent (RGBA)
            result = output_array

        # Save if output path specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if background_color is not None:
                # Save as RGB
                cv2.imwrite(str(output_path), cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
            else:
                # Save as RGBA (PNG)
                if not str(output_path).endswith('.png'):
                    output_path = output_path.with_suffix('.png')
                Image.fromarray(result).save(str(output_path))

            logger.info(f"Saved result to: {output_path}")

        return result

    def get_mask(
        self,
        image: Union[str, np.ndarray, Image.Image]
    ) -> np.ndarray:
        """
        Get binary mask of the foreground object

        Args:
            image: Input image

        Returns:
            Binary mask (0=background, 255=foreground)
        """
        # Remove background to get alpha channel
        result = self.remove_background(image)

        # Extract alpha channel as mask
        if len(result.shape) == 3 and result.shape[2] == 4:
            mask = result[:, :, 3]
        else:
            # If no alpha, threshold on brightness
            gray = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
            _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

        return mask

    def batch_process(
        self,
        input_dir: str,
        output_dir: str,
        file_pattern: str = "*.jpg",
        background_color: Optional[Tuple[int, int, int]] = (255, 255, 255)
    ):
        """
        Process multiple images in a directory

        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save processed images
            file_pattern: Glob pattern for input files (e.g., "*.jpg", "*.png")
            background_color: Background color for processed images
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all matching files
        image_files = list(input_path.glob(file_pattern))

        if not image_files:
            logger.warning(f"No files matching pattern '{file_pattern}' found in {input_dir}")
            return

        logger.info(f"Processing {len(image_files)} images...")

        for i, img_file in enumerate(image_files, 1):
            try:
                logger.info(f"[{i}/{len(image_files)}] Processing: {img_file.name}")

                output_file = output_path / img_file.name
                self.remove_background(
                    str(img_file),
                    str(output_file),
                    background_color=background_color
                )

            except Exception as e:
                logger.error(f"Error processing {img_file.name}: {e}")
                continue

        logger.info(f"Batch processing complete. Results saved to: {output_dir}")


class BackgroundReplacementProcessor:
    """
    Advanced background replacement with additional preprocessing options
    """

    def __init__(self, remover: Optional[BackgroundRemover] = None):
        """
        Initialize with optional custom BackgroundRemover
        """
        self.remover = remover or BackgroundRemover()

    def replace_with_solid_color(
        self,
        image: Union[str, np.ndarray],
        color: Tuple[int, int, int] = (255, 255, 255),
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """Replace background with solid color"""
        return self.remover.remove_background(
            image,
            output_path=output_path,
            background_color=color
        )

    def replace_with_gradient(
        self,
        image: Union[str, np.ndarray],
        color1: Tuple[int, int, int] = (240, 240, 240),
        color2: Tuple[int, int, int] = (255, 255, 255),
        direction: str = 'vertical',
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """Replace background with gradient"""
        # Get foreground with alpha
        fg_with_alpha = self.remover.remove_background(image)

        # Create gradient background
        if isinstance(image, str):
            img = cv2.imread(image)
        else:
            img = image

        h, w = img.shape[:2]
        gradient = np.zeros((h, w, 3), dtype=np.uint8)

        if direction == 'vertical':
            for i in range(h):
                t = i / h
                color = tuple(int(c1 * (1 - t) + c2 * t)
                            for c1, c2 in zip(color1, color2))
                gradient[i, :] = color
        else:  # horizontal
            for i in range(w):
                t = i / w
                color = tuple(int(c1 * (1 - t) + c2 * t)
                            for c1, c2 in zip(color1, color2))
                gradient[:, i] = color

        # Blend foreground with gradient
        if fg_with_alpha.shape[2] == 4:
            rgb = fg_with_alpha[:, :, :3]
            alpha = fg_with_alpha[:, :, 3:4] / 255.0
            result = (rgb * alpha + gradient * (1 - alpha)).astype(np.uint8)
        else:
            result = fg_with_alpha

        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        return result

    def replace_with_image(
        self,
        foreground: Union[str, np.ndarray],
        background: Union[str, np.ndarray],
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """Replace background with custom image"""
        # Get foreground with alpha
        fg_with_alpha = self.remover.remove_background(foreground)

        # Load background
        if isinstance(background, str):
            bg_img = cv2.imread(background)
            bg_img = cv2.cvtColor(bg_img, cv2.COLOR_BGR2RGB)
        else:
            if len(background.shape) == 3 and background.shape[2] == 3:
                bg_img = cv2.cvtColor(background, cv2.COLOR_BGR2RGB)
            else:
                bg_img = background

        # Resize background to match foreground
        h, w = fg_with_alpha.shape[:2]
        bg_resized = cv2.resize(bg_img, (w, h))

        # Blend
        if fg_with_alpha.shape[2] == 4:
            rgb = fg_with_alpha[:, :, :3]
            alpha = fg_with_alpha[:, :, 3:4] / 255.0
            result = (rgb * alpha + bg_resized * (1 - alpha)).astype(np.uint8)
        else:
            result = fg_with_alpha

        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        return result


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Background Removal for Garment Images")
    parser.add_argument("input", help="Input image or directory")
    parser.add_argument("--output", help="Output path or directory")
    parser.add_argument("--model", default="u2net",
                       choices=["u2net", "u2netp", "u2net_human_seg", "u2net_cloth_seg", "silueta"],
                       help="Model to use for segmentation")
    parser.add_argument("--bg-color", nargs=3, type=int, metavar=('R', 'G', 'B'),
                       help="Background color (e.g., 255 255 255 for white)")
    parser.add_argument("--batch", action="store_true",
                       help="Process all images in input directory")
    parser.add_argument("--alpha-matting", action="store_true", default=True,
                       help="Enable alpha matting for smoother edges")
    parser.add_argument("--mask-only", action="store_true",
                       help="Output binary mask instead of image")

    args = parser.parse_args()

    # Initialize remover
    remover = BackgroundRemover(
        model_name=args.model,
        use_alpha_matting=args.alpha_matting
    )

    bg_color = tuple(args.bg_color) if args.bg_color else None

    if args.batch:
        # Batch processing
        remover.batch_process(
            args.input,
            args.output or "output",
            background_color=bg_color
        )
    else:
        # Single image
        if args.mask_only:
            mask = remover.get_mask(args.input)
            if args.output:
                cv2.imwrite(args.output, mask)
            else:
                cv2.imshow("Mask", mask)
                cv2.waitKey(0)
        else:
            result = remover.remove_background(
                args.input,
                output_path=args.output,
                background_color=bg_color
            )

            if not args.output:
                # Display result
                if len(result.shape) == 3 and result.shape[2] == 4:
                    # Create checkerboard for transparent background visualization
                    h, w = result.shape[:2]
                    checker = np.zeros((h, w, 3), dtype=np.uint8)
                    checker[::20, ::20] = 200
                    checker[10::20, 10::20] = 200

                    rgb = result[:, :, :3]
                    alpha = result[:, :, 3:4] / 255.0
                    display = (rgb * alpha + checker * (1 - alpha)).astype(np.uint8)
                else:
                    display = result

                cv2.imshow("Result", cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
                cv2.waitKey(0)
                cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
