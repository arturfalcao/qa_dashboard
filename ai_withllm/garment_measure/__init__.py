"""
Garment Measurement System
High-precision automated garment measurement pipeline with sub-2mm accuracy targets.
"""

from .calibration_tool import CalibrationTool
from .segmentation import GarmentSegmenter
from .classifier import GarmentClassifier
from .landmarks import LandmarkDetector
from .measurement import MeasurementCalculator
from .overlay import OverlayGenerator
from .pipeline import Pipeline

__version__ = '1.0.0'
__author__ = 'Pack & Polish QA'

__all__ = [
    'CalibrationTool',
    'GarmentSegmenter',
    'GarmentClassifier',
    'LandmarkDetector',
    'MeasurementCalculator',
    'OverlayGenerator',
    'Pipeline'
]