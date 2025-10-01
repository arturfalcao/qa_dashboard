#!/usr/bin/env python3
"""
CLIP-based Garment Type Classifier
Uses OpenAI's CLIP model for zero-shot garment classification
Much more accurate than rule-based heuristics
"""

import cv2
import numpy as np
from typing import Tuple, Dict
from enum import Enum
from PIL import Image
import warnings
warnings.filterwarnings('ignore')


class GarmentType(Enum):
    """Types of garments the system can identify"""
    TROUSERS = "trousers"  # Jeans, pants, shorts
    SHIRT = "shirt"  # T-shirts, shirts, tops
    DRESS = "dress"  # Dresses, skirts
    JACKET = "jacket"  # Jackets, coats
    UNKNOWN = "unknown"


class CLIPGarmentClassifier:
    """
    CLIP-based classifier using vision-language model for zero-shot classification
    Much more accurate than rule-based approach
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.model = None
        self.processor = None
        self._initialize_clip()

    def _initialize_clip(self):
        """Initialize CLIP model"""
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch

            print("🤖 Loading CLIP model (this may take a moment on first run)...")

            # Use a smaller, faster CLIP model
            model_name = "openai/clip-vit-base-patch32"

            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model = CLIPModel.from_pretrained(model_name)

            # Set to eval mode
            self.model.eval()

            # Check if CUDA is available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = self.model.to(self.device)

            print(f"✅ CLIP model loaded on {self.device.upper()}")

        except Exception as e:
            print(f"❌ Error loading CLIP model: {e}")
            print("   Falling back to rule-based classification")
            self.model = None

    def classify(self, mask: np.ndarray, image: np.ndarray = None) -> Tuple[GarmentType, float, Dict]:
        """
        Classify garment type using CLIP

        Args:
            mask: Segmentation mask (not used in CLIP, but kept for compatibility)
            image: Original image (BGR format from cv2)

        Returns:
            (GarmentType, confidence, features_dict)
        """
        if self.model is None or image is None:
            # Fallback to basic aspect ratio classification
            return self._fallback_classify(mask)

        try:
            import torch

            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Apply mask to focus on garment only
            if mask is not None:
                # Create 3-channel mask
                mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) if len(mask.shape) == 2 else mask
                # Apply mask to image
                masked_image = cv2.bitwise_and(image_rgb, mask_3ch)

                # Find bounding box of the garment
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    # Crop to garment with some padding
                    pad = 10
                    x1 = max(0, x - pad)
                    y1 = max(0, y - pad)
                    x2 = min(image_rgb.shape[1], x + w + pad)
                    y2 = min(image_rgb.shape[0], y + h + pad)
                    image_rgb = masked_image[y1:y2, x1:x2]

            # Convert to PIL Image
            pil_image = Image.fromarray(image_rgb)

            # Define text prompts for each garment type
            # More descriptive prompts lead to better accuracy
            text_prompts = [
                "a photo of trousers laid flat",
                "a photo of pants laid flat",
                "a photo of jeans laid flat",
                "a photo of a t-shirt laid flat",
                "a photo of a shirt laid flat",
                "a photo of a top laid flat",
                "a photo of a dress laid flat",
                "a photo of a skirt laid flat",
                "a photo of a jacket laid flat",
                "a photo of a coat laid flat"
            ]

            # Map prompts to garment types
            prompt_to_type = {
                0: GarmentType.TROUSERS,  # trousers
                1: GarmentType.TROUSERS,  # pants
                2: GarmentType.TROUSERS,  # jeans
                3: GarmentType.SHIRT,     # t-shirt
                4: GarmentType.SHIRT,     # shirt
                5: GarmentType.SHIRT,     # top
                6: GarmentType.DRESS,     # dress
                7: GarmentType.DRESS,     # skirt
                8: GarmentType.JACKET,    # jacket
                9: GarmentType.JACKET,    # coat
            }

            # Process inputs
            inputs = self.processor(
                text=text_prompts,
                images=pil_image,
                return_tensors="pt",
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)

            # Get probabilities for each garment type
            probs_np = probs.cpu().numpy()[0]

            # Aggregate probabilities by garment type
            type_probs = {}
            for idx, prob in enumerate(probs_np):
                garment_type = prompt_to_type[idx]
                if garment_type not in type_probs:
                    type_probs[garment_type] = 0
                type_probs[garment_type] += prob

            # Normalize probabilities
            total_prob = sum(type_probs.values())
            type_probs = {k: v/total_prob for k, v in type_probs.items()}

            # Get the most likely garment type
            best_type = max(type_probs.items(), key=lambda x: x[1])
            garment_type = best_type[0]
            confidence = float(best_type[1])

            if self.debug:
                print(f"\n🤖 CLIP Garment Classification:")
                print(f"   Type: {garment_type.value}")
                print(f"   Confidence: {confidence:.1%}")
                print(f"\n   All probabilities:")
                for gtype, prob in sorted(type_probs.items(), key=lambda x: x[1], reverse=True):
                    print(f"      {gtype.value}: {prob:.1%}")

            # Build features dict (for compatibility)
            features = {
                'clip_probabilities': type_probs,
                'method': 'CLIP',
            }

            return garment_type, confidence, features

        except Exception as e:
            print(f"⚠️ CLIP classification error: {e}")
            print("   Falling back to rule-based classification")
            return self._fallback_classify(mask)

    def _fallback_classify(self, mask: np.ndarray) -> Tuple[GarmentType, float, Dict]:
        """Fallback to simple aspect ratio-based classification"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return GarmentType.UNKNOWN, 0.0, {}

        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 1

        # Simple aspect ratio rules
        if aspect_ratio < 0.8:
            return GarmentType.DRESS, 0.6, {'method': 'fallback', 'aspect_ratio': aspect_ratio}
        elif aspect_ratio > 1.2:
            return GarmentType.SHIRT, 0.6, {'method': 'fallback', 'aspect_ratio': aspect_ratio}
        else:
            return GarmentType.TROUSERS, 0.5, {'method': 'fallback', 'aspect_ratio': aspect_ratio}


