#!/usr/bin/env python3
"""
Test script for labeled landmark detection with measurement visualization
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
import json

# Add the module to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from hrnet_landmark_detector import FashionLandmarkDetector

def test_labeled_landmarks(image_path: str, output_dir: str = "labeled_output"):
    """
    Test landmark detection with meaningful labels and measurements

    Args:
        image_path: Path to input image
        output_dir: Directory to save output files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize detector
    model_path = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"
    detector = FashionLandmarkDetector(model_path, device='cpu')

    # Load image
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load image from {image_path}")
        return

    # Detect landmarks
    print("Detecting landmarks...")
    result = detector.detect_landmarks(image, confidence_threshold=0.3)

    print(f"✓ Detected category: {result['category']}")
    print(f"✓ Number of landmarks: {result['num_detected']}")

    # Get labeled landmarks
    labeled_landmarks = detector.get_landmark_labels(result)
    print(f"✓ Labeled landmarks: {len(labeled_landmarks)}")

    # Print key landmark positions
    print("\n📍 Key Measurement Points:")
    print("-" * 50)
    for label in ['left_shoulder', 'right_shoulder', 'left_collar_tip', 'right_collar_tip',
                  'center_collar', 'center_hem', 'left_armpit', 'right_armpit',
                  'left_chest', 'right_chest', 'waist_left', 'waist_right']:
        if label in labeled_landmarks:
            coord = labeled_landmarks[label]
            print(f"  {label:20s}: ({coord[0]:4d}, {coord[1]:4d})")

    # Calculate measurements
    measurements = detector.calculate_measurements(result)

    print("\n📏 Garment Measurements (in pixels):")
    print("-" * 50)
    for name, value in measurements.items():
        print(f"  {name:20s}: {value:8.1f} px")

    # Create visualizations
    print("\n🎨 Creating visualizations...")

    # 1. Original landmarks (numbered)
    basic_result = detector.draw_landmarks(image, result)
    output_path = os.path.join(output_dir, "landmarks_numbered.jpg")
    cv2.imwrite(output_path, basic_result)
    print(f"  ✓ Saved: {output_path}")

    # 2. Labeled landmarks with measurements
    labeled_result = detector.draw_landmarks_with_labels(
        image, result,
        show_measurements=True,
        point_size=8,
        font_scale=0.4
    )
    output_path = os.path.join(output_dir, "landmarks_labeled_with_measurements.jpg")
    cv2.imwrite(output_path, labeled_result)
    print(f"  ✓ Saved: {output_path}")

    # 3. Labeled landmarks without measurements (cleaner view)
    labeled_clean = detector.draw_landmarks_with_labels(
        image, result,
        show_measurements=False,
        point_size=6,
        font_scale=0.35
    )
    output_path = os.path.join(output_dir, "landmarks_labeled_clean.jpg")
    cv2.imwrite(output_path, labeled_clean)
    print(f"  ✓ Saved: {output_path}")

    # 4. Save landmark data to JSON
    landmark_data = {
        "image": os.path.basename(image_path),
        "category": result['category'],
        "num_detected": result['num_detected'],
        "labeled_landmarks": {k: list(v) for k, v in labeled_landmarks.items()},
        "measurements_px": measurements,
        "landmark_indices": {}
    }

    # Add reverse mapping (label -> index)
    if result['category'] in detector.LANDMARK_LABELS:
        labels = detector.LANDMARK_LABELS[result['category']]
        landmark_data["landmark_indices"] = {v: k for k, v in labels.items()}

    output_path = os.path.join(output_dir, "landmark_data.json")
    with open(output_path, 'w') as f:
        json.dump(landmark_data, f, indent=2)
    print(f"  ✓ Saved: {output_path}")

    # 5. Create a measurement report
    report = []
    report.append("=" * 60)
    report.append("GARMENT MEASUREMENT REPORT")
    report.append("=" * 60)
    report.append(f"Image: {os.path.basename(image_path)}")
    report.append(f"Category: {result['category']}")
    report.append(f"Detected Landmarks: {result['num_detected']}")
    report.append("")
    report.append("KEY MEASUREMENTS")
    report.append("-" * 60)

    # Add measurements with estimated cm (assuming 10 px/cm for demo)
    pixels_per_cm = 10  # This should be calibrated properly
    for name, value_px in measurements.items():
        value_cm = value_px / pixels_per_cm
        report.append(f"{name:25s}: {value_px:8.1f} px  (~{value_cm:6.1f} cm)")

    report.append("")
    report.append("LANDMARK POSITIONS")
    report.append("-" * 60)

    # Group landmarks by type
    grouped = {
        'Collar': ['left_collar_tip', 'center_collar', 'right_collar_tip'],
        'Shoulders': ['left_shoulder', 'right_shoulder'],
        'Chest': ['left_chest', 'center_chest', 'right_chest'],
        'Waist': ['waist_left', 'waist_center', 'waist_right'],
        'Hem': ['left_hem', 'center_hem', 'right_hem'],
        'Armpit': ['left_armpit', 'right_armpit'],
        'Armhole': ['left_armhole_top', 'left_armhole_bottom', 'right_armhole_top', 'right_armhole_bottom']
    }

    for group_name, labels in grouped.items():
        found = [l for l in labels if l in labeled_landmarks]
        if found:
            report.append(f"\n{group_name}:")
            for label in found:
                coord = labeled_landmarks[label]
                report.append(f"  {label:25s}: ({coord[0]:4d}, {coord[1]:4d})")

    report.append("")
    report.append("=" * 60)
    report.append("Note: For accurate measurements, calibration with a reference")
    report.append("object of known size is required.")
    report.append("=" * 60)

    # Save report
    output_path = os.path.join(output_dir, "measurement_report.txt")
    with open(output_path, 'w') as f:
        f.write('\n'.join(report))
    print(f"  ✓ Saved: {output_path}")

    print("\n✅ All visualizations and reports generated successfully!")
    print(f"📁 Output directory: {output_dir}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test labeled landmark detection")
    parser.add_argument("--image", default="shirt.jpg", help="Input image path")
    parser.add_argument("--output", default="labeled_output", help="Output directory")

    args = parser.parse_args()

    test_labeled_landmarks(args.image, args.output)


if __name__ == "__main__":
    main()