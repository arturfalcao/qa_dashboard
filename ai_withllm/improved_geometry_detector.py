#!/usr/bin/env python3
"""
Improved geometry-based landmark detector with better contour detection
and more robust landmark finding.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path
from scipy import signal
from scipy.ndimage import binary_fill_holes


class ImprovedGeometryDetector:
    """Advanced geometry-based landmark detection."""

    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode

    def segment_garment(self, image: np.ndarray) -> np.ndarray:
        """Improved garment segmentation."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Apply morphological operations to connect edges
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        dilated = cv2.dilate(closed, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create mask from largest contour
        if contours:
            largest = max(contours, key=cv2.contourArea)
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [largest], -1, 255, -1)

            # Fill holes
            mask = binary_fill_holes(mask).astype(np.uint8) * 255

            # Get clean contour from mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                return max(contours, key=cv2.contourArea), mask

        return np.array([]), np.zeros(gray.shape, np.uint8)

    def analyze_width_profile(self, mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Analyze garment width at different heights."""
        height, width = mask.shape

        widths = []
        y_positions = []

        for y in range(0, height, 5):  # Sample every 5 pixels
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) > 0:
                width_at_y = nonzero[-1] - nonzero[0]
                widths.append(width_at_y)
                y_positions.append(y)

        return np.array(widths), np.array(y_positions)

    def find_sleeve_body_junction(self, mask: np.ndarray, widths: np.ndarray, y_positions: np.ndarray) -> Dict:
        """Find where sleeves meet the body using width analysis."""
        if len(widths) == 0:
            return {}

        height, width = mask.shape

        # Smooth the width profile
        if len(widths) > 20:
            widths_smooth = signal.savgol_filter(widths, min(51, len(widths) // 2 * 2 + 1), 3)
        else:
            widths_smooth = widths

        # Find local maxima (potential sleeve positions)
        # Look in upper 40% of garment
        upper_portion = len(widths_smooth) * 2 // 5

        if upper_portion > 10:
            upper_widths = widths_smooth[:upper_portion]

            # Find the widest point in upper portion (usually sleeves)
            max_width_idx = np.argmax(upper_widths)
            sleeve_y = y_positions[max_width_idx]

            # Find where width starts decreasing significantly (armpit level)
            # Look for the point where width reduces to ~70% of max
            target_width = upper_widths[max_width_idx] * 0.7

            # Search downward from max width point
            armpit_idx = max_width_idx
            for i in range(max_width_idx, min(len(widths_smooth), upper_portion + 20)):
                if widths_smooth[i] < target_width:
                    armpit_idx = i
                    break

            armpit_y = y_positions[armpit_idx]

            # Find x coordinates at armpit level
            row = mask[armpit_y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) > 0:
                # Find inner edges (where sleeves meet body)
                # These are typically 25-35% in from edges
                x_min, x_max = nonzero[0], nonzero[-1]
                x_range = x_max - x_min

                left_armpit_x = x_min + int(x_range * 0.3)
                right_armpit_x = x_max - int(x_range * 0.3)

                return {
                    'left': (left_armpit_x, armpit_y),
                    'right': (right_armpit_x, armpit_y)
                }

        return {}

    def find_shoulders_from_contour(self, contour: np.ndarray, mask: np.ndarray) -> Dict:
        """Find shoulder points more accurately."""
        if len(contour) == 0:
            return {}

        height, width = mask.shape
        points = contour.reshape(-1, 2)

        # Find top of garment
        top_y = np.min(points[:, 1])

        # Shoulders are where the garment starts widening (top outer corners)
        # Look in region just below the very top
        shoulder_region_y_min = top_y + 20
        shoulder_region_y_max = top_y + height * 0.15  # Top 15%

        shoulder_points = points[(points[:, 1] > shoulder_region_y_min) &
                                 (points[:, 1] < shoulder_region_y_max)]

        if len(shoulder_points) > 0:
            center_x = np.mean(shoulder_points[:, 0])

            # Find outermost points on each side
            left_points = shoulder_points[shoulder_points[:, 0] < center_x]
            right_points = shoulder_points[shoulder_points[:, 0] > center_x]

            shoulders = {}

            if len(left_points) > 0:
                # Get the leftmost point that's not too high
                left_shoulder = left_points[np.argmin(left_points[:, 0])]
                shoulders['left'] = tuple(left_shoulder.astype(int))

            if len(right_points) > 0:
                # Get the rightmost point that's not too high
                right_shoulder = right_points[np.argmax(right_points[:, 0])]
                shoulders['right'] = tuple(right_shoulder.astype(int))

            return shoulders

        return {}

    def find_chest_measurement(self, mask: np.ndarray, armpits: Dict) -> Dict:
        """Find chest measurement points below armpits."""
        if not armpits:
            return {}

        height, width = mask.shape

        # Chest is measured 2-4 inches (50-100 pixels) below armpits
        armpit_y = (armpits['left'][1] + armpits['right'][1]) // 2
        chest_y = min(armpit_y + 80, height - 1)

        # Find garment edges at chest level
        chest_row = mask[chest_y, :]
        nonzero = np.nonzero(chest_row)[0]

        if len(nonzero) > 0:
            # Find the main body edges (excluding sleeves)
            x_min, x_max = nonzero[0], nonzero[-1]
            x_center = (x_min + x_max) // 2

            # Look for body edges (where width is consistent)
            # Check a few rows around chest level
            body_edges = []
            for y_offset in range(-10, 11, 5):
                check_y = max(0, min(height - 1, chest_y + y_offset))
                row = mask[check_y, :]
                nonzero = np.nonzero(row)[0]

                if len(nonzero) > 0:
                    # Find edges that are reasonably close to center
                    center = np.mean(nonzero)
                    width = nonzero[-1] - nonzero[0]

                    # Body width is typically 40-60% of total width at this level
                    body_left = None
                    body_right = None

                    for x in nonzero:
                        if body_left is None and x > center - width * 0.3:
                            body_left = x
                            break

                    for x in reversed(nonzero):
                        if body_right is None and x < center + width * 0.3:
                            body_right = x
                            break

                    if body_left and body_right:
                        body_edges.append((body_left, body_right))

            if body_edges:
                # Average the detected edges
                avg_left = int(np.mean([e[0] for e in body_edges]))
                avg_right = int(np.mean([e[1] for e in body_edges]))

                return {
                    'left': (avg_left, chest_y),
                    'right': (avg_right, chest_y)
                }

        return {}

    def find_collar(self, contour: np.ndarray) -> Optional[Tuple]:
        """Find collar point at top center."""
        if len(contour) == 0:
            return None

        points = contour.reshape(-1, 2)
        top_y = np.min(points[:, 1])

        # Get points near top
        top_points = points[points[:, 1] < top_y + 30]

        if len(top_points) > 0:
            center_x = int(np.mean(top_points[:, 0]))
            return (center_x, int(top_y))

        return None

    def find_hem(self, contour: np.ndarray) -> Dict:
        """Find hem points at bottom."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)
        bottom_y = np.max(points[:, 1])

        # Get points near bottom
        hem_points = points[points[:, 1] > bottom_y - 30]

        if len(hem_points) > 0:
            left_x = int(np.min(hem_points[:, 0]))
            right_x = int(np.max(hem_points[:, 0]))
            center_x = int(np.mean(hem_points[:, 0]))

            return {
                'left': (left_x, int(bottom_y)),
                'right': (right_x, int(bottom_y)),
                'center': (center_x, int(bottom_y))
            }

        return {}

    def find_cuffs_from_mask(self, mask: np.ndarray, shoulders: Dict) -> Dict:
        """Find cuff points using mask analysis."""
        if not shoulders:
            return {}

        height, width = mask.shape
        cuffs = {}

        # For shirts, cuffs are at the ends of sleeves
        # Find extremities in middle portion of garment height
        middle_y_min = height // 3
        middle_y_max = 2 * height // 3

        # Left cuff - leftmost point in middle section
        for y in range(middle_y_min, middle_y_max):
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) > 0:
                left_x = nonzero[0]
                if left_x < width // 3:  # Ensure it's on left side
                    if 'left' not in cuffs or left_x < cuffs['left'][0]:
                        cuffs['left'] = (left_x, y)

        # Right cuff - rightmost point in middle section
        for y in range(middle_y_min, middle_y_max):
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) > 0:
                right_x = nonzero[-1]
                if right_x > 2 * width // 3:  # Ensure it's on right side
                    if 'right' not in cuffs or right_x > cuffs['right'][0]:
                        cuffs['right'] = (right_x, y)

        return cuffs

    def detect_landmarks(self, image_path: str) -> Dict:
        """Main detection pipeline."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Segment garment
        contour, mask = self.segment_garment(image)

        if len(contour) == 0:
            print("Warning: Could not segment garment properly")
            return {'landmarks': {}, 'measurements': {}}

        # Analyze width profile
        widths, y_positions = self.analyze_width_profile(mask)

        # Find all landmarks
        collar = self.find_collar(contour)
        shoulders = self.find_shoulders_from_contour(contour, mask)
        armpits = self.find_sleeve_body_junction(mask, widths, y_positions)
        chest = self.find_chest_measurement(mask, armpits)
        hem = self.find_hem(contour)
        cuffs = self.find_cuffs_from_mask(mask, shoulders)

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

        # Visualize
        if self.debug_mode:
            vis = self.visualize_landmarks(image, landmarks, mask)
            output_path = image_path.replace('.jpg', '_improved_geometry.jpg').replace('.png', '_improved_geometry.png')
            cv2.imwrite(output_path, vis)
            print(f"Saved visualization to {output_path}")

        return {
            'landmarks': landmarks,
            'measurements': measurements,
            'mask': mask
        }

    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """Calculate garment measurements."""
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

        # Sleeve lengths
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
            measurements['garment_length'] = abs(hem[1] - collar[1])

        return measurements

    def visualize_landmarks(self, image: np.ndarray, landmarks: Dict, mask: np.ndarray) -> np.ndarray:
        """Create visualization with landmarks and measurements."""
        vis = image.copy()

        # Overlay mask lightly
        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_colored[:, :, 1] = mask_colored[:, :, 1] // 2  # Reduce green channel
        vis = cv2.addWeighted(vis, 0.7, mask_colored, 0.3, 0)

        # Define colors
        colors = {
            'collar': (255, 255, 0),     # Yellow
            'shoulder': (0, 0, 255),     # Red
            'armpit': (255, 0, 255),     # Magenta
            'chest': (0, 255, 255),      # Cyan
            'hem': (255, 0, 0),          # Blue
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
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Draw measurement lines
        line_pairs = [
            ('shoulder_left', 'shoulder_right', 'Shoulders', (0, 0, 255)),
            ('chest_left', 'chest_right', 'Chest', (0, 255, 255)),
            ('armpit_left', 'armpit_right', 'Armpits', (255, 0, 255)),
            ('hem_left', 'hem_right', 'Hem', (255, 0, 0)),
            ('shoulder_left', 'cuff_left', 'L Sleeve', (0, 255, 0)),
            ('shoulder_right', 'cuff_right', 'R Sleeve', (0, 255, 0))
        ]

        for left_key, right_key, label, color in line_pairs:
            if left_key in landmarks and right_key in landmarks:
                left_pos = landmarks[left_key]['position']
                right_pos = landmarks[right_key]['position']

                # Draw line
                cv2.line(vis, left_pos, right_pos, color, 3)

                # Add measurement
                mid_x = (left_pos[0] + right_pos[0]) // 2
                mid_y = (left_pos[1] + right_pos[1]) // 2
                distance = np.sqrt((right_pos[0] - left_pos[0])**2 + (right_pos[1] - left_pos[1])**2)

                text = f"{label}: {distance:.0f}px"
                cv2.putText(vis, text, (mid_x - 60, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
                cv2.putText(vis, text, (mid_x - 60, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return vis


def main():
    """Test the improved detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='improved_geometry_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = ImprovedGeometryDetector(debug_mode=True)

    # Process image
    print(f"Processing {args.image_path}...")
    results = detector.detect_landmarks(args.image_path)

    # Save JSON results
    image_name = Path(args.image_path).stem
    json_path = output_dir / f"{image_name}_measurements.json"

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