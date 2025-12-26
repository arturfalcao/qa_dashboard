#!/bin/bash

# Upload mock lot images to S3/MinIO using AWS CLI
# Make sure AWS CLI is configured with your MinIO/S3 credentials

set -e  # Exit on error

echo "=========================================="
echo "Upload Mock Images to S3"
echo "=========================================="
echo ""

# Configuration
IMAGES_DIR="mock_lot_images"
BUCKET="pp-photos"
ENDPOINT="http://localhost:9000"

# Check if images directory exists
if [ ! -d "$IMAGES_DIR" ]; then
    echo "✗ Error: $IMAGES_DIR directory not found"
    echo "Run generate_lot_images.py first to create mock images"
    exit 1
fi

# Count images
IMAGE_COUNT=$(ls -1 "$IMAGES_DIR"/*.jpg 2>/dev/null | wc -l)
echo "Found $IMAGE_COUNT images in $IMAGES_DIR"
echo ""

# Upload to S3
echo "Uploading images to S3..."
echo "Bucket: $BUCKET"
echo "Endpoint: $ENDPOINT"
echo ""

aws --endpoint-url=$ENDPOINT s3 sync $IMAGES_DIR/ s3://$BUCKET/mock_lot_images/ \
    --no-progress \
    --content-type "image/jpeg"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Upload complete!"
    echo "  Uploaded $IMAGE_COUNT images to s3://$BUCKET/mock_lot_images/"
else
    echo ""
    echo "✗ Upload failed"
    exit 1
fi

echo ""
echo "Note: Database records still reference 'mock_lot_images/' paths"
echo "Images are now accessible at: $ENDPOINT/$BUCKET/mock_lot_images/"
