# Landmark Filtering Fix - Category-Based Visualization

## Problem

Landmarks were appearing **outside the garment boundaries** because:

1. The HRNet model outputs predictions for **all 294 keypoints** across 13 different garment categories
2. The visualization was showing **all high-confidence landmarks**, regardless of detected category
3. For example, jeans (category: "trousers") was showing:
   - Only 8 landmarks from the correct "trousers" range (indices 168-182)
   - Plus 68 landmarks from irrelevant categories (shirts, dresses, etc.)
   - These irrelevant landmarks were detecting features on the **background**!

## Root Cause

The DeepFashion2 model structure has 294 keypoints divided into 13 garment categories:

| Category | Index Range | # Keypoints |
|----------|------------|-------------|
| short_sleeved_shirt | 0-25 | 25 |
| long_sleeved_shirt | 25-58 | 33 |
| short_sleeved_outwear | 58-89 | 31 |
| long_sleeved_outwear | 89-128 | 39 |
| vest | 128-143 | 15 |
| sling | 143-158 | 15 |
| shorts | 158-168 | 10 |
| **trousers** | **168-182** | **14** |
| skirt | 182-190 | 8 |
| short_sleeved_dress | 190-219 | 29 |
| long_sleeved_dress | 219-256 | 37 |
| vest_dress | 256-275 | 19 |
| sling_dress | 275-294 | 19 |

**The visualization was showing landmarks from ALL categories, not just the detected one!**

## Solution

Updated both visualization methods to **filter landmarks by category range**:

### 1. `landmark_measurement_system.py` (lines 360-420)

```python
def _create_measurement_visualization(self, image: np.ndarray,
                                     detection: Dict,
                                     measurements: Dict) -> np.ndarray:
    """Create visualization showing only category-appropriate landmarks"""

    # Define valid landmark index ranges for each category
    category_ranges = {
        'short_sleeved_shirt': (0, 25),
        'long_sleeved_shirt': (25, 58),
        # ... all 13 categories
        'trousers': (168, 182),
        'sling_dress': (275, 294)
    }

    # Get valid range for detected category
    start_idx, end_idx = category_ranges[category]

    # Draw ONLY landmarks within the category range
    for idx, (landmark, conf) in enumerate(zip(landmarks, confidences)):
        if start_idx <= idx < end_idx and landmark is not None and conf > 0.7:
            # Draw landmark
            cv2.circle(vis, landmark, radius, color, -1)
```

### 2. `sviplab_hrnet_integration.py` (lines 445-545)

Applied the same category-based filtering to the core detector's `visualize_landmarks()` method.

## Results

### Before Fix
- **Jeans**: Showed 76 landmarks (68 from wrong categories on background!)
- **Shirt**: Showed landmarks from dress/pants categories on background
- **Shirt2**: Same issue - irrelevant landmarks everywhere

### After Fix
- **Jeans**: Shows only 8 landmarks from trousers range (168-182) ✓
- **Shirt**: Shows only 21 landmarks from long_sleeved_shirt range (25-58) ✓
- **Shirt2**: Shows only 23 landmarks from long_sleeved_shirt range (25-58) ✓

**All landmarks now stay within garment boundaries!**

## Files Modified

1. **`landmark_measurement_system.py`** (lines 360-420)
   - Updated `_create_measurement_visualization()` method

2. **`sviplab_hrnet_integration.py`** (lines 445-545)
   - Updated `visualize_landmarks()` method
   - Added `confidence_threshold` parameter

## Usage

### Measurement System
```bash
python landmark_measurement_system.py shirt.jpg --output results --no-classifier
```

### Core Detector
```bash
python sviplab_hrnet_integration.py --image jeans.jpg --output results
```

Both will now show **only category-appropriate landmarks**!

## Technical Details

### Why This Happened

The HRNet model is trained on **all 13 garment categories simultaneously**. During inference:

1. Model outputs 294 heatmaps (one per keypoint)
2. Each heatmap can have high-confidence peaks, even for irrelevant categories
3. Background textures/wrinkles can trigger false positives in wrong category ranges
4. Without filtering, ALL high-confidence peaks are shown

### The Fix

Filter visualization by:
1. **Category detection** - Determine garment type (already working)
2. **Index range mapping** - Map category to its keypoint index range
3. **Range filtering** - Show ONLY landmarks within the valid range
4. **Confidence threshold** - Apply confidence filter on top (>0.7 or >0.3)

## Testing

Tested on 3 images:
- `shirt.jpg` → long_sleeved_shirt → Shows 21/33 landmarks ✓
- `shirt2.jpg` → long_sleeved_shirt → Shows 23/33 landmarks ✓
- `jeans.jpg` → trousers → Shows 8/14 landmarks ✓

**No landmarks appearing outside garments!**

## Next Steps

This fix is now integrated into the pipeline. Any code using these visualization methods will automatically benefit from category-based filtering.

If you create new visualization code, remember to:
1. Get the detected category from `detection['category']`
2. Map category to index range using the `category_ranges` dict
3. Filter landmarks: `if start_idx <= idx < end_idx`
4. Apply confidence threshold as needed

---

**Generated**: 2025-10-20
**Fix Applied To**: landmark_measurement_system.py, sviplab_hrnet_integration.py
