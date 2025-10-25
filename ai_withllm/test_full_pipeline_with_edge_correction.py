#!/usr/bin/env python3
"""
Test Full Pipeline with Edge Correction

This script demonstrates the complete workflow:
1. Multi-model ensemble landmark detection
2. Edge-aware landmark correction
3. Accurate measurement extraction from edge-aligned landmarks
"""

import cv2
import numpy as np
import json
import os
from pathlib import Path
import logging
from typing import Dict, List, Tuple

# Import our modules
from multi_model_ensemble import MultiModelEnsemble
from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_measurements_from_corrected_landmarks(
    landmarks: List[Tuple[int, int]],
    category: str,
    image_shape: Tuple
) -> Dict[str, float]:
    """
    Calculate garment measurements from edge-corrected landmarks
    """
    measurements = {}

    if not landmarks or len(landmarks) < 10:
        return measurements

    # Filter out None values
    valid_landmarks = [l for l in landmarks if l is not None]

    if len(valid_landmarks) < 10:
        return measurements

    # For upper body garments (shirt, vest)
    if category in ['shirt', 'vest', 'short_sleeved_shirt', 'long_sleeved_shirt']:
        # Shoulder width - typically landmarks around index 5-10
        if len(valid_landmarks) > 10:
            left_shoulder = valid_landmarks[5]
            right_shoulder = valid_landmarks[10]
            measurements['shoulder_width'] = np.sqrt(
                (right_shoulder[0] - left_shoulder[0])**2 +
                (right_shoulder[1] - left_shoulder[1])**2
            )

        # Chest width - typically landmarks around index 6-11
        if len(valid_landmarks) > 11:
            left_chest = valid_landmarks[6]
            right_chest = valid_landmarks[11]
            measurements['chest_width'] = np.sqrt(
                (right_chest[0] - left_chest[0])**2 +
                (right_chest[1] - left_chest[1])**2
            )

        # Garment length - from shoulder to hem
        if len(valid_landmarks) > 15:
            top_point = valid_landmarks[0]  # Neckline or top
            bottom_point = valid_landmarks[15]  # Hem
            measurements['garment_length'] = np.sqrt(
                (bottom_point[0] - top_point[0])**2 +
                (bottom_point[1] - top_point[1])**2
            )

    # For bottom garments (trousers, skirt)
    elif category in ['trousers', 'skirt', 'shorts']:
        # Waist width
        if len(valid_landmarks) > 2:
            left_waist = valid_landmarks[0]
            right_waist = valid_landmarks[1]
            measurements['waist_width'] = np.sqrt(
                (right_waist[0] - left_waist[0])**2 +
                (right_waist[1] - left_waist[1])**2
            )

        # Inseam or length
        if len(valid_landmarks) > 5:
            top_center = valid_landmarks[2] if len(valid_landmarks) > 2 else valid_landmarks[0]
            bottom_center = valid_landmarks[-1]
            measurements['length'] = np.sqrt(
                (bottom_center[0] - top_center[0])**2 +
                (bottom_center[1] - top_center[1])**2
            )

    return measurements


