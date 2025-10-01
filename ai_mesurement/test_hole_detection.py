#!/usr/bin/env python3
"""
Test script for hole detection in garments
"""

import sys
from pathlib import Path

# Test with the intelligent measurement system
from garment_measurement_intelligent import IntelligentGarmentMeasurement


def test_hole_detection():
    """Test hole detection on garment images"""

    print("\n" + "="*60)
    print("🔍 TESTING GARMENT HOLE DETECTION SYSTEM")
    print("="*60 + "\n")

    # Initialize the intelligent measurement system
    system = IntelligentGarmentMeasurement(
        ruler_length_cm=31.0,
        debug=True
    )

    # Test images
    test_images = [
        "../test_images_mesurements/ant.jpg",
        # Add more test images here
    ]

    for image_path in test_images:
        if Path(image_path).exists():
            print(f"\n🧪 Testing: {image_path}")
            print("-" * 40)

            try:
                # Run the measurement with hole detection
                result = system.measure(image_path)

                # Print hole detection results
                print(f"\n📊 HOLE DETECTION RESULTS:")
                print(f"   Defects found: {result.holes_detected}")
                print(f"   Quality score: {result.quality_score:.1f}/100")

                if result.holes_detected > 0:
                    report = result.hole_report
                    print(f"\n   Defects by type:")
                    for dtype, count in report['defects_by_type'].items():
                        print(f"      - {dtype}: {count}")

                    print(f"\n   Defects by severity:")
                    for severity, count in report['defects_by_severity'].items():
                        print(f"      - {severity}: {count}")

                    print(f"\n   Total damage area: {report['total_damage_area_cm2']:.2f} cm²")
                    print(f"   Recommendation: {report['recommendation']}")

                    if report['critical_defects']:
                        print(f"\n   ⚠️ Critical defects found:")
                        for defect in report['critical_defects']:
                            print(f"      - {defect['type']}: {defect['area_cm2']:.2f} cm² at {defect['location']}")
                else:
                    print("   ✅ No defects detected - garment in good condition")

                print(f"\n✅ Test completed successfully for {Path(image_path).name}")

            except Exception as e:
                print(f"❌ Error processing {image_path}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ Image not found: {image_path}")

    print("\n" + "="*60)
    print("✅ HOLE DETECTION TESTING COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_hole_detection()