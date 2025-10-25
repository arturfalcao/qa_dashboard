#!/usr/bin/env python3
"""
Build a FLAT-LAY TOPS subset from DeepFashion2 and export COCO for keypoint annotation.

What it does:
1) Scans DeepFashion2 annotations.
2) Keeps only items with category_id in {1, 2} (short/long-sleeve tops).
3) Optional: drops images that contain a PERSON (using a small YOLO model).
4) Flat-lay / shop-photo heuristic: require high near-white background outside mask.
5) Copies images to output and writes COCO (images + bbox; no keypoints yet).

Usage:
  python build_flatlay_tops_from_df2.py \
    --df2_root /path/to/DeepFashion2 \
    --split train \
    --out_dir ./df2_flatlay_tops \
    --min_bg_white 0.70 \
    --person_filter true

Notes:
- DeepFashion2 structure typically:
  {df2_root}/train/image/xxxxx.jpg
  {df2_root}/train/annos/xxxxx.json
- If you downloaded a mirror, adapt the paths accordingly.
"""

import argparse
import json
import os
import shutil
import math
from pathlib import Path
from typing import List, Dict
import numpy as np
from PIL import Image
from tqdm import tqdm

# Check for cv2 (required)
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False
    print("[ERROR] OpenCV (cv2) is required but not installed. Install with: pip install opencv-python")

# Optional: person filter via Ultralytics YOLO (COCO 'person')
try:
    import torch  # noqa
    from ultralytics import YOLO
    _HAS_YOLO = True
except ImportError:
    _HAS_YOLO = False

# ---------- helpers ----------

def load_df2_anno(fp: Path) -> Dict:
    """Load DeepFashion2 annotation JSON file."""
    with open(fp, "r") as f:
        return json.load(f)

def poly_to_mask(poly: List[float], w: int, h: int) -> np.ndarray:
    """
    Convert polygon to binary mask.

    Args:
        poly: Flat list [x1,y1,x2,y2,...]
        w: Image width
        h: Image height

    Returns:
        Binary mask (uint8, 1=inside polygon, 0=outside)
    """
    if not _HAS_CV2:
        raise RuntimeError("OpenCV is required for poly_to_mask")

    pts = np.array(poly, dtype=np.float32).reshape(-1, 2)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts.astype(np.int32)], 1)
    return mask

def background_whiteness_score(img: np.ndarray, mask: np.ndarray) -> float:
    """
    Calculate ratio of near-white pixels OUTSIDE the garment mask.

    Args:
        img: HxWx3 uint8 RGB image
        mask: HxW uint8 mask (1=garment, 0=background)

    Returns:
        Score between 0.0 and 1.0
    """
    bg = (mask == 0)
    if not np.any(bg):
        return 0.0

    # Near-white criteria: all channels >= 230 and low variance across channels
    rgb = img.astype(np.int16)
    near_white = (rgb[..., 0] >= 230) & (rgb[..., 1] >= 230) & (rgb[..., 2] >= 230)

    # Penalize strong color casts: channel spread <= 20
    spread = (np.max(rgb, axis=-1) - np.min(rgb, axis=-1)) <= 20
    good = near_white & spread

    return float(np.sum(good & bg)) / float(np.sum(bg))

def has_person(img_path: Path, yolo_model) -> bool:
    """
    Check if a person is detected in the image.

    Args:
        img_path: Path to image file
        yolo_model: YOLO model instance

    Returns:
        True if person detected (COCO class 0)
    """
    try:
        results = yolo_model.predict(str(img_path), verbose=False)
        for r in results:
            if r.boxes is None:
                continue
            cls = r.boxes.cls.cpu().numpy().astype(int)
            if (cls == 0).any():  # person class id in COCO
                return True
    except Exception as e:
        print(f"[WARN] Person detection failed for {img_path}: {e}")
    return False

