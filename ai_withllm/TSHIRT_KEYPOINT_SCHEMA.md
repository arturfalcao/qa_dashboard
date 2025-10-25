# T-Shirt Keypoint Annotation Schema

## Overview
This document defines the keypoint schema for flat-lay t-shirt annotation. These keypoints are designed to enable accurate garment measurements extraction.

## Keypoint Definitions (Total: 21 keypoints)

### 1. Collar Region (4 keypoints)
- **0: collar_left** - Left edge of collar opening
- **1: collar_right** - Right edge of collar opening
- **2: collar_top** - Top/back of collar
- **3: collar_bottom** - Bottom/front of collar (neckline)

### 2. Shoulder Region (4 keypoints)
- **4: shoulder_left_outer** - Left shoulder seam outer edge
- **5: shoulder_left_inner** - Left shoulder seam inner edge (neck side)
- **6: shoulder_right_inner** - Right shoulder seam inner edge (neck side)
- **7: shoulder_right_outer** - Right shoulder seam outer edge

### 3. Sleeve Region (6 keypoints)
- **8: sleeve_left_top** - Top of left sleeve opening
- **9: sleeve_left_bottom** - Bottom of left sleeve opening
- **10: sleeve_left_end** - End of left sleeve (cuff)
- **11: sleeve_right_top** - Top of right sleeve opening
- **12: sleeve_right_bottom** - Bottom of right sleeve opening
- **13: sleeve_right_end** - End of right sleeve (cuff)

### 4. Body Region (7 keypoints)
- **14: armpit_left** - Left armpit point (body-sleeve junction)
- **15: armpit_right** - Right armpit point (body-sleeve junction)
- **16: waist_left** - Left side seam at waist level
- **17: waist_right** - Right side seam at waist level
- **18: hem_left** - Left bottom hem edge
- **19: hem_center** - Center bottom hem edge
- **20: hem_right** - Right bottom hem edge

## Measurement Derivations

From these keypoints, the following measurements can be calculated:

### Standard T-Shirt Measurements

1. **Shoulder Width**: Distance from shoulder_left_outer to shoulder_right_outer
2. **Chest Width**: Distance from armpit_left to armpit_right (or sleeve attachment points)
3. **Body Length**: Distance from collar_bottom to hem_center
4. **Sleeve Length**: Distance from shoulder_outer to sleeve_end
5. **Collar Width**: Distance from collar_left to collar_right
6. **Hem Width**: Distance from hem_left to hem_right
7. **Waist Width**: Distance from waist_left to waist_right (if applicable)

### Additional Measurements

8. **Raglan Length**: Distance from collar to armpit (for raglan sleeves)
9. **Armhole Depth**: Vertical distance from shoulder to armpit
10. **Sleeve Opening**: Distance from sleeve_top to sleeve_bottom

## Annotation Guidelines

### General Rules
1. **Flat-lay positioning**: All t-shirts should be photographed lying flat
2. **Visibility**: Mark keypoints as "not visible" (x=0, y=0, v=0) if obscured
3. **Precision**: Annotate at seam intersections or edge midpoints
4. **Consistency**: Always annotate from the viewer's perspective (left/right as you see them)

### Keypoint Visibility Values (COCO format)
- **v=0**: Not labeled/not visible
- **v=1**: Labeled but occluded
- **v=2**: Labeled and visible

### Special Cases

#### Short Sleeves
- For t-shirts with short sleeves, sleeve_end points should be at the cuff/hem of the short sleeve

#### Long Sleeves
- sleeve_end points should be at the wrist cuff

#### Sleeveless/Tank Tops
- Mark all sleeve keypoints as not visible (v=0)
- Measurements should be adjusted accordingly

#### V-Neck vs Crew Neck
- collar_bottom position varies based on neckline style
- Maintain consistency in collar region annotation

## COCO Format Integration

### Keypoint Array Format
Each annotation contains a flat array of [x, y, v] triplets:
```python
keypoints = [
    x0, y0, v0,  # collar_left
    x1, y1, v1,  # collar_right
    # ... (21 keypoints total = 63 values)
    x20, y20, v20  # hem_right
]
```

### Category Definition
```json
{
  "id": 1,
  "name": "tshirt",
  "supercategory": "clothing",
  "keypoints": [
    "collar_left", "collar_right", "collar_top", "collar_bottom",
    "shoulder_left_outer", "shoulder_left_inner", "shoulder_right_inner", "shoulder_right_outer",
    "sleeve_left_top", "sleeve_left_bottom", "sleeve_left_end",
    "sleeve_right_top", "sleeve_right_bottom", "sleeve_right_end",
    "armpit_left", "armpit_right",
    "waist_left", "waist_right",
    "hem_left", "hem_center", "hem_right"
  ],
  "skeleton": [
    [0, 1], [2, 3], [3, 0], [3, 1],
    [4, 5], [5, 6], [6, 7],
    [5, 8], [8, 9], [9, 10],
    [6, 11], [11, 12], [12, 13],
    [9, 14], [14, 16], [16, 18],
    [12, 15], [15, 17], [17, 20],
    [18, 19], [19, 20]
  ]
}
```

## Annotation Tools

### Recommended Tools
1. **CVAT** - Computer Vision Annotation Tool (web-based)
2. **Labelme** - Python-based annotation tool
3. **LabelStudio** - Versatile annotation platform
4. **VGG Image Annotator (VIA)** - Lightweight browser-based tool

### Using Labelme
```bash
# Install
pip install labelme

# Start annotation
labelme tshirt_dataset/images --labels tshirt --config labelme_config.json

# Convert to COCO
labelme2coco tshirt_dataset/images --output tshirt_dataset/annotations.json
```

## Quality Control

### Checklist for Each Annotation
- [ ] All visible keypoints are marked
- [ ] Occluded keypoints are marked with v=1
- [ ] Keypoint positions are at exact seam/edge locations
- [ ] Left/right symmetry is maintained
- [ ] Measurements derived from keypoints are reasonable

### Expected Measurement Ranges (in pixels for 2000x2000 images)
- Shoulder width: 400-700px
- Body length: 800-1400px
- Chest width: 500-900px
- Sleeve length: 200-800px (depending on style)

## Next Steps

1. **Setup annotation tool** - Install and configure preferred tool
2. **Create pilot annotations** - Annotate 10-20 images as examples
3. **Validate schema** - Ensure keypoints enable all required measurements
4. **Batch annotation** - Annotate remaining images
5. **Quality review** - Cross-validate annotations
6. **Model training** - Train keypoint detection model on annotated dataset

## References

- COCO Keypoint Format: https://cocodataset.org/#format-data
- Garment Measurement Standards: ISO 3635, ISO 8559
- DeepFashion2 Dataset: Similar fashion keypoint annotation approach
- Fashionpedia: Comprehensive fashion attributes and keypoints
