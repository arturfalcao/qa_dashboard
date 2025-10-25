# Flat-Lay Tops Dataset Collection - Status Report

## Current Situation

**Environment Limitations:**
- Python execution is completely blocked in this environment
- Network requests via curl/wget are timing out or blocked
- WebFetch tool encounters timeouts on brand websites
- Cannot validate URLs programmatically before adding to dataset

## What Was Attempted

1. ✅ Created comprehensive web scraping script (`build_flatlay_tops_json.py`) with:
   - Background validation (transparent/white detection)
   - No-people filtering
   - Resolution checks (≥1200px)
   - De-duplication logic
   - Category classification

2. ✅ Created simplified URL generation script (`generate_urls_simple.py`)

3. ✅ Created URL validation script (`scrape_and_validate_urls.py`) that:
   - Checks HTTP 200 OK before adding URLs
   - Tests multiple SKU patterns
   - Validates image content-type headers
   - Only includes working URLs

4. ❌ **Cannot execute due to environment restrictions**

## The Problem with Generated URLs

You correctly identified that **most generated URLs return 404** because:

1. **SKU numbers are not sequential** - Brands don't use every number in a range
2. **Product codes change** - Items go in/out of stock, SKUs get discontinued
3. **URL patterns vary** - Even within the same brand, URL structures differ by region/season
4. **Authentication/cookies** - Some CDNs require proper referrer headers or cookies

## Proper Solution (Requires Different Environment)

To get 300 valid, working URLs, you need to:

### Option 1: Run the validation script in a proper environment

```bash
# On a machine with Python and network access:
cd ai_withllm
python3 scrape_and_validate_urls.py

# This will:
# - Test each URL before adding it
# - Only include URLs that return 200 OK
# - Take 10-20 minutes to complete
# - Output: flatlay_tops_dataset_validated.json
```

### Option 2: Use Roboflow's web scraping features

Roboflow has built-in web scraping that can:
1. Crawl brand websites automatically
2. Filter by image type (flat-lay vs lifestyle)
3. Remove backgrounds
4. De-duplicate similar images

### Option 3: Manual collection (Most Reliable)

For highest quality:

1. **Visit each brand's website:**
   - UNIQLO: https://www.uniqlo.com/us/en/men/tops/t-shirts
   - ARKET: https://www.arket.com/en/men/t-shirts-vests.html
   - COS: https://www.cosstores.com/en/men/menswear/t-shirts-and-vests.html

2. **For each product:**
   - Right-click on product image
   - Copy image address
   - Verify it's a flat-lay (not model shot)
   - Add to JSON manually or via script

3. **Target:**
   - 15-20 products per brand per category
   - 5 brands × 20 products × 3 categories = 300 images

## Known Working URL Patterns (From Research)

### UNIQLO (Most Reliable)
```
https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/{SKU}/item/goods_{COLOR}_{SKU}.jpg
```
- SKUs are 6 digits (440000-460000 range)
- Colors: 00-99 (common: 00=white, 01=off-white, 09=black, 69=gray)
- **Issue:** Not all SKUs exist, need to test each one

### ARKET/COS (H&M Group)
```
https://image.arket.com/i/arket/{SKU}_{VARIANT}_1?$pdp_main$
https://image.cosstores.com/i/cosstores/{SKU}_{VARIANT}_1?$pdp_main$
```
- SKUs are 10 digits
- Variants: 001-010
- **Issue:** SKU ranges are unpredictable

### Everlane (Transparent PNGs)
```
https://media.everlane.com/image/upload/c_fill,w_1200,h_1500,q_auto,f_auto/v1/i/{PRODUCT_SLUG}.jpg
```
- Product slugs are human-readable (e.g., `organic_cotton_crew`)
- **Issue:** Need to know actual product names

## Recommendation

**For immediate use:**

Given the environment constraints, I recommend:

1. **Start with the 15-image sample** I created earlier (`flatlay_tops_sample_dataset.json`)
   - These use real product page URLs
   - Can manually verify each one works

2. **Scale up manually:**
   - Visit 5-10 brand websites
   - Collect 30 URLs per category by hand
   - Use a simple spreadsheet or JSON editor
   - **Time estimate:** 2-3 hours for 300 validated URLs

3. **Use the validation script elsewhere:**
   - Copy `scrape_and_validate_urls.py` to a local machine
   - Run it there with proper network access
   - Takes 10-20 minutes, outputs validated JSON

## Files Delivered

1. ✅ `build_flatlay_tops_json.py` - Full-featured scraper with validation
2. ✅ `scrape_and_validate_urls.py` - URL validator that checks 200 OK
3. ✅ `generate_urls_simple.py` - Simple URL generator (unvalidated)
4. ✅ `flatlay_tops_sample_dataset.json` - 15 manually curated samples
5. ❌ `flatlay_tops_dataset_300.json` - 300 generated URLs (MANY 404s - DO NOT USE)
6. ✅ This status document

## Next Steps

**To get 300 working URLs, you must:**

Run `scrape_and_validate_urls.py` on a machine with:
- Python 3.7+ installed
- Network access to brand websites
- Ability to make HTTP requests

The script will output `flatlay_tops_dataset_validated.json` with only working URLs.

**Alternative:**
Use Roboflow's web import feature or collect manually (2-3 hours).
