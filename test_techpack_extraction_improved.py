#!/usr/bin/env python3
"""
Test improved tech pack extraction with GPT-4 Vision
This tests the same extraction logic as tech-pack.service.ts but in Python
"""

import os
import sys
import json
import subprocess
import tempfile
import base64
from pathlib import Path

# Load OpenAI API key from .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("OPENAI_API_KEY="):
                os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip()
                break

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "-q"])
    from openai import OpenAI

# Standard measurement schema (same as in tech-pack.service.ts)
STANDARD_MEASUREMENTS = {
    "front_length": "Front length from HPS to hem",
    "back_length": "Back length from HPS to hem",
    "cb_length": "Center back length",
    "cf_length": "Center front length",
    "side_length": "Side seam length",
    "sleeve_length": "Sleeve length from shoulder point",
    "sleeve_length_cb": "Sleeve length from center back neck",
    "sleeve_bicep": "Sleeve width at bicep/underarm",
    "sleeve_elbow": "Sleeve width at elbow",
    "sleeve_cuff": "Sleeve opening/cuff width",
    "sleeve_cuff_height": "Cuff/rib height",
    "chest_width": "Chest width 1\" below armhole",
    "bust_width": "Bust width at fullest point",
    "body_width": "Body width at sweep/hem",
    "waist_width": "Waist width",
    "hip_width": "Hip width",
    "hem_width": "Bottom hem width",
    "shoulder_width": "Shoulder to shoulder width (back)",
    "across_front": "Across front chest measurement",
    "across_back": "Across back measurement",
    "neck_width": "Neck opening width",
    "neck_depth_front": "Front neck drop from HPS",
    "neck_depth_back": "Back neck drop from HPS",
    "collar_height": "Collar/neckband height",
    "armhole_depth": "Armhole depth from shoulder",
    "armhole_width": "Armhole width/opening",
    "hem_height": "Hem/rib band height",
    "waist": "Waist measurement (pants)",
    "front_rise": "Front rise (crotch to waist)",
    "back_rise": "Back rise (crotch to waist)",
    "inseam": "Inseam length",
    "outseam": "Outseam length",
    "thigh_width": "Thigh width 1\" from crotch",
    "knee_width": "Knee width",
    "leg_opening": "Leg opening/hem width",
    "waistband_height": "Waistband height",
}


def convert_pdf_to_images(pdf_path: str, max_pages: int = 20) -> list[bytes]:
    """Convert PDF to images using pdftoppm"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf = Path(temp_dir) / "input.pdf"

        # Copy PDF to temp location
        with open(pdf_path, "rb") as f:
            temp_pdf.write_bytes(f.read())

        # Convert to PNG
        output_prefix = Path(temp_dir) / "page"
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", "-l", str(max_pages), str(temp_pdf), str(output_prefix)],
                check=True,
                capture_output=True,
                timeout=120
            )
        except subprocess.CalledProcessError as e:
            print(f"pdftoppm error: {e.stderr.decode()}")
            return []
        except FileNotFoundError:
            print("pdftoppm not found. Install poppler-utils.")
            return []

        # Read images
        images = []
        for png_file in sorted(Path(temp_dir).glob("*.png")):
            images.append(png_file.read_bytes())

        return images


def extract_with_vision(client: OpenAI, page_images: list[bytes], batch_size: int = 3) -> list[dict]:
    """Extract data using GPT-4 Vision"""
    all_extracted = []

    for i in range(0, len(page_images), batch_size):
        batch = page_images[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Processing batch {batch_num} (pages {i + 1}-{min(i + batch_size, len(page_images))})...")

        image_content = []
        for img in batch:
            b64 = base64.b64encode(img).decode()
            image_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
            })

        prompt = f"""You are an expert tech pack analyzer for garment manufacturing QC systems. Analyze these tech pack pages (pages {i + 1}-{min(i + batch_size, len(page_images))} of {len(page_images)}).

