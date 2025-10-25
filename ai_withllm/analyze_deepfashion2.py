#!/usr/bin/env python3
"""
Analyze DeepFashion2 dataset to understand category names and scale values.
"""

import json
from pathlib import Path
from collections import Counter

def analyze_deepfashion2(annos_dir: str, num_samples: int = 1000):
    """Analyze DeepFashion2 annotations."""

    annos_path = Path(annos_dir)
    anno_files = sorted(annos_path.glob('*.json'))[:num_samples]

    categories = []
    scales = []
    viewpoints = []
    zoom_levels = []
    scale_category_combos = []

    print(f"Analyzing {len(anno_files)} annotation files...")

    for anno_file in anno_files:
        try:
            with open(anno_file, 'r') as f:
                data = json.load(f)

            # Process item1 and item2
            for item_key in ['item1', 'item2']:
                if item_key in data:
                    item = data[item_key]
                    cat_name = item.get('category_name', '')
                    scale = item.get('scale', 0)
                    viewpoint = item.get('viewpoint', 0)
                    zoom = item.get('zoom_in', 0)

                    if cat_name:
                        categories.append(cat_name)
                        scales.append(scale)
                        viewpoints.append(viewpoint)
                        zoom_levels.append(zoom)
                        scale_category_combos.append(f"scale_{scale}_{cat_name}")

        except Exception as e:
            print(f"Error processing {anno_file}: {e}")
            continue

    # Print statistics
    print("\n" + "="*60)
    print("CATEGORY ANALYSIS")
    print("="*60)
    cat_counts = Counter(categories)
    for cat, count in cat_counts.most_common(20):
        print(f"  {cat:30s}: {count:5d}")

    print("\n" + "="*60)
    print("SCALE DISTRIBUTION")
    print("="*60)
    scale_counts = Counter(scales)
    for scale, count in sorted(scale_counts.items()):
        print(f"  Scale {scale}: {count:5d} ({count/len(scales)*100:.1f}%)")

    print("\n" + "="*60)
    print("VIEWPOINT DISTRIBUTION")
    print("="*60)
    vp_counts = Counter(viewpoints)
    for vp, count in sorted(vp_counts.items()):
        print(f"  Viewpoint {vp}: {count:5d} ({count/len(viewpoints)*100:.1f}%)")

    print("\n" + "="*60)
    print("ZOOM_IN DISTRIBUTION")
    print("="*60)
    zoom_counts = Counter(zoom_levels)
    for zoom, count in sorted(zoom_counts.items()):
        print(f"  Zoom {zoom}: {count:5d} ({count/len(zoom_levels)*100:.1f}%)")

    # T-shirt specific analysis
    print("\n" + "="*60)
    print("T-SHIRT RELATED CATEGORIES")
    print("="*60)
    tshirt_cats = [cat for cat in cat_counts.keys() if 'top' in cat.lower() or 'shirt' in cat.lower() or 'tee' in cat.lower()]
    for cat in tshirt_cats:
        print(f"  {cat}: {cat_counts[cat]} items")

    # Scale analysis for t-shirts
    print("\n" + "="*60)
    print("SCALE DISTRIBUTION FOR 'short sleeve top' (likely t-shirts)")
    print("="*60)
    tshirt_scales = [s.split('_')[1] for s in scale_category_combos if 'short sleeve top' in s]
    if tshirt_scales:
        ts_counts = Counter(tshirt_scales)
        for scale, count in sorted(ts_counts.items()):
            print(f"  Scale {scale}: {count} items ({count/len(tshirt_scales)*100:.1f}%)")

if __name__ == '__main__':
    analyze_deepfashion2('/home/celso/Downloads/train2020/train/annos', num_samples=1000)
