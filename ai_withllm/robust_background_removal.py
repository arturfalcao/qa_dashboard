#!/usr/bin/env python3
"""
ROBUST Background Removal - Uses rembg (U2-Net) for professional results
"""

import cv2
import numpy as np
from pathlib import Path
from rembg import remove
from PIL import Image
import io


def remove_background_robust(image_path: str, output_path: str = None) -> tuple:
    """
    Remove background using rembg (U2-Net deep learning model)

    Returns:
        mask: Binary mask (255=garment, 0=background)
        image_no_bg: Image with transparent background
        image_original: Original image
    """

    print(f"Loading image: {image_path}")

    # Load image
    image_original = cv2.imread(image_path)
    if image_original is None:
        raise ValueError(f"Could not load image: {image_path}")

    print(f"Image size: {image_original.shape[1]}x{image_original.shape[0]}")

    # Convert to PIL Image for rembg
    image_rgb = cv2.cvtColor(image_original, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    print("Removing background with rembg (U2-Net)...")

    # Remove background - returns RGBA image
    output_pil = remove(pil_image)

    # Convert back to numpy array
    output_rgba = np.array(output_pil)

    # Extract alpha channel as mask
    if output_rgba.shape[2] == 4:
        alpha = output_rgba[:, :, 3]
    else:
        raise ValueError("rembg did not return RGBA image")

    # Create binary mask (255 = garment, 0 = background)
    mask = (alpha > 127).astype(np.uint8) * 255

    # Create image with background removed (RGB)
    image_no_bg = cv2.cvtColor(output_rgba[:, :, :3], cv2.COLOR_RGB2BGR)

    # Apply mask to clean up edges
    image_no_bg = cv2.bitwise_and(image_no_bg, image_no_bg, mask=mask)

    print(f"✓ Background removed successfully")
    print(f"  Garment pixels: {np.sum(mask > 0)}")
    print(f"  Background pixels: {np.sum(mask == 0)}")
    print(f"  Garment coverage: {np.sum(mask > 0) / mask.size * 100:.1f}%")

    # Save if output path provided
    if output_path:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(output_path, image_no_bg)
        mask_path = str(output_path).replace('.', '_mask.')
        cv2.imwrite(mask_path, mask)
        print(f"✓ Saved cleaned image: {output_path}")
        print(f"✓ Saved mask: {mask_path}")

    return mask, image_no_bg, image_original


def create_white_background(image_no_bg: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Add white background to transparent image"""
    white_bg = np.ones_like(image_no_bg) * 255
    result = np.where(mask[:, :, None] > 0, image_no_bg, white_bg)
    return result.astype(np.uint8)


def visualize_removal(image_original: np.ndarray,
                     mask: np.ndarray,
                     image_no_bg: np.ndarray,
                     output_path: str):
    """Create visualization comparing original, mask, and result"""

    h, w = image_original.shape[:2]

    # Create side-by-side comparison
    comparison = np.zeros((h, w * 3, 3), dtype=np.uint8)

    # Panel 1: Original
    comparison[:, :w] = image_original

    # Panel 2: Mask (grayscale to BGR)
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    comparison[:, w:2*w] = mask_bgr

    # Panel 3: Result with white background
    result_white_bg = create_white_background(image_no_bg, mask)
    comparison[:, 2*w:3*w] = result_white_bg

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, "Original", (20, 50), font, 1.5, (0, 255, 0), 3)
    cv2.putText(comparison, "Mask", (w + 20, 50), font, 1.5, (0, 255, 0), 3)
    cv2.putText(comparison, "Background Removed", (2*w + 20, 50), font, 1.5, (0, 255, 0), 3)

    cv2.imwrite(output_path, comparison)
    print(f"✓ Saved comparison: {output_path}")

    return comparison


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Robust Background Removal using rembg')
    parser.add_argument('image', help='Input image path')
    parser.add_argument('--output', default='output_no_bg.jpg', help='Output image path')
    parser.add_argument('--visualize', action='store_true', help='Create visualization')

    args = parser.parse_args()

    print("="*60)
    print("ROBUST BACKGROUND REMOVAL")
    print("="*60)
    print()

    # Remove background
    mask, image_no_bg, image_original = remove_background_robust(
        args.image,
        args.output
    )

    # Create visualization if requested
    if args.visualize:
        output_dir = Path(args.output).parent
        base_name = Path(args.output).stem
        viz_path = output_dir / f"{base_name}_comparison.jpg"
        visualize_removal(image_original, mask, image_no_bg, str(viz_path))

    print()
    print("="*60)
    print("✓ BACKGROUND REMOVAL COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
