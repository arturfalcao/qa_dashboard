#!/usr/bin/env python3
"""
Focused Landmark Extractor for Garment Measurements

This module extracts only the critical measurement landmarks for garments,
focusing on key points like hem, chest, shoulder, collar, sleeves, and cuffs.
Designed for accurate garment measurements with minimal landmarks.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from scipy.spatial.distance import cdist
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MeasurementPoint:
    """Represents a key measurement point on a garment"""
    name: str  # e.g., "shoulder_left", "hem_center"
    position: Tuple[int, int]
    confidence: float
    type: str  # "hem", "chest", "shoulder", "collar", "sleeve", "cuff"
    side: str  # "left", "right", "center"
    pair_name: Optional[str] = None  # Name of corresponding point for width measurements


class FocusedLandmarkExtractor:
    """
    Extracts only the key measurement landmarks from detected points
    """

    # SVIP-Lab DeepFashion2 landmark indices for different garment types
    # Based on the model's 294 landmarks structure
    LANDMARK_MAPPINGS = {
        'short_sleeved_shirt': {
            'collar': [0, 1, 2],  # Neckline points
            'shoulder_left': [5, 6],
            'shoulder_right': [10, 11],
            'sleeve_left': [7, 8],  # Short sleeve opening
            'sleeve_right': [12, 13],
            'chest_left': [6, 7],  # Armpit area
            'chest_right': [11, 12],
            'hem_left': [14, 15],
            'hem_center': [16],
            'hem_right': [17, 18]
        },
        'long_sleeved_shirt': {
            'collar': [25, 26, 27],  # Neckline
            'shoulder_left': [30, 31],
            'shoulder_right': [35, 36],
            'sleeve_left': [32, 33],  # Sleeve attachment
            'sleeve_right': [37, 38],
            'cuff_left': [33, 34],  # Wrist area
            'cuff_right': [38, 39],
            'chest_left': [31, 32],
            'chest_right': [36, 37],
            'hem_left': [40, 41],
            'hem_center': [42],
            'hem_right': [43, 44]
        },
        'vest': {
            'collar': [128, 129, 130],  # Neckline
            'shoulder_left': [131, 132],
            'shoulder_right': [135, 136],
            'armhole_left': [132, 133],  # No sleeves, just armholes
            'armhole_right': [136, 137],
            'chest_left': [133],
            'chest_right': [137],
            'hem_left': [138, 139],
            'hem_center': [140],
            'hem_right': [141, 142]
        }
    }

    def __init__(self,
                 min_confidence: float = 0.3,
                 use_edge_correction: bool = True,
                 symmetry_threshold: float = 100.0):
        """
        Initialize the focused landmark extractor

        Args:
            min_confidence: Minimum confidence for landmark selection
            use_edge_correction: Whether to apply edge correction
            symmetry_threshold: Maximum pixel difference for symmetric pairs
        """
        self.min_confidence = min_confidence
        self.use_edge_correction = use_edge_correction
        self.symmetry_threshold = symmetry_threshold

    def extract_key_landmarks(self,
                             all_landmarks: List[Tuple[int, int]],
                             confidences: List[float],
                             category: str,
                             image_shape: Optional[Tuple] = None) -> Dict[str, Any]:
        """
        Extract only the key measurement landmarks from all detected landmarks

        Args:
            all_landmarks: List of all detected landmarks
            confidences: Confidence scores for each landmark
            category: Garment category (e.g., 'vest', 'short_sleeved_shirt')
            image_shape: Optional image shape for validation

        Returns:
            Dictionary with key measurement points and pairs
        """
        results = {
            'key_points': {},
            'measurement_pairs': [],
            'measurements': {},
            'category': category,
            'quality_score': 0.0
        }

        # Get the appropriate mapping for this category
        mapping = self._get_landmark_mapping(category)
        if not mapping:
            logger.warning(f"No mapping found for category: {category}")
            return results

        # Extract key points based on mapping
        key_points = {}
        for point_name, indices in mapping.items():
            point = self._extract_single_point(
                point_name,
                indices,
                all_landmarks,
                confidences
            )
            if point:
                key_points[point_name] = point

        results['key_points'] = key_points

        # Identify measurement pairs
        results['measurement_pairs'] = self._identify_pairs(key_points, image_shape)

        # Calculate measurements from pairs
        results['measurements'] = self._calculate_measurements(results['measurement_pairs'])

        # Assess quality of extracted landmarks
        results['quality_score'] = self._assess_quality(key_points, results['measurement_pairs'])

        return results

    def _get_landmark_mapping(self, category: str) -> Dict:
        """
        Get the landmark mapping for a category, with fallbacks
        """
        # Direct mapping
        if category in self.LANDMARK_MAPPINGS:
            return self.LANDMARK_MAPPINGS[category]

        # Try to find a similar category
        category_lower = category.lower()

        # Check for shirt variants
        if 'shirt' in category_lower:
            if 'long' in category_lower:
                return self.LANDMARK_MAPPINGS['long_sleeved_shirt']
            else:
                return self.LANDMARK_MAPPINGS['short_sleeved_shirt']

        # Check for vest
        if 'vest' in category_lower:
            return self.LANDMARK_MAPPINGS['vest']

        # Default to short sleeved shirt for tops
        if category_lower in ['top', 'blouse', 't-shirt', 'tshirt']:
            return self.LANDMARK_MAPPINGS['short_sleeved_shirt']

        # If no mapping found, create a generic one
        return self._create_generic_mapping(category)

    def _create_generic_mapping(self, category: str) -> Dict:
        """
        Create a generic mapping for unknown categories
        """
        # Use heuristics to identify key points
        # This assumes the first ~50 landmarks are for upper garments
        return {
            'collar': [0, 1, 2],
            'shoulder_left': [5, 6],
            'shoulder_right': [10, 11],
            'chest_left': [7, 8],
            'chest_right': [12, 13],
            'hem_left': [15, 16],
            'hem_center': [17],
            'hem_right': [18, 19]
        }

    def _extract_single_point(self,
                             point_name: str,
                             indices: List[int],
                             all_landmarks: List,
                             confidences: List) -> Optional[MeasurementPoint]:
        """
        Extract a single measurement point from multiple candidate indices
        """
        valid_candidates = []

        for idx in indices:
            if idx < len(all_landmarks) and idx < len(confidences):
                landmark = all_landmarks[idx]
                confidence = confidences[idx]

                if landmark is not None and confidence >= self.min_confidence:
                    valid_candidates.append({
                        'position': landmark,
                        'confidence': confidence,
                        'index': idx
                    })

        if not valid_candidates:
            return None

        # Choose the best candidate (highest confidence)
        best = max(valid_candidates, key=lambda x: x['confidence'])

        # Determine type and side from name
        point_type = self._get_point_type(point_name)
        side = self._get_point_side(point_name)

        return MeasurementPoint(
            name=point_name,
            position=best['position'],
            confidence=best['confidence'],
            type=point_type,
            side=side
        )

    def _get_point_type(self, point_name: str) -> str:
        """Extract point type from name"""
        for type_name in ['hem', 'chest', 'shoulder', 'collar', 'sleeve', 'cuff', 'armhole']:
            if type_name in point_name.lower():
                return type_name
        return 'unknown'

    def _get_point_side(self, point_name: str) -> str:
        """Extract side from point name"""
        if 'left' in point_name.lower():
            return 'left'
        elif 'right' in point_name.lower():
            return 'right'
        elif 'center' in point_name.lower():
            return 'center'
        else:
            return 'unknown'

    def _identify_pairs(self,
                       key_points: Dict[str, MeasurementPoint],
                       image_shape: Optional[Tuple]) -> List[Tuple[MeasurementPoint, MeasurementPoint]]:
        """
        Identify left-right pairs for width measurements
        """
        pairs = []

        # Define pairing rules
        pair_definitions = [
            ('shoulder_left', 'shoulder_right', 'shoulder_width'),
            ('chest_left', 'chest_right', 'chest_width'),
            ('hem_left', 'hem_right', 'hem_width'),
            ('cuff_left', 'cuff_right', 'cuff_width'),
            ('sleeve_left', 'sleeve_right', 'sleeve_span'),
            ('armhole_left', 'armhole_right', 'armhole_span')
        ]

        for left_name, right_name, measurement_name in pair_definitions:
            if left_name in key_points and right_name in key_points:
                left_point = key_points[left_name]
                right_point = key_points[right_name]

                # Validate pair symmetry if image shape provided
                if image_shape and self._validate_pair_symmetry(left_point, right_point, image_shape):
                    left_point.pair_name = right_name
                    right_point.pair_name = left_name
                    pairs.append((left_point, right_point, measurement_name))

        return pairs

    def _validate_pair_symmetry(self,
                               left: MeasurementPoint,
                               right: MeasurementPoint,
                               image_shape: Tuple) -> bool:
        """
        Validate that a pair is reasonably symmetric
        """
        # Check vertical alignment (should be at similar height)
        y_diff = abs(left.position[1] - right.position[1])

        # Check horizontal positioning (left should be on left side, right on right)
        image_center_x = image_shape[1] / 2
        left_on_left = left.position[0] < image_center_x
        right_on_right = right.position[0] > image_center_x

        return y_diff < self.symmetry_threshold and left_on_left and right_on_right

    def _calculate_measurements(self,
                              pairs: List[Tuple[MeasurementPoint, MeasurementPoint, str]]) -> Dict[str, float]:
        """
        Calculate measurements from identified pairs
        """
        measurements = {}

        for left, right, measurement_name in pairs:
            distance = np.sqrt(
                (right.position[0] - left.position[0])**2 +
                (right.position[1] - left.position[1])**2
            )
            measurements[measurement_name] = distance

        # Add vertical measurements if we have the points
        # This would need to be expanded based on available points

        return measurements

    def _assess_quality(self,
                       key_points: Dict[str, MeasurementPoint],
                       pairs: List) -> float:
        """
        Assess the quality of extracted landmarks
        """
        # Quality factors:
        # 1. Completeness: How many expected points were found
        # 2. Confidence: Average confidence of found points
        # 3. Symmetry: How well pairs align

        expected_points = ['shoulder_left', 'shoulder_right',
                          'chest_left', 'chest_right',
                          'hem_left', 'hem_right']

        found_count = sum(1 for p in expected_points if p in key_points)
        completeness = found_count / len(expected_points)

        if key_points:
            avg_confidence = np.mean([p.confidence for p in key_points.values()])
        else:
            avg_confidence = 0

        # Combine scores
        quality_score = (completeness * 0.5 + avg_confidence * 0.5)

        return quality_score

    def visualize_key_landmarks(self,
                               image: np.ndarray,
                               extraction_results: Dict,
                               show_pairs: bool = True,
                               show_labels: bool = True) -> np.ndarray:
        """
        Visualize only the key measurement landmarks
        """
        vis = image.copy()
        key_points = extraction_results.get('key_points', {})
        pairs = extraction_results.get('measurement_pairs', [])

        # Color scheme for different point types
        colors = {
            'collar': (255, 0, 0),      # Red
            'shoulder': (0, 255, 0),     # Green
            'chest': (0, 165, 255),      # Orange
            'hem': (255, 0, 255),        # Magenta
            'sleeve': (255, 255, 0),     # Cyan
            'cuff': (128, 0, 128),       # Purple
            'armhole': (0, 255, 255),    # Yellow
            'unknown': (128, 128, 128)   # Gray
        }

        # Draw key points
        for name, point in key_points.items():
            color = colors.get(point.type, colors['unknown'])
            pos = tuple(map(int, point.position))

            # Draw point
            cv2.circle(vis, pos, 8, color, -1)
            cv2.circle(vis, pos, 10, (0, 0, 0), 2)

            # Add label
            if show_labels:
                label = f"{point.type}_{point.side}"
                cv2.putText(vis, label, (pos[0] + 12, pos[1] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)

        # Draw measurement pairs
        if show_pairs:
            for left, right, measurement_name in pairs:
                left_pos = tuple(map(int, left.position))
                right_pos = tuple(map(int, right.position))

                # Draw connection line
                cv2.line(vis, left_pos, right_pos, (0, 255, 0), 2)

                # Add measurement value
                distance = extraction_results['measurements'].get(measurement_name, 0)
                mid_point = ((left_pos[0] + right_pos[0])//2,
                            (left_pos[1] + right_pos[1])//2)

                cv2.putText(vis, f"{distance:.0f}px",
                           (mid_point[0] - 30, mid_point[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        # Add summary
        quality = extraction_results.get('quality_score', 0)
        num_points = len(key_points)
        num_measurements = len(extraction_results.get('measurements', {}))

        cv2.putText(vis, f"Key Points: {num_points} | Measurements: {num_measurements} | Quality: {quality:.2f}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

        # Add legend
        y_offset = 60
        for point_type, color in colors.items():
            if point_type != 'unknown':
                cv2.circle(vis, (20, y_offset), 5, color, -1)
                cv2.putText(vis, point_type.capitalize(), (35, y_offset + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
                y_offset += 25

        return vis


def extract_focused_landmarks_from_ensemble(ensemble_results: Dict,
                                           image: np.ndarray,
                                           edge_corrector=None) -> Dict:
    """
    Extract focused landmarks from ensemble results with optional edge correction
    """
    # Get landmarks from ensemble
    landmarks = ensemble_results.get('ensemble_results', {}).get('landmarks', [])
    confidences = ensemble_results.get('ensemble_results', {}).get('confidences', [])
    category = ensemble_results.get('category', 'unknown')

    # Apply edge correction if corrector provided
    if edge_corrector:
        from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector

        correction_results = edge_corrector.correct_landmarks(
            image,
            landmarks,
            confidences,
            has_background=False
        )
        landmarks = correction_results['corrected_landmarks']
        logger.info(f"Applied edge correction to {correction_results['validation']['num_corrected']} landmarks")

    # Extract focused landmarks
    extractor = FocusedLandmarkExtractor()
    focused_results = extractor.extract_key_landmarks(
        landmarks,
        confidences,
        category,
        image.shape
    )

    return focused_results


def main():
    """Test focused landmark extraction"""
    import argparse

    parser = argparse.ArgumentParser(description='Focused Landmark Extraction for Measurements')
    parser.add_argument('--image', type=str, required=True,
                       help='Input image path')
    parser.add_argument('--ensemble-results', type=str,
                       help='Path to ensemble results JSON')
    parser.add_argument('--output', type=str, default='focused_landmarks_output',
                       help='Output directory')
    parser.add_argument('--use-edge-correction', action='store_true',
                       help='Apply edge correction before extraction')

    args = parser.parse_args()

    # Create output directory
    import os
    os.makedirs(args.output, exist_ok=True)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Get landmarks
    if args.ensemble_results:
        # Load from ensemble results
        with open(args.ensemble_results, 'r') as f:
            ensemble_results = json.load(f)
    else:
        # Run ensemble to get landmarks
        from multi_model_ensemble import MultiModelEnsemble
        ensemble = MultiModelEnsemble()
        ensemble_results = ensemble.detect_landmarks_ensemble(image, remove_background=False)

    # Apply edge correction if requested
    edge_corrector = None
    if args.use_edge_correction:
        from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector
        edge_corrector = EdgeAwareLandmarkCorrector()

    # Extract focused landmarks
    focused_results = extract_focused_landmarks_from_ensemble(
        ensemble_results,
        image,
        edge_corrector
    )

    # Print results
    print("\n" + "="*60)
    print("FOCUSED LANDMARK EXTRACTION RESULTS")
    print("="*60)
    print(f"Category: {focused_results['category']}")
    print(f"Quality Score: {focused_results['quality_score']:.2f}")
    print(f"Key Points Found: {len(focused_results['key_points'])}")

    print("\nKey Measurement Points:")
    for name, point in focused_results['key_points'].items():
        print(f"  {name}: ({point.position[0]}, {point.position[1]}) - conf: {point.confidence:.2f}")

    print("\nMeasurements (pixels):")
    for name, value in focused_results['measurements'].items():
        print(f"  {name}: {value:.1f}")

    # Create visualization
    extractor = FocusedLandmarkExtractor()
    vis = extractor.visualize_key_landmarks(image, focused_results)

    vis_path = os.path.join(args.output, 'focused_landmarks_visualization.jpg')
    cv2.imwrite(vis_path, vis)
    print(f"\nVisualization saved to: {vis_path}")

    # Save results
    results_path = os.path.join(args.output, 'focused_landmarks.json')

    # Convert to JSON-serializable format
    json_results = {
        'category': focused_results['category'],
        'quality_score': focused_results['quality_score'],
        'key_points': {
            name: {
                'position': point.position,
                'confidence': float(point.confidence),
                'type': point.type,
                'side': point.side
            }
            for name, point in focused_results['key_points'].items()
        },
        'measurements': focused_results['measurements']
    }

    with open(results_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"Results saved to: {results_path}")


if __name__ == '__main__':
    main()