# Changelog

## [2.0.0] - 2024-12-XX

### Added

#### Production ML Integrations
- **SAM Integration**: Segment Anything Model for refined segmentation
  - Automatic refinement when QC fails
  - Extreme points prompting for optimal masks
  - Graceful fallback to OpenCV baseline

- **CLIP Integration**: Zero-shot garment classification
  - Support for 8 garment types
  - Confidence-based fallback to heuristics
  - Normalized category output (top/pants/skirt/dress)

- **HRNet ONNX Integration**: Deep learning landmark detection
  - ROI-based inference for efficiency
  - Soft-argmax keypoint extraction
  - Per-point confidence fusion with heuristics

#### CLI Enhancements
- New flags: `--use_sam`, `--sam_checkpoint`, `--use_clip`, `--kp_model_path`
- Backward compatible - no flags means heuristics only
- Detailed logging for model usage

#### Testing
- Comprehensive test suite with mocks
- No heavy model downloads required for tests
- Coverage for all fallback scenarios

### Changed

- `segmentation.py`: Enhanced with SAM predictor and QC-triggered refinement
- `classifier.py`: Added CLIP model with text embedding cache
- `landmarks.py`: ONNX runtime integration with ROI inference
- `pipeline.py`: Extended CLI argument parsing
- `requirements.txt`: Added ML dependencies with platform-specific ONNX

### Fixed

- Device auto-detection for CUDA/CPU
- Graceful handling of missing models
- Memory-efficient ROI processing

### Compatibility

- Python 3.8+
- CUDA 11.x/12.x or CPU
- Backward compatible - existing code works unchanged

## [1.0.0] - Previous Version

Initial release with heuristic methods only.
