"""
Industrial Garment Landmark Detection System

A production-ready system for detecting landmarks on flat-lay garments,
inspired by:
- Kim et al. (2022): "Automatic Measurements of Garment Sizes Using Computer
  Vision, Deep Learning Models and Point Cloud Data"
- GarmentIQ (2025): Full pipeline for automated garment measurement

This system is optimized for industrial inspection benches with:
- Fixed overhead camera positioning
- Controlled lighting conditions
- Flat-lay garment presentation
- High accuracy requirements (1-2mm error tolerance)

Components:
- landmark_schemas: Defines landmark skeletons for each garment category
- measurement_instructions: JSON-based measurement definitions (GarmentIQ-style)
- hrnet_detector: HRNet-W48 based landmark detection with enhanced processing
- segmentation: Background removal and garment isolation
- measurement_engine: Physical measurement calculation with validation
- pipeline: End-to-end measurement pipeline
"""

from .landmark_schemas import (
    INDUSTRIAL_LANDMARK_SCHEMAS,
    get_schema_for_category,
    get_landmark_names,
    get_skeleton_connections,
)

from .measurement_instructions import (
    MeasurementInstruction,
    MeasurementInstructionSet,
    load_measurement_instructions,
)

__version__ = "1.0.0"
__author__ = "QA Dashboard Team"
