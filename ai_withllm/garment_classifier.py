#!/usr/bin/env python3
"""
Garment Category Classifier using YOLOv8 or CNN

This module provides accurate garment classification before landmark detection
to fix the misclassification issue where shirts are detected as vests.
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from pathlib import Path
import logging
from typing import Dict, Tuple, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GarmentClassifier:
    """
    Garment category classifier that provides accurate category detection
    before running landmark detection.

    Supports three approaches:
    1. YOLOv8 - Fast and accurate object detection
    2. ResNet50 - Image classification
    3. Rule-based - Using aspect ratio and color analysis
    """

    # DeepFashion2 categories
    CATEGORIES = [
        'short_sleeved_shirt',
        'long_sleeved_shirt',
        'short_sleeved_outwear',
        'long_sleeved_outwear',
        'vest',
        'sling',
        'shorts',
        'trousers',
        'skirt',
        'short_sleeved_dress',
        'long_sleeved_dress',
        'vest_dress',
        'sling_dress'
    ]

    # Simplified category groups for easier classification
    CATEGORY_GROUPS = {
        'shirt': ['short_sleeved_shirt', 'long_sleeved_shirt'],
        'outerwear': ['short_sleeved_outwear', 'long_sleeved_outwear'],
        'vest': ['vest'],
        'sling': ['sling'],
        'pants': ['shorts', 'trousers'],
        'skirt': ['skirt'],
        'dress': ['short_sleeved_dress', 'long_sleeved_dress', 'vest_dress', 'sling_dress']
    }

    def __init__(self, method: str = 'yolo'):
        """
        Initialize garment classifier

        Args:
            method: Classification method - 'yolo', 'resnet', or 'rule-based'
        """
        self.method = method
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        if method == 'yolo':
            self.model = self._init_yolo()
        elif method == 'resnet':
            self.model = self._init_resnet()
        else:
            self.model = None  # Rule-based doesn't need a model

        logger.info(f"Garment Classifier initialized using {method} method")

    def _init_yolo(self):
        """Initialize YOLOv8 model"""
        try:
            from ultralytics import YOLO

            # Check if we have a custom trained model
            custom_model_path = 'models/garment_classifier_yolo.pt'
            if Path(custom_model_path).exists():
                logger.info(f"Loading custom YOLOv8 model from {custom_model_path}")
                model = YOLO(custom_model_path)
            else:
                # Use pretrained YOLOv8n for general object detection
                logger.info("Using YOLOv8n pretrained model")
                model = YOLO('yolov8n.pt')

            return model
        except ImportError:
            logger.warning("ultralytics not installed. Install with: pip install ultralytics")
            logger.info("Falling back to rule-based classification")
            self.method = 'rule-based'
            return None

    def _init_resnet(self):
        """Initialize ResNet50 classifier"""
        # Load pretrained ResNet50
        model = models.resnet50(pretrained=True)

        # Replace final layer for our categories
        num_classes = len(self.CATEGORIES)
        model.fc = nn.Linear(model.fc.in_features, num_classes)

        # Load custom weights if available
        custom_weights = 'models/garment_classifier_resnet50.pth'
        if Path(custom_weights).exists():
            logger.info(f"Loading custom ResNet50 weights from {custom_weights}")
            model.load_state_dict(torch.load(custom_weights, map_location=self.device))
        else:
            logger.warning("Custom weights not found. Using random initialization for final layer.")

        model.to(self.device)
        model.eval()

        return model

    def classify(self, image: np.ndarray, return_confidence: bool = True) -> Dict:
        """
        Classify garment category

        Args:
            image: Input image (BGR format)
            return_confidence: Whether to return confidence scores

        Returns:
            Dictionary with category, confidence, and method
        """
        if self.method == 'yolo':
            return self._classify_yolo(image, return_confidence)
        elif self.method == 'resnet':
            return self._classify_resnet(image, return_confidence)
        else:
            return self._classify_rule_based(image, return_confidence)

    def _classify_yolo(self, image: np.ndarray, return_confidence: bool) -> Dict:
        """Classify using YOLOv8"""
        # Run inference
        results = self.model(image, verbose=False)

        # Get detections
        if len(results) > 0 and len(results[0].boxes) > 0:
            # Get the detection with highest confidence
            boxes = results[0].boxes
            confidences = boxes.conf.cpu().numpy()
            classes = boxes.cls.cpu().numpy()

            best_idx = np.argmax(confidences)
            class_id = int(classes[best_idx])
            confidence = float(confidences[best_idx])

            # Map YOLO class to garment category
            category = self._map_yolo_class_to_category(class_id, image)

            return {
                'category': category,
                'confidence': confidence if return_confidence else None,
                'method': 'yolo',
                'bbox': boxes.xyxy[best_idx].cpu().numpy().tolist()
            }

        # Fall back to rule-based if no detection
        logger.warning("YOLOv8 found no detections, falling back to rule-based")
        return self._classify_rule_based(image, return_confidence)

    def _classify_resnet(self, image: np.ndarray, return_confidence: bool) -> Dict:
        """Classify using ResNet50"""
        # Preprocess image
        transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        input_tensor = transform(image_rgb).unsqueeze(0).to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)

        category = self.CATEGORIES[predicted.item()]
        conf_value = confidence.item()

        return {
            'category': category,
            'confidence': conf_value if return_confidence else None,
            'method': 'resnet'
        }

    def _classify_rule_based(self, image: np.ndarray, return_confidence: bool) -> Dict:
        """
        Classify using rule-based approach with aspect ratio and structure analysis

        This is a fallback method that uses heuristics to determine garment category.
        """
        # Calculate aspect ratio based on garment pixels only (not background)
        garment_bbox = self._get_garment_bbox(image)
        if garment_bbox:
            bbox_height = garment_bbox[3] - garment_bbox[1]
            bbox_width = garment_bbox[2] - garment_bbox[0]
            aspect_ratio = bbox_height / bbox_width if bbox_width > 0 else 1.0
        else:
            # Fallback to image aspect ratio
            height, width = image.shape[:2]
            aspect_ratio = height / width

        # Detect structural features
        has_sleeves = self._detect_sleeves(image)
        has_collar = self._detect_collar(image)
        has_inseam = self._detect_inseam(image)
        top_opening_width = self._measure_top_opening(image)

        # Analyze garment structure with improved logic
        # Handle both vertical and horizontal orientations
        is_pants_vertical = aspect_ratio > 1.3 and has_inseam  # Tall with leg separation (vertical orientation)
        is_pants_horizontal = aspect_ratio < 0.9 and has_inseam  # Wide with leg separation (horizontal orientation)
        is_pants = is_pants_vertical or is_pants_horizontal

        is_skirt = aspect_ratio > 1.3 and not has_inseam  # Tall without leg separation
        is_dress = aspect_ratio > 1.1 and aspect_ratio <= 1.3 and top_opening_width > 0.5  # Medium height with wide top
        is_upper_body = aspect_ratio <= 1.1 and not is_pants_horizontal  # Wider than tall = likely upper body garment (unless horizontal pants)

        # Classify based on improved rules
        if is_pants:
            category = 'trousers'
            confidence = 0.85
        elif is_skirt:
            category = 'skirt'
            confidence = 0.75
        elif is_dress:
            if has_sleeves:
                sleeve_length = self._estimate_sleeve_length(image)
                if sleeve_length > 0.6:
                    category = 'long_sleeved_dress'
                else:
                    category = 'short_sleeved_dress'
            else:
                category = 'vest_dress'
            confidence = 0.70
        elif is_upper_body:
            if has_sleeves:
                # Check sleeve length by analyzing edge coverage
                sleeve_length = self._estimate_sleeve_length(image)
                if sleeve_length > 0.6:
                    category = 'long_sleeved_shirt'
                else:
                    category = 'short_sleeved_shirt'
                confidence = 0.80
            else:
                # No sleeves - could be vest or sling
                if has_collar:
                    category = 'vest'
                else:
                    category = 'sling'
                confidence = 0.70
        else:
            # Fallback - use aspect ratio
            if aspect_ratio > 1.5:
                category = 'trousers'
            else:
                category = 'short_sleeved_shirt'
            confidence = 0.60

        return {
            'category': category,
            'confidence': confidence if return_confidence else None,
            'method': 'rule-based',
            'features': {
                'aspect_ratio': aspect_ratio,
                'has_sleeves': has_sleeves,
                'has_collar': has_collar,
                'has_inseam': has_inseam,
                'is_pants': is_pants,
                'is_pants_horizontal': is_pants_horizontal,
                'is_upper_body': is_upper_body
            }
        }

    def _map_yolo_class_to_category(self, yolo_class: int, image: np.ndarray) -> str:
        """
        Map YOLO class to DeepFashion2 category

        YOLO detects general objects, so we need additional analysis
        """
        # YOLO class names (for YOLOv8 COCO)
        yolo_classes = {
            0: 'person',
            # ... other classes we don't need
        }

        # Since YOLO doesn't have specific garment classes,
        # we detect the garment region and apply rule-based classification
        return self._classify_rule_based(image, False)['category']

    def _detect_sleeves(self, image: np.ndarray) -> bool:
        """Detect presence of sleeves by analyzing edge regions"""
        height, width = image.shape[:2]

        # Check left and right edges (15% from each side)
        left_edge = image[:, :int(width * 0.15)]
        right_edge = image[:, int(width * 0.85):]

        # Convert to grayscale
        left_gray = cv2.cvtColor(left_edge, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_edge, cv2.COLOR_BGR2GRAY)

        # Check for non-background pixels (assuming background is white/light)
        left_coverage = np.sum(left_gray < 240) / left_gray.size
        right_coverage = np.sum(right_gray < 240) / right_gray.size

        # If both edges have significant coverage, sleeves likely present
        return left_coverage > 0.1 and right_coverage > 0.1

    def _detect_collar(self, image: np.ndarray) -> bool:
        """Detect presence of collar/neckline in top region"""
        height, width = image.shape[:2]

        # Check top 20% of image
        top_region = image[:int(height * 0.2), :]
        gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Look for horizontal/curved edges in center (collar line)
        center_edges = edges[:, int(width * 0.3):int(width * 0.7)]
        edge_density = np.sum(center_edges > 0) / center_edges.size

        return edge_density > 0.05

    def _detect_inseam(self, image: np.ndarray) -> bool:
        """
        Detect inseam (leg separation) for pants vs skirt

        An inseam is characterized by:
        1. A visible gap/separation in the BOTTOM 2/3 of the garment
        2. Significant width (not just a thin line like a button placket)
        3. Continuous vertical separation
        """
        height, width = image.shape[:2]

        # Check bottom 2/3 for vertical separation (not top - avoids button plackets)
        bottom_region = image[int(height * 0.33):, :]
        gray = cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY)

        # Look for gap in center region (not just a single column)
        center_left = width // 2 - 20
        center_right = width // 2 + 20
        center_region = gray[:, center_left:center_right]

        # Count background pixels (light pixels indicating gap)
        background_pixels = np.sum(center_region > 240)
        total_pixels = center_region.size

        # If >30% of center region is background, likely an inseam
        background_ratio = background_pixels / total_pixels if total_pixels > 0 else 0

        return background_ratio > 0.3

    def _estimate_sleeve_length(self, image: np.ndarray) -> float:
        """Estimate sleeve length as fraction of total height"""
        height, width = image.shape[:2]

        # Check left edge coverage across height
        left_edge = image[:, :int(width * 0.15)]
        gray = cv2.cvtColor(left_edge, cv2.COLOR_BGR2GRAY)

        # Find where sleeve ends (background becomes dominant)
        row_coverage = []
        for row in gray:
            coverage = np.sum(row < 240) / len(row)
            row_coverage.append(coverage)

        # Find last row with significant coverage
        sleeve_end = 0
        for i, coverage in enumerate(row_coverage):
            if coverage > 0.3:
                sleeve_end = i

        return sleeve_end / height if height > 0 else 0

    def _measure_top_opening(self, image: np.ndarray) -> float:
        """
        Measure top opening width as fraction of total width
        Helps distinguish dresses (wide top) from pants (narrow top)
        """
        height, width = image.shape[:2]

        # Check top 10% of image
        top_region = image[:int(height * 0.1), :]
        gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)

        # Find horizontal extent of garment in top region
        top_coverage = []
        for col in range(width):
            column = gray[:, col]
            coverage = np.sum(column < 240) / len(column)
            top_coverage.append(coverage > 0.3)

        # Find leftmost and rightmost covered columns
        covered_cols = [i for i, covered in enumerate(top_coverage) if covered]

        if not covered_cols:
            return 0.0

        opening_width = max(covered_cols) - min(covered_cols)
        return opening_width / width if width > 0 else 0

    def _get_garment_bbox(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Get bounding box of garment pixels (excluding background)

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) or None if no garment found
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Use Otsu's method for automatic thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Apply morphological operations to clean up noise
        kernel = np.ones((5, 5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Get the largest contour (assumed to be the garment)
        largest_contour = max(contours, key=cv2.contourArea)

        # Get bounding box of largest contour
        x, y, w, h = cv2.boundingRect(largest_contour)

        return (int(x), int(y), int(x + w), int(y + h))

    def classify_with_fallback(self, image: np.ndarray) -> Dict:
        """
        Classify with multiple methods and pick the most confident result

        Args:
            image: Input image

        Returns:
            Best classification result
        """
        results = []

        # Try YOLO if available
        if self.method == 'yolo' and self.model is not None:
            try:
                results.append(self._classify_yolo(image, True))
            except Exception as e:
                logger.warning(f"YOLO classification failed: {e}")

        # Always try rule-based as fallback
        results.append(self._classify_rule_based(image, True))

        # Pick result with highest confidence
        best_result = max(results, key=lambda x: x.get('confidence', 0))

        logger.info(f"Classified as {best_result['category']} "
                   f"(confidence: {best_result['confidence']:.2f}, "
                   f"method: {best_result['method']})")

        return best_result


def main():
    """Test garment classifier"""
    import argparse

    parser = argparse.ArgumentParser(description="Garment Category Classifier")
    parser.add_argument("image", help="Input image path")
    parser.add_argument("--method", choices=['yolo', 'resnet', 'rule-based'],
                       default='rule-based',
                       help="Classification method")
    parser.add_argument("--output", help="Output JSON path")

    args = parser.parse_args()

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"Could not load image: {args.image}")
        return

    # Initialize classifier
    classifier = GarmentClassifier(method=args.method)

    # Classify
    result = classifier.classify(image, return_confidence=True)

    # Print results
    print("\n" + "="*60)
    print("GARMENT CLASSIFICATION RESULT")
    print("="*60)
    print(f"Category: {result['category']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Method: {result['method']}")

    if 'features' in result:
        print("\nFeatures:")
        for key, value in result['features'].items():
            print(f"  {key}: {value}")

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
