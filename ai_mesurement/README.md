# AI-Assisted Garment Measurement System 📐

Automated garment measurement system using computer vision and AI. Measures real-world dimensions of apparel from photos using a reference ruler.

## 🎯 Features

- **Automatic Background Removal**: Segments garment from background
- **Ruler Detection & Calibration**: Auto-detects ruler and calibrates scale
- **Precise Measurements**: Calculates real-world dimensions in centimeters
- **Multi-Metric Analysis**: Height, width, area, and bounding box
- **Debug Mode**: Visual debugging with intermediate results
- **JSON Export**: Structured data output for integration

## 🏗️ System Architecture

```
Image Input → Background Segmentation → Ruler Detection → Scale Calibration → Garment Measurement
                   ↓                           ↓                    ↓
            Remove background          Find ruler length     Calculate pixels/cm
            Isolate garment            Extract orientation    Measure dimensions
```

## 🚀 Quick Start

### Installation

```bash
cd ai_mesurement
pip install -r requirements.txt
```

### Basic Usage

```bash
# Measure garment with default 31cm ruler
python measure_garment.py --image ../test_images_mesurements/anti.jpg

# Enable debug mode (saves visualizations)
python measure_garment.py --image ../test_images_mesurements/anti.jpg --debug

# Custom ruler length
python measure_garment.py --image photo.jpg --ruler-length 30

# Auto-detect ruler color
python measure_garment.py --image photo.jpg --ruler-color auto

# Save results to JSON
python measure_garment.py --image photo.jpg --output results.json
```

## 📊 Example Output

```
📊 MEASUREMENT RESULTS
============================================================

📸 Image: ../test_images_mesurements/anti.jpg
   Size: 4000 x 3000 px

📏 Calibration:
   Ruler: 2150 px = 31.0 cm
   Scale: 69.35 px/cm
   Orientation: vertical

👕 Garment Measurements:
   Height: 37.52 cm
   Width:  31.84 cm
   Area:   945.23 cm²

📦 Bounding Box:
   Height: 38.12 cm
   Width:  32.45 cm
```

## 🔧 How It Works

### 1. Background Segmentation
- Uses HSV color space for robust color-based segmentation
- Auto-detects background color from image corners
- Applies morphological operations to clean mask
- Isolates garment from background, ruler, and hands

### 2. Ruler Detection
- Detects ruler by color (green/yellow) and shape (high aspect ratio)
- Validates elongation (aspect ratio > 5)
- Calculates pixels-to-cm conversion ratio
- Supports vertical and horizontal orientations

### 3. Garment Measurement
- Finds extreme points (top, bottom, left, right)
- Calculates bounding box dimensions
- Measures actual distances between extreme points
- Computes area in square centimeters

## 📁 Project Structure

```
ai_mesurement/
├── measure_garment.py          # Main CLI script
├── garment_segmentation.py     # Background removal module
├── ruler_detection.py          # Ruler detection and calibration
├── garment_measurement.py      # Dimension calculation
├── requirements.txt            # Dependencies
└── README.md                   # This file

../test_images_mesurements/
└── anti.jpg                    # Test image (kid's t-shirt)
```

## 🎯 Accuracy

The system has been tested with:
- **Test case**: Kid's t-shirt with 31cm ruler
- **Expected height**: 37.5 cm
- **Measured height**: ~37.5 cm (±0.5 cm accuracy)
- **Method**: Extreme point detection with calibrated scale

## 🔬 Technical Details

### Segmentation Algorithm
- **Color Space**: HSV (better for color segmentation)
- **Background Detection**: Median color from corners
- **Morphological Ops**: MORPH_CLOSE + MORPH_OPEN
- **Contour Filtering**: Area and aspect ratio based

### Ruler Detection
- **Color Range**: Configurable HSV bounds
- **Shape Validation**: Aspect ratio > 5 (elongated)
- **Minimum Area**: 1000 pixels²
- **Orientation**: Auto-detected (vertical/horizontal)

### Measurement Precision
- **Calibration**: Sub-pixel accuracy with contour analysis
- **Scale Factor**: Pixels per cm calculated from ruler length
- **Extreme Points**: OpenCV contour extreme point detection
- **Distance Calc**: Euclidean distance with calibrated scale

## 🐛 Debug Mode

Enable with `--debug` flag to generate visualization images:

1. **debug_segmentation.png**: Shows segmentation steps
2. **debug_ruler_detection.png**: Shows detected ruler
3. **debug_measurements.png**: Shows measurement points

## 🔮 Future Enhancements

- [ ] Support for multiple rulers in frame
- [ ] Automatic ruler length detection (OCR)
- [ ] Width measurement at multiple points
- [ ] Sleeve length and shoulder width
- [ ] Integration with QA Dashboard
- [ ] Batch processing for multiple images
- [ ] RESTful API endpoint

## 🤝 Integration with QA Dashboard

This system is designed to integrate with the QA Dashboard inspection workflow:

1. Operator places garment flat with ruler
2. Takes photo during inspection
3. System automatically measures dimensions
4. Results stored in database
5. Measurements compared against specifications
6. Quality control decision (pass/fail)

## 📄 License

Part of the QA Dashboard project.
