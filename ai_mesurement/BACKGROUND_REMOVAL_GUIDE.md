# Background Removal for Garment Measurement System

## Overview

The garment measurement system now includes advanced background removal capabilities using U2-Net deep learning models via the `rembg` library. This feature significantly improves segmentation accuracy, especially for:

- Complex or cluttered backgrounds
- Dark garments on dark backgrounds
- Light garments on light backgrounds
- Patterned or textured backgrounds
- Poor lighting conditions

## Installation

### 1. Install Required Packages

```bash
# Activate virtual environment
source venv/bin/activate

# Install rembg with GPU support (recommended)
pip install rembg[gpu] pillow

# Or CPU-only version
pip install rembg pillow
```

### 2. Verify Installation

```bash
python -c "from background_removal import BackgroundRemover; print('✓ Background removal ready')"
```

## Usage

### Standalone Background Removal

#### Basic Usage

```bash
# Remove background and replace with white
venv/bin/python background_removal.py input.jpg --output output.png --bg-color 255 255 255

# Remove background (transparent PNG)
venv/bin/python background_removal.py input.jpg --output output.png

# Get binary mask only
venv/bin/python background_removal.py input.jpg --output mask.png --mask-only
```

#### Batch Processing

```bash
# Process entire directory
venv/bin/python background_removal.py input_dir/ --output output_dir/ --batch --bg-color 255 255 255
```

#### Model Options

```bash
# Use cloth-specific model (recommended for garments)
venv/bin/python background_removal.py input.jpg --model u2net_cloth_seg --output output.png

# Use human segmentation model
venv/bin/python background_removal.py input.jpg --model u2net_human_seg --output output.png

# Use general purpose model
venv/bin/python background_removal.py input.jpg --model u2net --output output.png
```

### Integrated with Measurement System

#### Enable Background Removal

```bash
# Use enhanced system with background removal
venv/bin/python enhanced_measurement_system.py test.jpg \
    --calibration calibration.json \
    --bg-removal \
    --model u2net_cloth_seg \
    --output results/
```

#### Compare Segmentation Methods

```bash
# Compare traditional vs background removal segmentation
venv/bin/python enhanced_measurement_system.py test.jpg \
    --calibration calibration.json \
    --bg-removal \
    --compare \
    --output comparison/
```

#### Save Intermediate Steps

```bash
# Save background-removed image for inspection
venv/bin/python enhanced_measurement_system.py test.jpg \
    --calibration calibration.json \
    --bg-removal \
    --save-intermediate \
    --output results/
```

## Python API

### BackgroundRemover Class

```python
from background_removal import BackgroundRemover
import cv2

# Initialize remover
remover = BackgroundRemover(
    model_name="u2net_cloth_seg",
    use_alpha_matting=True
)

# Remove background from image
image = cv2.imread("garment.jpg")
result = remover.remove_background(
    image,
    background_color=(255, 255, 255),  # White background
    output_path="output.png"
)

# Get binary mask
mask = remover.get_mask("garment.jpg")

# Batch processing
remover.batch_process(
    input_dir="images/",
    output_dir="processed/",
    file_pattern="*.jpg",
    background_color=(255, 255, 255)
)
```

### Enhanced Measurement System

```python
from enhanced_measurement_system import EnhancedGarmentMeasurementSystem

# Initialize with background removal
system = EnhancedGarmentMeasurementSystem(
    calibration_file="calibration.json",
    use_background_removal=True,
    bg_removal_model="u2net_cloth_seg"
)

# Process image
results = system.process_image(
    "garment.jpg",
    output_dir="results/",
    save_intermediate=True
)

# Compare segmentation methods
comparison = system.compare_segmentation_methods(
    "garment.jpg",
    output_dir="comparison/"
)
```

### Advanced Background Replacement

```python
from background_removal import BackgroundReplacementProcessor

processor = BackgroundReplacementProcessor()

# Replace with solid color
result = processor.replace_with_solid_color(
    "garment.jpg",
    color=(240, 240, 240),  # Light gray
    output_path="solid_bg.png"
)

# Replace with gradient
result = processor.replace_with_gradient(
    "garment.jpg",
    color1=(240, 240, 240),
    color2=(255, 255, 255),
    direction='vertical',
    output_path="gradient_bg.png"
)

# Replace with custom background image
result = processor.replace_with_image(
    foreground="garment.jpg",
    background="texture.jpg",
    output_path="custom_bg.png"
)
```

## Model Selection Guide

### Available Models

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| `u2net` | General purpose | Medium | High |
| `u2net_cloth_seg` | **Clothing/garments** | Fast | Very High |
| `u2net_human_seg` | Clothing on people | Fast | High |
| `u2netp` | Resource-constrained | Very Fast | Medium |
| `silueta` | Alternative cloth model | Medium | High |

### Recommendations

- **Production garment measurement**: Use `u2net_cloth_seg` (optimized for flat clothing)
- **Fashion photography**: Use `u2net_human_seg` (clothing worn by models)
- **Quick prototyping**: Use `u2netp` (faster but lower quality)
- **General use**: Use `u2net` (balanced performance)

## Configuration Options

### Alpha Matting Parameters

Fine-tune edge quality with alpha matting parameters:

