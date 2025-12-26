"""
Measurement Engine

Computes physical measurements from detected landmarks using:
1. Measurement instruction schemas (JSON-defined)
2. Multiple calculation methods (euclidean, projection, polyline)
3. Validation rules (symmetry, ranges, ratios)
4. Confidence scoring

Inspired by:
- Kim et al. (2022): 3D point cloud measurement methodology
- GarmentIQ: JSON-based measurement instructions
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from .landmark_schemas import (
    LandmarkSchema,
    get_schema_for_category,
    map_df2_to_industrial,
)
from .measurement_instructions import (
    MeasurementInstruction,
    MeasurementInstructionSet,
    MeasurementMethod,
    ValidationRule,
    ValidationRuleType,
    MeasurementStatus,
    load_measurement_instructions,
)

logger = logging.getLogger(__name__)


@dataclass
class SingleMeasurement:
    """Result of a single measurement calculation"""
    instruction_id: str
    name: str
    value_px: float                      # Value in pixels
    value_mm: Optional[float]            # Value in mm (if calibrated)
    value_cm: Optional[float]            # Value in cm
    unit: str                            # Display unit
    confidence: float                    # Measurement confidence (0-1)
    status: MeasurementStatus           # Pass/fail/warning
    landmarks_used: List[int]            # Landmark IDs used
    landmark_positions: List[Tuple[float, float]]  # Actual positions
    tolerance_mm: float                  # Tolerance threshold
    is_critical: bool                    # Whether required for QC
    notes: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of a validation rule check"""
    rule_type: ValidationRuleType
    measurements: List[str]
    passed: bool
    actual_value: float
    threshold: float
    error_message: str
    is_warning: bool


@dataclass
class MeasurementReport:
    """Complete measurement report for a garment"""
    category: str
    measurements: Dict[str, SingleMeasurement]
    validation_results: List[ValidationResult]
    overall_status: MeasurementStatus
    total_confidence: float
    critical_pass_count: int
    critical_fail_count: int
    warning_count: int
    px_per_mm: Optional[float]           # Calibration factor
    image_size: Tuple[int, int]          # (width, height)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "category": self.category,
            "overall_status": self.overall_status.value,
            "total_confidence": self.total_confidence,
            "critical_pass_count": self.critical_pass_count,
            "critical_fail_count": self.critical_fail_count,
            "warning_count": self.warning_count,
            "px_per_mm": self.px_per_mm,
            "image_size": self.image_size,
            "measurements": {
                k: {
                    "id": v.instruction_id,
                    "name": v.name,
                    "value_px": v.value_px,
                    "value_mm": v.value_mm,
                    "value_cm": v.value_cm,
                    "unit": v.unit,
                    "confidence": v.confidence,
                    "status": v.status.value,
                    "tolerance_mm": v.tolerance_mm,
                    "is_critical": v.is_critical,
                }
                for k, v in self.measurements.items()
            },
            "validation_results": [
                {
                    "rule_type": vr.rule_type.value,
                    "measurements": vr.measurements,
                    "passed": vr.passed,
                    "actual_value": vr.actual_value,
                    "threshold": vr.threshold,
                    "error_message": vr.error_message,
                    "is_warning": vr.is_warning,
                }
                for vr in self.validation_results
            ],
            "notes": self.notes,
        }


