#!/usr/bin/env python3
"""
Easy script to run the smart fabric defect detector
"""

import sys
from pathlib import Path
from smart_fabric_defect_detector import SmartFabricDefectDetector
import json

def run():
    print("\n" + "="*60)
    print("🧵 SMART FABRIC DEFECT DETECTOR")
    print("   Detects defects ONLY in fabric area")
    print("   Ignores background, ruler, shadows")
    print("="*60)

    # Use test images if no arguments provided
    if len(sys.argv) < 3:
        golden = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
        test = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
        print("\n📌 Using test images (calças)")
    else:
        golden = sys.argv[1]
        test = sys.argv[2]
        print(f"\n📌 Using provided images")

    print(f"  Golden: {Path(golden).name}")
    print(f"  Test: {Path(test).name}")

    # Create detector
    detector = SmartFabricDefectDetector()

    # Output path
    output = "smart_result.png"

    # Run detection
    result = detector.detect(golden, test, output)

    if result and result['defects_found'] > 0:
        print("\n" + "="*60)
        print("✅ DEFECTS DETECTED IN FABRIC")
        print("="*60)

        for i, defect in enumerate(result['defects'][:5], 1):
            print(f"\n🎯 Defect #{i}:")
            print(f"   Type: {defect['type'].upper()}")
            print(f"   Location: ({defect['center'][0]}, {defect['center'][1]})")
            print(f"   Size: {defect['bbox'][2]}x{defect['bbox'][3]} pixels")
            if defect['type'] == 'hole':
                print(f"   ⚫ Darker than reference by {defect['brightness_diff']:.1f} units")
            print(f"   Confidence: {defect['confidence']:.0%}")

        # Save report
        with open('smart_result.json', 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n📁 Files saved:")
        print(f"   • smart_result.png - Grid visualization")
        print(f"   • smart_result_marked.png - Marked defects")
        print(f"   • smart_result_mask.png - Fabric mask")
        print(f"   • smart_result.json - Detailed report")

    else:
        print("\n✅ No defects found in fabric - garments match!")

    print("\n✨ Analysis complete!\n")

if __name__ == "__main__":
    run()