INSTRUCTIONS:
1. Extract ALL information visible in the document - be thorough and comprehensive
2. Translate ALL descriptive text to PORTUGUESE (Brazilian Portuguese)
3. Keep codes/references unchanged (SKUs, article numbers, Pantone codes, stitch codes, POM codes, size labels)
4. Keep numeric measurements exactly as shown with their units
5. PAY SPECIAL ATTENTION to measurement tables, tolerance tables, BOM tables, and folding/packing diagrams

Return a JSON object with these fields when applicable:

{{
  "styleReference": "style number, SKU, article number",
  "productName": "product name or description",
  "productType": "type of garment (JACKET, PANTS, SHIRT, etc.)",
  "season": "season or collection",
  "brand": "brand name",
  "designer": "designer or manufacturer name",
  "revision": "document revision number",
  "date": "document date",

  "colorways": [{{"name": "nome da cor", "colorCode": "código", "pantone": "código Pantone", "hex": "#RRGGBB"}}],

  "sizeRange": ["all size labels found"],

  "pointsOfMeasure": [
    {{
      "pomCode": "código POM (ex: LT018, CH002B)",
      "name": "nome da medida exatamente como mostrado",
      "description": "descrição de como medir",
      "tolerancePlus": "número",
      "toleranceMinus": "número",
      "category": "categoria"
    }}
  ],

  "sizeSpecifications": [
    {{
      "size": "size label exactly as shown",
      "measurements": {{
        "EXACT_MEASUREMENT_NAME_FROM_DOCUMENT": "value as number"
      }}
    }}
  ],
  "measurementUnit": "unit used (inches, cm, mm)",

  "constructionDetails": [
    {{
      "area": "área da peça",
      "description": "descrição completa",
      "stitchType": "tipo de ponto",
      "stitchCode": "código de ponto",
      "seam": "tipo de costura",
      "seamAllowance": "margem de costura",
      "notes": "observações"
    }}
  ],

  "billOfMaterials": [
    {{
      "category": "categoria do material",
      "itemName": "nome do item",
      "itemCode": "código do item",
      "supplier": "fornecedor",
      "supplierCode": "código do fornecedor",
      "composition": "composição",
      "weight": "peso",
      "color": "cor",
      "colorCode": "código da cor",
      "pantone": "código Pantone",
      "size": "dimensões",
      "placement": "posição",
      "quantity": "quantidade",
      "unit": "unidade",
      "notes": "notas"
    }}
  ],

  "materialComposition": [{{"fiber": "tipo de fibra", "percentage": "número"}}],

  "labels": [
    {{
      "type": "tipo de etiqueta",
      "sequence": "número de sequência",
      "placement": "posição",
      "material": "material",
      "content": "conteúdo",
      "size": "dimensões",
      "foldType": "tipo de dobra",
      "notes": "observações"
    }}
  ],

  "labelSequence": [
    {{
      "position": "posição",
      "sequence": ["Label 1 type", "Label 2 type"],
      "notes": "observações"
    }}
  ],

  "hangTags": [{{"type": "tipo", "material": "material", "content": "conteúdo", "size": "dimensões", "attachment": "fixação"}}],

  "foldingInstructions": [
    {{
      "step": "número",
      "description": "descrição",
      "dimensions": "dimensões"
    }}
  ],

  "packagingInstructions": [
    {{
      "step": "número",
      "description": "descrição",
      "material": "material",
      "dimensions": "dimensões"
    }}
  ],

  "careSymbols": ["símbolos de cuidado"],

  "careInstructions": [
    {{
      "language": "idioma",
      "instructions": ["lista de instruções"]
    }}
  ],

  "artwork": [
    {{
      "type": "tipo",
      "name": "nome",
      "placement": "posição",
      "technique": "técnica",
      "colors": ["cores"],
      "dimensions": "dimensões"
    }}
  ],

  "sampleReview": [
    {{
      "pomCode": "código POM",
      "pomName": "nome",
      "targetValue": "valor esperado",
      "actualValue": "valor medido",
      "tolerance": "tolerância",
      "status": "status"
    }}
  ],

  "fitComments": ["comentários de fit"]
}}

