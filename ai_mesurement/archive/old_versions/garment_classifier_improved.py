#!/usr/bin/env python3
"""
Improved Garment Type Classifier
Better handles modern trouser styles and laid-flat garments
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


class ImprovedGarmentClassifier:
    """
    Improved classifier with better trouser detection
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    def classify(self, mask: np.ndarray, image: np.ndarray = None) -> Tuple[GarmentType, float, Dict]:
        """
        Classify garment type from segmentation mask
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
            print(f"\n🔍 Improved Garment Classification:")
            print(f"   Type: {garment_type.value}")
            print(f"   Confidence: {confidence:.1%}")
            print(f"   Aspect Ratio: {features['aspect_ratio']:.2f}")
            print(f"   Bottom Width Ratio: {features.get('bottom_width_ratio', 0):.2f}")
            print(f"   Top-Bottom Ratio: {features.get('top_bottom_ratio', 0):.2f}")

        return garment_type, confidence, features

    def _extract_features(self, contour: np.ndarray, mask: np.ndarray) -> Dict:
        """Extract improved shape features for classification"""

        # Bounding box
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 1

        # Area and perimeter
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        # Solidity
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area / hull_area if hull_area > 0 else 0

        # Improved leg detection for laid-flat trousers
        has_leg_indication = self._detect_trouser_characteristics(mask, x, y, w, h)

        # Check for waistband
        has_waistband = self._detect_waistband(mask, x, y, w, h)

        # Check symmetry
        symmetry = self._check_symmetry(mask, x, y, w, h)

        # Improved width analysis
        width_analysis = self._analyze_width_pattern(mask, x, y, w, h)

        features = {
            'aspect_ratio': aspect_ratio,
            'solidity': solidity,
            'has_leg_indication': has_leg_indication,
            'has_waistband': has_waistband,
            'symmetry': symmetry,
            'width_pattern': width_analysis['pattern'],
            'bottom_width_ratio': width_analysis['bottom_width_ratio'],
            'top_bottom_ratio': width_analysis['top_bottom_ratio'],
            'middle_narrowing': width_analysis['middle_narrowing'],
            'bbox': (x, y, w, h),
            'area': area
        }

        return features

    def _detect_trouser_characteristics(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """
        Improved trouser detection that works for laid-flat garments
        Looks for multiple indicators rather than just leg split
        """
        region = mask[y:y+h, x:x+w]
        if region.size == 0:
            return False

        # Check bottom third (more specific to trousers)
        bottom_third = region[2*h//3:, :]

        # 1. Check for significant vertical gap in bottom region
        middle_x = w // 2
        search_width = w // 15  # Narrower search area

        significant_gap_found = False
        for offset in range(-search_width, search_width + 1):
            check_x = middle_x + offset
            if 0 <= check_x < bottom_third.shape[1]:
                column = bottom_third[:, check_x]
                # Look for significant continuous gap (not just scattered pixels)
                if len(column) > 0:
                    # Find longest continuous gap
                    gap_runs = []
                    current_gap = 0
                    for pixel in column:
                        if pixel == 0:
                            current_gap += 1
                        else:
                            if current_gap > 0:
                                gap_runs.append(current_gap)
                            current_gap = 0
                    if current_gap > 0:
                        gap_runs.append(current_gap)

                    # Need a significant continuous gap (at least 20% of height)
                    if gap_runs and max(gap_runs) > len(column) * 0.2:
                        significant_gap_found = True
                        break

        # 2. Check for two distinct leg shapes in bottom half
        bottom_half = region[h//2:, :]
        if significant_gap_found:
            # Verify there are two separate masses
            left_mass = np.sum(bottom_half[:, :w//2] > 0)
            right_mass = np.sum(bottom_half[:, w//2:] > 0)

            if left_mass > 0 and right_mass > 0:
                balance = min(left_mass, right_mass) / max(left_mass, right_mass)
                if balance > 0.6:  # Both legs present
                    return True

        # 3. Check bottom edge for two distinct leg openings
        # More strict check - need clear separation
        bottom_rows = region[-5:, :]  # Check last 5 rows
        for row in bottom_rows:
            filled_regions = []
            in_region = False
            start = 0

            for i, pixel in enumerate(row):
                if pixel > 0 and not in_region:
                    in_region = True
                    start = i
                elif pixel == 0 and in_region:
                    in_region = False
                    filled_regions.append((start, i))

            if in_region:
                filled_regions.append((start, len(row)))

            # Check if we have exactly 2 distinct regions with significant gap
            if len(filled_regions) == 2:
                gap_start = filled_regions[0][1]
                gap_end = filled_regions[1][0]
                gap_size = gap_end - gap_start

                # Gap should be at least 10% of width
                if gap_size > w * 0.1:
                    return True

        return False

    def _detect_waistband(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
        """Detect if garment has distinct waistband"""

        # Check top 10% of garment
        top_region_height = max(int(h * 0.1), 5)
        top_region = mask[y:y+top_region_height, x:x+w]

        if top_region.size == 0:
            return False

        # Waistband has consistent width
        row_widths = []
        for row in top_region:
            width = np.sum(row > 0)
            if width > 0:
                row_widths.append(width)

        if len(row_widths) < 3:
            return False

        # Check consistency
        std_dev = np.std(row_widths)
        mean_width = np.mean(row_widths)

        if mean_width > 0:
            variation = std_dev / mean_width
            return variation < 0.15  # More lenient threshold

        return False

    def _check_symmetry(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> float:
        """Check vertical symmetry"""

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

    def _analyze_width_pattern(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Dict:
        """
        Improved width analysis that better handles laid-flat garments
        """
        region = mask[y:y+h, x:x+w]
        if region.size == 0:
            return {'pattern': 'unknown', 'bottom_width_ratio': 0,
                   'top_bottom_ratio': 0, 'middle_narrowing': False}

        # Sample more points for better analysis
        sample_heights = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
        widths = []

        for height_ratio in sample_heights:
            row_idx = int(h * height_ratio)
            if row_idx < region.shape[0]:
                row = region[row_idx]
                # Find actual garment width (excluding gaps)
                filled = row > 0
                if np.any(filled):
                    first = np.argmax(filled)
                    last = len(filled) - np.argmax(filled[::-1]) - 1
                    width = last - first + 1
                    widths.append(width)
                else:
                    widths.append(0)

        if len(widths) < 5:
            return {'pattern': 'unknown', 'bottom_width_ratio': 0,
                   'top_bottom_ratio': 0, 'middle_narrowing': False}

        # Analyze the pattern
        top_avg = np.mean(widths[:3]) if widths[:3] else 0
        middle_avg = np.mean(widths[3:7]) if widths[3:7] else 0
        bottom_avg = np.mean(widths[7:]) if widths[7:] else 0

        # Calculate ratios
        if bottom_avg > 0:
            bottom_width_ratio = bottom_avg / w
        else:
            bottom_width_ratio = 0

        if top_avg > 0 and bottom_avg > 0:
            top_bottom_ratio = top_avg / bottom_avg
        else:
            top_bottom_ratio = 1

        # Check for middle narrowing (common in trousers at knee)
        middle_narrowing = False
        if middle_avg > 0 and top_avg > 0 and bottom_avg > 0:
            if middle_avg < top_avg and middle_avg < bottom_avg * 1.1:
                middle_narrowing = True

        # Determine pattern
        if top_avg > bottom_avg * 1.2:
            pattern = 'narrowing'
        elif bottom_avg > top_avg * 1.2:
            pattern = 'widening'
        elif middle_narrowing:
            pattern = 'hourglass'  # Characteristic of trousers
        else:
            pattern = 'straight'

        return {
            'pattern': pattern,
            'bottom_width_ratio': bottom_width_ratio,
            'top_bottom_ratio': top_bottom_ratio,
            'middle_narrowing': middle_narrowing
        }

    def _classify_by_features(self, features: Dict) -> Tuple[GarmentType, float]:
        """
        Improved classification logic with better trouser detection
        """
        aspect_ratio = features['aspect_ratio']
        has_leg_indication = features['has_leg_indication']
        width_pattern = features['width_pattern']
        has_waistband = features.get('has_waistband', False)
        bottom_width_ratio = features.get('bottom_width_ratio', 0)
        top_bottom_ratio = features.get('top_bottom_ratio', 1)
        middle_narrowing = features.get('middle_narrowing', False)
        solidity = features['solidity']
        symmetry = features['symmetry']

        # Debug output
        print("\n🔍 Classification Features:")
        print(f"   Aspect Ratio: {aspect_ratio:.2f}")
        print(f"   Has Leg Indication: {has_leg_indication}")
        print(f"   Width Pattern: {width_pattern}")
        print(f"   Has Waistband: {has_waistband}")
        print(f"   Bottom Width Ratio: {bottom_width_ratio:.2f}")
        print(f"   Top-Bottom Ratio: {top_bottom_ratio:.2f}")
        print(f"   Middle Narrowing: {middle_narrowing}")
        print(f"   Solidity: {solidity:.2f}")
        print(f"   Symmetry: {symmetry:.2f}")

        # Score-based classification system
        trouser_score = 0
        shirt_score = 0
        dress_score = 0

        # TROUSER SCORING
        # Strong requirement: must have leg indication for high confidence
        if has_leg_indication:
            trouser_score += 50  # Strong indicator

            # Additional trouser features
            if 0.8 <= aspect_ratio <= 1.1:
                trouser_score += 20
            if has_waistband:
                trouser_score += 20
            if width_pattern in ['narrowing', 'hourglass']:
                trouser_score += 15
            if middle_narrowing:
                trouser_score += 15
            if 0.3 <= bottom_width_ratio <= 0.7:
                trouser_score += 10
            if top_bottom_ratio > 1.1:
                trouser_score += 10
        else:
            # Without leg indication, need very strong other evidence
            if has_waistband and middle_narrowing and 0.85 <= aspect_ratio <= 1.0:
                trouser_score += 40

        # SHIRT SCORING
        # T-shirts/shirts typically don't have leg splits
        if not has_leg_indication:
            shirt_score += 30  # Important negative indicator

            # T-shirt characteristics
            if 0.9 <= aspect_ratio <= 1.4:
                shirt_score += 25  # T-shirts can be squarish to wide
            if width_pattern in ['straight', 'widening']:
                shirt_score += 20  # T-shirts often widen at bottom (sleeves)
            if top_bottom_ratio < 1.2:
                shirt_score += 15  # More uniform width
            if bottom_width_ratio > 0.6:
                shirt_score += 15  # Wide bottom (sleeves spread)
            if symmetry > 0.85:
                shirt_score += 10  # T-shirts are usually symmetric

            # Strong t-shirt indicator: wider than tall
            if aspect_ratio > 1.15:
                shirt_score += 20

        # Additional shirt features even with some leg-like indication
        # (sleeves might be detected as legs)
        elif aspect_ratio > 1.2 and bottom_width_ratio > 0.7:
            shirt_score += 40  # Wide garment, likely shirt even if sleeves look like legs

        # DRESS SCORING
        if aspect_ratio < 0.8 and not has_leg_indication:
            dress_score += 50
            if width_pattern == 'widening':
                dress_score += 20

        # Determine classification based on scores
        scores = {
            'trouser': trouser_score,
            'shirt': shirt_score,
            'dress': dress_score
        }

        print(f"\n📊 Classification Scores:")
        print(f"   Trouser: {trouser_score}")
        print(f"   Shirt: {shirt_score}")
        print(f"   Dress: {dress_score}")

        max_score = max(scores.values())
        if max_score < 30:
            # No strong evidence for any type
            # Fall back to aspect ratio
            if aspect_ratio < 0.8:
                return GarmentType.DRESS, 0.55
            elif aspect_ratio > 1.2:
                return GarmentType.SHIRT, 0.60
            elif 0.85 <= aspect_ratio <= 1.1:
                # Only classify as trousers if there's some indication
                if has_leg_indication or has_waistband:
                    return GarmentType.TROUSERS, 0.55
                else:
                    return GarmentType.SHIRT, 0.55
            else:
                return GarmentType.UNKNOWN, 0.50

        # Return type with highest score
        if scores['trouser'] == max_score and scores['trouser'] >= 30:
            confidence = min(0.95, scores['trouser'] / 100)
            return GarmentType.TROUSERS, confidence
        elif scores['shirt'] == max_score and scores['shirt'] >= 30:
            confidence = min(0.95, scores['shirt'] / 100)
            return GarmentType.SHIRT, confidence
        elif scores['dress'] == max_score and scores['dress'] >= 30:
            confidence = min(0.95, scores['dress'] / 100)
            return GarmentType.DRESS, confidence

        # Shouldn't reach here, but fallback to unknown
        return GarmentType.UNKNOWN, 0.50


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