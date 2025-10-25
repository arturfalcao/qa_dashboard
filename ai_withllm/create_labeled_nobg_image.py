#!/usr/bin/env python3
"""
Create an image with background removed and meaningful landmark labels
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
from rembg import remove, new_session
import logging

# Add the module to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from hrnet_landmark_detector import FashionLandmarkDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_labeled_nobg_image(image_path: str, output_dir: str = "nobg_labeled_output"):
    """
    Create image with background removed and meaningful landmark labels

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

    # Convert BGR to RGB for rembg
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Remove background (returns RGBA)
    output_rgba = remove(image_rgb, session=session)

    # Convert RGBA to BGRA for OpenCV
    output_bgra = cv2.cvtColor(output_rgba, cv2.COLOR_RGBA2BGRA)

    logger.info("Background removed successfully")

    # Step 2: Detect landmarks on original image (better accuracy)
    logger.info("Detecting landmarks...")
    result = detector.detect_landmarks(image, confidence_threshold=0.3)
    logger.info(f"Detected {result['num_detected']} landmarks, category: {result['category']}")

    # Get labeled landmarks
    labeled_landmarks = detector.get_landmark_labels(result)
    logger.info(f"Identified {len(labeled_landmarks)} meaningful landmarks")

    # Step 3: Draw landmarks on transparent image
    # Create a copy for drawing
    labeled_nobg = output_bgra.copy()

    # Define colors for different landmark types (BGR format)
    colors = {
        'collar': (255, 100, 100),      # Light blue
        'shoulder': (100, 255, 100),    # Light green
        'chest': (255, 255, 100),       # Cyan
        'waist': (255, 100, 255),       # Magenta
        'hem': (100, 255, 255),         # Yellow
        'sleeve': (150, 255, 150),      # Light green
        'armpit': (255, 180, 100),      # Orange
        'armhole': (255, 150, 150),     # Light red
        'neckline': (200, 200, 255),    # Light pink
        'default': (180, 180, 255)      # Light blue default
    }

    # Draw landmarks with labels
    for label, coord in labeled_landmarks.items():
        # Determine color based on landmark type
        color = colors['default']
        for key in colors:
            if key in label.lower():
                color = colors[key]
                break

        # Draw landmark point with border
        cv2.circle(labeled_nobg, coord, 8, color, -1)
        cv2.circle(labeled_nobg, coord, 10, (0, 0, 0, 255), 2)

        # Add label with background for readability
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Position text to avoid overlap
        text_x = coord[0] + 15
        text_y = coord[1] + 5

        # Draw white background rectangle for text
        padding = 3
        cv2.rectangle(labeled_nobg,
                     (text_x - padding, text_y - text_height - padding),
                     (text_x + text_width + padding, text_y + padding),
                     (255, 255, 255, 255), -1)

        # Draw text
        cv2.putText(labeled_nobg, label, (text_x, text_y),
                   font, font_scale, (0, 0, 0, 255), thickness, cv2.LINE_AA)

    # Add title at the top
    title = f"Garment: {result['category']} | Landmarks: {len(labeled_landmarks)}"
    cv2.putText(labeled_nobg, title, (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0, 255), 2, cv2.LINE_AA)

    # Step 4: Save outputs
    # Save transparent version (PNG with alpha)
    output_path = os.path.join(output_dir, "nobg_with_landmarks.png")
    cv2.imwrite(output_path, labeled_nobg)
    logger.info(f"✓ Saved: {output_path}")

    # Also create version with white background for better visibility
    height, width = labeled_nobg.shape[:2]
    white_bg = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Extract alpha channel
    alpha = labeled_nobg[:, :, 3] / 255.0

    # Blend with white background
    for c in range(3):
        white_bg[:, :, c] = (1 - alpha) * 255 + alpha * labeled_nobg[:, :, c]

    # Draw landmarks on white background version
    white_bg_labeled = white_bg.copy()

    for label, coord in labeled_landmarks.items():
        # Determine color
        color = colors['default']
        for key in colors:
            if key in label.lower():
                color = colors[key][:3]  # Remove alpha for regular image
                break

        # Draw landmark point
        cv2.circle(white_bg_labeled, coord, 8, color, -1)
        cv2.circle(white_bg_labeled, coord, 10, (0, 0, 0), 2)

        # Add label
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        text_x = coord[0] + 15
        text_y = coord[1] + 5

        # Get text size for background
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        # Draw semi-transparent white background
        padding = 3
        overlay = white_bg_labeled.copy()
        cv2.rectangle(overlay,
                     (text_x - padding, text_y - text_height - padding),
                     (text_x + text_width + padding, text_y + padding),
                     (255, 255, 255), -1)
        cv2.addWeighted(overlay, 0.7, white_bg_labeled, 0.3, 0, white_bg_labeled)

        # Draw text
        cv2.putText(white_bg_labeled, label, (text_x, text_y),
                   font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

    # Add title
    cv2.putText(white_bg_labeled, title, (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 150, 0), 2, cv2.LINE_AA)

    output_path = os.path.join(output_dir, "white_bg_with_landmarks.jpg")
    cv2.imwrite(output_path, white_bg_labeled)
    logger.info(f"✓ Saved: {output_path}")

    # Save just the transparent image without landmarks for reference
    output_path = os.path.join(output_dir, "nobg_clean.png")
    cv2.imwrite(output_path, output_bgra)
    logger.info(f"✓ Saved: {output_path}")

    # Create a summary image showing key measurements
    measurement_img = white_bg.copy()
    measurements = detector.calculate_measurements(result)

    # Draw measurement lines
    for measurement_name, landmark_names in detector.MEASUREMENTS.items():
        if measurement_name in measurements and len(landmark_names) == 2:
            if landmark_names[0] in labeled_landmarks and landmark_names[1] in labeled_landmarks:
                p1 = labeled_landmarks[landmark_names[0]]
                p2 = labeled_landmarks[landmark_names[1]]

                # Draw measurement line
                cv2.line(measurement_img, p1, p2, (0, 200, 0), 3, cv2.LINE_AA)

                # Add measurement label
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2
                value = measurements[measurement_name]
                label = f"{measurement_name}: {value:.0f}px"

                # Background for text
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(measurement_img, (mid_x - 5, mid_y - h - 5),
                            (mid_x + w + 5, mid_y + 5), (255, 255, 255), -1)
                cv2.putText(measurement_img, label, (mid_x, mid_y),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 0), 2, cv2.LINE_AA)

                # Draw endpoint circles
                cv2.circle(measurement_img, p1, 10, (0, 0, 255), -1)
                cv2.circle(measurement_img, p2, 10, (0, 0, 255), -1)

    output_path = os.path.join(output_dir, "measurements_visual.jpg")
    cv2.imwrite(output_path, measurement_img)
    logger.info(f"✓ Saved: {output_path}")

    # Create summary report
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Garment Type: {result['category']}")
    logger.info(f"Total Landmarks Detected: {result['num_detected']}")
    logger.info(f"Meaningful Landmarks: {len(labeled_landmarks)}")
    logger.info("\nKey Measurement Points Found:")
    for label in sorted(labeled_landmarks.keys()):
        coord = labeled_landmarks[label]
        logger.info(f"  • {label:25s} at ({coord[0]:4d}, {coord[1]:4d})")

    if measurements:
        logger.info("\nMeasurements (in pixels):")
        for name, value in measurements.items():
            logger.info(f"  • {name:20s}: {value:8.1f} px")

    logger.info("\n✅ All outputs generated successfully!")
    logger.info(f"📁 Output directory: {output_dir}")

    return output_dir


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create labeled image with no background")
    parser.add_argument("--image", default="shirt.jpg", help="Input image path")
    parser.add_argument("--output", default="nobg_labeled_output", help="Output directory")

    args = parser.parse_args()

    create_labeled_nobg_image(args.image, args.output)


if __name__ == "__main__":
    main()