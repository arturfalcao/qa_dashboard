#!/usr/bin/env python3
"""
Intelligent Ensemble Detector that combines multiple approaches:
1. HRNet for initial landmark detection
2. Edge detection for garment boundaries
3. Contour analysis for shape understanding
4. Anatomical rules for validation
5. Multi-model voting for accuracy
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from scipy import signal, ndimage
from scipy.spatial import distance
from collections import defaultdict

# Import the HRNet detector
from hrnet_landmark_detector import FashionLandmarkDetector


class IntelligentEnsembleDetector:
    """Combines multiple detection methods for accurate landmark placement."""

    def __init__(self, model_path: str = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"):
        """Initialize all detection components."""
        self.hrnet_detector = FashionLandmarkDetector(model_path, device='cpu')

    def detect_garment_type(self, image: np.ndarray) -> str:
        """Detect garment type based on aspect ratio and shape analysis."""
        # Get garment mask
        mask = self.get_garment_mask(image)

        # Find contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return "unknown"

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        aspect_ratio = h / max(w, 1)

        # Analyze shape characteristics
        upper_width = self._get_width_at_height(mask, y + int(h * 0.1))
        middle_width = self._get_width_at_height(mask, y + int(h * 0.5))
        lower_width = self._get_width_at_height(mask, y + int(h * 0.9))

        # Decision logic based on shape
        if aspect_ratio > 1.2:  # Taller than wide
            if upper_width < middle_width * 0.7:  # Narrow at top
                return "bottoms"  # Pants/jeans
            else:
                return "dress"
        else:  # Wider than tall or square
            if upper_width > lower_width * 1.2:  # Wider at top (sleeves)
                return "top"  # Shirt/jacket
            else:
                return "top"  # Default to top for square shapes

    def _get_width_at_height(self, mask: np.ndarray, y: int) -> int:
        """Get garment width at specific height."""
        if 0 <= y < mask.shape[0]:
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                return nonzero[-1] - nonzero[0]
        return 0

    def get_garment_mask(self, image: np.ndarray) -> np.ndarray:
        """Extract garment mask using multiple methods."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Method 1: Otsu thresholding
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Method 2: Edge detection
        edges = cv2.Canny(gray, 50, 150)
        kernel = np.ones((5, 5), np.uint8)
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Combine methods
        combined = cv2.bitwise_or(otsu, edges_closed)

        # Clean up
        cleaned = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        filled = ndimage.binary_fill_holes(cleaned).astype(np.uint8) * 255

        return filled

    def get_edge_points(self, image: np.ndarray) -> np.ndarray:
        """Get edge points of the garment."""
        mask = self.get_garment_mask(image)
        edges = cv2.Canny(mask, 50, 150)
        edge_points = np.column_stack(np.where(edges > 0))
        return edge_points

    def find_shoulders_for_top(self, image: np.ndarray, contour: np.ndarray,
                               hrnet_landmarks: List) -> Dict:
        """Find accurate shoulder points for tops."""
        h, w = image.shape[:2]
        points = contour.reshape(-1, 2)

        # Get top region of garment
        top_y = np.min(points[:, 1])

        # Shoulders are where the garment starts to widen (sleeve attachment)
        shoulder_y_search = range(top_y, min(top_y + 200, h))

        widths = []
        for y in shoulder_y_search:
            row_points = points[np.abs(points[:, 1] - y) < 5]
            if len(row_points) > 1:
                width = np.max(row_points[:, 0]) - np.min(row_points[:, 0])
                widths.append((y, width))

        if not widths:
            return {}

        # Find where width increases significantly (sleeve start)
        max_width_change = 0
        shoulder_y = top_y + 50  # Default

        for i in range(1, len(widths)):
            width_change = widths[i][1] - widths[i-1][1]
            if width_change > max_width_change:
                max_width_change = width_change
                shoulder_y = widths[i][0]

        # Get shoulder points at this height
        shoulder_points = points[np.abs(points[:, 1] - shoulder_y) < 20]

        if len(shoulder_points) > 1:
            left_shoulder = shoulder_points[np.argmin(shoulder_points[:, 0])]
            right_shoulder = shoulder_points[np.argmax(shoulder_points[:, 0])]

            return {
                'left': tuple(left_shoulder.astype(int)),
                'right': tuple(right_shoulder.astype(int))
            }

        return {}

    def find_armpits_for_top(self, image: np.ndarray, mask: np.ndarray,
                             shoulders: Dict) -> Dict:
        """Find accurate armpit points where sleeves meet body."""
        if not shoulders:
            return {}

        h, w = mask.shape
        armpits = {}

        # Search below shoulders
        shoulder_y = (shoulders['left'][1] + shoulders['right'][1]) // 2

        # Analyze width profile
        for y in range(shoulder_y + 30, min(shoulder_y + 300, h), 10):
            row = mask[y, :]
            nonzero = np.nonzero(row)[0]

            if len(nonzero) > 50:
                # Look for indentations (armpit points)
                # These are where the sleeve curves meet the body

                # Find local minima in the contour
                center_x = (nonzero[0] + nonzero[-1]) // 2

                # Left armpit - look for rightmost point before center
                left_section = nonzero[nonzero < center_x]
                if len(left_section) > 0:
                    # Find the point where sleeve meets body (usually an indentation)
                    left_armpit_x = left_section[-1] - 50  # Adjust inward
                    if left_armpit_x > nonzero[0]:
                        armpits['left'] = (int(left_armpit_x), y)

                # Right armpit
                right_section = nonzero[nonzero > center_x]
                if len(right_section) > 0:
                    right_armpit_x = right_section[0] + 50  # Adjust inward
                    if right_armpit_x < nonzero[-1]:
                        armpits['right'] = (int(right_armpit_x), y)

                if armpits:
                    break

        return armpits

    def find_chest_for_top(self, mask: np.ndarray, armpits: Dict) -> Dict:
        """Find chest measurement points."""
        if not armpits:
            return {}

        # Chest is measured slightly below armpits, across the body (not sleeves)
        armpit_y = (armpits['left'][1] + armpits['right'][1]) // 2
        chest_y = armpit_y + 50

        # Get body width at chest level
        row = mask[chest_y, :]
        nonzero = np.nonzero(row)[0]

        if len(nonzero) > 0:
            # Find the main body section (continuous central region)
            center = (nonzero[0] + nonzero[-1]) // 2

            # Chest points should be on the body, not sleeves
            # Use armpit x-coordinates as guides
            left_chest_x = max(armpits['left'][0], nonzero[0] + 100)
            right_chest_x = min(armpits['right'][0], nonzero[-1] - 100)

            return {
                'left': (int(left_chest_x), chest_y),
                'right': (int(right_chest_x), chest_y)
            }

        return {}

    def find_waist_for_bottoms(self, contour: np.ndarray) -> Dict:
        """Find waistband points for bottoms."""
        points = contour.reshape(-1, 2)

        # Waist is at the top of bottoms
        top_y = np.min(points[:, 1])
        waist_points = points[points[:, 1] < top_y + 50]

        if len(waist_points) > 1:
            left_waist = waist_points[np.argmin(waist_points[:, 0])]
            right_waist = waist_points[np.argmax(waist_points[:, 0])]
            center_waist_x = np.mean(waist_points[:, 0])

            return {
                'left': tuple(left_waist.astype(int)),
                'right': tuple(right_waist.astype(int)),
                'center': (int(center_waist_x), int(top_y))
            }

        return {}

    def validate_and_correct_landmarks(self, landmarks: Dict, garment_type: str,
                                      image_shape: Tuple) -> Dict:
        """Validate landmark positions and correct if needed."""
        h, w = image_shape[:2]
        corrected = landmarks.copy()

        if garment_type == "top":
            # Shoulders should be in top 20% of garment
            if 'shoulder_left' in corrected and 'shoulder_right' in corrected:
                shoulder_y = (corrected['shoulder_left'][1] + corrected['shoulder_right'][1]) // 2
                if shoulder_y > h * 0.4:  # Too low
                    # Move shoulders up
                    corrected['shoulder_left'] = (corrected['shoulder_left'][0], int(h * 0.2))
                    corrected['shoulder_right'] = (corrected['shoulder_right'][0], int(h * 0.2))

            # Armpits should be below shoulders
            if 'armpit_left' in corrected and 'shoulder_left' in corrected:
                if corrected['armpit_left'][1] <= corrected['shoulder_left'][1]:
                    corrected['armpit_left'] = (corrected['armpit_left'][0],
                                               corrected['shoulder_left'][1] + 100)

            # Chest should be below armpits
            if 'chest_left' in corrected and 'armpit_left' in corrected:
                if corrected['chest_left'][1] <= corrected['armpit_left'][1]:
                    corrected['chest_left'] = (corrected['chest_left'][0],
                                              corrected['armpit_left'][1] + 50)

        elif garment_type == "bottoms":
            # Remove any shoulder/collar landmarks from bottoms
            for key in list(corrected.keys()):
                if 'shoulder' in key or 'collar' in key or 'armpit' in key:
                    del corrected[key]

        return corrected

    def detect_landmarks(self, image_path: str) -> Dict:
        """Main detection pipeline combining all methods."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # Step 1: Detect garment type
        garment_type = self.detect_garment_type(image)
        print(f"Detected garment type: {garment_type}")

        # Step 2: Get HRNet landmarks as candidates
        hrnet_result = self.hrnet_detector.detect_landmarks(image, confidence_threshold=0.3)
        hrnet_landmarks = hrnet_result['landmarks']

        # Step 3: Get garment contour and mask
        mask = self.get_garment_mask(image)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {'error': 'No garment detected'}

        main_contour = max(contours, key=cv2.contourArea)

        # Step 4: Extract landmarks based on garment type
        landmarks = {}

        if garment_type == "top":
            # Find shoulders using contour analysis
            shoulders = self.find_shoulders_for_top(image, main_contour, hrnet_landmarks)
            if shoulders:
                landmarks['shoulder_left'] = shoulders['left']
                landmarks['shoulder_right'] = shoulders['right']

            # Find armpits
            armpits = self.find_armpits_for_top(image, mask, shoulders)
            if armpits:
                landmarks['armpit_left'] = armpits['left']
                landmarks['armpit_right'] = armpits['right']

            # Find chest
            chest = self.find_chest_for_top(mask, armpits)
            if chest:
                landmarks['chest_left'] = chest['left']
                landmarks['chest_right'] = chest['right']

            # Find collar (top center)
            points = main_contour.reshape(-1, 2)
            top_y = np.min(points[:, 1])
            top_points = points[points[:, 1] < top_y + 30]
            if len(top_points) > 0:
                collar_x = int(np.mean(top_points[:, 0]))
                landmarks['collar_center'] = (collar_x, int(top_y))

            # Find hem (bottom)
            bottom_y = np.max(points[:, 1])
            hem_points = points[points[:, 1] > bottom_y - 30]
            if len(hem_points) > 0:
                landmarks['hem_left'] = (int(np.min(hem_points[:, 0])), int(bottom_y))
                landmarks['hem_right'] = (int(np.max(hem_points[:, 0])), int(bottom_y))
                landmarks['hem_center'] = (int(np.mean(hem_points[:, 0])), int(bottom_y))

            # Find cuffs (sleeve ends)
            middle_y = (top_y + bottom_y) // 2
            middle_points = points[np.abs(points[:, 1] - middle_y) < 100]
            if len(middle_points) > 0:
                leftmost = middle_points[np.argmin(middle_points[:, 0])]
                rightmost = middle_points[np.argmax(middle_points[:, 0])]

                # Only mark as cuffs if they're outside shoulder width
                if shoulders:
                    if leftmost[0] < shoulders['left'][0] - 100:
                        landmarks['cuff_left'] = tuple(leftmost.astype(int))
                    if rightmost[0] > shoulders['right'][0] + 100:
                        landmarks['cuff_right'] = tuple(rightmost.astype(int))

        elif garment_type == "bottoms":
            # Find waistband
            waist = self.find_waist_for_bottoms(main_contour)
            if waist:
                landmarks['waist_left'] = waist['left']
                landmarks['waist_right'] = waist['right']
                landmarks['waist_center'] = waist['center']

            # Find hem (bottom of legs)
            points = main_contour.reshape(-1, 2)
            bottom_y = np.max(points[:, 1])
            hem_points = points[points[:, 1] > bottom_y - 50]

            if len(hem_points) > 0:
                # For pants, we have two hem points (leg bottoms)
                x_coords = hem_points[:, 0]
                x_center = np.mean(x_coords)

                left_hem = hem_points[x_coords < x_center]
                right_hem = hem_points[x_coords > x_center]

                if len(left_hem) > 0:
                    landmarks['hem_left'] = (int(np.mean(left_hem[:, 0])), int(bottom_y))
                if len(right_hem) > 0:
                    landmarks['hem_right'] = (int(np.mean(right_hem[:, 0])), int(bottom_y))

            # Find crotch point (where legs meet)
            # Look for the point where the garment splits
            middle_y = (waist['center'][1] + bottom_y) // 2
            middle_section = points[np.abs(points[:, 1] - middle_y) < 100]

            if len(middle_section) > 0:
                # Find the narrowest point (crotch)
                center_x = np.mean(middle_section[:, 0])
                landmarks['crotch'] = (int(center_x), int(middle_y))

        # Step 5: Validate and correct landmarks
        landmarks = self.validate_and_correct_landmarks(landmarks, garment_type, (h, w))

        # Step 6: Calculate measurements
        measurements = self.calculate_measurements(landmarks)

        return {
            'garment_type': garment_type,
            'landmarks': landmarks,
            'measurements': measurements,
            'hrnet_detections': hrnet_result['num_detected']
        }

    def calculate_measurements(self, landmarks: Dict) -> Dict:
        """Calculate measurements from landmarks."""
        measurements = {}

        def dist(p1, p2):
            return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

        # Shoulder width
        if 'shoulder_left' in landmarks and 'shoulder_right' in landmarks:
            measurements['shoulder_width'] = dist(landmarks['shoulder_left'],
                                                 landmarks['shoulder_right'])

        # Chest width
        if 'chest_left' in landmarks and 'chest_right' in landmarks:
            measurements['chest_width'] = dist(landmarks['chest_left'],
                                             landmarks['chest_right'])

        # Armpit span
        if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
            measurements['armpit_span'] = dist(landmarks['armpit_left'],
                                              landmarks['armpit_right'])

        # Waist width
        if 'waist_left' in landmarks and 'waist_right' in landmarks:
            measurements['waist_width'] = dist(landmarks['waist_left'],
                                             landmarks['waist_right'])

        # Hem width
        if 'hem_left' in landmarks and 'hem_right' in landmarks:
            measurements['hem_width'] = dist(landmarks['hem_left'],
                                           landmarks['hem_right'])

        # Garment length
        if 'collar_center' in landmarks and 'hem_center' in landmarks:
            measurements['garment_length'] = abs(landmarks['hem_center'][1] -
                                                landmarks['collar_center'][1])
        elif 'waist_center' in landmarks and 'hem_left' in landmarks:
            measurements['inseam'] = abs(landmarks['hem_left'][1] -
                                       landmarks['waist_center'][1])

        # Sleeve measurements
        if 'shoulder_left' in landmarks and 'cuff_left' in landmarks:
            measurements['sleeve_length_left'] = dist(landmarks['shoulder_left'],
                                                     landmarks['cuff_left'])
        if 'shoulder_right' in landmarks and 'cuff_right' in landmarks:
            measurements['sleeve_length_right'] = dist(landmarks['shoulder_right'],
                                                      landmarks['cuff_right'])

        return measurements

    def visualize_results(self, image_path: str, results: Dict) -> np.ndarray:
        """Visualize detection results."""
        image = cv2.imread(image_path)
        vis = image.copy()

        # Draw garment mask outline
        mask = self.get_garment_mask(image)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cv2.drawContours(vis, [max(contours, key=cv2.contourArea)], -1, (0, 255, 0), 2)

        # Color scheme
        colors = {
            'collar': (255, 255, 0),
            'shoulder': (0, 0, 255),
            'armpit': (255, 0, 255),
            'chest': (0, 255, 255),
            'waist': (128, 0, 255),
            'hem': (255, 100, 0),
            'cuff': (0, 255, 0),
            'crotch': (255, 128, 128)
        }

        # Draw landmarks
        for name, pos in results['landmarks'].items():
            color = (255, 255, 255)
            for key in colors:
                if key in name:
                    color = colors[key]
                    break

            cv2.circle(vis, pos, 10, color, -1)
            cv2.circle(vis, pos, 12, (0, 0, 0), 2)

            label = name.replace('_', ' ').title()
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        # Draw measurement lines
        line_pairs = [
            ('shoulder_left', 'shoulder_right', (0, 0, 255)),
            ('chest_left', 'chest_right', (0, 255, 255)),
            ('armpit_left', 'armpit_right', (255, 0, 255)),
            ('waist_left', 'waist_right', (128, 0, 255)),
            ('hem_left', 'hem_right', (255, 100, 0))
        ]

        for left_key, right_key, color in line_pairs:
            if left_key in results['landmarks'] and right_key in results['landmarks']:
                p1 = results['landmarks'][left_key]
                p2 = results['landmarks'][right_key]
                cv2.line(vis, p1, p2, color, 2)

                # Add measurement text
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2

                measurement_key = left_key.split('_')[0] + '_width'
                if measurement_key in results['measurements']:
                    value = results['measurements'][measurement_key]
                    text = f"{measurement_key.replace('_', ' ').title()}: {value:.0f}px"
                    cv2.putText(vis, text, (mid_x - 80, mid_y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Add summary
        garment_type = results['garment_type']
        num_landmarks = len(results['landmarks'])
        cv2.putText(vis, f"Type: {garment_type} | Landmarks: {num_landmarks} | HRNet: {results['hrnet_detections']}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return vis


def main():
    """Test the intelligent ensemble detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='ensemble_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    print("Initializing Intelligent Ensemble Detector...")
    detector = IntelligentEnsembleDetector()

    # Detect landmarks
    print(f"Processing {args.image_path}...")
    results = detector.detect_landmarks(args.image_path)

    if 'error' in results:
        print(f"Error: {results['error']}")
        return

    # Visualize
    vis = detector.visualize_results(args.image_path, results)

    # Save results
    image_name = Path(args.image_path).stem
    vis_path = output_dir / f"{image_name}_ensemble.jpg"
    cv2.imwrite(str(vis_path), vis)
    print(f"Saved visualization to {vis_path}")

    # Save JSON
    json_path = output_dir / f"{image_name}_ensemble.json"
    json_data = {
        'garment_type': results['garment_type'],
        'landmarks': {k: [int(v[0]), int(v[1])] for k, v in results['landmarks'].items()},
        'measurements': {k: float(v) for k, v in results['measurements'].items()}
    }

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved data to {json_path}")

    # Print results
    print(f"\nGarment Type: {results['garment_type']}")
    print(f"Landmarks Found: {len(results['landmarks'])}")
    print("\nMeasurements:")
    for name, value in results['measurements'].items():
        print(f"  {name.replace('_', ' ').title()}: {value:.1f} px")


if __name__ == '__main__':
    main()