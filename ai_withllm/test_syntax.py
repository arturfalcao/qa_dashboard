#!/usr/bin/env python3
"""
Test script to verify Python syntax is correct in all files.
"""

import ast
import sys
from pathlib import Path

def check_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            source = f.read()

        ast.parse(source)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def main():
    """Check syntax of all Python files."""
    print("Checking Python syntax...")
    print("=" * 60)

    package_dir = Path(__file__).parent / "garment_measure"

    files_to_check = [
        "calibration_tool.py",
        "segmentation.py",
        "classifier.py",
        "landmarks.py",
        "calculator.py",
        "overlay.py",
        "pipeline.py"
    ]

    all_ok = True
    for filename in files_to_check:
        file_path = package_dir / filename
        if file_path.exists():
            valid, msg = check_syntax(file_path)
            if valid:
                print(f"✓ {filename}: {msg}")
            else:
                print(f"✗ {filename}: {msg}")
                all_ok = False
        else:
            print(f"⚠ {filename}: File not found")

    print("=" * 60)
    if all_ok:
        print("✅ All files have valid Python syntax!")
        return 0
    else:
        print("❌ Some files have syntax errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())