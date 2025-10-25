#!/usr/bin/env python3
"""
Collect specifically T-SHIRT URLs from Uniqlo.
"""

import requests
import json

def get_tshirt_urls_from_api():
    """Try to get t-shirt URLs from Uniqlo API."""
    urls = set()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Uniqlo API endpoints for different regions
    api_endpoints = [
        # US API
        {
            'url': 'https://www.uniqlo.com/us/api/commerce/v5/en/products',
            'params': {
                'categoryId': '26150',  # Men's T-shirts
                'offset': 0,
                'limit': 100
            }
        },
        {
            'url': 'https://www.uniqlo.com/us/api/commerce/v5/en/products',
            'params': {
                'categoryId': '26199',  # Men's graphic T-shirts
                'offset': 0,
                'limit': 100
            }
        },
        # Women's T-shirts
        {
            'url': 'https://www.uniqlo.com/us/api/commerce/v5/en/products',
            'params': {
                'categoryId': '25226',  # Women's T-shirts
                'offset': 0,
                'limit': 100
            }
        }
    ]

    for endpoint in api_endpoints:
        try:
            print(f"Trying API: {endpoint['params'].get('categoryId')}...")
            response = requests.get(
                endpoint['url'],
                params=endpoint['params'],
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Extract product info
                if 'result' in data and 'items' in data['result']:
                    items = data['result']['items']
                elif 'items' in data:
                    items = data['items']
                else:
                    print(f"  No items found in response")
                    continue

                print(f"  Found {len(items)} products")

                for item in items:
                    # Get product code
                    product_code = item.get('productId') or item.get('code')

                    if not product_code:
                        continue

                    # Get images
                    images = item.get('images', {})

                    # Main image
                    if 'main' in images:
                        main_img = images['main'].get('url', '')
                        if main_img:
                            if not main_img.startswith('http'):
                                main_img = 'https:' + main_img
                            urls.add(main_img)

                    # Try chip images (color variations)
                    if 'chip' in images:
                        chip_imgs = images.get('chip', [])
                        if isinstance(chip_imgs, list):
                            for chip in chip_imgs:
                                if isinstance(chip, dict):
                                    img_url = chip.get('url', '')
                                    if img_url:
                                        if not img_url.startswith('http'):
                                            img_url = 'https:' + img_url
                                        urls.add(img_url)

                    # Also generate standard product image URLs
                    # Format: https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{CODE}/item/goods_{COLOR}_{CODE}.jpg
                    for color in ['00', '01', '03', '04', '05', '06', '07', '08', '09', '69']:
                        img_url = f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{product_code}/item/goods_{color}_{product_code}.jpg"
                        urls.add(img_url)

        except Exception as e:
            print(f"  API call failed: {e}")
            continue

    return list(urls)

def generate_tshirt_product_codes():
    """Generate product codes that are likely to be t-shirts based on Uniqlo patterns."""
    urls = set()

    # Known Uniqlo t-shirt product code ranges (based on their numbering system)
    # T-shirts typically fall in these ranges
    tshirt_ranges = [
        (422000, 424000),  # Classic t-shirts
        (425000, 429000),  # Graphic tees
        (437000, 439000),  # UT collection
        (440000, 445000),  # Seasonal tees
        (450000, 455000),  # Recent releases
        (455000, 460000),  # Current season
        (460000, 465000),  # New arrivals
    ]

    colors = ['00', '01', '03', '04', '05', '06', '07', '08', '09',
              '30', '31', '32', '33', '34', '35', '56', '57', '58', '69']

    for start, end in tshirt_ranges:
        for code in range(start, end, 100):  # Sample every 100
            for color in colors:
                url = f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{code}/item/goods_{color}_{code}.jpg"
                urls.add(url)

    return list(urls)

def main():
    print("=" * 60)
    print("COLLECTING T-SHIRT URLs FROM UNIQLO")
    print("=" * 60)

    all_urls = set()

    # Method 1: Try API
    print("\n[1/2] Trying Uniqlo API...")
    api_urls = get_tshirt_urls_from_api()
    all_urls.update(api_urls)
    print(f"  → Got {len(api_urls)} URLs from API")

    # Method 2: Generate from known patterns
    print("\n[2/2] Generating from t-shirt product ranges...")
    generated_urls = generate_tshirt_product_codes()
    all_urls.update(generated_urls)
    print(f"  → Generated {len(generated_urls)} URLs")

    # Save
    final_urls = list(all_urls)[:1000]  # Limit to 1000

    with open('tshirt_urls.txt', 'w') as f:
        for url in final_urls:
            f.write(url + '\n')

    print("\n" + "=" * 60)
    print(f"✓ SAVED {len(final_urls)} T-SHIRT URLs to tshirt_urls.txt")
    print("=" * 60)

if __name__ == '__main__':
    main()
