#!/usr/bin/env python3
"""Debug what measurements are actually being returned"""

import cv2
import json
from pathlib import Path
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier_improved import ImprovedGarmentClassifier, GarmentType
from garment_measurement_proper import ProperGarmentMeasurer

print("🔍 DEBUG: MEASUREMENT SYSTEM")
print("=" * 60)

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

# Step 1: Ruler detection
print("\n📏 Detecting ruler...")
ruler_detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
ruler_info = ruler_detector.detect_ruler(image)
pixels_per_cm = ruler_info['pixels_per_cm']
print(f"✅ Scale: {pixels_per_cm:.2f} pixels/cm")

# Step 2: Segmentation
print("\n✂️ Segmenting garment...")
segmenter = FastGarmentSegmenter(debug=False)
mask, seg_info = segmenter.segment_garment(image, ruler_bbox=ruler_info['bbox'])
print(f"✅ Garment segmented")

# Step 3: Classification
print("\n🔍 Classifying garment...")
classifier = ImprovedGarmentClassifier(debug=False)
garment_type, confidence, features = classifier.classify(mask, image)
print(f"✅ Type: {garment_type.value} ({confidence:.1%})")

# Step 4: Proper measurements
print("\n📐 Getting proper measurements...")
proper_measurer = ProperGarmentMeasurer(pixels_per_cm)
measurements = proper_measurer.measure_garment(mask, garment_type, image)

print("\n📊 RETURNED MEASUREMENTS:")
print("-" * 40)
print(json.dumps(measurements, indent=2, default=str))

print("\n📋 MEASUREMENT KEYS:")
print("-" * 40)
for key in sorted(measurements.keys()):
    if 'cm' in key or 'cm2' in key:
        print(f"   {key}: {measurements[key]:.1f}")

print("\n🎯 ANALYSIS:")
print("-" * 40)

expected_trouser_keys = [
    'outseam_cm', 'waist_width_cm', 'waist_circumference_cm',
    'hip_width_cm', 'thigh_width_cm', 'knee_width_cm', 'leg_opening_cm'
]

basic_keys = ['height_cm', 'width_cm', 'area_cm2']

has_trouser_measurements = any(key in measurements for key in expected_trouser_keys)
has_only_basic = all(key in basic_keys for key in measurements.keys() if 'cm' in key)

if has_trouser_measurements:
    print("✅ Proper trouser measurements found")
elif has_only_basic:
    print("❌ Only basic measurements returned")
    print("   This suggests the measure_garment method is returning basic measurements")
else:
    print("⚠️  Mixed or unknown measurements")

print("\n" + "=" * 60)