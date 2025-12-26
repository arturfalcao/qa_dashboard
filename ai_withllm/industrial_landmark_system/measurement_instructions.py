"""
GarmentIQ-Inspired Measurement Instruction Schema

This module implements a JSON-based measurement instruction system inspired by
GarmentIQ (2025). The schema allows flexible definition of:

1. Which landmarks to use for each measurement
2. How to calculate the measurement (euclidean, projection, arc)
3. Tolerance thresholds for QC pass/fail
4. Validation rules (symmetry, ratios, ranges)
5. Localized display names

This design enables easy extension to new garment types and measurement
specifications without code changes.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MeasurementMethod(Enum):
    """Methods for calculating measurements from landmarks"""
    EUCLIDEAN = "euclidean"              # Straight-line distance
    HORIZONTAL_PROJECTION = "horizontal_projection"  # X-axis distance only
    VERTICAL_PROJECTION = "vertical_projection"      # Y-axis distance only
    ARC_LENGTH = "arc_length"            # Length along curve through points
    POLYLINE = "polyline"                # Sum of segment lengths
    CIRCUMFERENCE_ESTIMATE = "circumference_estimate"  # 2x width for circumference


class MeasurementStatus(Enum):
    """Status of a measurement for QC"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_MEASURED = "not_measured"


class ValidationRuleType(Enum):
    """Types of validation rules"""
    RANGE = "range"          # Value must be within min/max
    RATIO = "ratio"          # Ratio between two measurements
    SYMMETRY = "symmetry"    # Left/right measurements should match
    DIFFERENCE = "difference"  # Absolute difference between measurements


@dataclass
class LocalizedString:
    """Localized display name"""
    en: str
    it: Optional[str] = None
    pt: Optional[str] = None
    es: Optional[str] = None
    fr: Optional[str] = None
    de: Optional[str] = None

    def get(self, lang: str = "en") -> str:
        """Get string in specified language, fallback to English"""
        return getattr(self, lang, None) or self.en


@dataclass
class MeasurementInstruction:
    """
    Instruction for computing a single measurement.

    Inspired by GarmentIQ's JSON measurement schema.
    """
    id: str                              # Unique identifier (e.g., "chest_width")
    name: str                            # Machine-readable name
    display_name: LocalizedString        # Human-readable names
    method: MeasurementMethod            # Calculation method
    landmarks: List[int]                 # Landmark IDs to use (usually 2)
    tolerance_mm: float                  # Acceptable tolerance for QC
    unit: str = "mm"                     # Output unit (mm, cm, inch)
    notes: Optional[str] = None          # Additional instructions
    fallback_landmarks: Optional[List[int]] = None  # Alternative if primary not visible
    min_confidence: float = 0.3          # Minimum landmark confidence required
    is_critical: bool = True             # Whether measurement is required for QC pass
    multiplier: float = 1.0              # Multiplier for derived measurements (e.g., 2x for circumference)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "id": self.id,
            "name": self.name,
            "display_name": {
                "en": self.display_name.en,
            },
            "method": self.method.value,
            "landmarks": self.landmarks,
            "tolerance_mm": self.tolerance_mm,
            "unit": self.unit,
            "min_confidence": self.min_confidence,
            "is_critical": self.is_critical,
            "multiplier": self.multiplier,
        }
        if self.display_name.it:
            result["display_name"]["it"] = self.display_name.it
        if self.display_name.pt:
            result["display_name"]["pt"] = self.display_name.pt
        if self.notes:
            result["notes"] = self.notes
        if self.fallback_landmarks:
            result["fallback_landmarks"] = self.fallback_landmarks
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "MeasurementInstruction":
        """Create from dictionary"""
        display_name = LocalizedString(**data.get("display_name", {"en": data["name"]}))
        return cls(
            id=data["id"],
            name=data["name"],
            display_name=display_name,
            method=MeasurementMethod(data["method"]),
            landmarks=data["landmarks"],
            tolerance_mm=data.get("tolerance_mm", 10.0),
            unit=data.get("unit", "mm"),
            notes=data.get("notes"),
            fallback_landmarks=data.get("fallback_landmarks"),
            min_confidence=data.get("min_confidence", 0.3),
            is_critical=data.get("is_critical", True),
            multiplier=data.get("multiplier", 1.0),
        )


