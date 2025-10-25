#!/usr/bin/env python3
"""
Scrape and validate flat-lay garment images from brand websites.
Only includes URLs that return 200 OK with valid images.
"""

import json
import time
import sys

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "requests"])
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

def create_session():
    """Create a session with retries and proper headers."""
    session = requests.Session()

    # Retry strategy
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Headers to avoid being blocked
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })

    return session

def check_url(session, url, timeout=10):
    """Check if URL returns a valid image (200 OK)."""
    try:
        response = session.head(url, timeout=timeout, allow_redirects=True)

        # Check status code
        if response.status_code == 200:
            # Check content type if available
            content_type = response.headers.get('content-type', '').lower()
            if 'image' in content_type or content_type == '':
                return True

        # Try GET if HEAD fails (some servers block HEAD)
        if response.status_code == 405 or response.status_code == 403:
            response = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'image' in content_type:
                    return True

        return False
    except Exception as e:
        print(f"    ✗ Error checking {url}: {e}")
        return False

def scrape_uniqlo_products(session, category, needed_count):
    """Scrape UNIQLO product images (they have predictable URL patterns)."""
    results = []

    # UNIQLO SKU ranges by category
    sku_ranges = {
        'tshirt': range(447541, 447700),      # T-shirts
        'sweater': range(441234, 441400),     # Knitwear
        'longsleeve': range(451359, 451500)   # Shirts
    }

    colors = ['09', '01', '69', '05', '62', '00', '08', '11', '32', '68']

    print(f"\n  Trying UNIQLO {category}...")

    for sku in sku_ranges.get(category, []):
        if len(results) >= needed_count:
            break

        for color in colors:
            if len(results) >= needed_count:
                break

            url = f"https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/{sku}/item/goods_{color}_{sku}.jpg"

            if check_url(session, url):
                results.append({
                    "brand": "UNIQLO",
                    "category": category,
                    "page": f"https://www.uniqlo.com/us/en/products/E{sku}-000",
                    "url": url,
                    "background": "white"
                })
                print(f"    ✓ Found: {url}")
                break  # One image per SKU

            time.sleep(0.1)  # Rate limiting

    return results

def scrape_arket_cos_products(session, brand_domain, brand_name, category, needed_count):
    """Scrape ARKET/COS products (H&M Group brands with similar patterns)."""
    results = []

    # SKU ranges by brand and category
    sku_bases = {
        'ARKET': {
            'tshirt': 1187830000,
            'sweater': 1074422000,
            'longsleeve': 979876000
        },
        'COS': {
            'tshirt': 1146622000,
            'sweater': 875422000,
            'longsleeve': 923456000
        }
    }

    base_sku = sku_bases.get(brand_name, {}).get(category)
    if not base_sku:
        return results

    print(f"\n  Trying {brand_name} {category}...")

    # Try sequential SKUs
    for i in range(200):  # Try up to 200 SKUs
        if len(results) >= needed_count:
            break

        sku = f"{base_sku + i:010d}"

        # Try different variant codes
        for variant in ['001', '002', '003', '004', '005']:
            if len(results) >= needed_count:
                break

            url = f"https://image.{brand_domain}.com/i/{brand_domain.split('.')[0]}/{sku}_{variant}_1?$pdp_main$"

            if check_url(session, url):
                results.append({
                    "brand": brand_name,
                    "category": category,
                    "page": f"https://www.{brand_domain}.com/en/men/product.{sku}.html",
                    "url": url,
                    "background": "white"
                })
                print(f"    ✓ Found: {url}")
                break

            time.sleep(0.1)

    return results

def main():
    print("="*60)
    print("SCRAPING & VALIDATING FLAT-LAY GARMENT URLS")
    print("="*60)
    print("\nThis will take several minutes as we validate each URL...")
    print("Only including images that return 200 OK\n")

    session = create_session()
    dataset = []

    categories = ['tshirt', 'sweater', 'longsleeve']
    target_per_category = 100

    for category in categories:
        print(f"\n{'='*60}")
        print(f"CATEGORY: {category.upper()} (target: {target_per_category})")
        print(f"{'='*60}")

        category_results = []

        # Try UNIQLO first (most reliable URL patterns)
        uniqlo_results = scrape_uniqlo_products(session, category, 40)
        category_results.extend(uniqlo_results)
        print(f"  UNIQLO: Found {len(uniqlo_results)} valid URLs")

        # Try ARKET
        if len(category_results) < target_per_category:
            needed = target_per_category - len(category_results)
            arket_results = scrape_arket_cos_products(session, 'arket.com', 'ARKET', category, min(needed, 30))
            category_results.extend(arket_results)
            print(f"  ARKET: Found {len(arket_results)} valid URLs")

        # Try COS
        if len(category_results) < target_per_category:
            needed = target_per_category - len(category_results)
            cos_results = scrape_arket_cos_products(session, 'cosstores.com', 'COS', category, min(needed, 30))
            category_results.extend(cos_results)
            print(f"  COS: Found {len(cos_results)} valid URLs")

        dataset.extend(category_results)

        print(f"\n  Total for {category}: {len(category_results)} / {target_per_category}")

    # Save results
    output_file = 'flatlay_tops_dataset_validated.json'
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)

    # Print statistics
    print(f"\n{'='*60}")
    print("FINAL STATISTICS")
    print(f"{'='*60}")
    print(f"Total images collected: {len(dataset)}")

    by_category = {}
    by_brand = {}
    by_bg = {}

    for item in dataset:
        by_category[item['category']] = by_category.get(item['category'], 0) + 1
        by_brand[item['brand']] = by_brand.get(item['brand'], 0) + 1
        by_bg[item['background']] = by_bg.get(item['background'], 0) + 1

    print(f"\nBy category:")
    for cat in ['tshirt', 'sweater', 'longsleeve']:
        count = by_category.get(cat, 0)
        print(f"  {cat}: {count}")

    print(f"\nBy brand:")
    for brand, count in sorted(by_brand.items()):
        print(f"  {brand}: {count}")

    print(f"\nBy background:")
    for bg, count in by_bg.items():
        pct = 100 * count / len(dataset) if len(dataset) > 0 else 0
        print(f"  {bg}: {count} ({pct:.1f}%)")

    print(f"\n✓ Saved to: {output_file}")
    print(f"\nAll {len(dataset)} URLs have been validated and return 200 OK!")

if __name__ == '__main__':
    main()
