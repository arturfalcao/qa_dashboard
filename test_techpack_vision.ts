#!/usr/bin/env npx ts-node
/**
 * Test script for tech pack vision extraction
 * This tests the extraction logic in isolation without requiring the full API
 */

import * as fs from 'fs';
import * as path from 'path';
import OpenAI from 'openai';
import * as pdf from 'pdf-parse';

// Use existing poppler if available
let pdftoppm: string | null = null;
try {
  const { execSync } = require('child_process');
  execSync('which pdftoppm', { stdio: 'pipe' });
  pdftoppm = 'pdftoppm';
} catch {
  console.log("pdftoppm not available");
}

// Standard measurement schema (copied from service)
const STANDARD_MEASUREMENTS = {
  front_length: { description: "Front length from HPS to hem", category: "length" },
  back_length: { description: "Back length from HPS to hem", category: "length" },
  cb_length: { description: "Center back length", category: "length" },
  sleeve_length: { description: "Sleeve length from shoulder point", category: "sleeve" },
  sleeve_length_cb: { description: "Sleeve length from center back neck", category: "sleeve" },
  sleeve_bicep: { description: "Sleeve width at bicep/underarm", category: "sleeve" },
  sleeve_cuff: { description: "Sleeve opening/cuff width", category: "sleeve" },
  chest_width: { description: "Chest width 1\" below armhole", category: "width" },
  waist_width: { description: "Waist width", category: "width" },
  hip_width: { description: "Hip width", category: "width" },
  hem_width: { description: "Bottom hem width", category: "width" },
  shoulder_width: { description: "Shoulder to shoulder width", category: "shoulder" },
  neck_width: { description: "Neck opening width", category: "neck" },
  neck_depth_front: { description: "Front neck drop from HPS", category: "neck" },
  armhole_depth: { description: "Armhole depth from shoulder", category: "armhole" },
  waist: { description: "Waist measurement (pants)", category: "pants" },
  front_rise: { description: "Front rise (crotch to waist)", category: "pants" },
  back_rise: { description: "Back rise (crotch to waist)", category: "pants" },
  inseam: { description: "Inseam length", category: "pants" },
  outseam: { description: "Outseam length", category: "pants" },
  thigh_width: { description: "Thigh width 1\" from crotch", category: "pants" },
  knee_width: { description: "Knee width", category: "pants" },
  leg_opening: { description: "Leg opening/hem width", category: "pants" },
  waistband_height: { description: "Waistband height", category: "pants" },
};

async function convertPdfToImages(pdfBuffer: Buffer, maxPages = 20): Promise<Buffer[]> {
  if (!pdftoppm) {
    console.log("pdftoppm not available, skipping image conversion");
    return [];
  }

  const { execSync } = require('child_process');
  const os = require('os');
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pdf-'));
  const tempPdf = path.join(tempDir, 'input.pdf');

  try {
    fs.writeFileSync(tempPdf, pdfBuffer);

    // Convert PDF to PNG images
    execSync(`pdftoppm -png -r 150 -l ${maxPages} "${tempPdf}" "${path.join(tempDir, 'page')}"`, {
      stdio: 'pipe',
      timeout: 120000,
    });

    const imageBuffers: Buffer[] = [];
    const files = fs.readdirSync(tempDir)
      .filter(f => f.endsWith('.png'))
      .sort();

    for (const file of files) {
      imageBuffers.push(fs.readFileSync(path.join(tempDir, file)));
    }

    return imageBuffers;
  } finally {
    // Cleanup
    try {
      fs.rmSync(tempDir, { recursive: true });
    } catch {}
  }
}