@dataclass
class ValidationRule:
    """
    Rule for validating measurements.
    """
    rule_type: ValidationRuleType
    measurements: List[str]              # Measurement IDs involved
    condition: str                       # Human-readable condition
    threshold: float                     # Threshold value
    error_message: str                   # Message if validation fails
    is_warning: bool = False             # True = warning, False = error

    def to_dict(self) -> Dict:
        return {
            "rule_type": self.rule_type.value,
            "measurements": self.measurements,
            "condition": self.condition,
            "threshold": self.threshold,
            "error_message": self.error_message,
            "is_warning": self.is_warning,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ValidationRule":
        return cls(
            rule_type=ValidationRuleType(data["rule_type"]),
            measurements=data["measurements"],
            condition=data["condition"],
            threshold=data["threshold"],
            error_message=data["error_message"],
            is_warning=data.get("is_warning", False),
        )


@dataclass
class MeasurementInstructionSet:
    """
    Complete set of measurement instructions for a garment category.
    """
    schema_version: str
    category: str
    display_name: LocalizedString
    measurements: List[MeasurementInstruction]
    validation_rules: List[ValidationRule] = field(default_factory=list)
    notes: Optional[str] = None

    def get_measurement(self, measurement_id: str) -> Optional[MeasurementInstruction]:
        """Get a specific measurement instruction by ID"""
        for m in self.measurements:
            if m.id == measurement_id:
                return m
        return None

    def get_critical_measurements(self) -> List[MeasurementInstruction]:
        """Get all critical measurements (required for QC pass)"""
        return [m for m in self.measurements if m.is_critical]

    def to_dict(self) -> Dict:
        return {
            "schema_version": self.schema_version,
            "category": self.category,
            "display_name": {
                "en": self.display_name.en,
                "it": self.display_name.it,
                "pt": self.display_name.pt,
            },
            "measurements": [m.to_dict() for m in self.measurements],
            "validation_rules": [r.to_dict() for r in self.validation_rules],
            "notes": self.notes,
        }

    def save_json(self, filepath: Union[str, Path]) -> None:
        """Save to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved measurement instructions to {filepath}")

    @classmethod
    def from_dict(cls, data: Dict) -> "MeasurementInstructionSet":
        display_name = LocalizedString(**data.get("display_name", {"en": data["category"]}))
        measurements = [MeasurementInstruction.from_dict(m) for m in data["measurements"]]
        validation_rules = [ValidationRule.from_dict(r) for r in data.get("validation_rules", [])]

        return cls(
            schema_version=data["schema_version"],
            category=data["category"],
            display_name=display_name,
            measurements=measurements,
            validation_rules=validation_rules,
            notes=data.get("notes"),
        )

    @classmethod
    def load_json(cls, filepath: Union[str, Path]) -> "MeasurementInstructionSet":
        """Load from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


# =============================================================================
# DEFAULT MEASUREMENT INSTRUCTION SETS
# =============================================================================

TSHIRT_MEASUREMENTS = MeasurementInstructionSet(
    schema_version="1.0.0",
    category="tshirt",
    display_name=LocalizedString(
        en="T-Shirt",
        it="Maglietta",
        pt="Camiseta"
    ),
    measurements=[
        MeasurementInstruction(
            id="collar_width",
            name="Collar Width",
            display_name=LocalizedString(
                en="Collar Opening",
                it="Apertura Collo",
                pt="Abertura do Colarinho"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[2, 4],  # DeepFashion2: collar_left (idx 2) to collar_right (idx 4)
            tolerance_mm=5.0,
            notes="Measure straight across collar opening",
        ),
        MeasurementInstruction(
            id="shoulder_width",
            name="Shoulder Width",
            display_name=LocalizedString(
                en="Shoulder to Shoulder",
                it="Larghezza Spalle",
                pt="Largura dos Ombros"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[6, 24],  # DeepFashion2: left_shoulder_seam (idx 6) to right_shoulder_seam (idx 24)
            tolerance_mm=8.0,
            is_critical=True,
            notes="Measured at shoulder seam where sleeve attaches to body",
        ),
        MeasurementInstruction(
            id="chest_width",
            name="Chest Width",
            display_name=LocalizedString(
                en="Chest Width (Pit to Pit)",
                it="Larghezza Petto",
                pt="Largura do Peito"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[9, 19],  # DeepFashion2: left_armpit (idx 9) to right_armpit (idx 19)
            tolerance_mm=10.0,
            is_critical=True,
            notes="Measured at armpit level (pit to pit)",
        ),
        MeasurementInstruction(
            id="chest_circumference",
            name="Chest Circumference",
            display_name=LocalizedString(
                en="Chest Circumference",
                it="Circonferenza Petto",
                pt="Circunferência do Peito"
            ),
            method=MeasurementMethod.CIRCUMFERENCE_ESTIMATE,
            landmarks=[9, 19],  # DeepFashion2: left_armpit to right_armpit
            tolerance_mm=20.0,
            is_critical=False,
            multiplier=2.0,  # Double the width for flat-lay circumference
            notes="Estimated as 2x chest width for flat-lay",
        ),
        MeasurementInstruction(
            id="hem_width",
            name="Hem Width",
            display_name=LocalizedString(
                en="Bottom Hem Width",
                it="Larghezza Orlo",
                pt="Largura da Bainha"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[14, 16],  # DeepFashion2: hem_left (idx 14) to hem_right (idx 16)
            tolerance_mm=10.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="body_length",
            name="Body Length",
            display_name=LocalizedString(
                en="Body Length (HPS)",
                it="Lunghezza Corpo",
                pt="Comprimento do Corpo"
            ),
            method=MeasurementMethod.VERTICAL_PROJECTION,
            landmarks=[0, 15],  # DeepFashion2: neckline_center (idx 0) to hem_center (idx 15)
            tolerance_mm=15.0,
            is_critical=True,
            notes="High Point Shoulder to hem center",
        ),
        MeasurementInstruction(
            id="sleeve_length_left",
            name="Left Sleeve Length",
            display_name=LocalizedString(
                en="Sleeve Length (L)",
                it="Lunghezza Manica (S)",
                pt="Comprimento da Manga (E)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[6, 8],  # DeepFashion2: left_shoulder_seam (idx 6) to left_sleeve_end (idx 8)
            tolerance_mm=10.0,
            is_critical=True,
            notes="From shoulder seam to sleeve cuff",
        ),
        MeasurementInstruction(
            id="sleeve_length_right",
            name="Right Sleeve Length",
            display_name=LocalizedString(
                en="Sleeve Length (R)",
                it="Lunghezza Manica (D)",
                pt="Comprimento da Manga (D)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[24, 22],  # DeepFashion2: right_shoulder_seam (idx 24) to right_sleeve_end (idx 22)
            tolerance_mm=10.0,
            is_critical=True,
            notes="From shoulder seam to sleeve cuff",
        ),
        MeasurementInstruction(
            id="side_length_left",
            name="Left Side Length",
            display_name=LocalizedString(
                en="Side Seam Length (L)",
                it="Lunghezza Cucitura Laterale (S)",
                pt="Comprimento da Costura Lateral (E)"
            ),
            method=MeasurementMethod.VERTICAL_PROJECTION,
            landmarks=[9, 14],  # DeepFashion2: left_armpit (idx 9) to hem_left (idx 14)
            tolerance_mm=10.0,
            is_critical=False,
        ),
        MeasurementInstruction(
            id="side_length_right",
            name="Right Side Length",
            display_name=LocalizedString(
                en="Side Seam Length (R)",
                it="Lunghezza Cucitura Laterale (D)",
                pt="Comprimento da Costura Lateral (D)"
            ),
            method=MeasurementMethod.VERTICAL_PROJECTION,
            landmarks=[19, 16],  # DeepFashion2: right_armpit (idx 19) to hem_right (idx 16)
            tolerance_mm=10.0,
            is_critical=False,
        ),
    ],
    validation_rules=[
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["sleeve_length_left", "sleeve_length_right"],
            condition="abs(left - right) < threshold",
            threshold=15.0,
            error_message="Sleeve lengths differ by more than 15mm",
            is_warning=False,
        ),
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["side_length_left", "side_length_right"],
            condition="abs(left - right) < threshold",
            threshold=10.0,
            error_message="Side lengths differ by more than 10mm",
            is_warning=True,
        ),
        ValidationRule(
            rule_type=ValidationRuleType.RATIO,
            measurements=["chest_width", "hem_width"],
            condition="0.8 < chest/hem < 1.3",
            threshold=0.0,  # Not used for ratio
            error_message="Unusual chest-to-hem ratio detected",
            is_warning=True,
        ),
        ValidationRule(
            rule_type=ValidationRuleType.RANGE,
            measurements=["body_length"],
            condition="400 < value < 900",
            threshold=0.0,
            error_message="Body length outside typical range (40-90cm)",
            is_warning=True,
        ),
        ValidationRule(
            rule_type=ValidationRuleType.RANGE,
            measurements=["shoulder_width"],
            condition="300 < value < 700",
            threshold=0.0,
            error_message="Shoulder width outside typical range (30-70cm)",
            is_warning=True,
        ),
    ],
    notes="Standard T-shirt measurement specification based on ASTM D5219",
)


HOODIE_MEASUREMENTS = MeasurementInstructionSet(
    schema_version="1.0.0",
    category="hoodie",
    display_name=LocalizedString(
        en="Hoodie / Sweatshirt",
        it="Felpa con Cappuccio",
        pt="Moletom com Capuz"
    ),
    measurements=[
        MeasurementInstruction(
            id="hood_width",
            name="Hood Width",
            display_name=LocalizedString(
                en="Hood Width",
                it="Larghezza Cappuccio",
                pt="Largura do Capuz"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[3, 4],  # hood_left_outer, hood_right_outer
            tolerance_mm=15.0,
            is_critical=False,
        ),
        MeasurementInstruction(
            id="collar_width",
            name="Collar/Hood Opening",
            display_name=LocalizedString(
                en="Collar Opening",
                it="Apertura Collo",
                pt="Abertura do Colarinho"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[6, 7],
            tolerance_mm=10.0,
        ),
        MeasurementInstruction(
            id="shoulder_width",
            name="Shoulder Width",
            display_name=LocalizedString(
                en="Shoulder to Shoulder",
                it="Larghezza Spalle",
                pt="Largura dos Ombros"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[8, 9],  # shoulder_left_outer, shoulder_right_outer
            tolerance_mm=10.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="chest_width",
            name="Chest Width",
            display_name=LocalizedString(
                en="Chest Width",
                it="Larghezza Petto",
                pt="Largura do Peito"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[12, 13],  # armpit_left, armpit_right
            tolerance_mm=10.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="hem_width",
            name="Hem Width",
            display_name=LocalizedString(
                en="Bottom Width",
                it="Larghezza Fondo",
                pt="Largura da Bainha"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[30, 31],  # hem_left_corner, hem_right_corner
            tolerance_mm=10.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="body_length",
            name="Body Length",
            display_name=LocalizedString(
                en="Body Length",
                it="Lunghezza Corpo",
                pt="Comprimento do Corpo"
            ),
            method=MeasurementMethod.VERTICAL_PROJECTION,
            landmarks=[5, 32],  # collar_center, hem_center
            tolerance_mm=15.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="sleeve_length_left",
            name="Left Sleeve Length",
            display_name=LocalizedString(
                en="Sleeve Length (L)",
                it="Lunghezza Manica (S)",
                pt="Comprimento da Manga (E)"
            ),
            method=MeasurementMethod.POLYLINE,
            landmarks=[8, 15, 16],  # shoulder -> elbow -> cuff
            tolerance_mm=15.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="sleeve_length_right",
            name="Right Sleeve Length",
            display_name=LocalizedString(
                en="Sleeve Length (R)",
                it="Lunghezza Manica (D)",
                pt="Comprimento da Manga (D)"
            ),
            method=MeasurementMethod.POLYLINE,
            landmarks=[9, 19, 20],  # shoulder -> elbow -> cuff
            tolerance_mm=15.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="cuff_width_left",
            name="Left Cuff Width",
            display_name=LocalizedString(
                en="Cuff Width (L)",
                it="Larghezza Polsino (S)",
                pt="Largura do Punho (E)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[16, 17],
            tolerance_mm=5.0,
        ),
        MeasurementInstruction(
            id="cuff_width_right",
            name="Right Cuff Width",
            display_name=LocalizedString(
                en="Cuff Width (R)",
                it="Larghezza Polsino (D)",
                pt="Largura do Punho (D)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[20, 21],
            tolerance_mm=5.0,
        ),
        MeasurementInstruction(
            id="pocket_width",
            name="Pocket Width",
            display_name=LocalizedString(
                en="Kangaroo Pocket Width",
                it="Larghezza Tasca",
                pt="Largura do Bolso"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[22, 23],
            tolerance_mm=10.0,
            is_critical=False,
        ),
    ],
    validation_rules=[
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["sleeve_length_left", "sleeve_length_right"],
            condition="abs(left - right) < threshold",
            threshold=20.0,
            error_message="Sleeve lengths differ significantly",
        ),
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["cuff_width_left", "cuff_width_right"],
            condition="abs(left - right) < threshold",
            threshold=5.0,
            error_message="Cuff widths differ by more than 5mm",
        ),
    ],
)


TROUSERS_MEASUREMENTS = MeasurementInstructionSet(
    schema_version="1.0.0",
    category="trousers",
    display_name=LocalizedString(
        en="Trousers / Pants",
        it="Pantaloni",
        pt="Calças"
    ),
    measurements=[
        MeasurementInstruction(
            id="waist_width",
            name="Waist Width",
            display_name=LocalizedString(
                en="Waist Width",
                it="Larghezza Vita",
                pt="Largura da Cintura"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[170, 174],  # DeepFashion2 trousers: waist_left, waist_right
            tolerance_mm=10.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="waist_circumference",
            name="Waist Circumference",
            display_name=LocalizedString(
                en="Waist Circumference",
                it="Circonferenza Vita",
                pt="Circunferência da Cintura"
            ),
            method=MeasurementMethod.CIRCUMFERENCE_ESTIMATE,
            landmarks=[170, 174],  # DeepFashion2 trousers: waist_left, waist_right
            tolerance_mm=20.0,
            multiplier=2.0,
        ),
        MeasurementInstruction(
            id="left_length",
            name="Left Leg Length",
            display_name=LocalizedString(
                en="Leg Length (L)",
                it="Lunghezza Gamba (S)",
                pt="Comprimento da Perna (E)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[171, 177],  # DeepFashion2: left_length start, end
            tolerance_mm=15.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="right_length",
            name="Right Leg Length",
            display_name=LocalizedString(
                en="Leg Length (R)",
                it="Lunghezza Gamba (D)",
                pt="Comprimento da Perna (D)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[173, 180],  # DeepFashion2: right_length start, end
            tolerance_mm=15.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="hem_width_left",
            name="Left Leg Opening",
            display_name=LocalizedString(
                en="Leg Opening (L)",
                it="Apertura Gamba (S)",
                pt="Abertura da Perna (E)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[176, 177],  # DeepFashion2: left_hem_width
            tolerance_mm=8.0,
            is_critical=True,
        ),
        MeasurementInstruction(
            id="hem_width_right",
            name="Right Leg Opening",
            display_name=LocalizedString(
                en="Leg Opening (R)",
                it="Apertura Gamba (D)",
                pt="Abertura da Perna (D)"
            ),
            method=MeasurementMethod.EUCLIDEAN,
            landmarks=[179, 180],  # DeepFashion2: right_hem_width
            tolerance_mm=8.0,
            is_critical=True,
        ),
    ],
    validation_rules=[
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["left_length", "right_length"],
            condition="abs(left - right) < threshold",
            threshold=15.0,
            error_message="Leg lengths differ by more than 15mm",
        ),
        ValidationRule(
            rule_type=ValidationRuleType.SYMMETRY,
            measurements=["hem_width_left", "hem_width_right"],
            condition="abs(left - right) < threshold",
            threshold=8.0,
            error_message="Leg openings differ by more than 8mm",
        ),
    ],
)


# =============================================================================
# INSTRUCTION SET REGISTRY
# =============================================================================

DEFAULT_INSTRUCTION_SETS: Dict[str, MeasurementInstructionSet] = {
    "tshirt": TSHIRT_MEASUREMENTS,
    "short_sleeved_shirt": TSHIRT_MEASUREMENTS,
    "hoodie": HOODIE_MEASUREMENTS,
    "sweatshirt": HOODIE_MEASUREMENTS,
    "long_sleeved_shirt": HOODIE_MEASUREMENTS,
    "trousers": TROUSERS_MEASUREMENTS,
    "pants": TROUSERS_MEASUREMENTS,
    "jeans": TROUSERS_MEASUREMENTS,
}


def load_measurement_instructions(category: str,
                                  custom_path: Optional[Union[str, Path]] = None
                                  ) -> Optional[MeasurementInstructionSet]:
    """
    Load measurement instructions for a category.

    First checks for custom JSON file, then falls back to defaults.

    Args:
        category: Garment category
        custom_path: Optional path to custom instruction JSON

    Returns:
        MeasurementInstructionSet or None if not found
    """
    # Try custom path first
    if custom_path is not None:
        path = Path(custom_path)
        if path.exists():
            try:
                return MeasurementInstructionSet.load_json(path)
            except Exception as e:
                logger.warning(f"Failed to load custom instructions from {path}: {e}")

    # Normalize category
    normalized = category.lower().replace("-", "_").replace(" ", "_")

    # Return default if available
    return DEFAULT_INSTRUCTION_SETS.get(normalized)


def save_default_instructions(output_dir: Union[str, Path]) -> None:
    """
    Save all default instruction sets to JSON files.

    Useful for creating templates that can be customized.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_categories = set()
    for category, instruction_set in DEFAULT_INSTRUCTION_SETS.items():
        if instruction_set.category not in saved_categories:
            filepath = output_dir / f"{instruction_set.category}_measurements.json"
            instruction_set.save_json(filepath)
            saved_categories.add(instruction_set.category)
            logger.info(f"Saved {category} instructions to {filepath}")
