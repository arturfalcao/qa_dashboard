#!/usr/bin/env python3
"""
Update the t-shirt dataset annotations with the proper keypoint schema.
"""

import json
from pathlib import Path

def update_schema():
    """Update annotations.json with proper keypoint schema."""

    annotations_path = Path('tshirt_dataset/annotations.json')

    with open(annotations_path, 'r') as f:
        data = json.load(f)

    # Define keypoint schema
    keypoints = [
        "collar_left", "collar_right", "collar_top", "collar_bottom",
        "shoulder_left_outer", "shoulder_left_inner", "shoulder_right_inner", "shoulder_right_outer",
        "sleeve_left_top", "sleeve_left_bottom", "sleeve_left_end",
        "sleeve_right_top", "sleeve_right_bottom", "sleeve_right_end",
        "armpit_left", "armpit_right",
        "waist_left", "waist_right",
        "hem_left", "hem_center", "hem_right"
    ]

    # Define skeleton connections
    skeleton = [
        # Collar
        [1, 2], [3, 4], [4, 1], [4, 2],
        # Shoulders
        [5, 6], [6, 7], [7, 8],
        # Left sleeve
        [6, 9], [9, 10], [10, 11],
        # Right sleeve
        [7, 12], [12, 13], [13, 14],
        # Body
        [10, 15], [15, 17], [17, 19],
        [13, 16], [16, 18], [18, 21],
        # Hem
        [19, 20], [20, 21]
    ]

    # Update category with keypoint schema
    data['categories'][0]['keypoints'] = keypoints
    data['categories'][0]['skeleton'] = skeleton

    print(f"Updated category with {len(keypoints)} keypoints")
    print(f"Defined {len(skeleton)} skeleton connections")

    # Save updated annotations
    with open(annotations_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nUpdated {annotations_path}")
    print(f"\nKeypoint schema:")
    for idx, kp in enumerate(keypoints):
        print(f"  {idx}: {kp}")

    print(f"\nNext steps:")
    print(f"  1. Review TSHIRT_KEYPOINT_SCHEMA.md for annotation guidelines")
    print(f"  2. Setup annotation tool (labelme, CVAT, etc.)")
    print(f"  3. Begin annotating keypoints on images")
    print(f"  4. Use preview image (tshirt_dataset_preview.jpg) to review dataset")

if __name__ == '__main__':
    update_schema()
