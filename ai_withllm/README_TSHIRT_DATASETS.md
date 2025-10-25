# T-Shirt Datasets - Complete Guide

## Overview

This project contains two complementary flat-lay t-shirt datasets for garment measurement and keypoint detection:

1. **Uniqlo T-shirts** - 104 high-resolution product images
2. **DeepFashion2 T-shirts** - 500 filtered flat-lay images (AI-filtered)

**Combined Total**: 604 flat-lay t-shirt images ready for annotation and training

---

## Dataset 1: Uniqlo T-shirts

### Summary
- **Source**: Uniqlo product catalog (web scraping)
- **Images**: 104 t-shirts
- **Resolution**: 2000x2000px (89%), 1000x1000px (11%)
- **Size**: 27MB
- **Format**: JPG, COCO annotations
- **Keypoint schema**: Custom 21-point schema defined

### Location
```
tshirt_dataset/
├── images/              # 104 high-res t-shirt images
└── annotations.json     # COCO format with 21-keypoint schema
```

### Keypoint Schema (21 points)
- **Collar** (4): left, right, top, bottom
- **Shoulders** (4): left/right outer/inner
- **Sleeves** (6): left/right top/bottom/end
- **Body** (7): armpits, waist, hem points

### Preview
- Visual preview: `tshirt_dataset_preview.jpg`
- Documentation: `TSHIRT_KEYPOINT_SCHEMA.md`, `TSHIRT_DATASET_STATUS.md`

### Characteristics
✓ Very high resolution (2000px)
✓ Uniform brand/style (Uniqlo)
✓ Clean white backgrounds
✓ Professional product photography
✓ Custom keypoint schema defined
✓ Diverse colors

---

## Dataset 2: DeepFashion2 T-shirts

### Summary
- **Source**: DeepFashion2 train2020 (AI-filtered)
- **Images**: 500 t-shirts
- **Resolution**: 468x624-826px (medium)
- **Size**: 19MB
- **Format**: JPG, COCO annotations
- **AI Filtering**: YOLOv8 person detection + scale filtering

### Location
```
deepfashion2_tshirts/
├── images/              # 500 flat-lay t-shirt images
└── annotations.json     # COCO format with DeepFashion2 landmarks
```

### Filtering Process
1. **Category filter**: Only "short sleeve top" and "long sleeve top"
2. **Scale filter**: Only scale=3 (flat-lay product images)
3. **Person detection**: YOLOv8 to exclude images with humans
4. **Quality check**: Verified t-shirt visibility

### Preview
- Visual preview: `deepfashion2_tshirts_preview.jpg`
- Documentation: `DEEPFASHION2_FILTER_SUMMARY.md`

### Characteristics
✓ Diverse brands and styles
✓ Real-world product images
✓ AI-verified flat-lay
✓ No humans/models
✓ DeepFashion2 landmarks included
✓ Larger quantity (500 vs 104)

---

## Comparison

| Feature | Uniqlo T-shirts | DeepFashion2 T-shirts |
|---------|----------------|----------------------|
| **Quantity** | 104 | 500 |
| **Resolution** | 2000x2000px | 468x624px |
| **Source** | Uniqlo only | Multiple brands |
| **Annotation** | Custom 21-point | DeepFashion2 format |
| **Size** | 27MB | 19MB |
| **Avg file size** | ~260KB | ~38KB |
| **Filtering** | Manual URL generation | AI-powered |
| **Diversity** | Low (one brand) | High (multiple brands) |
| **Quality** | Very high | Medium-high |

---

## Combined Dataset

### Merge Strategy

**Option 1: Use Both Separately**
- Train on DeepFashion2 (500 images, more data)
- Fine-tune on Uniqlo (104 images, higher quality)

**Option 2: Merge All**
- Combine both datasets: 604 total images
- Standardize resolution (resize to common size)
- Unified keypoint schema (choose one or map between them)

