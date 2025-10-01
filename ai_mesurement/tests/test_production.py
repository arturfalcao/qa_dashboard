#!/usr/bin/env python3
"""Test the production measurement system"""

import sys
import signal
import traceback

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Processing timeout")

# Set 30 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

try:
    from garment_measurement_production import GarmentMeasurementProduction

    print("Testing production system with adaptive segmentation...")
    print("-" * 60)

    # Initialize with production settings
    system = GarmentMeasurementProduction(
        ruler_length_cm=31.0,
        height_calibration=0.969,
        width_calibration=1.0,
        debug=False
    )

    # Single measurement test
    result = system.measure(
        '../test_images_mesurements/ant.jpg',
        num_measurements=1
    )

    print("\n✅ TEST SUCCESSFUL!")
    print("-" * 60)
    print(f"Results:")
    print(f"  Height: {result.height_cm} cm (target: 42.5 cm)")
    print(f"  Width: {result.width_cm} cm")
    print(f"  Size: {result.size} - {result.size_category}")
    print(f"  Confidence: {result.confidence:.1%}")
    print(f"  Error: {abs(result.height_cm - 42.5):.2f} cm")

    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

except TimeoutError:
    print("❌ TEST TIMEOUT - Processing took too long")
    sys.exit(1)

except Exception as e:
    print(f"❌ TEST FAILED: {e}")
    print("\nTraceback:")
    traceback.print_exc()
    sys.exit(1)

finally:
    signal.alarm(0)  # Cancel alarm