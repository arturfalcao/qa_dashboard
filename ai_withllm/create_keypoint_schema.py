#!/usr/bin/env python3
"""
Create DeepFashion2 Keypoint Schema by Analyzing Detected Landmarks

This script analyzes detected keypoints and groups them by spatial location
to help understand what each index represents for measurement purposes.
"""

import json
import numpy as np
from collections import defaultdict
from pathlib import Path


def analyze_keypoints(json_path: str):
    """Analyze keypoints and create a practical mapping"""

    with open(json_path, 'r') as f:
        data = json.load(f)

    landmarks = data['landmarks']
    confidences = data['confidences']
    category = data.get('category', 'unknown')

    # Get valid landmarks
    valid_landmarks = []
    for idx, (lm, conf) in enumerate(zip(landmarks, confidences)):
        if lm is not None and conf > 0.5:
            x, y = lm
            valid_landmarks.append({
                'index': idx,
                'x': x,
                'y': y,
                'confidence': conf
            })

    if not valid_landmarks:
        print("No valid landmarks found!")
        return

    # Calculate bounding box
    xs = [l['x'] for l in valid_landmarks]
    ys = [l['y'] for l in valid_landmarks]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y

    print("="*80)
    print(f"DEEPFASHION2 KEYPOINT SCHEMA ANALYSIS")
    print("="*80)
    print(f"\nCategory: {category}")
    print(f"Total valid keypoints (conf >50%): {len(valid_landmarks)}")
    print(f"Garment bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"Dimensions: {width}px × {height}px")

    # Divide garment into regions
    regions = categorize_by_region(valid_landmarks, min_x, max_x, min_y, max_y)

    print("\n" + "="*80)
    print("KEYPOINT MAPPING BY GARMENT REGION")
    print("="*80)

    for region_name, indices in regions.items():
        if indices:
            print(f"\n{region_name}:")
            print(f"  Indices: {sorted(indices)}")
            print(f"  Count: {len(indices)}")

    # Create measurement guide
    print("\n" + "="*80)
    print("MEASUREMENT GUIDE")
    print("="*80)
    create_measurement_guide(regions, data)

    # Save to file
    save_schema(regions, category, Path(json_path).parent / "keypoint_schema_mapping.json")


def categorize_by_region(landmarks, min_x, max_x, min_y, max_y):
    """Categorize keypoints by spatial region"""

    width = max_x - min_x
    height = max_y - min_y

    # Define regions
    top = min_y + height * 0.15
    upper = min_y + height * 0.33
    middle = min_y + height * 0.66

    left = min_x + width * 0.15
    center_left = min_x + width * 0.4
    center_right = min_x + width * 0.6
    right = min_x + width * 0.85

    regions = defaultdict(list)

    for lm in landmarks:
        idx, x, y = lm['index'], lm['x'], lm['y']

        # Vertical classification
        if y < top:
            v_region = "COLLAR"
        elif y < upper:
            v_region = "SHOULDER/UPPER"
        elif y < middle:
            v_region = "CHEST/MIDDLE"
        else:
            v_region = "HEM/BOTTOM"

        # Horizontal classification
        if x < left:
            h_region = "LEFT_EDGE"
        elif x < center_left:
            h_region = "LEFT"
        elif x < center_right:
            h_region = "CENTER"
        elif x < right:
            h_region = "RIGHT"
        else:
            h_region = "RIGHT_EDGE"

        # Combined region
        combined = f"{v_region}_{h_region}"
        regions[combined].append(idx)

        # Also add to simple regions
        regions[v_region].append(idx)
        regions[h_region].append(idx)

    return dict(regions)


def create_measurement_guide(regions, data):
    """Create a practical measurement guide"""

    key_points = data['measurements'].get('key_points', {})
    landmarks = data['landmarks']

    print("\nFor COLLAR WIDTH measurement:")
    collar_indices = regions.get('COLLAR', [])
    left_collar = [i for i in collar_indices if landmarks[i][0] < np.mean([landmarks[i][0] for i in collar_indices if landmarks[i] is not None])]
    right_collar = [i for i in collar_indices if i not in left_collar]
    print(f"  Leftmost collar points: {sorted(left_collar[:5])}")
    print(f"  Rightmost collar points: {sorted(right_collar[:5])}")
    if 'collar_left' in key_points and 'collar_right' in key_points:
        print(f"  System detected: {key_points['collar_left']} to {key_points['collar_right']}")

    print("\nFor SHOULDER WIDTH measurement:")
    shoulder_indices = regions.get('SHOULDER/UPPER', [])
    print(f"  Shoulder region indices: {sorted(shoulder_indices[:10])}")
    if 'shoulder_left' in key_points and 'shoulder_right' in key_points:
        print(f"  System detected: {key_points['shoulder_left']} to {key_points['shoulder_right']}")

    print("\nFor CHEST WIDTH measurement:")
    chest_indices = regions.get('CHEST/MIDDLE', [])
    print(f"  Chest region indices: {sorted(chest_indices[:10])}")
    if 'chest_left' in key_points and 'chest_right' in key_points:
        print(f"  System detected: {key_points['chest_left']} to {key_points['chest_right']}")

    print("\nFor HEM WIDTH measurement:")
    hem_indices = regions.get('HEM/BOTTOM', [])
    print(f"  Hem region indices: {sorted(hem_indices[:10])}")
    if 'hem_left' in key_points and 'hem_right' in key_points:
        print(f"  System detected: {key_points['hem_left']} to {key_points['hem_right']}")

    print("\nFor SLEEVE/LENGTH measurements:")
    left_edge = regions.get('LEFT_EDGE', [])
    right_edge = regions.get('RIGHT_EDGE', [])
    print(f"  Left sleeve edge indices: {sorted(left_edge[:10])}")
    print(f"  Right sleeve edge indices: {sorted(right_edge[:10])}")


def save_schema(regions, category, output_path):
    """Save the schema to JSON"""

    schema = {
        'category': category,
        'regions': {k: sorted(v) for k, v in regions.items()},
        'note': 'Indices are approximate and based on spatial analysis of detected landmarks'
    }

    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)

    print(f"\n\nSchema saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyze DeepFashion2 Keypoint Schema')
    parser.add_argument('json', help='Measurements JSON file from landmark detection')

    args = parser.parse_args()

    analyze_keypoints(args.json)


if __name__ == '__main__':
    main()
