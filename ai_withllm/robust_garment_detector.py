#!/usr/bin/env python3
"""
Robust garment detector that properly identifies the main garment
and finds anatomically correct landmarks.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path
from scipy import signal, ndimage


class RobustGarmentDetector:
    """Robust detection of garment landmarks with proper contour identification."""

    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode

    def extract_garment_contour(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract the main garment contour, filtering out markers and noise."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        height, width = gray.shape

        # Use multiple methods to find the garment
        masks = []

        # Method 1: Otsu thresholding
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, otsu_mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        masks.append(otsu_mask)

        # Method 2: Adaptive thresholding
        adaptive_mask = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY_INV, 51, 10)
        masks.append(adaptive_mask)

        # Method 3: Edge-based
        edges = cv2.Canny(blur, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        edge_mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        edge_mask = cv2.dilate(edge_mask, kernel, iterations=2)
        masks.append(edge_mask)

        # Combine masks
        combined_mask = np.zeros_like(gray)
        for mask in masks:
            combined_mask = cv2.bitwise_or(combined_mask, mask)

        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = ndimage.binary_fill_holes(combined_mask).astype(np.uint8) * 255

        # Find all contours
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return np.array([]), np.zeros_like(gray)

        # Filter contours to find the main garment
        min_area = (width * height) * 0.05  # At least 5% of image area
        max_area = (width * height) * 0.8   # At most 80% of image area

        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Check if contour is roughly centered
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # Garment should be roughly centered
                    if width * 0.2 < cx < width * 0.8 and height * 0.1 < cy < height * 0.9:
                        valid_contours.append((contour, area))

        if not valid_contours:
            # If no valid contours, just take the largest one
            largest = max(contours, key=cv2.contourArea)
            return largest, combined_mask

        # Select the largest valid contour
        best_contour = max(valid_contours, key=lambda x: x[1])[0]

        # Create clean mask from selected contour
        garment_mask = np.zeros_like(gray)
        cv2.drawContours(garment_mask, [best_contour], -1, 255, -1)

        return best_contour, garment_mask

    def find_collar_point(self, contour: np.ndarray) -> Tuple[Optional[Tuple[int, int]], int]:
        """Find the collar/neckline at the top center."""
        if len(contour) == 0:
            return None, 0

        points = contour.reshape(-1, 2)

        # Find top of garment
        top_y = np.min(points[:, 1])
        garment_height = np.max(points[:, 1]) - top_y

        # Collar region is top 5%
        collar_threshold = top_y + garment_height * 0.05

        # Get points in collar region
        collar_points = points[points[:, 1] <= collar_threshold]

        if len(collar_points) > 0:
            center_x = int(np.mean(collar_points[:, 0]))
            return (center_x, int(top_y)), int(collar_threshold)

        return None, 0

    def find_shoulders(self, contour: np.ndarray, collar_y: int) -> Dict:
        """Find shoulder points at the top outer edges where sleeves begin."""
        if len(contour) == 0 or collar_y == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Get garment dimensions
        top_y = np.min(points[:, 1])
        bottom_y = np.max(points[:, 1])
        garment_height = bottom_y - top_y

        # Shoulders are in top 10-15% of garment, at the widest points
        shoulder_y_min = collar_y
        shoulder_y_max = top_y + garment_height * 0.12

        # Get points in shoulder region
        shoulder_region = points[(points[:, 1] >= shoulder_y_min) &
                                (points[:, 1] <= shoulder_y_max)]

        if len(shoulder_region) < 2:
            return {}

        # Find center
        center_x = np.mean(points[:, 0])

        # Find leftmost and rightmost points
        shoulders = {}

        left_points = shoulder_region[shoulder_region[:, 0] < center_x]
        if len(left_points) > 0:
            left_shoulder_idx = np.argmin(left_points[:, 0])
            shoulders['left'] = tuple(left_points[left_shoulder_idx].astype(int))

        right_points = shoulder_region[shoulder_region[:, 0] > center_x]
        if len(right_points) > 0:
            right_shoulder_idx = np.argmax(right_points[:, 0])
            shoulders['right'] = tuple(right_points[right_shoulder_idx].astype(int))

        return shoulders

    def find_armpits(self, mask: np.ndarray, shoulders: Dict) -> Dict:
        """Find armpit points where sleeves meet body."""
        if not shoulders or len(mask) == 0:
            return {}

        height, width = mask.shape
        armpits = {}

        # Start from shoulder level
        shoulder_y = (shoulders['left'][1] + shoulders['right'][1]) // 2 if 'left' in shoulders and 'right' in shoulders else 0

        if shoulder_y == 0:
            return {}

        # Look for width expansion indicating sleeves
        prev_width = abs(shoulders.get('right', (0, 0))[0] - shoulders.get('left', (width, 0))[0])

        for y in range(shoulder_y + 20, min(shoulder_y + height // 3, height), 5):
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) < 2:
                continue

            current_width = nonzero[-1] - nonzero[0]

            # Significant width increase indicates sleeve level
            if current_width > prev_width * 1.2:
                # Find inner edges where body meets sleeves
                center = (nonzero[0] + nonzero[-1]) // 2

                # Left armpit - inner edge of left side
                left_section = nonzero[nonzero < center]
                if len(left_section) > 10:
                    # Armpit is about 25-30% in from outer edge
                    left_armpit_idx = len(left_section) * 3 // 10
                    armpits['left'] = (int(left_section[left_armpit_idx]), y)

                # Right armpit - inner edge of right side
                right_section = nonzero[nonzero > center]
                if len(right_section) > 10:
                    # Armpit is about 25-30% in from outer edge
                    right_armpit_idx = len(right_section) * 7 // 10
                    armpits['right'] = (int(right_section[right_armpit_idx]), y)

                if armpits:
                    break

            prev_width = current_width

        return armpits

    def find_chest_points(self, mask: np.ndarray, armpits: Dict, contour: np.ndarray) -> Dict:
        """Find chest measurement points on torso."""
        if not armpits or len(mask) == 0:
            return {}

        height, width = mask.shape

        # Chest is measured below armpits
        armpit_y = (armpits['left'][1] + armpits['right'][1]) // 2
        chest_y = min(armpit_y + 70, height - 1)

        # Get contour points to find body edges
        points = contour.reshape(-1, 2)

        # Find points at chest level
        chest_level_points = points[np.abs(points[:, 1] - chest_y) < 20]

        if len(chest_level_points) < 2:
            return {}

        # Find body portion (central continuous region)
        chest_x_coords = np.sort(chest_level_points[:, 0])

        # Remove outliers (potential sleeve points)
        if len(chest_x_coords) > 4:
            # Use interquartile range to filter
            q1 = np.percentile(chest_x_coords, 25)
            q3 = np.percentile(chest_x_coords, 75)
            iqr = q3 - q1

            # Filter points within reasonable range
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            body_points = chest_x_coords[(chest_x_coords >= lower_bound) &
                                        (chest_x_coords <= upper_bound)]

            if len(body_points) >= 2:
                return {
                    'left': (int(body_points[0]), chest_y),
                    'right': (int(body_points[-1]), chest_y)
                }

        # Fallback: use mask analysis
        row = mask[chest_y, :]
        nonzero = np.nonzero(row)[0]

        if len(nonzero) > 20:
            # Find central continuous region
            center = (nonzero[0] + nonzero[-1]) // 2
            body_width = (nonzero[-1] - nonzero[0]) // 3

            left_x = center - body_width // 2
            right_x = center + body_width // 2

            return {
                'left': (int(left_x), chest_y),
                'right': (int(right_x), chest_y)
            }

        return {}

    def find_hem_points(self, contour: np.ndarray) -> Dict:
        """Find hem points at bottom of garment."""
        if len(contour) == 0:
            return {}

        points = contour.reshape(-1, 2)

        # Find bottom
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

    def find_cuffs(self, contour: np.ndarray, shoulders: Dict) -> Dict:
        """Find cuff points at sleeve ends."""
        if len(contour) == 0 or not shoulders:
            return {}

        points = contour.reshape(-1, 2)
        cuffs = {}

        # Find extremities in middle portion of garment
        y_min = np.min(points[:, 1])
        y_max = np.max(points[:, 1])
        middle_y_min = y_min + (y_max - y_min) // 4
        middle_y_max = y_min + 3 * (y_max - y_min) // 4

        # Filter points in middle region
        middle_points = points[(points[:, 1] > middle_y_min) &
                              (points[:, 1] < middle_y_max)]

        if len(middle_points) > 0:
            # Left cuff - leftmost point
            left_idx = np.argmin(middle_points[:, 0])
            cuffs['left'] = tuple(middle_points[left_idx].astype(int))

            # Right cuff - rightmost point
            right_idx = np.argmax(middle_points[:, 0])
            cuffs['right'] = tuple(middle_points[right_idx].astype(int))

        return cuffs

    def detect_landmarks(self, image_path: str) -> Dict:
        """Main detection pipeline."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        print(f"Image shape: {image.shape}")

        # Extract garment contour
        contour, mask = self.extract_garment_contour(image)

        if len(contour) == 0:
            print("Warning: Could not extract garment contour")
            return {'landmarks': {}, 'measurements': {}}

        # Get contour statistics
        area = cv2.contourArea(contour)
        print(f"Contour area: {area:.0f} pixels ({area/(image.shape[0]*image.shape[1])*100:.1f}% of image)")

        # Find all landmarks
        collar, collar_y = self.find_collar_point(contour)
        shoulders = self.find_shoulders(contour, collar_y)
        armpits = self.find_armpits(mask, shoulders)
        chest = self.find_chest_points(mask, armpits, contour)
        hem = self.find_hem_points(contour)
        cuffs = self.find_cuffs(contour, shoulders)

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
            vis = self.visualize_results(image, landmarks, contour, mask)
            output_path = image_path.replace('.jpg', '_robust_detection.jpg').replace('.png', '_robust_detection.png')
            cv2.imwrite(output_path, vis)
            print(f"Saved visualization to {output_path}")

        return {
            'landmarks': landmarks,
            'measurements': measurements
        }

    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """Calculate garment measurements."""
        measurements = {}

        def calc_dist(p1, p2):
            return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

        # Standard measurements
        if 'shoulder_left' in landmarks and 'shoulder_right' in landmarks:
            measurements['shoulder_width'] = calc_dist(
                landmarks['shoulder_left']['position'],
                landmarks['shoulder_right']['position']
            )

        if 'chest_left' in landmarks and 'chest_right' in landmarks:
            measurements['chest_width'] = calc_dist(
                landmarks['chest_left']['position'],
                landmarks['chest_right']['position']
            )

        if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
            measurements['armpit_span'] = calc_dist(
                landmarks['armpit_left']['position'],
                landmarks['armpit_right']['position']
            )

        if 'hem_left' in landmarks and 'hem_right' in landmarks:
            measurements['hem_width'] = calc_dist(
                landmarks['hem_left']['position'],
                landmarks['hem_right']['position']
            )

        if 'shoulder_left' in landmarks and 'cuff_left' in landmarks:
            measurements['sleeve_length_left'] = calc_dist(
                landmarks['shoulder_left']['position'],
                landmarks['cuff_left']['position']
            )

        if 'shoulder_right' in landmarks and 'cuff_right' in landmarks:
            measurements['sleeve_length_right'] = calc_dist(
                landmarks['shoulder_right']['position'],
                landmarks['cuff_right']['position']
            )

        if 'collar_center' in landmarks and 'hem_center' in landmarks:
            collar_y = landmarks['collar_center']['position'][1]
            hem_y = landmarks['hem_center']['position'][1]
            measurements['garment_length'] = abs(hem_y - collar_y)

        if 'cuff_left' in landmarks and 'cuff_right' in landmarks:
            measurements['sleeve_span'] = calc_dist(
                landmarks['cuff_left']['position'],
                landmarks['cuff_right']['position']
            )

        return measurements

    def visualize_results(self, image: np.ndarray, landmarks: Dict,
                          contour: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Create comprehensive visualization."""
        vis = image.copy()

        # Show mask as overlay
        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_colored[:, :, 0] = 0  # Remove blue channel
        mask_colored[:, :, 1] = mask_colored[:, :, 1] // 3  # Reduce green
        vis = cv2.addWeighted(vis, 0.8, mask_colored, 0.2, 0)

        # Draw contour
        if len(contour) > 0:
            cv2.drawContours(vis, [contour], -1, (0, 255, 0), 2)

        # Color scheme
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
            cv2.circle(vis, pos, 12, color, -1)
            cv2.circle(vis, pos, 14, (0, 0, 0), 2)

            # Add label with background
            label = name.replace('_', ' ').title()
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(vis, (pos[0] + 15, pos[1] - h - 5),
                         (pos[0] + 20 + w, pos[1] + 5), (255, 255, 255), -1)
            cv2.rectangle(vis, (pos[0] + 15, pos[1] - h - 5),
                         (pos[0] + 20 + w, pos[1] + 5), color, 2)
            cv2.putText(vis, label, (pos[0] + 18, pos[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        # Draw measurement lines
        measurements = [
            ('shoulder_left', 'shoulder_right', 'Shoulder', (0, 0, 255)),
            ('chest_left', 'chest_right', 'Chest', (0, 255, 255)),
            ('armpit_left', 'armpit_right', 'Armpit', (255, 0, 255)),
            ('hem_left', 'hem_right', 'Hem', (255, 100, 0)),
            ('shoulder_left', 'cuff_left', 'L Sleeve', (0, 200, 0)),
            ('shoulder_right', 'cuff_right', 'R Sleeve', (0, 200, 0)),
            ('cuff_left', 'cuff_right', 'Span', (100, 255, 100))
        ]

        for left_key, right_key, label, color in measurements:
            if left_key in landmarks and right_key in landmarks:
                p1 = landmarks[left_key]['position']
                p2 = landmarks[right_key]['position']

                # Draw line
                cv2.line(vis, p1, p2, color, 3)

                # Add measurement text
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2
                dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

                text = f"{label}: {dist:.0f}px"
                (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                cv2.rectangle(vis, (mid_x - w//2 - 5, mid_y - h - 5),
                            (mid_x + w//2 + 5, mid_y + 5), (255, 255, 255), -1)
                cv2.putText(vis, text, (mid_x - w//2, mid_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return vis


def main():
    """Test the robust garment detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='robust_detection_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    detector = RobustGarmentDetector(debug_mode=True)

    # Process image
    print(f"\nProcessing {args.image_path}...")
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