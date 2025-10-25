#!/usr/bin/env python3
"""Convert all AVIF files to JPG in a directory."""

import os
import sys
from pathlib import Path
from PIL import Image

def convert_avif_to_jpg(directory: str):
    """Convert all .avif files to .jpg and delete originals."""
    dir_path = Path(directory)
    avif_files = list(dir_path.glob("*.avif"))

    print(f"Found {len(avif_files)} AVIF files to convert...")

    converted = 0
    errors = 0

    for avif_file in avif_files:
        try:
            # Open AVIF
            img = Image.open(avif_file)

            # Convert to RGB if necessary (AVIF might have alpha)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create JPG filename
            jpg_file = avif_file.with_suffix('.jpg')

            # Save as JPG
            img.save(jpg_file, 'JPEG', quality=95)

            # Delete original AVIF
            avif_file.unlink()

            converted += 1
            print(f"✓ {avif_file.name} → {jpg_file.name}")

        except Exception as e:
            print(f"✗ Error converting {avif_file.name}: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"Converted: {converted}")
    print(f"Errors: {errors}")
    print(f"{'='*60}")

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "/home/celso/datasets/tshirt"
    convert_avif_to_jpg(directory)
