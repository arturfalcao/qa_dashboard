# Tech Pack Loader Feature

## Overview
The tech pack loader automatically extracts product specifications and measurements from uploaded tech pack files when creating or editing lots. This feature uses OpenAI's GPT-4 to intelligently parse various file formats and extract relevant information.

## Features
- **Automatic Data Extraction**: Extracts style reference, material composition, dye lot, quantities, and size specifications
- **Multiple Format Support**: Works with PDF, Excel, CSV, and image files
- **Smart Population**: Automatically fills lot form fields with extracted data
- **Permanent Storage**: Tech packs are stored and can be downloaded later
- **Size Measurement Tracking**: Extracted measurements can be cross-referenced with AI measurement results

## Setup

### 1. Add OpenAI API Key
Add your OpenAI API key to the `.env` file:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Run Database Migration
The migration has already been run, but for new installations:
```bash
cd apps/api
pnpm run migration:run
```

## Usage

### Uploading a Tech Pack

#### When Creating a New Lot:
1. Fill in the lot details as usual
2. In the "Tech Pack Upload" section, click "Choose File"
3. Select your tech pack file (PDF, Excel, CSV, or image)
4. Complete the lot creation
5. The tech pack will be automatically processed after the lot is created

#### When Editing an Existing Lot:
1. Open the lot edit form
2. In the "Tech Pack Upload" section, click "Choose File"
3. Select your tech pack file
4. Click "Upload & Process Tech Pack"
5. The extracted data will automatically populate the form fields
6. Review and save the changes

### Viewing Tech Pack Data
- The tech pack status is displayed in the lot form
- Size specifications are shown in an expandable section
- Original tech pack files can be downloaded using the "Download Tech Pack" button

## API Endpoints

### Upload Tech Pack
```
POST /lots/:id/tech-pack
Content-Type: multipart/form-data
```

### Get Tech Pack Data
```
GET /lots/:id/tech-pack
```

### Download Tech Pack
```
GET /lots/:id/tech-pack/download
```

## Extracted Information

The system extracts:
- **Style Reference/SKU**: Product identification codes
- **Material Composition**: Fiber types and percentages (e.g., 80% Cotton, 20% Polyester)
- **Dye Lot**: Dye batch identifiers for color consistency
- **Production Quantities**: Total units to be produced
- **Size Specifications**: Detailed measurements for each size (chest, length, sleeve, etc.)
- **Color Information**: Main colors, variants, Pantone references
- **Technical Specifications**: Fabric weight, construction details, wash care instructions

## Size Specifications Format

Size measurements are stored in a structured format:
```json
{
  "sizeSpecifications": [
    {
      "size": "S",
      "measurements": {
        "chest": 96,
        "length": 68,
        "sleeve": 60,
        "shoulder": 44
      }
    },
    {
      "size": "M",
      "measurements": {
        "chest": 102,
        "length": 71,
        "sleeve": 62,
        "shoulder": 46
      }
    }
  ]
}
```

## Notes

### PDF Support
Currently, PDFs are processed using OpenAI's text analysis. For complex PDFs with images and tables, the system provides a template response. For production use, consider integrating:
- PDF to image conversion service
- OCR capabilities
- Alternative PDF parsing libraries

### Best Practices
1. **Clear Tech Packs**: Use tech packs with clear, structured information
2. **Standard Formats**: Excel or CSV files work best for structured data
3. **Image Quality**: For image-based tech packs, ensure good resolution and clarity
4. **Review Extracted Data**: Always review the automatically extracted information before saving

### Troubleshooting

**Issue**: "OpenAI API key not configured"
**Solution**: Add your OpenAI API key to the `.env` file

**Issue**: "Failed to parse PDF file"
**Solution**: PDF parsing is simplified in the current implementation. The system will still process the file but may provide template data.

**Issue**: "Invalid file type"
**Solution**: Ensure you're uploading supported formats: PDF, Excel (.xlsx, .xls), CSV, or images (JPG, PNG)

## Future Enhancements
- Advanced PDF parsing with OCR
- Machine learning model training for specific client formats
- Automatic validation against historical data
- Integration with AI measurement validation
- Batch tech pack processing