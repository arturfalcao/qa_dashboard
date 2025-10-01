#!/usr/bin/env python3
"""
Test universal detector with different sensitivities
"""

from universal_defect_detector import UniversalDefectDetector
from pathlib import Path
import json

def test_with_sensitivities():
    """Test detector with various sensitivity levels"""

    golden_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test_path = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"

    sensitivities = [0.1, 0.3, 0.5, 0.7, 0.9]

    print("\n" + "="*60)
    print("TESTING UNIVERSAL DETECTOR WITH DIFFERENT SENSITIVITIES")
    print("="*60)

    best_result = None
    best_sensitivity = None

    for sensitivity in sensitivities:
        print(f"\n🔍 Testing with sensitivity: {sensitivity}")
        print("-" * 40)

        detector = UniversalDefectDetector(sensitivity=sensitivity)
        detector.debug = True

        output_path = f"/home/celso/projects/qa_dashboard/ai_mesurement/universal_test_sens_{sensitivity}.png"

        result = detector.detect(golden_path, test_path, output_path)

        if result and result['defects_found'] > 0:
            print(f"✅ Found {result['defects_found']} defects")

            if not best_result or result['defects_found'] > 0:
                best_result = result
                best_sensitivity = sensitivity

            # Show first defect
            if result['defects']:
                defect = result['defects'][0]
                print(f"   Main defect: {defect['type']} at ({defect['center'][0]}, {defect['center'][1]})")
                print(f"   Confidence: {defect['confidence']:.1%}")
        else:
            print(f"❌ No defects found")

    if best_result:
        print(f"\n{'='*60}")
        print("BEST RESULT")
        print(f"{'='*60}")
        print(f"✅ Best sensitivity: {best_sensitivity}")
        print(f"✅ Defects found: {best_result['defects_found']}")

        # Save best result
        best_report_path = "/home/celso/projects/qa_dashboard/ai_mesurement/universal_best_result.json"
        with open(best_report_path, 'w') as f:
            json.dump(best_result, f, indent=2)
        print(f"📄 Best result saved to: {best_report_path}")

        # Display all defects from best result
        print(f"\n📋 All defects detected:")
        for i, defect in enumerate(best_result['defects'][:5], 1):
            print(f"\n  {i}. {defect['type'].upper()}")
            print(f"     Location: ({defect['center'][0]}, {defect['center'][1]})")
            print(f"     Size: {defect['bbox'][2]}x{defect['bbox'][3]} pixels")
            print(f"     Area: {defect['area']:.0f} pixels²")
            print(f"     Confidence: {defect['confidence']:.1%}")
    else:
        print(f"\n⚠️ No defects found with any sensitivity level")
        print("  The hole might be too small or similar to the texture")

if __name__ == "__main__":
    test_with_sensitivities()