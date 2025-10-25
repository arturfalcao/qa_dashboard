# DeepFashion2 T-Shirt Filtering - Summary

## Overview

Successfully filtered the DeepFashion2 dataset to extract flat-lay t-shirt images without humans using AI-powered detection.

## Results

### Dataset Statistics
- **Source**: DeepFashion2 train2020 dataset
- **Total annotations processed**: 14,425
- **T-shirt items found**: 7,659 (short sleeve top + long sleeve top)
- **Flat-lay t-shirts (scale=3)**: 2,309
- **Passed person detection**: 500
- **Final images exported**: 500

### Filtering Criteria

1. **Category Filter**:
   - `short sleeve top` (t-shirts)
   - `long sleeve top` (long-sleeve t-shirts)

2. **Flat-lay Filter**:
   - Only `scale=3` images (flat-lay/product photography)
   - Excluded `scale=1` and `scale=2` (model-worn)

3. **Person Detection**:
   - Used YOLOv8 nano model
   - Confidence threshold: 0.3
   - Excluded any image with detected person

## Output

### Files Created
```
deepfashion2_tshirts/
├── images/                    # 500 flat-lay t-shirt images
│   ├── 000010.jpg            # Long sleeve tops
│   ├── 000042.jpg            # Short sleeve tops
│   └── ...
└── annotations.json           # COCO format annotations
```

### Dataset Characteristics
- **Total images**: 500
- **Image sizes**: Mostly 468x624-826px
- **Total size**: 19MB
- **Format**: JPG
- **Annotation format**: COCO
- **Categories**:
  - `short sleeve top` - majority
  - `long sleeve top` - minority

## Script Usage

### Basic Usage
```bash
python3 filter_deepfashion2_tshirts.py \
  --deepfashion_dir /path/to/deepfashion2/train \
  --output_dir ./output \
  --max_images 500
```

### Options
```
--deepfashion_dir     Path to DeepFashion2 train folder (contains image/ and annos/)
--output_dir          Output directory for filtered images
--max_images          Maximum number of images to extract
--no-person-detection Disable YOLO person detection (faster but less accurate)
--all-scales          Include all scales, not just flat-lay (scale=3)
--person-threshold    Confidence threshold for person detection (default: 0.5)
```

### Examples

**Extract 1000 t-shirts with strict person filtering:**
```bash
python3 filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./tshirts_strict \
  --max_images 1000 \
  --person-threshold 0.2
```

**Extract all scale images (not just flat-lay):**
```bash
python3 filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./tshirts_all_scales \
  --all-scales \
  --max_images 1000
```

**Fast extraction without person detection:**
```bash
python3 filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./tshirts_fast \
  --no-person-detection \
  --max_images 1000
```

## Technical Details

### Person Detection
- **Model**: YOLOv8n (nano - fastest)
- **Detection class**: Person (class 0 in COCO)
- **Threshold**: Configurable (default 0.5, used 0.3 in this run)
- **Purpose**: Ensure flat-lay images without models/humans

### DeepFashion2 Scale Values
Based on analysis of 1000 samples:
- **Scale 1**: 21.3% - Close-up/model shots
- **Scale 2**: 50.2% - Medium/model shots
- **Scale 3**: 28.5% - Flat-lay/product shots ✅

For t-shirts specifically:
- **Scale 1**: 22.1%
- **Scale 2**: 38.4%
- **Scale 3**: 39.5% ✅ (selected for filtering)

### Category Distribution (in 1000 samples)
- short sleeve top: 375 (most common t-shirt type)
- long sleeve top: 207
- trousers: 327
- shorts: 152
- vest dress: 130
- (other categories...)

## COCO Format Annotations

The exported annotations follow COCO keypoint format:

```json
{
  "images": [
    {
      "id": 1,
      "file_name": "000010.jpg",
      "width": 468,
      "height": 624,
      "source": "deepfashion2",
      "category": "long sleeve top",
      "scale": 3,
      "viewpoint": 2,
      "zoom_in": 1
    }
  ],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "bbox": [x, y, width, height],
      "area": area,
      "keypoints": [...],
      "num_keypoints": N
    }
  ],
  "categories": [
    {
      "id": 1,
      "name": "tshirt",
      "supercategory": "clothing"
    }
  ]
}
```

