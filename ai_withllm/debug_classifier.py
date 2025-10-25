#!/usr/bin/env python3
"""Debug classifier to visualize detection features"""

import cv2
import numpy as np
from garment_classifier import GarmentClassifier

def visualize_features(image_path):
    """Visualize classifier features for debugging"""

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load {image_path}")
        return

    classifier = GarmentClassifier(method='rule-based')

    # Get bbox
    bbox = classifier._get_garment_bbox(image)
    print(f"\n{image_path}:")
    print(f"  Image size: {image.shape[:2]}")
    print(f"  Garment bbox: {bbox}")

    if bbox:
        bbox_height = bbox[3] - bbox[1]
        bbox_width = bbox[2] - bbox[0]
        aspect_ratio = bbox_height / bbox_width
        print(f"  Bbox size: {bbox_width} x {bbox_height}")
        print(f"  Aspect ratio: {aspect_ratio:.4f}")

    # Test inseam detection
    has_inseam = classifier._detect_inseam(image)
    print(f"  Has inseam: {has_inseam}")

    # Test sleeve detection
    has_sleeves = classifier._detect_sleeves(image)
    print(f"  Has sleeves: {has_sleeves}")

    # Classify
    result = classifier.classify(image)
    print(f"  Classification: {result['category']} ({result['confidence']:.0%})")


if __name__ == '__main__':
    for img in ['shirt.jpg', 'shirt2.jpg', 'jeans.jpg']:
        visualize_features(img)
