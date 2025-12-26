#!/usr/bin/env python3
"""Test tech pack extraction with OpenAI"""

import os
import json
import fitz  # PyMuPDF
from openai import OpenAI

# Load OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def extract_pdf_text(pdf_path):
    """Extract text from PDF"""
    doc = fitz.open(pdf_path)
    all_text = []
    for page in doc:
        all_text.append(page.get_text())
    return "\n".join(all_text)

def extract_techpack_data(text_content):
    """Use OpenAI to extract structured data"""
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""You are an expert tech pack analyzer for garment manufacturing. Extract ALL information from this tech pack document comprehensively.

Tech Pack Content:
{text_content}

Extract and return a JSON object with the following structure. Be THOROUGH - extract everything you can find:

{{
  "styleReference": "Style number/SKU",
  "productName": "Full product name/description",
  "season": "Season e.g. S/S 2025, F/W 2024",
  "designer": "Designer or brand name",
  "sampleSize": "Base sample size for measurements",
  "sizeRange": ["XS", "S", "M", "L", "XL", "XXL"],

  "colorways": [
    {{
      "name": "Color name",
      "pantone": "Pantone code e.g. 16-4114 TCX",
      "fabric": {{ "name": "Fabric name", "weight": "300GSM", "finish": "Potassium Sprayed" }},
      "thread": {{ "color": "DTM/color name", "type": "Cotton" }},
      "trim": {{ "description": "Drawcords", "color": "Same as self" }},
      "isMain": true
    }}
  ],

  "constructionDetails": [
    {{
      "area": "Waistband/Hemline/Pocket/etc",
      "description": "Double needle edgestitch along waistband seam",
      "stitchType": "Double needle/Single needle/Overlock/Coverstitch",
      "stitchCode": "A/B/C/I/K/L if mentioned",
      "notes": "Any additional notes"
    }}
  ],

  "sizeSpecifications": [
    {{
      "size": "M",
      "measurements": {{
        "waist": 14.5,
        "frontRise": 12.8,
        "backRise": 16,
        "length": 22.5,
        "thigh": 12.4,
        "inseam": 8.9,
        "legOpening": 11.5,
        "waistbandHeight": 2,
        "hemHeight": 1
      }}
    }}
  ],

  "measurementTolerances": {{
    "waist": 0.5,
    "frontRise": 0.25,
    "backRise": 0.25,
    "length": 0.5,
    "thigh": 0.5,
    "inseam": 0.5
  }},

  "artwork": [
    {{
      "type": "Flockprint/Embroidery/Screen print/etc",
      "placement": "Left thigh/Center front/etc",
      "width": "5.5 inches",
      "height": "4.5 inches",
      "pantones": ["5455 C"],
      "technique": "Flock print detail"
    }}
  ],

  "fabricMap": [
    {{ "zone": "Main fabric", "fabricType": "Cotton Fleece 300GSM", "areas": ["Body", "Waistband"] }},
    {{ "zone": "Trim fabric", "fabricType": "Self fabric", "areas": ["Drawcords"] }}
  ],

  "labels": [
    {{
      "type": "Main label/Care label/Size label",
      "width": "1.25 inch",
      "height": "2.75 inch",
      "material": "Black satin",
      "placement": "Center back waistband",
      "colors": ["19-0303 TCX", "11-0616 TCX"]
    }}
  ],

  "hangTags": [
    {{
      "width": "2.44 inch",
      "height": "1.5 inch",
      "material": "Textured cardstock paper, glossy embossed"
    }}
  ],

  "packaging": [
    {{
      "type": "Polybag",
      "material": "Clear plastic"
    }}
  ],

  "foldingInstructions": [
    {{ "step": 1, "description": "Step 1 description" }}
  ],

  "careInstructions": [
    {{
      "language": "English",
      "instructions": ["Machine wash cold", "Do not bleach", "Tumble dry low"]
    }}
  ],

  "billOfMaterials": [
    {{
      "category": "Trims",
      "description": "Item description",
      "supplier": "Supplier name"
    }}
  ],

  "materialComposition": [
    {{ "fiber": "Cotton", "percentage": 100 }}
  ]
}}

IMPORTANT:
- Extract ALL measurements from the spec sheet with their exact values
- Include ALL Pantone colors found in the document
- Extract ALL construction/stitching details
- Include care instructions in ALL languages found
- Be precise with measurements (keep original units)
- If information is not found, omit that field"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a technical expert in garment manufacturing and tech pack analysis. Extract complete and accurate structured data from tech pack documents."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=8000
    )

    return json.loads(response.choices[0].message.content)

def main():
    pdf_path = "/home/celso/projects/qa_dashboard/techpacks/Glass Factory- Sweatshorts Techpack Template.ai.pdf"

    print("=" * 60)
    print("TECH PACK EXTRACTION TEST")
    print("=" * 60)

    print("\n1. Extracting text from PDF...")
    text_content = extract_pdf_text(pdf_path)
    print(f"   Extracted {len(text_content)} characters")

    print("\n2. Sending to OpenAI for extraction...")
    result = extract_techpack_data(text_content)

    print("\n3. EXTRACTION RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Save to file
    output_path = "/home/celso/projects/qa_dashboard/techpacks/extracted_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to {output_path}")

if __name__ == "__main__":
    main()
