#!/usr/bin/env python3
"""Direct test of adaptive segmentation"""

import cv2
import numpy as np
from garment_segmentation_adaptive import AdaptiveGarmentSegmenter

print("Testing adaptive segmentation directly...")

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

if image is None:
    print(f"Failed to load image: {image_path}")
    exit(1)

print(f"Image loaded: {image.shape}")

# Test segmenter
segmenter = AdaptiveGarmentSegmenter(debug=True)

# Simple test without ruler bbox
try:
    print("\nSegmenting garment...")
    mask, info = segmenter.segment_garment(image, ruler_bbox=None)

    print(f"\n✅ Segmentation successful!")
    print(f"  Method used: {info['method']}")
    print(f"  Area: {info['area']:,.0f} pixels")
    print(f"  Score: {info['score']:.3f}")

    # Save result
    cv2.imwrite('test_segmentation_result.png', mask)
    print(f"\nMask saved to: test_segmentation_result.png")

except Exception as e:
    print(f"\n❌ Segmentation failed: {e}")
    import traceback
    traceback.print_exc()