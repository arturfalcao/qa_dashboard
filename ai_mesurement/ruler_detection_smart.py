"""
Smart Ruler Detection - Hybrid CV + Simple ML approach
Solves the marking/text problem without heavy models
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats


class SmartRulerDetector:
    """
    Intelligent ruler detection using multiple CV techniques
    No heavy ML models required - uses geometric and edge-based methods
    """

    def __init__(self, known_length_cm: float = 31.0, debug: bool = False):
        self.known_length_cm = known_length_cm
        self.debug = debug

    def detect_ruler(self, image: np.ndarray) -> Dict:
        """
        Detect ruler using multi-strategy approach

        Strategies:
        1. Edge-based detection (Hough Lines)
        2. Color blob + shape analysis
        3. Geometric validation
        """
        print(f"🔍 Detecting ruler using smart CV methods...")

        # Try multiple strategies
        candidates = []

        # Strategy 1: Hough Line Transform for straight edges
        ruler_lines = self._detect_ruler_by_edges(image)
        if ruler_lines:
            candidates.append(('hough_lines', ruler_lines))

        # Strategy 2: Color segmentation + morphology (improved)
        ruler_color = self._detect_ruler_by_color_improved(image)
        if ruler_color:
            candidates.append(('color_morphology', ruler_color))

        # Strategy 3: Texture + elongation analysis
        ruler_texture = self._detect_ruler_by_texture(image)
        if ruler_texture:
            candidates.append(('texture', ruler_texture))

        if not candidates:
            raise ValueError("No ruler detected using any strategy")

        # Score and select best candidate
        best_candidate = self._select_best_ruler(candidates, image)

        if self.debug:
            self._visualize_detection(image, best_candidate)

        return best_candidate

    def _detect_ruler_by_edges(self, image: np.ndarray) -> Optional[Dict]:
        """Detect ruler using edge detection + Hough Lines"""

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Strong edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Morphological operations to connect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Detect lines using Hough Transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=500,  # At least 500 pixels long
            maxLineGap=50
        )

        if lines is None:
            return None

        # Filter for very long, straight lines (likely ruler edges)
        ruler_candidates = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)

            # Calculate angle (should be close to 0° or 90°)
            angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)

            # Ruler should be horizontal or vertical
            is_horizontal = angle < 10 or angle > 170
            is_vertical = 80 < angle < 100

            if (is_horizontal or is_vertical) and length > 1000:
                ruler_candidates.append({
                    'line': (x1, y1, x2, y2),
                    'length': length,
                    'angle': angle,
                    'orientation': 'horizontal' if is_horizontal else 'vertical'
                })

        if not ruler_candidates:
            return None

        # Get longest line
        best = max(ruler_candidates, key=lambda x: x['length'])

        return {
            'method': 'hough_lines',
            'bbox': self._line_to_bbox(best['line'], image.shape),
            'length_pixels': best['length'],
            'pixels_per_cm': best['length'] / self.known_length_cm,
            'orientation': best['orientation'],
            'confidence': min(0.9, best['length'] / 2000)  # Higher confidence for longer lines
        }

    def _detect_ruler_by_color_improved(self, image: np.ndarray) -> Optional[Dict]:
        """
        Improved color-based detection
        Uses LAB color space + intelligent morphology
        """

        # Convert to LAB (better for green detection)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Green objects have negative 'a' channel values
        green_mask = (a < 120).astype(np.uint8) * 255

        # Also try HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_green = np.array([30, 20, 20])
        upper_green = np.array([90, 255, 255])
        hsv_mask = cv2.inRange(hsv, lower_green, upper_green)

        # Combine both masks
        combined_mask = cv2.bitwise_or(green_mask, hsv_mask)

        # Aggressive morphology to connect ruler parts
        # Use directional kernels
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))

        mask_h = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_h, iterations=2)
        mask_v = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_v, iterations=2)

        # Combine both
        connected_mask = cv2.bitwise_or(mask_h, mask_v)

        # Find contours
        contours, _ = cv2.findContours(connected_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Find best ruler candidate
        image_width = image.shape[1]
        best_score = 0
        best_contour = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 5000:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / max(min(w, h), 1)

            # Ruler: high aspect ratio + near edge + good size
            if aspect_ratio > 2:
                position_score = 2.0 if x < image_width * 0.2 else 1.0
                score = aspect_ratio * np.sqrt(area) * position_score

                if score > best_score:
                    best_score = score
                    best_contour = contour

        if best_contour is None:
            return None

        # Calculate length from contour extreme points
        leftmost = tuple(best_contour[best_contour[:, :, 0].argmin()][0])
        rightmost = tuple(best_contour[best_contour[:, :, 0].argmax()][0])
        topmost = tuple(best_contour[best_contour[:, :, 1].argmin()][0])
        bottommost = tuple(best_contour[best_contour[:, :, 1].argmax()][0])

        h_dist = np.sqrt((rightmost[0]-leftmost[0])**2 + (rightmost[1]-leftmost[1])**2)
        v_dist = np.sqrt((bottommost[0]-topmost[0])**2 + (bottommost[1]-topmost[1])**2)

        length_pixels = max(h_dist, v_dist)
        orientation = 'vertical' if v_dist > h_dist else 'horizontal'

        x, y, w, h = cv2.boundingRect(best_contour)

        return {
            'method': 'color_improved',
            'bbox': (x, y, w, h),
            'length_pixels': length_pixels,
            'pixels_per_cm': length_pixels / self.known_length_cm,
            'orientation': orientation,
            'confidence': min(0.85, best_score / 50000)
        }

    def _detect_ruler_by_texture(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect ruler by analyzing texture patterns
        Rulers have regular marking patterns
        """

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gabor filters to detect regular patterns
        # Rulers often have regular markings at intervals

        # Compute standard deviation in sliding windows
        # Rulers have consistent texture (markings every cm)

        # This is a simplified version - full implementation would use
        # multiple Gabor filter orientations

        # For now, return None (not implemented in basic version)
        return None

    def _select_best_ruler(self, candidates: List[Tuple[str, Dict]], image: np.ndarray) -> Dict:
        """Select best ruler detection from multiple candidates"""

        if len(candidates) == 1:
            return candidates[0][1]

        # Score each candidate
        scored = []
        for method, ruler_info in candidates:
            score = ruler_info.get('confidence', 0.5)

            # Bonus for longer detections (more reliable)
            if ruler_info['length_pixels'] > 1500:
                score += 0.1

            # Bonus for edge-based detection (most reliable)
            if method == 'hough_lines':
                score += 0.05

            scored.append((score, ruler_info))

        # Return highest scoring candidate
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]

        print(f"   ✅ Best method: {best['method']} (confidence: {best.get('confidence', 0):.2f})")

        return best

    def _line_to_bbox(self, line: Tuple[int, int, int, int], image_shape: Tuple) -> Tuple:
        """Convert line to bounding box"""
        x1, y1, x2, y2 = line

        # Add margin around line
        margin = 20
        x_min = max(0, min(x1, x2) - margin)
        x_max = min(image_shape[1], max(x1, x2) + margin)
        y_min = max(0, min(y1, y2) - margin)
        y_max = min(image_shape[0], max(y1, y2) + margin)

        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def _visualize_detection(self, image: np.ndarray, ruler_info: Dict):
        """Save debug visualization"""
        import matplotlib.pyplot as plt

        vis = image.copy()
        x, y, w, h = ruler_info['bbox']

        cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 3)

        text = f"{ruler_info['method']}: {ruler_info['length_pixels']:.0f}px = {self.known_length_cm}cm"
        cv2.putText(vis, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        plt.figure(figsize=(12, 8))
        plt.imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        plt.title(f"Ruler Detection: {ruler_info['method']}")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig('debug_smart_ruler_detection.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✅ Debug visualization saved: debug_smart_ruler_detection.png")
