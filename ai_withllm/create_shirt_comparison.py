#!/usr/bin/env python3
"""
Create visual comparison of shirt1 and shirt2 edge detection results
"""

import cv2
import numpy as np
import json
import os

def load_anatomical_points(json_path):
    """Load anatomical points from JSON file"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data.get('anatomical_points', {})

def visualize_comparison():
    """Create side-by-side comparison of shirt1 and shirt2"""

    # Load images
    shirt1 = cv2.imread('shirt.jpg')
    shirt2 = cv2.imread('shirt2.jpg')

    if shirt1 is None or shirt2 is None:
        print("Error loading images")
        return

    # Load anatomical points
    shirt1_points = load_anatomical_points('edge_detection_results/shirt_anatomical_points.json')
    shirt2_points = load_anatomical_points('edge_detection_results/shirt2_anatomical_points.json')

    # Create visualization copies
    shirt1_vis = shirt1.copy()
    shirt2_vis = shirt2.copy()

    # Define colors for different point types
    colors = {
        'shoulder': (0, 255, 0),       # Green
        'armpit': (255, 255, 0),       # Cyan
        'chest': (0, 0, 255),          # Red
        'hem': (255, 165, 0),          # Orange
        'collar': (255, 0, 255),       # Magenta
    }

    # Draw points and measurements on shirt1
    for name, point_data in shirt1_points.items():
        pos = tuple(point_data['position'])
        color = (0, 255, 0)  # Default green
        for key in colors:
            if key in name:
                color = colors[key]
                break

        cv2.circle(shirt1_vis, pos, 10, color, -1)
        cv2.circle(shirt1_vis, pos, 12, color, 2)
        cv2.putText(shirt1_vis, name.replace('_', ' ').title(),
                   (pos[0] + 15, pos[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw measurement lines on shirt1
    if 'left_shoulder' in shirt1_points and 'right_shoulder' in shirt1_points:
        cv2.line(shirt1_vis,
                tuple(shirt1_points['left_shoulder']['position']),
                tuple(shirt1_points['right_shoulder']['position']),
                (0, 255, 0), 2)

    if 'left_chest' in shirt1_points and 'right_chest' in shirt1_points:
        cv2.line(shirt1_vis,
                tuple(shirt1_points['left_chest']['position']),
                tuple(shirt1_points['right_chest']['position']),
                (0, 0, 255), 2)

    if 'left_hem' in shirt1_points and 'right_hem' in shirt1_points:
        cv2.line(shirt1_vis,
                tuple(shirt1_points['left_hem']['position']),
                tuple(shirt1_points['right_hem']['position']),
                (255, 165, 0), 2)

    # Draw points and measurements on shirt2
    for name, point_data in shirt2_points.items():
        pos = tuple(point_data['position'])
        color = (0, 255, 0)  # Default green
        for key in colors:
            if key in name:
                color = colors[key]
                break

        cv2.circle(shirt2_vis, pos, 10, color, -1)
        cv2.circle(shirt2_vis, pos, 12, color, 2)
        cv2.putText(shirt2_vis, name.replace('_', ' ').title(),
                   (pos[0] + 15, pos[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw measurement lines on shirt2
    if 'left_shoulder' in shirt2_points and 'right_shoulder' in shirt2_points:
        cv2.line(shirt2_vis,
                tuple(shirt2_points['left_shoulder']['position']),
                tuple(shirt2_points['right_shoulder']['position']),
                (0, 255, 0), 2)

    if 'left_chest' in shirt2_points and 'right_chest' in shirt2_points:
        cv2.line(shirt2_vis,
                tuple(shirt2_points['left_chest']['position']),
                tuple(shirt2_points['right_chest']['position']),
                (0, 0, 255), 2)

    if 'left_hem' in shirt2_points and 'right_hem' in shirt2_points:
        cv2.line(shirt2_vis,
                tuple(shirt2_points['left_hem']['position']),
                tuple(shirt2_points['right_hem']['position']),
                (255, 165, 0), 2)

    # Add titles
    cv2.putText(shirt1_vis, "Shirt1 (Blue) - Edge Detection Results",
               (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
    cv2.putText(shirt1_vis, "Shoulder: 466px | Chest: 1046px | Hem: 961px",
               (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    cv2.putText(shirt2_vis, "Shirt2 (Pink) - Edge Detection Results",
               (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
    cv2.putText(shirt2_vis, "Shoulder: 980px | Chest: 2107px | Hem: 476px",
               (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Resize images to same height for comparison
    h1, w1 = shirt1_vis.shape[:2]
    h2, w2 = shirt2_vis.shape[:2]

    # Use the smaller height
    target_height = min(h1, h2)

    # Resize if needed
    if h1 != target_height:
        scale = target_height / h1
        new_width = int(w1 * scale)
        shirt1_vis = cv2.resize(shirt1_vis, (new_width, target_height))

    if h2 != target_height:
        scale = target_height / h2
        new_width = int(w2 * scale)
        shirt2_vis = cv2.resize(shirt2_vis, (new_width, target_height))

    # Create side-by-side comparison
    comparison = np.hstack([shirt1_vis, shirt2_vis])

    # Save comparison
    output_path = 'edge_detection_results/shirt_comparison.jpg'
    cv2.imwrite(output_path, comparison)
    print(f"Saved comparison to {output_path}")

    # Also save individual annotated images
    cv2.imwrite('edge_detection_results/shirt1_annotated.jpg', shirt1_vis)
    cv2.imwrite('edge_detection_results/shirt2_annotated.jpg', shirt2_vis)

    # Print measurement comparison
    print("\n" + "="*60)
    print("MEASUREMENT COMPARISON")
    print("="*60)
    print(f"{'Measurement':<20} {'Shirt1 (Blue)':<15} {'Shirt2 (Pink)':<15} {'Difference':<15}")
    print("-"*60)

    measurements = {
        'Shoulder Width': (466.0, 980.0),
        'Chest Width': (1046.4, 2107.0),
        'Hem Width': (961.1, 476.1),
        'Length': (1346.0, 1336.0)
    }

    for name, (val1, val2) in measurements.items():
        diff = val2 - val1
        diff_pct = (diff / val1) * 100 if val1 > 0 else 0
        print(f"{name:<20} {val1:<15.1f} {val2:<15.1f} {diff:+.1f} ({diff_pct:+.1f}%)")

    print("="*60)

if __name__ == '__main__':
    visualize_comparison()