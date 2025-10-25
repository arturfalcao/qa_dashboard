# T-Shirt Dataset Collection - Status Report

## Summary

Successfully collected and prepared a t-shirt flat-lay image dataset for keypoint annotation and garment measurement extraction.

## Dataset Statistics

### Collection Results
- **Total images collected**: 104 t-shirt images
- **Source**: Uniqlo product images (verified flat-lay photography)
- **URLs processed**: 2,000 generated URLs
- **Success rate**: ~5.2% (typical for product code generation)

### Image Specifications
- **High resolution (2000x2000px)**: 93 images (89.4%)
- **Medium resolution (1000x1000px)**: 11 images (10.6%)
- **Total dataset size**: 27MB
- **Format**: JPG
- **Background**: White/clean backgrounds (product photography)

## Files Created

### Dataset Files
```
tshirt_dataset/
├── images/                          # 104 t-shirt images
│   ├── goods_*.jpg                  # Individual t-shirt images
├── annotations.json                 # COCO format annotations with keypoint schema
```

### Tools and Scripts
1. **scrape_ecommerce_flatlay.py** - Main collection script
   - Multi-threaded downloading
   - Quality filtering
   - COCO format export

2. **collect_tshirt_urls.py** - Initial URL generator
   - Generated 1,000 URLs from known t-shirt ranges

