#!/usr/bin/env python3
"""
Structural Keypoint Mapper
Maps structural heatmap keypoints to anatomical measurement points
"""

import cv2
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import argparse
from scipy.spatial.distance import cdist
from sklearn.cluster import DBSCAN

@dataclass
class MeasurementPoint:
    """Represents a key measurement point on a garment"""
    name: str
    position: Tuple[int, int]
    confidence: float
    source: str = "structural"

class StructuralKeypointMapper:
    """Maps structural keypoints to anatomical measurement points"""

    def __init__(self):
        self.measurement_points = {}
        self.garment_type = None

    def detect_garment_type(self, image: np.ndarray, keypoints: List[Dict]) -> str:
        """Detect garment type based on keypoint distribution"""

        # Get image dimensions
        h, w = image.shape[:2]

        # Analyze keypoint distribution
        kp_array = np.array([[kp['position'][0], kp['position'][1]] for kp in keypoints[:20]])

        # Calculate aspect ratio of keypoint bounding box
        min_x, min_y = kp_array.min(axis=0)
        max_x, max_y = kp_array.max(axis=0)
        width = max_x - min_x
        height = max_y - min_y
        aspect_ratio = width / height if height > 0 else 1

        # Check vertical distribution
        vertical_spread = np.std(kp_array[:, 1])
        horizontal_spread = np.std(kp_array[:, 0])

        # Classify based on characteristics
        if aspect_ratio > 1.2 and horizontal_spread > vertical_spread:
            # Wider than tall, likely a top laid flat
            return 'top'
        elif aspect_ratio < 0.8 and vertical_spread > horizontal_spread:
            # Taller than wide, likely pants/skirt
            return 'bottom'
        else:
            # Default to top for now
            return 'top'

    def cluster_keypoints(self, keypoints: List[Dict], eps: float = 100) -> Dict[int, List[Dict]]:
        """Cluster nearby keypoints to find regions of interest"""

        if len(keypoints) == 0:
            return {}

        # Extract positions
        positions = np.array([[kp['position'][0], kp['position'][1]] for kp in keypoints])

        # Cluster using DBSCAN
        clustering = DBSCAN(eps=eps, min_samples=2).fit(positions)

        # Group keypoints by cluster
        clusters = {}
        for i, label in enumerate(clustering.labels_):
            if label == -1:  # Noise points
                continue
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(keypoints[i])

        return clusters

    def find_collar_region(self, image: np.ndarray, keypoints: List[Dict]) -> Optional[MeasurementPoint]:
        """Find collar region for tops"""

        # Look for keypoints in the upper-center region
        h, w = image.shape[:2]

        # Define collar search region (top 20% of image, center 40%)
        collar_candidates = []
        for kp in keypoints[:30]:  # Check top 30 strongest keypoints
            x, y = kp['position']

            # Check if in collar region
            if (y < h * 0.3 and  # Upper portion
                w * 0.3 < x < w * 0.7):  # Center horizontally
                collar_candidates.append(kp)

        if collar_candidates:
            # Find the topmost strong keypoint
            collar_kp = min(collar_candidates, key=lambda k: k['position'][1])
            return MeasurementPoint(
                name='collar',
                position=tuple(collar_kp['position']),
                confidence=collar_kp['strength']
            )
        return None

    def find_shoulders(self, image: np.ndarray, keypoints: List[Dict]) -> Dict[str, MeasurementPoint]:
        """Find left and right shoulder points"""

        shoulders = {}
        h, w = image.shape[:2]

        # Look for keypoints in shoulder regions (upper sides)
        left_shoulder_candidates = []
        right_shoulder_candidates = []

        for kp in keypoints[:30]:
            x, y = kp['position']

            # Check if in shoulder height range
            if h * 0.15 < y < h * 0.35:
                if x < w * 0.4:  # Left side
                    left_shoulder_candidates.append(kp)
                elif x > w * 0.6:  # Right side
                    right_shoulder_candidates.append(kp)

        # Select best candidates
        if left_shoulder_candidates:
            # Leftmost point in shoulder region
            left_kp = min(left_shoulder_candidates, key=lambda k: k['position'][0])
            shoulders['left_shoulder'] = MeasurementPoint(
                name='left_shoulder',
                position=tuple(left_kp['position']),
                confidence=left_kp['strength']
            )

        if right_shoulder_candidates:
            # Rightmost point in shoulder region
            right_kp = max(right_shoulder_candidates, key=lambda k: k['position'][0])
            shoulders['right_shoulder'] = MeasurementPoint(
                name='right_shoulder',
                position=tuple(right_kp['position']),
                confidence=right_kp['strength']
            )

        return shoulders

    def find_armpits(self, image: np.ndarray, keypoints: List[Dict], shoulders: Dict) -> Dict[str, MeasurementPoint]:
        """Find armpit points based on shoulders"""

        armpits = {}
        h, w = image.shape[:2]

        # Look for keypoints below shoulders
        if 'left_shoulder' in shoulders:
            left_shoulder_y = shoulders['left_shoulder'].position[1]
            left_armpit_candidates = []

            for kp in keypoints:
                x, y = kp['position']
                # Below shoulder, left side
                if (left_shoulder_y + 50 < y < left_shoulder_y + h * 0.2 and
                    x < w * 0.4):
                    left_armpit_candidates.append(kp)

            if left_armpit_candidates:
                # Choose strongest keypoint in region
                left_kp = max(left_armpit_candidates, key=lambda k: k['strength'])
                armpits['left_armpit'] = MeasurementPoint(
                    name='left_armpit',
                    position=tuple(left_kp['position']),
                    confidence=left_kp['strength']
                )

        if 'right_shoulder' in shoulders:
            right_shoulder_y = shoulders['right_shoulder'].position[1]
            right_armpit_candidates = []

            for kp in keypoints:
                x, y = kp['position']
                # Below shoulder, right side
                if (right_shoulder_y + 50 < y < right_shoulder_y + h * 0.2 and
                    x > w * 0.6):
                    right_armpit_candidates.append(kp)

            if right_armpit_candidates:
                # Choose strongest keypoint in region
                right_kp = max(right_armpit_candidates, key=lambda k: k['strength'])
                armpits['right_armpit'] = MeasurementPoint(
                    name='right_armpit',
                    position=tuple(right_kp['position']),
                    confidence=right_kp['strength']
                )

        return armpits

    def find_chest_points(self, image: np.ndarray, keypoints: List[Dict], armpits: Dict) -> Dict[str, MeasurementPoint]:
        """Find chest measurement points"""

        chest_points = {}
        h, w = image.shape[:2]

        # Chest is typically at armpit level
        if armpits:
            # Get average armpit height
            armpit_ys = [ap.position[1] for ap in armpits.values()]
            avg_armpit_y = np.mean(armpit_ys)

            # Look for keypoints at chest level
            chest_candidates = []
            for kp in keypoints:
                x, y = kp['position']
                # At armpit height, near edges
                if (abs(y - avg_armpit_y) < h * 0.05 and
                    (x < w * 0.35 or x > w * 0.65)):
                    chest_candidates.append(kp)

            if len(chest_candidates) >= 2:
                # Sort by x position
                chest_candidates.sort(key=lambda k: k['position'][0])

                # Take leftmost and rightmost
                chest_points['left_chest'] = MeasurementPoint(
                    name='left_chest',
                    position=tuple(chest_candidates[0]['position']),
                    confidence=chest_candidates[0]['strength']
                )
                chest_points['right_chest'] = MeasurementPoint(
                    name='right_chest',
                    position=tuple(chest_candidates[-1]['position']),
                    confidence=chest_candidates[-1]['strength']
                )

        return chest_points

    def find_hem_points(self, image: np.ndarray, keypoints: List[Dict]) -> Dict[str, MeasurementPoint]:
        """Find hem points at bottom of garment"""

        hem_points = {}
        h, w = image.shape[:2]

        # Look for keypoints in bottom region
        bottom_candidates = []
        for kp in keypoints:
            x, y = kp['position']
            if y > h * 0.7:  # Bottom 30% of image
                bottom_candidates.append(kp)

        if len(bottom_candidates) >= 2:
            # Sort by x position
            bottom_candidates.sort(key=lambda k: k['position'][0])

            # Get leftmost and rightmost
            hem_points['left_hem'] = MeasurementPoint(
                name='left_hem',
                position=tuple(bottom_candidates[0]['position']),
                confidence=bottom_candidates[0]['strength']
            )
            hem_points['right_hem'] = MeasurementPoint(
                name='right_hem',
                position=tuple(bottom_candidates[-1]['position']),
                confidence=bottom_candidates[-1]['strength']
            )

        return hem_points

    def find_sleeve_cuffs(self, image: np.ndarray, keypoints: List[Dict]) -> Dict[str, MeasurementPoint]:
        """Find sleeve cuff points"""

        cuffs = {}
        h, w = image.shape[:2]

        # Look for keypoints in outer regions at mid-height
        left_cuff_candidates = []
        right_cuff_candidates = []

        for kp in keypoints:
            x, y = kp['position']

            # Mid to lower height, outer edges
            if h * 0.4 < y < h * 0.8:
                if x < w * 0.25:  # Far left
                    left_cuff_candidates.append(kp)
                elif x > w * 0.75:  # Far right
                    right_cuff_candidates.append(kp)

        if left_cuff_candidates:
            # Leftmost point
            left_kp = min(left_cuff_candidates, key=lambda k: k['position'][0])
            cuffs['left_cuff'] = MeasurementPoint(
                name='left_cuff',
                position=tuple(left_kp['position']),
                confidence=left_kp['strength']
            )

        if right_cuff_candidates:
            # Rightmost point
            right_kp = max(right_cuff_candidates, key=lambda k: k['position'][0])
            cuffs['right_cuff'] = MeasurementPoint(
                name='right_cuff',
                position=tuple(right_kp['position']),
                confidence=right_kp['strength']
            )

        return cuffs

    def find_waist_points(self, image: np.ndarray, keypoints: List[Dict]) -> Dict[str, MeasurementPoint]:
        """Find waist points for bottoms"""

        waist_points = {}
        h, w = image.shape[:2]

        # Look for keypoints in top region for bottoms
        top_candidates = []
        for kp in keypoints[:30]:
            x, y = kp['position']
            if y < h * 0.3:  # Top 30% of image
                top_candidates.append(kp)

        if len(top_candidates) >= 2:
            # Sort by x position
            top_candidates.sort(key=lambda k: k['position'][0])

            # Get leftmost and rightmost
            waist_points['left_waist'] = MeasurementPoint(
                name='left_waist',
                position=tuple(top_candidates[0]['position']),
                confidence=top_candidates[0]['strength']
            )
            waist_points['right_waist'] = MeasurementPoint(
                name='right_waist',
                position=tuple(top_candidates[-1]['position']),
                confidence=top_candidates[-1]['strength']
            )

        return waist_points

    def map_keypoints_to_measurements(self, image: np.ndarray, keypoints_file: str) -> Dict[str, MeasurementPoint]:
        """Main function to map structural keypoints to measurement points"""

        # Load keypoints
        with open(keypoints_file, 'r') as f:
            data = json.load(f)

        keypoints = data['keypoints']

        # Detect garment type
        self.garment_type = self.detect_garment_type(image, keypoints)
        print(f"Detected garment type: {self.garment_type}")

        # Initialize measurement points
        measurement_points = {}

        if self.garment_type == 'top':
            # Find key regions for tops
            collar = self.find_collar_region(image, keypoints)
            if collar:
                measurement_points['collar'] = collar

            shoulders = self.find_shoulders(image, keypoints)
            measurement_points.update(shoulders)

            armpits = self.find_armpits(image, keypoints, shoulders)
            measurement_points.update(armpits)

            chest = self.find_chest_points(image, keypoints, armpits)
            measurement_points.update(chest)

            hem = self.find_hem_points(image, keypoints)
            measurement_points.update(hem)

            cuffs = self.find_sleeve_cuffs(image, keypoints)
            measurement_points.update(cuffs)

        elif self.garment_type == 'bottom':
            # Find key regions for bottoms
            waist = self.find_waist_points(image, keypoints)
            measurement_points.update(waist)

            hem = self.find_hem_points(image, keypoints)
            measurement_points.update(hem)

        return measurement_points

    def visualize_measurement_points(self, image: np.ndarray, measurement_points: Dict[str, MeasurementPoint],
                                    output_path: str):
        """Visualize the mapped measurement points"""

        vis = image.copy()

        # Define colors for different point types
        colors = {
            'collar': (255, 255, 0),      # Cyan
            'shoulder': (0, 255, 0),       # Green
            'armpit': (255, 0, 255),       # Magenta
            'chest': (0, 0, 255),          # Red
            'hem': (255, 165, 0),          # Orange
            'cuff': (128, 0, 128),         # Purple
            'waist': (0, 255, 255),        # Yellow
        }

        # Draw measurement points
        for name, point in measurement_points.items():
            # Determine color based on point type
            color = (0, 255, 0)  # Default green
            for key in colors:
                if key in name:
                    color = colors[key]
                    break

            # Draw circle
            cv2.circle(vis, point.position, 15, color, -1)
            cv2.circle(vis, point.position, 20, color, 3)

            # Add label
            label = f"{name}: {point.confidence:.2f}"
            cv2.putText(vis, label,
                       (point.position[0] + 25, point.position[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Add title
        cv2.putText(vis, f"Measurement Points - {self.garment_type.upper()}",
                   (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)

        # Draw measurement lines for visual clarity
        if self.garment_type == 'top':
            # Draw chest line
            if 'left_chest' in measurement_points and 'right_chest' in measurement_points:
                cv2.line(vis,
                        measurement_points['left_chest'].position,
                        measurement_points['right_chest'].position,
                        (0, 0, 255), 2)

            # Draw shoulder line
            if 'left_shoulder' in measurement_points and 'right_shoulder' in measurement_points:
                cv2.line(vis,
                        measurement_points['left_shoulder'].position,
                        measurement_points['right_shoulder'].position,
                        (0, 255, 0), 2)

            # Draw hem line
            if 'left_hem' in measurement_points and 'right_hem' in measurement_points:
                cv2.line(vis,
                        measurement_points['left_hem'].position,
                        measurement_points['right_hem'].position,
                        (255, 165, 0), 2)

        cv2.imwrite(output_path, vis)
        return vis

    def calculate_measurements(self, measurement_points: Dict[str, MeasurementPoint]) -> Dict[str, float]:
        """Calculate actual measurements from points"""

        measurements = {}

        if self.garment_type == 'top':
            # Chest width
            if 'left_chest' in measurement_points and 'right_chest' in measurement_points:
                chest_width = np.linalg.norm(
                    np.array(measurement_points['left_chest'].position) -
                    np.array(measurement_points['right_chest'].position)
                )
                measurements['chest_width_px'] = chest_width

            # Shoulder width
            if 'left_shoulder' in measurement_points and 'right_shoulder' in measurement_points:
                shoulder_width = np.linalg.norm(
                    np.array(measurement_points['left_shoulder'].position) -
                    np.array(measurement_points['right_shoulder'].position)
                )
                measurements['shoulder_width_px'] = shoulder_width

            # Hem width
            if 'left_hem' in measurement_points and 'right_hem' in measurement_points:
                hem_width = np.linalg.norm(
                    np.array(measurement_points['left_hem'].position) -
                    np.array(measurement_points['right_hem'].position)
                )
                measurements['hem_width_px'] = hem_width

            # Garment length (collar to hem)
            if 'collar' in measurement_points and 'left_hem' in measurement_points:
                length = abs(measurement_points['collar'].position[1] -
                           measurement_points['left_hem'].position[1])
                measurements['length_px'] = length

        elif self.garment_type == 'bottom':
            # Waist width
            if 'left_waist' in measurement_points and 'right_waist' in measurement_points:
                waist_width = np.linalg.norm(
                    np.array(measurement_points['left_waist'].position) -
                    np.array(measurement_points['right_waist'].position)
                )
                measurements['waist_width_px'] = waist_width

            # Hem width
            if 'left_hem' in measurement_points and 'right_hem' in measurement_points:
                hem_width = np.linalg.norm(
                    np.array(measurement_points['left_hem'].position) -
                    np.array(measurement_points['right_hem'].position)
                )
                measurements['hem_width_px'] = hem_width

            # Length
            if 'left_waist' in measurement_points and 'left_hem' in measurement_points:
                length = abs(measurement_points['left_waist'].position[1] -
                           measurement_points['left_hem'].position[1])
                measurements['length_px'] = length

        return measurements

def main():
    parser = argparse.ArgumentParser(description='Map structural keypoints to measurement points')
    parser.add_argument('image', help='Input image file')
    parser.add_argument('--keypoints-dir', default='structural_heatmap',
                       help='Directory containing keypoints JSON files')
    parser.add_argument('--output-dir', default='measurement_mapping',
                       help='Output directory for results')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Get base name
    base_name = os.path.splitext(os.path.basename(args.image))[0]

    # Path to keypoints file
    keypoints_file = os.path.join(args.keypoints_dir, f"{base_name}_keypoints.json")

    if not os.path.exists(keypoints_file):
        print(f"Error: Keypoints file not found: {keypoints_file}")
        return

    # Initialize mapper
    mapper = StructuralKeypointMapper()

    # Map keypoints to measurement points
    print(f"Mapping structural keypoints to measurement points for {args.image}...")
    measurement_points = mapper.map_keypoints_to_measurements(image, keypoints_file)

    # Save measurement points
    mp_data = {
        'garment_type': mapper.garment_type,
        'measurement_points': {
            name: {
                'position': list(point.position),
                'confidence': float(point.confidence),
                'source': point.source
            }
            for name, point in measurement_points.items()
        }
    }

    mp_file = os.path.join(args.output_dir, f"{base_name}_measurement_points.json")
    with open(mp_file, 'w') as f:
        json.dump(mp_data, f, indent=2)

    print(f"Saved measurement points to {mp_file}")

    # Visualize measurement points
    vis_path = os.path.join(args.output_dir, f"{base_name}_measurement_visualization.jpg")
    mapper.visualize_measurement_points(image, measurement_points, vis_path)
    print(f"Saved visualization to {vis_path}")

    # Calculate measurements
    measurements = mapper.calculate_measurements(measurement_points)

    # Save measurements
    meas_file = os.path.join(args.output_dir, f"{base_name}_measurements.json")
    with open(meas_file, 'w') as f:
        json.dump(measurements, f, indent=2)

    print(f"Saved measurements to {meas_file}")

    # Print summary
    print("\n" + "="*60)
    print(f"MEASUREMENT MAPPING COMPLETE - {mapper.garment_type.upper()}")
    print("="*60)
    print(f"Total measurement points found: {len(measurement_points)}")

    print("\nMeasurement Points:")
    for name, point in measurement_points.items():
        print(f"  - {name}: Position {point.position}, Confidence: {point.confidence:.3f}")

    print("\nCalculated Measurements (in pixels):")
    for name, value in measurements.items():
        print(f"  - {name}: {value:.1f}")

    print("="*60)

if __name__ == '__main__':
    main()