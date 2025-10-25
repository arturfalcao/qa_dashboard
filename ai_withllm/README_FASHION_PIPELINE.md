# Fashion Analysis Pipeline with HRNet

A complete pipeline for fashion image analysis that combines HRNet-based landmark detection with advanced background removal.

## Features

- **Fashion Landmark Detection**: Uses HRNet trained on DeepFashion2 dataset to detect up to 294 keypoints on garments
- **Background Removal**: Removes background using U2-Net models optimized for clothing
- **Garment Classification**: Automatically identifies garment types (shirts, dresses, trousers, etc.)
- **Combined Visualization**: Creates images with landmarks overlaid on transparent backgrounds

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Download the HRNet model:
   - Place `pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth` in the `models/` directory
   - This model is trained specifically for fashion landmark detection

## Usage

### Quick Demo

Run the demo script with a sample image:
```bash
python demo_fashion_pipeline.py
```

Or with your own image:
```bash
python demo_fashion_pipeline.py --image path/to/your/image.jpg --output results/
```

### Command Line Interface

Process a single image:
```bash
python fashion_pipeline.py input_image.jpg --output output_dir/
```

Batch process multiple images:
```bash
python fashion_pipeline.py input_dir/ --output output_dir/ --batch
```

### Python API

```python
from fashion_pipeline import FashionAnalysisPipeline

# Initialize pipeline
pipeline = FashionAnalysisPipeline(
    model_path="models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
    bg_model="u2net_cloth_seg",
    device="cuda"  # or "cpu"
)

# Process image
results = pipeline.process_image(
    "input_image.jpg",
    output_dir="output/",
    visualize=True,
    remove_background=True,
    detect_landmarks=True,
    confidence_threshold=0.3
)

# Access results
print(f"Detected {results['landmarks']['num_detected']} landmarks")
print(f"Garment category: {results['landmarks']['category']}")
```

## Pipeline Architecture

### Components

1. **HRNet Landmark Detector** (`hrnet_landmark_detector.py`)
   - High-Resolution Network for pose estimation
   - Trained on DeepFashion2 dataset
   - Detects 294 fashion-specific keypoints
   - Supports 13 garment categories

2. **Background Remover** (from `ai_mesurement/background_removal.py`)
   - U2-Net based segmentation
   - Multiple model options (u2net, u2net_cloth_seg, etc.)
   - Alpha matting for smooth edges
   - Transparent or custom background support

3. **Fashion Pipeline** (`fashion_pipeline.py`)
   - Combines landmark detection and background removal
   - Multiple output formats
   - Batch processing support
   - Comprehensive metadata generation

## Output Files

For each processed image, the pipeline generates:

- `*_landmarks.jpg`: Original image with detected landmarks
- `*_no_bg.png`: Image with transparent background
- `*_white_bg.jpg`: Image with white background
- `*_clean_landmarks.jpg`: Landmarks on white background
- `*_final.png`: Final composite with landmarks on transparent background
- `*_metadata.json`: Processing metadata and statistics

## Garment Categories

The model can detect landmarks for:

- Short-sleeved shirts (25 points)
- Long-sleeved shirts (33 points)
- Short-sleeved outerwear (31 points)
- Long-sleeved outerwear (39 points)
- Vests (15 points)
- Sling tops (15 points)
- Shorts (10 points)
- Trousers (14 points)
- Skirts (8 points)
- Short-sleeved dresses (29 points)
- Long-sleeved dresses (37 points)
- Vest dresses (19 points)
- Sling dresses (19 points)

## Configuration Options

### Background Removal Models

- `u2net`: General purpose segmentation
- `u2netp`: Lightweight version
- `u2net_human_seg`: Optimized for human/clothing
- `u2net_cloth_seg`: Specifically for cloth segmentation
- `silueta`: Alternative cloth model

### Processing Parameters

- `confidence_threshold`: Minimum confidence for landmark detection (0.0-1.0)
- `use_alpha_matting`: Enable edge refinement
- `background_color`: RGB tuple or None for transparent

## Performance Tips

1. **GPU Usage**: Use CUDA-enabled GPU for faster processing
2. **Batch Processing**: Process multiple images together for efficiency
3. **Model Selection**: Use `u2net_cloth_seg` for best clothing results
4. **Image Resolution**: Input images are automatically resized to 384x288 for HRNet

## Troubleshooting

### Missing Model File
If the HRNet model is not found:
- Ensure `pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth` is in the `models/` directory
- The pipeline will still run but landmark detection will use random weights

### CUDA/GPU Issues
If GPU is not available:
- The pipeline automatically falls back to CPU
- Processing will be slower but still functional

### Memory Issues
For large batches or high-resolution images:
- Process images in smaller batches
- Reduce image resolution before processing
- Use the lightweight `u2netp` background model

## Examples

### Process with specific background model:
```bash
python fashion_pipeline.py image.jpg --bg-model u2net_human_seg
```

### Skip background removal:
```bash
python fashion_pipeline.py image.jpg --no-background
```

### Skip landmark detection:
```bash
python fashion_pipeline.py image.jpg --no-landmarks
```

### Adjust landmark confidence:
```bash
python fashion_pipeline.py image.jpg --confidence 0.5
```

## Citation

This pipeline is based on:
- [HRNet for Fashion Landmark Estimation](https://github.com/svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch)
- [Rembg Background Removal](https://github.com/danielgatis/rembg)

## License

Please refer to the individual component licenses:
- HRNet: MIT License
- Rembg: MIT License
- U2-Net: Apache 2.0 License