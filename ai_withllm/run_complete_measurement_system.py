#!/usr/bin/env python3
"""
Complete Focused Measurement System Runner
Runs the full pipeline and generates all deliverables
"""

import cv2
import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path
import logging

# Import all our modules
from multi_model_ensemble import MultiModelEnsemble
from edge_aware_landmark_corrector import EdgeAwareLandmarkCorrector
from spatial_measurement_extractor import SpatialMeasurementExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_complete_measurement_pipeline(image_path: str, output_base_dir: str):
    """
    Run the complete measurement pipeline on an image
    """
    image_name = Path(image_path).stem
    output_dir = os.path.join(output_base_dir, image_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"PROCESSING: {image_name}")
    print(f"{'='*80}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return None

    print(f"Image size: {image.shape[1]}x{image.shape[0]} pixels")

    # STEP 1: Multi-Model Ensemble Detection
    print("\n[1/4] Running Multi-Model Ensemble Detection...")
    ensemble = MultiModelEnsemble(
        device='cpu',
        ensemble_strategy='weighted_voting'
    )

    ensemble_results = ensemble.detect_landmarks_ensemble(
        image,
        remove_background=False
    )

    initial_landmarks = ensemble_results['ensemble_results'].get('landmarks', [])
    initial_confidences = ensemble_results['ensemble_results'].get('confidences', [])

    print(f"  ✓ Detected {len(initial_landmarks)} initial landmarks")
    print(f"  ✓ Category: {ensemble_results.get('category', 'unknown')}")

    # Save ensemble visualization
    ensemble_vis = ensemble.visualize_ensemble_results(image, ensemble_results)
    ensemble_vis_path = os.path.join(output_dir, f'{image_name}_1_ensemble.jpg')
    cv2.imwrite(ensemble_vis_path, ensemble_vis)

    # STEP 2: Edge-Aware Landmark Correction
    print("\n[2/4] Applying Edge-Aware Landmark Correction...")
    corrector = EdgeAwareLandmarkCorrector(
        edge_threshold=50,
        max_correction_distance=100,
        edge_detection_method='canny_morphology'
    )

    correction_results = corrector.correct_landmarks(
        image,
        initial_landmarks,
        initial_confidences,
        has_background=False
    )

    corrected_landmarks = correction_results['corrected_landmarks']
    corrected_confidences = initial_confidences  # Keep same confidences

    validation = correction_results['validation']
    print(f"  ✓ Corrected {validation['num_corrected']}/{len(initial_landmarks)} landmarks")
    print(f"  ✓ Average correction: {validation['avg_correction_distance']:.1f} pixels")

    # Save correction visualization
    correction_vis = corrector.visualize_corrections(image, correction_results)
    correction_vis_path = os.path.join(output_dir, f'{image_name}_2_edge_correction.jpg')
    cv2.imwrite(correction_vis_path, correction_vis)

    # STEP 3: Spatial Measurement Extraction
    print("\n[3/4] Extracting Key Measurement Points...")
    extractor = SpatialMeasurementExtractor()

    measurement_results = extractor.extract_measurement_points(
        corrected_landmarks,
        corrected_confidences,
        image.shape
    )

    measurement_points = measurement_results['measurement_points']
    measurements = measurement_results['measurements']

    print(f"  ✓ Identified {len(measurement_points)} key measurement points:")
    for name, point in measurement_points.items():
        print(f"    • {name}: {point.type}")

    print(f"\n  ✓ Calculated {len(measurements)} measurements:")
    for name, value in measurements.items():
        print(f"    • {name}: {value:.1f} pixels")

    # Save measurement visualization
    measurement_vis = extractor.visualize_measurement_points(image, measurement_results)
    measurement_vis_path = os.path.join(output_dir, f'{image_name}_3_measurements.jpg')
    cv2.imwrite(measurement_vis_path, measurement_vis)

    # STEP 4: Create Final Comprehensive Report
    print("\n[4/4] Creating Final Report...")
    final_report = create_final_report(
        image,
        initial_landmarks,
        corrected_landmarks,
        measurement_points,
        measurements,
        ensemble_results.get('category', 'unknown')
    )

    report_path = os.path.join(output_dir, f'{image_name}_4_final_report.jpg')
    cv2.imwrite(report_path, final_report)

    # Save JSON results
    results = {
        'image': image_path,
        'image_size': {'width': image.shape[1], 'height': image.shape[0]},
        'timestamp': datetime.now().isoformat(),
        'category': ensemble_results.get('category', 'unknown'),
        'pipeline_stages': {
            'ensemble': {
                'num_landmarks': len(initial_landmarks),
                'strategy': 'weighted_voting'
            },
            'edge_correction': {
                'num_corrected': validation['num_corrected'],
                'avg_correction_distance': validation['avg_correction_distance']
            },
            'spatial_extraction': {
                'num_key_points': len(measurement_points),
                'num_measurements': len(measurements)
            }
        },
        'key_points': {
            name: {
                'position': [int(p.position[0]), int(p.position[1])],
                'type': p.type,
                'confidence': float(p.confidence)
            }
            for name, p in measurement_points.items()
        },
        'measurements_pixels': {k: float(v) for k, v in measurements.items()},
        'output_files': {
            'ensemble': ensemble_vis_path,
            'correction': correction_vis_path,
            'measurements': measurement_vis_path,
            'report': report_path
        }
    }

    json_path = os.path.join(output_dir, f'{image_name}_results.json')
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✓ All outputs saved to: {output_dir}")

    return results


def create_final_report(image, initial_landmarks, corrected_landmarks,
                        measurement_points, measurements, category):
    """
    Create a comprehensive final report showing the complete pipeline
    """
    h, w = image.shape[:2]

    # Create 2x2 grid
    grid_size = max(h, w) // 2
    report = np.ones((grid_size * 2 + 100, grid_size * 2 + 20, 3), dtype=np.uint8) * 240

    # Resize image to fit
    scale = min(grid_size / h, grid_size / w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized_image = cv2.resize(image, (new_w, new_h))

    # Panel 1: Original + Initial Landmarks
    panel1 = resized_image.copy()
    for lm in initial_landmarks:
        if lm is not None:
            scaled_pos = (int(lm[0] * scale), int(lm[1] * scale))
            cv2.circle(panel1, scaled_pos, 3, (0, 0, 255), -1)

    y_offset = (grid_size - new_h) // 2
    x_offset = (grid_size - new_w) // 2
    report[10+y_offset:10+y_offset+new_h, 10+x_offset:10+x_offset+new_w] = panel1
    cv2.putText(report, f"1. Initial: {len(initial_landmarks)} landmarks",
                (15, grid_size + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Panel 2: Edge Corrected
    panel2 = resized_image.copy()
    for lm in corrected_landmarks:
        if lm is not None:
            scaled_pos = (int(lm[0] * scale), int(lm[1] * scale))
            cv2.circle(panel2, scaled_pos, 3, (0, 255, 0), -1)

    report[10+y_offset:10+y_offset+new_h, grid_size+15+x_offset:grid_size+15+x_offset+new_w] = panel2
    cv2.putText(report, "2. Edge Corrected",
                (grid_size + 20, grid_size + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 128, 0), 2)

    # Panel 3: Key Measurement Points
    panel3 = resized_image.copy()
    colors = {
        'collar': (255, 0, 0),
        'shoulder': (0, 255, 0),
        'chest': (0, 165, 255),
        'hem': (255, 0, 255),
        'sleeve': (255, 255, 0)
    }

    # Draw measurement lines
    pairs = [
        ('shoulder_left', 'shoulder_right', 'shoulder_width'),
        ('chest_left', 'chest_right', 'chest_width'),
        ('hem_left', 'hem_right', 'hem_width')
    ]

    for left_name, right_name, meas_name in pairs:
        if left_name in measurement_points and right_name in measurement_points:
            left_pos = measurement_points[left_name].position
            right_pos = measurement_points[right_name].position
            scaled_left = (int(left_pos[0] * scale), int(left_pos[1] * scale))
            scaled_right = (int(right_pos[0] * scale), int(right_pos[1] * scale))
            cv2.line(panel3, scaled_left, scaled_right, (0, 255, 0), 2)

    for name, point in measurement_points.items():
        color = colors.get(point.type, (128, 128, 128))
        scaled_pos = (int(point.position[0] * scale), int(point.position[1] * scale))
        cv2.circle(panel3, scaled_pos, 6, color, -1)
        cv2.circle(panel3, scaled_pos, 8, (0, 0, 0), 2)

    report[grid_size+60+y_offset:grid_size+60+y_offset+new_h,
           10+x_offset:10+x_offset+new_w] = panel3
    cv2.putText(report, f"3. Key Points: {len(measurement_points)}",
                (15, grid_size * 2 + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Panel 4: Measurements Summary
    summary_panel = np.ones((grid_size, grid_size, 3), dtype=np.uint8) * 255

    y_pos = 40
    cv2.putText(summary_panel, f"FINAL MEASUREMENTS", (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    y_pos += 40
    cv2.putText(summary_panel, f"Category: {category}", (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    y_pos += 40
    cv2.putText(summary_panel, "Measurements (pixels):", (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    y_pos += 30
    for name, value in measurements.items():
        text = f"{name}: {value:.1f}"
        cv2.putText(summary_panel, text, (30, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 0), 1)
        y_pos += 25

    # Pipeline summary
    y_pos += 30
    cv2.putText(summary_panel, "Pipeline Stats:", (20, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    y_pos += 25
    cv2.putText(summary_panel, f"Initial: {len(initial_landmarks)} landmarks", (30, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y_pos += 20
    cv2.putText(summary_panel, f"Corrected: {len([l for l in corrected_landmarks if l])}",
                (30, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y_pos += 20
    cv2.putText(summary_panel, f"Final: {len(measurement_points)} key points", (30, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 0), 2)

    report[grid_size+60:grid_size*2+60, grid_size+15:grid_size*2+15] = summary_panel

    # Add title
    cv2.putText(report, "FOCUSED MEASUREMENT SYSTEM - COMPLETE PIPELINE",
                (report.shape[1]//2 - 400, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 128, 0), 2)

    return report


def main():
    """
    Run the complete measurement system on test images
    """
    output_base_dir = '/home/celso/projects/qa_dashboard/ai_withllm/FINAL_DELIVERABLES'
    os.makedirs(output_base_dir, exist_ok=True)

    print("\n" + "="*80)
    print("FOCUSED MEASUREMENT SYSTEM - COMPLETE RUN")
    print("="*80)
    print(f"Output directory: {output_base_dir}")

    # Test images
    test_images = [
        '/home/celso/projects/qa_dashboard/ai_withllm/shirt.jpg',
        '/home/celso/projects/qa_dashboard/ai_withllm/jeans.jpg'
    ]

    all_results = {}

    for image_path in test_images:
        if os.path.exists(image_path):
            results = run_complete_measurement_pipeline(image_path, output_base_dir)
            if results:
                all_results[Path(image_path).stem] = results
        else:
            print(f"Warning: Image not found: {image_path}")

    # Create master summary
    summary = {
        'run_timestamp': datetime.now().isoformat(),
        'system_version': '1.0.0',
        'images_processed': len(all_results),
        'results': all_results
    }

    summary_path = os.path.join(output_base_dir, 'complete_run_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*80)
    print("COMPLETE RUN FINISHED")
    print("="*80)
    print(f"\nAll deliverables saved to: {output_base_dir}")
    print("\nDeliverables include:")
    print("  1. Ensemble detection visualizations")
    print("  2. Edge correction visualizations")
    print("  3. Key measurement point visualizations")
    print("  4. Final comprehensive reports")
    print("  5. JSON data files with all measurements")
    print(f"\nMaster summary: {summary_path}")


if __name__ == '__main__':
    main()