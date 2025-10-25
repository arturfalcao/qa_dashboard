# Background Removal - Quick Start Guide

## ⚡ Quick Commands

### 1. Simple Background Removal

```bash
# Remove background → white
venv/bin/python background_removal.py input.jpg --output result.png --bg-color 255 255 255

# Remove background → transparent
venv/bin/python background_removal.py input.jpg --output result.png

# Get mask only
venv/bin/python background_removal.py input.jpg --output mask.png --mask-only
```

### 2. Batch Processing

```bash
# Process entire folder
venv/bin/python background_removal.py images/ --output cleaned/ --batch --bg-color 255 255 255
```

### 3. Enhanced Measurements

```bash
# Measure with background removal
venv/bin/python enhanced_measurement_system.py garment.jpg \
    --calibration calibration.json \
    --bg-removal \
    --output results/

# Compare segmentation methods
venv/bin/python enhanced_measurement_system.py garment.jpg \
    --bg-removal \
    --compare \
    --output comparison/
```

## 🎯 Model Selection

```bash
# For flat garments (RECOMMENDED)
--model u2net_cloth_seg

# For worn clothing
--model u2net_human_seg

# General purpose
--model u2net
```

## 🐍 Python Quick Code

```python
# Basic usage
from background_removal import BackgroundRemover

remover = BackgroundRemover(model_name="u2net_cloth_seg")
result = remover.remove_background("image.jpg", background_color=(255,255,255))

# Enhanced measurement
from enhanced_measurement_system import EnhancedGarmentMeasurementSystem

system = EnhancedGarmentMeasurementSystem(
    calibration_file="calibration.json",
    use_background_removal=True,
    bg_removal_model="u2net_cloth_seg"
)
results = system.process_image("garment.jpg", output_dir="results/")
```

## 📋 File Structure

```
ai_mesurement/
├── background_removal.py                    # Core module
├── enhanced_measurement_system.py          # Integration
├── BACKGROUND_REMOVAL_GUIDE.md            # Full docs
├── BACKGROUND_REMOVAL_QUICKSTART.md       # This file
└── BACKGROUND_REMOVAL_SUMMARY.md          # Completion summary
```

## ⚙️ Optimal Settings

```python
# For best garment results
remover = BackgroundRemover(
    model_name="u2net_cloth_seg",
    use_alpha_matting=True
)

result = remover.remove_background(
    image,
    alpha_matting_foreground_threshold=240,
    alpha_matting_background_threshold=10,
    alpha_matting_erode_size=10,
    background_color=(255, 255, 255)
)
```

## 🔧 Troubleshooting

**CUDA warnings?** → Normal, using CPU (slower but works)
**Slow processing?** → Expected on CPU, 10-30s per image
**Poor edges?** → Adjust alpha_matting parameters
**Out of memory?** → Resize image before processing

## 📚 More Info

- Full guide: `BACKGROUND_REMOVAL_GUIDE.md`
- Summary: `BACKGROUND_REMOVAL_SUMMARY.md`
- Test: `venv/bin/python test_background_removal.py`