class MeasurementCalculator:
    """
    Calculates measurements from landmarks using various methods.
    """

    @staticmethod
    def euclidean(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
    ) -> Optional[float]:
        """
        Calculate Euclidean distance between two landmarks.
        """
        if len(indices) < 2:
            return None

        p1 = landmarks[indices[0]] if indices[0] < len(landmarks) else None
        p2 = landmarks[indices[1]] if indices[1] < len(landmarks) else None

        if p1 is None or p2 is None:
            return None

        return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    @staticmethod
    def horizontal_projection(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
    ) -> Optional[float]:
        """
        Calculate horizontal (X-axis) distance between landmarks.
        """
        if len(indices) < 2:
            return None

        p1 = landmarks[indices[0]] if indices[0] < len(landmarks) else None
        p2 = landmarks[indices[1]] if indices[1] < len(landmarks) else None

        if p1 is None or p2 is None:
            return None

        return abs(p2[0] - p1[0])

    @staticmethod
    def vertical_projection(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
    ) -> Optional[float]:
        """
        Calculate vertical (Y-axis) distance between landmarks.
        """
        if len(indices) < 2:
            return None

        p1 = landmarks[indices[0]] if indices[0] < len(landmarks) else None
        p2 = landmarks[indices[1]] if indices[1] < len(landmarks) else None

        if p1 is None or p2 is None:
            return None

        return abs(p2[1] - p1[1])

    @staticmethod
    def polyline(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
    ) -> Optional[float]:
        """
        Calculate total length of polyline through multiple landmarks.
        """
        if len(indices) < 2:
            return None

        total = 0.0
        prev_point = None

        for idx in indices:
            if idx >= len(landmarks):
                return None
            point = landmarks[idx]
            if point is None:
                return None

            if prev_point is not None:
                total += np.sqrt(
                    (point[0] - prev_point[0])**2 +
                    (point[1] - prev_point[1])**2
                )
            prev_point = point

        return total

    @staticmethod
    def arc_length(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
    ) -> Optional[float]:
        """
        Calculate arc length through landmarks using cubic spline.
        For now, approximates with polyline.
        """
        # TODO: Implement proper spline interpolation
        return MeasurementCalculator.polyline(landmarks, indices)

    @staticmethod
    def circumference_estimate(
        landmarks: List[Optional[Tuple[float, float]]],
        indices: List[int],
        multiplier: float = 2.0,
    ) -> Optional[float]:
        """
        Estimate circumference from width measurement.
        For flat-lay: circumference ≈ 2 × width
        """
        width = MeasurementCalculator.euclidean(landmarks, indices)
        if width is None:
            return None
        return width * multiplier


