# Numbered Landmarks Visualization Guide

## Overview

The pipeline now displays **landmark index numbers** on each detected point, making it easy to identify which landmarks correspond to which measurements according to the DeepFashion2 structure.

## Visualization Features

### Landmark Display

Each landmark is shown with:
- **Colored dot**: Green (high confidence >50%) or Orange (moderate confidence 30-50%)
- **White border**: For visibility against any background
- **Index number**: The landmark's position in the 294-landmark array

### Example - long_sleeved_shirt (landmarks 25-57):

You can now see the exact landmark indices:
- **Landmark 27, 31**: Collar width endpoints
- **Landmark 33, 46**: Shoulder width endpoints  
- **Landmark 38, 44**: Chest width endpoints
- **Landmark 41, 43**: Hem width endpoints
- **Landmark 35, 36**: Left cuff endpoints
- **Landmark 48, 49**: Right cuff endpoints
- **Landmark 28, 42**: Body length endpoints
- **Landmark 33, 36**: Left sleeve length
- **Landmark 46, 49**: Right sleeve length

## Using the Numbered Landmarks

### To Measure Specific Features:

1. **Look at the visualization** to find the landmark numbers
2. **Reference the mapping** in `deepfashion2_landmark_mapping.py`
3. **Verify measurements** match the expected landmark pairs

### Example Usage:

If you want to measure collar width on a long-sleeved shirt:
- Find landmarks **27** and **31** on the visualization
- The distance between them is the collar width
- Verify in JSON: `collar_width: landmarks [27, 31]`

## Landmark Ranges by Category

All landmarks are numbered 0-293 in the detection array:

| Category | Landmark Range | Total |
|----------|---------------|-------|
| short_sleeved_shirt | 0-24 | 25 |
| long_sleeved_shirt | 25-57 | 33 |
| short_sleeved_outwear | 58-88 | 31 |
| long_sleeved_outwear | 89-127 | 39 |
| vest | 128-142 | 15 |
| sling | 143-157 | 15 |
| shorts | 158-167 | 10 |
| trousers | 168-181 | 14 |
| skirt | 182-189 | 8 |
| short_sleeved_dress | 190-218 | 29 |
| long_sleeved_dress | 219-255 | 37 |
| vest_dress | 256-274 | 19 |
| sling_dress | 275-293 | 19 |

## Results

### shirt.jpg (long_sleeved_shirt):
```
Detected landmarks: 25 visible (from range 25-57)
Measurements:
  COLLAR_WIDTH: 303.4px (landmarks 27→31)
  SHOULDER_WIDTH: 1399.4px (landmarks 33→46)
  CHEST_WIDTH: 903.6px (landmarks 38→44)
  HEM_WIDTH: 723.5px (landmarks 41→43)
  LEFT_CUFF_WIDTH: 239.3px (landmarks 35→36)
  RIGHT_CUFF_WIDTH: 135.6px (landmarks 48→49)
  BODY_LENGTH: 835.0px (landmarks 28→42)
  LEFT_SLEEVE_LENGTH: 644.7px (landmarks 33→36)
  RIGHT_SLEEVE_LENGTH: 215.0px (landmarks 46→49)
```

### shirt2.jpg (long_sleeved_shirt):
```
Detected landmarks: 32 visible (from range 25-57)
Similar measurements with different values
```

### jeans.jpg (trousers):
```
Detected landmarks: 8 visible (from range 168-181)
Measurements:
  WAIST_WIDTH: 2004.9px (landmarks 170→174)
```

## Files Generated

For each processed image:

1. **`{name}_preprocessed.jpg`**
   - Background removed
   - Enhanced and cleaned

2. **`{name}_landmark_measurements.jpg`**
   - **All landmarks numbered** according to DeepFashion2 index
   - Green dots = high confidence
   - Orange dots = moderate confidence
   - Numbers positioned above-right of each landmark

3. **`{name}_measurements.json`**
   - Complete data including all 294 landmarks
   - Confidence scores
   - Precise measurements

## Benefits

✅ **Easy Verification**: See exactly which landmarks are detected  
✅ **Debugging**: Identify missing or misplaced landmarks  
✅ **Mapping**: Match visualization to landmark mapping definitions  
✅ **Understanding**: See the DeepFashion2 structure in action  
✅ **Quality Check**: Verify measurements use correct landmark pairs  

## Usage

Run the pipeline normally:

```bash
python landmark_measurement_system.py image.jpg \
    --output results \
    --no-classifier \
    --preprocess
```

The visualization will show numbered landmarks automatically!

## Results Location

**`numbered_landmarks/`** - Latest results with numbered landmarks:
- 9 files total (3 images × 3 files each)
- Each landmark clearly numbered
- Easy to identify specific measurement points

---

*Implementation Date: 2025-10-21*
*Status: Production Ready ✅*