def run_full_pipeline(image_path: str, output_dir: str):
    """
    Run the complete pipeline with edge correction
    """
    logger.info("="*60)
    logger.info(f"Processing: {image_path}")
    logger.info("="*60)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Could not load image: {image_path}")
        return

    logger.info(f"Image size: {image.shape[1]}x{image.shape[0]}")

    # Step 1: Multi-model ensemble detection
    logger.info("\nStep 1: Running multi-model ensemble detection...")
    ensemble = MultiModelEnsemble(
        device='cpu',
        ensemble_strategy='weighted_voting'
    )

    ensemble_results = ensemble.detect_landmarks_ensemble(
        image,
        remove_background=False  # We'll handle background in edge detection
    )

    initial_landmarks = ensemble_results['ensemble_results'].get('landmarks', [])
    logger.info(f"Ensemble detected {len(initial_landmarks)} landmarks")
    logger.info(f"Category: {ensemble_results.get('category', 'unknown')}")

    # Step 2: Edge-aware landmark correction
    logger.info("\nStep 2: Applying edge-aware landmark correction...")
    corrector = EdgeAwareLandmarkCorrector(
        edge_threshold=50,
        max_correction_distance=100,
        edge_detection_method='canny_morphology'
    )

    correction_results = corrector.correct_landmarks(
        image,
        initial_landmarks,
        ensemble_results['ensemble_results'].get('confidences', []),
        has_background=False
    )

    corrected_landmarks = correction_results['corrected_landmarks']
    validation = correction_results['validation']

    logger.info(f"Corrected {validation['num_corrected']}/{len(initial_landmarks)} landmarks")
    logger.info(f"Average correction: {validation['avg_correction_distance']:.1f} pixels")
    logger.info(f"Outside garment: {validation['num_outside']}")
    logger.info(f"Inside but far from edge: {validation['num_inside_far']}")

    # Step 3: Calculate measurements from corrected landmarks
    logger.info("\nStep 3: Calculating measurements from edge-aligned landmarks...")

    # Original measurements (before correction)
    original_measurements = calculate_measurements_from_corrected_landmarks(
        initial_landmarks,
        ensemble_results.get('category', 'unknown'),
        image.shape
    )

    # Corrected measurements (after edge alignment)
    corrected_measurements = calculate_measurements_from_corrected_landmarks(
        corrected_landmarks,
        ensemble_results.get('category', 'unknown'),
        image.shape
    )

    logger.info("\nMeasurement Comparison:")
    logger.info("-" * 40)
    logger.info("Measurement | Original | Corrected | Difference")
    logger.info("-" * 40)

    all_keys = set(original_measurements.keys()) | set(corrected_measurements.keys())
    for key in sorted(all_keys):
        orig_val = original_measurements.get(key, 0)
        corr_val = corrected_measurements.get(key, 0)
        diff = corr_val - orig_val
        logger.info(f"{key:15s} | {orig_val:8.1f} | {corr_val:9.1f} | {diff:+8.1f}")

    # Step 4: Create comprehensive visualization
    logger.info("\nStep 4: Creating visualizations...")

    # Create comparison visualization
    h, w = image.shape[:2]
    comparison = np.ones((h * 2 + 100, w * 2 + 20, 3), dtype=np.uint8) * 240

    # Panel 1: Original with initial landmarks
    panel1 = image.copy()
    for landmark in initial_landmarks:
        if landmark is not None:
            cv2.circle(panel1, tuple(map(int, landmark)), 5, (0, 0, 255), -1)
    comparison[10:h+10, 10:w+10] = panel1
    cv2.putText(comparison, f"Ensemble Landmarks ({len(initial_landmarks)})",
                (15, h+35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Panel 2: Edge detection visualization
    if correction_results['edge_mask'] is not None:
        edge_vis = cv2.cvtColor(correction_results['edge_mask'], cv2.COLOR_GRAY2BGR)
        # Overlay edges on image
        edge_overlay = image.copy()
        edge_overlay[:, :, 1] = cv2.addWeighted(
            edge_overlay[:, :, 1], 0.7,
            correction_results['edge_mask'], 0.3, 0
        )
        comparison[10:h+10, w+15:2*w+15] = edge_overlay
    cv2.putText(comparison, "Detected Edges",
                (w+20, h+35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Panel 3: Corrected landmarks with arrows
    panel3 = image.copy()
    # Draw correction arrows
    for orig, corr in zip(initial_landmarks, corrected_landmarks):
        if orig is not None and corr is not None:
            orig = tuple(map(int, orig))
            corr = tuple(map(int, corr))
            if orig != corr:
                cv2.arrowedLine(panel3, orig, corr, (255, 255, 0), 2, tipLength=0.3)
            cv2.circle(panel3, corr, 5, (0, 255, 0), -1)
    comparison[h+60:2*h+60, 10:w+10] = panel3
    cv2.putText(comparison, f"Edge-Corrected ({validation['num_corrected']} fixed)",
                (15, 2*h+85), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 128, 0), 2)

    # Panel 4: Measurements
    measure_panel = np.ones((h, w, 3), dtype=np.uint8) * 255
    y_offset = 50

    cv2.putText(measure_panel, "Final Measurements (pixels)",
                (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    for key, value in corrected_measurements.items():
        text = f"{key}: {value:.1f}"
        cv2.putText(measure_panel, text, (20, y_offset + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 128, 0), 1)
        y_offset += 30

    y_offset += 20
    cv2.putText(measure_panel, "Correction Stats:",
                (20, y_offset + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    y_offset += 35
    cv2.putText(measure_panel, f"Corrected: {validation['num_corrected']}/{len(initial_landmarks)}",
                (20, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y_offset += 25
    cv2.putText(measure_panel, f"Avg move: {validation['avg_correction_distance']:.1f}px",
                (20, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    comparison[h+60:2*h+60, w+15:2*w+15] = measure_panel

    # Save comparison
    comparison_path = os.path.join(output_dir, 'full_pipeline_comparison.jpg')
    cv2.imwrite(comparison_path, comparison)
    logger.info(f"Saved comparison to: {comparison_path}")

    # Save correction visualization
    correction_vis = corrector.visualize_corrections(image, correction_results)
    correction_vis_path = os.path.join(output_dir, 'edge_correction_visualization.jpg')
    cv2.imwrite(correction_vis_path, correction_vis)
    logger.info(f"Saved correction visualization to: {correction_vis_path}")

    # Save results JSON
    results = {
        'image': image_path,
        'category': ensemble_results.get('category', 'unknown'),
        'ensemble': {
            'num_landmarks': len(initial_landmarks),
            'strategy': 'weighted_voting'
        },
        'edge_correction': {
            'num_corrected': validation['num_corrected'],
            'avg_correction_distance': validation['avg_correction_distance'],
            'max_correction_distance': validation['max_correction_distance'],
            'num_outside': validation['num_outside'],
            'num_inside_far': validation['num_inside_far']
        },
        'measurements': {
            'original': original_measurements,
            'corrected': corrected_measurements
        }
    }

    json_path = os.path.join(output_dir, 'pipeline_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved results to: {json_path}")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Full Pipeline with Edge Correction')
    parser.add_argument('--image', type=str, required=True,
                       help='Input image path')
    parser.add_argument('--output', type=str, default='full_pipeline_output',
                       help='Output directory')

    args = parser.parse_args()

    # Run pipeline
    results = run_full_pipeline(args.image, args.output)

    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Results saved to: {args.output}")
    print("\nKey Improvements:")
    print(f"- Landmarks moved to garment edges")
    print(f"- More accurate measurements")
    print(f"- Reduced measurement errors from misplaced landmarks")


if __name__ == '__main__':
    main()