## Comparison with Uniqlo Dataset

### DeepFashion2 T-shirts (this dataset)
- **Quantity**: 500 images
- **Resolution**: 468x624-826px (medium)
- **Source**: DeepFashion2 (diverse brands/styles)
- **Annotation**: COCO format with DeepFashion2 landmarks
- **Size**: 19MB

### Uniqlo T-shirts (previous collection)
- **Quantity**: 104 images
- **Resolution**: 2000x2000px (high)
- **Source**: Uniqlo only (uniform style)
- **Annotation**: COCO format with custom 21-keypoint schema
- **Size**: 27MB

### Combined Dataset Potential
By merging both datasets:
- **Total**: 604 high-quality flat-lay t-shirt images
- **Diversity**: Multiple brands + Uniqlo
- **Resolution**: Mixed (can standardize)
- **Use case**: More robust model training

## Next Steps

### 1. Merge Datasets (Optional)
Combine DeepFashion2 and Uniqlo t-shirt datasets:
```bash
# Copy Uniqlo images to DeepFashion2 output
cp tshirt_dataset/images/* deepfashion2_tshirts/images/

# Merge annotations (requires custom script)
python merge_annotations.py \
  --source1 tshirt_dataset/annotations.json \
  --source2 deepfashion2_tshirts/annotations.json \
  --output merged_tshirts/annotations.json
```

### 2. Annotation
- DeepFashion2 images already have landmarks (DeepFashion2 format)
- Can convert to custom 21-keypoint schema
- Or train with DeepFashion2 landmarks directly

### 3. Training
Options for keypoint detection:
- **MMPose** with HRNet backbone
- **Detectron2** Keypoint R-CNN
- **Custom models** using DeepFashion2 as base

### 4. Extract More Images
The script processed only 14,425/191,961 annotations to get 500 images.
To extract more:
```bash
# Extract 2000 images
python3 filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./deepfashion2_tshirts_large \
  --max_images 2000
```

### 5. Quality Check
Manually review a sample to ensure:
- All images are truly flat-lay
- No persons/models detected
- T-shirts are clearly visible
- Annotations are accurate

## Files Reference

### Scripts
- `filter_deepfashion2_tshirts.py` - Main filtering script
- `analyze_deepfashion2.py` - Dataset analysis script

### Outputs
- `deepfashion2_tshirts/` - Filtered dataset (500 images)
- `deepfashion2_tshirts_sample/` - Test run (50 images)
- `DEEPFASHION2_FILTER_SUMMARY.md` - This document

### Dependencies
```
ultralytics>=8.0.0    # YOLOv8 for person detection
Pillow>=10.0.0        # Image processing
```

## Performance

### Processing Speed
- **With person detection**: ~30-50 annotations/sec
- **Without person detection**: ~100-150 annotations/sec
- **Total time for 500 images**: ~5-8 minutes (with YOLO)

### Success Rate
- From 14,425 annotations processed:
  - 53% were t-shirt items (7,659)
  - 30% of t-shirts were flat-lay (2,309)
  - 22% passed person detection (500 final)

## Troubleshooting

### Issue: YOLO model download slow
**Solution**: Pre-download YOLOv8n model:
```python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # Downloads once
```

### Issue: Out of memory
**Solution**: Process in batches with `--max_images`:
```bash
# Batch 1
python3 filter_deepfashion2_tshirts.py --max_images 500 --output_dir batch1

# Batch 2 (modify script to skip first 14425 annotations)
python3 filter_deepfashion2_tshirts.py --max_images 500 --output_dir batch2
```

### Issue: Too few flat-lay images
**Solution**: Use `--all-scales` to include all images:
```bash
python3 filter_deepfashion2_tshirts.py --all-scales --max_images 1000
```

## References

- **DeepFashion2 Paper**: [Link](https://arxiv.org/abs/1901.07973)
- **DeepFashion2 Dataset**: Contains 491K images with annotations
- **COCO Format**: [https://cocodataset.org](https://cocodataset.org)
- **YOLOv8**: [Ultralytics](https://docs.ultralytics.com)

---

**Created**: 2025-10-16
**Dataset Version**: 1.0
**Status**: ✅ Complete - 500 images filtered and ready for use