async function extractWithVision(
  openai: OpenAI,
  pageImages: Buffer[],
  batchSize = 3
): Promise<any[]> {
  const allExtractedData: any[] = [];

  for (let i = 0; i < pageImages.length; i += batchSize) {
    const batch = pageImages.slice(i, i + batchSize);
    const batchNum = Math.floor(i / batchSize) + 1;
    console.log(`Processing batch ${batchNum} (pages ${i + 1}-${Math.min(i + batchSize, pageImages.length)})...`);

    const imageContent = batch.map((buf, idx) => ({
      type: "image_url" as const,
      image_url: {
        url: `data:image/png;base64,${buf.toString('base64')}`,
        detail: "high" as const,
      },
    }));

    const prompt = `You are an expert tech pack analyzer for garment manufacturing QC systems. Analyze these tech pack pages (pages ${i + 1}-${Math.min(i + batchSize, pageImages.length)} of ${pageImages.length}).

INSTRUCTIONS:
1. Extract ALL information visible in the document - be thorough and comprehensive
2. Translate ALL descriptive text to PORTUGUESE (Brazilian Portuguese)
3. Keep codes/references unchanged (SKUs, article numbers, Pantone codes, stitch codes, POM codes, size labels)
4. Keep numeric measurements exactly as shown with their units
5. PAY SPECIAL ATTENTION to measurement tables, tolerance tables, BOM tables, and folding/packing diagrams

Return a JSON object with these fields when applicable:

{
  "styleReference": "style number, SKU, article number",
  "productName": "product name or description",
  "productType": "type of garment (JACKET, PANTS, SHIRT, etc.)",
  "season": "season or collection",
  "brand": "brand name",
  "designer": "designer or manufacturer name",
  "revision": "document revision number",
  "date": "document date",

  "colorways": [{"name": "nome da cor", "colorCode": "código", "pantone": "código Pantone", "hex": "#RRGGBB"}],

  "sizeRange": ["all size labels found"],

  "pointsOfMeasure": [
    {
      "pomCode": "código POM (ex: LT018, CH002B)",
      "name": "nome da medida exatamente como mostrado",
      "description": "descrição de como medir",
      "tolerancePlus": "número",
      "toleranceMinus": "número",
      "category": "categoria"
    }
  ],

  "sizeSpecifications": [
    {
      "size": "size label exactly as shown",
      "measurements": {
        "EXACT_MEASUREMENT_NAME_FROM_DOCUMENT": "value as number"
      }
    }
  ],
  "measurementUnit": "unit used (inches, cm, mm)",

  "constructionDetails": [
    {
      "area": "área da peça",
      "description": "descrição completa",
      "stitchType": "tipo de ponto",
      "stitchCode": "código de ponto",
      "seam": "tipo de costura",
      "seamAllowance": "margem de costura",
      "notes": "observações"
    }
  ],

  "billOfMaterials": [
    {
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
    }
  ],

  "materialComposition": [{"fiber": "tipo de fibra", "percentage": "número"}],

  "labels": [
    {
      "type": "tipo de etiqueta",
      "sequence": "número de sequência",
      "placement": "posição",
      "material": "material",
      "content": "conteúdo",
      "size": "dimensões",
      "foldType": "tipo de dobra",
      "notes": "observações"
    }
  ],

  "labelSequence": [
    {
      "position": "posição",
      "sequence": ["Label 1 type", "Label 2 type"],
      "notes": "observações"
    }
  ],

  "foldingInstructions": [
    {
      "step": "número",
      "description": "descrição",
      "dimensions": "dimensões"
    }
  ],

  "packagingInstructions": [
    {
      "step": "número",
      "description": "descrição",
      "material": "material",
      "dimensions": "dimensões"
    }
  ],

  "careSymbols": ["símbolos de cuidado"],

  "careInstructions": [
    {
      "language": "idioma",
      "instructions": ["lista de instruções"]
    }
  ],

  "artwork": [
    {
      "type": "tipo",
      "name": "nome",
      "placement": "posição",
      "technique": "técnica",
      "colors": ["cores"],
      "dimensions": "dimensões"
    }
  ],

  "sampleReview": [
    {
      "pomCode": "código POM",
      "pomName": "nome",
      "targetValue": "valor esperado",
      "actualValue": "valor medido",
      "tolerance": "tolerância",
      "status": "status"
    }
  ],

  "fitComments": ["comentários de fit"]
}

CRITICAL: Extract EVERY size, EVERY measurement, EVERY BOM item. Be thorough!
Include only fields that have actual data - do not include empty arrays.`;

    try {
      const completion = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: prompt },
              ...imageContent,
            ],
          },
        ],
        response_format: { type: "json_object" },
        temperature: 0,
        max_tokens: 16384,
      });

      const responseText = completion.choices[0]?.message?.content || "{}";
      const batchData = JSON.parse(responseText);
      allExtractedData.push(batchData);
      console.log(`  ✓ Extracted ${Object.keys(batchData).length} fields`);
    } catch (error: any) {
      console.error(`  ✗ Error in batch ${batchNum}:`, error.message);
    }
  }

  return allExtractedData;
}

