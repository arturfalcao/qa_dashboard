#!/usr/bin/env python3
"""
Measurement computation module with uncertainty estimation.
Calculates garment dimensions from landmarks with sub-2mm precision targets.
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class MeasurementCalculator:
    """
    Calculates garment measurements from detected landmarks.
    Includes uncertainty estimation and validation.
    """

    # Measurement definitions: (point1, point2, name)
    MEASUREMENT_DEFINITIONS = {
        'tshirt': {
            'chest': ('left_armpit', 'right_armpit'),
            'hps_length': ('neck_center', 'bottom_hem_center'),
            'left_sleeve': ('left_shoulder', 'left_sleeve_end'),
            'right_sleeve': ('right_shoulder', 'right_sleeve_end'),
            'shoulder_width': ('left_shoulder', 'right_shoulder')
        },
        'hoodie': {
            'chest': ('left_armpit', 'right_armpit'),
            'hps_length': ('neck_center', 'bottom_hem_center'),
            'left_sleeve': ('left_shoulder', 'left_sleeve_end'),
            'right_sleeve': ('right_shoulder', 'right_sleeve_end'),
            'shoulder_width': ('left_shoulder', 'right_shoulder'),
            'hood_height': ('neck_center', 'hood_top')
        },
        'pants': {
            'waist': ('waist_left', 'waist_right'),
            'hip': ('hip_left', 'hip_right'),
            'left_inseam': ('crotch', 'left_hem'),
            'right_inseam': ('crotch', 'right_hem'),
            'left_outseam': ('left_outseam_top', 'left_hem'),
            'right_outseam': ('right_outseam_top', 'right_hem'),
            'rise': ('crotch', 'waist_center')  # If waist_center available
        },
        'shorts': {
            'waist': ('waist_left', 'waist_right'),
            'hip': ('hip_left', 'hip_right'),
            'left_inseam': ('crotch', 'left_hem'),
            'right_inseam': ('crotch', 'right_hem'),
            'left_outseam': ('left_outseam_top', 'left_hem'),
            'right_outseam': ('right_outseam_top', 'right_hem')
        },
        'skirt': {
            'waist': ('waist_left', 'waist_right'),
            'hip': ('hip_left', 'hip_right'),
            'length': ('waist_center', 'hem_center'),
            'hem_width': ('hem_left', 'hem_right')
        },
        'dress': {
            'bust': ('bust_left', 'bust_right'),
            'waist': ('waist_left', 'waist_right'),
            'hip': ('hip_left', 'hip_right'),
            'length': ('shoulder_center', 'hem_center'),
            'hem_width': ('hem_left', 'hem_right')
        }
    }

    def __init__(self, pixel_to_mm: float, rect_rms_mm: float = 0.5):
        """
        Initialize calculator.

        Args:
            pixel_to_mm: Conversion factor from pixels to millimeters
            rect_rms_mm: RMS error from rectification in mm
        """
        self.pixel_to_mm = pixel_to_mm
        self.rect_rms_mm = rect_rms_mm

        # Uncertainty components (in mm)
        self.landmark_uncertainty_px = 2.0  # Pixels uncertainty in landmark position
        self.scale_uncertainty_factor = 0.002  # 0.2% scale uncertainty

    def calculate_distance(self, point1: Tuple[float, float],
                          point2: Tuple[float, float]) -> float:
        """
        Calculate Euclidean distance between two points.

        Args:
            point1: (x, y) coordinates
            point2: (x, y) coordinates

        Returns:
            Distance in pixels
        """
        return np.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

    def calculate_measurements(self, landmarks: Dict[str, Tuple[float, float, float]],
                              garment_type: str,
                              rectified: bool = False) -> Dict[str, float]:
        """
        Calculate all measurements for a garment type.

        Args:
            landmarks: Dictionary of landmark positions
            garment_type: Type of garment
            rectified: Whether landmarks are in rectified coordinates

        Returns:
            Dictionary of measurements in mm
        """
        measurements = {}

        definitions = self.MEASUREMENT_DEFINITIONS.get(garment_type, {})

        for measure_name, (point1_name, point2_name) in definitions.items():
            if point1_name in landmarks and point2_name in landmarks:
                point1 = landmarks[point1_name][:2]  # (x, y)
                point2 = landmarks[point2_name][:2]

                # Calculate distance
                distance_px = self.calculate_distance(point1, point2)
                distance_mm = distance_px * self.pixel_to_mm

                measurements[measure_name] = distance_mm

                logger.debug(f"{measure_name}: {distance_mm:.1f} mm "
                           f"({point1_name} to {point2_name})")
            else:
                logger.warning(f"Missing landmarks for {measure_name}: "
                             f"{point1_name} or {point2_name}")

        # Add derived measurements
        measurements.update(self._calculate_derived_measurements(
            measurements, landmarks, garment_type))

        return measurements

    def _calculate_derived_measurements(self, measurements: Dict[str, float],
                                       landmarks: Dict[str, Tuple[float, float, float]],
                                       garment_type: str) -> Dict[str, float]:
        """Calculate derived measurements like averages."""
        derived = {}

        # Average sleeve length for tops
        if garment_type in ['tshirt', 'hoodie']:
            if 'left_sleeve' in measurements and 'right_sleeve' in measurements:
                derived['sleeve_avg'] = (measurements['left_sleeve'] +
                                        measurements['right_sleeve']) / 2

        # Average inseam for pants
        if garment_type in ['pants', 'shorts']:
            if 'left_inseam' in measurements and 'right_inseam' in measurements:
                derived['inseam_avg'] = (measurements['left_inseam'] +
                                        measurements['right_inseam']) / 2

            if 'left_outseam' in measurements and 'right_outseam' in measurements:
                derived['outseam_avg'] = (measurements['left_outseam'] +
                                         measurements['right_outseam']) / 2

        # Calculate waist_center if not available
        if 'waist_left' in landmarks and 'waist_right' in landmarks:
            waist_left = landmarks['waist_left'][:2]
            waist_right = landmarks['waist_right'][:2]
            waist_center_x = (waist_left[0] + waist_right[0]) / 2
            waist_center_y = (waist_left[1] + waist_right[1]) / 2

            # Add rise measurement for pants if crotch available
            if garment_type in ['pants', 'shorts'] and 'crotch' in landmarks:
                crotch = landmarks['crotch'][:2]
                rise_px = self.calculate_distance((waist_center_x, waist_center_y), crotch)
                derived['rise'] = rise_px * self.pixel_to_mm

        return derived

    def estimate_uncertainty(self, landmarks: Dict[str, Tuple[float, float, float]],
                           measurements: Dict[str, float],
                           mask: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Estimate measurement uncertainty (95% confidence interval).

        Components:
        1. Landmark detection uncertainty
        2. Scale/calibration uncertainty
        3. Rectification uncertainty
        4. Mask boundary uncertainty

        Args:
            landmarks: Dictionary of landmark positions with confidence
            measurements: Calculated measurements
            mask: Optional segmentation mask for boundary uncertainty

        Returns:
            Dictionary of uncertainties in mm (95% CI half-width)
        """
        uncertainties = {}

        definitions = self.MEASUREMENT_DEFINITIONS.get('tshirt', {})  # Default

        for measure_name, distance_mm in measurements.items():
            # Base uncertainty from landmark detection (in pixels)
            landmark_uncertainty_mm = self.landmark_uncertainty_px * self.pixel_to_mm

            # Get confidence scores if available
            confidence_factor = 1.0
            if measure_name in definitions:
                point1_name, point2_name = definitions[measure_name]
                if point1_name in landmarks and point2_name in landmarks:
                    conf1 = landmarks[point1_name][2] if len(landmarks[point1_name]) > 2 else 0.5
                    conf2 = landmarks[point2_name][2] if len(landmarks[point2_name]) > 2 else 0.5
                    avg_confidence = (conf1 + conf2) / 2
                    # Lower confidence increases uncertainty
                    confidence_factor = 1.0 / max(avg_confidence, 0.1)

            # Scale uncertainty (proportional to measurement)
            scale_uncertainty_mm = distance_mm * self.scale_uncertainty_factor

            # Rectification uncertainty
            rect_uncertainty_mm = self.rect_rms_mm

            # Combine uncertainties (assuming independent)
            # Using root sum of squares for independent errors
            total_variance = (
                (landmark_uncertainty_mm * confidence_factor) ** 2 +
                scale_uncertainty_mm ** 2 +
                rect_uncertainty_mm ** 2
            )

            # 95% CI is approximately 2 * standard deviation
            uncertainty_95ci = 2.0 * np.sqrt(total_variance)

            # Add mask boundary uncertainty if available
            if mask is not None:
                # Estimate based on edge gradient strength
                # (This is simplified - could use actual edge analysis)
                boundary_uncertainty_mm = 0.5  # Conservative estimate
                uncertainty_95ci = np.sqrt(uncertainty_95ci ** 2 +
                                          boundary_uncertainty_mm ** 2)

            uncertainties[measure_name] = uncertainty_95ci

        return uncertainties

    def validate_measurements(self, measurements: Dict[str, float],
                            garment_type: str) -> Dict[str, Any]:
        """
        Validate measurements against expected ranges.

        Args:
            measurements: Dictionary of measurements in mm
            garment_type: Type of garment

        Returns:
            Validation results with warnings and flags
        """
        # Physical constraints (in mm)
        constraints = {
            'tshirt': {
                'chest': (300, 800),
                'hps_length': (400, 900),
                'sleeve_avg': (100, 300)
            },
            'hoodie': {
                'chest': (350, 850),
                'hps_length': (450, 950),
                'sleeve_avg': (400, 800)
            },
            'pants': {
                'waist': (500, 1400),
                'hip': (600, 1500),
                'inseam_avg': (500, 950),
                'outseam_avg': (800, 1300)
            },
            'shorts': {
                'waist': (500, 1400),
                'hip': (600, 1500),
                'inseam_avg': (50, 500),
                'outseam_avg': (200, 700)
            },
            'skirt': {
                'waist': (500, 1200),
                'hip': (600, 1400),
                'length': (200, 1200)
            },
            'dress': {
                'bust': (600, 1300),
                'waist': (500, 1100),
                'hip': (700, 1400),
                'length': (600, 1600)
            }
        }

        validation = {
            'valid': True,
            'warnings': [],
            'out_of_range': []
        }

        if garment_type not in constraints:
            validation['warnings'].append(f"No constraints defined for {garment_type}")
            return validation

        ranges = constraints[garment_type]

        for measure_name, value in measurements.items():
            if measure_name in ranges:
                min_val, max_val = ranges[measure_name]
                if value < min_val or value > max_val:
                    validation['out_of_range'].append(
                        f"{measure_name}: {value:.0f}mm (expected {min_val}-{max_val}mm)"
                    )
                    if value < min_val * 0.5 or value > max_val * 1.5:
                        validation['valid'] = False  # Way out of range

        # Check for measurement consistency
        if garment_type in ['pants', 'shorts']:
            if 'inseam_avg' in measurements and 'outseam_avg' in measurements:
                if measurements['outseam_avg'] < measurements['inseam_avg']:
                    validation['warnings'].append(
                        "Outseam shorter than inseam - possible measurement error"
                    )
                    validation['valid'] = False

        return validation

    def apply_correction_model(self, measurements: Dict[str, float],
                             correction_params: Optional[Dict] = None) -> Dict[str, float]:
        """
        Apply learned correction model to reduce systematic errors.

        Args:
            measurements: Raw measurements
            correction_params: Learned correction parameters

        Returns:
            Corrected measurements
        """
        if correction_params is None:
            # Default: no correction
            return measurements

        corrected = {}
        for name, value in measurements.items():
            if name in correction_params:
                # Linear correction: corrected = alpha * raw + beta
                alpha = correction_params[name].get('alpha', 1.0)
                beta = correction_params[name].get('beta', 0.0)
                corrected[name] = alpha * value + beta
            else:
                corrected[name] = value

        return corrected

    def format_measurements(self, measurements: Dict[str, float],
                           uncertainties: Dict[str, float],
                           units: str = 'mm') -> Dict[str, str]:
        """
        Format measurements with uncertainties for display.

        Args:
            measurements: Dictionary of measurements in mm
            uncertainties: Dictionary of uncertainties in mm
            units: Output units ('mm', 'cm', 'in')

        Returns:
            Formatted strings with measurements ± uncertainty
        """
        formatted = {}

        conversion = {
            'mm': 1.0,
            'cm': 0.1,
            'in': 0.0393701
        }

        factor = conversion.get(units, 1.0)

        for name, value in measurements.items():
            converted_value = value * factor
            uncertainty = uncertainties.get(name, 0) * factor

            if units == 'mm':
                formatted[name] = f"{converted_value:.0f} ± {uncertainty:.0f} mm"
            elif units == 'cm':
                formatted[name] = f"{converted_value:.1f} ± {uncertainty:.1f} cm"
            else:  # inches
                formatted[name] = f"{converted_value:.2f} ± {uncertainty:.2f} in"

        return formatted


