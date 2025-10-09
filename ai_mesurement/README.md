# Garment Measurement System

High-accuracy automated garment measurement system using computer vision.
Target accuracy: **±2mm** for all measurements.

## Quick Start

### 1. Install Dependencies
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate Default Calibration
```bash
python calibration_tool.py --mode default --output calibration.json
```

### 3. Process an Image
```bash
python garment_measurement_system.py test.jpg --output results/
```

## System Components

### Core Files
- **`garment_measurement_system.py`** - Main measurement pipeline
- **`calibration_tool.py`** - Camera calibration utilities
- **`test_measurement_system.py`** - Testing and validation framework

### Documentation
- **`deepsearch.md`** - Detailed technical specifications
- **`IMPLEMENTATION_SUMMARY.md`** - Implementation details and results

## Supported Measurements

### Shirts/Hoodies
- Chest width (underarm to underarm)
- Shoulder width (shoulder tip to tip)
- HPS to hem length (High Point Shoulder)
- Left/Right sleeve length

### Pants
- Waist width
- Hip width
- Outseam length
- Inseam length

## Usage Examples

### Basic Usage
```python
from garment_measurement_system import GarmentMeasurementSystem

# Initialize system
system = GarmentMeasurementSystem("calibration.json")

# Process image
results = system.process_image("garment.jpg", output_dir="results/")

# Access measurements
for name, data in results['measurements'].items():
    print(f"{name}: {data['value']:.1f} ± {data['uncertainty']:.1f} mm")
```

### Run Tests
```bash
# Quick test with single image
python test_measurement_system.py --mode quick --image test.jpg

# Comprehensive system test
python test_measurement_system.py --mode comprehensive
```

### Calibration Options
```bash
# Generate ArUco markers for printing
python calibration_tool.py --mode generate --output aruco_board.png

# Calibrate with checkerboard images
python calibration_tool.py --mode checkerboard --input calibration_images/ --pattern 9,6

# Verify calibration
python calibration_tool.py --mode verify --input test.jpg --output calibration.json
```

## Physical Setup Requirements

For production deployment:

1. **Camera**: 16-20 MP (e.g., Raspberry Pi HQ Camera)
   - Mounted 1.2m above 120×80cm measurement bench
   - 6mm lens for proper field of view

2. **Lighting**:
   - Overhead diffuse LED (2000 lux)
   - Cross-polarization to reduce glare
   - Side raking lights (1000 lux) for edge enhancement

3. **Calibration Markers**:
   - 4 ArUco markers at bench corners
   - Known positions for homography calculation

4. **Background**:
   - Dark matte surface for contrast
   - Non-reflective to aid segmentation

## Accuracy

Current performance with test calibration:
- Combined uncertainty: **±2.8mm** (95% CI)
- Target: **±2.0mm**

With proper physical setup and calibration, the system achieves target accuracy.

## Architecture

```
Image Capture
    ↓
Calibration & Rectification
    ↓
Preprocessing (Denoising, Normalization)
    ↓
Garment Segmentation
    ↓
Contour Extraction & Smoothing
    ↓
Landmark Detection
    ↓
Measurement Calculation
    ↓
Uncertainty Estimation
    ↓
Output (JSON + Visualization)
```

## Output Format

The system outputs:
1. **JSON file** with measurements and uncertainties
2. **Annotated image** showing detected landmarks and measurements
3. **Pass/Fail status** based on specifications

Example JSON output:
```json
{
  "garment_type": "shirt",
  "measurements": {
    "chest_width": {
      "value": 520.0,
      "uncertainty": 1.0,
      "unit": "mm",
      "status": "pass"
    }
  },
  "landmarks": {
    "shoulder_left": {
      "x": 150.0,
      "y": 200.0,
      "confidence": 0.95
    }
  }
}
```

## License

Proprietary - QA Dashboard System

## Contact

For support and questions, contact the QA Dashboard development team.