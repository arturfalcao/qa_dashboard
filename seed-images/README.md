# Seed Images

This directory should contain sample garment images for the mock data generator:

## Required Images:

### Normal Garment Images (8-10 images)
- `garment-1.jpg` - Clean t-shirt
- `garment-2.jpg` - Hoodie  
- `garment-3.jpg` - Jeans
- `garment-4.jpg` - Polo shirt
- `garment-5.jpg` - Jacket
- `garment-6.jpg` - Dress shirt
- `garment-7.jpg` - Sweater
- `garment-8.jpg` - Pants

### Defected Garment Images (4-6 images)
- `defect-stain.jpg` - Garment with visible stain
- `defect-stitching.jpg` - Poor stitching visible
- `defect-misprint.jpg` - Logo/text misalignment
- `defect-measurement.jpg` - Size/fit issues
- `defect-other.jpg` - Other visible defects

## Image Specifications:
- Format: JPG/JPEG
- Size: 400x400 to 800x800 pixels
- Quality: Good enough to see details
- Lighting: Well-lit, clear visibility

## Mock Generator Behavior:
The mock service will:
1. Randomly select from normal images for non-defective inspections
2. Randomly select from defect images for defective inspections  
3. Generate simple placeholder images if no files are found
4. Create presigned URLs for MinIO storage

## Note:
For the demo, the mock service generates simple colored squares with red dots to indicate defects if no actual images are provided.