CRITICAL: Extract EVERY size, EVERY measurement, EVERY BOM item. Be thorough!
Include only fields that have actual data - do not include empty arrays."""

        try:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}] + image_content
                }],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=16384
            )

            response_text = completion.choices[0].message.content or "{}"
            batch_data = json.loads(response_text)
            all_extracted.append(batch_data)
            print(f"    ✓ Extracted {len(batch_data)} fields")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    return all_extracted


def merge_extracted_data(batches: list[dict]) -> dict:
    """Merge data from multiple batches"""
    if not batches:
        return {}
    if len(batches) == 1:
        return batches[0]

    merged = {}
    array_fields = [
        'sizeRange', 'colorways', 'sizeSpecifications', 'constructionDetails',
        'artwork', 'labels', 'hangTags', 'packaging', 'careInstructions',
        'billOfMaterials', 'materialComposition', 'foldingInstructions',
        'pointsOfMeasure', 'labelSequence', 'packagingInstructions',
        'sampleReview', 'fitComments', 'careSymbols'
    ]

    for batch in batches:
        for key, value in batch.items():
            if key in array_fields:
                if key not in merged:
                    merged[key] = []
                if isinstance(value, list):
                    merged[key].extend(value)
            elif key not in merged and value:
                merged[key] = value

    # Deduplicate arrays
    for field in array_fields:
        if field in merged and merged[field]:
            # Use JSON serialization for deduplication
            seen = set()
            unique = []
            for item in merged[field]:
                item_str = json.dumps(item, sort_keys=True)
                if item_str not in seen:
                    seen.add(item_str)
                    unique.append(item)
            merged[field] = unique

    return merged


def map_measurements_to_standard(client: OpenAI, raw_measurements: dict) -> dict:
    """Map raw measurement names to standard names using OpenAI"""
    measurement_names = list(raw_measurements.keys())
    standard_names = list(STANDARD_MEASUREMENTS.keys())

    prompt = f"""Map these raw measurement names from a tech pack to standard measurement names.

RAW MEASUREMENT NAMES:
{chr(10).join(measurement_names)}

AVAILABLE STANDARD NAMES:
{chr(10).join(standard_names)}

Rules:
- Map each raw name to the most appropriate standard name
- Use null if no good match exists
- Consider common variations (e.g., "waist relaxed" -> "waist", "body length" -> "front_length")

