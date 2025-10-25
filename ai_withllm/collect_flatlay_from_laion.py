#!/usr/bin/env python3
"""
Collect flat-lay garment images from LAION-5B using CLIP retrieval.

This script:
1. Queries LAION-5B using semantic text search
2. Applies quality filters (aesthetic, NSFW, watermark)
3. Downloads images
4. Post-filters using person detection and background analysis
5. Exports to COCO format for keypoint annotation

Usage:
  python collect_flatlay_from_laion.py \
    --query "flat lay t-shirt, isolated on white background" \
    --out_dir ./laion_flatlay_dataset \
    --max_images 1000 \
    --aesthetic_min 5.0 \
    --person_filter true

Requirements:
  pip install clip-retrieval pillow numpy opencv-python tqdm requests ultralytics
"""

import argparse
import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image
from tqdm import tqdm
import requests

# LAION CLIP retrieval
try:
    from clip_retrieval.clip_client import ClipClient
    _HAS_CLIP_RETRIEVAL = True
except ImportError:
    _HAS_CLIP_RETRIEVAL = False
    print("[ERROR] clip-retrieval not installed. Install with: pip install clip-retrieval")

# OpenCV for background analysis
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False
    print("[WARN] OpenCV not installed. Background filtering will be limited.")

# YOLO for person detection
try:
    from ultralytics import YOLO
    _HAS_YOLO = True
except ImportError:
    _HAS_YOLO = False
    print("[WARN] ultralytics not installed. Person filtering will be disabled.")

# ---------- Constants ----------

DEFAULT_QUERIES = [
    "flat lay t-shirt, isolated on white background, sleeves extended, no model, product photo",
    "flat lay long sleeve t-shirt, white background, no mannequin",
    "tshirt flat lay on white, retail product, top view",
    "shirt flat lay white background product photography",
    "flatlay shirt isolated white studio shot no person",
]

LAION_INDICES = {
    "laion5B-H-14": "https://knn.laion.ai/knn-service",  # ViT-H-14 (best quality)
    "laion5B-L-14": "https://knn.laion.ai/knn-service",  # ViT-L-14
}

# ---------- Helper Functions ----------

def download_image(url: str, output_path: Path, timeout: int = 10) -> bool:
    """
    Download image from URL.

    Args:
        url: Image URL
        output_path: Where to save the image
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers, stream=True)
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
            return True
        except Exception:
            output_path.unlink(missing_ok=True)
            return False

    except Exception as e:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return False

def url_to_filename(url: str, extension: str = ".jpg") -> str:
    """Convert URL to safe filename using hash."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return f"{url_hash}{extension}"

def has_person(img_path: Path, yolo_model) -> bool:
    """
    Check if image contains a person.

    Args:
        img_path: Path to image
        yolo_model: YOLO model instance

    Returns:
        True if person detected
    """
    try:
        results = yolo_model.predict(str(img_path), verbose=False, conf=0.3)
        for r in results:
            if r.boxes is None:
                continue
            cls = r.boxes.cls.cpu().numpy().astype(int)
            if (cls == 0).any():  # person class in COCO
                return True
    except Exception as e:
        print(f"[WARN] Person detection failed for {img_path}: {e}")
    return False

def background_whiteness_score(img_path: Path) -> float:
    """
    Calculate what fraction of the image is near-white.

    Args:
        img_path: Path to image

    Returns:
        Score between 0.0 and 1.0
    """
    try:
        img = cv2.imread(str(img_path))
        if img is None:
            return 0.0

        # Convert to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Near-white: all channels >= 230
        near_white = np.all(img >= 230, axis=-1)

        # Low color variance (channel spread <= 20)
        spread = np.max(img, axis=-1) - np.min(img, axis=-1)
        low_variance = spread <= 20

        good_bg = near_white & low_variance
        score = np.sum(good_bg) / good_bg.size

        return float(score)
    except Exception as e:
        print(f"[WARN] Background analysis failed for {img_path}: {e}")
        return 0.0

def check_image_quality(img_path: Path, min_width: int = 512, min_height: int = 512) -> bool:
    """
    Check basic image quality requirements.

    Args:
        img_path: Path to image
        min_width: Minimum width
        min_height: Minimum height

    Returns:
        True if image meets requirements
    """
    try:
        img = Image.open(img_path)
        w, h = img.size

        # Size check
        if w < min_width or h < min_height:
            return False

        # Aspect ratio check (reasonable for garments)
        aspect = max(w, h) / min(w, h)
        if aspect > 3.0:  # too extreme
            return False

        return True
    except Exception:
        return False

# ---------- Main Collection Logic ----------

