#!/usr/bin/env python3
"""Test the proper measurement system with debugging"""

import cv2
import numpy as np
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier import GarmentClassifier
from garment_measurement_proper import ProperGarmentMeasurer
from ruler_detection_smart import SmartRulerDetector

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

print("Testing Proper Measurement System")
print("="*60)

# Step 1: Ruler detection
print("\n1. Detecting ruler...")
ruler_detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
ruler_info = ruler_detector.detect_ruler(image)
pixels_per_cm = ruler_info['pixels_per_cm']
print(f"   Scale: {pixels_per_cm:.2f} pixels/cm")

# Step 2: Segmentation
print("\n2. Segmenting garment...")
segmenter = FastGarmentSegmenter(debug=False)
mask, seg_info = segmenter.segment_garment(image, ruler_bbox=ruler_info['bbox'])
print(f"   Area: {seg_info['area']:,.0f} pixels")

# Step 3: Classification with debug
print("\n3. Classifying garment...")
classifier = GarmentClassifier(debug=True)
garment_type, confidence, features = classifier.classify(mask, image)

# Step 4: Proper measurements
print("\n4. Applying proper measurements...")
measurer = ProperGarmentMeasurer(pixels_per_cm)

# Force it to be TROUSERS for testing
from garment_classifier import GarmentType
garment_type = GarmentType.TROUSERS
print(f"   Forcing type to: {garment_type.value}")

measurements = measurer.measure_garment(mask, garment_type, image)

print("\n5. RESULTS:")
print("-"*40)
for key, value in measurements.items():
    if isinstance(value, (int, float)) and 'cm' in key:
        print(f"   {key}: {value:.1f}")
    elif key == 'outseam_points' and value:
        print(f"   Outseam: Top ({value['top'][0]}, {value['top'][1]}) -> Bottom ({value['bottom'][0]}, {value['bottom'][1]})")
    elif key == 'crotch_point' and value:
        print(f"   Crotch Point: ({value[0]}, {value[1]})")

print("\nNote: All measurements are using PROPER industry standards:")
print("- Outseam: Vertical measurement from waist to hem")
print("- Hip: Measured 7-9 inches below waist")
print("- Thigh: Measured 1-2 inches below crotch")
print("- All widths are HORIZONTAL, not diagonal")