#!/usr/bin/env python3
"""
Landmark-Based Measurement System using modelo.pth

Uses HRNet trained model to detect anatomical landmarks and extract precise measurements.
"""

import os
import cv2
import numpy as np
import torch
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import logging
from sviplab_hrnet_integration import SVIPLabFashionDetector
from garment_classifier import GarmentClassifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LandmarkMeasurementSystem:
    """
    Measurement system based on detected fashion landmarks with accurate classification
    """

    def __init__(self, model_path: str = "models/modelo.pth",
                 confidence_threshold: float = 0.01,
                 use_preprocessing: bool = False,
                 use_classifier: bool = True,
                 classifier_method: str = 'rule-based'):
        """
        Initialize landmark-based measurement system

        Args:
            model_path: Path to trained HRNet model
            confidence_threshold: Minimum confidence for landmarks
            use_preprocessing: Apply image preprocessing before detection
            use_classifier: Use separate classifier for category detection
            classifier_method: Classification method ('yolo', 'resnet', 'rule-based')
        """
        self.detector = SVIPLabFashionDetector(model_path=model_path)
        self.confidence_threshold = confidence_threshold
        self.use_preprocessing = use_preprocessing
        self.use_classifier = use_classifier

        # Initialize garment classifier if enabled
        if self.use_classifier:
            logger.info("Initializing garment classifier...")
            self.classifier = GarmentClassifier(method=classifier_method)
        else:
            self.classifier = None

        if self.use_preprocessing:
            from image_preprocessing import FashionImagePreprocessor
            self.preprocessor = FashionImagePreprocessor(
                remove_background=True,
                enhance_contrast=True,
                denoise=True,
                sharpen=True,
                normalize_colors=True
            )

    def extract_measurements(self, image_path: str, output_dir: str = "landmark_measurements") -> Dict:
        """
        Extract all measurements from garment image using landmarks

        Args:
            image_path: Path to garment image
            output_dir: Directory to save results

        Returns:
            Dictionary with all measurements and landmarks
        """
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(image_path).stem

        # Load image
        logger.info(f"Loading image: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Apply preprocessing if enabled
        if self.use_preprocessing:
            logger.info("Applying preprocessing pipeline...")
            image = self.preprocessor.preprocess(image)
            # Save preprocessed image for reference
            preprocessed_path = output_dir / f"{base_name}_preprocessed.jpg"
            cv2.imwrite(str(preprocessed_path), image)
            logger.info(f"Saved preprocessed image: {preprocessed_path}")

        # Classify garment category first (if classifier is enabled)
        predicted_category = None
        classification_confidence = None
        if self.use_classifier:
            logger.info("Classifying garment category...")
            classification_result = self.classifier.classify(image, return_confidence=True)
            predicted_category = classification_result['category']
            classification_confidence = classification_result.get('confidence', 0.0)
            logger.info(f"Classified as: {predicted_category} (confidence: {classification_confidence:.2%})")

        # Detect landmarks
        logger.info("Detecting landmarks...")
        detection = self.detector.detect_landmarks(
            image,
            confidence_threshold=self.confidence_threshold
        )

        # Override category with classifier prediction if available and confident
        if predicted_category and classification_confidence and classification_confidence > 0.6:
            original_category = detection['category']
            detection['category'] = predicted_category
            detection['category_source'] = 'classifier'
            detection['category_confidence'] = classification_confidence
            detection['original_category'] = original_category
            logger.info(f"Category overridden: {original_category} → {predicted_category}")
        else:
            detection['category_source'] = 'landmarks'

        logger.info(f"Final Category: {detection['category']}")
        logger.info(f"Detected {detection['num_detected']} landmarks")

        # Extract measurements based on category
        measurements = self._calculate_measurements(detection, image.shape)

        # Create comprehensive result
        result = {
            'image': image_path,
            'category': detection['category'],
            'num_landmarks': detection['num_detected'],
            'measurements': measurements,
            'landmarks': detection['landmarks'],
            'confidences': detection['confidences']
        }

        # Visualize
        logger.info("Creating visualization...")
        vis_image = self._create_measurement_visualization(
            image, detection, measurements
        )

        # Save visualization
        vis_path = output_dir / f"{base_name}_landmark_measurements.jpg"
        cv2.imwrite(str(vis_path), vis_image)
        logger.info(f"Saved visualization: {vis_path}")

        # Save JSON data
        json_path = output_dir / f"{base_name}_measurements.json"
        self._save_json(result, json_path)
        logger.info(f"Saved measurements: {json_path}")

        # Print summary
        self._print_summary(measurements)

        return result

    def _calculate_measurements(self, detection: Dict, image_shape: Tuple) -> Dict:
        """
        Calculate measurements from detected landmarks using DeepFashion2 landmark mappings

        Strategy:
        - Use precise landmark index pairs from DeepFashion2 mapping
        - Calculate Euclidean distances between specific landmark pairs
        - Extract measurements based on garment category
        """
        from deepfashion2_landmark_mapping import get_all_measurements_for_category

        landmarks = detection['landmarks']
        confidences = detection['confidences']
        category = detection['category']

        measurements = {}

        # Get landmark mapping for this category
        landmark_map = get_all_measurements_for_category(category)

        if not landmark_map:
            logger.warning(f"No landmark mapping found for category: {category}")
            # Fallback to old method
            return self._calculate_measurements_fallback(detection, image_shape)

        # Extract measurements using precise landmark indices
        measurements['key_points'] = {}
        measurements['widths'] = {}
        measurements['lengths'] = {}

        for measurement_name, [idx1, idx2] in landmark_map.items():
            # Check if both landmarks are valid
            lm1 = landmarks[idx1] if idx1 < len(landmarks) else None
            lm2 = landmarks[idx2] if idx2 < len(landmarks) else None
            conf1 = confidences[idx1] if idx1 < len(confidences) else 0
            conf2 = confidences[idx2] if idx2 < len(confidences) else 0

            if lm1 is not None and lm2 is not None and conf1 > 0.3 and conf2 > 0.3:
                # Calculate distance
                distance = self._distance(lm1, lm2)

                # Store based on measurement type
                if 'width' in measurement_name or 'opening' in measurement_name:
                    measurements['widths'][measurement_name] = distance
                    # Also store key points
                    measurements['key_points'][f"{measurement_name}_left"] = lm1
                    measurements['key_points'][f"{measurement_name}_right"] = lm2
                elif 'length' in measurement_name:
                    measurements['lengths'][measurement_name] = distance
                    # Store key points
                    measurements['key_points'][f"{measurement_name}_start"] = lm1
                    measurements['key_points'][f"{measurement_name}_end"] = lm2

        # Calculate overall dimensions
        valid_landmarks = [
            (i, lm, conf) for i, (lm, conf) in enumerate(zip(landmarks, confidences))
            if lm is not None and conf > 0
        ]
        measurements['dimensions'] = self._calculate_dimensions(valid_landmarks, image_shape)

        # Map to legacy key_point names for compatibility
        self._map_to_legacy_keypoints(measurements, landmark_map, landmarks, confidences)

        return measurements

    def _map_to_legacy_keypoints(self, measurements: Dict, landmark_map: Dict,
                                 landmarks: List, confidences: List):
        """Map new measurements to legacy key point names for visualization compatibility"""
        key_points = measurements['key_points']

        # Map collar
        if 'collar_width' in landmark_map:
            idx1, idx2 = landmark_map['collar_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['collar_left'] = landmarks[idx1]
                key_points['collar_right'] = landmarks[idx2]

        # Map shoulder
        if 'shoulder_width' in landmark_map:
            idx1, idx2 = landmark_map['shoulder_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['shoulder_left'] = landmarks[idx1]
                key_points['shoulder_right'] = landmarks[idx2]

        # Map chest
        if 'chest_width' in landmark_map:
            idx1, idx2 = landmark_map['chest_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['chest_left'] = landmarks[idx1]
                key_points['chest_right'] = landmarks[idx2]

        # Map hem
        if 'hem_width' in landmark_map:
            idx1, idx2 = landmark_map['hem_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['hem_left'] = landmarks[idx1]
                key_points['hem_right'] = landmarks[idx2]

        # Map cuffs
        if 'left_cuff_width' in landmark_map:
            idx1, idx2 = landmark_map['left_cuff_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['cuff_left'] = landmarks[idx1]

        if 'right_cuff_width' in landmark_map:
            idx1, idx2 = landmark_map['right_cuff_width']
            if landmarks[idx1] and landmarks[idx2]:
                key_points['cuff_right'] = landmarks[idx2]

    def _calculate_measurements_fallback(self, detection: Dict, image_shape: Tuple) -> Dict:
        """
        Fallback measurement calculation using region-based approach
        Used when no precise landmark mapping is available
        """
        landmarks = detection['landmarks']
        confidences = detection['confidences']
        category = detection['category']

        measurements = {}

        # Filter valid landmarks (non-None with confidence)
        valid_landmarks = [
            (i, lm, conf) for i, (lm, conf) in enumerate(zip(landmarks, confidences))
            if lm is not None and conf > 0
        ]

        if not valid_landmarks:
            logger.warning("No valid landmarks detected")
            return measurements

        # Extract key points
        measurements['key_points'] = self._extract_key_points(valid_landmarks, category)

        # Calculate distances
        measurements['widths'] = self._calculate_widths(measurements['key_points'])
        measurements['lengths'] = self._calculate_lengths(measurements['key_points'], image_shape)

        # Overall dimensions
        measurements['dimensions'] = self._calculate_dimensions(valid_landmarks, image_shape)

        return measurements

    def _extract_key_points(self, valid_landmarks: List, category: str) -> Dict:
        """
        Extract key anatomical points from landmarks

        Returns dict with:
        - collar_left, collar_right
        - shoulder_left, shoulder_right
        - chest_left, chest_right
        - hem_left, hem_right
        - cuff_left, cuff_right (if applicable)
        """
        key_points = {}

        # Get all landmark positions
        all_points = [(idx, lm, conf) for idx, lm, conf in valid_landmarks]

        # Sort by Y coordinate to identify regions
        sorted_by_y = sorted(all_points, key=lambda x: x[1][1])

        # Divide into vertical regions
        total_landmarks = len(sorted_by_y)
        top_region = sorted_by_y[:total_landmarks // 4]  # Top 25%
        upper_region = sorted_by_y[:total_landmarks // 3]  # Top 33%
        middle_region = sorted_by_y[total_landmarks // 3:2 * total_landmarks // 3]  # Middle
        bottom_region = sorted_by_y[2 * total_landmarks // 3:]  # Bottom 33%

        # COLLAR - Top-most points, leftmost and rightmost
        if top_region:
            collar_candidates = sorted(top_region, key=lambda x: x[1][0])  # Sort by X
            if len(collar_candidates) >= 2:
                key_points['collar_left'] = collar_candidates[0][1]
                key_points['collar_right'] = collar_candidates[-1][1]
            elif len(collar_candidates) == 1:
                key_points['collar_center'] = collar_candidates[0][1]

        # SHOULDER - Outermost points in upper region
        if upper_region:
            shoulder_candidates = sorted(upper_region, key=lambda x: x[1][0])  # Sort by X
            if len(shoulder_candidates) >= 2:
                # Take 2nd and 2nd-to-last to avoid collar points
                if len(shoulder_candidates) > 3:
                    key_points['shoulder_left'] = shoulder_candidates[1][1]
                    key_points['shoulder_right'] = shoulder_candidates[-2][1]
                else:
                    key_points['shoulder_left'] = shoulder_candidates[0][1]
                    key_points['shoulder_right'] = shoulder_candidates[-1][1]

        # CHEST/ARMPIT - Widest points in middle region
        if middle_region:
            chest_candidates = sorted(middle_region, key=lambda x: x[1][0])  # Sort by X
            if len(chest_candidates) >= 2:
                key_points['chest_left'] = chest_candidates[0][1]
                key_points['chest_right'] = chest_candidates[-1][1]

        # HEM - Bottom-most points
        if bottom_region:
            hem_candidates = sorted(bottom_region, key=lambda x: x[1][0])  # Sort by X
            if len(hem_candidates) >= 2:
                key_points['hem_left'] = hem_candidates[0][1]
                key_points['hem_right'] = hem_candidates[-1][1]
            elif len(hem_candidates) == 1:
                key_points['hem_center'] = hem_candidates[0][1]

        # CUFFS - Extreme left and right points in middle-to-bottom region
        middle_bottom = middle_region + bottom_region
        if middle_bottom:
            sorted_by_x = sorted(middle_bottom, key=lambda x: x[1][0])
            if len(sorted_by_x) >= 2:
                # Leftmost and rightmost are likely cuffs
                key_points['cuff_left'] = sorted_by_x[0][1]
                key_points['cuff_right'] = sorted_by_x[-1][1]

        return key_points

    def _calculate_widths(self, key_points: Dict) -> Dict:
        """Calculate horizontal widths"""
        widths = {}

        # Collar width
        if 'collar_left' in key_points and 'collar_right' in key_points:
            widths['collar'] = self._distance(
                key_points['collar_left'],
                key_points['collar_right']
            )

        # Shoulder width
        if 'shoulder_left' in key_points and 'shoulder_right' in key_points:
            widths['shoulder'] = self._distance(
                key_points['shoulder_left'],
                key_points['shoulder_right']
            )

        # Chest width
        if 'chest_left' in key_points and 'chest_right' in key_points:
            widths['chest'] = self._distance(
                key_points['chest_left'],
                key_points['chest_right']
            )

        # Hem width
        if 'hem_left' in key_points and 'hem_right' in key_points:
            widths['hem'] = self._distance(
                key_points['hem_left'],
                key_points['hem_right']
            )

        return widths

    def _calculate_lengths(self, key_points: Dict, image_shape: Tuple) -> Dict:
        """Calculate vertical lengths"""
        lengths = {}

        # Total length (collar to hem)
        if 'collar_left' in key_points and 'hem_left' in key_points:
            lengths['total_left'] = abs(
                key_points['hem_left'][1] - key_points['collar_left'][1]
            )

        if 'collar_right' in key_points and 'hem_right' in key_points:
            lengths['total_right'] = abs(
                key_points['hem_right'][1] - key_points['collar_right'][1]
            )

        # Sleeve length (shoulder to cuff)
        if 'shoulder_left' in key_points and 'cuff_left' in key_points:
            lengths['sleeve_left'] = self._distance(
                key_points['shoulder_left'],
                key_points['cuff_left']
            )

        if 'shoulder_right' in key_points and 'cuff_right' in key_points:
            lengths['sleeve_right'] = self._distance(
                key_points['shoulder_right'],
                key_points['cuff_right']
            )

        return lengths

    def _calculate_dimensions(self, valid_landmarks: List, image_shape: Tuple) -> Dict:
        """Calculate overall garment dimensions"""
        if not valid_landmarks:
            return {}

        points = [lm for _, lm, _ in valid_landmarks]

        # Extract all X and Y coordinates
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        return {
            'min_x': int(min(xs)),
            'max_x': int(max(xs)),
            'min_y': int(min(ys)),
            'max_y': int(max(ys)),
            'width': int(max(xs) - min(xs)),
            'height': int(max(ys) - min(ys))
        }

    def _distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points"""
        return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def _create_measurement_visualization(self, image: np.ndarray,
                                         detection: Dict,
                                         measurements: Dict) -> np.ndarray:
        """Create visualization showing only category-appropriate landmarks"""
        vis = image.copy()

        category = detection['category']

        # Define valid landmark index ranges for each category
        # Based on DeepFashion2 keypoint structure
        category_ranges = {
            'short_sleeved_shirt': (0, 25),
            'long_sleeved_shirt': (25, 58),
            'short_sleeved_outwear': (58, 89),
            'long_sleeved_outwear': (89, 128),
            'vest': (128, 143),
            'sling': (143, 158),
            'shorts': (158, 168),
            'trousers': (168, 182),
            'skirt': (182, 190),
            'short_sleeved_dress': (190, 219),
            'long_sleeved_dress': (219, 256),
            'vest_dress': (256, 275),
            'sling_dress': (275, 294)
        }

        # Get valid index range for this category
        if category in category_ranges:
            start_idx, end_idx = category_ranges[category]
            logger.info(f"Filtering landmarks to category range: {start_idx}-{end_idx} for {category}")
        else:
            # Unknown category - show all landmarks
            start_idx, end_idx = 0, 294
            logger.warning(f"Unknown category '{category}', showing all landmarks")

        # Draw only high confidence landmarks within the category range
        high_conf_count = 0
        total_category_landmarks = 0

        for idx, (landmark, conf) in enumerate(zip(detection['landmarks'], detection['confidences'])):
            # Check if landmark is in valid range for this category
            if start_idx <= idx < end_idx:
                total_category_landmarks += 1

                if landmark is not None and conf > 0.3:
                    # High confidence landmark within category range
                    # Color based on confidence level
                    if conf > 0.5:
                        color = (0, 255, 0)      # Green - very confident
                        radius = 6
                    else:
                        color = (0, 200, 255)    # Orange - moderate confidence
                        radius = 5

                    # Convert to integer coordinates (for sub-pixel precision from DeepMark++)
                    landmark_int = (int(round(landmark[0])), int(round(landmark[1])))

                    # Draw landmark point
                    cv2.circle(vis, landmark_int, radius, color, -1)
                    cv2.circle(vis, landmark_int, radius + 2, (255, 255, 255), 2)  # White border

                    # Draw landmark index number
                    text_pos = (landmark_int[0] + 10, landmark_int[1] - 10)
                    cv2.putText(vis, str(idx), text_pos, cv2.FONT_HERSHEY_SIMPLEX,
                               0.5, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(vis, str(idx), text_pos, cv2.FONT_HERSHEY_SIMPLEX,
                               0.5, (0, 0, 0), 1, cv2.LINE_AA)  # Black outline for readability

                    high_conf_count += 1

        # Add summary text
        cv2.putText(vis, f"Category: {category} | Landmarks: {high_conf_count}/{total_category_landmarks} (>30% conf)",
                   (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        logger.info(f"Visualization: showing {high_conf_count} high-confidence landmarks from {category} range")

        return vis

    def _save_json(self, result: Dict, json_path: Path):
        """Save measurements to JSON (convert numpy types)"""
        # Convert numpy types to Python native
        def convert(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert(item) for item in obj]
            return obj

        converted = convert(result)

        with open(json_path, 'w') as f:
            json.dump(converted, f, indent=2)

    def _print_summary(self, measurements: Dict):
        """Print measurement summary"""
        print("\n" + "="*60)
        print("LANDMARK-BASED MEASUREMENTS")
        print("="*60)

        widths = measurements.get('widths', {})
        lengths = measurements.get('lengths', {})
        dimensions = measurements.get('dimensions', {})

        if widths:
            print("\nWidths (pixels):")
            for name, value in widths.items():
                print(f"  {name.upper()}: {value:.1f}px")

        if lengths:
            print("\nLengths (pixels):")
            for name, value in lengths.items():
                print(f"  {name.upper()}: {value:.1f}px")

        if dimensions:
            print("\nOverall Dimensions:")
            print(f"  Width: {dimensions['width']}px")
            print(f"  Height: {dimensions['height']}px")

        print("="*60 + "\n")


def main():
    """Test landmark measurement system"""
    import argparse

    parser = argparse.ArgumentParser(description='Landmark-Based Measurement System with Accurate Classification')
    parser.add_argument('image', help='Input garment image')
    parser.add_argument('--model', default='models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
                       help='HRNet model path')
    parser.add_argument('--output', default='landmark_measurements', help='Output directory')
    parser.add_argument('--threshold', type=float, default=0.01,
                       help='Confidence threshold for landmarks')
    parser.add_argument('--preprocess', action='store_true',
                       help='Apply image preprocessing (bg removal, contrast, denoise, sharpen)')
    parser.add_argument('--no-classifier', action='store_true',
                       help='Disable separate garment classifier (use landmark-based category inference)')
    parser.add_argument('--classifier-method', choices=['yolo', 'resnet', 'rule-based'],
                       default='rule-based',
                       help='Classification method (default: rule-based)')

    args = parser.parse_args()

    print("="*60)
    print("LANDMARK-BASED MEASUREMENT SYSTEM")
    print("="*60)
    print()

    # Initialize system
    system = LandmarkMeasurementSystem(
        model_path=args.model,
        confidence_threshold=args.threshold,
        use_preprocessing=args.preprocess,
        use_classifier=not args.no_classifier,
        classifier_method=args.classifier_method
    )

    # Extract measurements
    result = system.extract_measurements(args.image, args.output)

    print("\n✓ Measurement extraction complete!")


if __name__ == '__main__':
    main()
