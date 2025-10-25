#!/usr/bin/env python3
"""
Contour-based anatomical landmark detector that finds actual garment features
based on contour analysis and structural understanding.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path
from scipy import signal, ndimage
from scipy.spatial import distance


class ContourAnatomicalDetector:
    """Detects anatomical landmarks by analyzing garment contours."""

    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode

    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess image to extract garment mask and contour."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        # Use adaptive thresholding for better edge detection
        edges = cv2.Canny(filtered, 30, 100)

        # Close gaps in edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Get largest contour
            main_contour = max(contours, key=cv2.contourArea)

            # Create filled mask
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [main_contour], -1, 255, -1)

            # Fill any holes
            mask = ndimage.binary_fill_holes(mask).astype(np.uint8) * 255

            # Get clean contour from filled mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                return max(contours, key=cv2.contourArea), mask

        return np.array([]), np.zeros(gray.shape, np.uint8)

    def find_collar_region(self, contour: np.ndarray) -> Tuple[Optional[Tuple[int, int]], int]:
        """Find the collar/neckline region at the top center of the garment."""
        if len(contour) == 0:
            return None, 0

        points = contour.reshape(-1, 2)

        # Find the topmost point
        top_y = np.min(points[:, 1])

        # Get points in the top 5% of the garment
        height_range = np.max(points[:, 1]) - top_y
        top_threshold = top_y + height_range * 0.05

        top_points = points[points[:, 1] <= top_threshold]

        if len(top_points) > 0:
            # Collar is at the center of top points
            center_x = int(np.mean(top_points[:, 0]))
            collar_point = (center_x, int(top_y))
            return collar_point, int(top_threshold)

        return None, 0

    def find_shoulder_points(self, contour: np.ndarray, collar_y: int) -> Dict:
        """Find shoulder points where sleeves meet the body at the top."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Shoulders are at the top outer edges, near collar level
        # Look for points slightly below collar (within 10-15% of garment height)
        garment_height = np.max(points[:, 1]) - np.min(points[:, 1])
        shoulder_y_min = collar_y
        shoulder_y_max = collar_y + garment_height * 0.1

        # Get points in shoulder region
        shoulder_candidates = points[(points[:, 1] >= shoulder_y_min) &
                                    (points[:, 1] <= shoulder_y_max)]

        if len(shoulder_candidates) < 2:
            return {}

        # Find the widest points in this region (actual shoulders)
        center_x = np.mean(shoulder_candidates[:, 0])

        # Left shoulder: leftmost point in shoulder region
        left_candidates = shoulder_candidates[shoulder_candidates[:, 0] < center_x]
        if len(left_candidates) > 0:
            left_shoulder_idx = np.argmin(left_candidates[:, 0])
            left_shoulder = tuple(left_candidates[left_shoulder_idx].astype(int))
        else:
            left_shoulder = None

        # Right shoulder: rightmost point in shoulder region
        right_candidates = shoulder_candidates[shoulder_candidates[:, 0] > center_x]
        if len(right_candidates) > 0:
            right_shoulder_idx = np.argmax(right_candidates[:, 0])
            right_shoulder = tuple(right_candidates[right_shoulder_idx].astype(int))
        else:
            right_shoulder = None

        shoulders = {}
        if left_shoulder:
            shoulders['left'] = left_shoulder
        if right_shoulder:
            shoulders['right'] = right_shoulder

        return shoulders

    def find_sleeve_body_junction(self, mask: np.ndarray, shoulders: Dict) -> Dict:
        """Find armpit points where sleeves meet the body."""
        if not shoulders or len(mask) == 0:
            return {}

        height, width = mask.shape
        armpits = {}

        # Start from shoulder level and move down
        if 'left' in shoulders and 'right' in shoulders:
            shoulder_y = (shoulders['left'][1] + shoulders['right'][1]) // 2

            # Analyze width profile starting from shoulders
            max_search_distance = height // 3  # Don't search too far down

            # Track width changes
            prev_width = shoulders['right'][0] - shoulders['left'][0]

            for y_offset in range(20, max_search_distance, 5):
                y = shoulder_y + y_offset
                if y >= height:
                    break

                # Get garment width at this level
                row = mask[y, :]
                nonzero = np.nonzero(row)[0]

                if len(nonzero) < 2:
                    continue

                current_width = nonzero[-1] - nonzero[0]

                # Look for where width stops increasing significantly
                # (indicates we've reached the armpit level)
                if current_width > prev_width * 1.3:  # Significant increase means we're at sleeve level
                    # Find the inner edges where sleeve meets body
                    # This is typically where there's a concave region

                    # Analyze the contour curvature at this level
                    center = (nonzero[0] + nonzero[-1]) // 2

                    # Left armpit: look for inner edge on left side
                    left_region = nonzero[nonzero < center]
                    if len(left_region) > 10:
                        # Find the rightmost point of left body section
                        # (before sleeve extends out)
                        left_armpit_x = left_region[-len(left_region)//3]  # Inner third
                        armpits['left'] = (int(left_armpit_x), y)

                    # Right armpit: look for inner edge on right side
                    right_region = nonzero[nonzero > center]
                    if len(right_region) > 10:
                        # Find the leftmost point of right body section
                        right_armpit_x = right_region[len(right_region)//3]  # Inner third
                        armpits['right'] = (int(right_armpit_x), y)

                    if armpits:
                        break

                prev_width = current_width

        return armpits

    def find_chest_measurement_points(self, mask: np.ndarray, armpits: Dict) -> Dict:
        """Find chest measurement points on the torso."""
        if not armpits or len(mask) == 0:
            return {}

        height, width = mask.shape

        # Chest is measured below armpits, on the body (not sleeves)
        armpit_y = (armpits['left'][1] + armpits['right'][1]) // 2

        # Measure chest about 50-100 pixels below armpits
        chest_y = min(armpit_y + 70, height - 1)

        # Find body edges (excluding sleeves)
        # The body is the narrower central portion
        chest_row = mask[chest_y, :]
        nonzero = np.nonzero(chest_row)[0]

        if len(nonzero) < 2:
            return {}

        # Find the continuous central region (body)
        # Look for the largest continuous segment
        diffs = np.diff(nonzero)
        gaps = np.where(diffs > 10)[0]  # Find gaps larger than 10 pixels

        if len(gaps) > 0:
            # Multiple segments - find the central one
            segments = []
            start_idx = 0

            for gap_idx in gaps:
                segment = nonzero[start_idx:gap_idx+1]
                if len(segment) > 0:
                    segments.append(segment)
                start_idx = gap_idx + 1

            # Add last segment
            if start_idx < len(nonzero):
                segments.append(nonzero[start_idx:])

            # Find the segment closest to image center
            image_center = width // 2
            best_segment = None
            best_distance = float('inf')

            for segment in segments:
                if len(segment) > 20:  # Minimum width for body
                    segment_center = (segment[0] + segment[-1]) // 2
                    dist = abs(segment_center - image_center)
                    if dist < best_distance:
                        best_distance = dist
                        best_segment = segment

            if best_segment is not None:
                return {
                    'left': (int(best_segment[0]), chest_y),
                    'right': (int(best_segment[-1]), chest_y)
                }
        else:
            # Single continuous segment
            # Use inner portion (excluding potential sleeve areas)
            segment_width = nonzero[-1] - nonzero[0]
            inset = segment_width // 5  # Inset by 20% on each side

            return {
                'left': (int(nonzero[0] + inset), chest_y),
                'right': (int(nonzero[-1] - inset), chest_y)
            }

        return {}

    def find_hem_points(self, contour: np.ndarray) -> Dict:
        """Find hem points at the bottom of the garment."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Hem is at the bottom
        bottom_y = np.max(points[:, 1])

        # Get points near bottom
        hem_region = points[points[:, 1] > bottom_y - 30]

        if len(hem_region) > 0:
            left_x = int(np.min(hem_region[:, 0]))
            right_x = int(np.max(hem_region[:, 0]))
            center_x = int(np.mean(hem_region[:, 0]))

            return {
                'left': (left_x, int(bottom_y)),
                'right': (right_x, int(bottom_y)),
                'center': (center_x, int(bottom_y))
            }

        return {}

    def find_cuff_points(self, contour: np.ndarray, shoulders: Dict) -> Dict:
        """Find cuff points at the end of sleeves."""
        if len(contour) == 0 or not shoulders:
            return {}

        points = contour.reshape(-1, 2)
        cuffs = {}

        # For each shoulder, trace along the sleeve to find the cuff
        if 'left' in shoulders:
            shoulder_left = np.array(shoulders['left'])

            # Find points that are:
            # 1. On the left side of the garment
            # 2. Below shoulder level
            # 3. Far from shoulder (sleeve end)
            left_candidates = points[(points[:, 0] < shoulder_left[0] + 100) &  # Left side
                                    (points[:, 1] > shoulder_left[1] + 50)]    # Below shoulder

            if len(left_candidates) > 0:
                # Find point with maximum distance from shoulder
                distances = np.sqrt(np.sum((left_candidates - shoulder_left)**2, axis=1))
                max_dist_idx = np.argmax(distances)
                cuffs['left'] = tuple(left_candidates[max_dist_idx].astype(int))

        if 'right' in shoulders:
            shoulder_right = np.array(shoulders['right'])

            # Find points on right side
            right_candidates = points[(points[:, 0] > shoulder_right[0] - 100) &  # Right side
                                     (points[:, 1] > shoulder_right[1] + 50)]     # Below shoulder

            if len(right_candidates) > 0:
                # Find point with maximum distance from shoulder
                distances = np.sqrt(np.sum((right_candidates - shoulder_right)**2, axis=1))
                max_dist_idx = np.argmax(distances)
                cuffs['right'] = tuple(right_candidates[max_dist_idx].astype(int))

        return cuffs

    def detect_landmarks(self, image_path: str) -> Dict:
        """Main detection pipeline."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Preprocess and get contour
        contour, mask = self.preprocess_image(image)

        if len(contour) == 0:
            print("Warning: Could not extract garment contour")
            return {'landmarks': {}, 'measurements': {}}

        # Find landmarks in order
        collar, collar_y = self.find_collar_region(contour)
        shoulders = self.find_shoulder_points(contour, collar_y)
        armpits = self.find_sleeve_body_junction(mask, shoulders)
        chest = self.find_chest_measurement_points(mask, armpits)
        hem = self.find_hem_points(contour)
        cuffs = self.find_cuff_points(contour, shoulders)

        # Compile landmarks
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
            vis = self.visualize_results(image, landmarks, contour)
            output_path = image_path.replace('.jpg', '_contour_anatomical.jpg').replace('.png', '_contour_anatomical.png')
            cv2.imwrite(output_path, vis)
            print(f"Saved visualization to {output_path}")

        return {
            'landmarks': landmarks,
            'measurements': measurements
        }

    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """Calculate garment measurements from landmarks."""
        measurements = {}

        # Helper function for distance calculation
        def calc_distance(p1, p2):
            return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

        # Shoulder width
        if 'shoulder_left' in landmarks and 'shoulder_right' in landmarks:
            measurements['shoulder_width'] = calc_distance(
                landmarks['shoulder_left']['position'],
                landmarks['shoulder_right']['position']
            )

        # Chest width
        if 'chest_left' in landmarks and 'chest_right' in landmarks:
            measurements['chest_width'] = calc_distance(
                landmarks['chest_left']['position'],
                landmarks['chest_right']['position']
            )

        # Armpit span
        if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
            measurements['armpit_span'] = calc_distance(
                landmarks['armpit_left']['position'],
                landmarks['armpit_right']['position']
            )

        # Hem width
        if 'hem_left' in landmarks and 'hem_right' in landmarks:
            measurements['hem_width'] = calc_distance(
                landmarks['hem_left']['position'],
                landmarks['hem_right']['position']
            )

        # Sleeve lengths
        if 'shoulder_left' in landmarks and 'cuff_left' in landmarks:
            measurements['sleeve_length_left'] = calc_distance(
                landmarks['shoulder_left']['position'],
                landmarks['cuff_left']['position']
            )

        if 'shoulder_right' in landmarks and 'cuff_right' in landmarks:
            measurements['sleeve_length_right'] = calc_distance(
                landmarks['shoulder_right']['position'],
                landmarks['cuff_right']['position']
            )

        # Garment length
        if 'collar_center' in landmarks and 'hem_center' in landmarks:
            collar_y = landmarks['collar_center']['position'][1]
            hem_y = landmarks['hem_center']['position'][1]
            measurements['garment_length'] = abs(hem_y - collar_y)

        # Sleeve span (cuff to cuff)
        if 'cuff_left' in landmarks and 'cuff_right' in landmarks:
            measurements['sleeve_span'] = calc_distance(
                landmarks['cuff_left']['position'],
                landmarks['cuff_right']['position']
            )

        return measurements

    def visualize_results(self, image: np.ndarray, landmarks: Dict, contour: np.ndarray) -> np.ndarray:
        """Create visualization with landmarks and measurements."""
        vis = image.copy()

        # Draw contour
        if len(contour) > 0:
            cv2.drawContours(vis, [contour], -1, (0, 255, 0), 2)

        # Color scheme for different landmark types
        colors = {
            'collar': (255, 255, 0),     # Yellow
            'shoulder': (0, 0, 255),     # Red
            'armpit': (255, 0, 255),     # Magenta
            'chest': (0, 255, 255),      # Cyan
            'hem': (255, 100, 0),        # Orange
            'cuff': (0, 255, 0)          # Green
        }

        # Draw landmarks
        for name, info in landmarks.items():
            pos = info['position']
            ltype = info['type']
            color = colors.get(ltype, (255, 255, 255))

            # Draw point
            cv2.circle(vis, pos, 10, color, -1)
            cv2.circle(vis, pos, 12, (0, 0, 0), 2)

            # Add label
            label = name.replace('_', ' ').title()
            # Add background for better readability
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(vis, (pos[0] + 12, pos[1] - h - 2),
                         (pos[0] + 15 + w, pos[1] + 5), (255, 255, 255), -1)
            cv2.putText(vis, label, (pos[0] + 15, pos[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        # Draw measurement lines
        measurements = [
            ('shoulder_left', 'shoulder_right', 'Shoulder', (0, 0, 255)),
            ('chest_left', 'chest_right', 'Chest', (0, 255, 255)),
            ('armpit_left', 'armpit_right', 'Armpit', (255, 0, 255)),
            ('hem_left', 'hem_right', 'Hem', (255, 100, 0)),
            ('shoulder_left', 'cuff_left', 'L Sleeve', (0, 255, 0)),
            ('shoulder_right', 'cuff_right', 'R Sleeve', (0, 255, 0)),
            ('cuff_left', 'cuff_right', 'Sleeve Span', (100, 255, 100))
        ]

        for left_key, right_key, label, color in measurements:
            if left_key in landmarks and right_key in landmarks:
                p1 = landmarks[left_key]['position']
                p2 = landmarks[right_key]['position']

                # Draw line
                cv2.line(vis, p1, p2, color, 2)

                # Calculate midpoint
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2

                # Calculate distance
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

                # Add measurement text
                text = f"{label}: {dist:.0f}px"
                (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(vis, (mid_x - w//2 - 5, mid_y - h - 5),
                            (mid_x + w//2 + 5, mid_y + 5), (255, 255, 255), -1)
                cv2.putText(vis, text, (mid_x - w//2, mid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        return vis


def main():
    """Test the contour-based anatomical detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='contour_anatomical_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = ContourAnatomicalDetector(debug_mode=True)

    # Process image
    print(f"Processing {args.image_path}...")
    results = detector.detect_landmarks(args.image_path)

    # Save results
    image_name = Path(args.image_path).stem
    json_path = output_dir / f"{image_name}_measurements.json"

    # Prepare JSON data
    json_data = {
        'landmarks': {},
        'measurements': {}
    }

    for key, value in results['landmarks'].items():
        json_data['landmarks'][key] = {
            'position': [int(p) for p in value['position']],
            'type': value['type'],
            'side': value['side']
        }

    for key, value in results['measurements'].items():
        json_data['measurements'][key] = float(value)

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"Saved results to {json_path}")

    # Print summary
    print("\nDetected Landmarks:")
    for name in sorted(results['landmarks'].keys()):
        info = results['landmarks'][name]
        print(f"  {name}: {info['position']}")

    print("\nMeasurements:")
    for name, value in results['measurements'].items():
        print(f"  {name}: {value:.1f} pixels")


if __name__ == '__main__':
    main()