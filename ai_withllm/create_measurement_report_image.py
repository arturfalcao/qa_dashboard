#!/usr/bin/env python3
"""
Create a professional measurement report image with no background garment
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
from rembg import remove, new_session
import logging
from datetime import datetime

# Add the module to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from hrnet_landmark_detector import FashionLandmarkDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_measurement_report(image_path: str, output_dir: str = "measurement_report"):
    """
    Create a professional measurement report image

    Args:
        image_path: Path to input image
        output_dir: Directory to save output files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize detector
    model_path = "models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"
    detector = FashionLandmarkDetector(model_path, device='cpu')

    # Load image
    logger.info(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Could not load image from {image_path}")
        return

    # Step 1: Remove background
    logger.info("Removing background...")
    session = new_session('u2net_cloth_seg')
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output_rgba = remove(image_rgb, session=session)
    output_bgra = cv2.cvtColor(output_rgba, cv2.COLOR_RGBA2BGRA)

    # Get actual dimensions after processing
    orig_height, orig_width = output_bgra.shape[:2]

    # Step 2: Detect landmarks
    logger.info("Detecting landmarks...")
    result = detector.detect_landmarks(image, confidence_threshold=0.3)
    labeled_landmarks = detector.get_landmark_labels(result)
    measurements = detector.calculate_measurements(result)

    # Calculate dynamic height based on content
    header_height = 120
    garment_margin = 50  # Top and bottom margin for garment

    # Since orig_height is quite large (9120), we need to fit it better
    # Calculate a reasonable report height
    report_height = orig_height + header_height + 200  # Header + margins

    # Create report canvas
    report_width = orig_width + 800  # Add space for info panels

    # Create white background
    report_canvas = np.ones((report_height, report_width, 3), dtype=np.uint8) * 255

    # Add subtle grid pattern for professional look
    for i in range(0, report_height, 50):
        cv2.line(report_canvas, (0, i), (report_width, i), (240, 240, 240), 1)
    for i in range(0, report_width, 50):
        cv2.line(report_canvas, (i, 0), (i, report_height), (240, 240, 240), 1)

    # Create header section
    header_height = 120
    cv2.rectangle(report_canvas, (0, 0), (report_width, header_height), (50, 50, 50), -1)

    # Add title
    title = "GARMENT MEASUREMENT REPORT"
    cv2.putText(report_canvas, title, (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2, cv2.LINE_AA)

    # Add subtitle with date and file info
    subtitle = f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | File: {os.path.basename(image_path)}"
    cv2.putText(report_canvas, subtitle, (30, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

    # Place garment image (with transparency handled)
    garment_x = 50
    garment_y = header_height + 50

    # Extract alpha channel and blend with white
    alpha = output_bgra[:, :, 3] / 255.0
    for c in range(3):
        report_canvas[garment_y:garment_y+orig_height, garment_x:garment_x+orig_width, c] = \
            (1 - alpha) * 255 + alpha * output_bgra[:, :, c]

    # Define colors for landmarks
    colors = {
        'collar': (255, 100, 100),
        'shoulder': (100, 255, 100),
        'chest': (255, 255, 100),
        'waist': (255, 100, 255),
        'hem': (100, 255, 255),
        'sleeve': (150, 255, 150),
        'armhole': (255, 150, 150),
        'neckline': (200, 200, 255),
        'default': (180, 180, 255)
    }

    # Draw landmarks with labels (no measurement lines)
    for label, coord in labeled_landmarks.items():
        # Determine color
        color = colors['default']
        for key in colors:
            if key in label.lower():
                color = colors[key]
                break

        # Adjust coordinates
        coord_adj = (coord[0] + garment_x, coord[1] + garment_y)

        # Draw landmark
        cv2.circle(report_canvas, coord_adj, 6, color, -1)
        cv2.circle(report_canvas, coord_adj, 8, (0, 0, 0), 1)

    # Create info panels on the right side
    panel_x = orig_width + 100
    panel_y = header_height + 50

    # Panel 1: Garment Information
    cv2.putText(report_canvas, "GARMENT INFORMATION", (panel_x, panel_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2, cv2.LINE_AA)

    cv2.line(report_canvas, (panel_x, panel_y + 10), (panel_x + 600, panel_y + 10), (100, 100, 100), 2)

    info_y = panel_y + 50
    info_items = [
        f"Type: {result['category'].upper()}",
        f"Total Landmarks: {result['num_detected']}",
        f"Key Points Identified: {len(labeled_landmarks)}",
        f"Image Dimensions: {orig_width} x {orig_height} px"
    ]

    for item in info_items:
        cv2.putText(report_canvas, item, (panel_x + 20, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (70, 70, 70), 1, cv2.LINE_AA)
        info_y += 30

    # Panel 2: Measurements
    info_y += 40
    cv2.putText(report_canvas, "MEASUREMENTS", (panel_x, info_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2, cv2.LINE_AA)
    cv2.line(report_canvas, (panel_x, info_y + 10), (panel_x + 600, info_y + 10), (100, 100, 100), 2)

    info_y += 50

    # Create measurement table
    if measurements:
        # Headers
        cv2.putText(report_canvas, "Measurement", (panel_x + 20, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)
        cv2.putText(report_canvas, "Pixels", (panel_x + 250, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)
        cv2.putText(report_canvas, "Est. cm*", (panel_x + 350, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)

        info_y += 5
        cv2.line(report_canvas, (panel_x + 20, info_y), (panel_x + 450, info_y), (150, 150, 150), 1)
        info_y += 25

        pixels_per_cm = 10  # Estimated, should be calibrated
        for name, value in measurements.items():
            # Format name
            display_name = name.replace('_', ' ').title()
            cv2.putText(report_canvas, display_name, (panel_x + 20, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)

            # Pixel value
            cv2.putText(report_canvas, f"{value:.1f}", (panel_x + 250, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)

            # Estimated cm
            cm_value = value / pixels_per_cm
            cv2.putText(report_canvas, f"{cm_value:.1f}", (panel_x + 350, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)

            info_y += 30

    # Panel 3: Key Landmark Points
    info_y += 40
    cv2.putText(report_canvas, "KEY LANDMARK POINTS", (panel_x, info_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2, cv2.LINE_AA)
    cv2.line(report_canvas, (panel_x, info_y + 10), (panel_x + 600, info_y + 10), (100, 100, 100), 2)

    info_y += 50

    # Group landmarks by type
    landmark_groups = {
        'Collar/Neckline': ['collar', 'neckline'],
        'Shoulders': ['shoulder'],
        'Armholes': ['armhole'],
        'Hem': ['hem'],
        'Chest/Waist': ['chest', 'waist']
    }

    for group_name, keywords in landmark_groups.items():
        group_landmarks = [(label, coord) for label, coord in labeled_landmarks.items()
                          if any(kw in label.lower() for kw in keywords)]

        if group_landmarks:
            cv2.putText(report_canvas, group_name + ":", (panel_x + 20, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)
            info_y += 30

            for label, coord in group_landmarks[:3]:  # Show first 3 of each type
                # Get color for this landmark
                color = colors['default']
                for key in colors:
                    if key in label.lower():
                        color = colors[key]
                        break

                # Draw color indicator
                cv2.circle(report_canvas, (panel_x + 40, info_y - 5), 4, color, -1)

                # Draw label
                display_label = label.replace('_', ' ').title()
                cv2.putText(report_canvas, display_label[:25], (panel_x + 55, info_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (70, 70, 70), 1, cv2.LINE_AA)

                # Draw coordinates
                cv2.putText(report_canvas, f"({coord[0]}, {coord[1]})", (panel_x + 300, info_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)
                info_y += 25

            info_y += 10

    # Add legend directly after content
    legend_y = info_y + 30
    cv2.putText(report_canvas, "LEGEND:", (panel_x, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)

    legend_x = panel_x + 20
    legend_y += 30

    legend_items = [
        ('Collar/Neckline', colors['collar']),
        ('Shoulders', colors['shoulder']),
        ('Armholes', colors['armhole']),
        ('Hem', colors['hem'])
    ]

    for label, color in legend_items:
        cv2.circle(report_canvas, (legend_x, legend_y - 5), 6, color, -1)
        cv2.putText(report_canvas, label, (legend_x + 15, legend_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (70, 70, 70), 1, cv2.LINE_AA)
        legend_x += 150

    # Add footer note right after legend
    footer_text = "*Estimated measurements. For accurate results, calibration with reference object required."
    cv2.putText(report_canvas, footer_text, (30, legend_y + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)

    # Save the report
    output_path = os.path.join(output_dir, "measurement_report.jpg")
    cv2.imwrite(output_path, report_canvas)
    logger.info(f"✓ Saved comprehensive report: {output_path}")

    # Also create a simplified version with just garment and key measurements
    simple_width = orig_width + 400
    simple_height = orig_height + 300
    simple_canvas = np.ones((simple_height, simple_width, 3), dtype=np.uint8) * 245

    # Header
    cv2.rectangle(simple_canvas, (0, 0), (simple_width, 80), (60, 60, 60), -1)
    cv2.putText(simple_canvas, f"GARMENT ANALYSIS - {result['category'].upper()}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

    # Place garment
    garment_offset_x = 30
    garment_offset_y = 100

    alpha = output_bgra[:, :, 3] / 255.0
    for c in range(3):
        simple_canvas[garment_offset_y:garment_offset_y+orig_height,
                     garment_offset_x:garment_offset_x+orig_width, c] = \
            (1 - alpha) * 245 + alpha * output_bgra[:, :, c]

    # Draw landmarks and measurements
    for label, coord in labeled_landmarks.items():
        color = colors['default']
        for key in colors:
            if key in label.lower():
                color = colors[key]
                break

        coord_adj = (coord[0] + garment_offset_x, coord[1] + garment_offset_y)
        cv2.circle(simple_canvas, coord_adj, 8, color, -1)
        cv2.circle(simple_canvas, coord_adj, 10, (0, 0, 0), 2)

        # Add compact label
        short_label = label.replace('_', ' ').replace('left ', 'L-').replace('right ', 'R-').replace('center ', 'C-')
        cv2.putText(simple_canvas, short_label, (coord_adj[0] + 12, coord_adj[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 50, 50), 1, cv2.LINE_AA)

    # Add measurement box on the right
    box_x = orig_width + 80
    box_y = 120
    cv2.rectangle(simple_canvas, (box_x, box_y), (box_x + 300, box_y + 200), (255, 255, 255), -1)
    cv2.rectangle(simple_canvas, (box_x, box_y), (box_x + 300, box_y + 200), (100, 100, 100), 2)

    cv2.putText(simple_canvas, "KEY MEASUREMENTS", (box_x + 10, box_y + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2, cv2.LINE_AA)

    meas_y = box_y + 60
    for name, value in list(measurements.items())[:5]:  # Show top 5 measurements
        display_name = name.replace('_', ' ').title()
        cv2.putText(simple_canvas, f"{display_name}: {value:.0f}px", (box_x + 20, meas_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 70), 1, cv2.LINE_AA)
        meas_y += 30

    output_path = os.path.join(output_dir, "measurement_summary.jpg")
    cv2.imwrite(output_path, simple_canvas)
    logger.info(f"✓ Saved summary report: {output_path}")

    # Create a clean annotated version (just garment with landmark dots, no lines)
    clean_canvas = np.ones((orig_height, orig_width, 4), dtype=np.uint8) * 255
    clean_canvas[:, :, 3] = 0  # Transparent

    # Copy the garment with transparency
    clean_canvas = output_bgra.copy()

    # Draw landmark points only (no measurement lines)
    for label, coord in labeled_landmarks.items():
        color = colors['default']
        for key in colors:
            if key in label.lower():
                color = (*color, 255)  # Add alpha
                break

        cv2.circle(clean_canvas, coord, 10, color, -1)
        cv2.circle(clean_canvas, coord, 12, (0, 0, 0, 255), 2)

    output_path = os.path.join(output_dir, "annotated_garment.png")
    cv2.imwrite(output_path, clean_canvas)
    logger.info(f"✓ Saved annotated garment: {output_path}")

    logger.info("\n✅ All report images generated successfully!")
    logger.info(f"📁 Output directory: {output_dir}")

    return output_dir


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create measurement report image")
    parser.add_argument("--image", default="shirt.jpg", help="Input image path")
    parser.add_argument("--output", default="measurement_report", help="Output directory")

    args = parser.parse_args()

    create_measurement_report(args.image, args.output)


if __name__ == "__main__":
    main()