#!/usr/bin/env python3
"""Final test with forced trouser classification to show proper measurements"""

import cv2
from pathlib import Path
from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_fast import FastGarmentSegmenter
from garment_classifier import GarmentType
from garment_measurement_proper import ProperGarmentMeasurer
from measurement_visualizer_clean import CleanMeasurementVisualizer

print("🤖 DEMONSTRATING PROPER GARMENT MEASUREMENT")
print("=" * 60)

# Load image
image_path = '../test_images_mesurements/ant.jpg'
image = cv2.imread(image_path)

print(f"\n📸 Image: {Path(image_path).name}")
print(f"   Size: {image.shape[1]}x{image.shape[0]} pixels\n")

# Step 1: Ruler detection
print("📏 STEP 1: RULER CALIBRATION")
print("-" * 40)
ruler_detector = SmartRulerDetector(known_length_cm=31.0, debug=False)
ruler_info = ruler_detector.detect_ruler(image)
pixels_per_cm = ruler_info['pixels_per_cm']
print(f"✅ Scale: {pixels_per_cm:.2f} pixels/cm")
print(f"   Confidence: {ruler_info.get('confidence', 0):.1%}\n")

# Step 2: Segmentation
print("✂️ STEP 2: GARMENT SEGMENTATION")
print("-" * 40)
segmenter = FastGarmentSegmenter(debug=False)
mask, seg_info = segmenter.segment_garment(image, ruler_bbox=ruler_info['bbox'])
print(f"✅ Garment isolated: {seg_info['area']:,.0f} pixels\n")

# Step 3: Force classification as TROUSERS (since classifier has issues)
print("🔍 STEP 3: GARMENT CLASSIFICATION")
print("-" * 40)
garment_type = GarmentType.TROUSERS
print(f"✅ Type: {garment_type.value.upper()} (manually set for demo)")
print("   Note: Classifier needs improvement for this image\n")

# Step 4: Proper measurements
print("📐 STEP 4: PROPER MEASUREMENTS (Industry Standard)")
print("-" * 40)
measurer = ProperGarmentMeasurer(pixels_per_cm)
measurements = measurer.measure_garment(mask, garment_type, image)

print("✅ Measurements completed using proper methods:")
print("   - Vertical measurements (not diagonal)")
print("   - Horizontal widths at specific points")
print("   - Following ISO standards\n")

# Step 5: Create visualization
print("🎨 STEP 5: CREATING ANNOTATED OUTPUT")
print("-" * 40)
visualizer = CleanMeasurementVisualizer()
visualizer.create_clean_annotated_image(
    image=image,
    mask=mask,
    measurements=measurements,
    garment_type=garment_type,
    pixels_per_cm=pixels_per_cm,
    save_path='final_proper_measurements.png'
)
print("✅ Saved: final_proper_measurements.png")
print("✅ Saved: final_proper_measurements_transparent.png\n")

# Print results
print("=" * 60)
print("📊 FINAL MEASUREMENTS (PROPER INDUSTRY STANDARD)")
print("=" * 60)

print("\n🏷️ GARMENT TYPE: TROUSERS")
print("\n📏 MEASUREMENTS:")

# Display measurements in order
measurement_order = [
    ('outseam_cm', 'Outseam (Side Length)'),
    ('waist_width_cm', 'Waist Width'),
    ('waist_circumference_cm', 'Waist Circumference (est)'),
    ('hip_width_cm', 'Hip Width (7-9" below waist)'),
    ('thigh_width_cm', 'Thigh Width (1-2" below crotch)'),
    ('knee_width_cm', 'Knee Width'),
    ('leg_opening_cm', 'Leg Opening (Hem)'),
    ('rise_cm', 'Rise (Waist to Crotch)'),
    ('inseam_cm', 'Inseam (Crotch to Hem)')
]

for key, label in measurement_order:
    if key in measurements:
        print(f"   {label:30}: {measurements[key]:7.1f} cm")

print("\n📌 KEY DIFFERENCES FROM INCORRECT MEASUREMENTS:")
print("   ❌ OLD: Diagonal line from extreme points")
print("   ✅ NEW: Vertical outseam from waist to hem")
print()
print("   ❌ OLD: Random width measurements")
print("   ✅ NEW: Hip at 7-9\" below waist (industry standard)")
print()
print("   ❌ OLD: Inconsistent measurement points")
print("   ✅ NEW: Following ISO 18890:2018 standards")

print("\n" + "=" * 60)
print("✅ PROPER MEASUREMENT SYSTEM COMPLETE")
print("=" * 60)