class MeasurementStrategy:
    """
    Defines measurement strategies for different garment types
    """

    @staticmethod
    def get_measurement_points(garment_type: GarmentType) -> Dict:
        """
        Get measurement strategy for garment type
        """

        strategies = {
            GarmentType.TROUSERS: {
                'measurements': [
                    'total_length',  # Waist to hem
                    'waist_width',  # Width at top
                    'hip_width',  # Width at widest point (usually upper third)
                    'thigh_width',  # Width at upper leg
                    'knee_width',  # Width at knee level
                    'hem_width',  # Width at bottom
                    'inseam',  # Crotch to hem (if detectable)
                    'rise',  # Waist to crotch
                ],
                'key_points': [
                    'waist_center',
                    'crotch_point',
                    'hem_left',
                    'hem_right',
                    'hip_left',
                    'hip_right'
                ],
                'size_reference': 'waist_width',
                'instructions': 'Measure length from waist to hem, width at multiple points'
            },

            GarmentType.SHIRT: {
                'measurements': [
                    'total_length',  # Shoulder/collar to hem
                    'chest_width',  # Width at chest level
                    'waist_width',  # Width at narrowest point
                    'hem_width',  # Width at bottom
                    'shoulder_width',  # If visible
                    'sleeve_length',  # If sleeves visible
                ],
                'key_points': [
                    'shoulder_left',
                    'shoulder_right',
                    'hem_left',
                    'hem_right',
                    'armpit_left',
                    'armpit_right'
                ],
                'size_reference': 'chest_width',
                'instructions': 'Measure length from shoulder to hem, width at chest'
            },

            GarmentType.DRESS: {
                'measurements': [
                    'total_length',  # Shoulder to hem
                    'bust_width',  # Width at bust level
                    'waist_width',  # Width at narrowest point
                    'hip_width',  # Width at hip level
                    'hem_width',  # Width at bottom
                ],
                'key_points': [
                    'shoulder_center',
                    'waist_left',
                    'waist_right',
                    'hem_left',
                    'hem_right'
                ],
                'size_reference': 'bust_width',
                'instructions': 'Measure length and widths at bust, waist, and hips'
            },

            GarmentType.JACKET: {
                'measurements': [
                    'total_length',  # Collar to hem
                    'chest_width',  # Width at chest
                    'shoulder_width',  # Shoulder to shoulder
                    'sleeve_length',  # If visible
                    'hem_width',  # Width at bottom
                ],
                'key_points': [
                    'collar_center',
                    'shoulder_left',
                    'shoulder_right',
                    'hem_left',
                    'hem_right'
                ],
                'size_reference': 'chest_width',
                'instructions': 'Measure length from collar to hem, chest width'
            },

            GarmentType.UNKNOWN: {
                'measurements': [
                    'height',  # Top to bottom
                    'width',  # Left to right at widest
                    'area',  # Total area
                ],
                'key_points': [
                    'top',
                    'bottom',
                    'left',
                    'right'
                ],
                'size_reference': 'width',
                'instructions': 'Basic height and width measurements'
            }
        }

        return strategies.get(garment_type, strategies[GarmentType.UNKNOWN])


# For backward compatibility, create an alias
ImprovedGarmentClassifier = CLIPGarmentClassifier


def main():
    """Test the CLIP classifier"""
    import argparse

    parser = argparse.ArgumentParser(description='Test CLIP-based garment classifier')
    parser.add_argument('-i', '--image', required=True, help='Path to garment image')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"❌ Cannot load image: {args.image}")
        return 1

    # Create classifier
    classifier = CLIPGarmentClassifier(debug=args.debug)

    # Create a simple mask (whole image for testing)
    mask = np.ones((image.shape[0], image.shape[1]), dtype=np.uint8) * 255

    # Classify
    print(f"\n📸 Analyzing: {args.image}")
    garment_type, confidence, features = classifier.classify(mask, image)

    print(f"\n✅ Classification Result:")
    print(f"   Type: {garment_type.value.upper()}")
    print(f"   Confidence: {confidence:.1%}")
    print(f"   Method: {features.get('method', 'CLIP')}")

    return 0


if __name__ == '__main__':
    exit(main())