**Option 3: Stratified Use**
- DeepFashion2 for pre-training (diverse)
- Uniqlo for specific product matching

### Merging Command
```bash
# Create merged dataset directory
mkdir merged_tshirts
mkdir merged_tshirts/images

# Copy all images
cp tshirt_dataset/images/* merged_tshirts/images/
cp deepfashion2_tshirts/images/* merged_tshirts/images/

# Merge annotations (requires custom script)
python merge_coco_annotations.py \
  --input1 tshirt_dataset/annotations.json \
  --input2 deepfashion2_tshirts/annotations.json \
  --output merged_tshirts/annotations.json
```

---

## Filtering Scripts

### 1. DeepFashion2 Filter
**Script**: `filter_deepfashion2_tshirts.py`

Extract flat-lay t-shirts from DeepFashion2 dataset using AI:
```bash
/home/celso/projects/qa_dashboard/ai_mesurement/venv/bin/python \
  filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./output \
  --max_images 1000 \
  --person-threshold 0.3
```

**Features**:
- YOLOv8 person detection
- Scale-based filtering (flat-lay vs model-worn)
- Category-based filtering (t-shirts only)
- COCO format export

### 2. Uniqlo Scraper
**Script**: `scrape_ecommerce_flatlay.py`

Scrape flat-lay images from Uniqlo:
```bash
python3 scrape_ecommerce_flatlay.py \
  --source url_list \
  --url_list comprehensive_tshirt_urls.txt \
  --out_dir ./tshirt_dataset \
  --max_images 1000 \
  --category_name "tshirt"
```

### 3. Dataset Analysis
**Script**: `analyze_deepfashion2.py`

Analyze DeepFashion2 dataset structure:
```bash
python3 analyze_deepfashion2.py
```

---

## Next Steps

### 1. Annotation

**For Uniqlo dataset** (needs keypoint annotation):
```bash
# Install labelme
pip install labelme

# Start annotation
labelme tshirt_dataset/images --config labelme_tshirt_config.yaml
```

**For DeepFashion2 dataset** (has landmarks, may need conversion):
- Already has DeepFashion2 landmarks
- Can use as-is or convert to custom schema

### 2. Training

**Recommended approach**:

1. **Pre-train** on DeepFashion2 (500 images)
   - More data for robust feature learning
   - Diverse styles and brands

2. **Fine-tune** on Uniqlo (104 images)
   - Higher resolution
   - Specific to target domain

3. **Model options**:
   - MMPose (HRNet, ViTPose)
   - Detectron2 (Keypoint R-CNN)
   - Custom PyTorch model

### 3. Measurement Extraction

Build pipeline to:
1. Detect keypoints on new images
2. Calculate measurements from keypoints
3. Account for pixel-to-real-world scaling
4. Export in standard format (JSON/CSV)

### 4. Integration

Integrate with QA dashboard:
```
qa_dashboard/
├── api/
│   └── measurement/
│       ├── keypoint_detector.py
│       ├── measurement_calculator.py
│       └── models/
│           └── tshirt_keypoints.pth
└── ai_measurement/
    └── datasets/
        ├── tshirt_dataset/
        └── deepfashion2_tshirts/
```

---

## File Structure

