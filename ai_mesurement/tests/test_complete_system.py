#!/usr/bin/env python3
"""Test the complete intelligent measurement system with improved classifier"""

import cv2
from pathlib import Path
from garment_measurement_intelligent import IntelligentGarmentMeasurement

print("🚀 TESTING COMPLETE INTELLIGENT SYSTEM WITH IMPROVED CLASSIFIER")
print("=" * 60)

# Initialize system
print("\n📚 Initializing intelligent measurement system...")
system = IntelligentGarmentMeasurement(ruler_length_cm=31.0, debug=False)
print("✅ System initialized\n")

# Test image
image_path = '../test_images_mesurements/ant.jpg'

print(f"📸 Processing: {Path(image_path).name}")
print("-" * 40)

# Run measurement
result = system.measure(image_path=image_path)

print("\n🎯 MEASUREMENT RESULTS:")
print("-" * 40)
print(f"   Garment Type: {result.garment_type.upper()}")
print(f"   Classification Confidence: {result.classification_confidence:.1%}")
print(f"   Overall Confidence: {result.confidence:.1%}")

print(f"\n📏 MEASUREMENTS:")
for key, value in result.measurements.items():
    if 'cm' in key:
        print(f"   {key.replace('_', ' ').title():30}: {value:7.1f} cm")

print(f"\n👕 Size Estimate: {result.size_estimate}")

# Check if visualizations were created
viz_path = Path(f"clean_annotated_{Path(image_path).stem}.png")
viz_transparent_path = Path(f"clean_annotated_{Path(image_path).stem}_transparent.png")
report_path = Path('measurement_reports') / f"intelligent_{result.garment_type}_{result.timestamp.replace(':', '').replace('-', '')[:15]}.json"

if viz_path.exists():
    print(f"\n🎨 Visualization saved: {viz_path}")
if viz_transparent_path.exists():
    print(f"🎨 Transparent visualization saved: {viz_transparent_path}")
if report_path.exists():
    print(f"📄 Report saved: {report_path}")

# Summary
print("\n" + "=" * 60)
if result.garment_type == "trousers":
    print("✅ SUCCESS! System correctly identified and measured TROUSERS")
    print("   - Using improved classifier")
    print("   - Applied proper trouser measurements")
    print("   - Following industry standards")
else:
    print(f"⚠️  System identified garment as {result.garment_type}")

print("=" * 60)