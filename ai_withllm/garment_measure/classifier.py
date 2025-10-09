#!/usr/bin/env python3
"""
Garment type classifier module with CLIP zero-shot integration.
Identifies garment category to determine measurement points.
"""

import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
import logging
import torch
from PIL import Image

logger = logging.getLogger(__name__)


class GarmentClassifier:
    """
    Classifies garment type based on shape and visual features.
    Provides heuristic baseline with CLIP zero-shot classification.
    """

    # Garment categories and their measurements
    CATEGORIES = {
        'tshirt': ['chest', 'hps_length', 'sleeve'],
        'hoodie': ['chest', 'hps_length', 'sleeve', 'hood_height'],
        'pants': ['waist', 'hip', 'inseam', 'outseam', 'thigh'],
        'shorts': ['waist', 'hip', 'inseam', 'outseam'],
        'skirt': ['waist', 'hip', 'length'],
        'dress': ['bust', 'waist', 'hip', 'length']
    }

    # CLIP labels to internal categories mapping
    CLIP_TO_CATEGORY = {
        't-shirt': 'tshirt',
        'shirt': 'tshirt',
        'hoodie': 'hoodie',
        'pants': 'pants',
        'trousers': 'pants',
        'shorts': 'shorts',
        'skirt': 'skirt',
        'dress': 'dress'
    }

    # Normalization to broader categories
    NORMALIZED_CATEGORIES = {
        'tshirt': 'top',
        'hoodie': 'top',
        'shirt': 'top',
        'pants': 'pants',
        'shorts': 'pants',
        'skirt': 'skirt',
        'dress': 'dress'
    }

    def __init__(self, model_path: Optional[str] = None, use_clip: bool = False,
                 device: Optional[str] = None, confidence_threshold: float = 0.40):
        """
        Initialize classifier.

        Args:
            model_path: Path to trained classifier model (future enhancement)
            use_clip: Whether to use CLIP for zero-shot classification
            device: Device for CLIP ('cuda', 'cpu', or None for auto-detect)
            confidence_threshold: Minimum confidence for CLIP predictions
        """
        self.model = None
        self.use_clip = use_clip
        self.confidence_threshold = confidence_threshold

        # Auto-detect device if not specified
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        self.clip_model = None
        self.clip_preprocess = None

        if model_path:
            self._load_model(model_path)
        elif use_clip:
            self._init_clip()

    def _load_model(self, model_path: str):
        """Load trained classification model (future enhancement)."""
        try:
            logger.info(f"Would load custom model from {model_path}")
            # Future: load ONNX or PyTorch model for classification
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def _init_clip(self):
        """Initialize CLIP for zero-shot classification."""
        try:
            import clip

            # Load CLIP model (ViT-B/32 is a good balance of speed and accuracy)
            model_name = "ViT-B/32"
            logger.info(f"Loading CLIP model: {model_name}")

            self.clip_model, self.clip_preprocess = clip.load(
                model_name,
                device=self.device,
                jit=False  # Disable JIT for better compatibility
            )

            self.clip_model.eval()

            # Prepare text embeddings for garment types
            self._prepare_text_embeddings()

            logger.info(f"CLIP model loaded successfully on {self.device}")

        except ImportError:
            logger.error("CLIP not installed. Install with: pip install git+https://github.com/openai/CLIP.git")
            self.use_clip = False
        except Exception as e:
            logger.error(f"Failed to initialize CLIP: {e}")
            self.use_clip = False

    def _prepare_text_embeddings(self):
        """Pre-compute text embeddings for garment types."""
        if not self.clip_model:
            return

        try:
            import clip

            # Define labels for zero-shot classification
            self.clip_labels = ["t-shirt", "hoodie", "shirt", "pants", "trousers", "shorts", "skirt", "dress"]

            # Create text prompts with context
            text_prompts = [f"a flat-lay photo of a {label}" for label in self.clip_labels]

            # Tokenize and encode text
            text_tokens = clip.tokenize(text_prompts).to(self.device)

            with torch.no_grad():
                self.text_features = self.clip_model.encode_text(text_tokens)
                self.text_features = self.text_features / self.text_features.norm(dim=-1, keepdim=True)

            logger.info(f"Prepared text embeddings for {len(self.clip_labels)} garment types")

        except Exception as e:
            logger.error(f"Failed to prepare text embeddings: {e}")
            self.use_clip = False

    def classify_heuristic(self, image: np.ndarray, mask: np.ndarray) -> Tuple[str, float, Dict]:
        """
        Classify garment using shape heuristics.

        Args:
            image: Original image
            mask: Binary segmentation mask

        Returns:
            category: Predicted garment type
            confidence: Confidence score (0-1)
            features: Extracted features used for classification
        """
        # Extract shape features from mask
        features = self._extract_shape_features(mask)

        # Simple heuristic rules based on aspect ratio and shape
        aspect_ratio = features['aspect_ratio']
        vertical_symmetry = features['vertical_symmetry']
        horizontal_thirds = features['horizontal_distribution']

        # Decision tree based on shape
        if aspect_ratio > 1.3:  # Taller than wide
            if horizontal_thirds[2] > horizontal_thirds[0] * 1.5:
                # Wider at bottom - likely skirt or dress
                if aspect_ratio > 2.0:
                    category = 'dress'
                else:
                    category = 'skirt'
                confidence = 0.7
            else:
                # Uniform or narrower at bottom - likely pants
                if aspect_ratio > 2.5:
                    category = 'pants'
                else:
                    category = 'shorts'
                confidence = 0.75
        else:  # Wider than tall or roughly square
            if vertical_symmetry > 0.85:
                # Highly symmetric - likely top garment
                if features.get('has_sleeves', False):
                    if features.get('has_hood', False):
                        category = 'hoodie'
                    else:
                        category = 'tshirt'
                    confidence = 0.8
                else:
                    category = 'tshirt'  # Tank top or sleeveless
                    confidence = 0.6
            else:
                # Asymmetric - could be folded or unusual garment
                category = 'tshirt'  # Default guess
                confidence = 0.4

        return category, confidence, features

    def _extract_shape_features(self, mask: np.ndarray) -> Dict:
        """
        Extract shape-based features from mask.

        Args:
            mask: Binary segmentation mask

        Returns:
            Dictionary of shape features
        """
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {'aspect_ratio': 1.0, 'vertical_symmetry': 0.0}

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)

        # Bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Basic shape metrics
        aspect_ratio = h / w if w > 0 else 1.0
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        solidity = area / (w * h) if w * h > 0 else 0

        # Vertical symmetry (compare left and right halves)
        mid_x = x + w // 2
        left_mask = mask.copy()
        left_mask[:, mid_x:] = 0
        right_mask = mask.copy()
        right_mask[:, :mid_x] = 0

        # Flip right half and compare
        right_flipped = cv2.flip(right_mask, 1)
        # Align the flipped right with left
        if right_flipped.shape[1] > mid_x:
            right_flipped = right_flipped[:, -mid_x:]
        elif right_flipped.shape[1] < mid_x:
            right_flipped = np.pad(right_flipped, ((0, 0), (mid_x - right_flipped.shape[1], 0)))

        left_area = np.sum(left_mask > 0)
        overlap = np.sum((left_mask > 0) & (right_flipped > 0))
        vertical_symmetry = 2 * overlap / (left_area + np.sum(right_mask > 0)) if left_area > 0 else 0

        # Horizontal distribution (divide into thirds)
        third_h = h // 3
        top_third = np.sum(mask[y:y+third_h, x:x+w] > 0)
        mid_third = np.sum(mask[y+third_h:y+2*third_h, x:x+w] > 0)
        bottom_third = np.sum(mask[y+2*third_h:y+h, x:x+w] > 0)
        total = top_third + mid_third + bottom_third

        horizontal_distribution = [
            top_third / total if total > 0 else 0,
            mid_third / total if total > 0 else 0,
            bottom_third / total if total > 0 else 0
        ]

        # Detect sleeves (protrusions on sides in upper portion)
        upper_half = mask[y:y+h//2, :]
        upper_contours, _ = cv2.findContours(upper_half, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        has_sleeves = False
        if upper_contours:
            hull = cv2.convexHull(upper_contours[0])
            hull_area = cv2.contourArea(hull)
            upper_area = np.sum(upper_half > 0)
            # If convex hull is much larger than actual area, likely has sleeves
            has_sleeves = (hull_area > upper_area * 1.3)

        # Detect hood (extra material at top)
        top_region = mask[max(0, y-20):y+h//4, x:x+w]
        top_density = np.sum(top_region > 0) / (top_region.size + 1e-6)
        has_hood = top_density > 0.7  # Dense top region might indicate hood

        features = {
            'aspect_ratio': aspect_ratio,
            'solidity': solidity,
            'vertical_symmetry': vertical_symmetry,
            'horizontal_distribution': horizontal_distribution,
            'has_sleeves': has_sleeves,
            'has_hood': has_hood,
            'bbox': [x, y, w, h],
            'area': area,
            'perimeter': perimeter
        }

        return features

    def classify_clip(self, image: np.ndarray, mask: Optional[np.ndarray] = None) -> Tuple[str, float, Dict]:
        """
        Classify using CLIP zero-shot classification.

        Args:
            image: Original image (BGR)
            mask: Optional mask to crop to garment region

        Returns:
            category: Predicted garment type
            confidence: Confidence score
            info: Additional information including all scores
        """
        if not self.use_clip or self.clip_model is None:
            logger.warning("CLIP not available, falling back to heuristic")
            return self.classify_heuristic(image, mask)

        try:
            # Crop to garment region if mask provided
            if mask is not None:
                # Find bounding box of mask
                ys, xs = np.where(mask > 0)
                if len(xs) > 0 and len(ys) > 0:
                    x_min, x_max = xs.min(), xs.max()
                    y_min, y_max = ys.min(), ys.max()

                    # Add small padding
                    pad = 10
                    y_min = max(0, y_min - pad)
                    y_max = min(image.shape[0], y_max + pad)
                    x_min = max(0, x_min - pad)
                    x_max = min(image.shape[1], x_max + pad)

                    cropped = image[y_min:y_max, x_min:x_max]
                else:
                    cropped = image
            else:
                cropped = image

            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image for CLIP preprocessing
            pil_image = Image.fromarray(rgb_image)

            # Preprocess image
            image_tensor = self.clip_preprocess(pil_image).unsqueeze(0).to(self.device)

            # Get image features
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

                # Compute similarities
                similarities = (100.0 * image_features @ self.text_features.T).softmax(dim=-1)
                similarities = similarities.squeeze(0).cpu().numpy()

            # Get best prediction
            best_idx = int(np.argmax(similarities))
            predicted_label = self.clip_labels[best_idx]
            confidence = float(similarities[best_idx])

            # Map CLIP label to internal category
            category = self.CLIP_TO_CATEGORY.get(predicted_label, predicted_label)

            # Create scores dictionary
            all_scores = {label: float(similarities[i])
                         for i, label in enumerate(self.clip_labels)}

            info = {
                'clip_scores': all_scores,
                'clip_label': predicted_label,
                'method': 'clip'
            }

            logger.info(f"CLIP classification: {predicted_label} -> {category} (conf: {confidence:.3f})")

            return category, confidence, info

        except Exception as e:
            logger.error(f"CLIP classification failed: {e}")
            return self.classify_heuristic(image, mask)

    def classify(self, image: np.ndarray, mask: np.ndarray) -> Tuple[str, float, Dict]:
        """
        Main classification method with automatic fallback.

        Args:
            image: Original image (BGR)
            mask: Binary segmentation mask

        Returns:
            category: Predicted garment type
            confidence: Confidence score (0-1)
            info: Additional information
        """
        # Try CLIP first if enabled
        if self.use_clip:
            category, confidence, info = self.classify_clip(image, mask)

            # Fall back to heuristic if confidence is too low
            if confidence < self.confidence_threshold:
                logger.info(f"CLIP confidence {confidence:.3f} below threshold {self.confidence_threshold}, "
                           f"falling back to heuristic")
                heur_category, heur_confidence, heur_info = self.classify_heuristic(image, mask)

                # Use heuristic result but keep CLIP scores for reference
                info.update({
                    'fallback': True,
                    'clip_category': category,
                    'clip_confidence': confidence,
                    'heuristic_features': heur_info,
                    'method': 'heuristic_fallback'
                })
                category = heur_category
                confidence = heur_confidence
        else:
            # Use heuristic directly
            category, confidence, info = self.classify_heuristic(image, mask)
            info['method'] = 'heuristic'

        # Add normalized category
        info['normalized_category'] = self.get_normalized_category(category)

        return category, confidence, info

    def get_normalized_category(self, category: str) -> str:
        """
        Get normalized category (top, pants, skirt, dress).

        Args:
            category: Specific garment type

        Returns:
            Normalized category string
        """
        return self.NORMALIZED_CATEGORIES.get(category, category)

    def get_measurement_points(self, category: str) -> List[str]:
        """
        Get required measurement points for a garment category.

        Args:
            category: Garment type

        Returns:
            List of measurement point names
        """
        return self.CATEGORIES.get(category, [])

    def validate_category(self, category: str, measurements: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate if measurements are reasonable for the category.

        Args:
            category: Garment type
            measurements: Dictionary of measurements in mm

        Returns:
            Validation results
        """
        # Expected ranges for adult garments (in mm)
        expected_ranges = {
            'tshirt': {
                'chest': (400, 700),
                'hps_length': (500, 850),
                'sleeve': (150, 250)
            },
            'hoodie': {
                'chest': (450, 750),
                'hps_length': (550, 900),
                'sleeve': (500, 700)
            },
            'pants': {
                'waist': (600, 1200),
                'hip': (700, 1400),
                'inseam': (600, 900),
                'outseam': (900, 1200)
            },
            'shorts': {
                'waist': (600, 1200),
                'hip': (700, 1400),
                'inseam': (100, 400),
                'outseam': (300, 600)
            },
            'skirt': {
                'waist': (600, 1000),
                'hip': (700, 1300),
                'length': (300, 1000)
            },
            'dress': {
                'bust': (700, 1200),
                'waist': (600, 1000),
                'hip': (800, 1300),
                'length': (700, 1500)
            }
        }

        if category not in expected_ranges:
            return {'valid': True, 'warnings': ['Unknown category']}

        ranges = expected_ranges[category]
        warnings = []
        errors = []

        for measure_name, value in measurements.items():
            if measure_name in ranges:
                min_val, max_val = ranges[measure_name]
                if value < min_val:
                    warnings.append(f"{measure_name} ({value:.0f}mm) below expected minimum ({min_val}mm)")
                elif value > max_val:
                    warnings.append(f"{measure_name} ({value:.0f}mm) above expected maximum ({max_val}mm)")

        valid = len(errors) == 0

        return {
            'valid': valid,
            'warnings': warnings,
            'errors': errors
        }


def main():
    """Test classifier on an image."""
    import argparse

    parser = argparse.ArgumentParser(description='Test garment classifier')
    parser.add_argument('--image', required=True, help='Input image')
    parser.add_argument('--mask', help='Segmentation mask')
    parser.add_argument('--clip', action='store_true', help='Use CLIP if available')
    parser.add_argument('--threshold', type=float, default=0.4,
                        help='Confidence threshold for CLIP')
    args = parser.parse_args()

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load {args.image}")
        return

    # Load or create mask
    if args.mask:
        mask = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)
    else:
        # Create simple threshold mask
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)

    # Initialize classifier
    classifier = GarmentClassifier(use_clip=args.clip, confidence_threshold=args.threshold)

    # Classify
    category, confidence, info = classifier.classify(image, mask)

    print(f"Classification result:")
    print(f"  Category: {category}")
    print(f"  Normalized: {info.get('normalized_category', category)}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Method: {info.get('method', 'unknown')}")
    print(f"  Required measurements: {classifier.get_measurement_points(category)}")

    if 'clip_scores' in info:
        print(f"\nCLIP scores:")
        for cat, score in sorted(info['clip_scores'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {cat}: {score:.3f}")

    if 'fallback' in info and info['fallback']:
        print(f"\n  Note: Fell back to heuristic (CLIP confidence {info['clip_confidence']:.3f} < {args.threshold})")

    if 'heuristic_features' in info:
        features = info.get('heuristic_features', {})
        print(f"\nShape features:")
        print(f"  Aspect ratio: {features.get('aspect_ratio', 0):.2f}")
        print(f"  Vertical symmetry: {features.get('vertical_symmetry', 0):.2f}")
        print(f"  Has sleeves: {features.get('has_sleeves', False)}")


if __name__ == '__main__':
    main()