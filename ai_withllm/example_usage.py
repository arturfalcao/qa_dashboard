#!/usr/bin/env python3
"""
Example usage script for the garment measurement system.
Demonstrates calibration and measurement workflow.
"""

import cv2
import numpy as np
from pathlib import Path
from garment_measure import Pipeline

def create_test_image_with_markers():
    """Create a synthetic test image with ArUco markers and a garment shape."""
    # Create image
    img_width, img_height = 1200, 1600
    image = np.ones((img_height, img_width, 3), dtype=np.uint8) * 20  # Dark gray background

    # Generate ArUco markers (using 6x6_50 for better stability)
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_50)
    marker_size = 100  # pixels

    # Place markers at corners
    markers_positions = [
        (50, 50),        # Top-left (ID 0)
        (img_width - 150, 50),   # Top-right (ID 1)
        (img_width - 150, img_height - 150),  # Bottom-right (ID 2)
        (50, img_height - 150)    # Bottom-left (ID 3)
    ]

    for marker_id, pos in enumerate(markers_positions):
        marker_img = cv2.aruco.drawMarker(aruco_dict, marker_id, marker_size)
        # Convert to 3-channel
        marker_3ch = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
        # Place marker on image
        y, x = pos
        image[y:y+marker_size, x:x+marker_size] = marker_3ch

    # Draw a synthetic T-shirt shape in the center
    # Simple polygon to represent a garment
    shirt_pts = np.array([
        [400, 400],   # Left shoulder
        [800, 400],   # Right shoulder
        [850, 450],   # Right sleeve start
        [950, 500],   # Right sleeve end
        [850, 550],   # Right sleeve bottom
        [820, 520],   # Right armpit
        [820, 900],   # Right hem
        [380, 900],   # Left hem
        [380, 520],   # Left armpit
        [350, 550],   # Left sleeve bottom
        [250, 500],   # Left sleeve end
        [350, 450],   # Left sleeve start
    ], np.int32)

    # Fill the shirt shape
    cv2.fillPoly(image, [shirt_pts], (180, 180, 180))  # Light gray garment

    # Add some texture/details
    cv2.line(image, (600, 400), (600, 900), (150, 150, 150), 2)  # Center seam
    cv2.circle(image, (600, 420), 20, (160, 160, 160), -1)  # Collar

    return image


def main():
    """Demonstrate the measurement pipeline."""
    print("Garment Measurement System - Example Usage")
    print("=" * 50)

    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Step 1: Create or load calibration image
    print("\n1. Creating test calibration image...")
    calibration_image = create_test_image_with_markers()
    cal_image_path = output_dir / "test_calibration.jpg"
    cv2.imwrite(str(cal_image_path), calibration_image)
    print(f"   Saved to {cal_image_path}")

    # Step 2: Initialize pipeline
    print("\n2. Initializing measurement pipeline...")
    pipeline = Pipeline(
        calibration_path="calibration.json",
        use_sam=False,  # Using OpenCV segmentation
        use_clip=False,  # Using heuristic classification
        output_dir=str(output_dir)
    )

    # Step 3: Perform calibration
    print("\n3. Performing calibration...")
    cal_result = pipeline.calibrate_from_image(str(cal_image_path))

    if cal_result['success']:
        print(f"   ✓ Calibration successful!")
        print(f"     - Pixels per mm: {cal_result['ppm']:.3f}")
        print(f"     - MM per pixel: {cal_result['pixel_to_mm']:.3f}")
        print(f"     - RMS error: {cal_result['rect_rms_mm']:.2f} mm")
    else:
        print(f"   ✗ Calibration failed: {cal_result['error']}")
        return

    # Step 4: Create test garment image (reuse the same for demo)
    print("\n4. Creating test garment image...")
    garment_image = create_test_image_with_markers()
    garment_image_path = output_dir / "test_garment.jpg"
    cv2.imwrite(str(garment_image_path), garment_image)
    print(f"   Saved to {garment_image_path}")

    # Step 5: Process garment image
    print("\n5. Processing garment image...")
    result = pipeline.process_image(
        str(garment_image_path),
        garment_type='tshirt',  # Override type for demo
        rectify=True
    )

    if result['ok']:
        print(f"   ✓ Processing successful!")
        print(f"     - Garment type: {result.get('garment_type')}")
        print(f"     - Landmarks found: {result.get('num_landmarks')}")
        print(f"     - Processing time: {result.get('processing_time_s', 0):.2f}s")

        # Display measurements
        print("\n   Measurements:")
        measurements = result.get('measurements_mm', {})
        uncertainties = result.get('uncertainty_ci95_mm', {})

        for name, value in measurements.items():
            uncertainty = uncertainties.get(name, 0)
            print(f"     • {name:20s}: {value:7.1f} ± {uncertainty:.1f} mm")

        # Validation results
        validation = result.get('validation', {})
        if validation:
            print(f"\n   Validation: {'✓ Passed' if validation.get('valid') else '✗ Failed'}")
            if validation.get('warnings'):
                for warning in validation['warnings']:
                    print(f"     ⚠ {warning}")

        # Output files
        print("\n   Output files:")
        if 'overlay_path' in result:
            print(f"     • Overlay: {result['overlay_path']}")
        if 'json_path' in result:
            print(f"     • Results: {result['json_path']}")

    else:
        print(f"   ✗ Processing failed: {result.get('error')}")

    print("\n" + "=" * 50)
    print("Example complete! Check the output directory for results.")


def test_with_real_image():
    """Test with a real garment image if available."""
    import sys

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Processing real image: {image_path}")

        # Initialize pipeline
        pipeline = Pipeline(
            calibration_path="calibration.json",
            output_dir="output"
        )

        # Process image
        result = pipeline.process_image(image_path)

        if result['ok']:
            print("Success! Measurements:")
            for name, value in result.get('measurements_mm', {}).items():
                print(f"  {name}: {value:.1f} mm")
        else:
            print(f"Failed: {result.get('error')}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # If image path provided, test with real image
        test_with_real_image()
    else:
        # Otherwise run demo with synthetic images
        main()