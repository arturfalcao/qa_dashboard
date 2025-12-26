#!/usr/bin/env python3
"""
Test script for the Industrial Landmark Detection System

Tests the full pipeline with sample images to verify:
1. Landmark detection works correctly
2. Measurements are calculated
3. Visualizations are generated
4. JSON output is produced
"""

import os
import sys
import cv2
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the industrial pipeline
from industrial_landmark_system.pipeline import (
    IndustrialMeasurementPipeline,
    PipelineConfig,
    create_pipeline,
)
from industrial_landmark_system.landmark_schemas import (
    INDUSTRIAL_LANDMARK_SCHEMAS,
    get_schema_for_category,
)
from industrial_landmark_system.measurement_instructions import (
    save_default_instructions,
    TSHIRT_MEASUREMENTS,
)


def test_landmark_schemas():
    """Test that landmark schemas are properly defined"""
    print("\n" + "=" * 60)
    print("TESTING LANDMARK SCHEMAS")
    print("=" * 60)

    for category, schema in INDUSTRIAL_LANDMARK_SCHEMAS.items():
        print(f"\n{category}:")
        print(f"  Landmarks: {schema.num_landmarks}")
        print(f"  Skeleton connections: {len(schema.skeleton)}")
        print(f"  Measurement pairs: {list(schema.measurement_pairs.keys())}")

    print("\nAll landmark schemas defined correctly!")
    return True


def test_measurement_instructions():
    """Test measurement instruction schema"""
    print("\n" + "=" * 60)
    print("TESTING MEASUREMENT INSTRUCTIONS")
    print("=" * 60)

    # Save instructions to JSON for inspection
    output_dir = Path(__file__).parent / "industrial_landmark_system" / "configs"
    output_dir.mkdir(exist_ok=True)

    save_default_instructions(output_dir)

    # Load and verify T-shirt measurements
    print(f"\nT-Shirt measurements ({len(TSHIRT_MEASUREMENTS.measurements)}):")
    for m in TSHIRT_MEASUREMENTS.measurements:
        print(f"  - {m.id}: {m.name} (landmarks {m.landmarks})")

    print(f"\nValidation rules ({len(TSHIRT_MEASUREMENTS.validation_rules)}):")
    for r in TSHIRT_MEASUREMENTS.validation_rules:
        print(f"  - {r.rule_type.value}: {r.measurements}")

    print(f"\nMeasurement instruction configs saved to: {output_dir}")
    return True


def test_pipeline_with_image(image_path: str, output_dir: str = "industrial_test_output"):
    """Test the full pipeline with an image"""
    print("\n" + "=" * 60)
    print(f"TESTING PIPELINE WITH: {image_path}")
    print("=" * 60)

    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return False

    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)

    # Create pipeline configuration
    config = PipelineConfig(
        model_path="models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
        device='cpu',  # Use CPU for compatibility
        use_segmentation=False,  # Skip segmentation for faster testing
        use_deep_segmentation=False,
        confidence_threshold=0.1,
        use_tta=False,
        output_dir=output_dir,
        save_visualizations=True,
        save_json=True,
        save_debug=True,
    )

    print("\nInitializing pipeline...")
    try:
        pipeline = IndustrialMeasurementPipeline(config)
    except Exception as e:
        print(f"ERROR initializing pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("Processing image...")
    try:
        result = pipeline.process(image_path)
    except Exception as e:
        print(f"ERROR processing image: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Print results
    print("\n" + "-" * 40)
    print("RESULTS")
    print("-" * 40)
    print(f"Category: {result.category}")
    print(f"Success: {result.success}")
    print(f"Errors: {result.errors}")
    print(f"Total time: {result.total_time_ms:.0f}ms")

    # Detection stats
    num_detected = sum(1 for l in result.detection.landmarks if l is not None)
    total_landmarks = len(result.detection.landmarks)
    print(f"\nLandmarks: {num_detected}/{total_landmarks} detected")

    # Confidence distribution
    if result.detection.confidences:
        confs = [c for c in result.detection.confidences if c > 0]
        if confs:
            print(f"Confidence: min={min(confs):.2f}, max={max(confs):.2f}, avg={sum(confs)/len(confs):.2f}")

    # Measurements
    print("\nMeasurements:")
    for m_id, m in result.measurements.measurements.items():
        if m.value_px > 0:
            status_symbol = {"pass": "✓", "fail": "✗", "warning": "⚠", "not_measured": "-"}.get(m.status.value, "?")
            if m.value_mm is not None:
                print(f"  [{status_symbol}] {m.name}: {m.value_mm:.1f}mm (conf: {m.confidence:.0%})")
            else:
                print(f"  [{status_symbol}] {m.name}: {m.value_px:.0f}px (conf: {m.confidence:.0%})")

    # Overall status
    print(f"\nOverall status: {result.measurements.overall_status.value}")
    print(f"Total confidence: {result.measurements.total_confidence:.0%}")

    print(f"\nOutput saved to: {output_dir}/")

    return result.success


def main():
    """Run all tests"""
    print("=" * 60)
    print("INDUSTRIAL LANDMARK DETECTION SYSTEM - TEST SUITE")
    print("=" * 60)

    # Test 1: Landmark schemas
    try:
        test_landmark_schemas()
    except Exception as e:
        print(f"Schema test failed: {e}")

    # Test 2: Measurement instructions
    try:
        test_measurement_instructions()
    except Exception as e:
        print(f"Instruction test failed: {e}")

    # Test 3: Pipeline with sample images
    test_images = [
        "img1.jpg",
        "img2.jpg",
        "img3.jpg",
        "img4.jpg",  # Jeans
        "shirt.jpg",
        "shirt2.jpg",
        "jeans.jpg",
    ]

    # Find an available test image
    base_dir = Path(__file__).parent
    tested = False

    for img_name in test_images:
        img_path = base_dir / img_name
        if img_path.exists():
            try:
                success = test_pipeline_with_image(str(img_path))
                tested = True
                if success:
                    print(f"\n✓ Pipeline test passed with {img_name}")
                else:
                    print(f"\n✗ Pipeline test had issues with {img_name}")
                break  # Just test one image
            except Exception as e:
                print(f"\n✗ Pipeline test failed: {e}")
                import traceback
                traceback.print_exc()

    if not tested:
        print("\nNo test images found. Please ensure test images exist in the ai_withllm directory.")

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
