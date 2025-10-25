#!/usr/bin/env python3
"""
Edge-Aware Landmark Correction System

This module ensures that all detected landmarks are precisely positioned on the
garment edges, not floating outside or placed too far inside the garment.
Critical for accurate garment measurements.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
import logging
from scipy.spatial.distance import cdist
from skimage import morphology, measure
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdgeAwareLandmarkCorrector:
    """
    Corrects landmark positions to ensure they lie precisely on garment edges
    """

    def __init__(self,
                 edge_threshold: int = 50,
                 max_correction_distance: int = 100,
                 edge_detection_method: str = 'canny_morphology'):
        """
        Initialize the edge-aware landmark corrector

        Args:
            edge_threshold: Threshold for edge detection sensitivity
            max_correction_distance: Maximum pixels to move a landmark
            edge_detection_method: Method for edge detection
                                  ('canny', 'canny_morphology', 'contour')
        """
        self.edge_threshold = edge_threshold
        self.max_correction_distance = max_correction_distance
        self.edge_detection_method = edge_detection_method

    def correct_landmarks(self,
                         image: np.ndarray,
                         landmarks: List[Tuple[int, int]],
                         confidences: List[float] = None,
                         has_background: bool = False) -> Dict[str, Any]:
        """
        Main method to correct landmark positions to garment edges

        Args:
            image: Input image (BGR)
            landmarks: List of (x, y) landmark positions
            confidences: Optional confidence scores for each landmark
            has_background: Whether image has background (if False, assumes white/removed bg)

        Returns:
            Dictionary with corrected landmarks and validation info
        """
        results = {
            'original_landmarks': landmarks.copy(),
            'corrected_landmarks': [],
            'corrections': [],
            'edge_mask': None,
            'contours': None,
            'validation': {}
        }

        # Step 1: Extract garment mask and edges
        logger.info("Extracting garment edges...")
        edge_data = self._extract_garment_edges(image, has_background)
        results['edge_mask'] = edge_data['edge_mask']
        results['contours'] = edge_data['contours']
        results['garment_mask'] = edge_data['garment_mask']

        # Step 2: Build edge point cloud for fast nearest-neighbor search
        edge_points = self._get_edge_points(edge_data['edge_mask'])
        logger.info(f"Found {len(edge_points)} edge points")

        if len(edge_points) == 0:
            logger.warning("No edge points found, returning original landmarks")
            results['corrected_landmarks'] = landmarks
            return results

        # Step 3: Correct each landmark
        corrected_landmarks = []
        corrections = []

        for i, landmark in enumerate(landmarks):
            if landmark is None:
                corrected_landmarks.append(None)
                corrections.append(None)
                continue

            # Check if landmark is valid
            x, y = landmark
            if not (0 <= x < image.shape[1] and 0 <= y < image.shape[0]):
                logger.warning(f"Landmark {i} out of image bounds: {landmark}")
                corrected_landmarks.append(None)
                corrections.append(None)
                continue

            # Find correction
            corrected, correction_info = self._correct_single_landmark(
                landmark,
                edge_points,
                edge_data['garment_mask'],
                confidences[i] if confidences else 1.0
            )

            corrected_landmarks.append(corrected)
            corrections.append(correction_info)

        results['corrected_landmarks'] = corrected_landmarks
        results['corrections'] = corrections

        # Step 4: Validate corrections
        results['validation'] = self._validate_corrections(
            landmarks,
            corrected_landmarks,
            corrections,
            edge_data['garment_mask']
        )

        logger.info(f"Corrected {results['validation']['num_corrected']}/{len(landmarks)} landmarks")

        return results

    def _extract_garment_edges(self,
                               image: np.ndarray,
                               has_background: bool) -> Dict:
        """
        Extract garment edges using various methods
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if self.edge_detection_method == 'canny_morphology':
            return self._extract_edges_canny_morphology(image, gray, has_background)
        elif self.edge_detection_method == 'contour':
            return self._extract_edges_contour(image, gray, has_background)
        else:  # canny
            return self._extract_edges_canny(gray, has_background)

    def _extract_edges_canny_morphology(self,
                                       image: np.ndarray,
                                       gray: np.ndarray,
                                       has_background: bool) -> Dict:
        """
        Extract edges using Canny edge detection with morphological operations
        Best for clean, isolated garments
        """
        # Step 1: Get garment mask
        if has_background:
            # Assume non-white pixels are garment
            mask = cv2.inRange(image, (0, 0, 0), (250, 250, 250))
        else:
            # For white background, find non-white regions
            if len(image.shape) == 3:
                # Check if pixel is not white (with tolerance)
                white_threshold = 245
                mask = np.any(image < white_threshold, axis=2).astype(np.uint8) * 255
            else:
                mask = (gray < 245).astype(np.uint8) * 255

        # Clean up mask with morphological operations
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

        # Fill holes
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled_mask = np.zeros_like(mask)
        if contours:
            # Find largest contour (main garment)
            largest_contour = max(contours, key=cv2.contourArea)
            cv2.drawContours(filled_mask, [largest_contour], -1, 255, -1)
        else:
            filled_mask = mask

        # Step 2: Apply Canny edge detection
        edges = cv2.Canny(gray, self.edge_threshold, self.edge_threshold * 2)

        # Step 3: Combine with mask to get only garment edges
        garment_edges = cv2.bitwise_and(edges, filled_mask)

        # Step 4: Add contour edges for robustness
        contour_edges = np.zeros_like(mask)
        if contours:
            cv2.drawContours(contour_edges, [largest_contour], -1, 255, 1)

        # Combine both edge types
        combined_edges = cv2.bitwise_or(garment_edges, contour_edges)

        # Thin the edges to single pixel width
        combined_edges = morphology.skeletonize(combined_edges > 0).astype(np.uint8) * 255

        return {
            'edge_mask': combined_edges,
            'garment_mask': filled_mask,
            'contours': [largest_contour] if contours else []
        }

    def _extract_edges_contour(self,
                              image: np.ndarray,
                              gray: np.ndarray,
                              has_background: bool) -> Dict:
        """
        Extract edges using contour detection
        More robust for complex backgrounds
        """
        # Create binary mask
        if has_background:
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        else:
            # For white background
            _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            logger.warning("No contours found")
            return {
                'edge_mask': np.zeros_like(gray),
                'garment_mask': binary,
                'contours': []
            }

        # Find largest contour (main garment)
        largest_contour = max(contours, key=cv2.contourArea)

        # Create edge mask from contour
        edge_mask = np.zeros_like(gray)
        cv2.drawContours(edge_mask, [largest_contour], -1, 255, 1)

        # Create filled mask
        garment_mask = np.zeros_like(gray)
        cv2.drawContours(garment_mask, [largest_contour], -1, 255, -1)

        return {
            'edge_mask': edge_mask,
            'garment_mask': garment_mask,
            'contours': [largest_contour]
        }

    def _extract_edges_canny(self, gray: np.ndarray, has_background: bool) -> Dict:
        """
        Simple Canny edge detection
        """
        edges = cv2.Canny(gray, self.edge_threshold, self.edge_threshold * 2)

        # Create approximate mask
        _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)

        return {
            'edge_mask': edges,
            'garment_mask': mask,
            'contours': []
        }

    def _get_edge_points(self, edge_mask: np.ndarray) -> np.ndarray:
        """
        Extract (x, y) coordinates of all edge pixels
        """
        edge_pixels = np.where(edge_mask > 0)
        if len(edge_pixels[0]) == 0:
            return np.array([])

        # Convert to (x, y) format
        edge_points = np.column_stack((edge_pixels[1], edge_pixels[0]))
        return edge_points

    def _correct_single_landmark(self,
                                landmark: Tuple[int, int],
                                edge_points: np.ndarray,
                                garment_mask: np.ndarray,
                                confidence: float) -> Tuple[Tuple[int, int], Dict]:
        """
        Correct a single landmark to nearest edge point
        """
        x, y = landmark
        correction_info = {
            'original': landmark,
            'corrected': landmark,
            'distance_moved': 0,
            'is_inside': False,
            'is_on_edge': False,
            'confidence': confidence
        }

        # Check if landmark is inside garment
        if 0 <= y < garment_mask.shape[0] and 0 <= x < garment_mask.shape[1]:
            is_inside = garment_mask[y, x] > 0
            correction_info['is_inside'] = is_inside
        else:
            is_inside = False

        # Find nearest edge point
        if len(edge_points) > 0:
            distances = cdist([landmark], edge_points, 'euclidean')[0]
            nearest_idx = np.argmin(distances)
            nearest_edge = tuple(edge_points[nearest_idx])
            distance = distances[nearest_idx]

            # Check if already on edge (within tolerance)
            if distance < 3:  # 3 pixel tolerance
                correction_info['is_on_edge'] = True
                correction_info['corrected'] = landmark
                return landmark, correction_info

            # Correct if within max correction distance
            if distance <= self.max_correction_distance:
                # Apply correction with confidence weighting
                if confidence < 0.5:
                    # Low confidence: move all the way to edge
                    correction_weight = 1.0
                elif confidence < 0.7:
                    # Medium confidence: partial correction
                    correction_weight = 0.8
                else:
                    # High confidence: minimal correction
                    correction_weight = 0.5

                # Calculate corrected position
                if is_inside and distance > 10:
                    # Landmark is inside garment but far from edge
                    # Move it to the edge
                    corrected = nearest_edge
                elif not is_inside:
                    # Landmark is outside garment
                    # Definitely move to edge
                    corrected = nearest_edge
                else:
                    # Landmark is close to edge, apply weighted correction
                    corrected_x = int(x + correction_weight * (nearest_edge[0] - x))
                    corrected_y = int(y + correction_weight * (nearest_edge[1] - y))
                    corrected = (corrected_x, corrected_y)

                correction_info['corrected'] = corrected
                correction_info['distance_moved'] = distance

                return corrected, correction_info

        # No correction applied
        return landmark, correction_info

    def _validate_corrections(self,
                            original: List,
                            corrected: List,
                            corrections: List,
                            garment_mask: np.ndarray) -> Dict:
        """
        Validate the quality of corrections
        """
        validation = {
            'num_corrected': 0,
            'num_invalid': 0,
            'num_outside': 0,
            'num_inside_far': 0,
            'avg_correction_distance': 0,
            'max_correction_distance': 0
        }

        distances = []

        for orig, corr, info in zip(original, corrected, corrections):
            if orig is None or corr is None or info is None:
                validation['num_invalid'] += 1
                continue

            if info['distance_moved'] > 0:
                validation['num_corrected'] += 1
                distances.append(info['distance_moved'])

            if not info['is_inside'] and not info['is_on_edge']:
                validation['num_outside'] += 1

            if info['is_inside'] and info['distance_moved'] > 20:
                validation['num_inside_far'] += 1

        if distances:
            validation['avg_correction_distance'] = np.mean(distances)
            validation['max_correction_distance'] = np.max(distances)

        return validation

    def visualize_corrections(self,
                             image: np.ndarray,
                             correction_results: Dict,
                             output_path: Optional[str] = None) -> np.ndarray:
        """
        Visualize the landmark corrections
        """
        vis = image.copy()

        # Draw edge mask overlay
        if correction_results['edge_mask'] is not None:
            edge_overlay = np.zeros_like(vis)
            edge_overlay[:, :, 1] = correction_results['edge_mask']  # Green edges
            vis = cv2.addWeighted(vis, 0.7, edge_overlay, 0.3, 0)

        # Draw original landmarks (red)
        for landmark in correction_results['original_landmarks']:
            if landmark is not None:
                cv2.circle(vis, landmark, 5, (0, 0, 255), -1)  # Red
                cv2.circle(vis, landmark, 7, (0, 0, 0), 1)

        # Draw corrected landmarks (green)
        for landmark in correction_results['corrected_landmarks']:
            if landmark is not None:
                cv2.circle(vis, landmark, 5, (0, 255, 0), -1)  # Green
                cv2.circle(vis, landmark, 7, (0, 0, 0), 1)

        # Draw correction arrows
        for orig, corr in zip(correction_results['original_landmarks'],
                            correction_results['corrected_landmarks']):
            if orig is not None and corr is not None and orig != corr:
                cv2.arrowedLine(vis, orig, corr, (255, 255, 0), 2, tipLength=0.3)

        # Add statistics
        validation = correction_results['validation']
        text_y = 30
        cv2.putText(vis, f"Corrected: {validation['num_corrected']} landmarks",
                   (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        text_y += 25
        cv2.putText(vis, f"Avg correction: {validation['avg_correction_distance']:.1f}px",
                   (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        text_y += 25
        cv2.putText(vis, f"Outside: {validation['num_outside']} | Inside far: {validation['num_inside_far']}",
                   (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Add legend
        legend_y = image.shape[0] - 60
        cv2.circle(vis, (20, legend_y), 5, (0, 0, 255), -1)
        cv2.putText(vis, "Original", (35, legend_y + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.circle(vis, (20, legend_y + 20), 5, (0, 255, 0), -1)
        cv2.putText(vis, "Corrected", (35, legend_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        if output_path:
            cv2.imwrite(output_path, vis)

        return vis

    def create_edge_analysis_report(self,
                                   image: np.ndarray,
                                   correction_results: Dict,
                                   output_path: str) -> np.ndarray:
        """
        Create comprehensive edge analysis report
        """
        h, w = image.shape[:2]

        # Create 2x2 grid
        report = np.ones((h * 2 + 60, w * 2 + 20, 3), dtype=np.uint8) * 240

        # Panel 1: Original with landmarks
        panel1 = image.copy()
        for landmark in correction_results['original_landmarks']:
            if landmark is not None:
                cv2.circle(panel1, landmark, 5, (0, 0, 255), -1)
        report[10:h+10, 10:w+10] = panel1
        cv2.putText(report, "Original Landmarks", (15, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # Panel 2: Edge detection
        if correction_results['edge_mask'] is not None:
            edge_vis = cv2.cvtColor(correction_results['edge_mask'], cv2.COLOR_GRAY2BGR)
            report[10:h+10, w+15:2*w+15] = cv2.resize(edge_vis, (w, h))
        cv2.putText(report, "Detected Edges", (w+20, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # Panel 3: Garment mask
        if correction_results['garment_mask'] is not None:
            mask_vis = cv2.cvtColor(correction_results['garment_mask'], cv2.COLOR_GRAY2BGR)
            report[h+55:2*h+55, 10:w+10] = cv2.resize(mask_vis, (w, h))
        cv2.putText(report, "Garment Mask", (15, 2*h+80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # Panel 4: Corrected landmarks
        panel4 = image.copy()
        for landmark in correction_results['corrected_landmarks']:
            if landmark is not None:
                cv2.circle(panel4, landmark, 5, (0, 255, 0), -1)
        report[h+55:2*h+55, w+15:2*w+15] = panel4
        cv2.putText(report, "Corrected Landmarks", (w+20, 2*h+80),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 128, 0), 2)

        cv2.imwrite(output_path, report)
        return report


def integrate_with_ensemble(ensemble_results: Dict,
                           image: np.ndarray,
                           corrector: EdgeAwareLandmarkCorrector) -> Dict:
    """
    Integrate edge correction with ensemble results
    """
    # Extract landmarks from ensemble
    landmarks = ensemble_results.get('ensemble_results', {}).get('landmarks', [])
    confidences = ensemble_results.get('ensemble_results', {}).get('confidences', [])

    # Apply edge correction
    correction_results = corrector.correct_landmarks(
        image,
        landmarks,
        confidences,
        has_background=not ensemble_results.get('background_removed', True)
    )

    # Update ensemble results
    ensemble_results['edge_correction'] = {
        'applied': True,
        'num_corrected': correction_results['validation']['num_corrected'],
        'avg_correction_distance': correction_results['validation']['avg_correction_distance']
    }

    # Replace landmarks with corrected ones
    ensemble_results['ensemble_results']['landmarks'] = correction_results['corrected_landmarks']
    ensemble_results['ensemble_results']['original_landmarks'] = landmarks

    return ensemble_results


def main():
    """
    Test edge-aware landmark correction
    """
    import argparse

    parser = argparse.ArgumentParser(description='Edge-Aware Landmark Correction')
    parser.add_argument('--image', type=str, required=True,
                       help='Input image path')
    parser.add_argument('--landmarks', type=str,
                       help='JSON file with landmarks (optional)')
    parser.add_argument('--output', type=str, default='edge_correction_output',
                       help='Output directory')
    parser.add_argument('--method', type=str, default='canny_morphology',
                       choices=['canny', 'canny_morphology', 'contour'],
                       help='Edge detection method')
    parser.add_argument('--threshold', type=int, default=50,
                       help='Edge detection threshold')
    parser.add_argument('--max-distance', type=int, default=100,
                       help='Maximum correction distance in pixels')

    args = parser.parse_args()

    # Create output directory
    import os
    os.makedirs(args.output, exist_ok=True)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Initialize corrector
    corrector = EdgeAwareLandmarkCorrector(
        edge_threshold=args.threshold,
        max_correction_distance=args.max_distance,
        edge_detection_method=args.method
    )

    # Load or generate test landmarks
    if args.landmarks:
        with open(args.landmarks, 'r') as f:
            data = json.load(f)
            landmarks = data.get('landmarks', [])
    else:
        # Generate test landmarks for demonstration
        print("Generating test landmarks...")
        # Import ensemble system to get landmarks
        from multi_model_ensemble import MultiModelEnsemble
        ensemble = MultiModelEnsemble()
        results = ensemble.detect_landmarks_ensemble(image, remove_background=False)
        landmarks = results['ensemble_results'].get('landmarks', [])

    print(f"Processing {len(landmarks)} landmarks...")

    # Apply correction
    correction_results = corrector.correct_landmarks(
        image,
        landmarks,
        has_background=False
    )

    # Print results
    print("\n" + "="*60)
    print("EDGE CORRECTION RESULTS")
    print("="*60)
    validation = correction_results['validation']
    print(f"Landmarks corrected: {validation['num_corrected']}/{len(landmarks)}")
    print(f"Average correction distance: {validation['avg_correction_distance']:.1f} pixels")
    print(f"Maximum correction distance: {validation['max_correction_distance']:.1f} pixels")
    print(f"Landmarks outside garment: {validation['num_outside']}")
    print(f"Landmarks inside but far from edge: {validation['num_inside_far']}")

    # Create visualizations
    vis_path = os.path.join(args.output, 'correction_visualization.jpg')
    corrector.visualize_corrections(image, correction_results, vis_path)
    print(f"\nVisualization saved to: {vis_path}")

    # Create analysis report
    report_path = os.path.join(args.output, 'edge_analysis_report.jpg')
    corrector.create_edge_analysis_report(image, correction_results, report_path)
    print(f"Analysis report saved to: {report_path}")

    # Save corrected landmarks
    output_data = {
        'original_landmarks': correction_results['original_landmarks'],
        'corrected_landmarks': correction_results['corrected_landmarks'],
        'validation': validation
    }

    json_path = os.path.join(args.output, 'corrected_landmarks.json')
    with open(json_path, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    print(f"Corrected landmarks saved to: {json_path}")


if __name__ == '__main__':
    main()