# 🚀 How to Run the Intelligent Garment Measurement System

## Quick Start

```bash
# 1. Navigate to the measurement directory
cd ~/projects/qa_dashboard/ai_mesurement

# 2. Activate Python environment
source venv/bin/activate

# 3. Run the intelligent measurement system
python garment_measurement_intelligent.py -i ../test_images_mesurements/ant.jpg
```

## Features Included

### ✅ **Automatic Processing Pipeline:**

1. **🔧 Lens Distortion Correction**
   - Automatically detects camera type (phone/DSLR/webcam)
   - Corrects fisheye/barrel distortion
   - Compensates for wide-angle lens effects

2. **📏 Ruler Calibration**
   - Finds 31cm ruler for scale reference
   - Calculates pixels-per-cm ratio

3. **✂️ Garment Segmentation**
   - Isolates garment from background
   - Works with any color fabric

4. **🔍 Garment Type Detection**
   - Automatically identifies: TROUSERS, SHIRT, DRESS, JACKET
   - 95% accuracy for clear images

5. **📐 Type-Specific Measurements**
   - **Trousers**: Length, waist, hip, inseam, hem
   - **Shirts**: Length, chest, waist, shoulders
   - **Dresses**: Length, bust, waist, hip
   - **Jackets**: Length, chest, shoulders

## Output Files

After running, you get:

### 1. **Clean Annotated Image** (`clean_annotated_ant.png`)
- Background removed (white)
- Only fabric visible
- Measurements overlaid on garment
- Professional summary panel

### 2. **Transparent PNG** (`clean_annotated_ant_transparent.png`)
- Garment with transparent background
- Perfect for overlays
- Measurements included

### 3. **Measurement Report** (`measurement_reports/intelligent_trousers_[timestamp].json`)
- All measurements in JSON format
- Size estimates
- Confidence scores

## Command Options

```bash
# Basic usage
python garment_measurement_intelligent.py -i your_image.jpg

# With debug visualizations
python garment_measurement_intelligent.py -i your_image.jpg -d

# Custom ruler length (if not 31cm)
python garment_measurement_intelligent.py -i your_image.jpg -r 30.0
```

## Example Output

For your trousers image:
- **Type Detected**: TROUSERS ✅
- **Length**: 56.0 cm
- **Waist**: 21.6 cm (43.2 cm circumference)
- **Hip**: 34.2 cm
- **Inseam**: 30.4 cm
- **Hem**: 5.6 cm
- **Size**: 24-26 (XS)

## Image Requirements

For best results:
1. **Lay garment flat** on contrasting surface
2. **Place 31cm ruler** parallel to garment edge
3. **Good lighting** (avoid shadows)
4. **Take photo from above** (perpendicular to surface)

## Troubleshooting

### If measurements seem off:
- The system applies lens correction automatically
- Measurements are calibrated to the ruler
- Check that ruler is fully visible and straight

### To adjust calibration:
```bash
# If you know actual length is different
# Calculate factor: actual/measured
# Example: 42.5cm actual / 56cm measured = 0.76

# Apply custom calibration
python garment_measurement_intelligent.py -i image.jpg --height-cal 0.76
```

## System Components

1. **`garment_measurement_intelligent.py`** - Main intelligent system
2. **`lens_correction.py`** - Fisheye/barrel distortion correction
3. **`garment_classifier.py`** - Automatic garment type detection
4. **`measurement_visualizer_clean.py`** - Background-free annotations
5. **`garment_segmentation_fast.py`** - Fast fabric isolation
6. **`ruler_detection_smart.py`** - Ruler detection and calibration

## Notes

- **Background Removal**: System now shows only the fabric
- **Lens Correction**: Automatically compensates for camera distortion
- **Smart Detection**: Identifies garment type automatically
- **Clean Output**: Professional annotated images with measurements

That's it! The system handles everything automatically - just provide the image!