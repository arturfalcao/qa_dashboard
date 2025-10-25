#!/usr/bin/env python3
"""
Multi-Model Ensemble System for Fashion Landmark Detection

This system intelligently combines results from multiple fashion landmark detection models:
- SVIP-Lab HRNet (294 fashion-specific keypoints)
- Standard HRNet (general purpose)
- Fashionpedia (semantic segmentation + attributes)

Uses confidence-based voting, spatial clustering, and intelligent merging strategies.
"""

import os
import cv2
import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from scipy.spatial.distance import cdist
from sklearn.cluster import DBSCAN
import argparse

# Import our integrated modules
from sviplab_hrnet_integration import SVIPLabFashionDetector
from fashionpedia_integration import FashionpediaIntegration
from hrnet_landmark_detector import FashionLandmarkDetector
from fashion_pipeline import FashionAnalysisPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class LandmarkCandidate:
    """Represents a landmark candidate from any model"""
    position: Tuple[float, float]
    confidence: float
    source_model: str
    landmark_type: str
    metadata: Dict = None


class MultiModelEnsemble:
    """
    Advanced ensemble system that combines multiple fashion landmark detection models
    """

    # Model strengths based on validation results
    MODEL_WEIGHTS = {
        'sviplab': {
            'upper_body': 0.9,  # 99% accuracy on shirts
            'lower_body': 0.6,  # 57% accuracy on jeans
            'confidence_threshold': 0.3
        },
        'hrnet_standard': {
            'upper_body': 0.7,
            'lower_body': 0.7,
            'confidence_threshold': 0.4
        },
        'fashionpedia': {
            'semantic': 0.8,
            'attributes': 0.85,
            'confidence_threshold': 0.35
        }
    }

    # Landmark type priorities (which model is best for which landmark)
    LANDMARK_PRIORITIES = {
        'neckline': ['sviplab', 'hrnet_standard'],
        'shoulder': ['sviplab', 'hrnet_standard'],
        'sleeve': ['sviplab', 'fashionpedia'],
        'hem': ['sviplab', 'fashionpedia'],
        'waist': ['fashionpedia', 'sviplab'],
        'collar': ['sviplab', 'hrnet_standard'],
        'cuff': ['sviplab', 'hrnet_standard'],
        'pocket': ['fashionpedia', 'sviplab'],
        'button': ['fashionpedia', 'sviplab']
    }

    def __init__(self,
                 sviplab_model_path: str = 'models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
                 device: str = 'cpu',
                 ensemble_strategy: str = 'weighted_voting'):
        """
        Initialize the multi-model ensemble system

        Args:
            sviplab_model_path: Path to SVIP-Lab model
            device: Computing device
            ensemble_strategy: Strategy for combining results
                              ('weighted_voting', 'max_confidence', 'spatial_clustering')
        """
        self.device = device
        self.ensemble_strategy = ensemble_strategy

        # Initialize all models
        logger.info("Initializing multi-model ensemble...")

        # SVIP-Lab HRNet (best for fashion-specific landmarks)
        self.sviplab_detector = SVIPLabFashionDetector(
            model_path=sviplab_model_path,
            device=device
        )

        # Standard HRNet (good general performance)
        self.hrnet_detector = FashionLandmarkDetector(
            model_path=sviplab_model_path,
            device=device
        )

        # Fashionpedia (best for semantic understanding)
        self.fashionpedia = FashionpediaIntegration()

        # Background removal pipeline
        self.bg_remover = FashionAnalysisPipeline()

        logger.info("Multi-model ensemble initialized successfully")

    def detect_landmarks_ensemble(self,
                                 image: np.ndarray,
                                 remove_background: bool = True) -> Dict[str, Any]:
        """
        Detect landmarks using all models and consolidate results

        Args:
            image: Input image (BGR)
            remove_background: Whether to remove background first

        Returns:
            Consolidated detection results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'individual_models': {},
            'ensemble_results': {},
            'metadata': {}
        }

        # Step 1: Preprocess image (background removal if needed)
        if remove_background:
            logger.info("Removing background...")
            try:
                bg_result = self.bg_remover.process_image_from_array(
                    image,
                    remove_background=True,
                    detect_landmarks=False
                )
                if bg_result.get('white_background') is not None:
                    clean_image = cv2.cvtColor(bg_result['white_background'], cv2.COLOR_RGB2BGR)
                    results['background_removed'] = True
                else:
                    clean_image = image
                    results['background_removed'] = False
            except Exception as e:
                logger.warning(f"Background removal failed: {e}")
                clean_image = image
                results['background_removed'] = False
        else:
            clean_image = image

        # Step 2: Run all models in parallel (collect candidates)
        all_candidates = []

        # SVIP-Lab detection
        logger.info("Running SVIP-Lab HRNet...")
        sviplab_result = self._run_sviplab_detection(clean_image)
        results['individual_models']['sviplab'] = sviplab_result
        all_candidates.extend(self._extract_candidates(sviplab_result, 'sviplab'))

        # Standard HRNet detection
        logger.info("Running standard HRNet...")
        hrnet_result = self._run_hrnet_detection(clean_image)
        results['individual_models']['hrnet'] = hrnet_result
        all_candidates.extend(self._extract_candidates(hrnet_result, 'hrnet_standard'))

        # Fashionpedia detection
        logger.info("Running Fashionpedia...")
        fashionpedia_result = self._run_fashionpedia_detection(clean_image)
        results['individual_models']['fashionpedia'] = fashionpedia_result
        all_candidates.extend(self._extract_candidates(fashionpedia_result, 'fashionpedia'))

        # Step 3: Consolidate results using ensemble strategy
        logger.info(f"Consolidating results using {self.ensemble_strategy} strategy...")

        if self.ensemble_strategy == 'weighted_voting':
            consolidated = self._weighted_voting_ensemble(all_candidates, sviplab_result.get('category', 'unknown'))
        elif self.ensemble_strategy == 'spatial_clustering':
            consolidated = self._spatial_clustering_ensemble(all_candidates)
        else:  # max_confidence
            consolidated = self._max_confidence_ensemble(all_candidates)

        results['ensemble_results'] = consolidated

        # Step 4: Category classification (use majority voting)
        results['category'] = self._determine_category_ensemble(results['individual_models'])

        # Step 5: Extract final measurements
        results['measurements'] = self._extract_ensemble_measurements(consolidated, image.shape)

        return results

    def _run_sviplab_detection(self, image: np.ndarray) -> Dict:
        """Run SVIP-Lab HRNet detection"""
        try:
            result = self.sviplab_detector.detect_landmarks(image)
            return {
                'success': True,
                'landmarks': result['landmarks'],
                'confidences': result['confidences'],
                'category': result['category'],
                'num_detected': result['num_detected']
            }
        except Exception as e:
            logger.error(f"SVIP-Lab detection failed: {e}")
            return {'success': False, 'error': str(e)}

    def _run_hrnet_detection(self, image: np.ndarray) -> Dict:
        """Run standard HRNet detection"""
        try:
            result = self.hrnet_detector.detect_landmarks(image)
            if result and 'keypoints' in result:
                keypoints = result['keypoints'][0] if len(result['keypoints']) > 0 else []
                return {
                    'success': True,
                    'keypoints': keypoints,
                    'landmark_labels': result.get('landmark_labels', {})
                }
            return {'success': False, 'error': 'No keypoints detected'}
        except Exception as e:
            logger.error(f"HRNet detection failed: {e}")
            return {'success': False, 'error': str(e)}

    def _run_fashionpedia_detection(self, image: np.ndarray) -> Dict:
        """Run Fashionpedia detection"""
        try:
            result = self.fashionpedia.process_image_with_fashionpedia(
                image,
                use_segmentation=True,
                detect_attributes=True
            )
            return {
                'success': True,
                'categories': result.get('categories', []),
                'attributes': result.get('attributes', {}),
                'measurement_zones': result.get('measurement_zones', []),
                'keypoints': result.get('keypoints', [])
            }
        except Exception as e:
            logger.error(f"Fashionpedia detection failed: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_candidates(self, result: Dict, model_name: str) -> List[LandmarkCandidate]:
        """Extract landmark candidates from model results"""
        candidates = []

        if not result.get('success', False):
            return candidates

        if model_name == 'sviplab':
            landmarks = result.get('landmarks', [])
            confidences = result.get('confidences', [])
            for i, (landmark, confidence) in enumerate(zip(landmarks, confidences)):
                if landmark is not None and confidence > self.MODEL_WEIGHTS['sviplab']['confidence_threshold']:
                    candidates.append(LandmarkCandidate(
                        position=landmark,
                        confidence=confidence,
                        source_model='sviplab',
                        landmark_type=self._get_landmark_type_from_index(i),
                        metadata={'index': i}
                    ))

        elif model_name == 'hrnet_standard':
            keypoints = result.get('keypoints', [])
            for i, kp in enumerate(keypoints):
                if len(kp) >= 3:  # x, y, confidence
                    confidence = kp[2] if len(kp) > 2 else 1.0
                    if confidence > self.MODEL_WEIGHTS['hrnet_standard']['confidence_threshold']:
                        candidates.append(LandmarkCandidate(
                            position=(kp[0], kp[1]),
                            confidence=confidence,
                            source_model='hrnet_standard',
                            landmark_type=f'hrnet_kp_{i}',
                            metadata={'index': i}
                        ))

        elif model_name == 'fashionpedia':
            keypoints = result.get('keypoints', [])
            for kp in keypoints:
                if isinstance(kp, dict) and 'position' in kp:
                    candidates.append(LandmarkCandidate(
                        position=kp['position'],
                        confidence=kp.get('confidence', 0.5),
                        source_model='fashionpedia',
                        landmark_type=kp.get('type', 'unknown'),
                        metadata=kp
                    ))

        return candidates

    def _weighted_voting_ensemble(self,
                                 candidates: List[LandmarkCandidate],
                                 category: str) -> Dict:
        """
        Consolidate landmarks using weighted voting based on model strengths
        """
        # Determine garment type for weighting
        is_upper = category in ['shirt', 'vest', 'short_sleeved_shirt', 'long_sleeved_shirt']

        # Group candidates by spatial proximity
        if not candidates:
            return {'landmarks': [], 'confidences': []}

        positions = np.array([c.position for c in candidates])

        # Use DBSCAN to cluster nearby landmarks
        clustering = DBSCAN(eps=20, min_samples=1).fit(positions)

        consolidated_landmarks = []
        consolidated_confidences = []

        for cluster_id in set(clustering.labels_):
            cluster_indices = np.where(clustering.labels_ == cluster_id)[0]
            cluster_candidates = [candidates[i] for i in cluster_indices]

            # Calculate weighted position and confidence
            total_weight = 0
            weighted_x = 0
            weighted_y = 0
            max_confidence = 0

            for candidate in cluster_candidates:
                # Get model-specific weight
                if candidate.source_model == 'sviplab':
                    weight = self.MODEL_WEIGHTS['sviplab']['upper_body' if is_upper else 'lower_body']
                elif candidate.source_model == 'hrnet_standard':
                    weight = self.MODEL_WEIGHTS['hrnet_standard']['upper_body' if is_upper else 'lower_body']
                else:  # fashionpedia
                    weight = self.MODEL_WEIGHTS['fashionpedia']['semantic']

                # Apply confidence-based weighting
                weight *= candidate.confidence

                weighted_x += candidate.position[0] * weight
                weighted_y += candidate.position[1] * weight
                total_weight += weight
                max_confidence = max(max_confidence, candidate.confidence)

            if total_weight > 0:
                final_x = weighted_x / total_weight
                final_y = weighted_y / total_weight
                consolidated_landmarks.append((int(final_x), int(final_y)))
                consolidated_confidences.append(max_confidence)

        return {
            'landmarks': consolidated_landmarks,
            'confidences': consolidated_confidences,
            'num_landmarks': len(consolidated_landmarks),
            'clustering_info': {
                'num_clusters': len(set(clustering.labels_)),
                'num_candidates': len(candidates)
            }
        }

    def _spatial_clustering_ensemble(self, candidates: List[LandmarkCandidate]) -> Dict:
        """
        Consolidate using spatial clustering (DBSCAN)
        """
        if not candidates:
            return {'landmarks': [], 'confidences': []}

        positions = np.array([c.position for c in candidates])

        # Adaptive epsilon based on image size
        eps = min(30, max(10, len(candidates) / 10))
        clustering = DBSCAN(eps=eps, min_samples=2).fit(positions)

        consolidated_landmarks = []
        consolidated_confidences = []

        for cluster_id in set(clustering.labels_):
            if cluster_id == -1:  # Noise points
                continue

            cluster_indices = np.where(clustering.labels_ == cluster_id)[0]
            cluster_positions = positions[cluster_indices]
            cluster_candidates = [candidates[i] for i in cluster_indices]

            # Use centroid of cluster
            centroid = np.mean(cluster_positions, axis=0)

            # Use maximum confidence in cluster
            max_confidence = max(c.confidence for c in cluster_candidates)

            consolidated_landmarks.append((int(centroid[0]), int(centroid[1])))
            consolidated_confidences.append(max_confidence)

        return {
            'landmarks': consolidated_landmarks,
            'confidences': consolidated_confidences,
            'num_landmarks': len(consolidated_landmarks),
            'noise_points': np.sum(clustering.labels_ == -1)
        }

    def _max_confidence_ensemble(self, candidates: List[LandmarkCandidate]) -> Dict:
        """
        Simple strategy: take landmarks with highest confidence
        """
        if not candidates:
            return {'landmarks': [], 'confidences': []}

        # Sort by confidence
        sorted_candidates = sorted(candidates, key=lambda c: c.confidence, reverse=True)

        # Take top N candidates with non-overlapping positions
        consolidated_landmarks = []
        consolidated_confidences = []
        min_distance = 15  # Minimum pixels between landmarks

        for candidate in sorted_candidates:
            # Check if too close to existing landmarks
            too_close = False
            for existing in consolidated_landmarks:
                dist = np.sqrt((candidate.position[0] - existing[0])**2 +
                             (candidate.position[1] - existing[1])**2)
                if dist < min_distance:
                    too_close = True
                    break

            if not too_close:
                consolidated_landmarks.append(candidate.position)
                consolidated_confidences.append(candidate.confidence)

        return {
            'landmarks': consolidated_landmarks,
            'confidences': consolidated_confidences,
            'num_landmarks': len(consolidated_landmarks)
        }

    def _determine_category_ensemble(self, individual_results: Dict) -> str:
        """
        Determine garment category using majority voting from all models
        """
        categories = []

        # SVIP-Lab category
        if individual_results.get('sviplab', {}).get('success'):
            svip_cat = individual_results['sviplab'].get('category', '')
            if svip_cat:
                # Weight SVIP-Lab higher for fashion-specific categories
                categories.extend([svip_cat] * 2)

        # Fashionpedia categories
        if individual_results.get('fashionpedia', {}).get('success'):
            fashion_cats = individual_results['fashionpedia'].get('categories', [])
            categories.extend(fashion_cats)

        if not categories:
            return 'unknown'

        # Find most common category
        from collections import Counter
        category_counts = Counter(categories)
        return category_counts.most_common(1)[0][0]

    def _get_landmark_type_from_index(self, index: int) -> str:
        """
        Map landmark index to type based on DeepFashion2 structure
        """
        # Simplified mapping - would need full mapping table
        if index < 25:
            return 'short_sleeve_shirt'
        elif index < 58:
            return 'long_sleeve_shirt'
        elif index < 143:
            return 'outerwear'
        elif index < 158:
            return 'vest_or_sling'
        elif index < 182:
            return 'bottom'
        elif index < 190:
            return 'skirt'
        else:
            return 'dress'

    def _extract_ensemble_measurements(self,
                                      consolidated: Dict,
                                      image_shape: Tuple) -> Dict:
        """
        Extract measurements from consolidated landmarks
        """
        measurements = {}
        landmarks = consolidated.get('landmarks', [])

        if len(landmarks) < 2:
            return measurements

        # Find key measurement pairs
        # This is simplified - would need proper landmark pairing logic
        if len(landmarks) >= 10:
            # Estimate shoulder width (typically landmarks 5-10)
            shoulder_left = landmarks[5] if len(landmarks) > 5 else None
            shoulder_right = landmarks[10] if len(landmarks) > 10 else None

            if shoulder_left and shoulder_right:
                measurements['shoulder_width'] = np.sqrt(
                    (shoulder_right[0] - shoulder_left[0])**2 +
                    (shoulder_right[1] - shoulder_left[1])**2
                )

        if len(landmarks) >= 15:
            # Estimate chest width
            chest_left = landmarks[6] if len(landmarks) > 6 else None
            chest_right = landmarks[11] if len(landmarks) > 11 else None

            if chest_left and chest_right:
                measurements['chest_width'] = np.sqrt(
                    (chest_right[0] - chest_left[0])**2 +
                    (chest_right[1] - chest_left[1])**2
                )

        # Add garment length if hem points detected
        if len(landmarks) >= 20:
            measurements['num_landmarks'] = len(landmarks)
            measurements['avg_confidence'] = np.mean(consolidated.get('confidences', []))

        return measurements

    def visualize_ensemble_results(self,
                                  image: np.ndarray,
                                  ensemble_results: Dict,
                                  output_path: Optional[str] = None) -> np.ndarray:
        """
        Create visualization of ensemble results
        """
        vis_image = image.copy()

        # Draw consolidated landmarks
        landmarks = ensemble_results.get('ensemble_results', {}).get('landmarks', [])
        confidences = ensemble_results.get('ensemble_results', {}).get('confidences', [])

        for landmark, confidence in zip(landmarks, confidences):
            if landmark:
                # Color based on confidence
                color = (0, int(255 * confidence), int(255 * (1 - confidence)))
                cv2.circle(vis_image, tuple(map(int, landmark)), 5, color, -1)
                cv2.circle(vis_image, tuple(map(int, landmark)), 7, (0, 0, 0), 1)

        # Add text overlay
        text = f"Ensemble: {len(landmarks)} landmarks | Category: {ensemble_results.get('category', 'unknown')}"
        cv2.putText(vis_image, text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Add measurements
        y_offset = 60
        for key, value in ensemble_results.get('measurements', {}).items():
            text = f"{key}: {value:.1f}"
            cv2.putText(vis_image, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)
            y_offset += 25

        if output_path:
            cv2.imwrite(output_path, vis_image)

        return vis_image

    def create_comparison_report(self,
                                image: np.ndarray,
                                ensemble_results: Dict,
                                output_dir: str) -> str:
        """
        Create detailed comparison report showing all models vs ensemble
        """
        h, w = image.shape[:2]

        # Create 2x3 grid for comparison
        grid_h = h * 2 + 60
        grid_w = w * 3 + 40
        report = np.ones((grid_h, grid_w, 3), dtype=np.uint8) * 240

        # Original image
        report[10:h+10, 10:w+10] = image
        cv2.putText(report, "Original", (15, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # SVIP-Lab results
        if ensemble_results['individual_models'].get('sviplab', {}).get('success'):
            svip_vis = self._visualize_model_results(
                image.copy(),
                ensemble_results['individual_models']['sviplab'],
                'SVIP-Lab'
            )
            report[10:h+10, w+20:2*w+20] = cv2.resize(svip_vis, (w, h))
        cv2.putText(report, "SVIP-Lab HRNet", (w+25, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # HRNet Standard results
        if ensemble_results['individual_models'].get('hrnet', {}).get('success'):
            hrnet_vis = self._visualize_model_results(
                image.copy(),
                ensemble_results['individual_models']['hrnet'],
                'HRNet'
            )
            report[10:h+10, 2*w+30:3*w+30] = cv2.resize(hrnet_vis, (w, h))
        cv2.putText(report, "Standard HRNet", (2*w+35, h+35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # Fashionpedia results
        if ensemble_results['individual_models'].get('fashionpedia', {}).get('success'):
            fashion_vis = self._visualize_model_results(
                image.copy(),
                ensemble_results['individual_models']['fashionpedia'],
                'Fashionpedia'
            )
            report[h+50:2*h+50, 10:w+10] = cv2.resize(fashion_vis, (w, h))
        cv2.putText(report, "Fashionpedia", (15, 2*h+75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # Ensemble results
        ensemble_vis = self.visualize_ensemble_results(image.copy(), ensemble_results)
        report[h+50:2*h+50, w+20:2*w+20] = cv2.resize(ensemble_vis, (w, h))
        cv2.putText(report, f"ENSEMBLE ({self.ensemble_strategy})",
                   (w+25, 2*h+75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Statistics panel
        stats_panel = np.ones((h, w, 3), dtype=np.uint8) * 255
        y_offset = 30

        cv2.putText(stats_panel, "Model Comparison", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        y_offset += 30

        # Add statistics for each model
        for model_name, model_data in ensemble_results['individual_models'].items():
            if model_data.get('success'):
                if model_name == 'sviplab':
                    text = f"SVIP: {model_data.get('num_detected', 0)} landmarks"
                else:
                    text = f"{model_name}: Active"
                cv2.putText(stats_panel, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                y_offset += 20

        y_offset += 20
        cv2.putText(stats_panel, "Ensemble Results:", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 0), 2)
        y_offset += 25

        ensemble_data = ensemble_results.get('ensemble_results', {})
        cv2.putText(stats_panel, f"Landmarks: {ensemble_data.get('num_landmarks', 0)}",
                   (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        y_offset += 20

        cv2.putText(stats_panel, f"Category: {ensemble_results.get('category', 'unknown')}",
                   (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        report[h+50:2*h+50, 2*w+30:3*w+30] = stats_panel

        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'{timestamp}_ensemble_comparison.jpg')
        cv2.imwrite(output_path, report)

        return output_path

    def _visualize_model_results(self,
                                image: np.ndarray,
                                results: Dict,
                                model_name: str) -> np.ndarray:
        """
        Visualize individual model results
        """
        vis = image.copy()

        if model_name == 'SVIP-Lab':
            landmarks = results.get('landmarks', [])
            for landmark in landmarks:
                if landmark:
                    cv2.circle(vis, landmark, 4, (255, 0, 0), -1)
        elif model_name == 'HRNet':
            keypoints = results.get('keypoints', [])
            for kp in keypoints:
                if len(kp) >= 2:
                    cv2.circle(vis, (int(kp[0]), int(kp[1])), 4, (0, 255, 0), -1)
        elif model_name == 'Fashionpedia':
            # Visualize categories as text
            categories = results.get('categories', [])
            if categories:
                cv2.putText(vis, ', '.join(categories), (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)

        return vis


def main():
    parser = argparse.ArgumentParser(description='Multi-Model Ensemble Fashion Analysis')
    parser.add_argument('--image', type=str, required=True,
                       help='Path to input garment image')
    parser.add_argument('--output', type=str, default='ensemble_output',
                       help='Output directory for results')
    parser.add_argument('--strategy', type=str, default='weighted_voting',
                       choices=['weighted_voting', 'spatial_clustering', 'max_confidence'],
                       help='Ensemble strategy to use')
    parser.add_argument('--device', type=str, default='cpu',
                       choices=['cpu', 'cuda'],
                       help='Computing device')
    parser.add_argument('--no-bg-removal', action='store_true',
                       help='Skip background removal')
    parser.add_argument('--compare', action='store_true',
                       help='Generate comparison report')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Initialize ensemble
    ensemble = MultiModelEnsemble(
        device=args.device,
        ensemble_strategy=args.strategy
    )

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image {args.image}")
        return

    # Run ensemble detection
    print(f"Running multi-model ensemble with {args.strategy} strategy...")
    results = ensemble.detect_landmarks_ensemble(
        image,
        remove_background=not args.no_bg_removal
    )

    # Create visualizations
    vis_path = os.path.join(args.output, 'ensemble_visualization.jpg')
    ensemble.visualize_ensemble_results(image, results, vis_path)

    if args.compare:
        report_path = ensemble.create_comparison_report(image, results, args.output)
        print(f"Comparison report saved to: {report_path}")

    # Save JSON results
    json_path = os.path.join(args.output, 'ensemble_results.json')
    with open(json_path, 'w') as f:
        # Convert numpy types for JSON serialization
        json_results = json.loads(json.dumps(results, default=str))
        json.dump(json_results, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("MULTI-MODEL ENSEMBLE RESULTS")
    print("="*60)
    print(f"Strategy: {args.strategy}")
    print(f"Category: {results.get('category', 'unknown')}")
    print(f"Background Removed: {results.get('background_removed', False)}")

    ensemble_data = results.get('ensemble_results', {})
    print(f"\nEnsemble Landmarks: {ensemble_data.get('num_landmarks', 0)}")

    if 'clustering_info' in ensemble_data:
        print(f"Clustering Info:")
        print(f"  - Clusters: {ensemble_data['clustering_info']['num_clusters']}")
        print(f"  - Candidates: {ensemble_data['clustering_info']['num_candidates']}")

    print("\nIndividual Model Performance:")
    for model, data in results.get('individual_models', {}).items():
        if data.get('success'):
            if model == 'sviplab':
                print(f"  SVIP-Lab: {data.get('num_detected', 0)} landmarks")
            else:
                print(f"  {model}: Active")

    print("\nMeasurements:")
    for key, value in results.get('measurements', {}).items():
        print(f"  {key}: {value:.1f}")

    print(f"\nResults saved to: {args.output}")
    print(f"  - Visualization: {vis_path}")
    print(f"  - JSON: {json_path}")


if __name__ == '__main__':
    main()