def query_laion(
    url: str,
    index_name: str,
    query: str,
    max_images: int,
    aesthetic_min: float,
    nsfw_max: float,
    watermark_max: float,
    clip_threshold: float
) -> List[Dict]:
    """
    Query LAION-5B for images matching the text query.

    Args:
        url: LAION backend URL
        index_name: Index name (e.g., "laion5B-H-14")
        query: Text query
        max_images: Maximum number of results
        aesthetic_min: Minimum aesthetic score
        nsfw_max: Maximum NSFW score
        watermark_max: Maximum watermark score
        clip_threshold: CLIP similarity threshold

    Returns:
        List of result dictionaries
    """
    print(f"\n[INFO] Querying LAION-5B: '{query}'")
    print(f"       Filters: aesthetic>={aesthetic_min}, nsfw<={nsfw_max}, watermark<={watermark_max}")

    try:
        # Create client with the correct parameters in constructor
        client = ClipClient(
            url=url,
            indice_name=index_name,
            use_mclip=False,
            aesthetic_score=int(aesthetic_min),  # Must be int
            aesthetic_weight=0.5,
            num_images=max_images * 3,  # Request more to account for filtering
            deduplicate=True,
            use_safety_model=True,
            use_violence_detector=True,
        )

        # Query only accepts text/image/embedding_input
        results = client.query(text=query)

        # Additional filtering
        filtered = []
        for r in results:
            # Check NSFW score
            if r.get('nsfw_score', 1.0) > nsfw_max:
                continue
            # Check watermark score (if available)
            if r.get('watermark_score', 0.0) > watermark_max:
                continue
            # Check similarity
            if r.get('similarity', 0.0) < clip_threshold:
                continue

            filtered.append(r)

        print(f"[INFO] Found {len(results)} results, {len(filtered)} after filtering")
        return filtered[:max_images]

    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def download_worker(args) -> Optional[Dict]:
    """Worker function for parallel downloads."""
    result, output_dir = args

    url = result.get('url')
    if not url:
        return None

    filename = url_to_filename(url)
    img_path = output_dir / filename

    if img_path.exists():
        return None  # Already downloaded

    if download_image(url, img_path):
        return {
            'path': img_path,
            'url': url,
            'caption': result.get('caption', ''),
            'similarity': result.get('similarity', 0.0),
            'aesthetic_score': result.get('aesthetic_score', 0.0),
        }
    return None

def collect_images(
    queries: List[str],
    output_dir: Path,
    max_images: int,
    aesthetic_min: float,
    nsfw_max: float,
    watermark_max: float,
    clip_threshold: float,
    index_name: str,
    num_workers: int = 10
) -> List[Dict]:
    """
    Collect images from LAION-5B.

    Returns:
        List of successfully downloaded image metadata
    """
    if not _HAS_CLIP_RETRIEVAL:
        print("[ERROR] clip-retrieval not available")
        return []

    print(f"[INFO] Querying LAION-5B index: {index_name}")

    # Query for each text prompt
    all_results = []
    for query in queries:
        results = query_laion(
            url=LAION_INDICES[index_name],
            index_name=index_name,
            query=query,
            max_images=max_images // len(queries),
            aesthetic_min=aesthetic_min,
            nsfw_max=nsfw_max,
            watermark_max=watermark_max,
            clip_threshold=clip_threshold
        )
        all_results.extend(results)
        time.sleep(1)  # Rate limiting

    if not all_results:
        print("[WARN] No results found")
        return []

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    print(f"\n[INFO] Downloading {len(unique_results)} unique images...")

    # Download in parallel
    download_args = [(r, output_dir) for r in unique_results]
    downloaded = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(download_worker, args) for args in download_args]

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
    min_width: int,
    min_height: int,
    yolo_model: Optional[object] = None
) -> List[Dict]:
    """
    Apply post-processing filters to downloaded images.

    Returns:
        Filtered list of image metadata
    """
    print(f"\n[INFO] Post-filtering {len(images)} images...")

    filtered = []
    stats = {
        'person': 0,
        'background': 0,
        'quality': 0,
    }

    for img_meta in tqdm(images, desc="Filtering"):
        img_path = img_meta['path']

        # Quality check
        if not check_image_quality(img_path, min_width, min_height):
            stats['quality'] += 1
            img_path.unlink(missing_ok=True)
            continue

        # Person filter
        if person_filter and yolo_model and has_person(img_path, yolo_model):
            stats['person'] += 1
            img_path.unlink(missing_ok=True)
            continue

        # Background filter
        if _HAS_CV2 and min_bg_white > 0:
            bg_score = background_whiteness_score(img_path)
            if bg_score < min_bg_white:
                stats['background'] += 1
                img_path.unlink(missing_ok=True)
                continue

        filtered.append(img_meta)

    print(f"[INFO] Kept {len(filtered)} images after filtering")
    print(f"       Removed: {stats['person']} (person), {stats['background']} (background), {stats['quality']} (quality)")

    return filtered

