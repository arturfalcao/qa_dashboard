#!/usr/bin/env python3
"""
Garment Type Classifier
Automatically detects the type of garment and returns appropriate measurement strategy
"""

import cv2
import numpy as np
from typing import Tuple, Dict, List
from enum import Enum


class GarmentType(Enum):
    """Types of garments the system can identify"""
    TROUSERS = "trousers"  # Jeans, pants, shorts
    SHIRT = "shirt"  # T-shirts, shirts, tops
    DRESS = "dress"  # Dresses, skirts
    JACKET = "jacket"  # Jackets, coats
    UNKNOWN = "unknown"


class GarmentClassifier:
    """
    Classifies garment type based on shape and aspect ratio analysis
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    def classify(self, mask: np.ndarray, image: np.ndarray = None) -> Tuple[GarmentType, float, Dict]:
        """
        Classify garment type from segmentation mask

        Args:
            mask: Binary mask of garment
            image: Optional original image for color analysis

        Returns:
            garment_type: Detected garment type
            confidence: Classification confidence (0-1)
            features: Dictionary of detected features
        """
        # Find contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return GarmentType.UNKNOWN, 0.0, {}

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)

        # Extract features
        features = self._extract_features(contour, mask)

        # Classify based on features
        garment_type, confidence = self._classify_by_features(features)

        if self.debug:
            print(f"\n🔍 Garment Classification:")
            print(f"   Type: {garment_type.value}")
            print(f"   Confidence: {confidence:.1%}")
            print(f"   Aspect Ratio: {features['aspect_ratio']:.2f}")
            print(f"   Leg Split Detected: {features.get('has_leg_split', False)}")

        return garment_type, confidence, features

    def _extract_features(self, contour: np.ndarray, mask: np.ndarray) -> Dict:
        """Extract shape features for classification"""

        # Bounding box
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 1

        # Area and perimeter
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        # Solidity (how solid vs hollow the shape is)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0

        # Check for leg split (characteristic of trousers)
        has_leg_split = self._detect_leg_split(mask, x, y, w, h)

        # Check for waist band (characteristic of trousers/skirts)
        has_waistband = self._detect_waistband(mask, x, y, w, h)

        # Check vertical symmetry
        symmetry = self._check_symmetry(mask, x, y, w, h)

        # Width variations (trousers narrow at bottom, shirts wider at top)
        width_profile = self._analyze_width_profile(mask, x, y, w, h)

        features = {
            'aspect_ratio': aspect_ratio,
            'solidity': solidity,
            'has_leg_split': has_leg_split,
            'has_waistband': has_waistband,
            'symmetry': symmetry,
            'width_profile': width_profile,
            'bbox': (x, y, w, h),
            'area': area
        }

        return features

    def _detect_leg_split(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """Detect if garment has leg split (trousers characteristic)"""

        # Check bottom third of garment
        bottom_third_y = y + int(h * 0.66)

        if bottom_third_y >= mask.shape[0]:
            return False

        # Look for vertical gap in bottom region
        bottom_region = mask[bottom_third_y:y+h, x:x+w]

        if bottom_region.size == 0:
            return False

        # Check middle column for gap
        middle_x = w // 2
        if middle_x < bottom_region.shape[1]:
            middle_column = bottom_region[:, middle_x]

            # Look for black pixels (gap) in middle
            black_pixels = np.sum(middle_column == 0)
            total_pixels = len(middle_column)

            # If more than 20% black pixels in middle column, likely leg split
            if total_pixels > 0:
                gap_ratio = black_pixels / total_pixels
                return gap_ratio > 0.2

        return False

    def _detect_waistband(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """Detect if garment has distinct waistband (trousers/skirt characteristic)"""

        # Check top 15% of garment
        top_region_height = int(h * 0.15)
        top_region = mask[y:y+top_region_height, x:x+w]

        if top_region.size == 0:
            return False

        # Waistband typically has consistent width
        row_widths = []
        for row in top_region:
            width = np.sum(row > 0)
            if width > 0:
                row_widths.append(width)

        if not row_widths:
            return False

        # Check consistency of widths
        std_dev = np.std(row_widths)
        mean_width = np.mean(row_widths)

        # Waistband has low variation
        if mean_width > 0:
            variation = std_dev / mean_width
            return variation < 0.1

        return False

    def _check_symmetry(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> float:
        """Check vertical symmetry (most garments are symmetric)"""

        region = mask[y:y+h, x:x+w]
        if region.size == 0:
            return 0.0

        # Flip horizontally
        flipped = cv2.flip(region, 1)

        # Compare
        intersection = cv2.bitwise_and(region, flipped)
        union = cv2.bitwise_or(region, flipped)

        intersection_area = np.sum(intersection > 0)
        union_area = np.sum(union > 0)

        if union_area > 0:
            symmetry = intersection_area / union_area
        else:
            symmetry = 0.0

        return symmetry

    def _analyze_width_profile(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> str:
        """Analyze how width changes from top to bottom"""

        region = mask[y:y+h, x:x+w]
        if region.size == 0:
            return "unknown"

        # Sample widths at different heights
        heights = [0.1, 0.3, 0.5, 0.7, 0.9]
        widths = []

        for height_ratio in heights:
            row_idx = int(h * height_ratio)
            if row_idx < region.shape[0]:
                row = region[row_idx]
                width = np.sum(row > 0)
                widths.append(width)

        if len(widths) < 3:
            return "unknown"

        # Analyze pattern
        top_width = widths[0]
        middle_width = widths[len(widths)//2]
        bottom_width = widths[-1]

        if top_width > middle_width > bottom_width:
            return "narrowing"  # Typical for trousers
        elif top_width < bottom_width:
            return "widening"  # Some dresses/skirts
        elif abs(top_width - bottom_width) < 0.1 * max(top_width, bottom_width):
            return "straight"  # Typical for shirts
        else:
            return "irregular"

    def _classify_by_features(self, features: Dict) -> Tuple[GarmentType, float]:
        """Classify garment based on extracted features"""

        aspect_ratio = features['aspect_ratio']
        has_leg_split = features['has_leg_split']
        width_profile = features['width_profile']
        solidity = features['solidity']

        # TROUSERS characteristics:
        # - Aspect ratio typically 0.7-1.1 (roughly square when laid flat)
        # - Often has leg split
        # - Narrowing width profile
        # - High solidity
        # Note: Modern trousers laid flat are wider than expected
        if 0.7 <= aspect_ratio <= 1.1:
            if has_leg_split:
                return GarmentType.TROUSERS, 0.95
            elif width_profile == "narrowing":
                return GarmentType.TROUSERS, 0.85
            elif features.get('has_waistband', False):
                return GarmentType.TROUSERS, 0.80
            else:
                # If aspect ratio is close to 0.9-1.0 and narrowing, likely trousers
                if 0.85 <= aspect_ratio <= 1.0 and width_profile in ["narrowing", "irregular"]:
                    return GarmentType.TROUSERS, 0.75

        # SHIRT characteristics:
        # - Aspect ratio typically 0.7-1.3
        # - No leg split
        # - Straight or slight narrowing profile
        # - May have sleeve protrusions
        if 0.7 <= aspect_ratio <= 1.4:
            if not has_leg_split and width_profile in ["straight", "irregular"]:
                return GarmentType.SHIRT, 0.85

        # DRESS characteristics:
        # - Aspect ratio typically 0.4-0.8 (similar to trousers but no split)
        # - No leg split
        # - May widen at bottom
        if 0.4 <= aspect_ratio <= 0.8:
            if not has_leg_split and width_profile in ["widening", "straight"]:
                return GarmentType.DRESS, 0.75

        # JACKET characteristics:
        # - Aspect ratio typically 0.9-1.5
        # - Complex shape (lower solidity)
        # - Irregular width profile
        if 0.9 <= aspect_ratio <= 1.5:
            if solidity < 0.85 and width_profile == "irregular":
                return GarmentType.JACKET, 0.70

        # Default fallback based on aspect ratio
        if aspect_ratio < 0.7:
            return GarmentType.TROUSERS, 0.60
        elif aspect_ratio > 1.2:
            return GarmentType.SHIRT, 0.60
        else:
            return GarmentType.UNKNOWN, 0.50


class MeasurementStrategy:
    """
    Defines measurement strategies for different garment types
    """

    @staticmethod
    def get_measurement_points(garment_type: GarmentType) -> Dict:
        """
        Get measurement strategy for garment type

        Returns dictionary with:
        - measurements: List of measurements to take
        - key_points: Key points to identify
        - instructions: Specific instructions
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