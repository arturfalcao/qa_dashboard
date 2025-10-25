#!/usr/bin/env python3
"""
Filter DeepFashion2 dataset for flat-lay t-shirt images without humans.

This script:
1. Reads DeepFashion2 annotations
2. Filters for t-shirt categories ("short sleeve top", "long sleeve top")
3. Filters for flat-lay images (scale=3)
4. Uses YOLO to detect and exclude images with humans
5. Exports filtered images and annotations in COCO format
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from PIL import Image
import argparse

# Try to import YOLO for person detection
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    print("⚠️  ultralytics not installed. Person detection will be skipped.")
    print("   Install with: pip install ultralytics")
    HAS_YOLO = False

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback: simple progress indicator
    class tqdm:
        def __init__(self, iterable, desc=''):
            self.iterable = iterable
            self.desc = desc
        def __iter__(self):
            for item in self.iterable:
                yield item
        def set_postfix(self, *args, **kwargs):
            pass


class DeepFashion2TShirtFilter:
    """Filter DeepFashion2 for flat-lay t-shirts."""

    # T-shirt category names in DeepFashion2
    TSHIRT_CATEGORIES = [
        'short sleeve top',
        'long sleeve top'
    ]

    # Scale 3 typically indicates flat-lay/product images
    FLATLAY_SCALE = 3

    def __init__(self,
                 deepfashion_dir: str,
                 output_dir: str,
                 use_person_detection: bool = True,
                 person_confidence_threshold: float = 0.5,
                 only_flatlay_scale: bool = True):
        """
        Initialize the filter.

        Args:
            deepfashion_dir: Path to DeepFashion2 train folder (contains image/ and annos/)
            output_dir: Output directory for filtered images
            use_person_detection: Whether to use YOLO for person detection
            person_confidence_threshold: Confidence threshold for person detection
            only_flatlay_scale: If True, only include scale=3 (flat-lay), else include all scales
        """
        self.deepfashion_dir = Path(deepfashion_dir)
        self.output_dir = Path(output_dir)
        self.use_person_detection = use_person_detection and HAS_YOLO
        self.person_threshold = person_confidence_threshold
        self.only_flatlay_scale = only_flatlay_scale

        # Setup paths
        self.images_dir = self.deepfashion_dir / 'image'
        self.annos_dir = self.deepfashion_dir / 'annos'

        # Create output directories
        self.output_images_dir = self.output_dir / 'images'
        self.output_images_dir.mkdir(parents=True, exist_ok=True)

        # Load YOLO model for person detection
        self.yolo_model = None
        if self.use_person_detection:
            print("Loading YOLO model for person detection...")
            self.yolo_model = YOLO('yolov8n.pt')  # Nano model for speed

        # Statistics
        self.stats = {
            'total_annotations': 0,
            'tshirt_items': 0,
            'flatlay_items': 0,
            'passed_person_check': 0,
            'final_copied': 0
        }

    def has_person(self, img_path: Path) -> bool:
        """Check if image contains a person using YOLO."""
        if not self.yolo_model:
            return False

        try:
            results = self.yolo_model(img_path, verbose=False)

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Class 0 is 'person' in COCO dataset
                    if int(box.cls[0]) == 0 and float(box.conf[0]) > self.person_threshold:
                        return True

            return False
        except Exception as e:
            print(f"  Error detecting person in {img_path.name}: {e}")
            return False

    def is_tshirt_item(self, item: Dict) -> bool:
        """Check if item is a t-shirt."""
        category = item.get('category_name', '')
        return category in self.TSHIRT_CATEGORIES

    def is_flatlay_item(self, item: Dict) -> bool:
        """Check if item is flat-lay (scale=3)."""
        if not self.only_flatlay_scale:
            return True
        return item.get('scale', 0) == self.FLATLAY_SCALE

    def process_annotation(self, anno_file: Path) -> Tuple[bool, Dict]:
        """
        Process a single annotation file.

        Returns:
            (should_copy, metadata) tuple
        """
        try:
            with open(anno_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {anno_file}: {e}")
            return False, {}

        self.stats['total_annotations'] += 1

        # Check item1 and item2 for t-shirts
        for item_key in ['item1', 'item2']:
            if item_key not in data:
                continue

            item = data[item_key]

            # Check if it's a t-shirt
            if not self.is_tshirt_item(item):
                continue

            self.stats['tshirt_items'] += 1

            # Check if it's flat-lay
            if not self.is_flatlay_item(item):
                continue

            self.stats['flatlay_items'] += 1

            # Get image path
            img_name = anno_file.stem + '.jpg'
            img_path = self.images_dir / img_name

            if not img_path.exists():
                print(f"  Image not found: {img_path}")
                continue

            # Check for person
            if self.use_person_detection:
                if self.has_person(img_path):
                    # print(f"  Person detected in {img_name}, skipping...")
                    continue

            self.stats['passed_person_check'] += 1

            # Extract metadata
            metadata = {
                'image_name': img_name,
                'image_path': str(img_path),
                'category_name': item.get('category_name'),
                'scale': item.get('scale'),
                'viewpoint': item.get('viewpoint'),
                'zoom_in': item.get('zoom_in'),
                'landmarks': item.get('landmarks', []),
                'segmentation': item.get('segmentation', []),
                'bounding_box': item.get('bounding_box', [])
            }

            return True, metadata

        return False, {}

    def filter_dataset(self, max_images: int = None):
        """Filter the entire dataset."""

        print("="*60)
        print("DEEPFASHION2 T-SHIRT FLAT-LAY FILTER")
        print("="*60)
        print(f"Source: {self.deepfashion_dir}")
        print(f"Output: {self.output_dir}")
        print(f"T-shirt categories: {', '.join(self.TSHIRT_CATEGORIES)}")
        print(f"Flat-lay scale filter: {'Yes (scale=3 only)' if self.only_flatlay_scale else 'No (all scales)'}")
        print(f"Person detection: {'Enabled' if self.use_person_detection else 'Disabled'}")
        print("="*60)

        # Get all annotation files
        anno_files = sorted(self.annos_dir.glob('*.json'))
        print(f"\nFound {len(anno_files)} annotation files")

        # Process annotations
        filtered_images = []
        pbar = tqdm(anno_files, desc="Processing annotations")

        for anno_file in pbar:
            should_copy, metadata = self.process_annotation(anno_file)

            if should_copy:
                filtered_images.append(metadata)
                pbar.set_postfix({'found': len(filtered_images)})

                if max_images and len(filtered_images) >= max_images:
                    print(f"\nReached maximum of {max_images} images")
                    break

        print(f"\n✓ Found {len(filtered_images)} flat-lay t-shirt images")

        # Copy images
        print("\nCopying images...")
        coco_images = []
        coco_annotations = []

        for idx, metadata in enumerate(tqdm(filtered_images, desc="Copying images"), 1):
            src_path = Path(metadata['image_path'])
            dst_path = self.output_images_dir / metadata['image_name']

            try:
                shutil.copy2(src_path, dst_path)

                # Get image dimensions
                with Image.open(dst_path) as img:
                    width, height = img.size

                # Create COCO image entry
                coco_images.append({
                    'id': idx,
                    'file_name': metadata['image_name'],
                    'width': width,
                    'height': height,
                    'source': 'deepfashion2',
                    'category': metadata['category_name'],
                    'scale': metadata['scale'],
                    'viewpoint': metadata['viewpoint'],
                    'zoom_in': metadata['zoom_in']
                })

                # Create COCO annotation entry
                bbox = metadata.get('bounding_box', [])
                if len(bbox) == 4:
                    x, y, w, h = bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]
                    area = w * h
                else:
                    x, y, w, h = 0, 0, 0, 0
                    area = 0

                coco_annotations.append({
                    'id': idx,
                    'image_id': idx,
                    'category_id': 1,
                    'bbox': [x, y, w, h],
                    'area': area,
                    'iscrowd': 0,
                    'keypoints': metadata.get('landmarks', []),
                    'num_keypoints': len([k for k in metadata.get('landmarks', []) if k > 0]) // 3 if metadata.get('landmarks') else 0
                })

                self.stats['final_copied'] += 1

            except Exception as e:
                print(f"  Error copying {metadata['image_name']}: {e}")

        # Export COCO annotations
        coco_data = {
            'images': coco_images,
            'annotations': coco_annotations,
            'categories': [{
                'id': 1,
                'name': 'tshirt',
                'supercategory': 'clothing',
                'keypoints': [],
                'skeleton': []
            }]
        }

        annotations_path = self.output_dir / 'annotations.json'
        with open(annotations_path, 'w') as f:
            json.dump(coco_data, f, indent=2)

        print(f"\n✓ Saved annotations to {annotations_path}")

        # Print statistics
        print("\n" + "="*60)
        print("FILTERING STATISTICS")
        print("="*60)
        print(f"Total annotations processed: {self.stats['total_annotations']}")
        print(f"T-shirt items found: {self.stats['tshirt_items']}")
        print(f"Flat-lay t-shirts (scale=3): {self.stats['flatlay_items']}")
        if self.use_person_detection:
            print(f"Passed person detection: {self.stats['passed_person_check']}")
        print(f"Final images copied: {self.stats['final_copied']}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Filter DeepFashion2 for flat-lay t-shirts')
    parser.add_argument('--deepfashion_dir', type=str,
                        default='/home/celso/Downloads/train2020/train',
                        help='Path to DeepFashion2 train folder')
    parser.add_argument('--output_dir', type=str,
                        default='./deepfashion2_tshirts',
                        help='Output directory')
    parser.add_argument('--max_images', type=int, default=None,
                        help='Maximum number of images to extract')
    parser.add_argument('--no-person-detection', action='store_true',
                        help='Disable person detection (faster but less accurate)')
    parser.add_argument('--all-scales', action='store_true',
                        help='Include all scales, not just flat-lay (scale=3)')
    parser.add_argument('--person-threshold', type=float, default=0.5,
                        help='Confidence threshold for person detection (0.0-1.0)')

    args = parser.parse_args()

    # Create filter
    filter_obj = DeepFashion2TShirtFilter(
        deepfashion_dir=args.deepfashion_dir,
        output_dir=args.output_dir,
        use_person_detection=not args.no_person_detection,
        person_confidence_threshold=args.person_threshold,
        only_flatlay_scale=not args.all_scales
    )

    # Run filtering
    filter_obj.filter_dataset(max_images=args.max_images)

    print("\n✅ Filtering complete!")
    print(f"\nFiltered images saved to: {args.output_dir}/images/")
    print(f"Annotations saved to: {args.output_dir}/annotations.json")


if __name__ == '__main__':
    main()
