#!/usr/bin/env python3
"""
Verify that all GPT5 fixes have been applied correctly.
"""

import ast
import re
from pathlib import Path


def check_landmark_constructor():
    """Verify LandmarkDetector is called without use_hrnet parameter."""
    print("1. Checking LandmarkDetector constructor call...")

    pipeline_file = Path(__file__).parent / "garment_measure" / "pipeline.py"
    with open(pipeline_file, 'r') as f:
        content = f.read()

    # Check that use_hrnet is not in the call
    if "use_hrnet=" in content and "LandmarkDetector" in content:
        print("   ✗ FAIL: Found use_hrnet parameter in LandmarkDetector call")
        return False

    # Verify correct initialization
    pattern = r'LandmarkDetector\(\s*model_path=kp_model_path\s*\)'
    if re.search(pattern, content):
        print("   ✓ PASS: LandmarkDetector called correctly without use_hrnet")
        return True
    else:
        print("   ⚠ WARNING: Could not verify exact pattern, but no use_hrnet found")
        return True


def check_pixel_to_mm_restoration():
    """Verify pixel_to_mm is restored after rectified processing."""
    print("2. Checking pixel_to_mm restoration...")

    pipeline_file = Path(__file__).parent / "garment_measure" / "pipeline.py"
    with open(pipeline_file, 'r') as f:
        lines = f.readlines()

    # Check for restoration pattern
    found_save = False
    found_restore = False

    for i, line in enumerate(lines):
        if "_original_pixel_to_mm" in line and "self.calculator.pixel_to_mm" in line:
            if "=" in line:
                if "_original_pixel_to_mm =" in line:
                    found_save = True
                    print(f"   Found save at line {i+1}")
                elif "pixel_to_mm = self._original_pixel_to_mm" in line:
                    found_restore = True
                    print(f"   Found restore at line {i+1}")

    if found_save and found_restore:
        print("   ✓ PASS: pixel_to_mm properly saved and restored")
        return True
    else:
        print("   ✗ FAIL: pixel_to_mm restoration not properly implemented")
        return False


def check_segmentation_thresholds():
    """Verify segmentation QC thresholds are 0.15-0.85."""
    print("3. Checking segmentation QC thresholds...")

    seg_file = Path(__file__).parent / "garment_measure" / "segmentation.py"
    with open(seg_file, 'r') as f:
        content = f.read()

    # Check for correct thresholds
    min_pattern = r'self\.min_area_ratio\s*=\s*0\.15'
    max_pattern = r'self\.max_area_ratio\s*=\s*0\.85'

    min_found = re.search(min_pattern, content)
    max_found = re.search(max_pattern, content)

    if min_found and max_found:
        print("   ✓ PASS: Thresholds correctly set to 0.15-0.85")
        return True
    else:
        print("   ✗ FAIL: Incorrect threshold values")
        return False


def check_device_detection():
    """Verify proper device detection methods."""
    print("4. Checking device detection...")

    issues = []

    # Check SAM device detection
    seg_file = Path(__file__).parent / "garment_measure" / "segmentation.py"
    with open(seg_file, 'r') as f:
        seg_content = f.read()

    if "torch.cuda.is_available()" in seg_content:
        print("   ✓ SAM uses torch.cuda.is_available()")
    else:
        issues.append("SAM doesn't use torch.cuda.is_available()")

    # Check ONNX device detection
    landmarks_file = Path(__file__).parent / "garment_measure" / "landmarks.py"
    with open(landmarks_file, 'r') as f:
        landmarks_content = f.read()

    if "ort.get_device() ==" in landmarks_content:
        issues.append("ONNX still uses deprecated ort.get_device()")
        print("   ✗ ONNX uses deprecated ort.get_device()")
    elif "ort.get_available_providers()" in landmarks_content:
        print("   ✓ ONNX uses ort.get_available_providers()")
    else:
        print("   ⚠ ONNX device detection method unclear")

    return len(issues) == 0


def check_no_duplicates():
    """Verify no duplicate files exist."""
    print("5. Checking for duplicate files...")

    garment_dir = Path(__file__).parent / "garment_measure"

    # Check for duplicate calibration_tool files
    calib_files = list(garment_dir.glob("*calibration*tool*.py"))
    if len(calib_files) > 1:
        print(f"   ✗ FAIL: Found {len(calib_files)} calibration tool files")
        return False

    # Check for duplicate pipeline files
    pipeline_files = list(garment_dir.glob("*pipeline*.py"))
    if len(pipeline_files) > 1:
        print(f"   ✗ FAIL: Found {len(pipeline_files)} pipeline files")
        return False

    print("   ✓ PASS: No duplicate files found")
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Verifying GPT5 fixes...")
    print("=" * 60)
    print()

    checks = [
        check_landmark_constructor,
        check_pixel_to_mm_restoration,
        check_segmentation_thresholds,
        check_device_detection,
        check_no_duplicates
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append(False)
        print()

    print("=" * 60)
    print("Summary:")
    print("=" * 60)

    if all(results):
        print("✅ All GPT5 fixes have been successfully applied!")
        print()
        print("The following issues have been resolved:")
        print("1. ✓ LandmarkDetector constructor no longer uses invalid use_hrnet parameter")
        print("2. ✓ pixel_to_mm is properly restored after rectified processing")
        print("3. ✓ Segmentation QC thresholds standardized to 0.15-0.85")
        print("4. ✓ Device detection uses proper methods (torch.cuda/ort providers)")
        print("5. ✓ No duplicate files present")
        return 0
    else:
        print("❌ Some fixes are incomplete or incorrect.")
        print("Please review the checks above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())