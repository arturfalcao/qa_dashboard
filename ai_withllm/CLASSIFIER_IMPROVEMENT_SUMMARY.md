# Garment Classification Improvement Summary

## Problem Identified

The landmark detection system (HRNet with DeepFashion2) was misclassifying garment categories:
- **shirt.jpg** → classified as "vest" (should be "long_sleeved_shirt")
- **shirt2.jpg** → classified as "vest" (should be "long_sleeved_shirt")
- **jeans.jpg** → classified as "shorts" (should be "trousers")

## Root Cause

The issue is in `sviplab_hrnet_integration.py` line 338-371, in the `_infer_category()` method:

```python
ranges = {
    'short_sleeved_shirt': (0, 25),
    'long_sleeved_shirt': (25, 58),
    'short_sleeved_outwear': (58, 89),
    'long_sleeved_outwear': (89, 128),
    'vest': (128, 143),  # INCORRECT RANGE
    # ... other categories
}
```

These keypoint index ranges are **arbitrary and incorrect**. They don't match the actual DeepFashion2 dataset structure.

## Solutions Attempted

### Attempt 1: Separate Garment Classifier ✓ Partially Successful

Created `garment_classifier.py` with three classification methods:
1. **YOLO-based** - requires YOLOv8 training
2. **ResNet-based** - requires custom training
3. **Rule-based** - uses heuristics (aspect ratio, sleeve detection, inseam detection)

**Results:**
- Rule-based classifier works for simple cases
- Successfully corrected "vest" → "long_sleeved_shirt" for shirt2.jpg initially
- BUT: Too fragile for flatlay images with complex backgrounds
- Aspect ratio calculation depends on accurate garment segmentation
- Inseam detection gives false positives on button plackets

### Attempt 2: Improve Feature Detection ⚠️ Challenges

Improved several detection methods:
- `_get_garment_bbox()` - now uses Otsu thresholding + contour detection
- `_detect_inseam()` - checks bottom 2/3 only, requires wider gap
- `_detect_sleeves()` - analyzes edge regions
- `_measure_top_opening()` - distinguishes dresses from pants

**Challenges:**
- Flatlay images are hard to segment automatically
- Background removal in preprocessing helps but isn't perfect
- Orientation matters (horizontal vs vertical flatlay)

## Recommended Solution

**Fix the landmark-based category inference** by using the correct DeepFashion2 keypoint mappings.

### Action Items

1. **Get the official DeepFashion2 keypoint schema**
   - Download from: https://github.com/switchablenorms/DeepFashion2
   - Reference Figure 2 in the paper
   - Each category has specific keypoint indices

2. **Update `_infer_category()` in `sviplab_hrnet_integration.py`**
   - Replace arbitrary ranges with correct DeepFashion2 mappings
   - Use category-specific keypoint patterns
   - Example: shirts have neckline, shoulder, sleeve, and hem keypoints in specific indices

3. **Alternative: Use the existing keypoint schema we created**
   - We already analyzed the detected keypoints and created `keypoint_schema_mapping.json`
   - This shows which keypoint indices appear in which spatial regions
   - Could use this to improve category inference

### Implementation Example

```python
def _infer_category_improved(self, landmarks, confidences):
    """Improved category inference using keypoint patterns"""

    # Count high-confidence keypoints in each category's key indices
    category_scores = {}

    # Shirts typically have:
    # - Neckline keypoints (indices 0-5)
    # - Shoulder keypoints (indices 6-7, 31-32)
    # - Sleeve keypoints (indices 8-14)
    # - Hem keypoints (indices 13-16)

    shirt_indices = [0,1,2,3,4,5,6,7,31,32,8,9,10,13,14,15,16]
    shirt_score = sum(1 for i in shirt_indices
                     if i < len(confidences) and confidences[i] > 0.5)

    # Trousers typically have:
    # - Waistband keypoints (indices 168-171)
    # - Crotch keypoint (index 172)
    # - Hem keypoints (indices 177-181)
    # - Knee keypoints (indices 173-176)

    trousers_indices = [168,169,170,171,172,173,174,175,176,177,178,179,180,181]
    trousers_score = sum(1 for i in trousers_indices
                        if i < len(confidences) and confidences[i] > 0.5)

    # ... etc for other categories

    # Return category with highest score
    if trousers_score > shirt_score and trousers_score > 5:
        return 'trousers'
    elif shirt_score > 8:
        # Check sleeve length to distinguish short vs long
        # ...
        return 'long_sleeved_shirt' or 'short_sleeved_shirt'
    # ... etc
```

## Current Status

### What Works ✓
- **Keypoint detection**: 294 landmarks detected with 70.17% mAP
- **Keypoint mapping**: Comprehensive schema created showing which indices map to which garment parts
- **Measurement extraction**: Accurate pixel measurements for collar, shoulder, chest, hem widths and lengths
- **Preprocessing pipeline**: Background removal, denoising, contrast enhancement
- **Garment classifier framework**: Built and tested, ready for improvements

### What Needs Work ⚠️
- **Category classification accuracy**: Still misclassifying garment types
- **Rule-based classifier robustness**: Too fragile for production use
- **Need correct DeepFashion2 keypoint mappings**: Currently using guesses

## Files Created

1. **garment_classifier.py** - Standalone garment classification module
2. **landmark_measurement_system.py** - Updated to integrate classifier
3. **KEYPOINT_MEASUREMENT_GUIDE.md** - Complete keypoint reference
4. **keypoint_schema_mapping.json** - Spatial region mapping
5. **debug_classifier.py** - Debug tool for classifier features

## Next Steps

**Priority 1: Fix landmark-based category inference**
- Reference official DeepFashion2 schema
- Update `_infer_category()` with correct keypoint ranges
- Test on all three images

**Priority 2: Train custom classifier (optional)**
- Collect labeled dataset of flatlay images
- Fine-tune YOLOv8 or ResNet50 for garment classification
- Use as separate pre-classification step

**Priority 3: Improve rule-based classifier (fallback)**
- Better segmentation for aspect ratio calculation
- More robust feature detection
- Handle different orientations and image types

## Test Results

### Current System Performance

**With original landmark-based inference:**
- shirt.jpg: vest ❌ (should be long_sleeved_shirt)
- shirt2.jpg: vest ❌ (should be long_sleeved_shirt)
- jeans.jpg: shorts ❌ (should be trousers)

**With classifier (v1 - has bugs):**
- shirt.jpg: trousers ❌ (classifier false positive on inseam)
- shirt2.jpg: skirt ❌ (bbox detection error)
- jeans.jpg: long_sleeved_dress ❌ (aspect ratio + sleeve detection confusion)

**Target performance:**
- shirt.jpg: long_sleeved_shirt ✓
- shirt2.jpg: long_sleeved_shirt ✓
- jeans.jpg: trousers ✓

## Conclusion

The best path forward is to **fix the landmark-based category inference** using the correct DeepFashion2 keypoint mappings, rather than relying on a fragile rule-based classifier. The separate classifier can be improved later with proper training data.

The keypoint detection and measurement extraction are working excellently - we just need to correctly interpret which category those keypoints belong to.
