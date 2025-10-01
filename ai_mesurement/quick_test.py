#!/usr/bin/env python3
"""Quick test of the production measurement system"""

import sys
sys.path.append('.')

from garment_measurement_production import GarmentMeasurementProduction

# Test with optimal calibration
system = GarmentMeasurementProduction(
    ruler_length_cm=31.0,
    height_calibration=0.969,  # Optimal: 42.5/43.85
    width_calibration=1.0,
    debug=False
)

try:
    # Quick single measurement
    result = system.measure(
        '../test_images_mesurements/ant.jpg',
        num_measurements=1
    )

    print("\n✅ Test completed!")
    print(f"   Height: {result.height_cm} cm (target: 42.5 cm)")
    print(f"   Error: {abs(result.height_cm - 42.5):.2f} cm")

except Exception as e:
    print(f"Test failed: {e}")