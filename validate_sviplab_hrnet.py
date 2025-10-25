#!/usr/bin/env python3
"""
Comprehensive validation script for SVIP-Lab HRNet Fashion Landmark Detection
"""

import sys
import os
import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add project path to sys.path
sys.path.insert(0, '/home/celso/projects/qa_dashboard/ai_withllm')

from sviplab_hrnet_integration import SVIPLabFashionDetector


def validate_detection(image_path: str, detector: SVIPLabFashionDetector, expected_category: str = None) -> Dict:
    """
    Validate detection on a single image

    Args:
        image_path: Path to test image
        detector: SVIP-Lab detector instance
        expected_category: Expected garment category (optional)

    Returns:
        Validation results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Validating: {image_path}")
    print(f"{'='*60}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        return {"error": f"Could not load image: {image_path}"}

    print(f"Image shape: {image.shape}")

    # Detect landmarks
    result = detector.detect_landmarks(image)

    # Analyze results
    validation = {
        "image": image_path,
        "category_detected": result['category'],
        "expected_category": expected_category,
        "num_landmarks": result['num_detected'],
        "total_possible": 294,
        "detection_rate": result['num_detected'] / 294 * 100,
        "measurements": detector.extract_measurements(result),
        "category_correct": result['category'] == expected_category if expected_category else "N/A"
    }

    # Analyze confidence scores
    confidences = [c for c in result['confidences'] if c > 0]
    if confidences:
        validation['confidence_stats'] = {
            "mean": np.mean(confidences),
            "std": np.std(confidences),
            "min": np.min(confidences),
            "max": np.max(confidences),
            "median": np.median(confidences)
        }

    # Check landmark distribution by category
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

    landmark_distribution = {}
    for cat, (start, end) in category_ranges.items():
        detected_in_range = sum(1 for i in range(start, min(end, len(result['confidences'])))
                               if result['confidences'][i] > 0)
        expected_in_range = end - start
        landmark_distribution[cat] = {
            "detected": detected_in_range,
            "expected": expected_in_range,
            "rate": detected_in_range / expected_in_range * 100 if expected_in_range > 0 else 0
        }

    validation['landmark_distribution'] = landmark_distribution

    # Print results
    print(f"Category detected: {validation['category_detected']}")
    if expected_category:
        print(f"Expected category: {expected_category}")
        print(f"Category match: {validation['category_correct']}")

    print(f"Landmarks detected: {validation['num_landmarks']}/{validation['total_possible']} ({validation['detection_rate']:.1f}%)")

    if validation.get('confidence_stats'):
        stats = validation['confidence_stats']
        print(f"Confidence stats:")
        print(f"  Mean: {stats['mean']:.3f} ± {stats['std']:.3f}")
        print(f"  Range: [{stats['min']:.3f}, {stats['max']:.3f}]")
        print(f"  Median: {stats['median']:.3f}")

    if validation['measurements']:
        print(f"Measurements (pixels):")
        for name, value in validation['measurements'].items():
            print(f"  {name}: {value:.1f}")
    else:
        print("No measurements extracted")

    # Show top categories by detection rate
    print("\nTop categories by landmark detection rate:")
    top_cats = sorted(landmark_distribution.items(),
                     key=lambda x: x[1]['rate'], reverse=True)[:3]
    for cat, info in top_cats:
        print(f"  {cat}: {info['detected']}/{info['expected']} ({info['rate']:.1f}%)")

    return validation


def create_comparison_visualization(image_path: str, detector: SVIPLabFashionDetector,
                                  output_path: str = None) -> None:
    """
    Create a side-by-side visualization comparing original and detected landmarks
    """
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    # Detect landmarks
    result = detector.detect_landmarks(image)

    # Create visualization
    vis_image = detector.visualize_landmarks(image, result, show_confidence=True, show_labels=False)

    # Create side-by-side comparison
    comparison = np.hstack([image, vis_image])

    # Add title
    h, w = comparison.shape[:2]
    title_bg = np.ones((60, w, 3), dtype=np.uint8) * 255
    cv2.putText(title_bg, f"Original vs Detected ({result['category']}: {result['num_detected']} landmarks)",
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    final = np.vstack([title_bg, comparison])

    if output_path:
        cv2.imwrite(output_path, final)
        print(f"Saved visualization to {output_path}")

    return final


def test_different_thresholds(image_path: str, detector: SVIPLabFashionDetector) -> Dict:
    """
    Test detection with different confidence thresholds
    """
    print(f"\nTesting different confidence thresholds on {image_path}:")
    print("-" * 40)

    image = cv2.imread(image_path)
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    results = {}

    for threshold in thresholds:
        result = detector.detect_landmarks(image, confidence_threshold=threshold)
        results[threshold] = {
            "num_detected": result['num_detected'],
            "category": result['category']
        }
        print(f"Threshold {threshold:.1f}: {result['num_detected']} landmarks, category: {result['category']}")

    return results


def main():
    """Main validation function"""
    print("SVIP-Lab HRNet Fashion Landmark Detection Validation")
    print("=" * 60)

    # Initialize detector
    model_path = "/home/celso/projects/qa_dashboard/ai_withllm/models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"

    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        print("Please download the model first.")
        return

    print("Initializing detector...")
    detector = SVIPLabFashionDetector(model_path=model_path, device='cpu')
    print("Detector initialized successfully!")

    # Test images with expected categories
    test_cases = [
        ("/home/celso/projects/qa_dashboard/ai_withllm/shirt.jpg", "short_sleeved_shirt"),  # Actual: vest (misclassified)
        ("/home/celso/projects/qa_dashboard/ai_withllm/jeans.jpg", "trousers"),             # Actual: skirt (misclassified)
    ]

    validation_results = []

    for image_path, expected_category in test_cases:
        if os.path.exists(image_path):
            # Validate detection
            result = validate_detection(image_path, detector, expected_category)
            validation_results.append(result)

            # Create visualization
            output_name = f"validation_{Path(image_path).stem}_comparison.jpg"
            create_comparison_visualization(image_path, detector, output_name)

            # Test different thresholds
            threshold_results = test_different_thresholds(image_path, detector)
            result['threshold_analysis'] = threshold_results
        else:
            print(f"Warning: Test image not found: {image_path}")

    # Summary report
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    total_tests = len(validation_results)
    category_correct = sum(1 for r in validation_results if r.get('category_correct') == True)
    avg_detection_rate = np.mean([r['detection_rate'] for r in validation_results if 'detection_rate' in r])

    print(f"Total tests: {total_tests}")
    print(f"Category accuracy: {category_correct}/{total_tests} ({category_correct/total_tests*100:.1f}%)")
    print(f"Average landmark detection rate: {avg_detection_rate:.1f}%")

    # Identified issues
    print("\n" + "-" * 40)
    print("IDENTIFIED ISSUES:")
    print("-" * 40)

    issues = []
    for result in validation_results:
        if result.get('category_correct') == False:
            issues.append(f"- {result['image']}: Detected as '{result['category_detected']}' instead of '{result['expected_category']}'")
        if result.get('detection_rate', 100) < 60:
            issues.append(f"- {result['image']}: Low detection rate ({result['detection_rate']:.1f}%)")
        if not result.get('measurements'):
            issues.append(f"- {result['image']}: No measurements extracted")

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("No major issues identified")

    # Recommendations
    print("\n" + "-" * 40)
    print("RECOMMENDATIONS:")
    print("-" * 40)
    print("1. The model appears to struggle with category classification")
    print("2. Consider implementing a separate classifier for garment type")
    print("3. Measurement extraction needs improvement for non-top garments")
    print("4. May need category-specific confidence thresholds")

    # Save full report
    report_path = "sviplab_validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(validation_results, f, indent=2, default=str)
    print(f"\nFull validation report saved to: {report_path}")


if __name__ == "__main__":
    main()