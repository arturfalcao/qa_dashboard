#!/usr/bin/env python3
"""Debug landmark-based category inference"""

import cv2
import sys
from sviplab_hrnet_integration import SVIPLabFashionDetector

def debug_inference(image_path):
    """Debug category inference for an image"""

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not load {image_path}")
        return

    # Detect landmarks
    detector = SVIPLabFashionDetector()
    result = detector.detect_landmarks(image, confidence_threshold=0.01)

    confidences = result['confidences']
    category = result['category']

    # Analyze landmark distribution
    high_conf_indices = [i for i, c in enumerate(confidences) if c > 0.5]

    print(f"\n{'='*60}")
    print(f"LANDMARK INFERENCE DEBUG: {image_path}")
    print(f"{'='*60}")
    print(f"Category detected: {category}")
    print(f"Total landmarks: {result['num_detected']}")
    print(f"High confidence (>0.5): {len(high_conf_indices)}")

    # Count by ranges
    upper_body = [i for i in high_conf_indices if 0 <= i < 158]
    lower_body = [i for i in high_conf_indices if 158 <= i < 190]
    dress_range = [i for i in high_conf_indices if 190 <= i < 294]

    print(f"\nLandmark distribution:")
    print(f"  Upper body range (0-157): {len(upper_body)} landmarks")
    print(f"  Lower body range (158-189): {len(lower_body)} landmarks")
    print(f"  Dress range (190-293): {len(dress_range)} landmarks")

    # Show specific indices
    print(f"\nHigh-confidence landmark indices:")
    print(f"  {high_conf_indices[:30]}...")

    # Check for specific patterns
    sleeve_markers = [8,9,10,11,21,22,33,34,35,36,37,52,53,54,66,67,97,98,99,100,101,116,117,118,198,199,215,216,227,228,229,230,231,250,251,252]
    trouser_markers = list(range(168, 182))

    has_sleeve = sum(1 for i in high_conf_indices if i in sleeve_markers)
    has_trouser = sum(1 for i in high_conf_indices if i in trouser_markers)

    print(f"\nPattern indicators:")
    print(f"  Sleeve markers: {has_sleeve} / {len([i for i in sleeve_markers if i in high_conf_indices])}")
    print(f"  Trouser markers: {has_trouser} / {len([i for i in trouser_markers if i in high_conf_indices])}")

    if has_trouser > 0:
        trouser_indices_found = [i for i in high_conf_indices if i in trouser_markers]
        print(f"  Trouser landmark indices found: {trouser_indices_found}")


if __name__ == '__main__':
    for img in ['shirt.jpg', 'shirt2.jpg', 'jeans.jpg']:
        debug_inference(img)