Return JSON: {{ "originalName": "standardName or null", ... }}"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Map measurement names accurately. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=2000
        )

        mapping = json.loads(completion.choices[0].message.content or "{}")
        standardized = {}

        for original, value in raw_measurements.items():
            standard_name = mapping.get(original)
            if standard_name and standard_name in STANDARD_MEASUREMENTS:
                standardized[standard_name] = value
            else:
                standardized[original] = value

        return standardized, mapping
    except Exception as e:
        print(f"Error mapping measurements: {e}")
        return raw_measurements, {}


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_techpack_extraction_improved.py <pdf_path>")
        print("\nAvailable tech packs:")
        for f in Path("techpacks").glob("*.pdf"):
            print(f"  - {f}")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    print("=" * 70)
    print("IMPROVED TECH PACK EXTRACTION TEST")
    print("=" * 70)
    print(f"\nFile: {pdf_path}")
    print(f"Size: {Path(pdf_path).stat().st_size / 1024 / 1024:.2f} MB")

    client = OpenAI(api_key=api_key)

    print("\n1. Converting PDF to images...")
    images = convert_pdf_to_images(pdf_path)
    print(f"   Converted {len(images)} pages")

    if not images:
        print("   No images extracted!")
        sys.exit(1)

    print("\n2. Extracting with GPT-4 Vision...")
    import time
    start = time.time()
    batches = extract_with_vision(client, images)
    elapsed = time.time() - start
    print(f"   Extraction completed in {elapsed:.1f}s")

    print("\n3. Merging batch results...")
    merged = merge_extracted_data(batches)

    # Map measurements to standard names
    if merged.get("sizeSpecifications"):
        print("\n4. Standardizing measurement names...")
        first_spec = merged["sizeSpecifications"][0]
        if first_spec.get("measurements"):
            standardized, mapping = map_measurements_to_standard(client, first_spec["measurements"])
            print(f"   Mapped {len(mapping)} measurements")

            # Apply to all sizes
            for spec in merged["sizeSpecifications"]:
                if spec.get("measurements"):
                    spec["rawMeasurements"] = spec["measurements"].copy()
                    new_meas = {}
                    for orig, val in spec["measurements"].items():
                        std_name = mapping.get(orig, orig)
                        if std_name and std_name in STANDARD_MEASUREMENTS:
                            new_meas[std_name] = val
                        else:
                            new_meas[orig] = val
                    spec["measurements"] = new_meas

    print("\n" + "=" * 70)
    print("EXTRACTION RESULTS")
    print("=" * 70)

    # Print summary
    print("\n📋 SUMMARY:")
    print(f"   Style: {merged.get('styleReference', 'N/A')}")
    print(f"   Product: {merged.get('productName', 'N/A')}")
    print(f"   Type: {merged.get('productType', 'N/A')}")
    print(f"   Season: {merged.get('season', 'N/A')}")
    print(f"   Brand: {merged.get('brand', 'N/A')}")
    print(f"   Revision: {merged.get('revision', 'N/A')}")

    if merged.get("sizeRange"):
        print(f"   Sizes: {', '.join(merged['sizeRange'])}")

    if merged.get("colorways"):
        print(f"\n🎨 COLORWAYS: {len(merged['colorways'])}")
        for c in merged["colorways"][:3]:
            pantone = f" ({c['pantone']})" if c.get('pantone') else ""
            print(f"   - {c['name']}{pantone}")

    if merged.get("pointsOfMeasure"):
        print(f"\n📏 POINTS OF MEASURE: {len(merged['pointsOfMeasure'])}")
        for pom in merged["pointsOfMeasure"][:5]:
            tol = f"±{pom.get('tolerancePlus', '?')}/{pom.get('toleranceMinus', '?')}"
            print(f"   {pom.get('pomCode', '-')}: {pom['name']} ({tol})")
        if len(merged["pointsOfMeasure"]) > 5:
            print(f"   ... and {len(merged['pointsOfMeasure']) - 5} more")

    if merged.get("sizeSpecifications"):
        print(f"\n📐 SIZE SPECIFICATIONS: {len(merged['sizeSpecifications'])} sizes")
        for spec in merged["sizeSpecifications"][:3]:
            meas_count = len(spec.get("measurements", {}))
            print(f"   Size {spec['size']}: {meas_count} measurements")

    if merged.get("billOfMaterials"):
        print(f"\n🧵 BILL OF MATERIALS: {len(merged['billOfMaterials'])} items")
        for item in merged["billOfMaterials"][:5]:
            name = item.get("itemName") or item.get("description") or "N/A"
            print(f"   - {item['category']}: {name}")
        if len(merged["billOfMaterials"]) > 5:
            print(f"   ... and {len(merged['billOfMaterials']) - 5} more")

    if merged.get("constructionDetails"):
        print(f"\n🪡 CONSTRUCTION: {len(merged['constructionDetails'])} details")

    if merged.get("labels"):
        print(f"\n🏷️ LABELS: {len(merged['labels'])}")
        for label in merged["labels"][:3]:
            print(f"   - {label.get('type', 'Unknown')}: {label.get('placement', 'N/A')}")

    if merged.get("foldingInstructions"):
        print(f"\n📦 FOLDING: {len(merged['foldingInstructions'])} steps")

    if merged.get("packagingInstructions"):
        print(f"\n📦 PACKAGING: {len(merged['packagingInstructions'])} steps")

    if merged.get("careSymbols"):
        print(f"\n🧺 CARE SYMBOLS: {', '.join(merged['careSymbols'][:5])}")

    if merged.get("artwork"):
        print(f"\n🎨 ARTWORK: {len(merged['artwork'])} items")
        for art in merged["artwork"][:3]:
            print(f"   - {art.get('type', 'Unknown')}: {art.get('placement', 'N/A')}")

    # Save full result
    output_path = pdf_path.replace(".pdf", "_extracted.json").replace(".PDF", "_extracted.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Full results saved to: {output_path}")


if __name__ == "__main__":
    main()
