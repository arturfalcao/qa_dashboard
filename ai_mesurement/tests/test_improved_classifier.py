#!/usr/bin/env python3
"""Test the improved classifier"""

import cv2
from pathlib import Path
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier_improved import ImprovedGarmentClassifier, GarmentType

print("🚀 TESTING IMPROVED CLASSIFIER")
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

# Step 3: Test IMPROVED classifier
print("🔍 TESTING IMPROVED CLASSIFIER")
print("-" * 40)
improved_classifier = ImprovedGarmentClassifier(debug=True)
garment_type, confidence, features = improved_classifier.classify(mask, image)

print("\n📊 IMPROVED FEATURES:")
print("-" * 40)
print(f"   Has Leg Indication: {features.get('has_leg_indication', False)}")
print(f"   Has Waistband: {features.get('has_waistband', False)}")
print(f"   Width Pattern: {features.get('width_pattern', 'unknown')}")
print(f"   Bottom Width Ratio: {features.get('bottom_width_ratio', 0):.2f}")
print(f"   Top-Bottom Ratio: {features.get('top_bottom_ratio', 0):.2f}")
print(f"   Middle Narrowing: {features.get('middle_narrowing', False)}")
print(f"   Symmetry: {features.get('symmetry', 0):.2f}")

print("\n🎯 CLASSIFICATION RESULT:")
print("-" * 40)
print(f"   Type: {garment_type.value.upper()}")
print(f"   Confidence: {confidence:.1%}")

# Compare with original classifier
from garment_classifier import GarmentClassifier
print("\n📊 COMPARISON WITH ORIGINAL:")
print("-" * 40)
original_classifier = GarmentClassifier(debug=False)
orig_type, orig_conf, _ = original_classifier.classify(mask, image)
print(f"   Original: {orig_type.value} ({orig_conf:.1%})")
print(f"   Improved: {garment_type.value} ({confidence:.1%})")

if garment_type == GarmentType.TROUSERS:
    print("\n✅ SUCCESS! Improved classifier correctly identifies TROUSERS")
else:
    print(f"\n⚠️  Still detecting as {garment_type.value}, needs further improvement")

print("\n" + "=" * 60)