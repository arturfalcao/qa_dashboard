#!/usr/bin/env python3
"""Diagnose why classifier isn't detecting trousers"""

import cv2
from pathlib import Path
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier import GarmentClassifier, GarmentType

print("🔍 CLASSIFIER DIAGNOSIS")
print("=" * 60)

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

print(f"\n📸 Image: {Path(image_path).name}")
print(f"   Size: {image.shape[1]}x{image.shape[0]} pixels\n")

# Step 1: Ruler detection
print("📏 Detecting ruler...")
ruler_detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
ruler_info = ruler_detector.detect_ruler(image)
print(f"✅ Ruler detected\n")

# Step 2: Segmentation
print("✂️ Segmenting garment...")
segmenter = FastGarmentSegmenter(debug=False)
mask, seg_info = segmenter.segment_garment(image, ruler_bbox=ruler_info['bbox'])
print(f"✅ Garment segmented\n")

# Step 3: Classification with debug
print("🔍 RUNNING CLASSIFIER WITH DEBUG")
print("-" * 40)
classifier = GarmentClassifier(debug=True)
garment_type, confidence, features = classifier.classify(mask, image)

print("\n📊 EXTRACTED FEATURES:")
print("-" * 40)
for key, value in features.items():
    if key not in ['bbox', 'area']:
        print(f"   {key:20}: {value}")

print("\n🎯 CLASSIFICATION RESULT:")
print("-" * 40)
print(f"   Type: {garment_type.value}")
print(f"   Confidence: {confidence:.1%}")

# Try to understand why it's not detecting trousers
print("\n🔬 ANALYSIS:")
print("-" * 40)

aspect_ratio = features['aspect_ratio']
has_leg_split = features['has_leg_split']
width_profile = features['width_profile']

print(f"   Aspect Ratio: {aspect_ratio:.2f}")
print(f"      - Expected for trousers: 0.7-1.1")
print(f"      - In range? {0.7 <= aspect_ratio <= 1.1}")

print(f"\n   Leg Split Detection: {has_leg_split}")
print(f"      - Expected for trousers: True")

print(f"\n   Width Profile: {width_profile}")
print(f"      - Expected for trousers: narrowing")

# Check what would happen with different aspect ratio ranges
print("\n🔧 TESTING DIFFERENT RANGES:")
print("-" * 40)

# Original range
if 0.7 <= aspect_ratio <= 1.1:
    print("   ✅ Would match original trouser range (0.7-1.1)")
else:
    print(f"   ❌ Outside original trouser range (0.7-1.1)")

# Wider range
if 0.6 <= aspect_ratio <= 1.3:
    print("   ✅ Would match wider range (0.6-1.3)")
else:
    print(f"   ❌ Outside wider range (0.6-1.3)")

# Very wide range
if 0.5 <= aspect_ratio <= 1.5:
    print("   ✅ Would match very wide range (0.5-1.5)")
else:
    print(f"   ❌ Outside very wide range (0.5-1.5)")

print("\n" + "=" * 60)