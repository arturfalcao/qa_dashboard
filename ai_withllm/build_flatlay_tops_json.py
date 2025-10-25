#!/usr/bin/env python3
"""
Build a flat-lay tops dataset from brand websites.
Validates background, filters out model shots, de-duplicates.
"""

import argparse
import json
import re
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image
import numpy as np
from io import BytesIO

# Configuration
BRANDS = [
    {"domain": "arket.com", "name": "ARKET"},
    {"domain": "cosstores.com", "name": "COS"},
    {"domain": "uniqlo.com", "name": "UNIQLO"},
    {"domain": "muji.com", "name": "MUJI"},
    {"domain": "nudiejeans.com", "name": "Nudie"},
    {"domain": "everlane.com", "name": "Everlane"},
    {"domain": "mango.com", "name": "Mango"},
    {"domain": "hm.com", "name": "H&M"},
    {"domain": "zara.com", "name": "Zara"},
    {"domain": "weekday.com", "name": "Weekday"},
    {"domain": "stories.com", "name": "&OtherStories"},
]

# Category mappings
CATEGORY_PATTERNS = {
    "tshirt": [r"t-shirt", r"\btee\b", r"tshirt", r"t shirt"],
    "sweater": [r"sweater", r"knit", r"jumper", r"cardigan", r"pullover", r"knitwear"],
    "longsleeve": [r"long-sleeve", r"longsleeve", r"long sleeve", r"\bshirt\b", r"blouse"],
}

# Filter patterns
NO_PEOPLE_REJECT = [
    r"model", r"look", r"onbody", r"editorial", r"campaign",
    r"lifestyle", r"mannequin", r"worn", r"styled"
]

PREFER_FLAT = [
    r"flat", r"flatshot", r"still", r"packshot", r"descriptive",
    r"cutout", r"laydown", r"product", r"front"
]

MIN_RESOLUTION = 1200
WHITE_THRESHOLD = 245
WHITE_RATIO_MIN = 0.92
POLITENESS_DELAY = 1.0

class ImageValidator:
    """Validates images for background and content."""

    @staticmethod
    def check_background(img_bytes: bytes) -> Optional[str]:
        """
        Check if image has transparent or white background.

        Returns:
            "transparent" | "white" | None
        """
        try:
            img = Image.open(BytesIO(img_bytes))

            # Check for transparency
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Has alpha channel
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')

                alpha = np.array(img)[:, :, 3]
                # Check if significant transparency exists
                transparent_ratio = np.sum(alpha < 10) / alpha.size
                if transparent_ratio > 0.05:  # >5% transparent
                    return "transparent"

            # Check for white background
            if img.mode != 'RGB':
                img = img.convert('RGB')

            arr = np.array(img)
            white_pixels = np.all(arr >= WHITE_THRESHOLD, axis=2)
            white_ratio = np.sum(white_pixels) / white_pixels.size

            if white_ratio >= WHITE_RATIO_MIN:
                # Also check that there's some foreground (not all white)
                foreground_ratio = 1 - white_ratio
                if foreground_ratio >= 0.05:  # At least 5% foreground
                    return "white"

            return None

        except Exception as e:
            print(f"  ✗ Image validation error: {e}")
            return None

    @staticmethod
    def check_resolution(img_bytes: bytes) -> bool:
        """Check if image meets minimum resolution."""
        try:
            img = Image.open(BytesIO(img_bytes))
            long_side = max(img.size)
            return long_side >= MIN_RESOLUTION
        except:
            return False

    @staticmethod
    def check_no_people(url: str, alt_text: str = "") -> bool:
        """Heuristic check for model/lifestyle shots."""
        text = f"{url.lower()} {alt_text.lower()}"

        # Reject if contains people-related terms
        for pattern in NO_PEOPLE_REJECT:
            if re.search(pattern, text):
                return False

        # Prefer if contains flat-lay terms
        has_flat_term = any(re.search(p, text) for p in PREFER_FLAT)

        return True  # or return has_flat_term for stricter filtering


