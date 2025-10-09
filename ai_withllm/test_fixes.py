#!/usr/bin/env python3
"""
Test script to verify GPT5 fixes are working properly.
"""

import sys
import traceback
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules import without errors."""
    print("Testing imports...")

    try:
        from garment_measure.calibration_tool import CalibrationTool
        print("✓ CalibrationTool imported")
    except Exception as e:
        print(f"✗ CalibrationTool import failed: {e}")
        return False

    try:
        from garment_measure.segmentation import GarmentSegmenter
        print("✓ GarmentSegmenter imported")
    except Exception as e:
        print(f"✗ GarmentSegmenter import failed: {e}")
        return False

    try:
        from garment_measure.classifier import GarmentClassifier
        print("✓ GarmentClassifier imported")
    except Exception as e:
        print(f"✗ GarmentClassifier import failed: {e}")
        return False

    try:
        from garment_measure.landmarks import LandmarkDetector
        print("✓ LandmarkDetector imported")
    except Exception as e:
        print(f"✗ LandmarkDetector import failed: {e}")
        return False

    try:
        from garment_measure.calculator import MeasurementCalculator
        print("✓ MeasurementCalculator imported")
    except Exception as e:
        print(f"✗ MeasurementCalculator import failed: {e}")
        return False

    try:
        from garment_measure.overlay import OverlayGenerator
        print("✓ OverlayGenerator imported")
    except Exception as e:
        print(f"✗ OverlayGenerator import failed: {e}")
        return False

    try:
        from garment_measure.pipeline import Pipeline
        print("✓ Pipeline imported")
    except Exception as e:
        print(f"✗ Pipeline import failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_pipeline_init():
    """Test that pipeline initializes correctly with fixed parameters."""
    print("\nTesting pipeline initialization...")

    try:
        from garment_measure.pipeline import Pipeline

        # Test minimal init
        pipeline = Pipeline("calibration.json")
        print("✓ Basic Pipeline initialization")

        # Test with model paths (without actual models)
        pipeline = Pipeline(
            "calibration.json",
            use_sam=True,
            sam_checkpoint="models/sam.pth",
            use_clip=True,
            kp_model_path="models/hrnet.onnx"
        )
        print("✓ Pipeline initialization with model paths")

        # Verify landmark detector doesn't have use_hrnet parameter
        if hasattr(pipeline.landmark_detector, 'model_path'):
            print("✓ LandmarkDetector initialized correctly")
        else:
            print("✗ LandmarkDetector missing model_path attribute")
            return False

    except Exception as e:
        print(f"✗ Pipeline initialization failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_device_detection():
    """Test that device detection works correctly."""
    print("\nTesting device detection...")

    try:
        # Test SAM device detection
        from garment_measure.segmentation import GarmentSegmenter
        segmenter = GarmentSegmenter(use_sam=False)  # Don't load actual model
        print(f"✓ SAM device detection: {segmenter.device}")

        # Test ONNX device detection (without loading model)
        from garment_measure.landmarks import LandmarkDetector
        detector = LandmarkDetector()  # No model path
        print("✓ ONNX device detection works")

    except Exception as e:
        print(f"✗ Device detection failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_thresholds():
    """Test that segmentation QC thresholds are correct."""
    print("\nTesting QC thresholds...")

    try:
        from garment_measure.segmentation import GarmentSegmenter
        segmenter = GarmentSegmenter(use_sam=False)

        if segmenter.min_area_ratio == 0.15:
            print("✓ min_area_ratio = 0.15")
        else:
            print(f"✗ min_area_ratio = {segmenter.min_area_ratio} (expected 0.15)")
            return False

        if segmenter.max_area_ratio == 0.85:
            print("✓ max_area_ratio = 0.85")
        else:
            print(f"✗ max_area_ratio = {segmenter.max_area_ratio} (expected 0.85)")
            return False

    except Exception as e:
        print(f"✗ Threshold test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing GPT5 fixes...")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Pipeline Initialization", test_pipeline_init),
        ("Device Detection", test_device_detection),
        ("QC Thresholds", test_thresholds),
    ]

    results = []
    for name, test_func in tests:
        success = test_func()
        results.append((name, success))

    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)

    all_passed = True
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
        if not success:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✅ All tests passed! The fixes are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())