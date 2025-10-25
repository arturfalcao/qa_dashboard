#!/usr/bin/env python3
"""
Test script for background removal integration
"""

import cv2
import numpy as np
from pathlib import Path
import sys

def test_background_removal():
    """Test basic background removal functionality"""
    try:
        from background_removal import BackgroundRemover
        print("✓ Background removal module imported successfully")

        # Initialize remover
        remover = BackgroundRemover(model_name="u2net")
        print("✓ BackgroundRemover initialized")

        # Test if we have a test image
        test_images = ["test.jpg", "calibration_ll.jpg"]
        test_image = None

        for img in test_images:
            if Path(img).exists():
                test_image = img
                break

        if test_image:
            print(f"✓ Found test image: {test_image}")

            # Test mask extraction
            mask = remover.get_mask(test_image)
            print(f"✓ Mask extracted: shape={mask.shape}")

            # Calculate coverage
            coverage = (np.count_nonzero(mask) / mask.size) * 100
            print(f"  - Foreground coverage: {coverage:.1f}%")

            # Test background replacement
            result = remover.remove_background(
                test_image,
                background_color=(255, 255, 255),
                output_path="test_bg_removed.png"
            )
            print(f"✓ Background removed: shape={result.shape}")
            print(f"✓ Saved to: test_bg_removed.png")

        else:
            print("⚠ No test image found (test.jpg or calibration_ll.jpg)")

        return True

    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_system():
    """Test enhanced measurement system"""
    try:
        from enhanced_measurement_system import EnhancedGarmentMeasurementSystem
        print("\n✓ Enhanced measurement system imported successfully")

        # Check if we can initialize (don't actually run without calibration)
        print("✓ EnhancedGarmentMeasurementSystem class available")

        return True

    except ImportError as e:
        print(f"\n✗ Failed to import enhanced system: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Background Removal Integration Test")
    print("=" * 60)

    # Test 1: Basic background removal
    print("\n[Test 1] Background Removal Module")
    print("-" * 60)
    test1_passed = test_background_removal()

    # Test 2: Enhanced system
    print("\n[Test 2] Enhanced Measurement System")
    print("-" * 60)
    test2_passed = test_enhanced_system()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Background Removal: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Enhanced System:    {'✓ PASSED' if test2_passed else '✗ FAILED'}")

    if test1_passed and test2_passed:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("1. Run: venv/bin/python background_removal.py test.jpg --output result.png")
        print("2. Run: venv/bin/python enhanced_measurement_system.py test.jpg --bg-removal --compare")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
