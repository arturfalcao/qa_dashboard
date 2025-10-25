# DeepFashion2 Keypoint Measurement Guide

## Overview
DeepFashion2 provides **294 total keypoints** across 13 garment categories. Each category uses a different subset. Your system detected this garment as **vest** category with **237 valid keypoints**.

---

## Quick Reference: Keypoint Indices by Measurement

### 1. COLLAR WIDTH
**Purpose:** Measure neckline opening

**Keypoint Regions:**
- **Left collar points:** Indices 1, 2, 26, 27, 59, 60, 61, 90, 91, 92, 129, 130
- **Right collar points:** Indices 23, 56, 81, 120, 217, 254
- **Center collar:** Indices 0, 3, 4, 5, 24, 25, 28, 29, 30

**How to measure:**
- Find the leftmost point in LEFT_COLLAR region
- Find the rightmost point in RIGHT_COLLAR region
- Calculate Euclidean distance

**Example from shirt2.jpg:**
- Left point: [1521, 802]
- Right point: [2492, 886]
- Width: 983.17px

---

### 2. SHOULDER WIDTH
**Purpose:** Measure across shoulders (widest point of upper garment)

**Keypoint Regions:**
- **Shoulder region:** Indices 6, 7, 19, 31, 32, 48, 55, 64, 65, 77, 95, 96, 112, 119, 134, 196, 197, 213, 225, 226, 246, 253, 262

**How to measure:**
- Find the leftmost point in SHOULDER/UPPER region
- Find the rightmost point in SHOULDER/UPPER region
- Calculate distance

**Example from shirt2.jpg:**
- Left point: [1140, 1182]
- Right point: [2788, 1097]
- Width: 1690.52px

---

### 3. CHEST WIDTH (Bust/Armpit Width)
**Purpose:** Measure widest part of garment body

**Keypoint Regions:**
- **Left chest:** Indices 10, 11, 12, 38, 39, 40, 41, 68, 69, 70, 102, 103, 104, 105
- **Right chest:** Indices 17, 18, 20, 46, 47, 49, 50, 51, 75, 76, 78, 110, 111, 113, 114, 115
- **Left edge:** Indices 33, 34, 97, 98, 227, 228
- **Right edge:** Indices 21, 22, 52, 53, 54, 79, 80, 116, 117, 118, 215, 216, 250, 251, 252

**How to measure:**
- Find the leftmost point in CHEST/MIDDLE_LEFT_EDGE
- Find the rightmost point in CHEST/MIDDLE_RIGHT_EDGE
- Calculate distance

**Example from shirt2.jpg:**
- Left point: [802, 1604]
- Right point: [3211, 1435]
- Width: 2414.87px

---

### 4. HEM WIDTH (Bottom Width)
**Purpose:** Measure bottom opening of garment

**Keypoint Regions:**
- **Left hem:** Indices 13, 14, 42, 43, 71, 72, 106, 107, 136, 137, 151, 152, 162, 173, 186, 206, 239, 267, 286
- **Right hem:** Indices 16, 45, 74, 109, 139, 154, 166, 179, 188, 208, 241, 269, 288
- **Left edge:** Indices 8, 9, 35, 36, 37, 66, 67, 99, 100, 101, 198, 199, 229, 230, 231

**How to measure:**
- Find the leftmost point in HEM/BOTTOM_LEFT_EDGE
- Find the rightmost point in HEM/BOTTOM (right side)
- Calculate distance

**Example from shirt2.jpg:**
- Left point: [676, 1900]
- Right point: [3084, 1646]
- Width: 2421.41px

---

### 5. TOTAL LENGTH (Collar to Hem)
**Purpose:** Measure garment length

**How to measure:**
- Find the topmost Y coordinate in COLLAR region
- Find the bottommost Y coordinate in HEM/BOTTOM region
- Calculate vertical distance

**Example from shirt2.jpg:**
- Top: Y = 760
- Bottom: Y = 2195
- Length: 1435px

---

### 6. SLEEVE LENGTH
**Purpose:** Measure sleeve from shoulder to cuff