class DatasetBuilder:
    """Crawls brands and builds dataset."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.seen_hashes = set()
        self.results = []
        self.validator = ImageValidator()
        self.stats = {
            "tshirt": 0,
            "sweater": 0,
            "longsleeve": 0,
            "transparent": 0,
            "white": 0,
            "rejected_background": 0,
            "rejected_people": 0,
            "rejected_resolution": 0,
            "rejected_duplicate": 0,
        }

    def fetch_url(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """Fetch URL with error handling."""
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"  ✗ Fetch error: {e}")
        return None

    def compute_hash(self, page_url: str, img_url: str, img_bytes: bytes) -> str:
        """Compute unique hash for de-duplication."""
        h = hashlib.md5()
        h.update(page_url.encode())
        h.update(img_url.encode())
        h.update(str(len(img_bytes)).encode())
        return h.hexdigest()

    def classify_category(self, text: str) -> Optional[str]:
        """Classify product into category based on text."""
        text = text.lower()

        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return category

        return None

    def extract_images_from_product(self, product_url: str, brand: str, category: str) -> List[Dict]:
        """Extract valid images from a product page."""
        print(f"  Checking: {product_url}")

        response = self.fetch_url(product_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        candidates = []

        # Find all images (common selectors for product images)
        img_tags = soup.find_all('img', src=True)

        for img_tag in img_tags:
            img_url = img_tag.get('src', '')
            alt_text = img_tag.get('alt', '')

            # Make absolute URL
            img_url = urljoin(product_url, img_url)

            # Skip small thumbnails, icons, logos
            if any(x in img_url.lower() for x in ['thumb', 'icon', 'logo', 'nav', 'banner']):
                continue

            # Check no-people heuristic
            if not self.validator.check_no_people(img_url, alt_text):
                self.stats["rejected_people"] += 1
                continue

            # Download and validate
            time.sleep(0.2)  # Politeness
            img_response = self.fetch_url(img_url)
            if not img_response:
                continue

            img_bytes = img_response.content

            # De-duplication
            img_hash = self.compute_hash(product_url, img_url, img_bytes)
            if img_hash in self.seen_hashes:
                self.stats["rejected_duplicate"] += 1
                continue

            # Background check
            bg_type = self.validator.check_background(img_bytes)
            if not bg_type:
                self.stats["rejected_background"] += 1
                continue

            # Resolution check
            if not self.validator.check_resolution(img_bytes):
                self.stats["rejected_resolution"] += 1
                continue

            # Valid image found
            self.seen_hashes.add(img_hash)

            candidates.append({
                "brand": brand,
                "category": category,
                "page": product_url,
                "url": img_url,
                "background": bg_type
            })

            # Limit to 1-2 images per product (front view priority)
            if len(candidates) >= 1:
                break

        return candidates

    def crawl_brand_category(self, brand_info: Dict, category: str, target_count: int) -> int:
        """
        Crawl a brand for a specific category.
        Returns number of images found.
        """
        print(f"\n{'='*60}")
        print(f"Crawling {brand_info['name']} for {category}")
        print(f"{'='*60}")

        # Build category URL (this is simplified - real implementation would need brand-specific logic)
        base_url = f"https://{brand_info['domain']}"

        # Try common category URL patterns
        category_paths = self.get_category_paths(category)

        found = 0

        for path in category_paths:
            if found >= target_count:
                break

            category_url = urljoin(base_url, path)
            print(f"\nTrying: {category_url}")

            response = self.fetch_url(category_url)
            if not response:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find product links (common patterns)
            product_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                href_full = urljoin(category_url, href)

                # Filter for product pages
                if any(x in href.lower() for x in ['product', 'item', '/p/', '/i/']):
                    if self.classify_category(href) == category:
                        product_links.append(href_full)

            # De-duplicate product links
            product_links = list(set(product_links))[:20]  # Limit per category page

            print(f"Found {len(product_links)} potential products")

            for product_url in product_links:
                if found >= target_count:
                    break

                images = self.extract_images_from_product(
                    product_url,
                    brand_info['name'],
                    category
                )

                for img in images:
                    if found >= target_count:
                        break

                    self.results.append(img)
                    self.stats[category] += 1
                    self.stats[img["background"]] += 1
                    found += 1
                    print(f"  ✓ Added {category} image #{found} ({img['background']})")

                time.sleep(POLITENESS_DELAY)

        return found

    def get_category_paths(self, category: str) -> List[str]:
        """Get common URL paths for category."""
        paths = {
            "tshirt": [
                "/men/t-shirts", "/women/t-shirts", "/tshirts",
                "/clothing/t-shirts", "/tops/t-shirts"
            ],
            "sweater": [
                "/men/sweaters", "/women/knitwear", "/sweaters",
                "/clothing/knitwear", "/tops/sweaters"
            ],
            "longsleeve": [
                "/men/shirts", "/women/shirts", "/shirts",
                "/clothing/shirts", "/tops/shirts"
            ]
        }
        return paths.get(category, [])

    def build_dataset(self, tshirt_count: int, sweater_count: int, longsleeve_count: int) -> List[Dict]:
        """Build complete dataset."""
        targets = {
            "tshirt": tshirt_count,
            "sweater": sweater_count,
            "longsleeve": longsleeve_count
        }

        for category, target in targets.items():
            for brand_info in BRANDS:
                if self.stats[category] >= target:
                    break

                remaining = target - self.stats[category]
                self.crawl_brand_category(brand_info, category, remaining)

        return self.results

    def print_stats(self):
        """Print final statistics."""
        print(f"\n{'='*60}")
        print("FINAL STATISTICS")
        print(f"{'='*60}")
        print(f"Total images collected: {len(self.results)}")
        print(f"\nBy category:")
        print(f"  T-shirts: {self.stats['tshirt']}")
        print(f"  Sweaters: {self.stats['sweater']}")
        print(f"  Long-sleeve: {self.stats['longsleeve']}")
        print(f"\nBy background:")
        total_bg = self.stats['transparent'] + self.stats['white']
        if total_bg > 0:
            print(f"  Transparent: {self.stats['transparent']} ({100*self.stats['transparent']/total_bg:.1f}%)")
            print(f"  White: {self.stats['white']} ({100*self.stats['white']/total_bg:.1f}%)")
        print(f"\nRejections:")
        print(f"  Background: {self.stats['rejected_background']}")
        print(f"  People/model: {self.stats['rejected_people']}")
        print(f"  Resolution: {self.stats['rejected_resolution']}")
        print(f"  Duplicate: {self.stats['rejected_duplicate']}")


def main():
    parser = argparse.ArgumentParser(
        description='Build flat-lay tops dataset from brand websites'
    )
    parser.add_argument('--out', default='flatlay_tops_dataset.json',
                       help='Output JSON file')
    parser.add_argument('--tee', type=int, default=100,
                       help='Number of t-shirts')
    parser.add_argument('--sweater', type=int, default=100,
                       help='Number of sweaters')
    parser.add_argument('--longsleeve', type=int, default=100,
                       help='Number of long-sleeve tops')

    args = parser.parse_args()

    print("Building flat-lay tops dataset...")
    print(f"Target: {args.tee} t-shirts, {args.sweater} sweaters, {args.longsleeve} long-sleeve")

    builder = DatasetBuilder()

    try:
        results = builder.build_dataset(args.tee, args.sweater, args.longsleeve)

        # Save JSON
        output_path = Path(args.out)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✓ Saved to: {output_path}")
        builder.print_stats()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving partial results...")
        output_path = Path(args.out)
        with open(output_path, 'w') as f:
            json.dump(builder.results, f, indent=2)
        print(f"✓ Partial results saved to: {output_path}")
        builder.print_stats()


if __name__ == '__main__':
    main()
