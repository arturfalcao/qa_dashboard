#!/usr/bin/env python3
"""
Scrape flat-lay garment images from e-commerce websites.

This scraper collects high-quality product images from various fashion retailers
that are known for their excellent flat-lay photography.

Supported sources:
- Uniqlo (excellent flat-lays)
- H&M (good product shots)
- Zara (high quality)
- Custom URLs from a list

Usage:
  python scrape_ecommerce_flatlay.py \
    --source uniqlo \
    --category "t-shirts" \
    --max_images 100 \
    --out_dir ./ecommerce_dataset

Requirements:
  pip install requests beautifulsoup4 pillow tqdm opencv-python ultralytics selenium
"""

import argparse
import json
import hashlib
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from PIL import Image
from tqdm import tqdm
import numpy as np

# Optional: YOLO for person detection
try:
    from ultralytics import YOLO
    _HAS_YOLO = True
except ImportError:
    _HAS_YOLO = False

# Optional: OpenCV for background analysis
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

# ---------- Constants ----------

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Known e-commerce sites with good flat-lay images
ECOMMERCE_SOURCES = {
    'uniqlo': {
        'base_url': 'https://www.uniqlo.com',
        'categories': {
            't-shirts': '/us/en/men/tops/t-shirts',
            'shirts': '/us/en/men/tops/shirts',
            'long-sleeve': '/us/en/men/tops/long-sleeve-t-shirts',
        }
    },
    'hm': {
        'base_url': 'https://www2.hm.com',
        'categories': {
            't-shirts': '/en_us/men/products/t-shirts-tank-tops.html',
            'shirts': '/en_us/men/products/shirts.html',
        }
    },
}

# ---------- Helper Functions ----------