3. **generate_more_tshirt_urls.py** - Extended URL generator
   - Generated 2,000 URLs with expanded ranges
   - Covers multiple t-shirt categories (classic, graphic, women's, kids)

4. **preview_tshirt_dataset.py** - Visualization tool
   - Creates 4x4 grid preview of random samples
   - Output: `tshirt_dataset_preview.jpg`

5. **update_tshirt_schema.py** - Schema updater
   - Adds keypoint definitions to annotations

### Documentation
1. **TSHIRT_KEYPOINT_SCHEMA.md** - Complete annotation specification
   - 21 keypoint definitions
   - Annotation guidelines
   - Measurement derivations
   - Tool recommendations

2. **DATASET_COLLECTION_GUIDE.md** - Collection methodology
   - Multiple collection strategies
   - Troubleshooting guide

## Keypoint Schema

### Defined Keypoints (21 total)

#### Collar Region (4)
- collar_left, collar_right, collar_top, collar_bottom

#### Shoulder Region (4)
- shoulder_left_outer, shoulder_left_inner
- shoulder_right_inner, shoulder_right_outer

#### Sleeve Region (6)
- sleeve_left_top, sleeve_left_bottom, sleeve_left_end
- sleeve_right_top, sleeve_right_bottom, sleeve_right_end

#### Body Region (7)
- armpit_left, armpit_right
- waist_left, waist_right
- hem_left, hem_center, hem_right

### Measurements Enabled
From these keypoints, the following measurements can be extracted:
1. Shoulder width
2. Chest width
3. Body length
4. Sleeve length
5. Collar width
6. Hem width
7. Waist width
8. Armhole depth
9. Sleeve opening

## Annotation Format

The dataset uses **COCO keypoint format**:

```json
{
  "images": [...],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "keypoints": [x0, y0, v0, x1, y1, v1, ..., x20, y20, v20],
      "num_keypoints": 0,
      "bbox": [],
      "area": 0
    }
  ],
  "categories": [
    {
      "id": 1,
      "name": "tshirt",
      "keypoints": ["collar_left", "collar_right", ...],
      "skeleton": [[1, 2], [3, 4], ...]
    }
  ]
}
```

## Next Steps

### 1. Setup Annotation Tool

#### Option A: Labelme (Recommended for local work)
```bash
pip install labelme

# Start annotation
labelme tshirt_dataset/images \
  --labels tshirt \
  --config labelme_config.json
```

#### Option B: CVAT (Web-based, team collaboration)
1. Setup CVAT instance or use cvat.ai
2. Create project with "tshirt" category
3. Import keypoint schema
4. Upload images
5. Begin annotation

#### Option C: Label Studio (Versatile)
1. Install: `pip install label-studio`
2. Start: `label-studio`
3. Import dataset
4. Configure keypoint template
5. Annotate

### 2. Pilot Annotation (10-20 images)
- Annotate a small sample
- Validate keypoint schema works for all t-shirt styles
- Adjust schema if needed
- Establish annotation time per image

### 3. Full Annotation (Remaining ~90 images)
- Complete annotation of all 104 images
- Maintain consistency across annotations
- Perform quality checks

### 4. Quality Control
- Cross-validate annotations
- Check measurement ranges are reasonable
- Verify skeleton connections are correct
- Fix any errors or inconsistencies

### 5. Dataset Split
```python
# Recommended split
- Training: 75 images (72%)
- Validation: 15 images (14%)
- Testing: 14 images (14%)
```

### 6. Model Training
Options for keypoint detection:
1. **MMPose** (HRNet, ViTPose)
2. **Detectron2** (Keypoint R-CNN)
3. **OpenPose** (Custom training)
4. **MediaPipe** (Custom pose estimation)

### 7. Measurement Extraction Pipeline
Create system to:
1. Detect keypoints on new images
2. Calculate garment measurements
3. Account for pixel-to-real-world scaling (using reference)
4. Export measurements in standard format

## Collection Methodology

### URL Generation Strategy
Generated Uniqlo product URLs using known patterns:
```
https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{CODE}/item/goods_{COLOR}_{CODE}.jpg
```

**Product code ranges tested:**
- Classic t-shirts: 410000-475000
- Graphic tees (UT): 436000-469000
- Women's: 415000-455000
- Kids: 405000-415000

**Color codes tested:** 34 variations (00-69)

### Quality Filters Applied
- Only downloadable images (HTTP 200)
- Minimum size verification
- Valid image format (JPG)
- Clean product photography (white backgrounds)

## Technical Details

### Dependencies
```
requests>=2.31.0
Pillow>=10.0.0
ultralytics>=8.0.0
tqdm>=4.66.0
beautifulsoup4>=4.12.0
```

### Performance
- Concurrent downloads: 25 workers
- Average download time: ~2-3 seconds per valid image
- Total collection time: ~15-20 minutes for 2000 URLs

## Challenges Encountered

1. **DeepFashion2 unavailable** - Original dataset not on system
   - Solution: Pivoted to web scraping approach

2. **LAION-5B offline** - Public CLIP retrieval endpoint down
   - Solution: Direct e-commerce scraping

3. **Low URL success rate** (~3-5%)
   - Reason: Most generated product codes don't exist
   - Solution: Generated more URLs (2000) to get sufficient dataset

4. **Initial focus on "tops" not "t-shirts"**
   - User feedback: "mas eu quero t shirts"
   - Solution: Created t-shirt-specific URL generators

## Dataset Quality Assessment

### Strengths
- High resolution images (mostly 2000x2000px)
- Consistent flat-lay perspective
- Clean white backgrounds
- Professional product photography
- Diverse colors and styles
- Real-world product images

### Limitations
- All from single brand (Uniqlo)
- Limited style variety (mostly basic tees)
- No extreme angles or distortions
- May need more graphic tees
- No long-sleeve shirts included

### Potential Improvements
- Add images from other brands (H&M, Zara, etc.)
- Include more t-shirt styles (V-neck, henley, etc.)
- Add long-sleeve variants
- Include polo shirts
- Expand to 200-300 images for better model training

## Commands Reference

### Generate more URLs
```bash
python3 generate_more_tshirt_urls.py
```

### Collect images from URL list
```bash
python3 scrape_ecommerce_flatlay.py \
  --source url_list \
  --url_list comprehensive_tshirt_urls.txt \
  --out_dir ./tshirt_dataset \
  --max_images 2000 \
  --category_name "tshirt" \
  --num_workers 25
```

### Preview dataset
```bash
python3 preview_tshirt_dataset.py
```

### Update keypoint schema
```bash
python3 update_tshirt_schema.py
```

## Contact and Support

For questions about:
- **Annotation guidelines**: See `TSHIRT_KEYPOINT_SCHEMA.md`
- **Collection process**: See `DATASET_COLLECTION_GUIDE.md`
- **COCO format**: https://cocodataset.org/#format-data

## Timeline

- **Initial request**: Correct DeepFashion2 extraction script
- **Alternative exploration**: LAION-5B (offline)
- **Pivot to scraping**: Created e-commerce scraper
- **User feedback**: Focus on t-shirts specifically
- **URL generation**: 1,000 then 2,000 URLs
- **Collection**: 104 valid t-shirt images
- **Schema definition**: 21-keypoint annotation schema
- **Status**: ✅ **Ready for annotation**

---

**Last Updated**: 2025-10-16
**Dataset Version**: 1.0
**Status**: Collection Complete - Ready for Annotation