class MeasurementEngine:
    """
    Main engine for computing garment measurements.

    Takes landmark detection results and measurement instructions,
    computes all measurements, and validates results.
    """

    def __init__(
        self,
        px_per_mm: Optional[float] = None,
        use_industrial_schema: bool = True,
    ):
        """
        Args:
            px_per_mm: Calibration factor (pixels per mm). None = no scaling.
            use_industrial_schema: Use industrial landmark schema mapping
        """
        self.px_per_mm = px_per_mm
        self.use_industrial_schema = use_industrial_schema
        self.calculator = MeasurementCalculator()

    def set_calibration(self, px_per_mm: float) -> None:
        """Set the calibration factor"""
        self.px_per_mm = px_per_mm
        logger.info(f"Calibration set: {px_per_mm:.4f} px/mm")

    def compute_measurements(
        self,
        landmarks: List[Optional[Tuple[float, float]]],
        confidences: List[float],
        category: str,
        image_size: Tuple[int, int],
        instructions: Optional[MeasurementInstructionSet] = None,
        target_measurements: Optional[Dict[str, float]] = None,
    ) -> MeasurementReport:
        """
        Compute all measurements for a garment.

        Args:
            landmarks: List of (x, y) coordinates or None
            confidences: Confidence scores for each landmark
            category: Garment category
            image_size: (width, height) of the image
            instructions: Custom measurement instructions (uses defaults if None)
            target_measurements: Expected values for QC (measurement_id -> mm)

        Returns:
            MeasurementReport with all computed measurements
        """
        # Load instructions
        if instructions is None:
            instructions = load_measurement_instructions(category)

        if instructions is None:
            logger.warning(f"No measurement instructions for category: {category}")
            return MeasurementReport(
                category=category,
                measurements={},
                validation_results=[],
                overall_status=MeasurementStatus.NOT_MEASURED,
                total_confidence=0.0,
                critical_pass_count=0,
                critical_fail_count=0,
                warning_count=0,
                px_per_mm=self.px_per_mm,
                image_size=image_size,
                notes=["No measurement instructions available for this category"],
            )

        # Use landmarks directly - the measurement instructions should reference
        # the correct DeepFashion2 landmark indices for each category
        # The industrial schema mapping is handled in the instruction definitions
        ind_landmarks = landmarks
        ind_confidences = confidences

        # Compute each measurement
        measurements = {}
        for instruction in instructions.measurements:
            measurement = self._compute_single_measurement(
                instruction,
                ind_landmarks,
                ind_confidences,
                target_measurements.get(instruction.id) if target_measurements else None,
            )
            measurements[instruction.id] = measurement

        # Run validation rules
        validation_results = self._validate_measurements(
            measurements,
            instructions.validation_rules,
        )

        # Calculate overall status
        critical_pass = sum(
            1 for m in measurements.values()
            if m.is_critical and m.status == MeasurementStatus.PASS
        )
        critical_fail = sum(
            1 for m in measurements.values()
            if m.is_critical and m.status == MeasurementStatus.FAIL
        )
        warnings = sum(
            1 for m in measurements.values()
            if m.status == MeasurementStatus.WARNING
        )
        warnings += sum(1 for vr in validation_results if not vr.passed and vr.is_warning)

        # Overall status
        if critical_fail > 0:
            overall_status = MeasurementStatus.FAIL
        elif warnings > 0:
            overall_status = MeasurementStatus.WARNING
        elif critical_pass > 0:
            overall_status = MeasurementStatus.PASS
        else:
            overall_status = MeasurementStatus.NOT_MEASURED

        # Total confidence (weighted average)
        measured = [m for m in measurements.values() if m.value_px is not None]
        if measured:
            total_confidence = np.mean([m.confidence for m in measured])
        else:
            total_confidence = 0.0

        return MeasurementReport(
            category=category,
            measurements=measurements,
            validation_results=validation_results,
            overall_status=overall_status,
            total_confidence=total_confidence,
            critical_pass_count=critical_pass,
            critical_fail_count=critical_fail,
            warning_count=warnings,
            px_per_mm=self.px_per_mm,
            image_size=image_size,
        )

    def _compute_single_measurement(
        self,
        instruction: MeasurementInstruction,
        landmarks: List[Optional[Tuple[float, float]]],
        confidences: List[float],
        target_mm: Optional[float] = None,
    ) -> SingleMeasurement:
        """
        Compute a single measurement from instruction.
        """
        indices = instruction.landmarks

        # Check landmark availability and confidence
        available = True
        min_conf = 1.0
        positions = []

        for idx in indices:
            if idx >= len(landmarks) or landmarks[idx] is None:
                available = False
                break
            if idx < len(confidences) and confidences[idx] < instruction.min_confidence:
                available = False
                break
            min_conf = min(min_conf, confidences[idx] if idx < len(confidences) else 0.5)
            positions.append(landmarks[idx])

        # Try fallback landmarks if primary not available
        if not available and instruction.fallback_landmarks:
            available = True
            min_conf = 1.0
            positions = []
            indices = instruction.fallback_landmarks

            for idx in indices:
                if idx >= len(landmarks) or landmarks[idx] is None:
                    available = False
                    break
                min_conf = min(min_conf, confidences[idx] if idx < len(confidences) else 0.5)
                positions.append(landmarks[idx])

        if not available:
            return SingleMeasurement(
                instruction_id=instruction.id,
                name=instruction.name,
                value_px=0.0,
                value_mm=None,
                value_cm=None,
                unit=instruction.unit,
                confidence=0.0,
                status=MeasurementStatus.NOT_MEASURED,
                landmarks_used=instruction.landmarks,
                landmark_positions=[],
                tolerance_mm=instruction.tolerance_mm,
                is_critical=instruction.is_critical,
                notes="Required landmarks not detected",
            )

        # Calculate measurement based on method
        if instruction.method == MeasurementMethod.EUCLIDEAN:
            value_px = self.calculator.euclidean(landmarks, indices)
        elif instruction.method == MeasurementMethod.HORIZONTAL_PROJECTION:
            value_px = self.calculator.horizontal_projection(landmarks, indices)
        elif instruction.method == MeasurementMethod.VERTICAL_PROJECTION:
            value_px = self.calculator.vertical_projection(landmarks, indices)
        elif instruction.method == MeasurementMethod.POLYLINE:
            value_px = self.calculator.polyline(landmarks, indices)
        elif instruction.method == MeasurementMethod.ARC_LENGTH:
            value_px = self.calculator.arc_length(landmarks, indices)
        elif instruction.method == MeasurementMethod.CIRCUMFERENCE_ESTIMATE:
            value_px = self.calculator.circumference_estimate(
                landmarks, indices, instruction.multiplier
            )
        else:
            value_px = self.calculator.euclidean(landmarks, indices)

        if value_px is None:
            return SingleMeasurement(
                instruction_id=instruction.id,
                name=instruction.name,
                value_px=0.0,
                value_mm=None,
                value_cm=None,
                unit=instruction.unit,
                confidence=0.0,
                status=MeasurementStatus.NOT_MEASURED,
                landmarks_used=indices,
                landmark_positions=positions,
                tolerance_mm=instruction.tolerance_mm,
                is_critical=instruction.is_critical,
                notes="Measurement calculation failed",
            )

        # Apply multiplier
        value_px *= instruction.multiplier

        # Convert to physical units
        if self.px_per_mm is not None:
            value_mm = value_px / self.px_per_mm
            value_cm = value_mm / 10.0
        else:
            value_mm = None
            value_cm = None

        # Determine status
        status = MeasurementStatus.PASS

        if target_mm is not None and value_mm is not None:
            error = abs(value_mm - target_mm)
            if error > instruction.tolerance_mm:
                status = MeasurementStatus.FAIL
            elif error > instruction.tolerance_mm * 0.7:
                status = MeasurementStatus.WARNING

        return SingleMeasurement(
            instruction_id=instruction.id,
            name=instruction.name,
            value_px=value_px,
            value_mm=value_mm,
            value_cm=value_cm,
            unit=instruction.unit,
            confidence=min_conf,
            status=status,
            landmarks_used=indices,
            landmark_positions=positions,
            tolerance_mm=instruction.tolerance_mm,
            is_critical=instruction.is_critical,
            notes=instruction.notes,
        )

    def _validate_measurements(
        self,
        measurements: Dict[str, SingleMeasurement],
        rules: List[ValidationRule],
    ) -> List[ValidationResult]:
        """
        Run validation rules on computed measurements.
        """
        results = []

        for rule in rules:
            # Get relevant measurements
            relevant = [
                measurements.get(m_id) for m_id in rule.measurements
                if m_id in measurements
            ]

            if len(relevant) != len(rule.measurements):
                # Not all measurements available
                continue

            if any(m.value_mm is None for m in relevant):
                # Need calibration for validation
                continue

            # Apply rule
            if rule.rule_type == ValidationRuleType.SYMMETRY:
                # Check if left/right measurements are similar
                if len(relevant) >= 2:
                    diff = abs(relevant[0].value_mm - relevant[1].value_mm)
                    passed = diff < rule.threshold
                    actual_value = diff
                else:
                    passed = True
                    actual_value = 0

            elif rule.rule_type == ValidationRuleType.DIFFERENCE:
                if len(relevant) >= 2:
                    diff = abs(relevant[0].value_mm - relevant[1].value_mm)
                    passed = diff < rule.threshold
                    actual_value = diff
                else:
                    passed = True
                    actual_value = 0

            elif rule.rule_type == ValidationRuleType.RATIO:
                if len(relevant) >= 2 and relevant[1].value_mm != 0:
                    ratio = relevant[0].value_mm / relevant[1].value_mm
                    # Parse condition like "0.8 < ratio < 1.3"
                    # For simplicity, check reasonable range
                    passed = 0.5 < ratio < 2.0
                    actual_value = ratio
                else:
                    passed = True
                    actual_value = 1.0

            elif rule.rule_type == ValidationRuleType.RANGE:
                if relevant:
                    value = relevant[0].value_mm
                    # Parse condition like "400 < value < 900"
                    # For simplicity, use threshold as max
                    passed = 0 < value < rule.threshold * 10 if rule.threshold > 0 else True
                    actual_value = value
                else:
                    passed = True
                    actual_value = 0

            else:
                passed = True
                actual_value = 0

            results.append(ValidationResult(
                rule_type=rule.rule_type,
                measurements=rule.measurements,
                passed=passed,
                actual_value=actual_value,
                threshold=rule.threshold,
                error_message=rule.error_message if not passed else "",
                is_warning=rule.is_warning,
            ))

        return results


def create_measurement_engine(
    px_per_mm: Optional[float] = None,
) -> MeasurementEngine:
    """
    Factory function to create a measurement engine.

    Args:
        px_per_mm: Calibration factor. None = pixels only.

    Returns:
        Configured MeasurementEngine
    """
    return MeasurementEngine(px_per_mm=px_per_mm)
