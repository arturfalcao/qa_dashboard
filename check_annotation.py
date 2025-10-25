#!/usr/bin/env python3
"""
Check and visualize annotation data against the actual image
"""
import cv2
import numpy as np
import json

# Annotation data
annotation = {
    "source": "user",
    "pair_id": 3,
    "item1": {
        "segmentation": [
            [163, 213, 184, 232, 155, 240, 105, 220, 53, 198, 3, 203, 1, 412, 13, 418, 21, 452, 5, 619, 391, 619, 344, 460, 303, 386, 327, 414, 358, 450, 328, 382, 294, 304, 352, 288, 389, 357, 394, 442, 327, 344, 270, 264, 163, 213],
            [3, 203, 1, 412, 13, 418, 3, 203],
            [303, 386, 327, 414, 358, 450, 328, 382, 294, 304, 352, 288, 389, 357, 394, 442, 327, 344, 270, 264, 303, 386],
            [358, 450, 328, 382, 294, 304, 352, 288, 389, 357, 394, 442, 358, 450]
        ],
        "scale": 3,
        "viewpoint": 2,
        "zoom_in": 2,
        "landmarks": [
            125, 209, 1, 53, 198, 2, 105, 220, 2, 155, 240, 2, 184, 232, 2, 163, 213, 1,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            13, 418, 2, 21, 452, 2,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            344, 460, 2, 303, 386, 1, 327, 414, 1, 358, 450, 2, 328, 382, 2, 294, 304, 2,
            352, 288, 2, 389, 357, 2, 394, 442, 2, 327, 344, 1, 270, 264, 2
        ],
        "style": 2,
        "bounding_box": [0, 197, 394, 622],
        "category_id": 2,
        "occlusion": 2,
        "category_name": "long sleeve top"
    }
}

# Load the image
img_path = "Pasted image (2).png"
img = cv2.imread(img_path)
if img is None:
    print(f"Error: Could not load image from {img_path}")
    exit(1)

print(f"Image shape: {img.shape}")
print(f"Annotation bounding box: {annotation['item1']['bounding_box']}")

# Create visualization
vis_img = img.copy()

# Parse landmarks (format: x, y, visibility)
landmarks_flat = annotation['item1']['landmarks']
landmarks = []
for i in range(0, len(landmarks_flat), 3):
    x, y, v = landmarks_flat[i:i+3]
    if v > 0:  # Only include visible landmarks
        landmarks.append((x, y, v))

print(f"\nTotal landmarks: {len(landmarks)}")
print("Landmark positions (x, y, visibility):")
for idx, (x, y, v) in enumerate(landmarks):
    print(f"  Landmark {idx}: ({x}, {y}, visibility={v})")

# Draw segmentation polygons
segmentations = annotation['item1']['segmentation']
for seg_idx, seg in enumerate(segmentations):
    # Convert flat list to polygon points
    points = []
    for i in range(0, len(seg), 2):
        points.append([seg[i], seg[i+1]])
    points = np.array(points, dtype=np.int32)

    # Draw polygon
    color = (0, 255, 0) if seg_idx == 0 else (0, 200, 200)
    cv2.polylines(vis_img, [points], isClosed=True, color=color, thickness=2)
    print(f"\nSegmentation polygon {seg_idx}: {len(points)} points")

# Draw bounding box
bbox = annotation['item1']['bounding_box']
x, y, w, h = bbox
cv2.rectangle(vis_img, (x, y), (x+w, y+h), (255, 0, 0), 2)
print(f"\nBounding box: x={x}, y={y}, w={w}, h={h}")

# Draw landmarks
for idx, (x, y, v) in enumerate(landmarks):
    # Different colors based on visibility
    if v == 1:  # Occluded but marked
        color = (0, 165, 255)  # Orange
    elif v == 2:  # Visible
        color = (0, 255, 0)  # Green
    else:
        color = (255, 0, 0)  # Blue

    cv2.circle(vis_img, (x, y), 5, color, -1)
    cv2.circle(vis_img, (x, y), 7, (255, 255, 255), 1)
    cv2.putText(vis_img, str(idx), (x+10, y+10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

# Add legend
legend_y = 30
cv2.putText(vis_img, "Legend:", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
cv2.circle(vis_img, (20, legend_y + 25), 5, (0, 255, 0), -1)
cv2.putText(vis_img, "Visible (v=2)", (35, legend_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
cv2.circle(vis_img, (20, legend_y + 50), 5, (0, 165, 255), -1)
cv2.putText(vis_img, "Occluded (v=1)", (35, legend_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

# Add annotation info
info_text = f"Category: {annotation['item1']['category_name']} | Scale: {annotation['item1']['scale']} | Viewpoint: {annotation['item1']['viewpoint']}"
cv2.putText(vis_img, info_text, (10, img.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

# Save visualization
output_path = "annotation_check_result.jpg"
cv2.imwrite(output_path, vis_img)
print(f"\n✓ Visualization saved to: {output_path}")

# Check if landmarks are within image bounds
h, w = img.shape[:2]
print(f"\nImage dimensions: {w}x{h}")
print("Checking landmark bounds:")
out_of_bounds = []
for idx, (x, y, v) in enumerate(landmarks):
    if x < 0 or x >= w or y < 0 or y >= h:
        out_of_bounds.append((idx, x, y))

if out_of_bounds:
    print("⚠ WARNING: Some landmarks are out of bounds:")
    for idx, x, y in out_of_bounds:
        print(f"  Landmark {idx}: ({x}, {y})")
else:
    print("✓ All landmarks are within image bounds")

# Check bounding box validity
bbox_x, bbox_y, bbox_w, bbox_h = annotation['item1']['bounding_box']
if bbox_x < 0 or bbox_y < 0 or bbox_x + bbox_w > w or bbox_y + bbox_h > h:
    print(f"⚠ WARNING: Bounding box extends outside image bounds")
else:
    print(f"✓ Bounding box is valid")
