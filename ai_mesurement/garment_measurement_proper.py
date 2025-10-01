#!/usr/bin/env python3
"""
Proper Garment Measurement Module
Implements industry-standard measurement methods following ISO standards and POMs
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional, List
# Use CLIP classifier's GarmentType for consistency
from garment_classifier_clip import GarmentType


class ProperGarmentMeasurer:
    """
    Implements proper garment measurements following industry standards

    Key Concepts:
    - HPS (High Point Shoulder): Where shoulder meets neckline
    - Measurements are taken vertically/horizontally, NOT diagonally
    - Specific points like "1 inch below armhole" are used
    """

    def __init__(self, pixels_per_cm: float):
        self.pixels_per_cm = pixels_per_cm

    def measure_garment(self, mask: np.ndarray, garment_type: GarmentType,
                       image: np.ndarray = None) -> Dict[str, float]:
        """
        Measure garment using proper industry methods

        Args:
            mask: Binary mask of garment
            garment_type: Type of garment
            image: Optional original image for color analysis

        Returns:
            Dictionary of proper measurements
        """

        # Get contour and bounding box
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("No garment found in mask")

        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)

        # Apply proper measurement based on garment type
        if garment_type == GarmentType.SHIRT:
            measurements = self._measure_shirt_proper(mask, contour, x, y, w, h)
        elif garment_type == GarmentType.TROUSERS:
            measurements = self._measure_trousers_proper(mask, contour, x, y, w, h)
        elif garment_type == GarmentType.DRESS:
            measurements = self._measure_dress_proper(mask, contour, x, y, w, h)
        elif garment_type == GarmentType.JACKET:
            measurements = self._measure_jacket_proper(mask, contour, x, y, w, h)
        else:
            measurements = self._measure_basic(mask, contour, x, y, w, h)

        return measurements

    def _measure_shirt_proper(self, mask: np.ndarray, contour: np.ndarray,
                             x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """
        Measure shirt/top using industry standards

        Key measurements:
        - Body Length: HPS to hem (vertical, not diagonal!)
        - Chest: 1" below armhole (horizontal)
        - Waist: At narrowest point (horizontal)
        - Bottom Sweep: Hem width (horizontal)
        - Shoulder: Seam to seam (if detectable)
        """

        measurements = {}

        # Find HPS (High Point Shoulder) - approximate as top center of garment
        hps_point = self._find_hps(mask, x, y, w, h)

        # 1. BODY LENGTH - Vertical from HPS to bottom
        if hps_point:
            # Draw vertical line from HPS down
            hps_x = hps_point[0]

            # Find bottom point directly below HPS
            bottom_y = y + h - 1
            # Scan up to find actual garment bottom at this x position
            for scan_y in range(bottom_y, y + int(h * 0.5), -1):
                if scan_y < mask.shape[0] and hps_x < mask.shape[1]:
                    if mask[scan_y, hps_x] > 0:
                        bottom_y = scan_y
                        break

            body_length_px = bottom_y - hps_point[1]
            measurements['body_length_cm'] = body_length_px / self.pixels_per_cm
            measurements['body_length_points'] = {
                'hps': hps_point,
                'bottom': (hps_x, bottom_y)
            }
        else:
            # Fallback to center line measurement
            center_x = x + w // 2
            top_y = y
            bottom_y = y + h

            # Find actual top at center
            for scan_y in range(y, y + int(h * 0.3)):
                if scan_y < mask.shape[0] and center_x < mask.shape[1]:
                    if mask[scan_y, center_x] > 0:
                        top_y = scan_y
                        break

            # Find actual bottom at center
            for scan_y in range(y + h - 1, y + int(h * 0.7), -1):
                if scan_y < mask.shape[0] and center_x < mask.shape[1]:
                    if mask[scan_y, center_x] > 0:
                        bottom_y = scan_y
                        break

            body_length_px = bottom_y - top_y
            measurements['body_length_cm'] = body_length_px / self.pixels_per_cm
            measurements['body_length_points'] = {
                'top': (center_x, top_y),
                'bottom': (center_x, bottom_y)
            }

        # 2. CHEST WIDTH - Find the widest point in upper half of the garment
        # This is typically around 20-40% from top for a laid-flat shirt
        chest_start = y + int(h * 0.20)
        chest_end = y + int(h * 0.45)
        max_chest_width = 0
        chest_measure_y = chest_start

        # Scan for the widest point in the chest region
        for scan_y in range(chest_start, chest_end, 5):
            width = self._measure_width_at_height(mask, scan_y, x, w)
            if width and width > max_chest_width:
                max_chest_width = width
                chest_measure_y = scan_y

        if max_chest_width > 0:
            measurements['chest_width_cm'] = max_chest_width / self.pixels_per_cm
            measurements['chest_circumference_cm'] = (max_chest_width / self.pixels_per_cm) * 2
            measurements['chest_y'] = chest_measure_y

        # 3. WAIST WIDTH - Look for the narrowest point or a moderate width in the middle
        waist_start = y + int(h * 0.40)
        waist_end = y + int(h * 0.60)

        # Collect all widths in the waist region
        waist_widths = []
        for scan_y in range(waist_start, waist_end, 3):
            width = self._measure_width_at_height(mask, scan_y, x, w)
            if width and width > 0:
                waist_widths.append((width, scan_y))

        if waist_widths:
            # Sort by width to find narrowest
            waist_widths.sort(key=lambda x: x[0])

            # For shirts, the waist isn't always the narrowest point
            # Take a point that's narrow but not the absolute minimum (which might be noise)
            # Use the 25th percentile for more stable measurement
            percentile_idx = max(0, min(len(waist_widths) // 4, len(waist_widths) - 1))
            waist_width, waist_y = waist_widths[percentile_idx]

            measurements['waist_width_cm'] = waist_width / self.pixels_per_cm
            measurements['waist_y'] = waist_y

        # 4. BOTTOM SWEEP (HEM) - Find the widest point at the bottom
        hem_start = y + int(h * 0.93)
        hem_end = y + h
        max_hem_width = 0
        hem_y = hem_start

        # Scan for widest point in hem region (the hem often flares out)
        for scan_y in range(hem_start, min(hem_end, mask.shape[0]), 2):
            width = self._measure_width_at_height(mask, scan_y, x, w)
            if width and width > max_hem_width:
                max_hem_width = width
                hem_y = scan_y

        if max_hem_width > 0:
            measurements['hem_width_cm'] = max_hem_width / self.pixels_per_cm
            measurements['hem_y'] = hem_y

        # 5. SHOULDER WIDTH - If detectable
        shoulder_width = self._find_shoulder_width(mask, x, y, w, h)
        if shoulder_width:
            measurements['shoulder_width_cm'] = shoulder_width / self.pixels_per_cm

        return measurements

    def _measure_trousers_proper(self, mask: np.ndarray, contour: np.ndarray,
                                x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """
        Measure trousers using industry standards

        Key measurements:
        - Body Length: Top of waistband to hem
        - Waist: Top edge width
        - Hip: 7-9" below waist
        - Rise: Crotch to waistband
        - Inseam: Inner leg from crotch to hem
        - Thigh: 1-2" below crotch
        - Leg Opening: Hem width
        """

        measurements = {}

        # 1. BODY LENGTH (OUTSEAM) - Side measurement from waist to hem
        # Find leftmost points at top and bottom
        left_edge_points = self._find_left_edge_points(mask, x, y, w, h)
        if left_edge_points:
            top_left, bottom_left = left_edge_points
            body_length_px = bottom_left[1] - top_left[1]
            measurements['outseam_cm'] = body_length_px / self.pixels_per_cm
            measurements['outseam_points'] = {'top': top_left, 'bottom': bottom_left}

        # 2. WAIST - Top edge
        waist_y = y + int(h * 0.05)
        waist_width = self._measure_width_at_height(mask, waist_y, x, w)
        if waist_width:
            measurements['waist_width_cm'] = waist_width / self.pixels_per_cm
            measurements['waist_circumference_cm'] = (waist_width / self.pixels_per_cm) * 2

        # 3. HIP - 7-9 inches below waist (approximately 20-25cm)
        hip_distance_cm = 20  # Standard hip measurement point
        hip_distance_px = int(hip_distance_cm * self.pixels_per_cm)
        hip_y = waist_y + hip_distance_px

        if hip_y < y + h * 0.5:  # Make sure we're not too far down
            hip_width = self._measure_width_at_height(mask, hip_y, x, w)
            if hip_width:
                measurements['hip_width_cm'] = hip_width / self.pixels_per_cm

        # 4. RISE & INSEAM - Find crotch point
        crotch_point = self._find_crotch_point(mask, x, y, w, h)
        if crotch_point:
            # Front rise
            rise_px = crotch_point[1] - y
            measurements['rise_cm'] = rise_px / self.pixels_per_cm

            # Inseam - from crotch to hem at inner leg
            inseam_px = (y + h) - crotch_point[1]
            measurements['inseam_cm'] = inseam_px / self.pixels_per_cm
            measurements['crotch_point'] = crotch_point

        # 5. THIGH - 1-2 inches below crotch
        if crotch_point:
            thigh_offset_cm = 3  # About 1.2 inches
            thigh_y = crotch_point[1] + int(thigh_offset_cm * self.pixels_per_cm)
            if thigh_y < y + h:
                thigh_width = self._measure_width_at_height(mask, thigh_y, x, w)
                if thigh_width:
                    measurements['thigh_width_cm'] = thigh_width / self.pixels_per_cm

        # 6. KNEE - Approximately 60% down
        knee_y = y + int(h * 0.6)
        knee_width = self._measure_width_at_height(mask, knee_y, x, w)
        if knee_width:
            measurements['knee_width_cm'] = knee_width / self.pixels_per_cm

        # 7. LEG OPENING (HEM)
        hem_y = y + int(h * 0.95)
        hem_width = self._measure_width_at_height(mask, hem_y, x, w)
        if hem_width:
            measurements['leg_opening_cm'] = hem_width / self.pixels_per_cm

        return measurements

    def _measure_dress_proper(self, mask: np.ndarray, contour: np.ndarray,
                             x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """Measure dress using proper methods"""

        # Similar to shirt but with additional measurements
        measurements = self._measure_shirt_proper(mask, contour, x, y, w, h)

        # Add hip measurement (typically 7-9" below waist)
        if 'waist_y' in measurements:
            hip_distance_cm = 20
            hip_y = measurements['waist_y'] + int(hip_distance_cm * self.pixels_per_cm)
            if hip_y < y + h:
                hip_width = self._measure_width_at_height(mask, hip_y, x, w)
                if hip_width:
                    measurements['hip_width_cm'] = hip_width / self.pixels_per_cm

        return measurements

    def _measure_jacket_proper(self, mask: np.ndarray, contour: np.ndarray,
                              x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """Measure jacket using proper methods"""

        # Similar to shirt measurements
        return self._measure_shirt_proper(mask, contour, x, y, w, h)

    def _measure_basic(self, mask: np.ndarray, contour: np.ndarray,
                      x: int, y: int, w: int, h: int) -> Dict[str, float]:
        """Basic measurements for unknown garments"""

        measurements = {
            'height_cm': h / self.pixels_per_cm,
            'width_cm': w / self.pixels_per_cm,
            'area_cm2': cv2.contourArea(contour) / (self.pixels_per_cm ** 2)
        }
        return measurements

    # Helper methods

    def _find_hps(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[Tuple[int, int]]:
        """
        Find High Point Shoulder (HPS) - where shoulder meets neckline
        For laid flat garments, this is typically the highest point near center
        """

        # Look in top 15% of garment
        search_height = int(h * 0.15)

        # Start from center and work outward
        center_x = x + w // 2

        # Find highest point near center (within 20% of width from center)
        search_width = int(w * 0.2)
        highest_y = y + search_height
        hps_x = center_x

        for scan_x in range(center_x - search_width, center_x + search_width, 5):
            if scan_x < x or scan_x >= x + w:
                continue

            # Find topmost point at this x
            for scan_y in range(y, y + search_height):
                if scan_y < mask.shape[0] and scan_x < mask.shape[1]:
                    if mask[scan_y, scan_x] > 0:
                        if scan_y < highest_y:
                            highest_y = scan_y
                            hps_x = scan_x
                        break

        if highest_y < y + search_height:
            return (hps_x, highest_y)

        return None

    def _measure_width_at_height(self, mask: np.ndarray, y: int, x: int, w: int) -> Optional[float]:
        """Measure horizontal width at specific height"""

        if y >= mask.shape[0]:
            return None

        # Get row at this height
        row = mask[y, x:x+w]

        # Find leftmost and rightmost points
        nonzero = np.nonzero(row)[0]

        if len(nonzero) > 0:
            left_x = nonzero[0]
            right_x = nonzero[-1]
            width = right_x - left_x
            return float(width)

        return None

    def _find_shoulder_width(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[float]:
        """Find shoulder width if detectable"""

        # Look in top 10% of garment
        shoulder_y = y + int(h * 0.05)

        # Measure width at shoulder level
        width = self._measure_width_at_height(mask, shoulder_y, x, w)

        # Verify it's actually shoulders (should be wider than neck area)
        if width:
            neck_y = y + int(h * 0.02)
            neck_width = self._measure_width_at_height(mask, neck_y, x, w)

            if neck_width and width > neck_width * 1.2:  # Shoulders should be wider
                return width

        return None

    def _find_crotch_point(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[Tuple[int, int]]:
        """Find crotch point for trousers"""

        # Look for where legs split (typically 35-50% down)
        center_x = x + w // 2

        for scan_y in range(y + int(h * 0.35), y + int(h * 0.65)):
            if scan_y < mask.shape[0] and center_x < mask.shape[1]:
                # Check if there's a gap in the middle
                if mask[scan_y, center_x] == 0:
                    # Verify it's the crotch (gap should continue)
                    gap_continues = True
                    for check_y in range(scan_y, min(scan_y + 30, mask.shape[0])):
                        if mask[check_y, center_x] > 0:
                            gap_continues = False
                            break

                    if gap_continues:
                        # Find actual crotch point (highest point of gap)
                        return (center_x, scan_y)

        return None

    def _find_left_edge_points(self, mask: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[Tuple]:
        """Find leftmost points at top and bottom for outseam measurement"""

        # Top left point
        top_region = mask[y:y+int(h*0.1), x:x+w]
        top_left = None

        for row_idx, row in enumerate(top_region):
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                top_left = (x + nonzero[0], y + row_idx)
                break

        # Bottom left point
        bottom_region = mask[y+int(h*0.9):y+h, x:x+w]
        bottom_left = None

        for row_idx, row in enumerate(bottom_region):
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                bottom_left = (x + nonzero[0], y + int(h*0.9) + row_idx)

        if top_left and bottom_left:
            return (top_left, bottom_left)

        return None