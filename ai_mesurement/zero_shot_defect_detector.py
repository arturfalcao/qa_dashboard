#!/usr/bin/env python3
"""
Zero-Shot Defect Detection using CLIP
No training required - uses pre-trained vision-language models
"""

import cv2
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ZeroShotDefect:
    """Information about a zero-shot detected defect"""
    type: str
    confidence: float
    area_cm2: float
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    severity: str
    description: str


class ZeroShotDefectDetector:
    """
    Zero-shot defect detection using CLIP
    Requires no training - works out of the box
    """

    def __init__(self, confidence_threshold: float = 0.9, debug: bool = False):
        """
        Initialize zero-shot detector

        Args:
            confidence_threshold: Minimum confidence to accept defect (0.9 = 90%)
            debug: Enable debug output
        """
        self.confidence_threshold = confidence_threshold
        self.debug = debug
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Load CLIP model (zero-shot capable) - using base model for speed
        print("🤖 Loading CLIP for zero-shot defect detection...")
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.model.to(self.device)
            self.model.eval()
            print(f"✅ Zero-shot detector ready (confidence threshold: {confidence_threshold*100:.0f}%)")
        except Exception as e:
            print(f"❌ Failed to load CLIP: {e}")
            raise

        # Comprehensive defect detection prompts
        # Positive prompts (defects)
        self.defect_prompts = [
            "a clear hole in the fabric",
            "a torn piece of clothing",
            "a rip in the garment",
            "damaged fabric with a hole",
            "a perforation in the textile",
            "a puncture in the material",
            "fabric with missing threads",
            "a tear in the cloth",
            "a cut in the fabric",
            "a worn through area showing hole"
        ]

        # Negative prompts (normal fabric)
        self.normal_prompts = [
            "perfect intact fabric",
            "normal clothing texture",
            "undamaged garment",
            "decorative button on fabric",
            "clothing design pattern",
            "fabric seam or stitching",
            "normal denim texture",
            "pocket on jeans",
            "belt loop on pants",
            "zipper on clothing"
        ]

        # Combined prompts for classification
        self.all_prompts = self.defect_prompts + self.normal_prompts
        self.defect_indices = list(range(len(self.defect_prompts)))
        self.normal_indices = list(range(len(self.defect_prompts), len(self.all_prompts)))

    def detect(self, image: np.ndarray, candidates: List[Tuple]) -> List[ZeroShotDefect]:
        """
        Zero-shot defect detection on candidate regions

        Args:
            image: Original image
            candidates: List of (contour, type) tuples

        Returns:
            List of high-confidence defects
        """
        if self.debug:
            print(f"\n🔍 ZERO-SHOT DETECTION")
            print(f"   Analyzing {len(candidates)} regions")
            print(f"   Confidence threshold: {self.confidence_threshold*100:.0f}%")

        validated_defects = []

        for i, (contour, original_type) in enumerate(candidates):
            # Extract region
            roi = self._extract_roi(image, contour)
            if roi is None:
                continue

            # Analyze with CLIP (zero-shot)
            is_defect, confidence, defect_type = self._analyze_zero_shot(roi)

            if is_defect and confidence >= self.confidence_threshold:
                # Calculate properties
                area_px = cv2.contourArea(contour)
                M = cv2.moments(contour)

                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = 0, 0

                x, y, w, h = cv2.boundingRect(contour)

                # Convert to cm² (assumes 50 pixels/cm default)
                pixels_per_cm = 50
                area_cm2 = area_px / (pixels_per_cm ** 2)

                severity = self._classify_severity(area_cm2)

                validated_defects.append(ZeroShotDefect(
                    type=defect_type,
                    confidence=confidence,
                    area_cm2=area_cm2,
                    center=(cx, cy),
                    bbox=(x, y, w, h),
                    severity=severity,
                    description=f"Zero-shot detected {defect_type} ({confidence*100:.0f}% confidence)"
                ))

        if self.debug:
            print(f"✅ Validated {len(validated_defects)} defects with ≥{self.confidence_threshold*100:.0f}% confidence")

        return validated_defects

    def _extract_roi(self, image: np.ndarray, contour: np.ndarray, size: int = 128) -> Optional[np.ndarray]:
        """Extract and prepare region of interest"""
        x, y, w, h = cv2.boundingRect(contour)

        # Add padding
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)

        if w <= 0 or h <= 0:
            return None

        roi = image[y:y+h, x:x+w]

        # Resize to standard size for CLIP
        if roi.size > 0:
            roi = cv2.resize(roi, (size, size))
            return roi
        return None

    def _analyze_zero_shot(self, roi: np.ndarray) -> Tuple[bool, float, str]:
        """
        Zero-shot analysis using CLIP

        Returns:
            (is_defect, confidence, defect_type)
        """
        try:
            # Convert to PIL
            pil_image = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))

            # Process with CLIP
            inputs = self.processor(
                text=self.all_prompts,
                images=pil_image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions (zero-shot)
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits_per_image[0]
                probs = torch.softmax(logits, dim=0).cpu().numpy()

            # Calculate defect vs normal scores
            defect_scores = probs[self.defect_indices]
            normal_scores = probs[self.normal_indices]

            # Get best defect match
            best_defect_idx = np.argmax(defect_scores)
            best_defect_score = defect_scores[best_defect_idx]
            best_defect_prompt = self.defect_prompts[best_defect_idx]

            # Get best normal match
            best_normal_score = np.max(normal_scores)

            # Calculate confidence
            # Average of top 3 defect scores vs top 3 normal scores
            top_defect_scores = np.sort(defect_scores)[-3:]
            top_normal_scores = np.sort(normal_scores)[-3:]

            avg_defect = np.mean(top_defect_scores)
            avg_normal = np.mean(top_normal_scores)

            # Calculate relative confidence
            if avg_defect + avg_normal > 0:
                confidence = avg_defect / (avg_defect + avg_normal)
            else:
                confidence = 0

            # Boost confidence if defect score is significantly higher
            if avg_defect > avg_normal * 1.5:
                confidence = min(1.0, confidence * 1.2)

            # Determine if it's a defect
            is_defect = confidence >= self.confidence_threshold

            # Extract defect type from prompt
            if "hole" in best_defect_prompt:
                defect_type = "hole"
            elif "tear" in best_defect_prompt or "torn" in best_defect_prompt:
                defect_type = "tear"
            elif "rip" in best_defect_prompt:
                defect_type = "rip"
            elif "worn" in best_defect_prompt:
                defect_type = "worn_area"
            else:
                defect_type = "defect"

            if self.debug and is_defect:
                print(f"   ✓ Defect found: {defect_type} ({confidence*100:.1f}%)")

            return is_defect, confidence, defect_type

        except Exception as e:
            if self.debug:
                print(f"   ✗ Analysis failed: {e}")
            return False, 0.0, "unknown"

    def _classify_severity(self, area_cm2: float) -> str:
        """Classify defect severity based on size"""
        if area_cm2 < 0.5:
            return 'minor'
        elif area_cm2 < 2.0:
            return 'moderate'
        elif area_cm2 < 5.0:
            return 'severe'
        else:
            return 'critical'

    def set_confidence(self, threshold: float):
        """
        Update confidence threshold

        Args:
            threshold: New threshold (0.0 to 1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        print(f"✅ Confidence threshold set to {self.confidence_threshold*100:.0f}%")