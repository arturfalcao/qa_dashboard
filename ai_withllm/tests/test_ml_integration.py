#!/usr/bin/env python3
"""
Test suite for ML model integrations using mocks.
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garment_measure.segmentation import GarmentSegmenter
from garment_measure.classifier import GarmentClassifier
from garment_measure.landmarks import LandmarkDetector


class TestSAMIntegration:
    """Test SAM integration with mocks."""

    @patch('garment_measure.segmentation.sam_model_registry')
    @patch('garment_measure.segmentation.SamPredictor')
    def test_sam_initialization(self, mock_predictor, mock_registry):
        """Test SAM model loads correctly."""
        # Setup mocks
        mock_model = MagicMock()
        mock_registry.__getitem__.return_value = mock_model

        # Initialize segmenter
        segmenter = GarmentSegmenter(use_sam=True, sam_checkpoint='test.pth')

        # Verify SAM was initialized
        assert segmenter.use_sam
        assert segmenter.sam_predictor is not None

    def test_opencv_fallback(self):
        """Test fallback to OpenCV when SAM unavailable."""
        segmenter = GarmentSegmenter(use_sam=False)

        # Create test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 50
        image[30:70, 30:70] = 200  # Add bright square

        # Segment
        mask, info = segmenter.segment(image)

        # Check results
        assert mask is not None
        assert info['method'] == 'opencv'
        assert 'quality_checks' in info

    @patch('garment_measure.segmentation.GarmentSegmenter.segment_sam_refine')
    def test_sam_refinement_on_qc_fail(self, mock_sam_refine):
        """Test SAM is called when QC fails."""
        # Setup mock
        refined_mask = np.zeros((100, 100), dtype=np.uint8)
        mock_sam_refine.return_value = (refined_mask, {'method': 'sam'})

        segmenter = GarmentSegmenter(use_sam=True)
        segmenter.sam_predictor = MagicMock()  # Fake SAM availability

        # Force QC failure by using small image
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Segment
        mask, info = segmenter.segment(image)

        # Verify SAM was called
        mock_sam_refine.assert_called_once()


class TestCLIPIntegration:
    """Test CLIP integration with mocks."""

    @patch('garment_measure.classifier.clip.load')
    def test_clip_initialization(self, mock_clip_load):
        """Test CLIP model loads correctly."""
        # Setup mocks
        mock_model = MagicMock()
        mock_preprocess = MagicMock()
        mock_clip_load.return_value = (mock_model, mock_preprocess)

        # Initialize classifier
        classifier = GarmentClassifier(use_clip=True)

        # Verify CLIP was initialized
        assert classifier.use_clip
        assert classifier.clip_model is not None

    def test_heuristic_fallback_low_confidence(self):
        """Test fallback to heuristic when CLIP confidence is low."""
        classifier = GarmentClassifier(use_clip=False, confidence_threshold=0.4)

        # Create test mask (tall = pants-like)
        mask = np.zeros((200, 100), dtype=np.uint8)
        mask[20:180, 20:80] = 255

        image = np.zeros((200, 100, 3), dtype=np.uint8)

        # Classify
        category, confidence, info = classifier.classify(image, mask)

        # Check heuristic was used
        assert info['method'] == 'heuristic'
        assert category in ['pants', 'shorts', 'dress']

    @patch('garment_measure.classifier.GarmentClassifier.classify_clip')
    def test_clip_with_fallback(self, mock_classify_clip):
        """Test CLIP classification with confidence-based fallback."""
        # Setup mock for low confidence
        mock_classify_clip.return_value = ('tshirt', 0.35, {'method': 'clip'})

        classifier = GarmentClassifier(use_clip=True, confidence_threshold=0.4)

        # Create test data
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Classify
        category, confidence, info = classifier.classify(image, mask)

        # Should fall back to heuristic
        assert 'fallback' in info
        assert info['fallback'] is True


class TestHRNetIntegration:
    """Test HRNet ONNX integration with mocks."""

    @patch('garment_measure.landmarks.ort.InferenceSession')
    def test_onnx_model_loading(self, mock_session):
        """Test ONNX model loads correctly."""
        # Setup mock
        mock_model = MagicMock()
        mock_session.return_value = mock_model

        # Mock input/output specs
        mock_input = MagicMock()
        mock_input.name = 'input'
        mock_input.shape = [1, 3, 256, 256]
        mock_model.get_inputs.return_value = [mock_input]

        mock_output = MagicMock()
        mock_output.name = 'output'
        mock_model.get_outputs.return_value = [mock_output]

        # Initialize detector
        detector = LandmarkDetector(model_path='test.onnx')

        # Verify model was loaded
        assert detector.model is not None
        assert detector.input_name == 'input'

    def test_heuristic_detection(self):
        """Test heuristic landmark detection works."""
        detector = LandmarkDetector()

        # Create test mask (T-shirt shape)
        mask = np.zeros((200, 150), dtype=np.uint8)
        # Body
        mask[50:150, 50:100] = 255
        # Sleeves
        mask[60:80, 20:50] = 255
        mask[60:80, 100:130] = 255

        image = np.zeros((200, 150, 3), dtype=np.uint8)

        # Detect landmarks
        landmarks = detector.detect(image, mask, 'tshirt')

        # Check some landmarks exist
        assert len(landmarks) > 0
        assert any('hem' in name for name in landmarks)

    @patch('garment_measure.landmarks.LandmarkDetector._infer_on_roi')
    def test_model_refinement(self, mock_infer):
        """Test model refines heuristic landmarks."""
        # Setup mock heatmaps
        mock_heatmaps = np.random.randn(8, 64, 64)
        mock_infer.return_value = (mock_heatmaps, (0, 0))

        detector = LandmarkDetector(conf_threshold=0.3)
        detector.model = MagicMock()  # Fake model availability

        # Create test data
        mask = np.zeros((200, 150), dtype=np.uint8)
        mask[50:150, 50:100] = 255
        image = np.zeros((200, 150, 3), dtype=np.uint8)

        # Detect with model
        landmarks = detector.detect(image, mask, 'tshirt')

        # Verify inference was called
        mock_infer.assert_called()


class TestPipelineIntegration:
    """Test full pipeline with ML models."""

    @patch('garment_measure.pipeline.GarmentSegmenter')
    @patch('garment_measure.pipeline.GarmentClassifier')
    @patch('garment_measure.pipeline.LandmarkDetector')
    def test_pipeline_with_models(self, mock_landmark, mock_classifier, mock_segmenter):
        """Test pipeline initializes with ML models."""
        from garment_measure.pipeline import Pipeline

        # Initialize with all models
        pipeline = Pipeline(
            calibration_path='calibration.json',
            use_sam=True,
            sam_checkpoint='sam.pth',
            use_clip=True,
            kp_model_path='hrnet.onnx'
        )

        # Verify models were initialized with correct params
        mock_segmenter.assert_called_with(use_sam=True, sam_checkpoint='sam.pth')
        mock_classifier.assert_called_with(use_clip=True)
        mock_landmark.assert_called_with(model_path='hrnet.onnx', use_hrnet=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