```python
result = remover.remove_background(
    image,
    alpha_matting_foreground_threshold=240,  # 0-255, higher = stricter foreground
    alpha_matting_background_threshold=10,   # 0-255, lower = stricter background
    alpha_matting_erode_size=10              # Erosion kernel size
)
```

**Tips**:
- Increase `foreground_threshold` for cleaner foreground (may lose fine details)
- Decrease `background_threshold` for complete background removal (may affect edges)
- Adjust `erode_size` to control edge smoothness (larger = smoother but less precise)

## Performance Considerations

### GPU vs CPU

- **GPU (CUDA)**: ~10-20x faster, requires NVIDIA GPU and CUDA libraries
- **CPU**: Slower but works everywhere, suitable for offline processing

### Memory Usage

- U2-Net model: ~176 MB download, ~500 MB RAM during inference
- Typical processing: 2-3 seconds per image (GPU), 10-30 seconds (CPU)

### Optimization Tips

1. **Batch Processing**: Process multiple images in one session to avoid model reload
2. **Image Resizing**: Resize very large images before processing
3. **Model Caching**: Models are cached in `~/.u2net/` after first download
4. **Session Reuse**: Keep `BackgroundRemover` instance for multiple images

```python
# Efficient batch processing
remover = BackgroundRemover(model_name="u2net_cloth_seg")

for image_path in image_list:
    # Reuses loaded model
    result = remover.remove_background(image_path)
```

## Troubleshooting

### CUDA/GPU Warnings

If you see CUDA warnings but processing still works, it's using CPU fallback (expected behavior if CUDA not installed):

```
[E:onnxruntime:Default] Failed to load library libonnxruntime_providers_cuda.so
```

**Solution**: Ignore if CPU performance is acceptable, or install CUDA toolkit for GPU acceleration.

### Out of Memory

For very large images:

```python
# Resize before processing
image = cv2.imread("large_image.jpg")
h, w = image.shape[:2]
if h > 4000 or w > 4000:
    scale = 4000 / max(h, w)
    image = cv2.resize(image, None, fx=scale, fy=scale)
```

### Poor Edge Quality

Adjust alpha matting parameters:

```python
# Smoother edges
result = remover.remove_background(
    image,
    alpha_matting_foreground_threshold=220,  # Lower
    alpha_matting_erode_size=15              # Larger
)
```

## Integration Examples

### Example 1: Preprocessing Pipeline

```python
# Complete preprocessing pipeline
def preprocess_garment(image_path, output_path):
    # Remove background
    remover = BackgroundRemover(model_name="u2net_cloth_seg")
    clean_image = remover.remove_background(
        image_path,
        background_color=(245, 245, 245)
    )

    # Save intermediate
    cv2.imwrite("temp_clean.jpg", cv2.cvtColor(clean_image, cv2.COLOR_RGB2BGR))

    # Measure on cleaned image
    system = GarmentMeasurementSystem(calibration_file="calibration.json")
    results = system.process_image("temp_clean.jpg", output_dir=output_path)

    return results
```

### Example 2: Quality Control

```python
# Compare with and without background removal
def quality_comparison(image_path):
    # Without background removal
    system_basic = GarmentMeasurementSystem("calibration.json")
    results_basic = system_basic.process_image(image_path)

    # With background removal
    system_enhanced = EnhancedGarmentMeasurementSystem(
        "calibration.json",
        use_background_removal=True
    )
    results_enhanced = system_enhanced.process_image(image_path)

    # Compare measurements
    for key in results_basic['measurements']:
        val_basic = results_basic['measurements'][key]['value']
        val_enhanced = results_enhanced['measurements'][key]['value']
        diff = abs(val_basic - val_enhanced)
        print(f"{key}: {val_basic:.1f} vs {val_enhanced:.1f} (diff: {diff:.1f}mm)")
```

### Example 3: Automated Quality Check

```python
def auto_select_method(image_path):
    """Automatically choose best segmentation method"""

    system = EnhancedGarmentMeasurementSystem(
        use_background_removal=True
    )

    # Compare methods
    masks = system.compare_segmentation_methods(image_path)

    # Calculate coverage for each method
    coverages = {
        method: np.count_nonzero(mask) / mask.size
        for method, mask in masks.items()
    }

    # Use background removal if traditional gives poor result
    if coverages['traditional'] < 0.3 or coverages['traditional'] > 0.8:
        print("Using background removal (traditional segmentation unreliable)")
        return 'background_removal'
    else:
        print("Using traditional segmentation (sufficient quality)")
        return 'traditional'
```

## Best Practices

1. **Test with sample images** before production deployment
2. **Use cloth-specific model** (`u2net_cloth_seg`) for best garment results
3. **Save intermediate results** during development for debugging
4. **Compare methods** on challenging images to validate improvement
5. **Monitor performance** - background removal adds 2-30s per image
6. **Batch process** when possible to amortize model loading time

## Future Enhancements

Potential improvements for the background removal system:

- [ ] Fine-tuned model on custom garment dataset
- [ ] Hybrid segmentation combining traditional + AI methods
- [ ] Real-time processing with optimized models
- [ ] Automatic method selection based on image analysis
- [ ] Edge refinement post-processing
- [ ] Support for additional segmentation models

## References

- [rembg GitHub](https://github.com/danielgatis/rembg)
- [U2-Net Paper](https://arxiv.org/abs/2005.09007)
- [Background Matting Techniques](https://en.wikipedia.org/wiki/Alpha_compositing)
