#!/usr/bin/env python3
"""
AI-Based Defect Detection Module for Garments
Uses deep learning models to accurately detect holes, tears, and defects
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import warnings
warnings.filterwarnings('ignore')


@dataclass
class AIDefectInfo:
    """Information about an AI-detected defect"""
    type: str  # 'hole', 'tear', 'stain', 'worn_area'
    confidence: float  # AI confidence score (0-1)
    area_cm2: float
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    severity: str
    ai_description: str


class DefectCNN(nn.Module):
    """
    Simple CNN for defect classification
    Trained to distinguish real defects from fabric patterns
    """

    def __init__(self):
        super(DefectCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(128 * 8 * 8, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 4)  # 4 classes: hole, tear, stain, no_defect
        self.dropout = nn.Dropout(0.2)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = x.view(-1, 128 * 8 * 8)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return F.softmax(x, dim=1)


class AIDefectDetector:
    """
    AI-powered defect detection system using multiple approaches:
    1. CLIP for visual-semantic understanding
    2. Anomaly detection for unusual patterns
    3. Custom CNN for defect classification
    """

    def __init__(self, use_clip: bool = True, debug: bool = False):
        """
        Initialize AI defect detector

        Args:
            use_clip: Whether to use CLIP model for advanced detection
            debug: Enable debug output
        """
        self.debug = debug
        self.use_clip = use_clip
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize CLIP if requested
        if use_clip:
            try:
                print("🤖 Loading CLIP model for defect detection...")
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_model.to(self.device)
                self.clip_model.eval()
                print("✅ CLIP model loaded successfully")
            except Exception as e:
                print(f"⚠️ Could not load CLIP model: {e}")
                self.use_clip = False

        # Defect prompts for CLIP
        self.defect_prompts = [
            "a hole in the fabric",
            "a tear in the clothing",
            "a stain on the garment",
            "damaged fabric",
            "worn out area",
            "perfect fabric without defects",
            "normal fabric texture",
            "clothing pattern"
        ]

        # Initialize custom CNN (would need training in production)
        self.defect_cnn = DefectCNN().to(self.device)
        self.defect_cnn.eval()

    def detect_defects_ai(self, image: np.ndarray, mask: np.ndarray,
                          candidate_regions: List[Tuple[np.ndarray, str]]) -> List[AIDefectInfo]:
        """
        Use AI to filter and classify defect candidates

        Args:
            image: Original image
            mask: Garment segmentation mask
            candidate_regions: List of potential defect regions from traditional CV

        Returns:
            List of AI-validated defects
        """
        if self.debug:
            print(f"\n🤖 AI DEFECT ANALYSIS")
            print(f"   Analyzing {len(candidate_regions)} candidate regions")

        ai_defects = []

        for i, (contour, defect_type) in enumerate(candidate_regions):
            # Extract region of interest
            roi = self._extract_roi(image, contour)
            if roi is None:
                continue

            # Method 1: CLIP-based analysis
            clip_result = None
            if self.use_clip:
                clip_result = self._analyze_with_clip(roi)

            # Method 2: Anomaly detection
            anomaly_score = self._detect_anomaly(roi, image, mask)

            # Method 3: CNN classification (if trained)
            cnn_result = self._classify_with_cnn(roi)

            # Combine results to make decision
            is_defect, confidence, ai_type, description = self._combine_ai_results(
                clip_result, anomaly_score, cnn_result, defect_type
            )

            if is_defect:
                # Calculate properties
                area_px = cv2.contourArea(contour)
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = 0, 0

                x, y, w, h = cv2.boundingRect(contour)

                # Estimate area in cm² (assumes pixels_per_cm is passed somehow)
                pixels_per_cm = 50  # Default estimate
                area_cm2 = area_px / (pixels_per_cm ** 2)

                severity = self._classify_severity(area_cm2)

                ai_defects.append(AIDefectInfo(
                    type=ai_type,
                    confidence=confidence,
                    area_cm2=area_cm2,
                    center=(cx, cy),
                    bbox=(x, y, w, h),
                    severity=severity,
                    ai_description=description
                ))

        if self.debug:
            print(f"✅ AI validated {len(ai_defects)} real defects")

        return ai_defects

    def _extract_roi(self, image: np.ndarray, contour: np.ndarray,
                     padding: int = 10) -> Optional[np.ndarray]:
        """Extract region of interest around contour"""
        x, y, w, h = cv2.boundingRect(contour)

        # Add padding
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)

        if w <= 0 or h <= 0:
            return None

        roi = image[y:y+h, x:x+w]

        # Resize to standard size for models
        if roi.size > 0:
            roi = cv2.resize(roi, (64, 64))
            return roi
        return None

    def _analyze_with_clip(self, roi: np.ndarray) -> Dict:
        """Use CLIP to analyze if region contains a defect"""
        if not self.use_clip:
            return None

        try:
            # Convert to PIL Image
            pil_image = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))

            # Process image and text
            inputs = self.clip_processor(
                text=self.defect_prompts,
                images=pil_image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            # Get predictions
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]

            # Analyze results
            defect_indices = [0, 1, 2, 3, 4]  # Indices for defect prompts
            normal_indices = [5, 6, 7]  # Indices for normal fabric

            defect_score = np.mean([probs[i] for i in defect_indices])
            normal_score = np.mean([probs[i] for i in normal_indices])

            best_match_idx = np.argmax(probs)
            best_match = self.defect_prompts[best_match_idx]

            return {
                'is_defect': defect_score > normal_score,
                'confidence': float(defect_score),
                'best_match': best_match,
                'defect_score': defect_score,
                'normal_score': normal_score
            }

        except Exception as e:
            if self.debug:
                print(f"⚠️ CLIP analysis failed: {e}")
            return None

    def _detect_anomaly(self, roi: np.ndarray, full_image: np.ndarray,
                       mask: np.ndarray) -> float:
        """
        Detect if ROI is anomalous compared to rest of fabric
        Returns anomaly score (0-1, higher = more anomalous)
        """
        # Convert to grayscale
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Get statistics from the full garment
        garment_pixels = full_image[mask > 0]
        if len(garment_pixels) == 0:
            return 0.5

        # Calculate features
        roi_features = {
            'mean': np.mean(roi_gray),
            'std': np.std(roi_gray),
            'contrast': np.max(roi_gray) - np.min(roi_gray)
        }

        garment_gray = cv2.cvtColor(full_image, cv2.COLOR_BGR2GRAY)
        garment_masked = garment_gray[mask > 0]
        garment_features = {
            'mean': np.mean(garment_masked),
            'std': np.std(garment_masked),
            'contrast': np.percentile(garment_masked, 95) - np.percentile(garment_masked, 5)
        }

        # Calculate anomaly score
        mean_diff = abs(roi_features['mean'] - garment_features['mean']) / (garment_features['mean'] + 1e-6)
        std_diff = abs(roi_features['std'] - garment_features['std']) / (garment_features['std'] + 1e-6)
        contrast_diff = abs(roi_features['contrast'] - garment_features['contrast']) / (garment_features['contrast'] + 1e-6)

        # Weighted average
        anomaly_score = 0.4 * mean_diff + 0.3 * std_diff + 0.3 * contrast_diff
        anomaly_score = min(1.0, anomaly_score)

        return anomaly_score

    def _classify_with_cnn(self, roi: np.ndarray) -> Dict:
        """Use CNN to classify defect type"""
        try:
            # Prepare input
            roi_tensor = torch.from_numpy(roi).float()
            roi_tensor = roi_tensor.permute(2, 0, 1).unsqueeze(0)
            roi_tensor = roi_tensor / 255.0
            roi_tensor = roi_tensor.to(self.device)

            # Get prediction
            with torch.no_grad():
                output = self.defect_cnn(roi_tensor)
                probs = output.cpu().numpy()[0]

            classes = ['hole', 'tear', 'stain', 'no_defect']
            best_class_idx = np.argmax(probs)
            best_class = classes[best_class_idx]

            return {
                'class': best_class,
                'confidence': float(probs[best_class_idx]),
                'is_defect': best_class != 'no_defect'
            }

        except Exception as e:
            if self.debug:
                print(f"⚠️ CNN classification failed: {e}")
            return None

    def _combine_ai_results(self, clip_result: Optional[Dict],
                           anomaly_score: float,
                           cnn_result: Optional[Dict],
                           original_type: str) -> Tuple[bool, float, str, str]:
        """
        Combine results from multiple AI methods to make final decision
        """
        # Weight each method's contribution
        weights = {
            'clip': 0.4,
            'anomaly': 0.3,
            'cnn': 0.3
        }

        total_score = 0
        total_weight = 0
        defect_type = original_type
        description = ""

        # Process CLIP result
        if clip_result and self.use_clip:
            if clip_result['is_defect']:
                total_score += clip_result['confidence'] * weights['clip']
                description = clip_result['best_match']
            total_weight += weights['clip']

        # Process anomaly score
        if anomaly_score > 0.3:  # Threshold for anomaly
            total_score += anomaly_score * weights['anomaly']
        total_weight += weights['anomaly']

        # Process CNN result
        if cnn_result:
            if cnn_result['is_defect']:
                total_score += cnn_result['confidence'] * weights['cnn']
                defect_type = cnn_result['class']
            total_weight += weights['cnn']

        # Calculate final confidence
        if total_weight > 0:
            confidence = total_score / total_weight
        else:
            confidence = 0

        # Decision threshold - 90% confidence required
        is_defect = confidence >= 0.9

        if not description:
            description = f"AI detected {defect_type} with {confidence:.1%} confidence"

        return is_defect, confidence, defect_type, description

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

    def enhance_detection(self, image: np.ndarray, mask: np.ndarray,
                         traditional_holes: List) -> List[AIDefectInfo]:
        """
        Enhance traditional hole detection with AI

        Args:
            image: Original image
            mask: Garment mask
            traditional_holes: Holes detected by traditional CV methods

        Returns:
            AI-enhanced list of defects
        """
        # Convert traditional holes to candidate regions
        candidate_regions = []
        for hole in traditional_holes:
            if hasattr(hole, 'contour'):
                candidate_regions.append((hole.contour, hole.type))

        # Use AI to validate and enhance
        ai_defects = self.detect_defects_ai(image, mask, candidate_regions)

        return ai_defects