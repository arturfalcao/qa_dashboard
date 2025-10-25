# Flat-Lay Garment Dataset Collection Guide

## Available Tools

You now have **3 different scripts** for collecting flat-lay garment images:

### 1. `collect_flatlay_from_laion.py` - LAION-5B Query (Currently Offline)
**Status:** ❌ `knn.laion.ai` is currently offline

Queries the LAION-5B dataset using CLIP semantic search.

```bash
python collect_flatlay_from_laion.py \
  --use_default_queries \
  --max_images 1000 \
  --out_dir ./laion_dataset \
  --person_filter \
  --min_bg_white 0.5 \
  --aesthetic_min 5.5
```

**Pros:**
- Massive dataset (5 billion images)
- High-quality semantic search
- Built-in aesthetic/NSFW filtering

**Cons:**
- Public endpoint frequently offline
- Requires internet connection
- Unpredictable availability

---

### 2. `scrape_ecommerce_flatlay.py` - E-commerce Scraper ✅ **WORKING**
**Status:** ✅ Working and tested

Scrapes product images from e-commerce websites or custom URL lists.

#### Option A: URL List (Recommended)
```bash
python scrape_ecommerce_flatlay.py \
  --source url_list \
  --url_list my_urls.txt \
  --out_dir ./ecommerce_dataset \
  --max_images 500 \
  --person_filter \
  --min_bg_white 0.4
```

**Create `my_urls.txt`:**
```text
https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/422990/item/goods_09_422990.jpg
https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/455359/item/goods_00_455359.jpg
# Add more URLs, one per line
```

#### Option B: Scrape Uniqlo
```bash
python scrape_ecommerce_flatlay.py \
  --source uniqlo \
  --category t-shirts \
  --out_dir ./uniqlo_dataset \
  --max_images 200
```

**Note:** Uniqlo uses React SPA, so scraping may be limited. URL list method is more reliable.

#### Option C: Custom Webpage
```bash
python scrape_ecommerce_flatlay.py \
  --source custom \
  --custom_url "https://www.example-store.com/mens-tshirts" \
  --out_dir ./custom_dataset \
  --max_images 100
```

**Pros:**
- Reliable and under your control
- High-quality product photos
- No external API dependencies
- Works offline once URLs are collected

**Cons:**
- Requires manual URL collection
- May need to update selectors if sites change
- Smaller scale than LAION

---

### 3. `build_flatlay_tops_from_df2.py` - DeepFashion2 Extractor
**Status:** ⏳ Requires DeepFashion2 dataset download

Extracts flat-lay tops from the DeepFashion2 dataset.

```bash
python build_flatlay_tops_from_df2.py \
  --df2_root /path/to/DeepFashion2 \
  --split train \
  --out_dir ./df2_flatlay \
  --min_bg_white 0.70 \
  --person_filter true \
  --max_items 1000
```

**Get DeepFashion2:**
```bash
# Visit: https://github.com/switchablenorms/DeepFashion2
# Follow their download instructions
```

**Pros:**
- High-quality annotated dataset
- Research-grade quality
- Includes fashion-specific categories

**Cons:**
- Large download (>100GB)
- Requires significant storage
- Setup time required

---

## Recommended Workflow

### For Quick Start (Today):
1. **Use the e-commerce scraper with URL list:**
   ```bash
   # 1. Create URL list with 100-500 URLs from:
   #    - Uniqlo product pages
   #    - H&M product pages
   #    - Your own product database

   # 2. Run scraper
   python scrape_ecommerce_flatlay.py \
     --source url_list \
     --url_list my_urls.txt \
     --out_dir ./dataset \
     --max_images 500 \
     --person_filter

   # 3. Review images in ./dataset/images/
   # 4. Import ./dataset/annotations.json into annotation tool
   ```

### For Maximum Scale:
1. **Download DeepFashion2** (if you have storage)
2. **Run DF2 extractor** to get 1000s of flat-lay images
3. **Supplement with e-commerce scraper** for specific styles
4. **Wait for LAION to come back online** for additional diversity

---

## Output Format