function mergeExtractedData(batches: any[]): any {
  if (batches.length === 0) return {};
  if (batches.length === 1) return batches[0];

  const merged: any = {};
  const arrayFields = [
    'sizeRange', 'colorways', 'sizeSpecifications', 'constructionDetails',
    'artwork', 'labels', 'hangTags', 'packaging', 'careInstructions',
    'billOfMaterials', 'materialComposition', 'foldingInstructions',
    'pointsOfMeasure', 'labelSequence', 'packagingInstructions',
    'sampleReview', 'fitComments', 'careSymbols'
  ];

  for (const batch of batches) {
    for (const [key, value] of Object.entries(batch)) {
      if (arrayFields.includes(key)) {
        if (!merged[key]) merged[key] = [];
        if (Array.isArray(value)) {
          merged[key].push(...value);
        }
      } else if (!merged[key] && value) {
        merged[key] = value;
      }
    }
  }

  // Deduplicate arrays
  for (const field of arrayFields) {
    if (merged[field]) {
      merged[field] = [...new Map(
        merged[field].map((item: any) => [JSON.stringify(item), item])
      ).values()];
    }
  }

  return merged;
}

async function mapMeasurementsToStandard(
  openai: OpenAI,
  rawMeasurements: Record<string, number>
): Promise<Record<string, number>> {
  const measurementNames = Object.keys(rawMeasurements);
  const standardNames = Object.keys(STANDARD_MEASUREMENTS);

  const prompt = `Map these raw measurement names from a tech pack to standard measurement names.

RAW MEASUREMENT NAMES:
${measurementNames.join('\n')}

AVAILABLE STANDARD NAMES:
${standardNames.join('\n')}

Rules:
- Map each raw name to the most appropriate standard name
- Use null if no good match exists
- Consider common variations (e.g., "waist relaxed" -> "waist", "body length" -> "front_length")

Return JSON: { "originalName": "standardName or null", ... }`;

  try {
    const completion = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: "Map measurement names accurately. Return only valid JSON." },
        { role: "user", content: prompt },
      ],
      response_format: { type: "json_object" },
      temperature: 0,
      max_tokens: 2000,
    });

    const mapping = JSON.parse(completion.choices[0]?.message?.content || "{}");
    const standardized: Record<string, number> = {};

    for (const [original, value] of Object.entries(rawMeasurements)) {
      const standardName = mapping[original];
      if (standardName) {
        standardized[standardName] = value as number;
      } else {
        standardized[original] = value as number;
      }
    }

    return standardized;
  } catch (error) {
    console.error("Error mapping measurements:", error);
    return rawMeasurements;
  }
}

