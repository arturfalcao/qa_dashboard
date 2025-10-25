#!/usr/bin/env python3
"""
Final Hybrid Detector that properly combines:
1. HRNet DeepFashion2 294 landmarks (primary source)
2. Edge detection for validation
3. Contour analysis for garment boundaries
4. Spatial reasoning for corrections
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Import the HRNet detector
from hrnet_landmark_detector import FashionLandmarkDetector


class FinalHybridDetector:
    """Final solution combining HRNet with intelligent validation."""

    # DeepFashion2 landmark mappings (based on actual model training)
    # These are approximate indices for common landmarks across categories
    LANDMARK_MAPPINGS = {
        'short_sleeved_shirt': {
            'collar_left': 0, 'collar_center': 2, 'collar_right': 4,
            'shoulder_left': 5, 'shoulder_right': 10,
            'armpit_left': 6, 'armpit_right': 11,
            'hem_left': 15, 'hem_center': 17, 'hem_right': 19,
            'chest_left': 20, 'chest_right': 21,
            'sleeve_left_edge': 7, 'sleeve_right_edge': 12,
            'cuff_left': 8, 'cuff_right': 13
        },
        'long_sleeved_shirt': {
            'collar_left': 25, 'collar_center': 27, 'collar_right': 29,
            'shoulder_left': 30, 'shoulder_right': 38,
            'armpit_left': 31, 'armpit_right': 39,
            'hem_left': 46, 'hem_center': 48, 'hem_right': 50,
            'chest_left': 51, 'chest_right': 53,
            'cuff_left': 35, 'cuff_right': 43
        },
        'trousers': {
            'waist_left': 168, 'waist_center': 169, 'waist_right': 170,
            'hip_left': 171, 'crotch': 172, 'hip_right': 173,
            'knee_left': 175, 'knee_right': 179,
            'hem_left_outer': 176, 'hem_left_inner': 177,
            'hem_right_outer': 180, 'hem_right_inner': 181
        },
        'vest': {
            'collar_left': 128, 'collar_center': 130, 'collar_right': 132,
            'shoulder_left': 133, 'shoulder_right': 136,
            'armhole_left': 134, 'armhole_right': 137,
            'hem_left': 139, 'hem_center': 140, 'hem_right': 141
        }
    }

    def __init__(self, model_path: str = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"):
        """Initialize the hybrid detector."""
        self.hrnet = FashionLandmarkDetector(model_path, device='cpu')

    def detect_garment_mask(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Detect garment mask and contour."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Use Otsu thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Clean up
        kernel = np.ones((5, 5), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        filled = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        # Find largest contour
        contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [largest], -1, 255, -1)
            return mask, largest

        return np.zeros_like(gray), np.array([])

    def classify_garment_type(self, hrnet_result: Dict, image_shape: Tuple) -> str:
        """Classify garment based on HRNet detection confidence."""
        # Check which category has the highest detection confidence
        category = hrnet_result.get('category', 'unknown')

        # Map HRNet categories to simplified types
        if any(x in category.lower() for x in ['shirt', 'outwear', 'vest', 'dress']):
            return 'top'
        elif any(x in category.lower() for x in ['trouser', 'short', 'skirt', 'pant']):
            return 'bottoms'

        # Fallback: use aspect ratio
        h, w = image_shape[:2]
        landmarks = hrnet_result['landmarks']
        valid_landmarks = [(i, lm) for i, lm in enumerate(landmarks) if lm is not None]

        if valid_landmarks:
            positions = np.array([lm[1] for i, lm in valid_landmarks])
            min_y = np.min(positions[:, 1])
            max_y = np.max(positions[:, 1])
            min_x = np.min(positions[:, 0])
            max_x = np.max(positions[:, 0])

            aspect_ratio = (max_y - min_y) / max(max_x - min_x, 1)

            # Check landmark distribution
            top_landmarks = sum(1 for i, lm in valid_landmarks if lm[1][1] < h * 0.3)
            bottom_landmarks = sum(1 for i, lm in valid_landmarks if lm[1][1] > h * 0.7)

            if aspect_ratio > 1.3 and bottom_landmarks > top_landmarks:
                return 'bottoms'

        return 'top'

    def find_nearest_edge_point(self, point: Tuple, mask: np.ndarray,
                               max_distance: int = 100) -> Tuple:
        """Find the nearest edge point to a given landmark."""
        edges = cv2.Canny(mask, 50, 150)
        edge_points = np.column_stack(np.where(edges > 0))

        if len(edge_points) == 0:
            return point

        # Convert point to (y, x) format for distance calculation
        point_yx = (point[1], point[0])
        distances = np.linalg.norm(edge_points - point_yx, axis=1)

        min_idx = np.argmin(distances)
        min_distance = distances[min_idx]

        if min_distance < max_distance:
            nearest = edge_points[min_idx]
            return (int(nearest[1]), int(nearest[0]))  # Convert back to (x, y)

        return point

    def extract_key_landmarks(self, hrnet_result: Dict, garment_type: str,
                              mask: np.ndarray, contour: np.ndarray) -> Dict:
        """Extract and correct key landmarks based on garment type."""
        landmarks = hrnet_result['landmarks']
        confidences = hrnet_result['confidences']
        category = hrnet_result.get('category', 'unknown')

        key_points = {}

        if garment_type == 'top':
            # Try multiple category mappings to find valid landmarks
            for cat_name in ['vest', 'short_sleeved_shirt', 'long_sleeved_shirt']:
                if cat_name in self.LANDMARK_MAPPINGS:
                    mapping = self.LANDMARK_MAPPINGS[cat_name]

                    # Extract key landmarks
                    for name, idx in mapping.items():
                        if idx < len(landmarks) and landmarks[idx] is not None:
                            if confidences[idx] > 0.3:  # Confidence threshold
                                # Validate and correct position
                                corrected = self.find_nearest_edge_point(
                                    landmarks[idx], mask, max_distance=50
                                )
                                key_points[name] = corrected

            # Ensure we have essential measurements
            key_points = self.validate_top_landmarks(key_points, contour, mask)

        elif garment_type == 'bottoms':
            # Use trousers mapping
            if 'trousers' in self.LANDMARK_MAPPINGS:
                mapping = self.LANDMARK_MAPPINGS['trousers']

                for name, idx in mapping.items():
                    if idx < len(landmarks) and landmarks[idx] is not None:
                        if confidences[idx] > 0.2:  # Lower threshold for bottoms
                            corrected = self.find_nearest_edge_point(
                                landmarks[idx], mask, max_distance=50
                            )
                            key_points[name] = corrected

            # Validate bottom landmarks
            key_points = self.validate_bottom_landmarks(key_points, contour, mask)

        return key_points

    def validate_top_landmarks(self, landmarks: Dict, contour: np.ndarray,
                               mask: np.ndarray) -> Dict:
        """Validate and fill missing landmarks for tops."""
        points = contour.reshape(-1, 2) if len(contour) > 0 else []

        if len(points) == 0:
            return landmarks

        # Ensure we have shoulders
        if 'shoulder_left' not in landmarks or 'shoulder_right' not in landmarks:
            # Find shoulders at top outer edges
            top_y = np.min(points[:, 1])
            shoulder_region = points[points[:, 1] < top_y + 150]

            if len(shoulder_region) > 0:
                left_shoulder = shoulder_region[np.argmin(shoulder_region[:, 0])]
                right_shoulder = shoulder_region[np.argmax(shoulder_region[:, 0])]
                landmarks['shoulder_left'] = tuple(left_shoulder.astype(int))
                landmarks['shoulder_right'] = tuple(right_shoulder.astype(int))

        # Ensure we have proper armpits (not too close together)
        if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
            armpit_dist = abs(landmarks['armpit_right'][0] - landmarks['armpit_left'][0])
            shoulder_dist = abs(landmarks.get('shoulder_right', (0, 0))[0] -
                              landmarks.get('shoulder_left', (0, 0))[0])

            # Armpits should be at least 50% of shoulder width
            if armpit_dist < shoulder_dist * 0.5:
                # Re-find armpits
                if 'shoulder_left' in landmarks and 'shoulder_right' in landmarks:
                    shoulder_y = (landmarks['shoulder_left'][1] +
                                landmarks['shoulder_right'][1]) // 2

                    # Search for width expansion below shoulders
                    for y in range(shoulder_y + 50, shoulder_y + 300, 10):
                        if y >= mask.shape[0]:
                            break

                        row = mask[y, :]
                        nonzero = np.nonzero(row)[0]

                        if len(nonzero) > 100:
                            # Find armpit positions (inner edges where sleeves meet body)
                            width = nonzero[-1] - nonzero[0]
                            center = (nonzero[0] + nonzero[-1]) // 2

                            # Armpits are typically 30-40% in from edges
                            left_armpit_x = nonzero[0] + int(width * 0.3)
                            right_armpit_x = nonzero[-1] - int(width * 0.3)

                            landmarks['armpit_left'] = (left_armpit_x, y)
                            landmarks['armpit_right'] = (right_armpit_x, y)
                            break

        # Ensure chest measurements
        if 'chest_left' not in landmarks or 'chest_right' not in landmarks:
            if 'armpit_left' in landmarks and 'armpit_right' in landmarks:
                # Chest is slightly below and inward from armpits
                armpit_y = (landmarks['armpit_left'][1] + landmarks['armpit_right'][1]) // 2
                chest_y = armpit_y + 50

                # Chest points are more central than armpits
                chest_left_x = landmarks['armpit_left'][0] + 50
                chest_right_x = landmarks['armpit_right'][0] - 50

                landmarks['chest_left'] = (chest_left_x, chest_y)
                landmarks['chest_right'] = (chest_right_x, chest_y)

        # Ensure hem
        if 'hem_left' not in landmarks or 'hem_right' not in landmarks:
            bottom_y = np.max(points[:, 1])
            hem_points = points[points[:, 1] > bottom_y - 30]

            if len(hem_points) > 0:
                landmarks['hem_left'] = (int(np.min(hem_points[:, 0])), int(bottom_y))
                landmarks['hem_right'] = (int(np.max(hem_points[:, 0])), int(bottom_y))
                landmarks['hem_center'] = (int(np.mean(hem_points[:, 0])), int(bottom_y))

        # Ensure collar
        if 'collar_center' not in landmarks:
            top_y = np.min(points[:, 1])
            top_points = points[points[:, 1] < top_y + 30]
            if len(top_points) > 0:
                landmarks['collar_center'] = (int(np.mean(top_points[:, 0])), int(top_y))

        # Find cuffs if we have sleeves
        if 'cuff_left' not in landmarks or 'cuff_right' not in landmarks:
            middle_y = (np.min(points[:, 1]) + np.max(points[:, 1])) // 2
            middle_points = points[np.abs(points[:, 1] - middle_y) < 200]

            if len(middle_points) > 0:
                leftmost = middle_points[np.argmin(middle_points[:, 0])]
                rightmost = middle_points[np.argmax(middle_points[:, 0])]

                # Only mark as cuffs if outside shoulder width
                if 'shoulder_left' in landmarks and leftmost[0] < landmarks['shoulder_left'][0] - 100:
                    landmarks['cuff_left'] = tuple(leftmost.astype(int))
                if 'shoulder_right' in landmarks and rightmost[0] > landmarks['shoulder_right'][0] + 100:
                    landmarks['cuff_right'] = tuple(rightmost.astype(int))

        return landmarks

    def validate_bottom_landmarks(self, landmarks: Dict, contour: np.ndarray,
                                 mask: np.ndarray) -> Dict:
        """Validate and fill missing landmarks for bottoms."""
        points = contour.reshape(-1, 2) if len(contour) > 0 else []

        if len(points) == 0:
            return landmarks

        # Ensure waistband
        if 'waist_left' not in landmarks or 'waist_right' not in landmarks:
            top_y = np.min(points[:, 1])
            waist_points = points[points[:, 1] < top_y + 50]

            if len(waist_points) > 0:
                landmarks['waist_left'] = (int(np.min(waist_points[:, 0])), int(top_y))
                landmarks['waist_right'] = (int(np.max(waist_points[:, 0])), int(top_y))
                landmarks['waist_center'] = (int(np.mean(waist_points[:, 0])), int(top_y))

        # Ensure hem
        if 'hem_left_outer' not in landmarks or 'hem_right_outer' not in landmarks:
            bottom_y = np.max(points[:, 1])
            hem_points = points[points[:, 1] > bottom_y - 50]

            if len(hem_points) > 0:
                # For pants, find the two leg hems
                x_coords = hem_points[:, 0]
                x_center = np.mean(x_coords)

                left_leg = hem_points[x_coords < x_center]
                right_leg = hem_points[x_coords > x_center]

                if len(left_leg) > 0:
                    landmarks['hem_left_outer'] = (int(np.min(left_leg[:, 0])), int(bottom_y))
                    landmarks['hem_left_inner'] = (int(np.max(left_leg[:, 0])), int(bottom_y))

                if len(right_leg) > 0:
                    landmarks['hem_right_inner'] = (int(np.min(right_leg[:, 0])), int(bottom_y))
                    landmarks['hem_right_outer'] = (int(np.max(right_leg[:, 0])), int(bottom_y))

        # Ensure crotch
        if 'crotch' not in landmarks:
            if 'waist_center' in landmarks and 'hem_left_inner' in landmarks:
                # Crotch is where legs meet, typically in middle third
                waist_y = landmarks['waist_center'][1]
                hem_y = landmarks.get('hem_left_inner', (0, mask.shape[0]))[1]
                crotch_y = waist_y + (hem_y - waist_y) * 2 // 3

                # Find narrowest point at this height
                row = mask[crotch_y, :] if crotch_y < mask.shape[0] else []
                if len(row) > 0:
                    nonzero = np.nonzero(row)[0]
                    if len(nonzero) > 0:
                        center_x = (nonzero[0] + nonzero[-1]) // 2
                        landmarks['crotch'] = (int(center_x), int(crotch_y))

        return landmarks

    def detect_landmarks(self, image_path: str) -> Dict:
        """Main detection pipeline."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # Step 1: Get HRNet detections
        print("Running HRNet detection...")
        hrnet_result = self.hrnet.detect_landmarks(image, confidence_threshold=0.2)

        # Step 2: Get garment mask and contour
        mask, contour = self.detect_garment_mask(image)

        # Step 3: Classify garment type
        garment_type = self.classify_garment_type(hrnet_result, (h, w))
        print(f"Detected garment type: {garment_type}")

        # Step 4: Extract and validate key landmarks
        landmarks = self.extract_key_landmarks(hrnet_result, garment_type, mask, contour)

        # Step 5: Calculate measurements
        measurements = self.calculate_measurements(landmarks, garment_type)

        return {
            'garment_type': garment_type,
            'landmarks': landmarks,
            'measurements': measurements,
            'hrnet_detected': hrnet_result['num_detected'],
            'hrnet_category': hrnet_result.get('category', 'unknown')
        }

    def calculate_measurements(self, landmarks: Dict, garment_type: str) -> Dict:
        """Calculate measurements based on landmarks."""
        measurements = {}

        def dist(p1, p2):
            if p1 and p2:
                return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            return 0

        if garment_type == 'top':
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

            # Hem width
            if 'hem_left' in landmarks and 'hem_right' in landmarks:
                measurements['hem_width'] = dist(landmarks['hem_left'],
                                               landmarks['hem_right'])

            # Garment length
            if 'collar_center' in landmarks and 'hem_center' in landmarks:
                measurements['garment_length'] = abs(landmarks['hem_center'][1] -
                                                    landmarks['collar_center'][1])

            # Sleeve lengths
            if 'shoulder_left' in landmarks and 'cuff_left' in landmarks:
                measurements['sleeve_length_left'] = dist(landmarks['shoulder_left'],
                                                         landmarks['cuff_left'])
            if 'shoulder_right' in landmarks and 'cuff_right' in landmarks:
                measurements['sleeve_length_right'] = dist(landmarks['shoulder_right'],
                                                          landmarks['cuff_right'])

            # Sleeve span
            if 'cuff_left' in landmarks and 'cuff_right' in landmarks:
                measurements['sleeve_span'] = dist(landmarks['cuff_left'],
                                                 landmarks['cuff_right'])

        elif garment_type == 'bottoms':
            # Waist width
            if 'waist_left' in landmarks and 'waist_right' in landmarks:
                measurements['waist_width'] = dist(landmarks['waist_left'],
                                                 landmarks['waist_right'])

            # Hip width (use widest point)
            if 'hip_left' in landmarks and 'hip_right' in landmarks:
                measurements['hip_width'] = dist(landmarks['hip_left'],
                                               landmarks['hip_right'])

            # Inseam
            if 'crotch' in landmarks and 'hem_left_inner' in landmarks:
                measurements['inseam'] = abs(landmarks['hem_left_inner'][1] -
                                           landmarks['crotch'][1])

            # Outseam
            if 'waist_left' in landmarks and 'hem_left_outer' in landmarks:
                measurements['outseam'] = abs(landmarks['hem_left_outer'][1] -
                                            landmarks['waist_left'][1])

            # Hem width (leg opening)
            if 'hem_left_outer' in landmarks and 'hem_left_inner' in landmarks:
                measurements['left_leg_opening'] = dist(landmarks['hem_left_outer'],
                                                       landmarks['hem_left_inner'])
            if 'hem_right_outer' in landmarks and 'hem_right_inner' in landmarks:
                measurements['right_leg_opening'] = dist(landmarks['hem_right_outer'],
                                                        landmarks['hem_right_inner'])

        return measurements

    def visualize_results(self, image_path: str, results: Dict) -> np.ndarray:
        """Create visualization of results."""
        image = cv2.imread(image_path)
        vis = image.copy()

        # Draw contour
        mask, contour = self.detect_garment_mask(image)
        if len(contour) > 0:
            cv2.drawContours(vis, [contour], -1, (0, 255, 0), 2)

        # Color scheme
        colors = {
            'collar': (255, 255, 0),      # Yellow
            'shoulder': (0, 0, 255),      # Red
            'armpit': (255, 0, 255),      # Magenta
            'chest': (0, 255, 255),       # Cyan
            'waist': (128, 0, 255),       # Purple
            'hem': (255, 100, 0),         # Orange
            'cuff': (0, 255, 0),          # Green
            'hip': (255, 128, 128),       # Pink
            'crotch': (128, 128, 255),    # Light blue
            'knee': (255, 255, 128)       # Light yellow
        }

        # Draw landmarks
        for name, pos in results['landmarks'].items():
            # Determine color
            color = (255, 255, 255)
            for key in colors:
                if key in name:
                    color = colors[key]
                    break

            # Draw point
            cv2.circle(vis, pos, 10, color, -1)
            cv2.circle(vis, pos, 12, (0, 0, 0), 2)

            # Add label
            label = name.replace('_', ' ').title()
            cv2.putText(vis, label, (pos[0] + 15, pos[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(vis, label, (pos[0] + 15, pos[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw measurement lines
        garment_type = results['garment_type']

        if garment_type == 'top':
            lines = [
                ('shoulder_left', 'shoulder_right', (0, 0, 255)),
                ('chest_left', 'chest_right', (0, 255, 255)),
                ('armpit_left', 'armpit_right', (255, 0, 255)),
                ('hem_left', 'hem_right', (255, 100, 0)),
                ('cuff_left', 'cuff_right', (0, 255, 0))
            ]
        else:
            lines = [
                ('waist_left', 'waist_right', (128, 0, 255)),
                ('hip_left', 'hip_right', (255, 128, 128)),
                ('hem_left_outer', 'hem_right_outer', (255, 100, 0))
            ]

        for left_key, right_key, color in lines:
            if left_key in results['landmarks'] and right_key in results['landmarks']:
                p1 = results['landmarks'][left_key]
                p2 = results['landmarks'][right_key]
                cv2.line(vis, p1, p2, color, 2)

                # Add measurement
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2

                # Find corresponding measurement
                for m_name, m_value in results['measurements'].items():
                    if left_key.split('_')[0] in m_name:
                        text = f"{m_name.replace('_', ' ').title()}: {m_value:.0f}px"
                        cv2.putText(vis, text, (mid_x - 80, mid_y - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        break

        # Add summary
        summary = (f"Type: {garment_type} | "
                  f"Landmarks: {len(results['landmarks'])} | "
                  f"HRNet: {results['hrnet_detected']} ({results['hrnet_category']})")
        cv2.putText(vis, summary, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        return vis


def main():
    """Test the final hybrid detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='final_results', help='Output directory')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    print("Initializing Final Hybrid Detector...")
    detector = FinalHybridDetector()

    # Detect landmarks
    print(f"Processing {args.image_path}...")
    results = detector.detect_landmarks(args.image_path)

    # Visualize
    vis = detector.visualize_results(args.image_path, results)

    # Save results
    image_name = Path(args.image_path).stem
    vis_path = output_dir / f"{image_name}_final.jpg"
    cv2.imwrite(str(vis_path), vis)
    print(f"Saved visualization to {vis_path}")

    # Save JSON
    json_path = output_dir / f"{image_name}_final.json"
    json_data = {
        'garment_type': results['garment_type'],
        'hrnet_category': results['hrnet_category'],
        'hrnet_detected': results['hrnet_detected'],
        'landmarks': {k: [int(v[0]), int(v[1])] for k, v in results['landmarks'].items()},
        'measurements': {k: float(v) for k, v in results['measurements'].items()}
    }

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved data to {json_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"GARMENT TYPE: {results['garment_type']}")
    print(f"HRNET CATEGORY: {results['hrnet_category']}")
    print(f"HRNET LANDMARKS: {results['hrnet_detected']}")
    print(f"\nKEY LANDMARKS FOUND: {len(results['landmarks'])}")
    for name in sorted(results['landmarks'].keys()):
        print(f"  ✓ {name.replace('_', ' ').title()}")

    print(f"\nMEASUREMENTS:")
    for name, value in results['measurements'].items():
        print(f"  {name.replace('_', ' ').title()}: {value:.0f} pixels")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()