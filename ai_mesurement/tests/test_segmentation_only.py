"""Quick test of segmentation only"""

import cv2
from garment_segmentation_v2 import ImprovedGarmentSegmenter

image = cv2.imread('../test_images_mesurements/anti.jpg')
print(f"Image loaded: {image.shape}")

segmenter = ImprovedGarmentSegmenter(debug=True)

# Test with ruler bbox from previous detection
ruler_bbox = (41, 1191, 1487, 1807)  # Approximate from debug image

print("Starting segmentation...")
garment_mask, garment_info = segmenter.segment_garment(image, ruler_bbox=ruler_bbox)

print(f"\nSegmentation complete!")
print(f"  Garment area: {garment_info['area']:.0f} pixels²")
print(f"  Garment bbox: {garment_info['bbox']}")