**Keypoint Regions:**
- **Left sleeve edge:** Indices 8, 9, 33, 34, 35, 36, 37, 66, 67, 97, 98, 99, 100, 101, 198, 199, 227, 228, 229, 230, 231
- **Right sleeve edge:** Indices 21, 22, 52, 53, 54, 79, 80, 116, 117, 118, 215, 216, 250, 251, 252

**How to measure:**
- Find shoulder point (intersection of SHOULDER and LEFT/RIGHT regions)
- Find cuff point (extremity of LEFT_EDGE or RIGHT_EDGE)
- Calculate distance along sleeve edge

**Example from shirt2.jpg:**
- Left sleeve: 854.90px
- Right sleeve: 854.49px

---

## Complete Region Mapping

### Vertical Regions (Top to Bottom)
1. **COLLAR** - Top 15% (neckline area)
2. **SHOULDER/UPPER** - 15-33% (shoulder area)
3. **CHEST/MIDDLE** - 33-66% (body area)
4. **HEM/BOTTOM** - 66-100% (bottom area)

### Horizontal Regions (Left to Right)
1. **LEFT_EDGE** - Leftmost 15% (left cuff/edge)
2. **LEFT** - 15-40% (left body)
3. **CENTER** - 40-60% (button placket, center seam)
4. **RIGHT** - 60-85% (right body)
5. **RIGHT_EDGE** - Rightmost 15% (right cuff/edge)

### Combined Regions
- **COLLAR_LEFT** (23 indices): Left neckline
- **COLLAR_CENTER** (40 indices): Center neckline
- **COLLAR_RIGHT** (6 indices): Right neckline
- **SHOULDER/UPPER_LEFT** (14 indices): Left shoulder
- **SHOULDER/UPPER_RIGHT** (9 indices): Right shoulder
- **CHEST/MIDDLE_LEFT_EDGE** (6 indices): Left armpit/side seam
- **CHEST/MIDDLE_RIGHT_EDGE** (15 indices): Right armpit/side seam
- **HEM/BOTTOM_LEFT_EDGE** (15 indices): Left cuff/hem edge
- And more...

---

## Usage in Code

```python
# Load measurements
with open('measurements.json', 'r') as f:
    data = json.load(f)

landmarks = data['landmarks']
confidences = data['confidences']

# Example: Get collar width
collar_left_indices = [1, 2, 26, 27, 59, 60, 61]
collar_right_indices = [23, 56, 81, 120, 217, 254]

# Find valid points with high confidence
left_points = [landmarks[i] for i in collar_left_indices
               if landmarks[i] is not None and confidences[i] > 0.7]
right_points = [landmarks[i] for i in collar_right_indices
                if landmarks[i] is not None and confidences[i] > 0.7]

# Get leftmost and rightmost
leftmost = min(left_points, key=lambda p: p[0])
rightmost = max(right_points, key=lambda p: p[0])

# Calculate width
import numpy as np
width = np.sqrt((rightmost[0] - leftmost[0])**2 + (rightmost[1] - leftmost[1])**2)
print(f"Collar width: {width:.2f}px")
```

---

## Files Generated

1. **keypoint_mapping_shirt2.jpg** - Visual map with all keypoint indices labeled
2. **keypoint_mapping_report.txt** - Detailed text report of all high-confidence keypoints
3. **keypoint_schema_mapping.json** - Machine-readable schema of regions and indices
4. **This guide** - Human-readable measurement instructions

---

## Important Notes

1. **Not all 294 keypoints are used** - Each garment category uses different indices
2. **Indices are consistent** - Same indices always represent the same garment feature within a category
3. **Confidence matters** - Only use keypoints with confidence >70% for accurate measurements
4. **Official schema** - See https://github.com/switchablenorms/DeepFashion2 for complete visual diagrams

---

## Next Steps

For calibration to real-world measurements:
1. Place a ruler/reference object of known size in the image
2. Calculate pixels-per-centimeter ratio
3. Convert all pixel measurements to centimeters

Example:
```python
# If ruler shows 30cm = 1200px
pixels_per_cm = 1200 / 30  # 40 pixels/cm

# Convert measurements
collar_width_cm = collar_width_px / pixels_per_cm
```