async function main() {
  const args = process.argv.slice(2);
  const pdfPath = args[0] || './techpacks/Sample - Tech Pack Advanced.pdf';

  if (!fs.existsSync(pdfPath)) {
    console.error(`File not found: ${pdfPath}`);
    process.exit(1);
  }

  console.log('='.repeat(70));
  console.log('TECH PACK VISION EXTRACTION TEST');
  console.log('='.repeat(70));
  console.log(`\nFile: ${pdfPath}`);

  // Check for API key
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error('\nError: OPENAI_API_KEY environment variable not set');
    console.log('Set it with: export OPENAI_API_KEY=your-key');
    process.exit(1);
  }

  const openai = new OpenAI({ apiKey });

  console.log('\n1. Reading PDF file...');
  const pdfBuffer = fs.readFileSync(pdfPath);
  console.log(`   File size: ${(pdfBuffer.length / 1024 / 1024).toFixed(2)} MB`);

  console.log('\n2. Converting PDF to images...');
  const pageImages = await convertPdfToImages(pdfBuffer);
  console.log(`   Converted ${pageImages.length} pages`);

  if (pageImages.length === 0) {
    console.error('   No images extracted. Make sure pdftoppm is installed.');
    process.exit(1);
  }

  console.log('\n3. Extracting with GPT-4 Vision...');
  const startTime = Date.now();
  const batches = await extractWithVision(openai, pageImages);
  const extractionTime = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`   Extraction completed in ${extractionTime}s`);

  console.log('\n4. Merging batch results...');
  const merged = mergeExtractedData(batches);

  // Map measurements to standard names if we have size specifications
  if (merged.sizeSpecifications && merged.sizeSpecifications.length > 0) {
    console.log('\n5. Standardizing measurement names...');
    const firstSpec = merged.sizeSpecifications[0];
    if (firstSpec.measurements) {
      const sampleMeasurements: Record<string, number> = {};
      for (const [k, v] of Object.entries(firstSpec.measurements)) {
        sampleMeasurements[k] = v as number;
      }

      const standardMapping = await mapMeasurementsToStandard(openai, sampleMeasurements);
      console.log(`   Mapped ${Object.keys(standardMapping).length} measurements`);

      // Apply mapping to all sizes
      for (const spec of merged.sizeSpecifications) {
        spec.rawMeasurements = { ...spec.measurements };
        const newMeasurements: Record<string, number> = {};
        for (const [orig, val] of Object.entries(spec.measurements || {})) {
          const standardKey = Object.keys(standardMapping).find(
            k => standardMapping[k] === sampleMeasurements[orig]
          ) || orig;
          newMeasurements[standardKey] = val as number;
        }
        spec.measurements = newMeasurements;
      }
    }
  }

  console.log('\n' + '='.repeat(70));
  console.log('EXTRACTION RESULTS');
  console.log('='.repeat(70));

  // Print summary
  console.log('\n📋 SUMMARY:');
  console.log(`   Style: ${merged.styleReference || 'N/A'}`);
  console.log(`   Product: ${merged.productName || 'N/A'}`);
  console.log(`   Type: ${merged.productType || 'N/A'}`);
  console.log(`   Season: ${merged.season || 'N/A'}`);
  console.log(`   Brand: ${merged.brand || 'N/A'}`);
  console.log(`   Revision: ${merged.revision || 'N/A'}`);

  if (merged.sizeRange) {
    console.log(`   Sizes: ${merged.sizeRange.join(', ')}`);
  }

  if (merged.colorways) {
    console.log(`   Colorways: ${merged.colorways.length}`);
    for (const c of merged.colorways.slice(0, 3)) {
      console.log(`     - ${c.name}${c.pantone ? ' (' + c.pantone + ')' : ''}`);
    }
  }

  if (merged.pointsOfMeasure) {
    console.log(`\n📏 POINTS OF MEASURE: ${merged.pointsOfMeasure.length}`);
    for (const pom of merged.pointsOfMeasure.slice(0, 5)) {
      console.log(`   ${pom.pomCode || '-'}: ${pom.name} (±${pom.tolerancePlus || '?'}/${pom.toleranceMinus || '?'})`);
    }
    if (merged.pointsOfMeasure.length > 5) {
      console.log(`   ... and ${merged.pointsOfMeasure.length - 5} more`);
    }
  }

  if (merged.sizeSpecifications) {
    console.log(`\n📐 SIZE SPECIFICATIONS: ${merged.sizeSpecifications.length} sizes`);
    for (const spec of merged.sizeSpecifications.slice(0, 3)) {
      const measurementCount = Object.keys(spec.measurements || {}).length;
      console.log(`   Size ${spec.size}: ${measurementCount} measurements`);
    }
  }

  if (merged.billOfMaterials) {
    console.log(`\n🧵 BILL OF MATERIALS: ${merged.billOfMaterials.length} items`);
    for (const item of merged.billOfMaterials.slice(0, 5)) {
      console.log(`   - ${item.category}: ${item.itemName || item.description || 'N/A'}`);
    }
    if (merged.billOfMaterials.length > 5) {
      console.log(`   ... and ${merged.billOfMaterials.length - 5} more`);
    }
  }

  if (merged.constructionDetails) {
    console.log(`\n🪡 CONSTRUCTION: ${merged.constructionDetails.length} details`);
  }

  if (merged.labels) {
    console.log(`\n🏷️ LABELS: ${merged.labels.length}`);
  }

  if (merged.foldingInstructions) {
    console.log(`\n📦 FOLDING: ${merged.foldingInstructions.length} steps`);
  }

  if (merged.packagingInstructions) {
    console.log(`\n📦 PACKAGING: ${merged.packagingInstructions.length} steps`);
  }

  if (merged.careSymbols) {
    console.log(`\n🧺 CARE SYMBOLS: ${merged.careSymbols.join(', ')}`);
  }

  // Save full result
  const outputPath = pdfPath.replace(/\.pdf$/i, '_extracted.json');
  fs.writeFileSync(outputPath, JSON.stringify(merged, null, 2), 'utf-8');
  console.log(`\n✅ Full results saved to: ${outputPath}`);
}

main().catch(console.error);
