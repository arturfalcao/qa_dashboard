#!/usr/bin/env python3
"""
Compare different confidence levels for defect detection
Shows the trade-off between precision and recall
"""

from hole_detection import GarmentHoleDetector
import cv2

def test_confidence_levels(image_path: str):
    """Test different confidence thresholds"""

    print("\n" + "="*70)
    print("🔬 CONFIDENCE LEVEL COMPARISON - ZERO-SHOT DETECTION")
    print("="*70)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Cannot load image: {image_path}")
        return

    # Simple mask
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    # Test different confidence levels
    confidence_levels = [0.70, 0.80, 0.85, 0.90, 0.95]

    print("\n📊 Results at Different Confidence Levels:\n")
    print(f"{'Confidence':<12} {'Defects':<10} {'Quality Score':<15} {'Recommendation'}")
    print("-" * 70)

    for conf in confidence_levels:
        # Initialize detector
        detector = GarmentHoleDetector(
            pixels_per_cm=50.0,
            min_size='medium',
            use_ai=True,
            debug=False
        )

        # Set confidence
        if detector.use_ai:
            detector.ai_detector.set_confidence(conf)

        # Detect
        holes = detector.detect_holes(image, mask)
        report = detector.generate_report(holes)

        # Print results
        quality = f"{report['quality_score']:.1f}/100"
        rec = report['recommendation'][:30] + "..." if len(report['recommendation']) > 30 else report['recommendation']

        print(f"{conf*100:.0f}%{'':<9} {len(holes):<10} {quality:<15} {rec}")

    print("\n" + "="*70)
    print("\n📌 INTERPRETATION GUIDE:")
    print("-" * 40)
    print("• 70-75%: Maximum detection (may have false positives)")
    print("• 80-85%: Balanced approach (recommended for production)")
    print("• 90-95%: Maximum precision (may miss subtle defects)")
    print("\n💡 RECOMMENDATION:")
    print("• Quality Control: Use 85-90%")
    print("• Initial Screening: Use 75-80%")
    print("• Critical Applications: Use 90-95%")
    print("="*70 + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "../test_images_mesurements/ant.jpg"

    test_confidence_levels(image_path)