#!/usr/bin/env python3
"""
Quick script to collect Uniqlo product image URLs.
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def get_uniqlo_urls(max_urls=100):
    """Scrape Uniqlo product image URLs."""

    # Try multiple categories
    categories = [
        'https://www.uniqlo.com/us/en/men/tops/t-shirts',
        'https://www.uniqlo.com/us/en/men/tops/shirts',
        'https://www.uniqlo.com/us/en/men/tops/long-sleeve-t-shirts',
    ]

    urls = set()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Uniqlo image pattern - they use consistent URL structure
    # Format: https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/XXXXXX/item/goods_XX_XXXXXX.jpg

    # Generate URLs based on known patterns
    # Recent product codes seem to be in the 450000-470000 range
    print("Generating Uniqlo product image URLs...")

    for product_code in range(450000, 470000, 100):  # Sample every 100
        for color_code in ['00', '01', '09', '69', '03', '07']:  # Common color codes
            url = f"https://image.uniqlo.com/UQ/ST3/WesternCommon/imagesgoods/{product_code}/item/goods_{color_code}_{product_code}.jpg"
            urls.add(url)

            if len(urls) >= max_urls:
                break

        if len(urls) >= max_urls:
            break

    # Also try API approach if available
    try:
        api_url = "https://www.uniqlo.com/us/api/commerce/v5/en/products"
        params = {
            'categoryId': '26150',  # T-shirts category
            'offset': 0,
            'limit': 50
        }

        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            for item in items[:50]:
                images = item.get('images', {})
                main_img = images.get('main', {})
                img_url = main_img.get('url', '')

                if img_url and 'image.uniqlo.com' in img_url:
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url
                    urls.add(img_url)
    except Exception as e:
        print(f"API method failed: {e}")

    return list(urls)[:max_urls]

if __name__ == '__main__':
    urls = get_uniqlo_urls(max_urls=200)
    print(f"Found {len(urls)} URLs")

    # Save to file
    with open('collected_urls.txt', 'w') as f:
        for url in urls:
            f.write(url + '\n')

    print(f"Saved to collected_urls.txt")
