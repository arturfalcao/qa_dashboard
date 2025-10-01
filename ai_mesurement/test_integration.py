#!/usr/bin/env python3
"""Test the measurement integration locally"""

from garment_measurement_intelligent import IntelligentGarmentMeasurement
import json
from pathlib import Path

def test_measurement():
    """Test measurement on a sample image"""

    print("🧪 Testing Measurement Integration\n")

    # Initialize with correct scale
    system = IntelligentGarmentMeasurement(
        ruler_length_cm=31.0,
        manual_scale=34.32,  # Correct scale for wooden ruler
        debug=False
    )

    # Test with ant.jpg
    test_image = "../test_images_mesurements/ant.jpg"

    if not Path(test_image).exists():
        print(f"❌ Test image not found: {test_image}")
        return

    print(f"📸 Testing with: {test_image}\n")

    # Run measurement
    result = system.measure(test_image)

    if result:
        print("\n✅ MEASUREMENT SUCCESSFUL!\n")
        print("📊 Results:")
        print(f"   Garment Type: {result.garment_type}")
        print(f"   Size: {result.size_estimate}")
        print(f"   Confidence: {result.confidence:.1%}\n")

        measurements = result.measurements
        print("📐 Key Measurements:")
        print(f"   Length: {measurements.get('body_length_cm', 0):.1f} cm")
        print(f"   Chest: {measurements.get('chest_width_cm', 0):.1f} cm")
        print(f"   Waist: {measurements.get('waist_width_cm', 0):.1f} cm")
        print(f"   Hem: {measurements.get('hem_width_cm', 0):.1f} cm")

        # Save results
        output_file = "test_measurement_result.json"
        result_dict = {
            'garment_type': result.garment_type,
            'size_estimate': result.size_estimate,
            'confidence': result.confidence,
            'measurements': result.measurements,
            'timestamp': result.timestamp,
            'image_path': result.image_path
        }
        with open(output_file, 'w') as f:
            json.dump(result_dict, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")

        # Check for annotated image
        annotated = Path(f"clean_annotated_ant.png")
        if annotated.exists():
            print(f"🖼️ Annotated image: {annotated}")

        return True
    else:
        print("❌ Measurement failed")
        return False

if __name__ == "__main__":
    success = test_measurement()
    exit(0 if success else 1)