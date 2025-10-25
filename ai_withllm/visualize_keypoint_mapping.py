#!/usr/bin/env python3
"""
Visualize and Map DeepFashion2 Keypoints

Creates an annotated visualization showing which keypoint index corresponds to which garment part.
"""

import cv2
import numpy as np
import json
from pathlib import Path
import argparse


def visualize_keypoint_mapping(image_path: str, json_path: str, output_path: str = None):
    """
    Visualize keypoints with index labels to understand the mapping

    Args:
        image_path: Path to garment image
        json_path: Path to measurements JSON with landmarks
        output_path: Where to save annotated image
    """
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Load landmarks
    with open(json_path, 'r') as f:
        data = json.load(f)

    landmarks = data['landmarks']
    confidences = data['confidences']
    category = data.get('category', 'unknown')

    # Create visualization
    vis = image.copy()

    # Draw each landmark with its index number
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    thickness = 1

    high_conf_indices = []

    for idx, (landmark, conf) in enumerate(zip(landmarks, confidences)):
        if landmark is not None and conf > 0.5:  # Only show confident points
            x, y = landmark

            # Color by confidence
            if conf > 0.8:
                color = (0, 255, 0)  # Green
                high_conf_indices.append(idx)
            elif conf > 0.7:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 165, 255)  # Orange

            # Draw point
            cv2.circle(vis, (x, y), 5, color, -1)
            cv2.circle(vis, (x, y), 7, (255, 255, 255), 1)

            # Draw index label
            label = str(idx)
            text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]

            # Background rectangle for text
            cv2.rectangle(vis,
                         (x - 2, y - text_size[1] - 4),
                         (x + text_size[0] + 2, y - 2),
                         (0, 0, 0), -1)

            # Text
            cv2.putText(vis, label, (x, y - 3), font, font_scale, (255, 255, 255), thickness)

    # Add header
    header = f"Category: {category} | Total keypoints: {len([l for l in landmarks if l is not None])}"
    cv2.putText(vis, header, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    # Save
    if output_path is None:
        output_path = str(Path(image_path).parent / f"{Path(image_path).stem}_keypoint_mapping.jpg")

    cv2.imwrite(output_path, vis)
    print(f"Saved keypoint mapping visualization: {output_path}")

    # Print high confidence indices
    print(f"\nHigh confidence keypoint indices (>80%):")
    print(high_conf_indices)

    # Create mapping report
    create_mapping_report(data, Path(output_path).parent / "keypoint_mapping_report.txt")

    return vis


def create_mapping_report(data: dict, output_path: str):
    """Create a text report of keypoint positions"""

    with open(output_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("DEEPFASHION2 KEYPOINT MAPPING REPORT\n")
        f.write("="*80 + "\n\n")

        f.write(f"Category: {data.get('category', 'unknown')}\n")
        f.write(f"Total landmarks: {data['num_landmarks']}\n\n")

        f.write("="*80 + "\n")
        f.write("HIGH CONFIDENCE LANDMARKS (>70%)\n")
        f.write("="*80 + "\n\n")

        f.write(f"{'Index':<8} {'X':<8} {'Y':<8} {'Confidence':<12} {'Notes'}\n")
        f.write("-"*80 + "\n")

        landmarks = data['landmarks']
        confidences = data['confidences']

        # Get key measurements for reference
        key_points = data['measurements'].get('key_points', {})

        for idx, (lm, conf) in enumerate(zip(landmarks, confidences)):
            if lm is not None and conf > 0.7:
                x, y = lm

                # Try to identify what this point might be
                notes = identify_keypoint(idx, lm, key_points)

                f.write(f"{idx:<8} {x:<8} {y:<8} {conf:<12.3f} {notes}\n")

        f.write("\n" + "="*80 + "\n")
        f.write("KEY MEASUREMENT POINTS\n")
        f.write("="*80 + "\n\n")

        for name, coords in key_points.items():
            f.write(f"{name}: {coords}\n")

    print(f"Saved mapping report: {output_path}")


def identify_keypoint(index: int, coords: tuple, key_points: dict) -> str:
    """Try to identify what this keypoint represents"""
    x, y = coords

    # Check if it matches any key points
    for name, kp_coords in key_points.items():
        if kp_coords == list(coords):
            return f"**{name.upper()}**"

    # General position description
    notes = []

    # This is a simplified heuristic - actual mapping would need documentation
    return ""


def main():
    parser = argparse.ArgumentParser(description='Visualize Keypoint Mapping')
    parser.add_argument('image', help='Input image')
    parser.add_argument('json', help='Measurements JSON file')
    parser.add_argument('--output', '-o', help='Output path')

    args = parser.parse_args()

    visualize_keypoint_mapping(args.image, args.json, args.output)


if __name__ == '__main__':
    main()