def export_to_coco(images: List[Dict], output_file: Path, category_name: str = "garment"):
    """
    Export filtered images to COCO format for annotation.

    Args:
        images: List of image metadata
        output_file: Path to output JSON file
        category_name: Category name for COCO
    """
    coco = {
        "images": [],
        "annotations": [],
        "categories": [{
            "id": 1,
            "name": category_name,
            "supercategory": "clothing",
            "keypoints": [],  # To be defined during annotation
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
            "caption": img_meta.get('caption', ''),
            "aesthetic_score": img_meta.get('aesthetic_score', 0.0),
            "similarity": img_meta.get('similarity', 0.0),
        })

        # Add empty annotation (bbox will be added during annotation)
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
    parser = argparse.ArgumentParser(description="Collect flat-lay garment images from LAION-5B")

    # Query parameters
    parser.add_argument("--query", type=str, nargs='+', help="Custom text queries")
    parser.add_argument("--use_default_queries", action="store_true", help="Use default flat-lay queries")
    parser.add_argument("--max_images", type=int, default=1000, help="Maximum images to collect")
    parser.add_argument("--index", default="laion5B-H-14", choices=list(LAION_INDICES.keys()),
                       help="LAION index to use")

    # Quality filters
    parser.add_argument("--aesthetic_min", type=float, default=5.0, help="Minimum aesthetic score")
    parser.add_argument("--nsfw_max", type=float, default=0.1, help="Maximum NSFW score")
    parser.add_argument("--watermark_max", type=float, default=0.5, help="Maximum watermark score")
    parser.add_argument("--clip_threshold", type=float, default=0.28, help="CLIP similarity threshold")

    # Post-processing filters
    parser.add_argument("--person_filter", action="store_true", help="Filter out images with people")
    parser.add_argument("--min_bg_white", type=float, default=0.50,
                       help="Minimum fraction of white background (0.0-1.0)")
    parser.add_argument("--min_width", type=int, default=512, help="Minimum image width")
    parser.add_argument("--min_height", type=int, default=512, help="Minimum image height")

    # Output
    parser.add_argument("--out_dir", type=Path, required=True, help="Output directory")
    parser.add_argument("--category_name", type=str, default="garment", help="COCO category name")
    parser.add_argument("--num_workers", type=int, default=10, help="Number of download workers")

    args = parser.parse_args()

    # Check dependencies
    if not _HAS_CLIP_RETRIEVAL:
        print("[ERROR] clip-retrieval is required. Install with: pip install clip-retrieval")
        return 1

    # Prepare queries
    queries = []
    if args.use_default_queries:
        queries.extend(DEFAULT_QUERIES)
    if args.query:
        queries.extend(args.query)
    if not queries:
        print("[ERROR] No queries specified. Use --query or --use_default_queries")
        return 1

    # Create output directory
    img_dir = args.out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Load YOLO model if needed
    yolo_model = None
    if args.person_filter:
        if not _HAS_YOLO:
            print("[WARN] Person filter requested but ultralytics not available")
        else:
            print("[INFO] Loading YOLO model for person detection...")
            try:
                yolo_model = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[WARN] Failed to load YOLO: {e}")

    # Step 1: Query and download
    downloaded = collect_images(
        queries=queries,
        output_dir=img_dir,
        max_images=args.max_images,
        aesthetic_min=args.aesthetic_min,
        nsfw_max=args.nsfw_max,
        watermark_max=args.watermark_max,
        clip_threshold=args.clip_threshold,
        index_name=args.index,
        num_workers=args.num_workers
    )

    if not downloaded:
        print("[ERROR] No images downloaded")
        return 1

    # Step 2: Post-filter
    filtered = post_filter_images(
        images=downloaded,
        person_filter=args.person_filter,
        min_bg_white=args.min_bg_white,
        min_width=args.min_width,
        min_height=args.min_height,
        yolo_model=yolo_model
    )

    if not filtered:
        print("[ERROR] No images passed filtering")
        return 1

    # Step 3: Export to COCO
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
    print("\nNext steps:")
    print("1. Review the collected images")
    print("2. Import annotations.json into your annotation tool (Roboflow/Label Studio)")
    print("3. Start annotating keypoints for garment measurements")

    return 0

if __name__ == "__main__":
    exit(main())
