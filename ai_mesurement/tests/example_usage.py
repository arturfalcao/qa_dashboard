#!/usr/bin/env python3
"""
Example usage of the Production Garment Measurement System
Demonstrates various use cases and best practices
"""

from garment_measurement_production import GarmentMeasurementProduction
from pathlib import Path
import json


def example_basic_measurement():
    """Example 1: Basic single measurement"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Measurement")
    print("="*60)

    # Initialize system with default settings
    system = GarmentMeasurementProduction(
        ruler_length_cm=31.0,  # Standard 31cm ruler
        debug=False
    )

    try:
        # Measure a single garment
        result = system.measure('../test_images_mesurements/ant.jpg')

        # Access measurement results
        print(f"\nMeasurement Results:")
        print(f"  Height: {result.height_cm} cm")
        print(f"  Width: {result.width_cm} cm")
        print(f"  Estimated chest: {result.chest_estimate_cm} cm")
        print(f"  Size: {result.size} - {result.size_category}")
        print(f"  Confidence: {result.confidence:.1%}")

        return result

    except Exception as e:
        print(f"Measurement failed: {e}")
        return None


def example_multiple_measurements():
    """Example 2: Multiple measurements for better accuracy"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Multiple Measurements (Recommended)")
    print("="*60)

    system = GarmentMeasurementProduction(ruler_length_cm=31.0)

    try:
        # Take 3 measurements and average them
        result = system.measure(
            '../test_images_mesurements/ant.jpg',
            num_measurements=3
        )

        print(f"\nAveraged Results (3 measurements):")
        print(f"  Height: {result.height_cm} cm")
        print(f"  Width: {result.width_cm} cm")
        print(f"  Size: {result.size}")
        print(f"  Confidence: {result.confidence:.1%}")

        return result

    except Exception as e:
        print(f"Measurement failed: {e}")
        return None


def example_custom_calibration():
    """Example 3: Using custom calibration factors"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Custom Calibration")
    print("="*60)

    # If you know your system tends to overestimate by a certain amount
    # you can adjust the calibration factors
    system = GarmentMeasurementProduction(
        ruler_length_cm=31.0,
        height_calibration=0.95,  # Reduce height by 5%
        width_calibration=1.02,   # Increase width by 2%
        debug=False
    )

    try:
        result = system.measure('../test_images_mesurements/ant.jpg')

        print(f"\nCustom Calibrated Results:")
        print(f"  Height: {result.height_cm} cm (calibration: 0.95)")
        print(f"  Width: {result.width_cm} cm (calibration: 1.02)")

        return result

    except Exception as e:
        print(f"Measurement failed: {e}")
        return None


def example_debug_mode():
    """Example 4: Debug mode with visualization"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Debug Mode")
    print("="*60)

    # Enable debug mode for visualization
    system = GarmentMeasurementProduction(
        ruler_length_cm=31.0,
        debug=True  # This will save visualization
    )

    try:
        result = system.measure('../test_images_mesurements/ant.jpg')

        print(f"\nDebug Measurement:")
        print(f"  Height: {result.height_cm} cm")
        print(f"  Width: {result.width_cm} cm")
        print(f"  Debug image saved: production_measurement_debug.png")

        # Check for warnings
        if result.warnings:
            print(f"\nWarnings detected:")
            for warning in result.warnings:
                print(f"  - {warning}")

        return result

    except Exception as e:
        print(f"Measurement failed: {e}")
        return None


def example_batch_processing():
    """Example 5: Process multiple images"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Batch Processing")
    print("="*60)

    system = GarmentMeasurementProduction(ruler_length_cm=31.0)

    # Simulate processing multiple images
    image_paths = [
        '../test_images_mesurements/ant.jpg',
        # Add more image paths here
    ]

    results = []
    for image_path in image_paths:
        try:
            print(f"\nProcessing: {Path(image_path).name}")
            result = system.measure(image_path)

            results.append({
                'file': Path(image_path).name,
                'height_cm': result.height_cm,
                'width_cm': result.width_cm,
                'size': result.size,
                'confidence': result.confidence
            })

            print(f"  ✓ {result.height_cm}×{result.width_cm} cm, Size: {result.size}")

        except Exception as e:
            print(f"  ✗ Failed: {e}")

    # Save batch results
    if results:
        with open('batch_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nBatch results saved to batch_results.json")

    return results


def example_quality_check():
    """Example 6: Quality validation"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Quality Validation")
    print("="*60)

    system = GarmentMeasurementProduction(ruler_length_cm=31.0)

    try:
        result = system.measure('../test_images_mesurements/ant.jpg')

        # Quality checks
        quality_issues = []

        if result.confidence < 0.7:
            quality_issues.append(f"Low confidence: {result.confidence:.1%}")

        if result.ruler_confidence < 0.6:
            quality_issues.append(f"Poor ruler detection: {result.ruler_confidence:.1%}")

        aspect_ratio = result.width_cm / result.height_cm
        if aspect_ratio < 0.6 or aspect_ratio > 1.5:
            quality_issues.append(f"Unusual aspect ratio: {aspect_ratio:.2f}")

        if result.warnings:
            quality_issues.extend(result.warnings)

        print(f"\nQuality Assessment:")
        if quality_issues:
            print("  ⚠️  Issues detected:")
            for issue in quality_issues:
                print(f"    - {issue}")
            print("  Recommendation: Retake photo with better lighting/contrast")
        else:
            print("  ✅ Measurement quality: GOOD")
            print(f"  Height: {result.height_cm} cm")
            print(f"  Width: {result.width_cm} cm")
            print(f"  Size: {result.size}")

        return result

    except Exception as e:
        print(f"Measurement failed: {e}")
        return None


def main():
    """Run all examples"""
    print("\n" + "█"*60)
    print(" GARMENT MEASUREMENT SYSTEM - USAGE EXAMPLES")
    print("█"*60)

    # Run examples
    print("\nRunning examples...")

    # Example 1: Basic measurement
    result1 = example_basic_measurement()

    # Example 2: Multiple measurements (commented out to save time)
    # result2 = example_multiple_measurements()

    # Example 3: Custom calibration
    result3 = example_custom_calibration()

    # Example 4: Debug mode
    # result4 = example_debug_mode()

    # Example 5: Batch processing
    # result5 = example_batch_processing()

    # Example 6: Quality check
    result6 = example_quality_check()

    print("\n" + "█"*60)
    print(" EXAMPLES COMPLETE")
    print("█"*60)

    # Summary
    if result1:
        print(f"\n📊 Summary:")
        print(f"  Default calibration: {result1.height_cm:.1f} × {result1.width_cm:.1f} cm")
        if result3:
            print(f"  Custom calibration:  {result3.height_cm:.1f} × {result3.width_cm:.1f} cm")
        print(f"  Detected size: {result1.size}")
        print(f"  Overall confidence: {result1.confidence:.1%}")


if __name__ == '__main__':
    main()