def main():
    """Test measurement calculation."""
    # Example landmarks (in pixels)
    test_landmarks = {
        'left_armpit': (150, 200, 0.8),
        'right_armpit': (350, 200, 0.8),
        'neck_center': (250, 100, 0.9),
        'bottom_hem_center': (250, 400, 0.9),
        'left_shoulder': (180, 120, 0.7),
        'right_shoulder': (320, 120, 0.7),
        'left_sleeve_end': (100, 180, 0.6),
        'right_sleeve_end': (400, 180, 0.6)
    }

    # Initialize calculator (example scale)
    calculator = MeasurementCalculator(pixel_to_mm=0.5, rect_rms_mm=0.3)

    # Calculate measurements
    measurements = calculator.calculate_measurements(test_landmarks, 'tshirt')
    print("Measurements:")
    for name, value in measurements.items():
        print(f"  {name}: {value:.1f} mm")

    # Estimate uncertainties
    uncertainties = calculator.estimate_uncertainty(test_landmarks, measurements)
    print("\nUncertainties (95% CI):")
    for name, value in uncertainties.items():
        print(f"  {name}: ±{value:.1f} mm")

    # Format for display
    formatted = calculator.format_measurements(measurements, uncertainties, 'cm')
    print("\nFormatted:")
    for name, value in formatted.items():
        print(f"  {name}: {value}")

    # Validate
    validation = calculator.validate_measurements(measurements, 'tshirt')
    print(f"\nValidation: {validation}")


if __name__ == '__main__':
    main()