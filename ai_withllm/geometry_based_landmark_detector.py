#!/usr/bin/env python3
"""
Geometry-based landmark detector that identifies anatomical points
based on actual garment structure rather than fixed zones.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class GeometryBasedLandmarkDetector:
    """Detects landmarks based on garment geometry and structure."""

    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode

    def detect_garment_contour(self, image: np.ndarray) -> np.ndarray:
        """Detect the main garment contour."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Create binary mask (assume white/light background)
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Get largest contour (main garment)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            return largest
        return np.array([])

    def find_sleeve_body_junctions(self, contour: np.ndarray, image_shape: tuple) -> Dict:
        """Find where sleeves meet the body (armpits)."""
        if len(contour) == 0:
            return {}

        # Get contour points
        points = contour.reshape(-1, 2)

        # Find horizontal extent at different heights
        height, width = image_shape[:2]

        # Analyze width variations to find sleeve junctions
        width_profile = []
        y_values = []

        for y in range(0, height, 10):  # Sample every 10 pixels
            x_coords = points[np.abs(points[:, 1] - y) < 5][:, 0] if len(points) > 0 else []
            if len(x_coords) > 1:
                width_at_y = np.max(x_coords) - np.min(x_coords)
                width_profile.append(width_at_y)
                y_values.append(y)

        if not width_profile:
            return {}

        width_profile = np.array(width_profile)
        y_values = np.array(y_values)

        # Find sudden width increases (indicating sleeves)
        if len(width_profile) > 1:
            width_changes = np.diff(width_profile)

            # Look for significant width increases in upper portion
            upper_third_idx = len(width_changes) // 3

            # Find peaks in width change (sleeve starts)
            significant_increases = np.where(width_changes[:upper_third_idx] > np.mean(width_profile) * 0.1)[0]

            if len(significant_increases) > 0:
                # Armpit is where width starts increasing significantly
                armpit_y = y_values[significant_increases[-1]]

                # Find x coordinates at this y level
                armpit_points = points[np.abs(points[:, 1] - armpit_y) < 20]

                if len(armpit_points) > 1:
                    x_coords = armpit_points[:, 0]

                    # Find the junction points (where sleeve meets body)
                    # These are typically interior points where width narrows
                    x_sorted = np.sort(x_coords)

                    # Get points that are about 20-30% in from edges
                    left_junction_x = x_sorted[len(x_sorted) // 4]
                    right_junction_x = x_sorted[3 * len(x_sorted) // 4]

                    return {
                        'left': (int(left_junction_x), int(armpit_y)),
                        'right': (int(right_junction_x), int(armpit_y))
                    }

        return {}

    def find_shoulders(self, contour: np.ndarray, collar_point: Optional[Tuple] = None) -> Dict:
        """Find shoulder points where sleeves begin."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Find topmost points
        top_y = np.min(points[:, 1])

        # Get points in top region
        top_region = points[points[:, 1] < top_y + 100]

        if len(top_region) > 0:
            # Find leftmost and rightmost in top region
            left_x = np.min(top_region[:, 0])
            right_x = np.max(top_region[:, 0])

            # Find actual shoulder points (where sleeve curves begin)
            # Look for points that are horizontally extreme but not at very top
            shoulder_region = points[(points[:, 1] > top_y + 20) & (points[:, 1] < top_y + 150)]

            if len(shoulder_region) > 0:
                # Group by x coordinate
                left_shoulder_candidates = shoulder_region[shoulder_region[:, 0] < np.mean(shoulder_region[:, 0])]
                right_shoulder_candidates = shoulder_region[shoulder_region[:, 0] > np.mean(shoulder_region[:, 0])]

                shoulders = {}

                if len(left_shoulder_candidates) > 0:
                    # Find the outermost point that's not too low
                    left_idx = np.argmin(left_shoulder_candidates[:, 0])
                    shoulders['left'] = tuple(left_shoulder_candidates[left_idx].astype(int))

                if len(right_shoulder_candidates) > 0:
                    # Find the outermost point that's not too low
                    right_idx = np.argmax(right_shoulder_candidates[:, 0])
                    shoulders['right'] = tuple(right_shoulder_candidates[right_idx].astype(int))

                return shoulders

        return {}

    def find_chest_line(self, contour: np.ndarray, armpits: Dict) -> Dict:
        """Find chest measurement points (across the torso below armpits)."""
        if len(contour) == 0 or not armpits:
            return {}

        points = contour.reshape(-1, 2)

        # Chest is typically measured just below armpits
        if 'left' in armpits and 'right' in armpits:
            armpit_y = (armpits['left'][1] + armpits['right'][1]) // 2

            # Chest line is slightly below armpits (about 50-100 pixels)
            chest_y = armpit_y + 80

            # Find contour points at chest level
            chest_points = points[np.abs(points[:, 1] - chest_y) < 30]

            if len(chest_points) > 1:
                # Find leftmost and rightmost points on body (not sleeves)
                x_coords = chest_points[:, 0]

                # Filter out sleeve points (too far from center)
                center_x = np.mean(x_coords)
                body_width = np.std(x_coords)

                # Body points are within reasonable distance from center
                body_mask = np.abs(x_coords - center_x) < body_width * 1.5
                body_points = chest_points[body_mask]

                if len(body_points) > 1:
                    left_chest_x = np.min(body_points[:, 0])
                    right_chest_x = np.max(body_points[:, 0])

                    return {
                        'left': (int(left_chest_x), int(chest_y)),
                        'right': (int(right_chest_x), int(chest_y))
                    }

        return {}

    def find_collar(self, contour: np.ndarray) -> Optional[Tuple]:
        """Find collar center point."""
        if len(contour) == 0:
            return None

        points = contour.reshape(-1, 2)

        # Collar is at the top center
        top_y = np.min(points[:, 1])
        top_points = points[points[:, 1] < top_y + 50]

        if len(top_points) > 0:
            center_x = np.mean(top_points[:, 0])
            return (int(center_x), int(top_y))

        return None

    def find_hem(self, contour: np.ndarray) -> Dict:
        """Find hem points at bottom of garment."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Hem is at the bottom
        bottom_y = np.max(points[:, 1])
        hem_points = points[points[:, 1] > bottom_y - 50]

        if len(hem_points) > 1:
            left_x = np.min(hem_points[:, 0])
            right_x = np.max(hem_points[:, 0])
            center_x = np.mean(hem_points[:, 0])

            return {
                'left': (int(left_x), int(bottom_y)),
                'right': (int(right_x), int(bottom_y)),
                'center': (int(center_x), int(bottom_y))
            }

        return {}

    def find_cuffs(self, contour: np.ndarray, shoulders: Dict) -> Dict:
        """Find cuff points at sleeve ends."""
        if len(contour) == 0 or not shoulders:
            return {}

        points = contour.reshape(-1, 2)
        cuffs = {}

        # For each side, find the furthest point from shoulder
        if 'left' in shoulders:
            shoulder_left = shoulders['left']
            # Find points on left side
            left_points = points[points[:, 0] < shoulder_left[0]]

            if len(left_points) > 0:
                # Find point furthest from shoulder
                distances = np.sqrt((left_points[:, 0] - shoulder_left[0])**2 +
                                   (left_points[:, 1] - shoulder_left[1])**2)
                furthest_idx = np.argmax(distances)
                cuffs['left'] = tuple(left_points[furthest_idx].astype(int))

        if 'right' in shoulders:
            shoulder_right = shoulders['right']
            # Find points on right side
            right_points = points[points[:, 0] > shoulder_right[0]]

            if len(right_points) > 0:
                # Find point furthest from shoulder
                distances = np.sqrt((right_points[:, 0] - shoulder_right[0])**2 +
                                   (right_points[:, 1] - shoulder_right[1])**2)
                furthest_idx = np.argmax(distances)
                cuffs['right'] = tuple(right_points[furthest_idx].astype(int))

        return cuffs

    def detect_landmarks(self, image_path: str) -> Dict:
        """Detect all landmarks for a garment image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Detect garment contour
        contour = self.detect_garment_contour(image)

        # Find all landmark types
        collar = self.find_collar(contour)
        shoulders = self.find_shoulders(contour, collar)
        armpits = self.find_sleeve_body_junctions(contour, image.shape)
        chest = self.find_chest_line(contour, armpits)
        hem = self.find_hem(contour)
        cuffs = self.find_cuffs(contour, shoulders)

        # Compile results
        landmarks = {}

        if collar:
            landmarks['collar_center'] = {
                'position': collar,
                'type': 'collar',
                'side': 'center'
            }

        for side in ['left', 'right']:
            if side in shoulders:
                landmarks[f'shoulder_{side}'] = {
                    'position': shoulders[side],
                    'type': 'shoulder',
                    'side': side
                }

            if side in armpits:
                landmarks[f'armpit_{side}'] = {
                    'position': armpits[side],
                    'type': 'armpit',
                    'side': side
                }

            if side in chest:
                landmarks[f'chest_{side}'] = {
                    'position': chest[side],
                    'type': 'chest',
                    'side': side
                }

            if side in hem:
                landmarks[f'hem_{side}'] = {
                    'position': hem[side],
                    'type': 'hem',
                    'side': side
                }

            if side in cuffs:
                landmarks[f'cuff_{side}'] = {
                    'position': cuffs[side],
                    'type': 'cuff',
                    'side': side
                }

        if 'center' in hem:
            landmarks['hem_center'] = {
                'position': hem['center'],
                'type': 'hem',
                'side': 'center'
            }

        # Calculate measurements
        measurements = self.calculate_measurements(landmarks)

        # Create visualization
        if self.debug_mode:
            vis_image = self.visualize_landmarks(image, landmarks, contour)
            output_path = image_path.replace('.jpg', '_geometry_landmarks.jpg')
            cv2.imwrite(output_path, vis_image)
            print(f"Saved visualization to {output_path}")

        return {
            'landmarks': landmarks,
            'measurements': measurements
        }

    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """Calculate measurements from landmarks."""
        measurements = {}

        # Shoulder width
        if 'shoulder_left' in landmarks and 'shoulder_right' in landmarks:
            left = landmarks['shoulder_left']['position']
            right = landmarks['shoulder_right']['position']
            measurements['shoulder_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Chest width
        if 'chest_left' in landmarks and 'chest_right' in landmarks:
            left = landmarks['chest_left']['position']
            right = landmarks['chest_right']['position']
            measurements['chest_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Armpit span
        if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
            left = landmarks['armpit_left']['position']
            right = landmarks['armpit_right']['position']
            measurements['armpit_span'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Hem width
        if 'hem_left' in landmarks and 'hem_right' in landmarks:
            left = landmarks['hem_left']['position']
            right = landmarks['hem_right']['position']
            measurements['hem_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Sleeve length
        if 'shoulder_left' in landmarks and 'cuff_left' in landmarks:
            shoulder = landmarks['shoulder_left']['position']
            cuff = landmarks['cuff_left']['position']
            measurements['sleeve_length_left'] = np.sqrt((cuff[0] - shoulder[0])**2 + (cuff[1] - shoulder[1])**2)

        if 'shoulder_right' in landmarks and 'cuff_right' in landmarks:
            shoulder = landmarks['shoulder_right']['position']
            cuff = landmarks['cuff_right']['position']
            measurements['sleeve_length_right'] = np.sqrt((cuff[0] - shoulder[0])**2 + (cuff[1] - shoulder[1])**2)

        # Garment length
        if 'collar_center' in landmarks and 'hem_center' in landmarks:
            collar = landmarks['collar_center']['position']
            hem = landmarks['hem_center']['position']
            measurements['garment_length'] = np.sqrt((hem[0] - collar[0])**2 + (hem[1] - collar[1])**2)

        return measurements

    def visualize_landmarks(self, image: np.ndarray, landmarks: Dict, contour: np.ndarray) -> np.ndarray:
        """Visualize landmarks on image."""
        vis = image.copy()

        # Draw contour
        if len(contour) > 0:
            cv2.drawContours(vis, [contour], -1, (0, 255, 0), 2)

        # Define colors for each landmark type
        colors = {
            'collar': (255, 255, 0),    # Yellow
            'shoulder': (255, 0, 0),     # Red
            'armpit': (0, 255, 255),     # Cyan
            'chest': (255, 0, 255),      # Magenta
            'hem': (0, 0, 255),          # Blue
            'cuff': (128, 255, 0)        # Green
        }

        # Draw landmarks
        for name, info in landmarks.items():
            pos = info['position']
            ltype = info['type']
            color = colors.get(ltype, (255, 255, 255))

            # Draw circle
            cv2.circle(vis, pos, 8, color, -1)
            cv2.circle(vis, pos, 10, (0, 0, 0), 2)

            # Add label
            label = name.replace('_', ' ').title()
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        # Draw measurement lines
        line_pairs = [
            ('shoulder_left', 'shoulder_right', 'Shoulders'),
            ('chest_left', 'chest_right', 'Chest'),
            ('armpit_left', 'armpit_right', 'Armpits'),
            ('hem_left', 'hem_right', 'Hem'),
            ('shoulder_left', 'cuff_left', 'L Sleeve'),
            ('shoulder_right', 'cuff_right', 'R Sleeve')
        ]

        for left_key, right_key, label in line_pairs:
            if left_key in landmarks and right_key in landmarks:
                left_pos = landmarks[left_key]['position']
                right_pos = landmarks[right_key]['position']

                # Draw line
                cv2.line(vis, left_pos, right_pos, (0, 255, 0), 2)

                # Add measurement label
                mid_x = (left_pos[0] + right_pos[0]) // 2
                mid_y = (left_pos[1] + right_pos[1]) // 2
                distance = np.sqrt((right_pos[0] - left_pos[0])**2 + (right_pos[1] - left_pos[1])**2)

                text = f"{label}: {distance:.0f}px"
                cv2.putText(vis, text, (mid_x - 50, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                cv2.putText(vis, text, (mid_x - 50, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)

        return vis


def main():
    """Test the geometry-based detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='geometry_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = GeometryBasedLandmarkDetector(debug_mode=True)

    # Detect landmarks
    print(f"Processing {args.image_path}...")
    results = detector.detect_landmarks(args.image_path)

    # Save results
    image_name = Path(args.image_path).stem
    json_path = output_dir / f"{image_name}_geometry_measurements.json"

    with open(json_path, 'w') as f:
        # Convert tuples to lists for JSON serialization
        json_results = {
            'landmarks': {},
            'measurements': {}
        }

        for key, value in results['landmarks'].items():
            json_results['landmarks'][key] = {
                'position': list(value['position']),
                'type': value['type'],
                'side': value['side']
            }

        for key, value in results['measurements'].items():
            json_results['measurements'][key] = float(value)

        json.dump(json_results, f, indent=2)

    print(f"Saved measurements to {json_path}")

    # Print measurements
    print("\nDetected Landmarks:")
    for name, info in results['landmarks'].items():
        print(f"  {name}: {info['position']}")

    print("\nMeasurements:")
    for name, value in results['measurements'].items():
        print(f"  {name}: {value:.1f} pixels")


if __name__ == '__main__':
    main()