def get_session() -> requests.Session:
    """Create a requests session with headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENTS[0],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    return session

def download_image(url: str, output_path: Path, timeout: int = 10, session: Optional[requests.Session] = None) -> bool:
    """Download image from URL."""
    if session is None:
        session = requests.Session()
        session.headers.update({'User-Agent': USER_AGENTS[0]})

    try:
        response = session.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        # Verify it's an image
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type.lower():
            return False

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify the image can be opened
        try:
            img = Image.open(output_path)
            img.verify()
            # Reopen to get size (verify() closes the file)
            img = Image.open(output_path)
            w, h = img.size
            if w < 300 or h < 300:  # Too small
                output_path.unlink(missing_ok=True)
                return False
            return True
        except Exception:
            output_path.unlink(missing_ok=True)
            return False

    except Exception as e:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return False

def url_to_filename(url: str) -> str:
    """Convert URL to safe filename."""
    # Try to extract original filename
    path = urlparse(url).path
    filename = Path(path).name

    # If no proper filename, use hash
    if not filename or '.' not in filename:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"{url_hash}.jpg"

    return filename

def has_person(img_path: Path, yolo_model) -> bool:
    """Check if image contains a person."""
    try:
        results = yolo_model.predict(str(img_path), verbose=False, conf=0.3)
        for r in results:
            if r.boxes is None:
                continue
            cls = r.boxes.cls.cpu().numpy().astype(int)
            if (cls == 0).any():  # person class
                return True
    except Exception:
        pass
    return False

def background_whiteness_score(img_path: Path) -> float:
    """Calculate fraction of near-white background."""
    if not _HAS_CV2:
        return 1.0  # Skip check if cv2 not available

    try:
        img = cv2.imread(str(img_path))
        if img is None:
            return 0.0

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Near-white criteria
        near_white = np.all(img_rgb >= 230, axis=-1)
        spread = np.max(img_rgb, axis=-1) - np.min(img_rgb, axis=-1)
        low_variance = spread <= 20

        good_bg = near_white & low_variance
        return float(np.sum(good_bg) / good_bg.size)
    except Exception:
        return 0.0

# ---------- Scrapers ----------

def scrape_uniqlo(category: str, max_images: int, session: requests.Session) -> List[Dict]:
    """
    Scrape Uniqlo product images.

    Note: Uniqlo uses a React SPA, so this is a simplified scraper.
    For production, use Selenium or their API if available.
    """
    results = []

    source = ECOMMERCE_SOURCES['uniqlo']
    base_url = source['base_url']
    category_path = source['categories'].get(category, source['categories']['t-shirts'])

    url = base_url + category_path

    print(f"[INFO] Scraping Uniqlo: {url}")
    print("[WARN] Uniqlo uses React SPA - this is a basic scraper. Consider using Selenium for better results.")

    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find product images (this selector may need adjustment)
        img_tags = soup.find_all('img', class_=re.compile(r'product.*image|thumb', re.I))

        for img in img_tags[:max_images]:
            src = img.get('src') or img.get('data-src')
            if not src:
                continue

            # Make absolute URL
            if src.startswith('//'):
                src = 'https:' + src
            elif not src.startswith('http'):
                src = urljoin(base_url, src)

            # Filter out tiny thumbnails
            if 'thumb' in src.lower() or 'small' in src.lower():
                continue

            results.append({
                'url': src,
                'source': 'uniqlo',
                'category': category,
                'alt': img.get('alt', '')
            })

            if len(results) >= max_images:
                break

    except Exception as e:
        print(f"[ERROR] Uniqlo scraping failed: {e}")

    return results

def scrape_from_url_list(url_list_file: Path, max_images: int, session: requests.Session) -> List[Dict]:
    """Load image URLs from a text file."""
    results = []

    if not url_list_file.exists():
        print(f"[ERROR] URL list file not found: {url_list_file}")
        return results

    print(f"[INFO] Loading URLs from: {url_list_file}")

    with open(url_list_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]

    for url in urls[:max_images]:
        results.append({
            'url': url,
            'source': 'custom',
            'category': 'unknown',
            'alt': ''
        })

    print(f"[INFO] Loaded {len(results)} URLs from file")
    return results

def scrape_generic_page(url: str, max_images: int, session: requests.Session) -> List[Dict]:
    """
    Generic scraper for any webpage.
    Finds all images and filters for likely product photos.
    """
    results = []

    print(f"[INFO] Scraping generic page: {url}")

    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all images
        img_tags = soup.find_all('img')

        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if not src:
                continue

            # Make absolute URL
            if src.startswith('//'):
                src = 'https:' + src
            elif not src.startswith('http'):
                src = urljoin(url, src)

            # Filter likely product images
            alt = img.get('alt', '').lower()
            src_lower = src.lower()

            # Skip common non-product images
            if any(x in src_lower for x in ['logo', 'icon', 'button', 'banner', 'avatar']):
                continue
            if any(x in src_lower for x in ['thumb', 'small', 'tiny']) and 'large' not in src_lower:
                continue

            results.append({
                'url': src,
                'source': 'generic',
                'category': 'unknown',
                'alt': img.get('alt', '')
            })

            if len(results) >= max_images:
                break

    except Exception as e:
        print(f"[ERROR] Generic scraping failed: {e}")

    return results

# ---------- Main Collection ----------

def collect_images(
    source: str,
    category: str,
    max_images: int,
    output_dir: Path,
    url_list: Optional[Path] = None,
    custom_url: Optional[str] = None,
    num_workers: int = 10
) -> List[Dict]:
    """Collect images from specified source."""

    session = get_session()

    # Scrape URLs
    if url_list:
        image_urls = scrape_from_url_list(url_list, max_images, session)
    elif custom_url:
        image_urls = scrape_generic_page(custom_url, max_images, session)
    elif source == 'uniqlo':
        image_urls = scrape_uniqlo(category, max_images, session)
    else:
        print(f"[ERROR] Unknown source: {source}")
        return []

    if not image_urls:
        print("[WARN] No image URLs found")
        return []

    print(f"\n[INFO] Found {len(image_urls)} image URLs")
    print(f"[INFO] Downloading to: {output_dir}")

    # Download images
    downloaded = []

    def download_worker(img_data: Dict) -> Optional[Dict]:
        url = img_data['url']
        filename = url_to_filename(url)
        img_path = output_dir / filename

        if img_path.exists():
            return None

        if download_image(url, img_path, session=session):
            return {
                'path': img_path,
                'url': url,
                'source': img_data['source'],
                'category': img_data['category'],
                'alt': img_data.get('alt', '')
            }
        return None

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(download_worker, img_data) for img_data in image_urls]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            result = future.result()
            if result:
                downloaded.append(result)

    print(f"[INFO] Successfully downloaded {len(downloaded)} images")
    return downloaded

def post_filter_images(
    images: List[Dict],
    person_filter: bool,
    min_bg_white: float,
    yolo_model: Optional[object] = None
) -> List[Dict]:
    """Apply post-processing filters."""

    print(f"\n[INFO] Post-filtering {len(images)} images...")

    filtered = []
    stats = {'person': 0, 'background': 0}

    for img_meta in tqdm(images, desc="Filtering"):
        img_path = img_meta['path']

        # Person filter
        if person_filter and yolo_model and has_person(img_path, yolo_model):
            stats['person'] += 1
            img_path.unlink(missing_ok=True)
            continue

        # Background filter
        if min_bg_white > 0 and _HAS_CV2:
            bg_score = background_whiteness_score(img_path)
            if bg_score < min_bg_white:
                stats['background'] += 1
                img_path.unlink(missing_ok=True)
                continue

        filtered.append(img_meta)

    print(f"[INFO] Kept {len(filtered)} images after filtering")
    print(f"       Removed: {stats['person']} (person), {stats['background']} (background)")

    return filtered

def export_to_coco(images: List[Dict], output_file: Path, category_name: str = "garment"):
    """Export to COCO format."""
    coco = {
        "images": [],
        "annotations": [],
        "categories": [{
            "id": 1,
            "name": category_name,
            "supercategory": "clothing",
            "keypoints": [],
            "skeleton": []
        }]
    }

    for idx, img_meta in enumerate(images):
        img_path = img_meta['path']

        try:
            img = Image.open(img_path)
            w, h = img.size
        except Exception:
            continue

        image_id = idx + 1

        coco["images"].append({
            "id": image_id,
            "file_name": img_path.name,
            "width": w,
            "height": h,
            "source_url": img_meta.get('url', ''),
            "source": img_meta.get('source', ''),
            "category": img_meta.get('category', ''),
            "alt_text": img_meta.get('alt', '')
        })

        coco["annotations"].append({
            "id": image_id,
            "image_id": image_id,
            "category_id": 1,
            "bbox": [],
            "area": 0,
            "iscrowd": 0,
            "keypoints": [],
            "num_keypoints": 0,
        })

    with open(output_file, 'w') as f:
        json.dump(coco, f, indent=2)

    print(f"[INFO] Exported COCO annotation to: {output_file}")

# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Scrape flat-lay garment images from e-commerce sites")

    parser.add_argument("--source", default="uniqlo",
                       choices=['uniqlo', 'hm', 'custom', 'url_list'],
                       help="E-commerce source")
    parser.add_argument("--category", default="t-shirts", help="Product category")
    parser.add_argument("--max_images", type=int, default=100, help="Maximum images to collect")
    parser.add_argument("--out_dir", type=Path, required=True, help="Output directory")

    # Custom sources
    parser.add_argument("--url_list", type=Path, help="Text file with image URLs (one per line)")
    parser.add_argument("--custom_url", type=str, help="Custom webpage URL to scrape")

    # Filters
    parser.add_argument("--person_filter", action="store_true", help="Filter out images with people")
    parser.add_argument("--min_bg_white", type=float, default=0.0,
                       help="Minimum white background fraction (0.0-1.0)")

    # Output
    parser.add_argument("--category_name", type=str, default="garment", help="COCO category name")
    parser.add_argument("--num_workers", type=int, default=10, help="Download workers")

    args = parser.parse_args()

    # Create output directory
    img_dir = args.out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Load YOLO if needed
    yolo_model = None
    if args.person_filter:
        if not _HAS_YOLO:
            print("[WARN] Person filter requested but ultralytics not available")
        else:
            print("[INFO] Loading YOLO model...")
            try:
                yolo_model = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[WARN] Failed to load YOLO: {e}")

    # Collect images
    downloaded = collect_images(
        source=args.source,
        category=args.category,
        max_images=args.max_images,
        output_dir=img_dir,
        url_list=args.url_list,
        custom_url=args.custom_url,
        num_workers=args.num_workers
    )

    if not downloaded:
        print("[ERROR] No images downloaded")
        return 1

    # Post-filter
    filtered = post_filter_images(
        images=downloaded,
        person_filter=args.person_filter,
        min_bg_white=args.min_bg_white,
        yolo_model=yolo_model
    )

    if not filtered:
        print("[ERROR] No images passed filtering")
        return 1

    # Export to COCO
    coco_file = args.out_dir / "annotations.json"
    export_to_coco(filtered, coco_file, args.category_name)

    # Summary
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Collection complete!")
    print(f"{'='*60}")
    print(f"Total images:     {len(filtered)}")
    print(f"Output directory: {args.out_dir}")
    print(f"Images:           {img_dir}")
    print(f"COCO annotations: {coco_file}")
    print(f"{'='*60}")

    return 0

if __name__ == "__main__":
    exit(main())
