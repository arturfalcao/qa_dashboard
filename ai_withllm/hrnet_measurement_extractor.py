#!/usr/bin/env python3
"""
HRNet-based measurement extraction that works generically for any garment.
Uses spatial analysis to identify key measurement points from the 294 DeepFashion2 landmarks.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import sys

# Import the existing HRNet detector
from hrnet_landmark_detector import FashionLandmarkDetector


class HRNetMeasurementExtractor:
    """Extract accurate measurements from HRNet DeepFashion2 landmarks."""

    def __init__(self, model_path: str = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"):
        """Initialize the HRNet detector."""
        self.detector = FashionLandmarkDetector(model_path, device='cpu')

    def extract_measurement_landmarks(self, image_path: str, confidence_threshold: float = 0.3) -> Dict:
        """Extract key measurement landmarks from an image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # Detect all landmarks
        detection_result = self.detector.detect_landmarks(image, confidence_threshold)

        # Extract valid landmarks with positions
        valid_landmarks = []
        for i, (landmark, conf) in enumerate(zip(detection_result['landmarks'],
                                                 detection_result['confidences'])):
            if landmark is not None and conf > confidence_threshold:
                valid_landmarks.append({
                    'index': i,
                    'position': landmark,
                    'confidence': conf
                })

        if not valid_landmarks:
            return {'error': 'No landmarks detected'}

        # Analyze spatial distribution to identify garment type and key points
        measurement_points = self.analyze_spatial_distribution(valid_landmarks, (w, h))

        return measurement_points

    def analyze_spatial_distribution(self, landmarks: List[Dict], image_size: Tuple) -> Dict:
        """Analyze landmark positions to extract measurement points."""
        width, height = image_size

        # Get bounding box of all landmarks
        positions = np.array([lm['position'] for lm in landmarks])
        min_x, min_y = np.min(positions, axis=0)
        max_x, max_y = np.max(positions, axis=0)

        garment_width = max_x - min_x
        garment_height = max_y - min_y
        center_x = (min_x + max_x) // 2

        # Categorize landmarks by vertical position
        top_region = []      # Top 15% - collar/neckline
        shoulder_region = [] # 10-25% - shoulders
        chest_region = []    # 25-40% - chest/armpits
        middle_region = []   # 40-70% - body
        bottom_region = []   # 70-100% - hem

        for lm in landmarks:
            x, y = lm['position']
            relative_y = (y - min_y) / garment_height

            if relative_y < 0.15:
                top_region.append(lm)
            elif relative_y < 0.25:
                shoulder_region.append(lm)
            elif relative_y < 0.40:
                chest_region.append(lm)
            elif relative_y < 0.70:
                middle_region.append(lm)
            else:
                bottom_region.append(lm)

        # Determine garment type based on aspect ratio and landmark distribution
        aspect_ratio = garment_height / max(garment_width, 1)
        is_top_garment = aspect_ratio < 1.5  # Tops are typically wider than tall

        measurements = {}

        # Extract collar/neckline (topmost center point)
        if top_region:
            collar_candidates = [lm for lm in top_region
                                if abs(lm['position'][0] - center_x) < garment_width * 0.2]
            if collar_candidates:
                collar = min(collar_candidates, key=lambda lm: lm['position'][1])
                measurements['collar_center'] = {
                    'position': collar['position'],
                    'confidence': collar['confidence']
                }

        # Extract shoulders (outermost points in shoulder region)
        if shoulder_region or top_region:
            search_region = shoulder_region + top_region
            left_shoulder_candidates = [lm for lm in search_region
                                       if lm['position'][0] < center_x]
            right_shoulder_candidates = [lm for lm in search_region
                                        if lm['position'][0] > center_x]

            if left_shoulder_candidates:
                left_shoulder = min(left_shoulder_candidates, key=lambda lm: lm['position'][0])
                measurements['shoulder_left'] = {
                    'position': left_shoulder['position'],
                    'confidence': left_shoulder['confidence']
                }

            if right_shoulder_candidates:
                right_shoulder = max(right_shoulder_candidates, key=lambda lm: lm['position'][0])
                measurements['shoulder_right'] = {
                    'position': right_shoulder['position'],
                    'confidence': right_shoulder['confidence']
                }

        # Extract armpits/chest (widest points in chest region)
        if chest_region:
            left_chest_candidates = [lm for lm in chest_region
                                    if lm['position'][0] < center_x]
            right_chest_candidates = [lm for lm in chest_region
                                     if lm['position'][0] > center_x]

            if left_chest_candidates:
                left_armpit = min(left_chest_candidates, key=lambda lm: lm['position'][0])
                measurements['armpit_left'] = {
                    'position': left_armpit['position'],
                    'confidence': left_armpit['confidence']
                }

                # Chest is slightly more central than armpit
                chest_left_candidates = [lm for lm in left_chest_candidates
                                        if lm['position'][0] > left_armpit['position'][0]]
                if chest_left_candidates:
                    chest_left = chest_left_candidates[0]
                    measurements['chest_left'] = {
                        'position': chest_left['position'],
                        'confidence': chest_left['confidence']
                    }

            if right_chest_candidates:
                right_armpit = max(right_chest_candidates, key=lambda lm: lm['position'][0])
                measurements['armpit_right'] = {
                    'position': right_armpit['position'],
                    'confidence': right_armpit['confidence']
                }

                # Chest is slightly more central than armpit
                chest_right_candidates = [lm for lm in right_chest_candidates
                                         if lm['position'][0] < right_armpit['position'][0]]
                if chest_right_candidates:
                    chest_right = chest_right_candidates[0]
                    measurements['chest_right'] = {
                        'position': chest_right['position'],
                        'confidence': chest_right['confidence']
                    }

        # Extract hem (bottom points)
        if bottom_region:
            # Find leftmost, rightmost, and center bottom points
            hem_left = min(bottom_region, key=lambda lm: lm['position'][0])
            hem_right = max(bottom_region, key=lambda lm: lm['position'][0])

            measurements['hem_left'] = {
                'position': hem_left['position'],
                'confidence': hem_left['confidence']
            }
            measurements['hem_right'] = {
                'position': hem_right['position'],
                'confidence': hem_right['confidence']
            }

            # Center hem
            hem_center_candidates = [lm for lm in bottom_region
                                    if abs(lm['position'][0] - center_x) < garment_width * 0.1]
            if hem_center_candidates:
                hem_center = max(hem_center_candidates, key=lambda lm: lm['position'][1])
                measurements['hem_center'] = {
                    'position': hem_center['position'],
                    'confidence': hem_center['confidence']
                }

        # Extract cuffs (for tops - extremities in middle region)
        if is_top_garment and middle_region:
            # Find leftmost and rightmost points in middle region (likely cuffs)
            cuff_left = min(middle_region, key=lambda lm: lm['position'][0])
            cuff_right = max(middle_region, key=lambda lm: lm['position'][0])

            # Only consider as cuffs if they're significantly outside shoulder width
            if 'shoulder_left' in measurements and cuff_left['position'][0] < measurements['shoulder_left']['position'][0] - 50:
                measurements['cuff_left'] = {
                    'position': cuff_left['position'],
                    'confidence': cuff_left['confidence']
                }

            if 'shoulder_right' in measurements and cuff_right['position'][0] > measurements['shoulder_right']['position'][0] + 50:
                measurements['cuff_right'] = {
                    'position': cuff_right['position'],
                    'confidence': cuff_right['confidence']
                }

        # Calculate actual measurements
        calculated_measurements = self.calculate_distances(measurements)

        return {
            'measurement_points': measurements,
            'measurements': calculated_measurements,
            'garment_bbox': {
                'min_x': int(min_x),
                'max_x': int(max_x),
                'min_y': int(min_y),
                'max_y': int(max_y),
                'width': int(garment_width),
                'height': int(garment_height)
            },
            'garment_type': 'top' if is_top_garment else 'bottom',
            'total_landmarks': len(landmarks)
        }

    def calculate_distances(self, measurement_points: Dict) -> Dict:
        """Calculate distances between measurement points."""
        measurements = {}

        # Shoulder width
        if 'shoulder_left' in measurement_points and 'shoulder_right' in measurement_points:
            left = measurement_points['shoulder_left']['position']
            right = measurement_points['shoulder_right']['position']
            measurements['shoulder_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Chest width
        if 'chest_left' in measurement_points and 'chest_right' in measurement_points:
            left = measurement_points['chest_left']['position']
            right = measurement_points['chest_right']['position']
            measurements['chest_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Armpit span
        if 'armpit_left' in measurement_points and 'armpit_right' in measurement_points:
            left = measurement_points['armpit_left']['position']
            right = measurement_points['armpit_right']['position']
            measurements['armpit_span'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Hem width
        if 'hem_left' in measurement_points and 'hem_right' in measurement_points:
            left = measurement_points['hem_left']['position']
            right = measurement_points['hem_right']['position']
            measurements['hem_width'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        # Sleeve lengths
        if 'shoulder_left' in measurement_points and 'cuff_left' in measurement_points:
            shoulder = measurement_points['shoulder_left']['position']
            cuff = measurement_points['cuff_left']['position']
            measurements['sleeve_length_left'] = np.sqrt((cuff[0] - shoulder[0])**2 + (cuff[1] - shoulder[1])**2)

        if 'shoulder_right' in measurement_points and 'cuff_right' in measurement_points:
            shoulder = measurement_points['shoulder_right']['position']
            cuff = measurement_points['cuff_right']['position']
            measurements['sleeve_length_right'] = np.sqrt((cuff[0] - shoulder[0])**2 + (cuff[1] - shoulder[1])**2)

        # Garment length
        if 'collar_center' in measurement_points and 'hem_center' in measurement_points:
            collar = measurement_points['collar_center']['position']
            hem = measurement_points['hem_center']['position']
            measurements['garment_length'] = abs(hem[1] - collar[1])

        # Sleeve span (cuff to cuff)
        if 'cuff_left' in measurement_points and 'cuff_right' in measurement_points:
            left = measurement_points['cuff_left']['position']
            right = measurement_points['cuff_right']['position']
            measurements['sleeve_span'] = np.sqrt((right[0] - left[0])**2 + (right[1] - left[1])**2)

        return measurements

    def visualize_measurements(self, image_path: str, results: Dict) -> np.ndarray:
        """Visualize measurement landmarks on the image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        vis = image.copy()

        # First run detection to get all landmarks for background visualization
        detection_result = self.detector.detect_landmarks(image, 0.3)

        # Draw all detected landmarks as small gray dots
        for landmark, conf in zip(detection_result['landmarks'], detection_result['confidences']):
            if landmark is not None and conf > 0.3:
                cv2.circle(vis, landmark, 2, (180, 180, 180), -1)

        # Color scheme for measurement points
        colors = {
            'collar': (255, 255, 0),     # Yellow
            'shoulder': (0, 0, 255),     # Red
            'armpit': (255, 0, 255),     # Magenta
            'chest': (0, 255, 255),      # Cyan
            'hem': (255, 100, 0),        # Orange
            'cuff': (0, 255, 0)          # Green
        }

        # Draw measurement points
        if 'measurement_points' in results:
            for name, data in results['measurement_points'].items():
                pos = data['position']
                conf = data['confidence']

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
                label = f"{name.replace('_', ' ').title()}"
                cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                cv2.putText(vis, label, (pos[0] + 15, pos[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        # Draw measurement lines
        if 'measurements' in results:
            line_configs = [
                ('shoulder_left', 'shoulder_right', 'shoulder_width', (0, 0, 255)),
                ('chest_left', 'chest_right', 'chest_width', (0, 255, 255)),
                ('armpit_left', 'armpit_right', 'armpit_span', (255, 0, 255)),
                ('hem_left', 'hem_right', 'hem_width', (255, 100, 0)),
                ('shoulder_left', 'cuff_left', 'sleeve_length_left', (0, 200, 0)),
                ('shoulder_right', 'cuff_right', 'sleeve_length_right', (0, 200, 0)),
                ('cuff_left', 'cuff_right', 'sleeve_span', (100, 255, 100))
            ]

            for left_key, right_key, measurement_key, color in line_configs:
                if (left_key in results['measurement_points'] and
                    right_key in results['measurement_points'] and
                    measurement_key in results['measurements']):

                    p1 = results['measurement_points'][left_key]['position']
                    p2 = results['measurement_points'][right_key]['position']

                    # Draw line
                    cv2.line(vis, p1, p2, color, 3)

                    # Add measurement text
                    mid_x = (p1[0] + p2[0]) // 2
                    mid_y = (p1[1] + p2[1]) // 2
                    value = results['measurements'][measurement_key]

                    text = f"{measurement_key.replace('_', ' ').title()}: {value:.0f}px"
                    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(vis, (mid_x - w//2 - 5, mid_y - h - 5),
                                (mid_x + w//2 + 5, mid_y + 5), (255, 255, 255), -1)
                    cv2.putText(vis, text, (mid_x - w//2, mid_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Add summary
        garment_type = results.get('garment_type', 'unknown')
        total_landmarks = results.get('total_landmarks', 0)
        num_measurements = len(results.get('measurement_points', {}))

        summary = f"Type: {garment_type} | HRNet Landmarks: {total_landmarks} | Measurements: {num_measurements}"
        cv2.putText(vis, summary, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return vis


def main():
    """Test the HRNet measurement extractor."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--output-dir', default='hrnet_measurements', help='Output directory')
    parser.add_argument('--confidence', type=float, default=0.3, help='Confidence threshold')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extractor
    print("Initializing HRNet measurement extractor...")
    extractor = HRNetMeasurementExtractor()

    # Extract measurements
    print(f"Processing {args.image_path}...")
    results = extractor.extract_measurement_landmarks(args.image_path, args.confidence)

    if 'error' in results:
        print(f"Error: {results['error']}")
        return

    # Visualize results
    vis_image = extractor.visualize_measurements(args.image_path, results)

    # Save visualization
    image_name = Path(args.image_path).stem
    vis_path = output_dir / f"{image_name}_hrnet_measurements.jpg"
    cv2.imwrite(str(vis_path), vis_image)
    print(f"Saved visualization to {vis_path}")

    # Save JSON results
    json_path = output_dir / f"{image_name}_measurements.json"

    # Convert positions to lists for JSON serialization
    json_results = {
        'garment_type': results.get('garment_type'),
        'total_landmarks': results.get('total_landmarks'),
        'garment_bbox': results.get('garment_bbox'),
        'measurement_points': {},
        'measurements': results.get('measurements', {})
    }

    for name, data in results.get('measurement_points', {}).items():
        json_results['measurement_points'][name] = {
            'position': list(data['position']),
            'confidence': float(data['confidence'])
        }

    with open(json_path, 'w') as f:
        json.dump(json_results, f, indent=2)
    print(f"Saved measurements to {json_path}")

    # Print summary
    print(f"\nGarment Type: {results.get('garment_type')}")
    print(f"Total HRNet Landmarks Detected: {results.get('total_landmarks')}")
    print(f"\nKey Measurement Points Found:")
    for name in results.get('measurement_points', {}).keys():
        print(f"  - {name.replace('_', ' ').title()}")

    print(f"\nMeasurements:")
    for name, value in results.get('measurements', {}).items():
        print(f"  {name.replace('_', ' ').title()}: {value:.1f} pixels")


if __name__ == '__main__':
    main()