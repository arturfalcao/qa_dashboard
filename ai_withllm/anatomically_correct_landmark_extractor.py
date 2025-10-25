#!/usr/bin/env python3
"""
Anatomically Correct Landmark Extractor

This module correctly identifies key measurement points based on actual garment anatomy,
fixing the issues with misplaced shoulder and chest landmarks.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from scipy.spatial.distance import cdist
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnatomicalMeasurementPoint:
    """Anatomically correct measurement point"""
    name: str
    position: Tuple[int, int]
    confidence: float
    type: str  # "shoulder", "armpit", "collar", "hem", "cuff"
    side: str  # "left", "right", "center"


class AnatomicallyCorrectExtractor:
    """
    Extracts measurement points based on actual garment anatomy
    """

    def __init__(self):
        """Initialize the anatomically correct extractor"""
        pass

    def extract_correct_measurement_points(self,
                                          landmarks: List[Tuple[int, int]],
                                          confidences: List[float],
                                          image_shape: Tuple,
                                          garment_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Extract anatomically correct measurement points

        Args:
            landmarks: All detected landmarks
            confidences: Confidence scores
            image_shape: (height, width) of image
            garment_mask: Optional binary mask of garment

        Returns:
            Dictionary with correctly identified measurement points
        """
        h, w = image_shape[:2]
        results = {
            'measurement_points': {},
            'pairs': [],
            'measurements': {},
            'anatomy_analysis': {}
        }

        # Filter valid landmarks
        valid_landmarks = []
        valid_confidences = []
        for lm, conf in zip(landmarks, confidences):
            if lm is not None and conf > 0.3:
                valid_landmarks.append(lm)
                valid_confidences.append(conf)

        if len(valid_landmarks) < 10:
            logger.warning(f"Only {len(valid_landmarks)} valid landmarks found")
            return results

        landmarks_array = np.array(valid_landmarks)

        # Analyze garment structure
        anatomy = self._analyze_garment_anatomy(landmarks_array, image_shape)
        results['anatomy_analysis'] = anatomy

        # Extract points based on anatomical positions
        measurement_points = {}

        # 1. COLLAR - Top center (this was correct)
        collar = self._find_collar_anatomical(landmarks_array, valid_confidences, anatomy)
        if collar:
            measurement_points['collar_center'] = collar

        # 2. SHOULDERS - At shoulder seams (top of garment where sleeves attach)
        shoulders = self._find_shoulders_anatomical(landmarks_array, valid_confidences, anatomy)
        measurement_points.update(shoulders)

        # 3. ARMPITS - Where sleeve meets body (not chest width)
        armpits = self._find_armpits_anatomical(landmarks_array, valid_confidences, anatomy)
        measurement_points.update(armpits)

        # 4. HEM - Bottom edge (this was correct)
        hem = self._find_hem_anatomical(landmarks_array, valid_confidences, anatomy)
        measurement_points.update(hem)

        # 5. CUFFS - Sleeve ends (this was correct for sleeve span)
        cuffs = self._find_cuffs_anatomical(landmarks_array, valid_confidences, anatomy)
        measurement_points.update(cuffs)

        results['measurement_points'] = measurement_points

        # Create correct measurement pairs
        results['pairs'] = self._create_anatomical_pairs(measurement_points)

        # Calculate measurements
        results['measurements'] = self._calculate_measurements(results['pairs'])

        return results

    def _analyze_garment_anatomy(self, landmarks: np.ndarray, image_shape: Tuple) -> Dict:
        """
        Analyze the anatomical structure of the garment
        """
        h, w = image_shape[:2]
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]

        # Find bounding box
        bbox = {
            'min_x': int(np.min(x_coords)),
            'max_x': int(np.max(x_coords)),
            'min_y': int(np.min(y_coords)),
            'max_y': int(np.max(y_coords)),
            'width': int(np.max(x_coords) - np.min(x_coords)),
            'height': int(np.max(y_coords) - np.min(y_coords))
        }

        # Calculate center
        center_x = int(np.mean(x_coords))
        center_y = int(np.mean(y_coords))

        # Define anatomical zones for a shirt laid flat
        # Shoulders are at the very top sides (0-10% height)
        # Armpits are slightly below shoulders (15-25% height)
        # Chest is at armpit level (for chest width measurement)
        # Waist is around 40-50% height
        # Hem is at bottom (90-100% height)

        zones = {
            'collar_zone': {
                'y_min': bbox['min_y'],
                'y_max': bbox['min_y'] + bbox['height'] * 0.1,
                'x_center': center_x,
                'x_tolerance': 150  # pixels from center for collar
            },
            'shoulder_zone': {
                'y_min': bbox['min_y'],
                'y_max': bbox['min_y'] + bbox['height'] * 0.15,  # Top 15% for shoulders
                'left_x_max': center_x - 200,  # Left shoulder area
                'right_x_min': center_x + 200   # Right shoulder area
            },
            'armpit_zone': {
                'y_min': bbox['min_y'] + bbox['height'] * 0.15,
                'y_max': bbox['min_y'] + bbox['height'] * 0.30,  # 15-30% for armpits
                'left_x_max': center_x - 100,
                'right_x_min': center_x + 100
            },
            'hem_zone': {
                'y_min': bbox['min_y'] + bbox['height'] * 0.85,
                'y_max': bbox['max_y']
            },
            'cuff_zone': {
                'y_min': bbox['min_y'] + bbox['height'] * 0.25,
                'y_max': bbox['min_y'] + bbox['height'] * 0.75,
                'outer_margin': 100  # How close to outer edge for cuffs
            }
        }

        return {
            'bbox': bbox,
            'center': {'x': center_x, 'y': center_y},
            'zones': zones,
            'garment_width': bbox['width'],
            'garment_height': bbox['height']
        }

    def _find_collar_anatomical(self, landmarks: np.ndarray, confidences: List[float],
                                anatomy: Dict) -> Optional[AnatomicalMeasurementPoint]:
        """
        Find the collar point at the top center
        """
        zone = anatomy['zones']['collar_zone']
        center_x = anatomy['center']['x']

        # Find points in collar zone
        collar_mask = (landmarks[:, 1] >= zone['y_min']) & \
                     (landmarks[:, 1] <= zone['y_max']) & \
                     (np.abs(landmarks[:, 0] - center_x) <= zone['x_tolerance'])

        collar_indices = np.where(collar_mask)[0]

        if len(collar_indices) > 0:
            # Get topmost point near center
            topmost_idx = collar_indices[np.argmin(landmarks[collar_indices, 1])]
            return AnatomicalMeasurementPoint(
                name='collar_center',
                position=tuple(landmarks[topmost_idx]),
                confidence=confidences[topmost_idx],
                type='collar',
                side='center'
            )
        return None

    def _find_shoulders_anatomical(self, landmarks: np.ndarray, confidences: List[float],
                                   anatomy: Dict) -> Dict[str, AnatomicalMeasurementPoint]:
        """
        Find shoulder points where sleeves attach to body (at the TOP of the garment)
        """
        points = {}
        zone = anatomy['zones']['shoulder_zone']

        # Find points in shoulder zone (very top of garment)
        shoulder_mask = (landmarks[:, 1] >= zone['y_min']) & \
                       (landmarks[:, 1] <= zone['y_max'])

        shoulder_indices = np.where(shoulder_mask)[0]

        if len(shoulder_indices) > 0:
            shoulder_points = landmarks[shoulder_indices]

            # LEFT SHOULDER - leftmost point in top zone
            left_shoulder_mask = shoulder_points[:, 0] < zone['left_x_max']
            if np.any(left_shoulder_mask):
                left_indices = np.where(left_shoulder_mask)[0]
                # Get the leftmost point that's still in the top zone
                leftmost_idx = left_indices[np.argmin(shoulder_points[left_indices, 0])]
                actual_idx = shoulder_indices[leftmost_idx]

                points['shoulder_left'] = AnatomicalMeasurementPoint(
                    name='shoulder_left',
                    position=tuple(landmarks[actual_idx]),
                    confidence=confidences[actual_idx],
                    type='shoulder',
                    side='left'
                )

            # RIGHT SHOULDER - rightmost point in top zone
            right_shoulder_mask = shoulder_points[:, 0] > zone['right_x_min']
            if np.any(right_shoulder_mask):
                right_indices = np.where(right_shoulder_mask)[0]
                # Get the rightmost point that's still in the top zone
                rightmost_idx = right_indices[np.argmax(shoulder_points[right_indices, 0])]
                actual_idx = shoulder_indices[rightmost_idx]

                points['shoulder_right'] = AnatomicalMeasurementPoint(
                    name='shoulder_right',
                    position=tuple(landmarks[actual_idx]),
                    confidence=confidences[actual_idx],
                    type='shoulder',
                    side='right'
                )

        return points

    def _find_armpits_anatomical(self, landmarks: np.ndarray, confidences: List[float],
                                 anatomy: Dict) -> Dict[str, AnatomicalMeasurementPoint]:
        """
        Find armpit points where sleeve meets body (for chest width measurement)
        These should be below shoulders but well above waist
        """
        points = {}
        zone = anatomy['zones']['armpit_zone']

        # Find points in armpit zone
        armpit_mask = (landmarks[:, 1] >= zone['y_min']) & \
                     (landmarks[:, 1] <= zone['y_max'])

        armpit_indices = np.where(armpit_mask)[0]

        if len(armpit_indices) > 0:
            armpit_points = landmarks[armpit_indices]

            # LEFT ARMPIT - leftmost point in armpit zone
            left_armpit_mask = armpit_points[:, 0] < zone['left_x_max']
            if np.any(left_armpit_mask):
                left_indices = np.where(left_armpit_mask)[0]
                leftmost_idx = left_indices[np.argmin(armpit_points[left_indices, 0])]
                actual_idx = armpit_indices[leftmost_idx]

                points['armpit_left'] = AnatomicalMeasurementPoint(
                    name='armpit_left',
                    position=tuple(landmarks[actual_idx]),
                    confidence=confidences[actual_idx],
                    type='armpit',
                    side='left'
                )

            # RIGHT ARMPIT - rightmost point in armpit zone
            right_armpit_mask = armpit_points[:, 0] > zone['right_x_min']
            if np.any(right_armpit_mask):
                right_indices = np.where(right_armpit_mask)[0]
                rightmost_idx = right_indices[np.argmax(armpit_points[right_indices, 0])]
                actual_idx = armpit_indices[rightmost_idx]

                points['armpit_right'] = AnatomicalMeasurementPoint(
                    name='armpit_right',
                    position=tuple(landmarks[actual_idx]),
                    confidence=confidences[actual_idx],
                    type='armpit',
                    side='right'
                )

        return points

    def _find_hem_anatomical(self, landmarks: np.ndarray, confidences: List[float],
                             anatomy: Dict) -> Dict[str, AnatomicalMeasurementPoint]:
        """
        Find hem points at bottom of garment
        """
        points = {}
        zone = anatomy['zones']['hem_zone']
        center_x = anatomy['center']['x']

        # Find points in hem zone
        hem_mask = (landmarks[:, 1] >= zone['y_min']) & \
                  (landmarks[:, 1] <= zone['y_max'])

        hem_indices = np.where(hem_mask)[0]

        if len(hem_indices) > 0:
            hem_points = landmarks[hem_indices]

            # Left hem
            left_hem = hem_points[hem_points[:, 0] < center_x - 100]
            if len(left_hem) > 0:
                leftmost_idx = np.argmin(left_hem[:, 0])
                actual_pos = left_hem[leftmost_idx]
                # Find the original index
                for i, lm in enumerate(landmarks):
                    if np.array_equal(lm, actual_pos):
                        points['hem_left'] = AnatomicalMeasurementPoint(
                            name='hem_left',
                            position=tuple(actual_pos),
                            confidence=confidences[i],
                            type='hem',
                            side='left'
                        )
                        break

            # Right hem
            right_hem = hem_points[hem_points[:, 0] > center_x + 100]
            if len(right_hem) > 0:
                rightmost_idx = np.argmax(right_hem[:, 0])
                actual_pos = right_hem[rightmost_idx]
                for i, lm in enumerate(landmarks):
                    if np.array_equal(lm, actual_pos):
                        points['hem_right'] = AnatomicalMeasurementPoint(
                            name='hem_right',
                            position=tuple(actual_pos),
                            confidence=confidences[i],
                            type='hem',
                            side='right'
                        )
                        break

            # Center hem
            center_hem = hem_points[np.abs(hem_points[:, 0] - center_x) < 150]
            if len(center_hem) > 0:
                bottom_idx = np.argmax(center_hem[:, 1])
                actual_pos = center_hem[bottom_idx]
                for i, lm in enumerate(landmarks):
                    if np.array_equal(lm, actual_pos):
                        points['hem_center'] = AnatomicalMeasurementPoint(
                            name='hem_center',
                            position=tuple(actual_pos),
                            confidence=confidences[i],
                            type='hem',
                            side='center'
                        )
                        break

        return points

    def _find_cuffs_anatomical(self, landmarks: np.ndarray, confidences: List[float],
                               anatomy: Dict) -> Dict[str, AnatomicalMeasurementPoint]:
        """
        Find cuff points at sleeve ends (for total span measurement)
        """
        points = {}
        zone = anatomy['zones']['cuff_zone']
        bbox = anatomy['bbox']

        # Cuffs are the extreme left and right points in the middle zone
        cuff_mask = (landmarks[:, 1] >= zone['y_min']) & \
                   (landmarks[:, 1] <= zone['y_max'])

        cuff_indices = np.where(cuff_mask)[0]

        if len(cuff_indices) > 0:
            cuff_points = landmarks[cuff_indices]

            # Left cuff - leftmost point
            if len(cuff_points) > 0:
                leftmost_idx = np.argmin(cuff_points[:, 0])
                if cuff_points[leftmost_idx, 0] < bbox['min_x'] + zone['outer_margin']:
                    actual_idx = cuff_indices[leftmost_idx]
                    points['cuff_left'] = AnatomicalMeasurementPoint(
                        name='cuff_left',
                        position=tuple(landmarks[actual_idx]),
                        confidence=confidences[actual_idx],
                        type='cuff',
                        side='left'
                    )

                # Right cuff - rightmost point
                rightmost_idx = np.argmax(cuff_points[:, 0])
                if cuff_points[rightmost_idx, 0] > bbox['max_x'] - zone['outer_margin']:
                    actual_idx = cuff_indices[rightmost_idx]
                    points['cuff_right'] = AnatomicalMeasurementPoint(
                        name='cuff_right',
                        position=tuple(landmarks[actual_idx]),
                        confidence=confidences[actual_idx],
                        type='cuff',
                        side='right'
                    )

        return points

    def _create_anatomical_pairs(self,
                                measurement_points: Dict[str, AnatomicalMeasurementPoint]) -> List[Tuple]:
        """
        Create anatomically correct measurement pairs
        """
        pairs = []

        # Correct measurement pairs
        pair_definitions = [
            ('shoulder_left', 'shoulder_right', 'shoulder_width'),  # Actual shoulder width
            ('armpit_left', 'armpit_right', 'chest_width'),        # Chest at armpit level
            ('hem_left', 'hem_right', 'hem_width'),                # Hem width
            ('cuff_left', 'cuff_right', 'sleeve_span'),            # Total span with sleeves
            ('collar_center', 'hem_center', 'garment_length'),     # Center front length
            ('shoulder_left', 'cuff_left', 'sleeve_length_left'),  # Left sleeve length
            ('shoulder_right', 'cuff_right', 'sleeve_length_right') # Right sleeve length
        ]

        for point1_name, point2_name, measurement_name in pair_definitions:
            if point1_name in measurement_points and point2_name in measurement_points:
                pairs.append((
                    measurement_points[point1_name],
                    measurement_points[point2_name],
                    measurement_name
                ))

        return pairs

    def _calculate_measurements(self, pairs: List[Tuple]) -> Dict[str, float]:
        """
        Calculate measurements from pairs
        """
        measurements = {}

        for point1, point2, measurement_name in pairs:
            distance = np.sqrt(
                (point2.position[0] - point1.position[0])**2 +
                (point2.position[1] - point1.position[1])**2
            )
            measurements[measurement_name] = distance

        return measurements

    def visualize_anatomical_measurements(self,
                                         image: np.ndarray,
                                         extraction_results: Dict,
                                         show_zones: bool = True) -> np.ndarray:
        """
        Visualize anatomically correct measurement points
        """
        vis = image.copy()
        measurement_points = extraction_results.get('measurement_points', {})
        pairs = extraction_results.get('pairs', [])
        measurements = extraction_results.get('measurements', {})
        anatomy = extraction_results.get('anatomy_analysis', {})

        # Show anatomical zones if requested
        if show_zones and anatomy:
            zones = anatomy.get('zones', {})

            # Draw zone rectangles with transparency
            overlay = vis.copy()

            # Shoulder zone (green)
            if 'shoulder_zone' in zones:
                sz = zones['shoulder_zone']
                cv2.rectangle(overlay,
                            (int(anatomy['bbox']['min_x']), int(sz['y_min'])),
                            (int(anatomy['bbox']['max_x']), int(sz['y_max'])),
                            (0, 255, 0), -1)

            # Armpit zone (orange)
            if 'armpit_zone' in zones:
                az = zones['armpit_zone']
                cv2.rectangle(overlay,
                            (int(anatomy['bbox']['min_x']), int(az['y_min'])),
                            (int(anatomy['bbox']['max_x']), int(az['y_max'])),
                            (0, 165, 255), -1)

            # Hem zone (magenta)
            if 'hem_zone' in zones:
                hz = zones['hem_zone']
                cv2.rectangle(overlay,
                            (int(anatomy['bbox']['min_x']), int(hz['y_min'])),
                            (int(anatomy['bbox']['max_x']), int(hz['y_max'])),
                            (255, 0, 255), -1)

            # Apply overlay with transparency
            vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)

        # Color scheme by type
        colors = {
            'collar': (255, 0, 0),      # Red
            'shoulder': (0, 255, 0),     # Green
            'armpit': (0, 165, 255),     # Orange
            'hem': (255, 0, 255),        # Magenta
            'cuff': (255, 255, 0),       # Cyan
        }

        # Draw measurement lines
        for point1, point2, measurement_name in pairs:
            pos1 = tuple(map(int, point1.position))
            pos2 = tuple(map(int, point2.position))

            # Different line styles for different measurements
            if 'width' in measurement_name or 'span' in measurement_name:
                # Horizontal measurements - thick green line
                cv2.line(vis, pos1, pos2, (0, 255, 0), 3)
            else:
                # Vertical measurements - thin blue line
                cv2.line(vis, pos1, pos2, (255, 0, 0), 2)

            # Add measurement value
            distance = measurements.get(measurement_name, 0)
            mid_point = ((pos1[0] + pos2[0])//2, (pos1[1] + pos2[1])//2)
            cv2.putText(vis, f"{distance:.0f}px",
                       (mid_point[0] - 30, mid_point[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Draw measurement points with correct labels
        for name, point in measurement_points.items():
            color = colors.get(point.type, (128, 128, 128))
            pos = tuple(map(int, point.position))

            # Draw point
            cv2.circle(vis, pos, 10, color, -1)
            cv2.circle(vis, pos, 12, (0, 0, 0), 2)

            # Add anatomically correct label
            label = f"{point.type.upper()}"
            if 'left' in name:
                label += "_L"
            elif 'right' in name:
                label += "_R"

            cv2.putText(vis, label, (pos[0] + 15, pos[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Add title with correct terminology
        cv2.putText(vis, "ANATOMICALLY CORRECT MEASUREMENT POINTS",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Add measurement summary
        y_offset = 60
        cv2.putText(vis, "Measurements:", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        y_offset += 30

        for name, value in measurements.items():
            text = f"{name}: {value:.1f}px"
            cv2.putText(vis, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 0), 1)
            y_offset += 25

        return vis


def main():
    """Test anatomically correct extraction"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Anatomically Correct Measurement Extraction')
    parser.add_argument('--image', type=str, required=True,
                       help='Input image path')
    parser.add_argument('--landmarks', type=str,
                       help='Path to landmarks JSON or ensemble results')
    parser.add_argument('--output', type=str, default='anatomical_output',
                       help='Output directory')
    parser.add_argument('--show-zones', action='store_true',
                       help='Show anatomical zones on visualization')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Get landmarks
    if args.landmarks and args.landmarks.endswith('.json'):
        with open(args.landmarks, 'r') as f:
            data = json.load(f)
            if 'ensemble_results' in data:
                landmarks = data['ensemble_results'].get('landmarks', [])
                confidences = data['ensemble_results'].get('confidences', [])
            else:
                landmarks = data.get('landmarks', [])
                confidences = data.get('confidences', [1.0] * len(landmarks))
    else:
        # Run ensemble to get landmarks
        from multi_model_ensemble import MultiModelEnsemble
        ensemble = MultiModelEnsemble()
        results = ensemble.detect_landmarks_ensemble(image, remove_background=False)
        landmarks = results['ensemble_results'].get('landmarks', [])
        confidences = results['ensemble_results'].get('confidences', [])

        # Apply edge correction
        from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector
        corrector = EdgeAwareLandmarkCorrector()
        correction_results = corrector.correct_landmarks(
            image, landmarks, confidences, has_background=False
        )
        landmarks = correction_results['corrected_landmarks']
        print(f"Applied edge correction to {correction_results['validation']['num_corrected']} landmarks")

    # Extract anatomically correct points
    extractor = AnatomicallyCorrectExtractor()
    results = extractor.extract_correct_measurement_points(
        landmarks,
        confidences,
        image.shape
    )

    # Print results
    print("\n" + "="*60)
    print("ANATOMICALLY CORRECT MEASUREMENT EXTRACTION")
    print("="*60)
    print(f"Measurement Points Found: {len(results['measurement_points'])}")

    print("\nIdentified Points (ANATOMICALLY CORRECT):")
    for name, point in results['measurement_points'].items():
        print(f"  {name}: ({point.position[0]}, {point.position[1]}) - {point.type}")

    print(f"\nMeasurement Pairs: {len(results['pairs'])}")
    print("\nMeasurements (pixels):")
    for name, value in results['measurements'].items():
        print(f"  {name}: {value:.1f}")

    # Create visualization
    vis = extractor.visualize_anatomical_measurements(image, results, show_zones=args.show_zones)
    vis_path = os.path.join(args.output, 'anatomical_measurements.jpg')
    cv2.imwrite(vis_path, vis)
    print(f"\nVisualization saved to: {vis_path}")

    # Save results
    json_results = {
        'measurement_points': {
            name: {
                'position': point.position,
                'confidence': float(point.confidence),
                'type': point.type,
                'side': point.side
            }
            for name, point in results['measurement_points'].items()
        },
        'measurements': results['measurements'],
        'anatomy_analysis': results['anatomy_analysis']
    }

    results_path = os.path.join(args.output, 'anatomical_measurements.json')
    with open(results_path, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    print(f"Results saved to: {results_path}")


if __name__ == '__main__':
    main()