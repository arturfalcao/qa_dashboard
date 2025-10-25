#!/usr/bin/env python3
"""
Seam Detection System for Garment Measurement

This system detects INTERNAL seams (construction lines) in addition to external edges.
Critical for accurate measurements like shoulder width, sleeve length, and distinguishing
front/back lengths.

Key insight: Garment construction creates visual seams that can be detected through:
1. Texture changes (stitching)
2. Shadow lines (depth changes)
3. Subtle color variations
4. Edge detection on INTERNAL features
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import json
from scipy import ndimage
from skimage import feature, morphology
import matplotlib.pyplot as plt


class SeamDetectionSystem:
    """
    Detects both external edges (outline) and internal seams (construction lines)
    """

    def __init__(self, debug: bool = True):
        self.debug = debug

    def extract_garment_mask(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract clean garment mask"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Threshold to get garment
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # Clean up
        kernel = np.ones((5, 5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Fill holes and get largest contour
        binary = ndimage.binary_fill_holes(binary).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            clean_mask = np.zeros_like(binary)
            cv2.drawContours(clean_mask, [largest], -1, 255, -1)
            return clean_mask, largest

        return binary, np.array([])

    def detect_external_edges(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Detect EXTERNAL edges (garment outline)
        """
        # Get contour edges only
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        external_edges = np.zeros_like(mask)
        if contours:
            cv2.drawContours(external_edges, contours, -1, 255, 2)

        return external_edges

    def detect_internal_seams(self, image: np.ndarray, mask: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Detect INTERNAL seams (stitching, construction lines)

        Key techniques:
        1. Canny on masked image (detect internal texture changes)
        2. Laplacian for subtle transitions
        3. Texture gradient analysis
        4. Shadow detection
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply mask to focus only on garment interior
        masked_img = cv2.bitwise_and(gray, gray, mask=mask)

        # Technique 1: Canny edge detection on internal features
        # Use lower thresholds to catch subtle seams
        canny_internal = cv2.Canny(masked_img, 20, 60)

        # Remove external edges
        external = self.detect_external_edges(image, mask)
        kernel_erode = np.ones((5, 5), np.uint8)
        external_dilated = cv2.dilate(external, kernel_erode, iterations=2)
        canny_internal = cv2.bitwise_and(canny_internal, cv2.bitwise_not(external_dilated))

        # Technique 2: Laplacian (detects subtle transitions)
        laplacian = cv2.Laplacian(masked_img, cv2.CV_64F, ksize=3)
        laplacian = np.abs(laplacian)
        laplacian = (laplacian / laplacian.max() * 255).astype(np.uint8) if laplacian.max() > 0 else laplacian.astype(np.uint8)
        laplacian = cv2.threshold(laplacian, 20, 255, cv2.THRESH_BINARY)[1]
        laplacian = cv2.bitwise_and(laplacian, cv2.bitwise_not(external_dilated))

        # Technique 3: Sobel gradient magnitude
        sobelx = cv2.Sobel(masked_img, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(masked_img, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(sobelx**2 + sobely**2)
        gradient_mag = (gradient_mag / gradient_mag.max() * 255).astype(np.uint8) if gradient_mag.max() > 0 else gradient_mag.astype(np.uint8)
        gradient_mag = cv2.threshold(gradient_mag, 30, 255, cv2.THRESH_BINARY)[1]
        gradient_mag = cv2.bitwise_and(gradient_mag, cv2.bitwise_not(external_dilated))

        # Technique 4: Shadow detection (helps find depth changes at seams)
        if len(image.shape) == 3:
            # Convert to LAB and analyze L channel
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]

            # Detect dark lines (shadows from stitching)
            shadows = cv2.adaptiveThreshold(
                l_channel, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )
            shadows = cv2.bitwise_and(shadows, mask)
            shadows = cv2.bitwise_and(shadows, cv2.bitwise_not(external_dilated))
        else:
            shadows = np.zeros_like(mask)

        return {
            'canny_internal': canny_internal,
            'laplacian': laplacian,
            'gradient': gradient_mag,
            'shadows': shadows
        }

    def combine_seam_detections(self, seam_maps: Dict[str, np.ndarray],
                               mask: np.ndarray) -> np.ndarray:
        """
        Combine different seam detection methods into a unified seam map
        """
        # Weight different detection methods
        combined = (
            seam_maps['canny_internal'].astype(np.float32) * 0.35 +
            seam_maps['laplacian'].astype(np.float32) * 0.25 +
            seam_maps['gradient'].astype(np.float32) * 0.25 +
            seam_maps['shadows'].astype(np.float32) * 0.15
        )

        # Normalize
        combined = (combined / combined.max() * 255).astype(np.uint8) if combined.max() > 0 else combined.astype(np.uint8)

        # Apply morphological operations to connect broken seam lines
        kernel_line = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_line)

        # Thin to single-pixel lines
        combined_binary = (combined > 30).astype(np.uint8) * 255
        combined_thin = morphology.skeletonize(combined_binary > 0).astype(np.uint8) * 255

        return combined_thin

    def detect_seam_orientation(self, seam_map: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Classify seams by orientation (vertical, horizontal, diagonal)

        This is CRITICAL for identifying:
        - Vertical seams = side seams, center seams
        - Horizontal seams = shoulder seams, waistbands
        - Diagonal seams = raglan sleeves, princess seams
        """
        # Get seam points
        seam_points = np.column_stack(np.where(seam_map > 0))

        if len(seam_points) == 0:
            empty = np.zeros_like(seam_map)
            return {
                'vertical_seams': empty,
                'horizontal_seams': empty,
                'diagonal_seams': empty
            }

        # Calculate local orientation using Sobel
        gray_seam = seam_map.astype(np.float32)
        sobelx = cv2.Sobel(gray_seam, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_seam, cv2.CV_64F, 0, 1, ksize=3)

        # Calculate orientation angle
        orientation = np.arctan2(sobely, sobelx)

        # Classify by angle
        # Vertical: angle close to ±90° (±π/2)
        # Horizontal: angle close to 0° or 180° (0 or π)
        vertical_mask = np.abs(np.abs(orientation) - np.pi/2) < np.pi/6  # Within 30° of vertical
        horizontal_mask = np.abs(orientation) < np.pi/6  # Within 30° of horizontal
        horizontal_mask |= np.abs(np.abs(orientation) - np.pi) < np.pi/6
        diagonal_mask = ~(vertical_mask | horizontal_mask)

        # Apply masks to seam map
        vertical_seams = np.where(vertical_mask, seam_map, 0).astype(np.uint8)
        horizontal_seams = np.where(horizontal_mask, seam_map, 0).astype(np.uint8)
        diagonal_seams = np.where(diagonal_mask, seam_map, 0).astype(np.uint8)

        return {
            'vertical_seams': vertical_seams,
            'horizontal_seams': horizontal_seams,
            'diagonal_seams': diagonal_seams
        }

    def find_shoulder_seam(self, image: np.ndarray, mask: np.ndarray,
                          horizontal_seams: np.ndarray, contour: np.ndarray) -> Optional[Dict]:
        """
        Find shoulder seam - where the garment "starts to fall"

        Strategy:
        1. Look for horizontal seams in upper region
        2. Identify where sleeve angle changes (slope transition)
        3. Find intersection of horizontal seam with sleeve outline
        """
        h, w = image.shape[:2]

        # Focus on upper 40% of garment
        upper_region = np.zeros_like(horizontal_seams)
        upper_region[0:int(h * 0.4), :] = 1
        shoulder_candidates = cv2.bitwise_and(horizontal_seams, horizontal_seams, mask=upper_region.astype(np.uint8))

        if np.sum(shoulder_candidates) == 0:
            return None

        # Find horizontal seam points in upper region
        seam_points = np.column_stack(np.where(shoulder_candidates > 0))

        # Group by y-coordinate (should form horizontal lines)
        from collections import defaultdict
        y_groups = defaultdict(list)
        for y, x in seam_points:
            y_groups[y].append(x)

        # Find the most prominent horizontal seam
        best_seam = None
        max_length = 0
        for y, x_coords in y_groups.items():
            if len(x_coords) > max_length:
                max_length = len(x_coords)
                best_seam = (y, x_coords)

        if best_seam is None:
            return None

        y_seam, x_coords = best_seam
        left_shoulder = (min(x_coords), y_seam)
        right_shoulder = (max(x_coords), y_seam)

        return {
            'seam_line_y': y_seam,
            'left_shoulder': left_shoulder,
            'right_shoulder': right_shoulder,
            'seam_length': max(x_coords) - min(x_coords),
            'confidence': min(1.0, max_length / (w * 0.5))  # Confidence based on seam continuity
        }

    def find_side_seams(self, vertical_seams: np.ndarray, mask: np.ndarray) -> Dict:
        """
        Find side seams for accurate front/back length measurement

        Strategy:
        1. Look for strong vertical lines on left and right sides
        2. These are typically side seams running from armpit to hem
        """
        h, w = mask.shape[:2]

        # Split into left and right halves
        left_half = vertical_seams.copy()
        left_half[:, w//2:] = 0

        right_half = vertical_seams.copy()
        right_half[:, :w//2] = 0

        # Find vertical line clusters
        from collections import defaultdict

        def find_strongest_vertical_line(seam_region):
            """Find the strongest continuous vertical line"""
            x_groups = defaultdict(list)
            points = np.column_stack(np.where(seam_region > 0))

            for y, x in points:
                x_groups[x].append(y)

            # Find longest vertical line
            best_line = None
            max_length = 0
            for x, y_coords in x_groups.items():
                if len(y_coords) > max_length:
                    max_length = len(y_coords)
                    best_line = (x, y_coords)

            return best_line

        left_seam = find_strongest_vertical_line(left_half)
        right_seam = find_strongest_vertical_line(right_half)

        result = {}

        if left_seam:
            x_left, y_coords_left = left_seam
            result['left_seam'] = {
                'x': x_left,
                'y_range': (min(y_coords_left), max(y_coords_left)),
                'length': max(y_coords_left) - min(y_coords_left)
            }

        if right_seam:
            x_right, y_coords_right = right_seam
            result['right_seam'] = {
                'x': x_right,
                'y_range': (min(y_coords_right), max(y_coords_right)),
                'length': max(y_coords_right) - min(y_coords_right)
            }

        return result

    def detect_sleeve_attachment(self, image: np.ndarray, mask: np.ndarray,
                                shoulder_seam: Optional[Dict],
                                contour: np.ndarray) -> Dict:
        """
        Detect where sleeves attach to body (armhole seam)

        This is where the sleeve "starts to fall" from the shoulder
        """
        h, w = image.shape[:2]

        result = {}

        if shoulder_seam is None:
            # Fallback: use curvature analysis on contour
            return self._detect_sleeve_by_curvature(contour, mask.shape)

        # Use shoulder seam as reference
        y_shoulder = shoulder_seam['seam_line_y']
        left_shoulder = shoulder_seam['left_shoulder']
        right_shoulder = shoulder_seam['right_shoulder']

        # The sleeve attachment point is where the shoulder seam meets the outline
        # and the slope changes from ~0 (horizontal shoulder) to high (vertical sleeve)

        result['left_sleeve_start'] = left_shoulder
        result['right_sleeve_start'] = right_shoulder
        result['method'] = 'shoulder_seam'

        return result

    def _detect_sleeve_by_curvature(self, contour: np.ndarray, image_shape: Tuple) -> Dict:
        """Fallback method using curvature to find sleeve attachment points"""
        if len(contour) == 0:
            return {}

        h, w = image_shape[:2]
        points = contour.reshape(-1, 2)

        # Find points in shoulder region (upper third, outer sides)
        shoulder_region_points = []
        for i, (x, y) in enumerate(points):
            if y < h * 0.35:  # Upper portion
                if x < w * 0.4 or x > w * 0.6:  # Sides
                    shoulder_region_points.append((i, x, y))

        if len(shoulder_region_points) < 10:
            return {}

        # Calculate curvature
        indices = [p[0] for p in shoulder_region_points]
        # Find high curvature points (where slope changes dramatically)

        # Simple approach: find leftmost and rightmost points in shoulder region
        left_point = min(shoulder_region_points, key=lambda p: p[1])
        right_point = max(shoulder_region_points, key=lambda p: p[1])

        return {
            'left_sleeve_start': (left_point[1], left_point[2]),
            'right_sleeve_start': (right_point[1], right_point[2]),
            'method': 'curvature_fallback'
        }

    def generate_full_seam_analysis(self, image_path: str, output_dir: str = "seam_analysis") -> Dict:
        """
        Complete seam detection and analysis pipeline
        """
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        print(f"Analyzing garment seams for {image_path}...")

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(image_path).stem

        # Step 1: Extract garment mask
        print("1. Extracting garment mask...")
        mask, contour = self.extract_garment_mask(image)

        # Step 2: Detect external edges
        print("2. Detecting external edges (outline)...")
        external_edges = self.detect_external_edges(image, mask)

        # Step 3: Detect internal seams
        print("3. Detecting internal seams (construction lines)...")
        seam_maps = self.detect_internal_seams(image, mask)
        combined_seams = self.combine_seam_detections(seam_maps, mask)

        # Step 4: Classify seams by orientation
        print("4. Classifying seam orientations...")
        oriented_seams = self.detect_seam_orientation(combined_seams)

        # Step 5: Find key anatomical seams
        print("5. Finding anatomical landmarks from seams...")
        shoulder_seam = self.find_shoulder_seam(
            image, mask,
            oriented_seams['horizontal_seams'],
            contour
        )

        side_seams = self.find_side_seams(oriented_seams['vertical_seams'], mask)

        sleeve_attachments = self.detect_sleeve_attachment(
            image, mask, shoulder_seam, contour
        )

        # Compile results
        results = {
            'external_edges': external_edges,
            'internal_seams': combined_seams,
            'seam_components': seam_maps,
            'oriented_seams': oriented_seams,
            'shoulder_seam': shoulder_seam,
            'side_seams': side_seams,
            'sleeve_attachments': sleeve_attachments,
            'mask': mask,
            'contour': contour
        }

        # Visualize
        self._visualize_seam_analysis(image, results, output_dir, base_name)

        # Save data
        self._save_seam_data(results, output_dir, base_name)

        return results

    def _visualize_seam_analysis(self, image: np.ndarray, results: Dict,
                                output_dir: Path, base_name: str):
        """Create comprehensive visualization"""

        # Create multi-panel visualization
        fig, axes = plt.subplots(2, 4, figsize=(24, 12))

        # Panel 1: Original image
        axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('Original Image', fontsize=14, fontweight='bold')
        axes[0, 0].axis('off')

        # Panel 2: External edges
        axes[0, 1].imshow(results['external_edges'], cmap='gray')
        axes[0, 1].set_title('External Edges (Outline)', fontsize=14, fontweight='bold')
        axes[0, 1].axis('off')

        # Panel 3: Internal seams
        axes[0, 2].imshow(results['internal_seams'], cmap='hot')
        axes[0, 2].set_title('Internal Seams (Construction)', fontsize=14, fontweight='bold')
        axes[0, 2].axis('off')

        # Panel 4: Combined (external + internal)
        combined_viz = cv2.addWeighted(
            results['external_edges'], 0.5,
            results['internal_seams'], 0.5, 0
        )
        axes[0, 3].imshow(combined_viz, cmap='hot')
        axes[0, 3].set_title('External + Internal Combined', fontsize=14, fontweight='bold')
        axes[0, 3].axis('off')

        # Panel 5: Horizontal seams
        axes[1, 0].imshow(results['oriented_seams']['horizontal_seams'], cmap='hot')
        axes[1, 0].set_title('Horizontal Seams\n(Shoulder, Yoke)', fontsize=14, fontweight='bold')
        axes[1, 0].axis('off')

        # Panel 6: Vertical seams
        axes[1, 1].imshow(results['oriented_seams']['vertical_seams'], cmap='hot')
        axes[1, 1].set_title('Vertical Seams\n(Side, Center)', fontsize=14, fontweight='bold')
        axes[1, 1].axis('off')

        # Panel 7: Diagonal seams
        axes[1, 2].imshow(results['oriented_seams']['diagonal_seams'], cmap='hot')
        axes[1, 2].set_title('Diagonal Seams\n(Raglan, Princess)', fontsize=14, fontweight='bold')
        axes[1, 2].axis('off')

        # Panel 8: Annotated landmarks from seams
        annotated = image.copy()

        # Draw shoulder seam if found
        if results['shoulder_seam']:
            ss = results['shoulder_seam']
            cv2.line(annotated,
                    ss['left_shoulder'], ss['right_shoulder'],
                    (0, 255, 0), 3)
            cv2.circle(annotated, ss['left_shoulder'], 10, (0, 255, 0), -1)
            cv2.circle(annotated, ss['right_shoulder'], 10, (0, 255, 0), -1)
            cv2.putText(annotated, "SHOULDER SEAM",
                       (ss['left_shoulder'][0], ss['left_shoulder'][1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Draw side seams if found
        for side_name, side_data in results['side_seams'].items():
            x = side_data['x']
            y_min, y_max = side_data['y_range']
            cv2.line(annotated, (x, y_min), (x, y_max), (255, 0, 255), 2)
            cv2.putText(annotated, f"{side_name.upper()}",
                       (x + 10, (y_min + y_max) // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

        # Draw sleeve attachments
        if results['sleeve_attachments']:
            sa = results['sleeve_attachments']
            if 'left_sleeve_start' in sa:
                cv2.circle(annotated, sa['left_sleeve_start'], 12, (0, 165, 255), -1)
                cv2.putText(annotated, "SLEEVE START",
                           (sa['left_sleeve_start'][0] - 100, sa['left_sleeve_start'][1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            if 'right_sleeve_start' in sa:
                cv2.circle(annotated, sa['right_sleeve_start'], 12, (0, 165, 255), -1)

        axes[1, 3].imshow(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        axes[1, 3].set_title('Detected Anatomical Seams', fontsize=14, fontweight='bold')
        axes[1, 3].axis('off')

        # Main title
        fig.suptitle(f'Seam Detection Analysis - {base_name.upper()}',
                    fontsize=18, fontweight='bold')

        # Save
        plt.tight_layout()
        analysis_path = output_dir / f"{base_name}_seam_analysis.png"
        plt.savefig(analysis_path, dpi=150, bbox_inches='tight')
        print(f"Saved analysis to {analysis_path}")

        # Also save the annotated image separately
        annotated_path = output_dir / f"{base_name}_seam_landmarks.jpg"
        cv2.imwrite(str(annotated_path), annotated)
        print(f"Saved annotated landmarks to {annotated_path}")

    def _save_seam_data(self, results: Dict, output_dir: Path, base_name: str):
        """Save seam detection data to JSON"""

        # Helper to convert numpy types to Python types
        def convert_to_serializable(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_to_serializable(item) for item in obj)
            return obj

        # Convert numpy arrays to serializable format
        data = {
            'shoulder_seam': convert_to_serializable(results['shoulder_seam']),
            'side_seams': convert_to_serializable(results['side_seams']),
            'sleeve_attachments': convert_to_serializable(results['sleeve_attachments'])
        }

        json_path = output_dir / f"{base_name}_seam_data.json"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved seam data to {json_path}")


def main():
    """Test seam detection system"""
    import argparse

    parser = argparse.ArgumentParser(description='Garment Seam Detection System')
    parser.add_argument('image', help='Input garment image')
    parser.add_argument('--output-dir', default='seam_analysis', help='Output directory')

    args = parser.parse_args()

    # Initialize system
    print("="*60)
    print("GARMENT SEAM DETECTION SYSTEM")
    print("="*60)

    detector = SeamDetectionSystem(debug=True)

    # Run analysis
    results = detector.generate_full_seam_analysis(args.image, args.output_dir)

    # Print summary
    print("\n" + "="*60)
    print("SEAM DETECTION SUMMARY")
    print("="*60)

    if results['shoulder_seam']:
        print(f"\n✓ SHOULDER SEAM DETECTED")
        print(f"  Location: Y={results['shoulder_seam']['seam_line_y']}")
        print(f"  Width: {results['shoulder_seam']['seam_length']} pixels")
        print(f"  Confidence: {results['shoulder_seam']['confidence']:.2f}")
    else:
        print("\n✗ Shoulder seam not detected")

    if results['side_seams']:
        print(f"\n✓ SIDE SEAMS DETECTED: {len(results['side_seams'])} seam(s)")
        for name, data in results['side_seams'].items():
            print(f"  {name}: X={data['x']}, Length={data['length']} pixels")
    else:
        print("\n✗ Side seams not detected")

    if results['sleeve_attachments']:
        print(f"\n✓ SLEEVE ATTACHMENTS DETECTED")
        print(f"  Method: {results['sleeve_attachments'].get('method', 'unknown')}")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
