#!/usr/bin/env python3
"""
Horizontal Width Analyzer - Simple pixel counting approach

Strategy:
1. Remove background (white/clean background removal)
2. For each horizontal line (Y coordinate), count non-background pixels
3. Analyze width profile along the garment height
4. Extract measurements from width distribution

This is MUCH simpler than seam detection and works for all garment types!
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
import matplotlib.pyplot as plt
from scipy import signal, ndimage
from rembg import remove
from PIL import Image


class HorizontalWidthAnalyzer:
    """Analyzes garment by counting pixels horizontally at each height"""

    def __init__(self, background_color: str = 'auto', tolerance: int = 10, use_rembg: bool = True):
        """
        Initialize analyzer

        Args:
            background_color: 'white', 'gray', 'auto', or 'rembg' (AI-powered)
            tolerance: Color tolerance for background removal (0-255)
            use_rembg: Use rembg (U2-Net) for robust background removal
        """
        self.background_color = 'rembg' if use_rembg else background_color
        self.tolerance = tolerance

    def remove_background(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Remove background and create binary mask

        Returns:
            mask: Binary mask where 255 = garment, 0 = background
            cleaned: Image with background removed (transparent)
        """
        if self.background_color == 'rembg':
            # Use AI-powered background removal (ROBUST!)
            print("  Using rembg (U2-Net) for background removal...")

            # Convert to PIL Image
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)

            # Remove background
            output_pil = remove(pil_image)
            output_rgba = np.array(output_pil)

            # Extract alpha channel as mask
            if output_rgba.shape[2] == 4:
                alpha = output_rgba[:, :, 3]
                mask = (alpha > 127).astype(np.uint8) * 255
            else:
                raise ValueError("rembg did not return RGBA image")

            # Create cleaned image
            cleaned = cv2.cvtColor(output_rgba[:, :, :3], cv2.COLOR_RGB2BGR)
            cleaned = cv2.bitwise_and(cleaned, cleaned, mask=mask)

            print(f"  ✓ Garment pixels: {np.sum(mask > 0):,}")
            print(f"  ✓ Coverage: {np.sum(mask > 0) / mask.size * 100:.1f}%")

            return mask, cleaned

        elif self.background_color == 'white':
            # Remove white/light background
            if len(image.shape) == 3:
                # Check if pixels are white (all channels > threshold)
                threshold = 255 - self.tolerance
                mask = ~np.all(image > threshold, axis=2).astype(np.uint8) * 255
            else:
                threshold = 255 - self.tolerance
                mask = (image < threshold).astype(np.uint8) * 255

        elif self.background_color == 'gray':
            # Remove gray background
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            # Assume background is near 127-200 range
            mask = ((gray < 100) | (gray > 220)).astype(np.uint8) * 255

        else:  # auto
            # Automatic background detection using edge-based approach
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Use Otsu's thresholding
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Fill holes
        mask = ndimage.binary_fill_holes(mask).astype(np.uint8) * 255

        # Get largest contour (main garment)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            clean_mask = np.zeros_like(mask)
            cv2.drawContours(clean_mask, [largest], -1, 255, -1)
            mask = clean_mask

        # Create cleaned image
        if len(image.shape) == 3:
            cleaned = cv2.bitwise_and(image, image, mask=mask)
        else:
            cleaned = cv2.bitwise_and(image, image, mask=mask)

        return mask, cleaned

    def count_horizontal_pixels(self, mask: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Count non-background pixels for each horizontal line

        Returns:
            Dict with:
                - width_profile: Array of widths (one per Y coordinate)
                - left_edge: X coordinate of left edge for each Y
                - right_edge: X coordinate of right edge for each Y
                - y_coords: Y coordinates (height values)
        """
        h, w = mask.shape[:2]

        width_profile = np.zeros(h, dtype=np.int32)
        left_edge = np.full(h, -1, dtype=np.int32)
        right_edge = np.full(h, -1, dtype=np.int32)

        for y in range(h):
            row = mask[y, :]
            nonzero = np.where(row > 0)[0]

            if len(nonzero) > 0:
                width_profile[y] = len(nonzero)
                left_edge[y] = nonzero[0]
                right_edge[y] = nonzero[-1]

        return {
            'width_profile': width_profile,
            'left_edge': left_edge,
            'right_edge': right_edge,
            'y_coords': np.arange(h)
        }

    def analyze_width_profile(self, profile_data: Dict) -> Dict:
        """
        Analyze the width profile to extract key measurements

        Strategy:
        1. Find garment bounds (top, bottom)
        2. Detect shoulder region (widest point in upper section)
        3. Detect chest region (widest stable section)
        4. Detect waist/hem region (lower section)
        """
        width_profile = profile_data['width_profile']
        left_edge = profile_data['left_edge']
        right_edge = profile_data['right_edge']
        y_coords = profile_data['y_coords']

        # Find garment vertical bounds
        garment_rows = np.where(width_profile > 0)[0]
        if len(garment_rows) == 0:
            return {'error': 'No garment detected'}

        top_y = garment_rows[0]
        bottom_y = garment_rows[-1]
        garment_height = bottom_y - top_y

        # Extract garment region only
        garment_width = width_profile[top_y:bottom_y+1]
        garment_y = y_coords[top_y:bottom_y+1]
        garment_left = left_edge[top_y:bottom_y+1]
        garment_right = right_edge[top_y:bottom_y+1]

        # Smooth the width profile to reduce noise
        if len(garment_width) > 20:
            window = min(21, len(garment_width) // 10 * 2 + 1)  # Odd window
            garment_width_smooth = signal.savgol_filter(garment_width, window, 3)
        else:
            garment_width_smooth = garment_width

        # Define regions (as percentages of height)
        upper_region = slice(0, int(len(garment_width) * 0.30))  # Top 30%
        middle_region = slice(int(len(garment_width) * 0.30), int(len(garment_width) * 0.70))  # Middle 40%
        lower_region = slice(int(len(garment_width) * 0.70), len(garment_width))  # Bottom 30%

        measurements = {}

        # 1. SHOULDER/TOP WIDTH - Maximum width in upper 30%
        if len(garment_width[upper_region]) > 0:
            shoulder_idx = np.argmax(garment_width_smooth[upper_region])
            shoulder_y_rel = upper_region.start + shoulder_idx
            shoulder_y_abs = top_y + shoulder_y_rel

            measurements['shoulder'] = {
                'width_pixels': int(garment_width[shoulder_y_rel]),
                'y_position': int(shoulder_y_abs),
                'left_x': int(garment_left[shoulder_y_rel]),
                'right_x': int(garment_right[shoulder_y_rel]),
                'region': 'upper_30%'
            }

        # 2. CHEST/BODY WIDTH - Maximum width in middle region or average of stable section
        if len(garment_width[middle_region]) > 0:
            # Find most stable (consistent) width in middle section
            chest_idx = np.argmax(garment_width_smooth[middle_region])
            chest_y_rel = middle_region.start + chest_idx
            chest_y_abs = top_y + chest_y_rel

            measurements['chest'] = {
                'width_pixels': int(garment_width[chest_y_rel]),
                'y_position': int(chest_y_abs),
                'left_x': int(garment_left[chest_y_rel]),
                'right_x': int(garment_right[chest_y_rel]),
                'region': 'middle_40%'
            }

        # 3. HEM/BOTTOM WIDTH - Width at bottom
        if len(garment_width[lower_region]) > 0:
            # Average of bottom 10% to get stable hem measurement
            hem_section = garment_width[int(len(garment_width) * 0.90):]
            hem_idx = len(garment_width) - len(hem_section) + len(hem_section) // 2
            hem_y_abs = top_y + hem_idx

            measurements['hem'] = {
                'width_pixels': int(np.mean(hem_section)),
                'y_position': int(hem_y_abs),
                'left_x': int(garment_left[hem_idx]),
                'right_x': int(garment_right[hem_idx]),
                'region': 'bottom_30%'
            }

        # 4. MAXIMUM WIDTH (absolute widest point)
        max_idx = np.argmax(garment_width)
        max_y_abs = top_y + max_idx

        measurements['max_width'] = {
            'width_pixels': int(garment_width[max_idx]),
            'y_position': int(max_y_abs),
            'left_x': int(garment_left[max_idx]),
            'right_x': int(garment_right[max_idx]),
            'region': 'absolute_max'
        }

        # 5. GARMENT DIMENSIONS
        measurements['dimensions'] = {
            'total_height': int(garment_height),
            'top_y': int(top_y),
            'bottom_y': int(bottom_y),
            'min_width': int(np.min(garment_width[garment_width > 0])),
            'max_width': int(np.max(garment_width)),
            'avg_width': int(np.mean(garment_width[garment_width > 0]))
        }

        # 6. COLLAR POINTS - Two outermost points at the UPPERMOST position
        # Strategy: Start from top, find first row with significant width, get leftmost/rightmost
        collar_found = False
        for i in range(min(50, len(garment_width))):  # Check first 50 rows max
            if garment_width[i] > 100:  # Found a row with significant width (collar area)
                if garment_left[i] >= 0 and garment_right[i] >= 0:
                    left_collar_point = (garment_left[i], top_y + i)
                    right_collar_point = (garment_right[i], top_y + i)
                    collar_width = right_collar_point[0] - left_collar_point[0]

                    measurements['collar'] = {
                        'width_pixels': int(collar_width),
                        'left_point': (int(left_collar_point[0]), int(left_collar_point[1])),
                        'right_point': (int(right_collar_point[0]), int(right_collar_point[1])),
                        'region': 'uppermost_with_width'
                    }
                    collar_found = True
                    break

        # 7. CUFF POINTS - Outermost points of sleeves (left and right extremities)
        # Strategy: Find the most extreme left and right points in the middle region (sleeves area)
        middle_region_start = int(len(garment_width) * 0.30)  # After shoulder
        middle_region_end = int(len(garment_width) * 0.70)    # Before hem

        if middle_region_end > middle_region_start:
            # Find leftmost point in middle region (left cuff)
            left_cuff_x = float('inf')
            left_cuff_point = None

            # Find rightmost point in middle region (right cuff)
            right_cuff_x = -1
            right_cuff_point = None

            for i in range(middle_region_start, min(middle_region_end, len(garment_left))):
                if garment_left[i] >= 0 and garment_left[i] < left_cuff_x:
                    left_cuff_x = garment_left[i]
                    left_cuff_point = (garment_left[i], top_y + i)

                if garment_right[i] >= 0 and garment_right[i] > right_cuff_x:
                    right_cuff_x = garment_right[i]
                    right_cuff_point = (garment_right[i], top_y + i)

            if left_cuff_point and right_cuff_point:
                # Measure cuff widths at their respective heights
                # For left cuff, measure width at that Y position
                left_cuff_idx = left_cuff_point[1] - top_y
                if 0 <= left_cuff_idx < len(garment_width):
                    left_cuff_width = garment_width[left_cuff_idx]

                    measurements['left_cuff'] = {
                        'position': (int(left_cuff_point[0]), int(left_cuff_point[1])),
                        'width_at_position': int(left_cuff_width),
                        'region': 'middle_leftmost'
                    }

                # For right cuff, measure width at that Y position
                right_cuff_idx = right_cuff_point[1] - top_y
                if 0 <= right_cuff_idx < len(garment_width):
                    right_cuff_width = garment_width[right_cuff_idx]

                    measurements['right_cuff'] = {
                        'position': (int(right_cuff_point[0]), int(right_cuff_point[1])),
                        'width_at_position': int(right_cuff_width),
                        'region': 'middle_rightmost'
                    }

        # Store profile for visualization
        measurements['_profile_data'] = {
            'width_profile': garment_width.tolist(),
            'width_profile_smooth': garment_width_smooth.tolist(),
            'y_coords': garment_y.tolist(),
            'left_edge': garment_left.tolist(),
            'right_edge': garment_right.tolist()
        }

        return measurements

    def analyze_garment(self, image_path: str, output_dir: str = "width_analysis") -> Dict:
        """
        Complete analysis pipeline
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        print(f"Analyzing {image_path}...")
        print(f"Image size: {image.shape[1]}x{image.shape[0]} pixels")

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(image_path).stem

        # Step 1: Remove background
        print("1. Removing background...")
        mask, cleaned = self.remove_background(image)

        # Step 2: Count horizontal pixels
        print("2. Counting horizontal pixels...")
        profile_data = self.count_horizontal_pixels(mask)

        # Step 3: Analyze width profile
        print("3. Analyzing width profile...")
        measurements = self.analyze_width_profile(profile_data)

        if 'error' in measurements:
            print(f"ERROR: {measurements['error']}")
            return measurements

        # Step 4: Visualize
        print("4. Creating visualizations...")
        self._visualize_analysis(image, mask, profile_data, measurements, output_dir, base_name)

        # Step 5: Save data
        print("5. Saving measurements...")
        self._save_measurements(measurements, output_dir, base_name)

        # Print summary
        self._print_summary(measurements)

        return measurements

    def _visualize_analysis(self, image: np.ndarray, mask: np.ndarray,
                           profile_data: Dict, measurements: Dict,
                           output_dir: Path, base_name: str):
        """Create comprehensive visualization"""

        h, w = image.shape[:2]

        # Create figure with multiple panels
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Panel 1: Original image
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ax1.set_title('Original Image', fontsize=14, fontweight='bold')
        ax1.axis('off')

        # Panel 2: Mask
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.imshow(mask, cmap='gray')
        ax2.set_title('Background Removed (Mask)', fontsize=14, fontweight='bold')
        ax2.axis('off')

        # Panel 3: Annotated measurements
        ax3 = fig.add_subplot(gs[0, 2])
        annotated = image.copy()

        colors = {
            'shoulder': (0, 255, 0),    # Green
            'chest': (255, 0, 0),       # Blue (BGR)
            'hem': (0, 165, 255),       # Orange
            'collar': (255, 255, 0),    # Cyan
            'left_cuff': (255, 0, 255), # Magenta
            'right_cuff': (255, 0, 255), # Magenta
            'max_width': (128, 128, 128)  # Gray
        }

        for key, color in colors.items():
            if key in measurements and key != 'max_width':
                m = measurements[key]

                # Handle collar differently (uses point coordinates instead of y_position)
                if key == 'collar':
                    left_point = m['left_point']
                    right_point = m['right_point']

                    # Draw line between collar points
                    cv2.line(annotated, left_point, right_point, color, 3)

                    # Draw circles at collar endpoints
                    cv2.circle(annotated, left_point, 10, color, -1)
                    cv2.circle(annotated, right_point, 10, color, -1)

                    # Add label at midpoint
                    mid_x = (left_point[0] + right_point[0]) // 2
                    mid_y = (left_point[1] + right_point[1]) // 2
                    label = f"COLLAR: {m['width_pixels']}px"
                    cv2.putText(annotated, label, (mid_x - 100, mid_y - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                # Handle cuffs (point markers)
                elif key in ['left_cuff', 'right_cuff']:
                    position = m['position']

                    # Draw large circle at cuff position
                    cv2.circle(annotated, position, 15, color, -1)
                    cv2.circle(annotated, position, 18, (0, 0, 0), 2)

                    # Add label
                    label = f"{key.upper().replace('_', ' ')}"
                    offset_x = -150 if key == 'left_cuff' else 20
                    cv2.putText(annotated, label, (position[0] + offset_x, position[1] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                else:
                    y = m['y_position']
                    left_x = m['left_x']
                    right_x = m['right_x']

                    # Draw horizontal line
                    cv2.line(annotated, (left_x, y), (right_x, y), color, 3)

                    # Draw circles at endpoints
                    cv2.circle(annotated, (left_x, y), 8, color, -1)
                    cv2.circle(annotated, (right_x, y), 8, color, -1)

                    # Add label
                    label = f"{key.upper()}: {m['width_pixels']}px"
                    cv2.putText(annotated, label, (left_x + 20, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        ax3.imshow(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        ax3.set_title('Detected Measurements', fontsize=14, fontweight='bold')
        ax3.axis('off')

        # Panel 4: Width profile graph
        ax4 = fig.add_subplot(gs[1, :])

        prof_data = measurements['_profile_data']
        y_coords = np.array(prof_data['y_coords'])
        width_profile = np.array(prof_data['width_profile'])
        width_smooth = np.array(prof_data['width_profile_smooth'])

        ax4.plot(y_coords, width_profile, 'b-', alpha=0.3, linewidth=1, label='Raw width')
        ax4.plot(y_coords, width_smooth, 'b-', linewidth=2, label='Smoothed width')

        # Mark measurement points
        if 'shoulder' in measurements:
            y = measurements['shoulder']['y_position']
            w = measurements['shoulder']['width_pixels']
            ax4.axhline(y=w, color='green', linestyle='--', alpha=0.5)
            ax4.plot(y, w, 'go', markersize=12, label='Shoulder')

        if 'chest' in measurements:
            y = measurements['chest']['y_position']
            w = measurements['chest']['width_pixels']
            ax4.axhline(y=w, color='red', linestyle='--', alpha=0.5)
            ax4.plot(y, w, 'ro', markersize=12, label='Chest')

        if 'hem' in measurements:
            y = measurements['hem']['y_position']
            w = measurements['hem']['width_pixels']
            ax4.axhline(y=w, color='orange', linestyle='--', alpha=0.5)
            ax4.plot(y, w, 'o', color='orange', markersize=12, label='Hem')

        ax4.set_xlabel('Y Position (pixels)', fontsize=12)
        ax4.set_ylabel('Width (pixels)', fontsize=12)
        ax4.set_title('Horizontal Width Profile', fontsize=14, fontweight='bold')
        ax4.legend(loc='best')
        ax4.grid(True, alpha=0.3)

        # Panel 5: Edge visualization
        ax5 = fig.add_subplot(gs[2, :])

        left_edge = np.array(prof_data['left_edge'])
        right_edge = np.array(prof_data['right_edge'])

        # Only plot where garment exists
        valid = width_profile > 0

        ax5.plot(y_coords[valid], left_edge[valid], 'b-', linewidth=2, label='Left edge')
        ax5.plot(y_coords[valid], right_edge[valid], 'r-', linewidth=2, label='Right edge')
        ax5.fill_betweenx(y_coords[valid], left_edge[valid], right_edge[valid],
                         alpha=0.2, color='gray', label='Garment area')

        ax5.set_xlabel('Y Position (pixels)', fontsize=12)
        ax5.set_ylabel('X Position (pixels)', fontsize=12)
        ax5.set_title('Left and Right Edges', fontsize=14, fontweight='bold')
        ax5.legend(loc='best')
        ax5.grid(True, alpha=0.3)
        ax5.invert_yaxis()  # Flip to match image orientation

        # Main title
        fig.suptitle(f'Horizontal Width Analysis - {base_name.upper()}',
                    fontsize=18, fontweight='bold')

        # Save
        analysis_path = output_dir / f"{base_name}_width_analysis.png"
        plt.savefig(analysis_path, dpi=150, bbox_inches='tight')
        print(f"Saved analysis to {analysis_path}")
        plt.close()

        # Save annotated image separately
        annotated_path = output_dir / f"{base_name}_measurements.jpg"
        cv2.imwrite(str(annotated_path), annotated)
        print(f"Saved annotated image to {annotated_path}")

    def _save_measurements(self, measurements: Dict, output_dir: Path, base_name: str):
        """Save measurements to JSON"""

        # Remove internal profile data from JSON output
        output_data = {k: v for k, v in measurements.items() if not k.startswith('_')}

        json_path = output_dir / f"{base_name}_measurements.json"
        with open(json_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"Saved measurements to {json_path}")

    def _print_summary(self, measurements: Dict):
        """Print measurement summary"""

        print("\n" + "="*60)
        print("MEASUREMENT SUMMARY")
        print("="*60)

        dims = measurements['dimensions']
        print(f"\nGarment Dimensions:")
        print(f"  Height: {dims['total_height']} pixels")
        print(f"  Min width: {dims['min_width']} pixels")
        print(f"  Max width: {dims['max_width']} pixels")
        print(f"  Avg width: {dims['avg_width']} pixels")

        print(f"\nKey Measurements:")

        if 'shoulder' in measurements:
            m = measurements['shoulder']
            print(f"  SHOULDER (upper 30%):")
            print(f"    Width: {m['width_pixels']} pixels")
            print(f"    Y position: {m['y_position']}")
            print(f"    Span: {m['left_x']} → {m['right_x']}")

        if 'chest' in measurements:
            m = measurements['chest']
            print(f"  CHEST (middle 40%):")
            print(f"    Width: {m['width_pixels']} pixels")
            print(f"    Y position: {m['y_position']}")
            print(f"    Span: {m['left_x']} → {m['right_x']}")

        if 'hem' in measurements:
            m = measurements['hem']
            print(f"  HEM (bottom 30%):")
            print(f"    Width: {m['width_pixels']} pixels")
            print(f"    Y position: {m['y_position']}")
            print(f"    Span: {m['left_x']} → {m['right_x']}")

        if 'collar' in measurements:
            m = measurements['collar']
            print(f"  COLLAR (uppermost outermost points):")
            print(f"    Width: {m['width_pixels']} pixels")
            print(f"    Left point: {m['left_point']}")
            print(f"    Right point: {m['right_point']}")

        if 'left_cuff' in measurements:
            m = measurements['left_cuff']
            print(f"  LEFT CUFF (leftmost point in middle region):")
            print(f"    Position: {m['position']}")
            print(f"    Width at position: {m['width_at_position']} pixels")

        if 'right_cuff' in measurements:
            m = measurements['right_cuff']
            print(f"  RIGHT CUFF (rightmost point in middle region):")
            print(f"    Position: {m['position']}")
            print(f"    Width at position: {m['width_at_position']} pixels")

        print("="*60 + "\n")


def main():
    """Test horizontal width analyzer"""
    import argparse

    parser = argparse.ArgumentParser(description='Horizontal Width Analyzer')
    parser.add_argument('image', help='Input garment image')
    parser.add_argument('--output-dir', default='width_analysis', help='Output directory')
    parser.add_argument('--bg-color', default='rembg',
                       choices=['white', 'gray', 'auto', 'rembg'],
                       help='Background removal method (rembg=AI-powered, recommended)')
    parser.add_argument('--tolerance', type=int, default=10,
                       help='Background removal tolerance (0-255)')
    parser.add_argument('--no-rembg', action='store_true',
                       help='Disable rembg and use simple thresholding')

    args = parser.parse_args()

    print("="*60)
    print("HORIZONTAL WIDTH ANALYZER")
    print("="*60)
    print()

    # Initialize analyzer
    use_rembg = (args.bg_color == 'rembg') and (not args.no_rembg)
    analyzer = HorizontalWidthAnalyzer(
        background_color=args.bg_color if not use_rembg else 'auto',
        tolerance=args.tolerance,
        use_rembg=use_rembg
    )

    # Run analysis
    measurements = analyzer.analyze_garment(args.image, args.output_dir)

    if 'error' not in measurements:
        print("\n✓ Analysis complete!")


if __name__ == '__main__':
    main()