All scripts generate **COCO-compatible annotations**:

```
output_dir/
├── images/
│   ├── image_001.jpg
│   ├── image_002.jpg
│   └── ...
└── annotations.json  # COCO format
```

**`annotations.json` structure:**
```json
{
  "images": [
    {
      "id": 1,
      "file_name": "image.jpg",
      "width": 2000,
      "height": 2000,
      "source_url": "https://...",
      "source": "uniqlo"
    }
  ],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "bbox": [],
      "keypoints": [],  # Fill during annotation
      "num_keypoints": 0
    }
  ],
  "categories": [
    {
      "id": 1,
      "name": "garment",
      "keypoints": [],  # Define your measurement points
      "skeleton": []
    }
  ]
}
```

---

## Filtering Options

All scripts support quality filters:

### Person Filter
Remove images with people/mannequins:
```bash
--person_filter  # Enables YOLO-based person detection
```

### Background Filter
Require white/clean backgrounds:
```bash
--min_bg_white 0.5  # 0.0 = any background, 1.0 = pure white
```

**Recommended values:**
- **0.3-0.4**: Allows light colored backgrounds
- **0.5-0.6**: Mostly white backgrounds
- **0.7+**: Very strict, pure white only

---

## Next Steps After Collection

### 1. Review Images
```bash
# Check what was downloaded
ls -lh dataset/images/
```

### 2. Define Keypoints Schema

Edit `annotations.json` categories to define measurement points:
```json
{
  "categories": [{
    "id": 1,
    "name": "garment",
    "keypoints": [
      "left_shoulder",
      "right_shoulder",
      "left_armpit",
      "right_armpit",
      "left_cuff",
      "right_cuff",
      "left_hem",
      "right_hem",
      "collar_left",
      "collar_right"
    ],
    "skeleton": [
      [0, 1],  // shoulders connected
      [0, 2],  // shoulder to armpit
      // ... define connections
    ]
  }]
}
```

### 3. Import to Annotation Tool

**Roboflow:**
```bash
# Upload annotations.json as COCO format
# Start annotating keypoints
```

**Label Studio:**
```bash
# Import COCO JSON
# Configure keypoint labeling interface
# Start annotation
```

### 4. Train Model

Once you have annotated 100-500 images:
- Train keypoint detection model (HRNet, MMPose, etc.)
- Use for automated measurement extraction

---

## Troubleshooting

### "No images downloaded"
- Check internet connection
- Verify URLs are valid
- Try reducing `--max_images` for testing

### "Person filter not working"
```bash
# Install ultralytics
pip install ultralytics
```

### "Background filter too strict"
```bash
# Lower threshold
--min_bg_white 0.3
```

### LAION still offline?
- Use e-commerce scraper instead
- Check status: https://github.com/rom1504/clip-retrieval/issues
- Use local CLIP retrieval (advanced)

---

## Example: Complete Workflow

```bash
# 1. Collect 200 images from Uniqlo URLs
python scrape_ecommerce_flatlay.py \
  --source url_list \
  --url_list uniqlo_urls.txt \
  --out_dir ./my_dataset \
  --max_images 200 \
  --person_filter \
  --min_bg_white 0.4

# 2. Verify results
ls my_dataset/images/
cat my_dataset/annotations.json | jq '.images | length'

# 3. Edit keypoints schema
nano my_dataset/annotations.json
# (Add your keypoint names to categories[0].keypoints)

# 4. Import to annotation tool
# Upload my_dataset/annotations.json to Roboflow/Label Studio

# 5. Start annotating!
```

---

## Contact & Support

- Scripts location: `/home/celso/projects/qa_dashboard/ai_withllm/`
- Test data: `./ecommerce_test/` (2 sample images)
- Example URLs: `./example_urls.txt`

**Need more URLs?**
- Browse Uniqlo/H&M product pages
- Right-click images → "Copy image address"
- Add to your `urls.txt` file

**Questions?**
Check the script help:
```bash
python scrape_ecommerce_flatlay.py --help
python build_flatlay_tops_from_df2.py --help
python collect_flatlay_from_laion.py --help
```
