# Quick Start: Annotating T-Shirt Keypoints

## Prerequisites

Install labelme:
```bash
pip install labelme
```

Or for other tools, see `TSHIRT_KEYPOINT_SCHEMA.md`.

## Option 1: Labelme (Recommended)

### Start annotation session:
```bash
labelme tshirt_dataset/images --config labelme_tshirt_config.yaml
```

### Annotation workflow:
1. **Load image** - Labelme will open the first image
2. **Create Points** - Right-click → "Create Point" or press keyboard shortcut
3. **Add keypoint** - Click on the location, select keypoint name from dropdown
4. **Repeat for all 21 keypoints** - Follow the schema order
5. **Save** - Labelme creates a JSON file per image
6. **Next image** - Press 'D' key or click Next

### Keypoint annotation order:
Follow this order for consistency:

**Step 1: Collar (4 points)**
1. collar_left
2. collar_right
3. collar_top
4. collar_bottom

**Step 2: Shoulders (4 points)**
5. shoulder_left_outer
6. shoulder_left_inner
7. shoulder_right_inner
8. shoulder_right_outer

**Step 3: Sleeves (6 points)**
9. sleeve_left_top
10. sleeve_left_bottom
11. sleeve_left_end
12. sleeve_right_top
13. sleeve_right_bottom
14. sleeve_right_end

**Step 4: Body (7 points)**
15. armpit_left
16. armpit_right
17. waist_left
18. waist_right
19. hem_left
20. hem_center
21. hem_right

### After annotation:

Convert labelme JSON files to COCO format:
```bash
labelme2coco tshirt_dataset/images --output tshirt_dataset/annotations_completed.json
```

## Option 2: CVAT (Web-based)

### Setup:
1. Go to https://cvat.ai or setup local instance
2. Create new project: "T-shirt Keypoint Annotation"
3. Add task with 104 images
4. Configure skeleton:
   - Import keypoint schema from `TSHIRT_KEYPOINT_SCHEMA.md`
   - Add all 21 keypoints
   - Define skeleton connections

### Annotation:
1. Open task
2. Select "Skeleton" tool
3. Click to place keypoints
4. Use skeleton connections as visual guide
5. Save and move to next frame

### Export:
1. Click "Actions" → "Export task dataset"
2. Select "COCO Keypoints 1.0" format
3. Download annotations

## Option 3: Manual JSON Editing

If you prefer to manually edit the COCO JSON:

```python
# Example annotation structure
{
  "id": 1,
  "image_id": 1,
  "category_id": 1,
  "keypoints": [
    x0, y0, 2,  # collar_left (visible)
    x1, y1, 2,  # collar_right (visible)
    # ... all 21 keypoints
    x20, y20, 2  # hem_right (visible)
  ],
  "num_keypoints": 21,
  "bbox": [x, y, width, height],
  "area": width * height
}
```

Visibility values:
- 0 = not labeled
- 1 = labeled but occluded
- 2 = labeled and visible

## Tips for Fast Annotation

1. **Use keyboard shortcuts** - Learn your tool's shortcuts
2. **Zoom in** - Ensure precision at seam intersections
3. **Follow a pattern** - Always annotate in same order
4. **Take breaks** - Maintain quality with fresh eyes
5. **Batch similar images** - Annotate similar styles together

## Estimated Time

- **Setup**: 10-15 minutes
- **Per image**: 3-5 minutes (after practice)
- **Total for 104 images**: 5-9 hours

## Quality Checks

After every 10-20 annotations, verify:
- ✅ All visible keypoints are marked
- ✅ Coordinates are at exact seam/edge locations
- ✅ Left/right symmetry looks correct
- ✅ No keypoints are misplaced

## Validation Script

Create a simple validation script:
```python
import json
from pathlib import Path

with open('tshirt_dataset/annotations.json') as f:
    data = json.load(f)

for ann in data['annotations']:
    kps = ann['keypoints']
    num_visible = sum(1 for i in range(2, len(kps), 3) if kps[i] == 2)
    print(f"Image {ann['image_id']}: {num_visible}/21 keypoints visible")
```

## Common Issues

### Issue: Can't see keypoint names in labelme
**Solution**: Make sure you're using the config file:
```bash
labelme tshirt_dataset/images --config labelme_tshirt_config.yaml
```

### Issue: Too many keypoints to manage
**Solution**: Annotate in sections:
1. First pass: Collar + Shoulders
2. Second pass: Sleeves
3. Third pass: Body + Hem

### Issue: Unsure where to place keypoint
**Solution**: Refer to `TSHIRT_KEYPOINT_SCHEMA.md` for detailed guidelines and examples

## Sample Annotation Session

```bash
# 1. Start labelme
labelme tshirt_dataset/images --config labelme_tshirt_config.yaml

# 2. Annotate 10-20 images as pilot

# 3. Convert to COCO format
labelme2coco tshirt_dataset/images --output pilot_annotations.json

# 4. Validate
python validate_annotations.py pilot_annotations.json

# 5. Continue with remaining images

# 6. Final conversion
labelme2coco tshirt_dataset/images --output tshirt_dataset/annotations_final.json
```

## Next Steps After Annotation

1. **Merge annotations** - Combine with existing COCO file if needed
2. **Split dataset** - Create train/val/test splits
3. **Train model** - Use MMPose, Detectron2, or similar
4. **Validate model** - Test on held-out images
5. **Deploy** - Create measurement extraction pipeline

## Resources

- **Schema reference**: `TSHIRT_KEYPOINT_SCHEMA.md`
- **Dataset status**: `TSHIRT_DATASET_STATUS.md`
- **COCO format**: https://cocodataset.org/#format-data
- **Labelme docs**: https://github.com/wkentaro/labelme
- **CVAT docs**: https://opencv.github.io/cvat/docs/

---

**Ready to start?** Run:
```bash
labelme tshirt_dataset/images --config labelme_tshirt_config.yaml
```
