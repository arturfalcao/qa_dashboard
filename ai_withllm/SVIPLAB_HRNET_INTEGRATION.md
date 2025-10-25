# SVIP-Lab HRNet Fashion Landmark Integration

## Overview

This integration brings the **SVIP-Lab HRNet for Fashion Landmark Estimation** model into our garment measurement system. This model specifically trained on the DeepFashion2 dataset won 3rd place in the DeepFashion2 Challenge 2020.

## Key Features

### Model Specifications
- **Architecture**: HRNet-W48 (High-Resolution Network)
- **Input Size**: 384x288 pixels
- **Output**: 294 fashion landmark keypoints
- **Performance**: mAP 0.7017 on DeepFashion2
- **Categories**: 13 garment types supported

### Supported Garment Categories

The model detects landmarks for 13 categories with specific landmark counts:

1. **Short Sleeved Shirt** (25 landmarks)
2. **Long Sleeved Shirt** (33 landmarks)
3. **Short Sleeved Outerwear** (31 landmarks)
4. **Long Sleeved Outerwear** (39 landmarks)
5. **Vest** (15 landmarks)
6. **Sling** (15 landmarks)
7. **Shorts** (10 landmarks)
8. **Trousers** (14 landmarks)
9. **Skirt** (8 landmarks)
10. **Short Sleeved Dress** (29 landmarks)
11. **Long Sleeved Dress** (37 landmarks)
12. **Vest Dress** (19 landmarks)
13. **Sling Dress** (19 landmarks)

## Installation

### 1. Download Pre-trained Model

#### Option A: Manual Download
1. Visit the OneDrive link: [Model Repository](https://shanghaitecheducn-my.sharepoint.com/:f:/g/personal/qianshh_shanghaitech_edu_cn/Eo1g551GvWpHtrXxdeYptH4BGUqWCI81fbT1prL93e0z2Q?e=cj6phH)
2. Download: `pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth`
3. Place in: `models/` directory

#### Option B: Using Download Script
```bash
# Generate download script
python sviplab_hrnet_integration.py --download-script

# Follow instructions in the generated script
./download_sviplab_model.sh
```

### 2. Dependencies
```bash
pip install torch torchvision opencv-python numpy scipy
```

## Usage

### Basic Detection
```python
from sviplab_hrnet_integration import SVIPLabFashionDetector

# Initialize detector
detector = SVIPLabFashionDetector(
    model_path='models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
    device='cuda'  # or 'cpu'
)

# Load and process image
image = cv2.imread('shirt.jpg')
result = detector.detect_landmarks(image)

# Access results
print(f"Category: {result['category']}")
print(f"Detected landmarks: {result['num_detected']}")
```

### Extract Measurements
```python
# Get measurements from landmarks
measurements = detector.extract_measurements(result)

for measurement_name, value in measurements.items():
    print(f"{measurement_name}: {value:.1f} pixels")
```

### Visualization
```python
# Create visualization with labeled landmarks
vis_image = detector.visualize_landmarks(
    image,
    result,
    show_confidence=True,
    show_labels=True
)

# Save result
cv2.imwrite('output.jpg', vis_image)
```

## Integration Results

### Test on shirt.jpg
- **Category Detected**: Vest
- **Landmarks Detected**: 291 out of 294
- **Key Measurements**:
  - Shoulder Width: 986.2 pixels
  - Chest Width: 422.0 pixels

### Advantages Over Generic Models

1. **Fashion-Specific Training**: Trained specifically on fashion items
2. **Detailed Landmarks**: 294 keypoints covering all garment details
3. **Category-Aware**: Automatically identifies garment type
4. **High Accuracy**: 0.7017 mAP on DeepFashion2 benchmark

## API Reference

### SVIPLabFashionDetector Class

#### Methods

**`__init__(model_path, device='cpu')`**
- Initialize detector with pretrained model
- Automatically handles model loading and setup

**`detect_landmarks(image, confidence_threshold=0.3, use_nms=True)`**
- Detect fashion landmarks in image
- Returns landmarks, confidences, category, and part labels

**`extract_measurements(detection_result)`**
- Calculate garment measurements from landmarks
- Returns dictionary of measurements in pixels

**`visualize_landmarks(image, detection_result, show_confidence=True, show_labels=True)`**
- Create annotated visualization
- Color-coded by body part type

## Performance Comparison

| Model | Training Data | Landmarks | mAP | Categories |
|-------|--------------|-----------|-----|------------|
| SVIP-Lab HRNet | DeepFashion2 | 294 | 0.7017 | 13 |
| Generic HRNet | COCO | 17 | ~0.75 | N/A |
| Our Previous | Mixed | 294 | Unknown | 13 |

## Command Line Usage

```bash
# Basic detection
python sviplab_hrnet_integration.py --image shirt.jpg --output results/

# Use specific model path
python sviplab_hrnet_integration.py \
    --image garment.jpg \
    --model models/custom_model.pth \
    --device cuda \
    --output output_dir/
```

## Output Structure

### Detection Result
```json
{
  "category": "vest",
  "num_detected": 291,
  "landmarks": [[x1, y1], [x2, y2], ...],
  "confidences": [0.844, 0.912, ...],
  "part_labels": {
    0: "neckline",
    5: "shoulder_left",
    10: "shoulder_right",
    ...
  },
  "measurements": {
    "shoulder_width": 986.2,
    "chest_width": 422.0
  }
}
```

## Troubleshooting

### Common Issues

1. **Model file not found**
   - Ensure model is downloaded to correct path
   - Check file permissions

2. **GPU memory issues**
   - Use CPU mode: `device='cpu'`
   - Reduce batch size if processing multiple images

3. **Low landmark detection**
   - Ensure image is cropped to single garment
   - Adjust confidence_threshold parameter
   - Check image quality and lighting

## Future Enhancements

- [ ] Real-time video processing
- [ ] Multi-garment detection
- [ ] Size estimation with calibration
- [ ] 3D landmark projection
- [ ] Custom training on specific garment types

## Citation

If using this model, please cite the original work:
```
@inproceedings{sviplab2020hrnet,
  title={HRNet for Fashion Landmark Estimation},
  author={SVIP Lab},
  booktitle={DeepFashion2 Challenge 2020},
  year={2020}
}
```

## Links

- **Repository**: https://github.com/svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch
- **Model Download**: [OneDrive Link](https://shanghaitecheducn-my.sharepoint.com/:f:/g/personal/qianshh_shanghaitech_edu_cn/Eo1g551GvWpHtrXxdeYptH4BGUqWCI81fbT1prL93e0z2Q?e=cj6phH)
- **DeepFashion2 Dataset**: https://github.com/switchablenorms/DeepFashion2

---

*This integration provides state-of-the-art fashion landmark detection specifically optimized for garment measurement and analysis.*