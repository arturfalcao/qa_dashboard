#!/bin/bash
# Quick start script for t-shirt annotation

echo "================================================"
echo "T-SHIRT DATASET ANNOTATION - QUICK START"
echo "================================================"
echo ""

# Check if labelme is installed
if ! command -v labelme &> /dev/null; then
    echo "❌ Labelme not found. Installing..."
    pip install labelme
    if [ $? -eq 0 ]; then
        echo "✅ Labelme installed successfully"
    else
        echo "❌ Failed to install labelme"
        exit 1
    fi
else
    echo "✅ Labelme is installed"
fi

echo ""
echo "Dataset Information:"
echo "  Location: $(pwd)/tshirt_dataset"
echo "  Total images: $(ls tshirt_dataset/images/*.jpg 2>/dev/null | wc -l)"
echo "  Keypoints per image: 21"
echo ""

echo "Starting labelme annotation tool..."
echo ""
echo "Annotation tips:"
echo "  - Follow keypoint order from TSHIRT_KEYPOINT_SCHEMA.md"
echo "  - Zoom in for precision"
echo "  - Press 'D' for next image"
echo "  - Press 'A' for previous image"
echo ""

read -p "Press ENTER to start annotation session..."

labelme tshirt_dataset/images --config labelme_tshirt_config.yaml

echo ""
echo "Annotation session ended."
echo ""
echo "To resume, run: ./annotation_quick_start.sh"
echo "To convert to COCO format, run: labelme2coco tshirt_dataset/images --output tshirt_dataset/annotations_completed.json"