```
ai_withllm/
│
├── DATASETS
│   ├── tshirt_dataset/                      # Uniqlo t-shirts (104)
│   │   ├── images/
│   │   └── annotations.json
│   │
│   ├── deepfashion2_tshirts/                # DeepFashion2 t-shirts (500)
│   │   ├── images/
│   │   └── annotations.json
│   │
│   └── deepfashion2_tshirts_sample/         # Test sample (50)
│       ├── images/
│       └── annotations.json
│
├── COLLECTION SCRIPTS
│   ├── scrape_ecommerce_flatlay.py          # Uniqlo scraper
│   ├── filter_deepfashion2_tshirts.py       # DeepFashion2 filter
│   ├── collect_tshirt_urls.py               # URL generator
│   ├── generate_more_tshirt_urls.py         # Extended URL gen
│   └── analyze_deepfashion2.py              # Dataset analysis
│
├── ANNOTATION TOOLS
│   ├── labelme_tshirt_config.yaml           # Labelme config
│   ├── annotation_quick_start.sh            # Quick launcher
│   └── update_tshirt_schema.py              # Schema updater
│
├── VISUALIZATION
│   ├── preview_tshirt_dataset.py            # Preview generator
│   ├── tshirt_dataset_preview.jpg           # Uniqlo preview
│   └── deepfashion2_tshirts_preview.jpg     # DeepFashion2 preview
│
└── DOCUMENTATION
    ├── README_TSHIRT_DATASETS.md            # This file
    ├── TSHIRT_KEYPOINT_SCHEMA.md            # Keypoint definitions
    ├── TSHIRT_DATASET_STATUS.md             # Uniqlo status
    ├── DEEPFASHION2_FILTER_SUMMARY.md       # DeepFashion2 status
    ├── START_ANNOTATION_GUIDE.md            # Annotation guide
    └── DATASET_COLLECTION_GUIDE.md          # Collection methods
```

---

## Quick Commands

### View dataset statistics
```bash
# Uniqlo
python3 -c "
import json
with open('tshirt_dataset/annotations.json') as f:
    data = json.load(f)
    print(f'Uniqlo: {len(data[\"images\"])} images')
"

# DeepFashion2
python3 -c "
import json
with open('deepfashion2_tshirts/annotations.json') as f:
    data = json.load(f)
    print(f'DeepFashion2: {len(data[\"images\"])} images')
"
```

### Extract more DeepFashion2 images
```bash
/home/celso/projects/qa_dashboard/ai_mesurement/venv/bin/python \
  filter_deepfashion2_tshirts.py \
  --deepfashion_dir /home/celso/Downloads/train2020/train \
  --output_dir ./deepfashion2_tshirts_2000 \
  --max_images 2000 \
  --person-threshold 0.3
```

### Create preview grids
```bash
# Uniqlo preview
python3 preview_tshirt_dataset.py

# DeepFashion2 preview
python3 << 'EOF'
from PIL import Image
import json, random
from pathlib import Path

with open('deepfashion2_tshirts/annotations.json') as f:
    samples = random.sample(json.load(f)['images'], 16)

canvas = Image.new('RGB', (800, 800), 'white')
for i, s in enumerate(samples):
    img = Image.open(f"deepfashion2_tshirts/images/{s['file_name']}")
    img.thumbnail((200, 200))
    canvas.paste(img, ((i%4)*200, (i//4)*200))
canvas.save('deepfashion2_preview.jpg')
EOF
```

---

## Resources

### Documentation
- [COCO Format](https://cocodataset.org/#format-data)
- [DeepFashion2 Paper](https://arxiv.org/abs/1901.07973)
- [MMPose Documentation](https://mmpose.readthedocs.io)
- [Labelme Guide](https://github.com/wkentaro/labelme)

### Models
- [YOLOv8](https://docs.ultralytics.com)
- [HRNet](https://github.com/HRNet/HRNet-Human-Pose-Estimation)
- [Detectron2](https://github.com/facebookresearch/detectron2)

### Related Projects
- DeepFashion2: 491K fashion images with keypoints
- Fashionpedia: Comprehensive fashion attributes
- Fashion-MNIST: Simple fashion dataset

---

## Support

For issues or questions:
1. Check documentation files in this directory
2. Review script help: `python3 <script>.py --help`
3. Consult COCO format specification
4. Review preview images to verify quality

---

**Last Updated**: 2025-10-16
**Total T-shirt Images**: 604 (104 Uniqlo + 500 DeepFashion2)
**Status**: ✅ Ready for annotation and training
