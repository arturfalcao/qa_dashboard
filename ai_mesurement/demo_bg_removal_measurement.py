#!/usr/bin/env python3
"""
Demo: Background Removal + Measurement Integration
Simple demonstration without strict calibration requirements
"""

import cv2
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_background_removal_measurement(image_path: str, output_dir: str = "demo_results"):
    """
    Demonstrate background removal integrated with measurements
    """
    from background_removal import BackgroundRemover

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("BACKGROUND REMOVAL + MEASUREMENT DEMO")
    logger.info("=" * 70)

    # Step 1: Load original image
    logger.info("\n[Step 1] Loading original image...")
    original = cv2.imread(image_path)
    if original is None:
        raise ValueError(f"Could not load image: {image_path}")
    logger.info(f"  ✓ Loaded: {image_path} ({original.shape[1]}x{original.shape[0]})")

    # Step 2: Remove background
    logger.info("\n[Step 2] Removing background with U2-Net...")
    remover = BackgroundRemover(model_name="u2net_cloth_seg", use_alpha_matting=True)

    # Get clean image with light gray background
    clean_image = remover.remove_background(
        image_path,
        background_color=(245, 245, 245),
        output_path=str(output_path / "01_bg_removed.png")
    )
    logger.info(f"  ✓ Background removed")

    # Get binary mask
    mask = remover.get_mask(image_path)
    cv2.imwrite(str(output_path / "02_mask.png"), mask)
    logger.info(f"  ✓ Mask extracted")

    # Calculate coverage
    coverage = (np.count_nonzero(mask) / mask.size) * 100
    logger.info(f"  ✓ Garment coverage: {coverage:.1f}%")

    # Step 3: Create comparison visualization
    logger.info("\n[Step 3] Creating comparison visualization...")

    # Resize for display
    h, w = original.shape[:2]
    max_h = 800
    if h > max_h:
        scale = max_h / h
        display_w = int(w * scale)
        display_h = max_h
    else:
        display_w, display_h = w, h

    orig_display = cv2.resize(original, (display_w, display_h))
    clean_display = cv2.resize(cv2.cvtColor(clean_image, cv2.COLOR_RGB2BGR), (display_w, display_h))
    mask_display = cv2.resize(mask, (display_w, display_h))
    mask_color = cv2.cvtColor(mask_display, cv2.COLOR_GRAY2BGR)

    # Create overlay
    overlay = orig_display.copy()
    overlay[mask_display > 0] = [0, 255, 0]  # Green overlay on detected garment
    overlay = cv2.addWeighted(orig_display, 0.6, overlay, 0.4, 0)

    # Stack images
    row1 = np.hstack([orig_display, clean_display])
    row2 = np.hstack([mask_color, overlay])
    comparison = np.vstack([row1, row2])

    # Add labels
    cv2.putText(comparison, "ORIGINAL", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(comparison, "BACKGROUND REMOVED", (display_w + 10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(comparison, "MASK", (10, display_h + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(comparison, "DETECTED GARMENT", (display_w + 10, display_h + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imwrite(str(output_path / "03_comparison.png"), comparison)
    logger.info(f"  ✓ Comparison saved")

    # Step 4: Extract basic measurements
    logger.info("\n[Step 4] Extracting basic measurements from mask...")

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        logger.warning("  ⚠ No contours found")
        return

    main_contour = max(contours, key=cv2.contourArea)

    # Get bounding box
    x, y, w, h = cv2.boundingRect(main_contour)

    # Calculate measurements (in pixels - would need calibration for mm)
    measurements = {
        "Width (px)": w,
        "Height (px)": h,
        "Area (px²)": cv2.contourArea(main_contour),
        "Perimeter (px)": cv2.arcLength(main_contour, True),
        "Aspect Ratio": h / w if w > 0 else 0
    }

    logger.info("  ✓ Measurements extracted:")
    for name, value in measurements.items():
        if "Ratio" in name:
            logger.info(f"    - {name}: {value:.2f}")
        else:
            logger.info(f"    - {name}: {value:.0f}")

    # Step 5: Create annotated visualization
    logger.info("\n[Step 5] Creating annotated visualization...")

    annotated = cv2.cvtColor(clean_image, cv2.COLOR_RGB2BGR).copy()

    # Draw contour
    cv2.drawContours(annotated, [main_contour], -1, (0, 255, 0), 3)

    # Draw bounding box
    cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Find extrema points
    points = main_contour[:, 0, :]
    leftmost = tuple(points[np.argmin(points[:, 0])])
    rightmost = tuple(points[np.argmax(points[:, 0])])
    topmost = tuple(points[np.argmin(points[:, 1])])
    bottommost = tuple(points[np.argmax(points[:, 1])])

    # Draw extrema points
    for pt, color, label in [
        (leftmost, (0, 0, 255), "L"),
        (rightmost, (255, 0, 0), "R"),
        (topmost, (0, 255, 0), "T"),
        (bottommost, (255, 255, 0), "B")
    ]:
        cv2.circle(annotated, pt, 10, color, -1)
        cv2.putText(annotated, label, (pt[0] + 15, pt[1]),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # Draw measurement lines
    cv2.line(annotated, leftmost, rightmost, (255, 0, 255), 2)
    cv2.line(annotated, topmost, bottommost, (0, 255, 255), 2)

    # Add measurements text
    y_offset = 30
    cv2.putText(annotated, "MEASUREMENTS:", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    y_offset += 30

    for name, value in measurements.items():
        if "Ratio" in name:
            text = f"{name}: {value:.2f}"
        else:
            text = f"{name}: {value:.0f}"
        cv2.putText(annotated, text, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25

    cv2.imwrite(str(output_path / "04_annotated.png"), annotated)
    logger.info(f"  ✓ Annotated image saved")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DEMO COMPLETE! ✅")
    logger.info("=" * 70)
    logger.info(f"\nResults saved to: {output_dir}/")
    logger.info("  • 01_bg_removed.png  - Clean image with uniform background")
    logger.info("  • 02_mask.png        - Binary segmentation mask")
    logger.info("  • 03_comparison.png  - Side-by-side comparison")
    logger.info("  • 04_annotated.png   - Measurements visualization")
    logger.info("\n💡 For calibrated measurements in mm, use the full system with:")
    logger.info("   venv/bin/python enhanced_measurement_system.py [image] --calibration [file] --bg-removal")
    logger.info("")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Background Removal + Measurement Demo")
    parser.add_argument("image", help="Path to garment image")
    parser.add_argument("--output", default="demo_results", help="Output directory")

    args = parser.parse_args()

    try:
        demo_background_removal_measurement(args.image, args.output)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
