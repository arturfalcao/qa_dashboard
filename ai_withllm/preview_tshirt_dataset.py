#!/usr/bin/env python3
"""
Preview t-shirt dataset images in a grid layout.
"""

import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

def create_preview_grid(dataset_dir: Path, num_samples: int = 16, output_file: str = "tshirt_dataset_preview.jpg"):
    """Create a grid preview of sample images from the dataset."""

    # Load annotations
    with open(dataset_dir / 'annotations.json', 'r') as f:
        data = json.load(f)

    images = data['images']
    print(f"Total images in dataset: {len(images)}")

    # Sample random images
    sample_images = random.sample(images, min(num_samples, len(images)))

    # Calculate grid dimensions
    cols = int(math.sqrt(num_samples))
    rows = math.ceil(num_samples / cols)

    # Thumbnail size
    thumb_size = 400

    # Create blank canvas
    canvas_width = cols * thumb_size
    canvas_height = rows * thumb_size
    canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')

    print(f"\nCreating {rows}x{cols} grid preview...")

    # Place images on canvas
    for idx, img_data in enumerate(sample_images):
        row = idx // cols
        col = idx % cols

        img_path = dataset_dir / 'images' / img_data['file_name']

        if not img_path.exists():
            print(f"Warning: {img_path} not found")
            continue

        # Load and resize image
        img = Image.open(img_path)
        img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)

        # Create thumbnail with border
        thumb = Image.new('RGB', (thumb_size, thumb_size), color='lightgray')

        # Center the image
        offset_x = (thumb_size - img.width) // 2
        offset_y = (thumb_size - img.height) // 2
        thumb.paste(img, (offset_x, offset_y))

        # Paste on canvas
        x = col * thumb_size
        y = row * thumb_size
        canvas.paste(thumb, (x, y))

        print(f"  Added {img_data['file_name']}")

    # Save
    canvas.save(output_file, quality=95)
    print(f"\nSaved preview to: {output_file}")

    # Print statistics
    print("\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    print(f"Total images: {len(images)}")

    # Dimension breakdown
    dims = {}
    for img in images:
        size = f'{img["width"]}x{img["height"]}'
        dims[size] = dims.get(size, 0) + 1

    print("\nImage dimensions:")
    for size, count in sorted(dims.items(), key=lambda x: -x[1]):
        print(f"  {size}: {count} images ({count/len(images)*100:.1f}%)")

    print(f"\nSample preview: {num_samples} randomly selected images")
    print(f"Preview saved to: {output_file}")

if __name__ == '__main__':
    dataset_dir = Path('tshirt_dataset')
    create_preview_grid(dataset_dir, num_samples=16)
