#!/usr/bin/env python3
"""
Edge-Based Keypoint Detector
Uses edge detection to create garment mask and find keypoints along garment outline
"""

import cv2
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import argparse
from scipy import ndimage
from scipy.signal import find_peaks
from sklearn.cluster import DBSCAN

@dataclass
class ContourKeypoint:
    """Represents a keypoint on the garment contour"""
    position: Tuple[int, int]
    type: str  # 'corner', 'extrema', 'inflection', 'regular'
    angle: float  # Angle at this point
    curvature: float  # Local curvature
    confidence: float
    index: int  # Index on contour

class EdgeBasedKeypointDetector:
    """Detects keypoints using edge-based garment masking"""

    def __init__(self):
        self.debug_mode = True
        self.garment_contour = None
        self.garment_mask = None
        self.keypoints = []

    def create_garment_mask(self, image: np.ndarray) -> np.ndarray:
        """Create a clean mask of the garment using edge detection"""

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 1)

        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)

        # Multi-scale edge detection
        edges1 = cv2.Canny(enhanced, 30, 100)
        edges2 = cv2.Canny(enhanced, 50, 150)
        edges3 = cv2.Canny(enhanced, 100, 200)

        # Combine edges
        edges = cv2.bitwise_or(edges1, cv2.bitwise_or(edges2, edges3))

        # Apply morphological operations to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(edges_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        # Find the largest contour (assumed to be the garment)
        if contours:
            # Filter out small contours
            min_area = image.shape[0] * image.shape[1] * 0.05  # At least 5% of image
            large_contours = [c for c in contours if cv2.contourArea(c) > min_area]

            if large_contours:
                # Get the largest contour
                garment_contour = max(large_contours, key=cv2.contourArea)

                # Create mask from contour
                mask = np.zeros(gray.shape, dtype=np.uint8)
                cv2.drawContours(mask, [garment_contour], -1, 255, -1)

                # Clean up mask
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

                # Store the main contour
                self.garment_contour = garment_contour

                return mask

        return np.zeros(gray.shape, dtype=np.uint8)

    def extract_garment_edges(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Extract clean edges of the garment only"""

        # Apply mask to image
        masked_image = cv2.bitwise_and(image, image, mask=mask)

        # Convert to grayscale
        gray = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)

        # Edge detection on masked image
        edges = cv2.Canny(gray, 50, 150)

        # Keep only edges within mask
        edges = cv2.bitwise_and(edges, edges, mask=mask)

        # Extract contour of mask as additional edge
        mask_contour = cv2.Canny(mask, 128, 255)

        # Combine edges
        combined_edges = cv2.bitwise_or(edges, mask_contour)

        return combined_edges

    def find_contour_keypoints(self, contour: np.ndarray) -> List[ContourKeypoint]:
        """Find keypoints along the garment contour"""

        keypoints = []

        # Reshape contour for easier processing
        points = contour.reshape(-1, 2)
        n_points = len(points)

        if n_points < 20:
            return keypoints

        # Calculate angles and curvatures along contour
        angles = []
        curvatures = []

        window = 10  # Window size for local analysis

        for i in range(n_points):
            # Get neighboring points
            prev_idx = (i - window) % n_points
            next_idx = (i + window) % n_points

            prev_point = points[prev_idx]
            curr_point = points[i]
            next_point = points[next_idx]

            # Calculate vectors
            v1 = prev_point - curr_point
            v2 = next_point - curr_point

            # Calculate angle
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                cos_angle = np.clip(cos_angle, -1, 1)
                angle = np.arccos(cos_angle)
            else:
                angle = np.pi

            angles.append(angle)

            # Calculate curvature (change in angle)
            if i > 0:
                curvature = abs(angles[i] - angles[i-1])
            else:
                curvature = 0
            curvatures.append(curvature)

        angles = np.array(angles)
        curvatures = np.array(curvatures)

        # Find corners (sharp angles)
        corner_threshold = np.pi * 0.6  # 108 degrees or less
        corner_indices = np.where(angles < corner_threshold)[0]

        for idx in corner_indices:
            keypoints.append(ContourKeypoint(
                position=(int(points[idx][0]), int(points[idx][1])),
                type='corner',
                angle=float(angles[idx]),
                curvature=float(curvatures[idx]),
                confidence=1.0 - (angles[idx] / np.pi),  # Sharper corners have higher confidence
                index=idx
            ))

        # Find high curvature points
        if len(curvatures) > 20:
            # Smooth curvatures
            smoothed_curvatures = ndimage.gaussian_filter1d(curvatures, sigma=3)

            # Find peaks in curvature
            peaks, properties = find_peaks(smoothed_curvatures,
                                         height=np.percentile(smoothed_curvatures, 75),
                                         distance=20)

            for peak_idx in peaks:
                if peak_idx not in corner_indices:  # Don't duplicate corners
                    keypoints.append(ContourKeypoint(
                        position=(int(points[peak_idx][0]), int(points[peak_idx][1])),
                        type='inflection',
                        angle=float(angles[peak_idx]),
                        curvature=float(curvatures[peak_idx]),
                        confidence=float(curvatures[peak_idx] / np.max(curvatures)),
                        index=peak_idx
                    ))

        # Find extrema points (topmost, bottommost, leftmost, rightmost)
        extrema_indices = [
            np.argmin(points[:, 1]),  # Topmost
            np.argmax(points[:, 1]),  # Bottommost
            np.argmin(points[:, 0]),  # Leftmost
            np.argmax(points[:, 0]),  # Rightmost
        ]

        for i, idx in enumerate(extrema_indices):
            extrema_names = ['top', 'bottom', 'left', 'right']
            keypoints.append(ContourKeypoint(
                position=(int(points[idx][0]), int(points[idx][1])),
                type=f'extrema_{extrema_names[i]}',
                angle=float(angles[idx]),
                curvature=float(curvatures[idx]),
                confidence=0.9,
                index=idx
            ))

        return keypoints

    def map_to_anatomical_points(self, keypoints: List[ContourKeypoint],
                                 image_shape: Tuple[int, int]) -> Dict[str, ContourKeypoint]:
        """Map contour keypoints to anatomical measurement points"""

        h, w = image_shape[:2]
        anatomical_points = {}

        # Separate keypoints by type and position
        corners = [kp for kp in keypoints if kp.type == 'corner']
        extrema = [kp for kp in keypoints if 'extrema' in kp.type]
        inflections = [kp for kp in keypoints if kp.type == 'inflection']

        # Find key anatomical points based on position and type

        # Get extrema points
        top_point = next((kp for kp in extrema if 'top' in kp.type), None)
        bottom_point = next((kp for kp in extrema if 'bottom' in kp.type), None)
        left_point = next((kp for kp in extrema if 'left' in kp.type), None)
        right_point = next((kp for kp in extrema if 'right' in kp.type), None)

        # Determine garment type based on aspect ratio
        if top_point and bottom_point and left_point and right_point:
            width = abs(right_point.position[0] - left_point.position[0])
            height = abs(bottom_point.position[1] - top_point.position[1])
            aspect_ratio = width / height if height > 0 else 1

            is_top = aspect_ratio > 0.8  # Tops are generally wider

            if is_top:
                # For tops, find shoulders, armpits, chest, hem

                # Shoulders: corners near the top-sides
                shoulder_candidates = [kp for kp in corners + inflections
                                      if kp.position[1] < h * 0.3]

                if shoulder_candidates:
                    # Left shoulder: leftmost among top candidates
                    left_shoulders = [kp for kp in shoulder_candidates
                                     if kp.position[0] < w * 0.5]
                    if left_shoulders:
                        anatomical_points['left_shoulder'] = min(left_shoulders,
                                                                key=lambda k: k.position[0])

                    # Right shoulder: rightmost among top candidates
                    right_shoulders = [kp for kp in shoulder_candidates
                                      if kp.position[0] > w * 0.5]
                    if right_shoulders:
                        anatomical_points['right_shoulder'] = max(right_shoulders,
                                                                 key=lambda k: k.position[0])

                # Armpits: inflection points below shoulders
                if 'left_shoulder' in anatomical_points:
                    shoulder_y = anatomical_points['left_shoulder'].position[1]
                    armpit_candidates = [kp for kp in corners + inflections
                                       if shoulder_y < kp.position[1] < shoulder_y + h * 0.2
                                       and kp.position[0] < w * 0.4]
                    if armpit_candidates:
                        anatomical_points['left_armpit'] = max(armpit_candidates,
                                                              key=lambda k: k.curvature)

                if 'right_shoulder' in anatomical_points:
                    shoulder_y = anatomical_points['right_shoulder'].position[1]
                    armpit_candidates = [kp for kp in corners + inflections
                                       if shoulder_y < kp.position[1] < shoulder_y + h * 0.2
                                       and kp.position[0] > w * 0.6]
                    if armpit_candidates:
                        anatomical_points['right_armpit'] = max(armpit_candidates,
                                                               key=lambda k: k.curvature)

                # Chest points: widest points at armpit level
                if 'left_armpit' in anatomical_points or 'right_armpit' in anatomical_points:
                    armpit_points = [ap for name, ap in anatomical_points.items() if 'armpit' in name]
                    if armpit_points:
                        armpit_y = np.mean([ap.position[1] for ap in armpit_points])
                    else:
                        armpit_y = h * 0.3  # Default to upper third if no armpits found

                    chest_candidates = [kp for kp in keypoints
                                      if abs(kp.position[1] - armpit_y) < h * 0.05]

                    if chest_candidates:
                        # Leftmost and rightmost at chest level
                        anatomical_points['left_chest'] = min(chest_candidates,
                                                             key=lambda k: k.position[0])
                        anatomical_points['right_chest'] = max(chest_candidates,
                                                              key=lambda k: k.position[0])

                # Hem points: corners/inflections near bottom
                hem_candidates = [kp for kp in corners + inflections
                                if kp.position[1] > h * 0.7]

                if hem_candidates:
                    # Leftmost and rightmost hem points
                    anatomical_points['left_hem'] = min(hem_candidates,
                                                       key=lambda k: k.position[0])
                    anatomical_points['right_hem'] = max(hem_candidates,
                                                        key=lambda k: k.position[0])

                # Collar: top center point
                collar_candidates = [kp for kp in keypoints
                                   if kp.position[1] < h * 0.2
                                   and w * 0.4 < kp.position[0] < w * 0.6]
                if collar_candidates:
                    anatomical_points['collar'] = min(collar_candidates,
                                                     key=lambda k: k.position[1])

            else:
                # For bottoms (pants/skirts)

                # Waist points: top corners
                waist_candidates = [kp for kp in corners + inflections
                                  if kp.position[1] < h * 0.3]

                if waist_candidates:
                    anatomical_points['left_waist'] = min(waist_candidates,
                                                         key=lambda k: k.position[0])
                    anatomical_points['right_waist'] = max(waist_candidates,
                                                          key=lambda k: k.position[0])

                # Hem points: bottom corners
                hem_candidates = [kp for kp in corners + inflections
                                if kp.position[1] > h * 0.7]

                if hem_candidates:
                    anatomical_points['left_hem'] = min(hem_candidates,
                                                       key=lambda k: k.position[0])
                    anatomical_points['right_hem'] = max(hem_candidates,
                                                        key=lambda k: k.position[0])

                # Crotch point: lowest point in center
                crotch_candidates = [kp for kp in keypoints
                                   if w * 0.4 < kp.position[0] < w * 0.6
                                   and kp.position[1] > h * 0.4]
                if crotch_candidates:
                    anatomical_points['crotch'] = max(crotch_candidates,
                                                     key=lambda k: k.position[1])

        return anatomical_points

    def visualize_results(self, image: np.ndarray, output_dir: str, base_name: str):
        """Create comprehensive visualization of edge-based keypoint detection"""

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create figure with multiple subplots
        h, w = image.shape[:2]
        canvas_width = w * 4
        canvas_height = h * 2
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

        # Original image
        canvas[:h, :w] = image
        cv2.putText(canvas, "Original Image", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Garment mask
        if self.garment_mask is not None:
            mask_colored = cv2.cvtColor(self.garment_mask, cv2.COLOR_GRAY2BGR)
            canvas[:h, w:w*2] = mask_colored
            cv2.putText(canvas, "Garment Mask", (w + 50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Edge detection on mask
        if self.garment_mask is not None:
            edges = self.extract_garment_edges(image, self.garment_mask)
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            edges_colored[:, :, 2] = edges  # Red channel for edges
            canvas[:h, w*2:w*3] = edges_colored
            cv2.putText(canvas, "Masked Edges", (w*2 + 50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Contour with keypoints
        if self.garment_contour is not None:
            contour_vis = image.copy()
            cv2.drawContours(contour_vis, [self.garment_contour], -1, (0, 255, 0), 2)

            # Draw keypoints
            for kp in self.keypoints:
                color = (0, 0, 255)  # Red default
                if kp.type == 'corner':
                    color = (255, 0, 0)  # Blue for corners
                elif 'extrema' in kp.type:
                    color = (0, 255, 0)  # Green for extrema
                elif kp.type == 'inflection':
                    color = (255, 255, 0)  # Cyan for inflections

                cv2.circle(contour_vis, kp.position, 8, color, -1)
                cv2.circle(contour_vis, kp.position, 10, color, 2)

            canvas[:h, w*3:w*4] = contour_vis
            cv2.putText(canvas, "Contour Keypoints", (w*3 + 50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Anatomical points
        if hasattr(self, 'anatomical_points') and self.anatomical_points:
            anatomical_vis = image.copy()

            # Draw anatomical points with labels
            for name, kp in self.anatomical_points.items():
                color = (0, 255, 0)
                if 'shoulder' in name:
                    color = (255, 0, 0)
                elif 'armpit' in name:
                    color = (255, 255, 0)
                elif 'chest' in name:
                    color = (0, 0, 255)
                elif 'hem' in name:
                    color = (255, 165, 0)
                elif 'waist' in name:
                    color = (128, 0, 128)

                cv2.circle(anatomical_vis, kp.position, 10, color, -1)
                cv2.putText(anatomical_vis, name,
                          (kp.position[0] + 15, kp.position[1]),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw measurement lines
            if 'left_shoulder' in self.anatomical_points and 'right_shoulder' in self.anatomical_points:
                cv2.line(anatomical_vis,
                        self.anatomical_points['left_shoulder'].position,
                        self.anatomical_points['right_shoulder'].position,
                        (255, 0, 0), 2)

            if 'left_chest' in self.anatomical_points and 'right_chest' in self.anatomical_points:
                cv2.line(anatomical_vis,
                        self.anatomical_points['left_chest'].position,
                        self.anatomical_points['right_chest'].position,
                        (0, 0, 255), 2)

            if 'left_hem' in self.anatomical_points and 'right_hem' in self.anatomical_points:
                cv2.line(anatomical_vis,
                        self.anatomical_points['left_hem'].position,
                        self.anatomical_points['right_hem'].position,
                        (255, 165, 0), 2)

            canvas[h:h*2, :w] = anatomical_vis
            cv2.putText(canvas, "Anatomical Points", (50, h + 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Save full visualization
        output_path = os.path.join(output_dir, f"{base_name}_edge_detection_analysis.jpg")
        cv2.imwrite(output_path, canvas)
        print(f"Saved visualization to {output_path}")

        # Save individual components
        if self.garment_mask is not None:
            mask_path = os.path.join(output_dir, f"{base_name}_garment_mask.jpg")
            cv2.imwrite(mask_path, self.garment_mask)

        # Save keypoints data
        if self.keypoints:
            keypoints_data = {
                'total_keypoints': len(self.keypoints),
                'keypoints': [
                    {
                        'position': list(kp.position),
                        'type': kp.type,
                        'angle': float(kp.angle),
                        'curvature': float(kp.curvature),
                        'confidence': float(kp.confidence),
                        'index': int(kp.index)
                    }
                    for kp in self.keypoints
                ]
            }

            json_path = os.path.join(output_dir, f"{base_name}_edge_keypoints.json")
            with open(json_path, 'w') as f:
                json.dump(keypoints_data, f, indent=2)
            print(f"Saved keypoints data to {json_path}")

        # Save anatomical points
        if hasattr(self, 'anatomical_points') and self.anatomical_points:
            anatomical_data = {
                'anatomical_points': {
                    name: {
                        'position': list(kp.position),
                        'type': kp.type,
                        'confidence': kp.confidence
                    }
                    for name, kp in self.anatomical_points.items()
                }
            }

            anatomical_path = os.path.join(output_dir, f"{base_name}_anatomical_points.json")
            with open(anatomical_path, 'w') as f:
                json.dump(anatomical_data, f, indent=2)
            print(f"Saved anatomical points to {anatomical_path}")

    def process_image(self, image_path: str, output_dir: str) -> Dict:
        """Main processing pipeline"""

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image {image_path}")
            return {}

        base_name = os.path.splitext(os.path.basename(image_path))[0]

        print(f"Processing {image_path}...")

        # Step 1: Create garment mask
        print("Creating garment mask...")
        self.garment_mask = self.create_garment_mask(image)

        if self.garment_mask is None or np.sum(self.garment_mask) == 0:
            print("Warning: Could not create garment mask")
            return {}

        # Step 2: Extract garment edges
        print("Extracting garment edges...")
        edges = self.extract_garment_edges(image, self.garment_mask)

        # Step 3: Find contour keypoints
        print("Finding contour keypoints...")
        if self.garment_contour is not None:
            self.keypoints = self.find_contour_keypoints(self.garment_contour)
            print(f"Found {len(self.keypoints)} contour keypoints")

            # Step 4: Map to anatomical points
            print("Mapping to anatomical points...")
            self.anatomical_points = self.map_to_anatomical_points(self.keypoints, image.shape)
            print(f"Identified {len(self.anatomical_points)} anatomical points")
        else:
            print("Warning: No garment contour found")
            self.keypoints = []
            self.anatomical_points = {}

        # Step 5: Visualize results
        print("Creating visualizations...")
        self.visualize_results(image, output_dir, base_name)

        # Calculate measurements
        measurements = self.calculate_measurements()

        # Print summary
        print("\n" + "="*60)
        print("EDGE-BASED KEYPOINT DETECTION COMPLETE")
        print("="*60)
        print(f"Total contour keypoints: {len(self.keypoints)}")
        print(f"Anatomical points identified: {len(self.anatomical_points)}")

        if self.keypoints:
            print("\nKeypoint Types:")
            type_counts = {}
            for kp in self.keypoints:
                kp_type = kp.type.split('_')[0] if '_' in kp.type else kp.type
                type_counts[kp_type] = type_counts.get(kp_type, 0) + 1
            for kp_type, count in type_counts.items():
                print(f"  - {kp_type}: {count}")

        if self.anatomical_points:
            print("\nAnatomical Points:")
            for name, kp in self.anatomical_points.items():
                print(f"  - {name}: {kp.position}, confidence: {kp.confidence:.3f}")

        if measurements:
            print("\nMeasurements (pixels):")
            for name, value in measurements.items():
                print(f"  - {name}: {value:.1f}")

        print("="*60)

        return {
            'keypoints': self.keypoints,
            'anatomical_points': self.anatomical_points,
            'measurements': measurements
        }

    def calculate_measurements(self) -> Dict[str, float]:
        """Calculate measurements from anatomical points"""

        measurements = {}

        if not self.anatomical_points:
            return measurements

        # Shoulder width
        if 'left_shoulder' in self.anatomical_points and 'right_shoulder' in self.anatomical_points:
            shoulder_width = np.linalg.norm(
                np.array(self.anatomical_points['left_shoulder'].position) -
                np.array(self.anatomical_points['right_shoulder'].position)
            )
            measurements['shoulder_width_px'] = shoulder_width

        # Chest width
        if 'left_chest' in self.anatomical_points and 'right_chest' in self.anatomical_points:
            chest_width = np.linalg.norm(
                np.array(self.anatomical_points['left_chest'].position) -
                np.array(self.anatomical_points['right_chest'].position)
            )
            measurements['chest_width_px'] = chest_width

        # Hem width
        if 'left_hem' in self.anatomical_points and 'right_hem' in self.anatomical_points:
            hem_width = np.linalg.norm(
                np.array(self.anatomical_points['left_hem'].position) -
                np.array(self.anatomical_points['right_hem'].position)
            )
            measurements['hem_width_px'] = hem_width

        # Waist width (for bottoms)
        if 'left_waist' in self.anatomical_points and 'right_waist' in self.anatomical_points:
            waist_width = np.linalg.norm(
                np.array(self.anatomical_points['left_waist'].position) -
                np.array(self.anatomical_points['right_waist'].position)
            )
            measurements['waist_width_px'] = waist_width

        # Length measurements
        if 'collar' in self.anatomical_points and 'left_hem' in self.anatomical_points:
            length = abs(self.anatomical_points['collar'].position[1] -
                       self.anatomical_points['left_hem'].position[1])
            measurements['length_px'] = length
        elif 'left_shoulder' in self.anatomical_points and 'left_hem' in self.anatomical_points:
            length = abs(self.anatomical_points['left_shoulder'].position[1] -
                       self.anatomical_points['left_hem'].position[1])
            measurements['length_px'] = length
        elif 'left_waist' in self.anatomical_points and 'left_hem' in self.anatomical_points:
            length = abs(self.anatomical_points['left_waist'].position[1] -
                       self.anatomical_points['left_hem'].position[1])
            measurements['length_px'] = length

        return measurements

def main():
    parser = argparse.ArgumentParser(description='Edge-based keypoint detection for garments')
    parser.add_argument('image', help='Input image file')
    parser.add_argument('--output-dir', default='edge_detection_results',
                       help='Output directory for results')

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize detector
    detector = EdgeBasedKeypointDetector()

    # Process image
    results = detector.process_image(args.image, args.output_dir)

    return results

if __name__ == '__main__':
    main()