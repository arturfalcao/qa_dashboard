#!/usr/bin/env python3
"""
Spatial Measurement Point Extractor

Uses spatial analysis to identify key measurement points on garments
based on their position rather than relying on fixed landmark indices.
This is more robust and works with any landmark detection model.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SpatialMeasurementPoint:
    """Key measurement point identified by spatial position"""
    name: str
    position: Tuple[int, int]
    confidence: float
    region: str  # "top", "middle", "bottom", "left", "right"
    type: str  # "hem", "chest", "shoulder", "collar", "sleeve", "cuff"


class SpatialMeasurementExtractor:
    """
    Extracts key measurement points using spatial analysis of landmark positions
    """

    def __init__(self,
                 min_edge_distance: int = 50,
                 cluster_threshold: int = 100):
        """
        Initialize the spatial measurement extractor

        Args:
            min_edge_distance: Minimum distance from image edge for valid points
            cluster_threshold: Maximum distance for points to be in same cluster
        """
        self.min_edge_distance = min_edge_distance
        self.cluster_threshold = cluster_threshold

    def extract_measurement_points(self,
                                  landmarks: List[Tuple[int, int]],
                                  confidences: List[float],
                                  image_shape: Tuple,
                                  garment_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Extract key measurement points using spatial analysis

        Args:
            landmarks: All detected landmarks
            confidences: Confidence scores
            image_shape: (height, width) of image
            garment_mask: Optional binary mask of garment region

        Returns:
            Dictionary with identified measurement points
        """
        h, w = image_shape[:2]
        results = {
            'measurement_points': {},
            'pairs': [],
            'measurements': {},
            'spatial_analysis': {}
        }

        # Filter valid landmarks
        valid_landmarks = []
        valid_confidences = []
        for lm, conf in zip(landmarks, confidences):
            if lm is not None and conf > 0.3:
                valid_landmarks.append(lm)
                valid_confidences.append(conf)

        if len(valid_landmarks) < 6:
            logger.warning(f"Only {len(valid_landmarks)} valid landmarks found, need at least 6")
            return results

        landmarks_array = np.array(valid_landmarks)

        # Analyze spatial distribution
        spatial_info = self._analyze_spatial_distribution(landmarks_array, image_shape)
        results['spatial_analysis'] = spatial_info

        # Extract key points by region
        measurement_points = {}

        # 1. COLLAR/NECKLINE - Top center points
        collar_points = self._find_collar_points(landmarks_array, valid_confidences, spatial_info, image_shape)
        measurement_points.update(collar_points)

        # 2. SHOULDER - Top left/right points
        shoulder_points = self._find_shoulder_points(landmarks_array, valid_confidences, spatial_info, image_shape)
        measurement_points.update(shoulder_points)

        # 3. CHEST/ARMPIT - Upper-middle left/right points
        chest_points = self._find_chest_points(landmarks_array, valid_confidences, spatial_info, image_shape)
        measurement_points.update(chest_points)

        # 4. HEM - Bottom points
        hem_points = self._find_hem_points(landmarks_array, valid_confidences, spatial_info, image_shape)
        measurement_points.update(hem_points)

        # 5. SLEEVE/CUFF - Middle-outer points
        sleeve_points = self._find_sleeve_points(landmarks_array, valid_confidences, spatial_info, image_shape)
        measurement_points.update(sleeve_points)

        results['measurement_points'] = measurement_points

        # Identify measurement pairs
        results['pairs'] = self._identify_measurement_pairs(measurement_points)

        # Calculate measurements
        results['measurements'] = self._calculate_measurements(results['pairs'])

        return results

    def _analyze_spatial_distribution(self,
                                     landmarks: np.ndarray,
                                     image_shape: Tuple) -> Dict:
        """
        Analyze the spatial distribution of landmarks
        """
        h, w = image_shape[:2]
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]

        # Find bounding box of landmarks
        bbox = {
            'min_x': int(np.min(x_coords)),
            'max_x': int(np.max(x_coords)),
            'min_y': int(np.min(y_coords)),
            'max_y': int(np.max(y_coords)),
            'width': int(np.max(x_coords) - np.min(x_coords)),
            'height': int(np.max(y_coords) - np.min(y_coords))
        }

        # Calculate center
        center = {
            'x': int(np.mean(x_coords)),
            'y': int(np.mean(y_coords))
        }

        # Define regions
        regions = {
            'top_threshold': bbox['min_y'] + bbox['height'] * 0.2,
            'bottom_threshold': bbox['min_y'] + bbox['height'] * 0.8,
            'left_threshold': center['x'] - bbox['width'] * 0.2,
            'right_threshold': center['x'] + bbox['width'] * 0.2,
        }

        return {
            'bbox': bbox,
            'center': center,
            'regions': regions,
            'num_landmarks': len(landmarks)
        }

    def _find_collar_points(self,
                           landmarks: np.ndarray,
                           confidences: List[float],
                           spatial_info: Dict,
                           image_shape: Tuple) -> Dict[str, SpatialMeasurementPoint]:
        """
        Find collar/neckline points at the top center of garment
        """
        points = {}
        bbox = spatial_info['bbox']
        center = spatial_info['center']

        # Find points in top region
        top_mask = landmarks[:, 1] < spatial_info['regions']['top_threshold']
        top_indices = np.where(top_mask)[0]

        if len(top_indices) > 0:
            top_landmarks = landmarks[top_indices]
            top_confidences = [confidences[i] for i in top_indices]

            # Find the topmost center point
            center_distance = np.abs(top_landmarks[:, 0] - center['x'])
            center_mask = center_distance < 200  # Within 200 pixels of center

            if np.any(center_mask):
                center_indices = np.where(center_mask)[0]
                # Get the highest confidence point near center
                best_idx = center_indices[np.argmax([top_confidences[i] for i in center_indices])]

                collar_pos = tuple(top_landmarks[best_idx])
                points['collar_center'] = SpatialMeasurementPoint(
                    name='collar_center',
                    position=collar_pos,
                    confidence=top_confidences[best_idx],
                    region='top',
                    type='collar'
                )

        return points

    def _find_shoulder_points(self,
                             landmarks: np.ndarray,
                             confidences: List[float],
                             spatial_info: Dict,
                             image_shape: Tuple) -> Dict[str, SpatialMeasurementPoint]:
        """
        Find shoulder points at top left and right
        """
        points = {}
        regions = spatial_info['regions']

        # Top region landmarks
        top_mask = landmarks[:, 1] < regions['top_threshold'] + 100  # Slightly lower than collar

        # Left shoulder
        left_mask = top_mask & (landmarks[:, 0] < regions['left_threshold'])
        left_indices = np.where(left_mask)[0]

        if len(left_indices) > 0:
            # Get leftmost point in top region
            leftmost_idx = left_indices[np.argmin(landmarks[left_indices, 0])]
            points['shoulder_left'] = SpatialMeasurementPoint(
                name='shoulder_left',
                position=tuple(landmarks[leftmost_idx]),
                confidence=confidences[leftmost_idx],
                region='left',
                type='shoulder'
            )

        # Right shoulder
        right_mask = top_mask & (landmarks[:, 0] > regions['right_threshold'])
        right_indices = np.where(right_mask)[0]

        if len(right_indices) > 0:
            # Get rightmost point in top region
            rightmost_idx = right_indices[np.argmax(landmarks[right_indices, 0])]
            points['shoulder_right'] = SpatialMeasurementPoint(
                name='shoulder_right',
                position=tuple(landmarks[rightmost_idx]),
                confidence=confidences[rightmost_idx],
                region='right',
                type='shoulder'
            )

        return points

    def _find_chest_points(self,
                          landmarks: np.ndarray,
                          confidences: List[float],
                          spatial_info: Dict,
                          image_shape: Tuple) -> Dict[str, SpatialMeasurementPoint]:
        """
        Find chest/armpit points in the upper-middle region
        """
        points = {}
        bbox = spatial_info['bbox']
        regions = spatial_info['regions']

        # Middle-upper region (between top and center)
        middle_y = bbox['min_y'] + bbox['height'] * 0.35
        middle_mask = (landmarks[:, 1] > regions['top_threshold']) & \
                     (landmarks[:, 1] < middle_y + 100)

        # Left chest/armpit
        left_chest_mask = middle_mask & (landmarks[:, 0] < regions['left_threshold'])
        left_indices = np.where(left_chest_mask)[0]

        if len(left_indices) > 0:
            # Get leftmost point in middle region
            leftmost_idx = left_indices[np.argmin(landmarks[left_indices, 0])]
            points['chest_left'] = SpatialMeasurementPoint(
                name='chest_left',
                position=tuple(landmarks[leftmost_idx]),
                confidence=confidences[leftmost_idx],
                region='left',
                type='chest'
            )

        # Right chest/armpit
        right_chest_mask = middle_mask & (landmarks[:, 0] > regions['right_threshold'])
        right_indices = np.where(right_chest_mask)[0]

        if len(right_indices) > 0:
            # Get rightmost point in middle region
            rightmost_idx = right_indices[np.argmax(landmarks[right_indices, 0])]
            points['chest_right'] = SpatialMeasurementPoint(
                name='chest_right',
                position=tuple(landmarks[rightmost_idx]),
                confidence=confidences[rightmost_idx],
                region='right',
                type='chest'
            )

        return points

    def _find_hem_points(self,
                        landmarks: np.ndarray,
                        confidences: List[float],
                        spatial_info: Dict,
                        image_shape: Tuple) -> Dict[str, SpatialMeasurementPoint]:
        """
        Find hem points at the bottom of the garment
        """
        points = {}
        regions = spatial_info['regions']
        center = spatial_info['center']

        # Bottom region
        bottom_mask = landmarks[:, 1] > regions['bottom_threshold']
        bottom_indices = np.where(bottom_mask)[0]

        if len(bottom_indices) > 0:
            bottom_landmarks = landmarks[bottom_indices]
            bottom_confidences = [confidences[i] for i in bottom_indices]

            # Left hem
            left_hem_mask = bottom_landmarks[:, 0] < center['x'] - 100
            if np.any(left_hem_mask):
                left_idx = np.where(left_hem_mask)[0]
                leftmost = left_idx[np.argmin(bottom_landmarks[left_idx, 0])]
                points['hem_left'] = SpatialMeasurementPoint(
                    name='hem_left',
                    position=tuple(bottom_landmarks[leftmost]),
                    confidence=bottom_confidences[leftmost],
                    region='bottom',
                    type='hem'
                )

            # Right hem
            right_hem_mask = bottom_landmarks[:, 0] > center['x'] + 100
            if np.any(right_hem_mask):
                right_idx = np.where(right_hem_mask)[0]
                rightmost = right_idx[np.argmax(bottom_landmarks[right_idx, 0])]
                points['hem_right'] = SpatialMeasurementPoint(
                    name='hem_right',
                    position=tuple(bottom_landmarks[rightmost]),
                    confidence=bottom_confidences[rightmost],
                    region='bottom',
                    type='hem'
                )

            # Center hem
            center_distance = np.abs(bottom_landmarks[:, 0] - center['x'])
            if len(center_distance) > 0:
                center_idx = np.argmin(center_distance)
                points['hem_center'] = SpatialMeasurementPoint(
                    name='hem_center',
                    position=tuple(bottom_landmarks[center_idx]),
                    confidence=bottom_confidences[center_idx],
                    region='bottom',
                    type='hem'
                )

        return points

    def _find_sleeve_points(self,
                          landmarks: np.ndarray,
                          confidences: List[float],
                          spatial_info: Dict,
                          image_shape: Tuple) -> Dict[str, SpatialMeasurementPoint]:
        """
        Find sleeve/cuff points at the outer edges
        """
        points = {}
        bbox = spatial_info['bbox']

        # Look for points at extreme left and right in middle region
        middle_y_min = bbox['min_y'] + bbox['height'] * 0.3
        middle_y_max = bbox['min_y'] + bbox['height'] * 0.7
        middle_mask = (landmarks[:, 1] > middle_y_min) & (landmarks[:, 1] < middle_y_max)

        if np.any(middle_mask):
            middle_landmarks = landmarks[middle_mask]
            middle_indices = np.where(middle_mask)[0]
            middle_confidences = [confidences[i] for i in middle_indices]

            # Leftmost point (potential sleeve)
            if len(middle_landmarks) > 0:
                leftmost_idx = np.argmin(middle_landmarks[:, 0])
                if middle_landmarks[leftmost_idx, 0] < bbox['min_x'] + 100:  # Near edge
                    points['sleeve_left'] = SpatialMeasurementPoint(
                        name='sleeve_left',
                        position=tuple(middle_landmarks[leftmost_idx]),
                        confidence=middle_confidences[leftmost_idx],
                        region='left',
                        type='sleeve'
                    )

                # Rightmost point (potential sleeve)
                rightmost_idx = np.argmax(middle_landmarks[:, 0])
                if middle_landmarks[rightmost_idx, 0] > bbox['max_x'] - 100:  # Near edge
                    points['sleeve_right'] = SpatialMeasurementPoint(
                        name='sleeve_right',
                        position=tuple(middle_landmarks[rightmost_idx]),
                        confidence=middle_confidences[rightmost_idx],
                        region='right',
                        type='sleeve'
                    )

        return points

    def _identify_measurement_pairs(self,
                                   measurement_points: Dict[str, SpatialMeasurementPoint]) -> List[Tuple]:
        """
        Identify paired points for measurements
        """
        pairs = []

        # Define measurement pairs
        pair_definitions = [
            ('shoulder_left', 'shoulder_right', 'shoulder_width'),
            ('chest_left', 'chest_right', 'chest_width'),
            ('hem_left', 'hem_right', 'hem_width'),
            ('sleeve_left', 'sleeve_right', 'sleeve_span')
        ]

        for left_name, right_name, measurement_name in pair_definitions:
            if left_name in measurement_points and right_name in measurement_points:
                pairs.append((
                    measurement_points[left_name],
                    measurement_points[right_name],
                    measurement_name
                ))

        # Add vertical measurements
        vertical_pairs = [
            ('collar_center', 'hem_center', 'garment_length'),
            ('shoulder_left', 'hem_left', 'side_length_left'),
            ('shoulder_right', 'hem_right', 'side_length_right')
        ]

        for top_name, bottom_name, measurement_name in vertical_pairs:
            if top_name in measurement_points and bottom_name in measurement_points:
                pairs.append((
                    measurement_points[top_name],
                    measurement_points[bottom_name],
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

    def visualize_measurement_points(self,
                                    image: np.ndarray,
                                    extraction_results: Dict,
                                    show_measurements: bool = True) -> np.ndarray:
        """
        Visualize the spatially identified measurement points
        """
        vis = image.copy()
        measurement_points = extraction_results.get('measurement_points', {})
        pairs = extraction_results.get('pairs', [])
        measurements = extraction_results.get('measurements', {})

        # Color scheme by type
        colors = {
            'collar': (255, 0, 0),      # Red
            'shoulder': (0, 255, 0),     # Green
            'chest': (0, 165, 255),      # Orange
            'hem': (255, 0, 255),        # Magenta
            'sleeve': (255, 255, 0),     # Cyan
        }

        # Draw measurement points
        for name, point in measurement_points.items():
            color = colors.get(point.type, (128, 128, 128))
            pos = tuple(map(int, point.position))

            # Draw larger circles for key points
            cv2.circle(vis, pos, 10, color, -1)
            cv2.circle(vis, pos, 12, (0, 0, 0), 2)

            # Add label
            label = f"{point.type}"
            if 'left' in name:
                label += "_L"
            elif 'right' in name:
                label += "_R"

            cv2.putText(vis, label, (pos[0] + 15, pos[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        # Draw measurement lines
        if show_measurements:
            for point1, point2, measurement_name in pairs:
                pos1 = tuple(map(int, point1.position))
                pos2 = tuple(map(int, point2.position))

                # Draw measurement line
                if 'width' in measurement_name or 'span' in measurement_name:
                    # Horizontal measurements - green line
                    cv2.line(vis, pos1, pos2, (0, 255, 0), 3)
                else:
                    # Vertical measurements - blue line
                    cv2.line(vis, pos1, pos2, (255, 0, 0), 2, cv2.LINE_4)

                # Add measurement value
                distance = measurements.get(measurement_name, 0)
                mid_point = ((pos1[0] + pos2[0])//2, (pos1[1] + pos2[1])//2)

                cv2.putText(vis, f"{distance:.0f}px",
                           (mid_point[0] - 30, mid_point[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

        # Add summary panel
        summary_bg = np.ones((150, image.shape[1], 3), dtype=np.uint8) * 240
        y_offset = 30

        cv2.putText(summary_bg, f"Spatial Measurement Points: {len(measurement_points)}",
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        y_offset += 35

        # List measurements
        for name, value in measurements.items():
            text = f"{name}: {value:.1f}px"
            cv2.putText(summary_bg, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 0), 1)
            y_offset += 25

        # Combine image and summary
        vis = np.vstack([vis, summary_bg])

        return vis


def main():
    """Test spatial measurement extraction"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Spatial Measurement Point Extraction')
    parser.add_argument('--image', type=str, required=True,
                       help='Input image path')
    parser.add_argument('--ensemble-results', type=str,
                       help='Path to ensemble results JSON')
    parser.add_argument('--output', type=str, default='spatial_measurement_output',
                       help='Output directory')
    parser.add_argument('--use-edge-correction', action='store_true',
                       help='Apply edge correction first')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Get landmarks
    if args.ensemble_results:
        with open(args.ensemble_results, 'r') as f:
            ensemble_results = json.load(f)
        landmarks = ensemble_results.get('ensemble_results', {}).get('landmarks', [])
        confidences = ensemble_results.get('ensemble_results', {}).get('confidences', [])
    else:
        # Run ensemble
        from multi_model_ensemble import MultiModelEnsemble
        ensemble = MultiModelEnsemble()
        ensemble_results = ensemble.detect_landmarks_ensemble(image, remove_background=False)
        landmarks = ensemble_results['ensemble_results'].get('landmarks', [])
        confidences = ensemble_results['ensemble_results'].get('confidences', [])

    # Apply edge correction if requested
    if args.use_edge_correction:
        from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector
        corrector = EdgeAwareLandmarkCorrector()
        correction_results = corrector.correct_landmarks(
            image, landmarks, confidences, has_background=False
        )
        landmarks = correction_results['corrected_landmarks']
        print(f"Applied edge correction to {correction_results['validation']['num_corrected']} landmarks")

    # Extract measurement points
    extractor = SpatialMeasurementExtractor()
    results = extractor.extract_measurement_points(
        landmarks,
        confidences,
        image.shape
    )

    # Print results
    print("\n" + "="*60)
    print("SPATIAL MEASUREMENT EXTRACTION RESULTS")
    print("="*60)
    print(f"Measurement Points Found: {len(results['measurement_points'])}")

    print("\nIdentified Points:")
    for name, point in results['measurement_points'].items():
        print(f"  {name}: ({point.position[0]}, {point.position[1]}) - {point.type}")

    print(f"\nMeasurement Pairs: {len(results['pairs'])}")
    print("\nMeasurements (pixels):")
    for name, value in results['measurements'].items():
        print(f"  {name}: {value:.1f}")

    # Create visualization
    vis = extractor.visualize_measurement_points(image, results)
    vis_path = os.path.join(args.output, 'spatial_measurements_visualization.jpg')
    cv2.imwrite(vis_path, vis)
    print(f"\nVisualization saved to: {vis_path}")

    # Save results
    json_results = {
        'measurement_points': {
            name: {
                'position': point.position,
                'confidence': float(point.confidence),
                'type': point.type,
                'region': point.region
            }
            for name, point in results['measurement_points'].items()
        },
        'measurements': results['measurements'],
        'spatial_analysis': results['spatial_analysis']
    }

    results_path = os.path.join(args.output, 'spatial_measurements.json')
    with open(results_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"Results saved to: {results_path}")


if __name__ == '__main__':
    main()