def df2_items_iter(df2_root: Path, split: str):
    """
    Iterate over DeepFashion2 annotation/image pairs.

    Args:
        df2_root: Root directory of DeepFashion2 dataset
        split: Dataset split (train/validation/test)

    Yields:
        Tuples of (image_path, annotation_path)
    """
    anno_dir = df2_root / split / "annos"
    img_dir = df2_root / split / "image"

    if not anno_dir.exists():
        print(f"[ERROR] Annotation directory not found: {anno_dir}")
        return

    if not img_dir.exists():
        print(f"[ERROR] Image directory not found: {img_dir}")
        return

    for anno_fp in sorted(anno_dir.glob("*.json")):
        # Try .jpg first
        img_fp = img_dir / (anno_fp.stem + ".jpg")
        if not img_fp.exists():
            # Fallback to .png
            img_fp = img_dir / (anno_fp.stem + ".png")
            if not img_fp.exists():
                continue
        yield img_fp, anno_fp

# ---------- main ----------

def main():
    if not _HAS_CV2:
        print("[ERROR] OpenCV (cv2) is required. Install with: pip install opencv-python")
        return 1

    ap = argparse.ArgumentParser(description="Extract flat-lay tops from DeepFashion2 for keypoint annotation")
    ap.add_argument("--df2_root", required=True, type=Path, help="Root directory of DeepFashion2 dataset")
    ap.add_argument("--split", default="train", choices=["train", "validation", "test"], help="Dataset split")
    ap.add_argument("--out_dir", required=True, type=Path, help="Output directory")
    ap.add_argument("--min_bg_white", type=float, default=0.70,
                    help="Minimum fraction of near-white background outside mask (0.0-1.0)")
    ap.add_argument("--person_filter", type=str, default="true", help="Filter out images with people (true/false)")
    ap.add_argument("--max_items", type=int, default=0, help="Maximum items to process (0 = no limit)")
    ap.add_argument("--copy_images", type=str, default="true", help="Copy images to output directory (true/false)")
    ap.add_argument("--category_name", type=str, default="top", help="COCO category name")
    args = ap.parse_args()

    person_filter = args.person_filter.lower() in ("1", "true", "yes", "y")
    do_copy = args.copy_images.lower() in ("1", "true", "yes", "y")

    # YOLO tiny model for person detection (optional)
    yolo_model = None
    if person_filter:
        if not _HAS_YOLO:
            print("[WARN] person_filter requested but 'ultralytics' not available. Skipping person filter.")
            print("       Install with: pip install ultralytics")
        else:
            print("[INFO] Loading YOLO model for person detection...")
            try:
                yolo_model = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[WARN] Failed to load YOLO model: {e}. Skipping person filter.")
                yolo_model = None

    # COCO scaffolding
    out = {
        "images": [],
        "annotations": [],
        "categories": [{
            "id": 1,
            "name": args.category_name,
            "supercategory": "garment",
            # Prepare for KEYPOINT annotation later (empty now, define your schema here if you want)
            "keypoints": [],
            "skeleton": []
        }]
    }
    ann_id = 1

    img_out_dir = args.out_dir / "images"
    os.makedirs(img_out_dir, exist_ok=True)
    anno_out_fp = args.out_dir / f"instances_{args.split}.json"

    kept = 0
    skipped_person = 0
    skipped_bg = 0
    skipped_no_top = 0
    skipped_no_mask = 0

    print(f"[INFO] Scanning DeepFashion2: {args.df2_root} / {args.split}")

    for img_fp, anno_fp in tqdm(list(df2_items_iter(args.df2_root, args.split)), desc="Processing images"):
        try:
            ann = load_df2_anno(anno_fp)
        except Exception as e:
            print(f"[WARN] Failed to load annotation {anno_fp}: {e}")
            continue

        # Each DF2 annotation has "items" (one or more garments per image)
        items = ann.get("items", [])
        # Keep only tops: category_id in {1, 2}
        top_items = [it for it in items if it.get("category_id") in (1, 2)]  # short/long-sleeve tops
        if not top_items:
            skipped_no_top += 1
            continue

        # Load image now (once)
        try:
            img = Image.open(img_fp).convert("RGB")
        except Exception as e:
            print(f"[WARN] Failed to load image {img_fp}: {e}")
            continue

        w, h = img.size
        np_img = np.array(img)

        # Person filter
        if yolo_model is not None and has_person(img_fp, yolo_model):
            skipped_person += 1
            continue

        # Flat-lay / shop-photo heuristic:
        # Require that the background OUTSIDE the garment (union of masks) is predominantly near-white.
        union_mask = np.zeros((h, w), dtype=np.uint8)
        ok_mask = False
        for it in top_items:
            seg = it.get("segmentation", [])
            if isinstance(seg, list) and len(seg) > 0:
                # DF2 uses polygon(s); take union
                for poly in seg:
                    if isinstance(poly, list) and len(poly) >= 6:
                        try:
                            m = poly_to_mask(poly, w, h)
                            union_mask |= m
                            ok_mask = True
                        except Exception as e:
                            print(f"[WARN] Failed to create mask for {img_fp}: {e}")

        if not ok_mask:
            # No mask → skip (we rely on mask to assess background)
            skipped_no_mask += 1
            continue

        bg_white = background_whiteness_score(np_img, union_mask)
        if bg_white < args.min_bg_white:
            skipped_bg += 1
            continue

        # Passed all filters -> keep image & add bbox annotations for the kept tops
        # Copy image
        if do_copy:
            dst = img_out_dir / img_fp.name
            if img_fp.resolve() != dst.resolve():
                try:
                    shutil.copy2(img_fp, dst)
                except Exception as e:
                    print(f"[WARN] Failed to copy {img_fp} to {dst}: {e}")
                    continue
            out_img_path = dst.name
        else:
            out_img_path = str(img_fp)

        # Add image record
        # Try to parse image_id from filename (DeepFashion2 uses numeric names)
        try:
            image_id = int(img_fp.stem)
        except ValueError:
            # If filename is not numeric, use hash or counter
            image_id = hash(img_fp.stem) % (2**31)

        out["images"].append({
            "id": image_id,
            "file_name": out_img_path,
            "width": w,
            "height": h
        })

        # Add bbox annos for each top item (COCO xywh)
        for it in top_items:
            bbox = it.get("bounding_box") or it.get("bbox") or it.get("box")
            # DF2 'bounding_box' is [x1, y1, x2, y2]; convert to xywh
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = bbox
                x, y = float(x1), float(y1)
                bw, bh = float(x2 - x1), float(y2 - y1)
            else:
                # Fallback from segmentation
                seg = it.get("segmentation", [])
                if not seg:
                    continue
                xs, ys = [], []
                for poly in seg:
                    if isinstance(poly, list):
                        xs.extend(poly[0::2])
                        ys.extend(poly[1::2])
                if not xs or not ys:
                    continue
                x, y = float(min(xs)), float(min(ys))
                bw, bh = float(max(xs) - x), float(max(ys) - y)

            area = max(bw, 0.0) * max(bh, 0.0)
            out["annotations"].append({
                "id": ann_id,
                "image_id": image_id,
                "category_id": 1,  # our single 'top' category
                "bbox": [x, y, bw, bh],
                "area": area,
                "iscrowd": 0,
                # No keypoints yet; you'll annotate them later in Roboflow/Label Studio
                "keypoints": [],
                "num_keypoints": 0,
                "segmentation": []
            })
            ann_id += 1

        kept += 1
        if args.max_items and kept >= args.max_items:
            break

    # Save COCO annotation file
    with open(anno_out_fp, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n{'='*60}")
    print(f"[DONE] Processing complete!")
    print(f"{'='*60}")
    print(f"Kept images:              {kept}")
    print(f"Skipped (no tops):        {skipped_no_top}")
    print(f"Skipped (no mask):        {skipped_no_mask}")
    print(f"Skipped (person detected): {skipped_person}")
    print(f"Skipped (background):     {skipped_bg}")
    print(f"\nOutput directory:         {args.out_dir}")
    print(f"COCO annotation file:     {anno_out_fp}")
    print(f"{'='*60}")

    if person_filter and yolo_model is None:
        print("[NOTE] Person filter was requested but wasn't available; no person filtering applied.")

    print("\nNext steps:")
    print("1. Review the filtered images in the output directory")
    print("2. Import the COCO JSON into Roboflow/Label Studio")
    print("3. Start annotating keypoints for garment measurements")

    return 0

if __name__ == "__main__":
    exit(main())
