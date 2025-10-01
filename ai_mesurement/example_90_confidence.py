#!/usr/bin/env python3
"""
Example: Using hole detection with 90% confidence threshold
Zero-shot detection - no training required
"""

from hole_detection import GarmentHoleDetector
import cv2
import numpy as np

def detect_with_high_confidence(image_path: str):
    """
    Detect defects with 90% confidence using zero-shot AI

    This provides maximum precision with minimal false positives
    """

    print("\n" + "="*60)
    print("🎯 ZERO-SHOT DEFECT DETECTION - 90% CONFIDENCE")
    print("="*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Cannot load image: {image_path}")
        return

    # Create a simple mask (in production, use proper segmentation)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    # Initialize detector with high standards
    print("\n📋 Configuration:")
    print("   • AI Model: CLIP (Zero-shot)")
    print("   • Confidence: 90%")
    print("   • Min Size: Medium (≥0.5 cm²)")
    print("   • No training required!\n")

    detector = GarmentHoleDetector(
        pixels_per_cm=50.0,
        min_size='medium',  # Only medium+ defects
        use_ai=True,
        debug=False
    )

    # Set confidence to 90%
    if detector.use_ai:
        detector.ai_detector.set_confidence(0.9)
        print("✅ Confidence set to 90%\n")

    # Detect defects
    print("🔍 Analyzing image...")
    holes = detector.detect_holes(image, mask)

    # Generate report
    report = detector.generate_report(holes)

    # Results
    print("\n📊 RESULTS (90% Confidence):")
    print("-" * 40)

    if len(holes) == 0:
        print("✅ NO DEFECTS detected with 90% confidence")
        print("   The garment appears to be in excellent condition")
        print("   (or defects don't meet the 90% confidence threshold)")
    else:
        print(f"⚠️ {len(holes)} HIGH-CONFIDENCE DEFECTS detected:")

        for i, hole in enumerate(holes[:5]):  # Show top 5
            print(f"\n   Defect #{i+1}:")
            print(f"      Type: {hole.type}")
            print(f"      Size: {hole.area_cm2:.2f} cm²")
            print(f"      Severity: {hole.severity}")
            print(f"      Location: {hole.center}")

        print(f"\n   Quality Score: {report['quality_score']:.1f}/100")
        print(f"   Recommendation: {report['recommendation']}")

    print("\n" + "="*60)
    print("💡 Notes:")
    print("   • 90% confidence = Very high certainty")
    print("   • Few false positives expected")
    print("   • May miss subtle defects")
    print("   • Best for quality control")
    print("="*60 + "\n")

    # Save visualization if defects found
    if len(holes) > 0:
        output_path = 'defects_90_confidence.png'
        detector.visualize_holes(image, holes, output_path)
        print(f"📸 Visualization saved: {output_path}")

    return holes, report


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default test image
        image_path = "../test_images_mesurements/ant.jpg"

    holes, report = detect_with_high_confidence(image_path)

    # Additional analysis
    if holes:
        print("\n🔬 Detailed Analysis:")
        print(f"   Total damage area: {sum(h.area_cm2 for h in holes):.2f} cm²")
        critical = [h for h in holes if h.severity in ['severe', 'critical']]
        if critical:
            print(f"   ⚠️ {len(critical)} critical defects require immediate attention")