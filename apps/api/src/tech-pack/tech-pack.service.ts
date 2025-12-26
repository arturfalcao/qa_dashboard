import { Injectable } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import OpenAI from "openai";
import * as XLSX from "xlsx";
import { PdfReader } from "pdfreader";
import { StorageService } from "../storage/storage.service";
import { File as NodeFile } from "node:buffer";
import { execSync, spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import sharp from "sharp";

// Polyfill File for Node.js < 20
if (typeof globalThis.File === "undefined") {
  (globalThis as any).File = NodeFile;
}

// Check if pdftoppm is available (from poppler-utils)
let pdftoppmAvailable = false;
try {
  execSync("which pdftoppm", { stdio: "ignore" });
  pdftoppmAvailable = true;
  console.log("pdftoppm is available for PDF to image conversion");
} catch (e) {
  console.log("pdftoppm not available - PDF page image extraction may be limited");
}

// ============================================
// STANDARD MEASUREMENT SCHEMA
// ============================================
// These are the standardized measurement names used in the database.
// OpenAI will map various tech pack naming conventions to these standards.

export const STANDARD_MEASUREMENTS = {
  // === LENGTH MEASUREMENTS ===
  front_length: { description: "Front length from HPS to hem", category: "length", unit: "inches" },
  back_length: { description: "Back length from HPS to hem", category: "length", unit: "inches" },
  cb_length: { description: "Center back length", category: "length", unit: "inches" },
  cf_length: { description: "Center front length", category: "length", unit: "inches" },
  side_length: { description: "Side seam length", category: "length", unit: "inches" },

  // === SLEEVE MEASUREMENTS ===
  sleeve_length: { description: "Sleeve length from shoulder point", category: "sleeve", unit: "inches" },
  sleeve_length_cb: { description: "Sleeve length from center back neck", category: "sleeve", unit: "inches" },
  sleeve_bicep: { description: "Sleeve width at bicep/underarm", category: "sleeve", unit: "inches" },
  sleeve_elbow: { description: "Sleeve width at elbow", category: "sleeve", unit: "inches" },
  sleeve_cuff: { description: "Sleeve opening/cuff width", category: "sleeve", unit: "inches" },
  sleeve_cuff_height: { description: "Cuff/rib height", category: "sleeve", unit: "inches" },

  // === CHEST/BODY WIDTH ===
  chest_width: { description: "Chest width 1\" below armhole", category: "width", unit: "inches" },
  bust_width: { description: "Bust width at fullest point", category: "width", unit: "inches" },
  body_width: { description: "Body width at sweep/hem", category: "width", unit: "inches" },
  waist_width: { description: "Waist width", category: "width", unit: "inches" },
  hip_width: { description: "Hip width", category: "width", unit: "inches" },
  hem_width: { description: "Bottom hem width", category: "width", unit: "inches" },
  rib_hem_width: { description: "Rib hem width (stretched)", category: "width", unit: "inches" },

  // === SHOULDER ===
  shoulder_width: { description: "Shoulder to shoulder width (back)", category: "shoulder", unit: "inches" },
  shoulder_slope: { description: "Shoulder slope/drop", category: "shoulder", unit: "inches" },
  shoulder_seam_position: { description: "Shoulder seam moved forward/backward", category: "shoulder", unit: "inches" },
  across_front: { description: "Across front chest measurement", category: "shoulder", unit: "inches" },
  across_back: { description: "Across back measurement", category: "shoulder", unit: "inches" },

  // === NECK ===
  neck_width: { description: "Neck opening width", category: "neck", unit: "inches" },
  neck_depth_front: { description: "Front neck drop from HPS", category: "neck", unit: "inches" },
  neck_depth_back: { description: "Back neck drop from HPS", category: "neck", unit: "inches" },
  neck_circumference: { description: "Neck circumference/stretch minimum", category: "neck", unit: "inches" },
  collar_height: { description: "Collar/neckband height", category: "neck", unit: "inches" },
  collar_width: { description: "Collar width", category: "neck", unit: "inches" },

  // === ARMHOLE ===
  armhole_depth: { description: "Armhole depth from shoulder", category: "armhole", unit: "inches" },
  armhole_width: { description: "Armhole width/opening", category: "armhole", unit: "inches" },
  armhole_circumference: { description: "Armhole circumference", category: "armhole", unit: "inches" },

  // === HEM/RIB ===
  hem_height: { description: "Hem/rib band height", category: "hem", unit: "inches" },
  hem_circumference: { description: "Hem circumference", category: "hem", unit: "inches" },

  // === PANTS/BOTTOMS ===
  waist: { description: "Waist measurement (pants)", category: "pants", unit: "inches" },
  front_rise: { description: "Front rise (crotch to waist)", category: "pants", unit: "inches" },
  back_rise: { description: "Back rise (crotch to waist)", category: "pants", unit: "inches" },
  inseam: { description: "Inseam length", category: "pants", unit: "inches" },
  outseam: { description: "Outseam length", category: "pants", unit: "inches" },
  thigh_width: { description: "Thigh width 1\" from crotch", category: "pants", unit: "inches" },
  knee_width: { description: "Knee width", category: "pants", unit: "inches" },
  leg_opening: { description: "Leg opening/hem width", category: "pants", unit: "inches" },
  waistband_height: { description: "Waistband height", category: "pants", unit: "inches" },

  // === POCKETS ===
  pocket_width: { description: "Pocket width", category: "detail", unit: "inches" },
  pocket_height: { description: "Pocket height/depth", category: "detail", unit: "inches" },
  pocket_placement_hps: { description: "Pocket placement from HPS", category: "detail", unit: "inches" },
  pocket_placement_cf: { description: "Pocket placement from CF", category: "detail", unit: "inches" },

  // === OTHER ===
  placket_width: { description: "Placket width", category: "detail", unit: "inches" },
  placket_length: { description: "Placket length", category: "detail", unit: "inches" },
  hood_height: { description: "Hood height", category: "detail", unit: "inches" },
  hood_width: { description: "Hood width", category: "detail", unit: "inches" },
} as const;

export type StandardMeasurementKey = keyof typeof STANDARD_MEASUREMENTS;

export interface ExtractedImage {
  base64: string;
  mimeType: string;
  pageNumber?: number;
  description?: string;
  type?: string; // 'product', 'colorway', 'artwork', 'label', 'construction', 'flatlay', 'other'
}

/** Region of interest identified in a tech pack page */
export interface ImageRegion {
  pageNumber: number;
  type: 'folding_diagram' | 'hangtag' | 'label' | 'packaging' | 'fabric_swatch' |
        'construction_detail' | 'artwork' | 'colorway' | 'measurement_diagram' | 'sketch' | 'other';
  description: string;
  // Bounding box as percentage of page dimensions (0-100)
  boundingBox: {
    x: number;      // Left edge percentage
    y: number;      // Top edge percentage
    width: number;  // Width percentage
    height: number; // Height percentage
  };
  // Association info
  associatedField?: string;  // e.g., 'foldingInstructions[0]', 'hangTags[0].front', 'labels[0]'
  associatedStep?: number;   // For step-by-step diagrams
}

// ============================================
// DEPARTMENT-BASED DATA STRUCTURES
// ============================================

/** DESIGN DEPARTMENT - Visual assets, colors, artwork */
export interface DesignDepartmentData {
  // Visual Assets
  sketches?: {
    frontUrl?: string;
    backUrl?: string;
    sideUrl?: string;
  };
  technicalDrawings?: Array<{
    view: string; // 'front', 'back', 'detail'
    imageUrl?: string;       // Cropped image of the technical drawing
    callouts?: string[];
  }>;

  // Style Info
  silhouette?: string;
  fitType?: string; // 'slim', 'regular', 'relaxed', 'oversized'
  garmentCategory?: string;

  // Colorways
  colorways?: Array<{
    name: string;
    colorCode?: string;
    pantone?: string;
    hex?: string;
    isMain?: boolean;
    swatchImageUrl?: string;  // Cropped image of the fabric swatch
    fabric?: {
      name: string;
      weight?: string;
      finish?: string;
    };
    thread?: {
      color: string;
      type?: string;
    };
  }>;

  // Artwork/Graphics
  artwork?: Array<{
    type: string; // 'Print', 'Embroidery', 'Patch', 'Label'
    placement: string;
    width?: string;
    height?: string;
    colors?: string[];
    pantones?: string[];
    technique?: string;
    artworkImageUrl?: string;  // Cropped image of the artwork/print
    notes?: string;
  }>;
}

/** PATTERN/GRADING DEPARTMENT - Measurements, grading, tolerances */
export interface PatternDepartmentData {
  // Base Pattern Info
  baseSize?: string;
  measurementUnit?: 'cm' | 'inches';

  // Points of Measure (POMs)
  pointsOfMeasure?: Array<{
    code: string; // 'A', 'B', 'CHEST_1'
    name: string;
    description?: string;
    measurementMethod?: string;
    referencePoint?: string; // 'HPS', 'CB', 'CF'
  }>;

  // Size Chart
  sizeChart?: Array<{
    size: string;
    measurements: Record<string, number>;
  }>;

  // Grade Rules
  gradeRules?: Array<{
    pom: string;
    increment: number;
    incrementLargeSizes?: number; // Different increment for XL+
    breakPoint?: string; // Size where increment changes
  }>;

  // Tolerances
  tolerances?: Record<string, {
    plus: number;
    minus: number;
    critical?: boolean;
  }>;

  // Size Range
  sizeRange?: string[];
}

/** PRODUCTION DEPARTMENT - Construction, stitching, assembly */
export interface ProductionDepartmentData {
  // Construction Details
  constructionDetails?: Array<{
    area: string;
    description: string;
    stitchType?: string;
    stitchCode?: string;
    seamsPerInch?: number;
    needleType?: string;
    seamAllowance?: string;
    notes?: string;
  }>;

  // Fabric Map
  fabricMap?: Array<{
    zone: string;
    fabricType: string; // 'Main', 'Lining', 'Contrast'
    areas: string[];
    fabricCode?: string;
  }>;

  // Assembly Sequence
  assemblySequence?: Array<{
    step: number;
    operation: string;
    machineType?: string;
    timeEstimate?: string;
  }>;

  // Special Operations
  specialOperations?: Array<{
    type: string; // 'Washing', 'Dyeing', 'Finishing'
    description: string;
    parameters?: Record<string, any>;
  }>;
}

/** SOURCING DEPARTMENT - Materials, suppliers, costs */
export interface SourcingDepartmentData {
  // Bill of Materials
  billOfMaterials?: Array<{
    category: string; // 'Main Fabric', 'Lining', 'Trim', 'Thread', 'Label'
    itemCode?: string;
    itemName: string;
    description?: string;
    supplier?: string;
    supplierCode?: string;
    color?: string;
    size?: string;
    quantityPerUnit?: number;
    unit?: string; // 'yards', 'meters', 'pieces'
    unitCost?: number;
    currency?: string;
    leadTimeDays?: number;
    moq?: number;
    swatchImageUrl?: string;  // Cropped image of material swatch
  }>;

  // Fabric Specifications
  fabricSpecs?: Array<{
    fabricCode?: string;
    fabricName: string;
    composition: string; // '100% Cotton'
    weight?: string; // '300 GSM'
    width?: string;
    finish?: string;
    supplier?: string;
    certifications?: string[];
    swatchImageUrl?: string;  // Cropped image of fabric swatch
  }>;

  // Trim Specifications
  trimSpecs?: Array<{
    trimCode?: string;
    trimName: string;
    type: string; // 'Button', 'Zipper', 'Elastic', 'Drawcord'
    material?: string;
    size?: string;
    color?: string;
    supplier?: string;
    imageUrl?: string;  // Cropped image of trim
  }>;
}

/** QC DEPARTMENT - Inspection points, tolerances, defect criteria */
export interface QCDepartmentData {
  // Inspection Points
  inspectionPoints?: Array<{
    pomCode: string;
    pomName: string;
    targetValue?: number;
    tolerancePlus: number;
    toleranceMinus: number;
    criticalLevel: 'critical' | 'major' | 'minor';
    inspectionMethod?: string;
    defectIfFail?: string;
  }>;

  // AQL Settings
  aqlSettings?: {
    level: string; // '2.5', '4.0'
    criticalDefects: string[];
    majorDefects: string[];
    minorDefects: string[];
  };

  // Visual Standards
  visualStandards?: Array<{
    area: string;
    requirement: string;
    acceptanceCriteria?: string;
  }>;

  // Testing Requirements
  testingRequirements?: Array<{
    testType: string;
    standard?: string; // 'ASTM', 'ISO'
    requirement: string;
    frequency?: string;
  }>;
}

/** PACKAGING DEPARTMENT - Labels, tags, packaging specs */
export interface PackagingDepartmentData {
  // Labels
  labels?: Array<{
    type: string; // 'Main Label', 'Care Label', 'Size Label', 'Content Label'
    width?: string;
    height?: string;
    material?: string;
    placement?: string;
    content?: string;
    imageUrl?: string;      // Cropped image of the label
    colors?: string[];
  }>;

  // Hang Tags
  hangTags?: Array<{
    type?: string;
    width?: string;
    height?: string;
    material?: string;
    content?: string;
    frontImageUrl?: string;  // Front side cropped image
    backImageUrl?: string;   // Back side cropped image
    attachmentMethod?: string;
  }>;

  // Care Instructions
  careInstructions?: {
    symbols?: string[];
    instructions?: Array<{
      language: string;
      text: string[];
    }>;
  };

  // Packaging Specs
  packaging?: Array<{
    type: string; // 'Polybag', 'Box', 'Tissue'
    material?: string;
    dimensions?: string;
    printingDetails?: string;
    quantity?: number;
    frontImageUrl?: string;  // Front side cropped image
    backImageUrl?: string;   // Back side cropped image
  }>;

  // Folding Instructions
  foldingInstructions?: Array<{
    step: number;
    description: string;
    imageUrl?: string;       // Cropped diagram for this step
  }>;

  // Carton Specs
  cartonSpecs?: {
    unitsPerCarton?: number;
    cartonDimensions?: string;
    grossWeight?: string;
    netWeight?: string;
  };
}

// ============================================
// MAIN EXTRACTION RESULT
// ============================================

export interface TechPackExtractionResult {
  // Basic Info (Header)
  styleRef?: string;
  productName?: string;
  productType?: string;
  season?: string;
  designer?: string;
  brand?: string;
  revision?: string;
  date?: string;

  // Extracted Images (base64 to be uploaded to S3 later)
  extractedImages?: ExtractedImage[];

  // Image regions identified for cropping (bounding boxes)
  imageRegions?: ImageRegion[];

  // Page images with dimensions (for cropping regions)
  pageImages?: Array<{ pageNumber: number; base64: string; width: number; height: number }>;

  // Department-Organized Data
  departments?: {
    design?: DesignDepartmentData;
    pattern?: PatternDepartmentData;
    production?: ProductionDepartmentData;
    sourcing?: SourcingDepartmentData;
    qc?: QCDepartmentData;
    packaging?: PackagingDepartmentData;
  };

  // === NEW QC FIELDS ===

  // Points of Measure with POM codes and tolerances
  pointsOfMeasure?: Array<{
    pomCode: string;
    name: string;
    description?: string;
    tolerancePlus?: number;
    toleranceMinus?: number;
    category?: string;
  }>;

  // Label sequence for QC verification
  labelSequence?: Array<{
    position: string;
    sequence: string[];
    notes?: string;
  }>;

  // Packaging instructions (separate from folding)
  packagingInstructions?: Array<{
    step: number;
    description: string;
    material?: string;
    dimensions?: string;
    notes?: string;
  }>;

  // Care symbols
  careSymbols?: string[];

  // Sample review data for QC
  sampleReview?: Array<{
    pomCode?: string;
    pomName: string;
    targetValue?: number;
    actualValue?: number;
    tolerance?: string;
    status?: string;
    notes?: string;
  }>;

  // Fit comments from sample review
  fitComments?: string[];

  // === LEGACY FLAT FIELDS (for backward compatibility) ===
  sampleSize?: string;
  materialComposition?: Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }>;
  dyeLot?: string;
  productionQuantity?: number;
  colorways?: Array<{
    name: string;
    colorCode?: string;
    pantone?: string;
    hex?: string;
    fabric?: { name: string; weight?: string; finish?: string } | string;
    thread?: { color: string; type?: string } | string;
    trim?: { description: string; color?: string };
    isMain?: boolean;
  }>;
  sizeSpecifications?: Array<{
    size: string;
    measurements: Record<string, number>;
    rawMeasurements?: Record<string, number>;
  }>;
  measurementTolerances?: Record<string, number>;
  measurementUnit?: string;
  sizeRange?: string[];
  grading?: Array<{
    measurement: string;
    sizes: Record<string, number>;
  }>;
  constructionDetails?: Array<{
    area: string;
    description: string;
    stitchType?: string;
    stitchCode?: string;
    needleType?: string;
    seamsPerInch?: number;
    seamAllowance?: string;
    seam?: string;
    notes?: string;
  }>;
  artwork?: Array<{
    type: string;
    name?: string;
    placement: string;
    placementBySize?: Record<string, string>;
    width?: string;
    height?: string;
    dimensions?: string;
    colors?: string[];
    pantones?: string[];
    technique?: string;
    imageUrl?: string;  // Cropped image of the artwork
    notes?: string;
  }>;
  fabricMap?: Array<{
    zone: string;
    fabricType: string;
    areas: string[];
  }>;
  labels?: Array<{
    type: string;
    sequence?: number;
    width?: string;
    height?: string;
    size?: string;
    material?: string;
    placement?: string;
    content?: string;
    foldType?: string;
    attachmentMethod?: string;
    colors?: string[];
    imageUrl?: string;  // Cropped image of the label
    notes?: string;
  }>;
  hangTags?: Array<{
    type?: string;
    width?: string;
    height?: string;
    size?: string;
    material?: string;
    content?: string;
    attachment?: string;
    attachmentPosition?: string;
    colors?: string[];
    frontImageUrl?: string;  // Front side cropped image
    backImageUrl?: string;   // Back side cropped image
    imageUrl?: string;       // Generic image URL
    notes?: string;
  }>;
  packaging?: Array<{
    type: string;
    width?: string;
    height?: string;
    dimensions?: string;
    material?: string;
    quantity?: number;
    frontImageUrl?: string;  // Front side cropped image
    backImageUrl?: string;   // Back side cropped image
    imageUrl?: string;       // Generic image URL
    notes?: string;
  }>;
  foldingInstructions?: Array<{
    step: number;
    description: string;
    dimensions?: string;
    imageUrl?: string;  // Cropped diagram for this step
    notes?: string;
  }>;
  careInstructions?: Array<{
    language: string;
    instructions: string[];
  }>;
  billOfMaterials?: Array<{
    category: string;
    itemName?: string;
    description?: string;
    itemCode?: string;
    articleNumber?: string;
    supplier?: string;
    supplierCode?: string;
    composition?: string;
    weight?: string;
    color?: string;
    colorCode?: string;
    pantone?: string;
    articleNo?: string;
    size?: string;
    placement?: string;
    quantity?: number;
    unit?: string;
    cost?: number;
    moq?: number;
    leadTime?: string;
    swatchImageUrl?: string;  // Cropped image of material swatch
    notes?: string;
  }>;

  // Raw data for debugging
  rawExtractedData?: Record<string, any>;
}

@Injectable()
export class TechPackService {
  private openai: OpenAI | null = null;

  constructor(
    private configService: ConfigService,
    private storageService: StorageService,
  ) {
    const apiKey = this.configService.get<string>("OPENAI_API_KEY");
    if (apiKey) {
      this.openai = new OpenAI({ apiKey });
    }
  }

  /**
   * Map raw measurements from tech pack to standardized measurement names using OpenAI.
   * This handles variations in naming conventions across different tech pack formats.
   *
   * @param rawMeasurements Object with raw measurement names and values
   * @param garmentType Optional garment type to help with context (e.g., "top", "pants", "dress")
   * @returns Object with standardized measurement names and values, plus original names for reference
   */
  async mapMeasurementsToStandard(
    rawMeasurements: Record<string, number>,
    garmentType?: string,
  ): Promise<{
    standardized: Record<string, number>;
    mapping: Record<string, { standardName: string | null; originalName: string; value: number }>;
  }> {
    if (!this.openai) {
      console.log("OpenAI not configured, returning raw measurements");
      return {
        standardized: rawMeasurements,
        mapping: Object.fromEntries(
          Object.entries(rawMeasurements).map(([k, v]) => [k, { standardName: null, originalName: k, value: v }])
        ),
      };
    }

    // Build the standard measurements reference for the prompt
    const standardMeasurementsRef = Object.entries(STANDARD_MEASUREMENTS)
      .map(([key, info]) => `  "${key}": "${info.description}"`)
      .join(",\n");

    const prompt = `You are a garment measurement expert. Map these raw measurement names from a tech pack to the standardized names.

RAW MEASUREMENTS FROM TECH PACK:
${JSON.stringify(rawMeasurements, null, 2)}

${garmentType ? `GARMENT TYPE: ${garmentType}` : ""}

STANDARD MEASUREMENT NAMES (use ONLY these exact keys):
{
${standardMeasurementsRef}
}

INSTRUCTIONS:
1. For each raw measurement, find the BEST matching standard name from the list above
2. Consider common variations and translations (English, Portuguese, French, Italian, Spanish)
3. If a measurement clearly doesn't match any standard, use null
4. Be smart about context - "length" alone on a top is likely "front_length", on pants it's "outseam"

COMMON VARIATIONS TO CONSIDER:
- "HPS" = High Point Shoulder
- "CB" = Center Back
- "CF" = Center Front
- "1\" below armhole" = chest measurement
- "sweep" = hem/body width
- "opening" = cuff or hem opening
- Portuguese: "comprimento" = length, "largura" = width, "manga" = sleeve, "peito" = chest
- French: "longueur" = length, "largeur" = width, "manche" = sleeve, "poitrine" = chest

Return a JSON object where keys are the ORIGINAL measurement names and values are the STANDARD names:
{
  "originalMeasurementName": "standard_measurement_name_or_null",
  ...
}

Only return the JSON object, no explanation.`;

    try {
      const completion = await this.openai.chat.completions.create({
        model: "gpt-4o-mini", // Use mini for cost efficiency - this is a simple mapping task
        messages: [
          {
            role: "system",
            content: "You are a garment measurement expert. Map measurement names accurately. Return only valid JSON.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        response_format: { type: "json_object" },
        temperature: 0,
        max_tokens: 2000,
      });

      const mappingResult = JSON.parse(completion.choices[0]?.message?.content || "{}");
      console.log("Measurement mapping result:", mappingResult);

      // Build the standardized measurements object
      const standardized: Record<string, number> = {};
      const mapping: Record<string, { standardName: string | null; originalName: string; value: number }> = {};

      for (const [originalName, value] of Object.entries(rawMeasurements)) {
        const standardName = mappingResult[originalName] as string | null;

        mapping[originalName] = {
          standardName: standardName || null,
          originalName,
          value: value as number,
        };

        if (standardName && standardName in STANDARD_MEASUREMENTS) {
          standardized[standardName] = value as number;
        } else if (standardName) {
          // If OpenAI returned a name not in our schema, keep it anyway
          standardized[standardName] = value as number;
        }
      }

      return { standardized, mapping };
    } catch (error) {
      console.error("Error mapping measurements:", error);
      // Fallback to raw measurements
      return {
        standardized: rawMeasurements,
        mapping: Object.fromEntries(
          Object.entries(rawMeasurements).map(([k, v]) => [k, { standardName: null, originalName: k, value: v }])
        ),
      };
    }
  }

  /**
   * Map size specifications array to standardized measurements
   */
  async mapSizeSpecificationsToStandard(
    sizeSpecs: Array<{ size: string; measurements: Record<string, number> }>,
    garmentType?: string,
  ): Promise<Array<{ size: string; measurements: Record<string, number>; rawMeasurements?: Record<string, number> }>> {
    if (!sizeSpecs || sizeSpecs.length === 0) {
      return sizeSpecs;
    }

    // Get all unique measurement names across all sizes
    const allMeasurementNames = new Set<string>();
    for (const spec of sizeSpecs) {
      if (spec.measurements) {
        Object.keys(spec.measurements).forEach(k => allMeasurementNames.add(k));
      }
    }

    // Create a sample measurements object for mapping (use first non-empty size)
    const sampleMeasurements: Record<string, number> = {};
    for (const name of allMeasurementNames) {
      for (const spec of sizeSpecs) {
        if (spec.measurements?.[name] !== undefined) {
          sampleMeasurements[name] = spec.measurements[name];
          break;
        }
      }
    }

    // Get the mapping once for all sizes
    const { mapping } = await this.mapMeasurementsToStandard(sampleMeasurements, garmentType);

    // Apply the mapping to all sizes
    return sizeSpecs.map(spec => {
      const standardizedMeasurements: Record<string, number> = {};

      for (const [originalName, value] of Object.entries(spec.measurements || {})) {
        const mappedInfo = mapping[originalName];
        if (mappedInfo?.standardName) {
          standardizedMeasurements[mappedInfo.standardName] = value;
        } else {
          // Keep unmapped measurements with original name
          standardizedMeasurements[originalName] = value;
        }
      }

      return {
        size: spec.size,
        measurements: standardizedMeasurements,
        rawMeasurements: spec.measurements, // Keep original for reference
      };
    });
  }

  async extractFromFile(
    fileBuffer: Buffer,
    fileName: string,
    mimeType: string,
  ): Promise<TechPackExtractionResult> {
    if (!this.openai) {
      throw new Error("OpenAI API key not configured");
    }

    let textContent = "";
    let structuredData: any = null;

    // Extract text/data based on file type
    if (mimeType === "application/pdf") {
      // For PDFs, we'll handle them differently - send directly to OpenAI
      // PDFs are complex and may contain images, tables, etc.
      return await this.extractFromPDFDirect(fileBuffer, fileName);
    } else if (
      mimeType.includes("spreadsheet") ||
      mimeType.includes("excel") ||
      fileName.endsWith(".xlsx") ||
      fileName.endsWith(".xls")
    ) {
      const result = await this.extractFromExcel(fileBuffer);
      textContent = result.text;
      structuredData = result.data;
    } else if (mimeType.startsWith("image/")) {
      // For images, use GPT-4 Vision
      return await this.extractFromImage(fileBuffer, mimeType);
    } else if (mimeType.includes("text") || mimeType.includes("csv")) {
      textContent = fileBuffer.toString("utf-8");
    } else {
      // Try to parse as text
      textContent = fileBuffer.toString("utf-8");
    }

    // Use GPT-4 to extract structured information
    const prompt = `You are a tech pack analyzer for garment manufacturing. Extract the following information from this tech pack document:

1. Style Reference/SKU
2. Material Composition (fiber types and percentages)
3. Dye Lot information
4. Production Quantities
5. Color Information (main colors, variants, Pantone references)
6. Size Specifications and Measurements (this is CRITICAL - extract all measurements for each size, including but not limited to: chest, length, sleeve, shoulder, hem, waist, hip, inseam, etc.)
7. Technical Specifications (fabric weight, construction, wash care, finishing)

Tech Pack Content:
${textContent}

${structuredData ? `\nStructured Data:\n${JSON.stringify(structuredData, null, 2)}` : ""}

Return a JSON object with the extracted information. For size specifications, create an array where each item has:
- size: the size label (e.g., "S", "M", "L", "38", "40")
- measurements: an object with measurement names as keys and values in cm (convert if needed)

Example format for size specifications:
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
    }
  ]
}

Be thorough in extracting ALL measurements mentioned in the document.`;

    const completion = await this.openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: "You are a technical expert in garment manufacturing and tech pack analysis. Extract structured data accurately.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      response_format: { type: "json_object" },
      temperature: 0,
      max_tokens: 4000,
    });

    const extractedData = JSON.parse(
      completion.choices[0]?.message?.content || "{}",
    );

    return this.formatExtractionResult(extractedData);
  }

  /**
   * Convert PDF pages to images using pdftoppm (from poppler-utils)
   */
  private async convertPdfPagesToImages(buffer: Buffer, dpi: number = 150): Promise<Array<{ pageNumber: number; base64: string; width: number; height: number }>> {
    const images: Array<{ pageNumber: number; base64: string; width: number; height: number }> = [];

    // Check if pdftoppm is available
    if (!pdftoppmAvailable) {
      console.log("pdftoppm not available, skipping PDF page image conversion");
      return images;
    }

    // Create a temp directory for the conversion
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pdf-'));
    const pdfPath = path.join(tempDir, 'input.pdf');
    const outputPrefix = path.join(tempDir, 'page');

    try {
      // Write PDF buffer to temp file
      fs.writeFileSync(pdfPath, buffer);

      // Convert PDF to PNG images using pdftoppm
      // -png: output PNG format
      // -r: resolution (DPI)
      const result = spawnSync('pdftoppm', [
        '-png',
        '-r', dpi.toString(),
        pdfPath,
        outputPrefix,
      ], { timeout: 60000 });

      if (result.error) {
        console.error('pdftoppm error:', result.error);
        return images;
      }

      if (result.status !== 0) {
        console.error('pdftoppm failed:', result.stderr?.toString());
        return images;
      }

      // Read all generated PNG files
      const files = fs.readdirSync(tempDir)
        .filter(f => f.startsWith('page-') && f.endsWith('.png'))
        .sort();

      console.log(`PDF converted to ${files.length} images`);

      for (let i = 0; i < files.length; i++) {
        const filePath = path.join(tempDir, files[i]);
        const imageBuffer = fs.readFileSync(filePath);
        const base64 = imageBuffer.toString('base64');

        // Get image dimensions by reading PNG header
        // PNG signature + IHDR chunk contains width (bytes 16-19) and height (bytes 20-23)
        const width = imageBuffer.readUInt32BE(16);
        const height = imageBuffer.readUInt32BE(20);

        images.push({
          pageNumber: i + 1,
          base64,
          width,
          height,
        });

        console.log(`Loaded page ${i + 1}/${files.length} (${width}x${height})`);
      }
    } catch (error) {
      console.error('Error converting PDF to images:', error);
    } finally {
      // Cleanup temp files
      try {
        const tempFiles = fs.readdirSync(tempDir);
        for (const file of tempFiles) {
          fs.unlinkSync(path.join(tempDir, file));
        }
        fs.rmdirSync(tempDir);
      } catch (cleanupError) {
        console.error('Cleanup error:', cleanupError);
      }
    }

    return images;
  }

  private async extractFromPDFDirect(
    buffer: Buffer,
    fileName: string,
  ): Promise<TechPackExtractionResult> {
    if (!this.openai) {
      throw new Error("OpenAI API key not configured");
    }

    try {
      console.log(`Processing PDF with Vision: ${fileName}, size: ${buffer.length} bytes`);

      // Convert PDF pages to images using pdftoppm
      const pageImages = await this.convertPdfPagesToImages(buffer, 150); // 150 DPI for good quality

      // If pdftoppm is not available, fall back to text-based extraction with Assistants API
      if (pageImages.length === 0) {
        console.log("pdftoppm not available, falling back to Assistants API extraction...");
        return await this.extractFromPDFWithAssistants(buffer, fileName);
      }

      console.log(`Converted ${pageImages.length} pages to images, analyzing with GPT-4 Vision...`);

      // Prepare image content for GPT-4 Vision
      // Process in batches to avoid token limits (max ~4-5 pages per request)
      const batchSize = 4;
      const allExtractedData: any[] = [];

      for (let i = 0; i < pageImages.length; i += batchSize) {
        const batch = pageImages.slice(i, i + batchSize);
        const batchNum = Math.floor(i / batchSize) + 1;
        const totalBatches = Math.ceil(pageImages.length / batchSize);

        console.log(`Processing batch ${batchNum}/${totalBatches} (pages ${i + 1}-${Math.min(i + batchSize, pageImages.length)})`);

        const imageContent: any[] = batch.map((img, idx) => ({
          type: "image_url",
          image_url: {
            url: `data:image/png;base64,${img.base64}`,
            detail: "high",
          },
        }));

        const prompt = `You are an expert tech pack analyzer for garment manufacturing QC systems. Analyze these tech pack pages (pages ${i + 1}-${Math.min(i + batchSize, pageImages.length)} of ${pageImages.length}).

INSTRUCTIONS:
1. Extract ALL information visible in the document - be thorough and comprehensive
2. Translate ALL descriptive text to PORTUGUESE (Brazilian Portuguese)
3. Keep codes/references unchanged (SKUs, article numbers, Pantone codes, stitch codes, POM codes, size labels like XS/S/M/L/XL/XXL or numeric 36/38/40/42)
4. Keep numeric measurements exactly as shown with their units
5. PAY SPECIAL ATTENTION to measurement tables, tolerance tables, BOM tables, and folding/packing diagrams

Return a JSON object. Use these field names when applicable, but extract ANY additional data you find:

{
  "styleReference": "style number, SKU, article number, or product code",
  "productName": "product name or description",
  "productType": "type of garment (e.g., JACKET, PANTS, SHIRT, DRESS)",
  "season": "season or collection (e.g., S2026, FW24)",
  "brand": "brand name",
  "designer": "designer, factory, or manufacturer name",
  "revision": "document revision number if shown",
  "date": "document date if shown",

  "colorways": [{"name": "nome da cor", "colorCode": "código", "pantone": "código Pantone", "hex": "#RRGGBB", "fabric": "cor do tecido", "thread": "cor da linha"}],

  "sizeRange": ["all size labels found in the document - MUST include ALL sizes"],

  "pointsOfMeasure": [
    {
      "pomCode": "código POM (ex: LT018, CH002B, SL001)",
      "name": "nome da medida exatamente como mostrado",
      "description": "descrição de como medir (traduzida para português)",
      "tolerancePlus": "valor de tolerância positiva (número)",
      "toleranceMinus": "valor de tolerância negativa (número)",
      "category": "categoria (Length, Width, Circumference, Opening, etc.)"
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
      "stitchCode": "código de ponto (ex: 301, 401, 504)",
      "seam": "tipo de costura",
      "seamAllowance": "margem de costura",
      "needleType": "tipo de agulha",
      "seamsPerInch": "pontos por polegada",
      "notes": "observações"
    }
  ],

  "billOfMaterials": [
    {
      "category": "categoria EXATA do documento (Main Fabric, Lining, Trim, Label, Zipper, Button, Thread, Elastic, Interlining, Packaging, Hardware, etc.)",
      "itemName": "nome do item",
      "itemCode": "código/artigo do item (ex: 63200036-600, BC-TT-01)",
      "articleNumber": "número do artigo se diferente do itemCode",
      "supplier": "nome do fornecedor",
      "supplierCode": "código do fornecedor (ex: CG NOM, VP, CG SUP)",
      "composition": "composição do material",
      "weight": "peso (ex: 20D, 300GSM)",
      "color": "cor",
      "colorCode": "código da cor",
      "pantone": "código Pantone",
      "size": "dimensões ou tamanho",
      "placement": "posição na peça",
      "quantity": "quantidade",
      "unit": "unidade (m, cm, pcs, yds)",
      "cost": "custo",
      "moq": "quantidade mínima de pedido",
      "leadTime": "prazo de entrega",
      "notes": "notas ou observações"
    }
  ],

  "materialComposition": [{"fiber": "tipo de fibra", "percentage": "número"}],

  "labels": [
    {
      "type": "tipo de etiqueta (Main Label, Care Label, Size Label, Content Label, Flag Label, etc.)",
      "sequence": "número de sequência/ordem (1, 2, 3...)",
      "placement": "posição (inside back neck, side seam, etc.)",
      "material": "material",
      "content": "conteúdo completo",
      "size": "dimensões",
      "foldType": "tipo de dobra (end fold, center fold, etc.)",
      "attachmentMethod": "método de fixação",
      "notes": "observações"
    }
  ],

  "labelSequence": [
    {
      "position": "posição (ex: Back Neck)",
      "sequence": ["Label 1 type", "Label 2 type", "..."],
      "notes": "observações sobre a sequência"
    }
  ],

  "hangTags": [
    {
      "type": "tipo",
      "material": "material",
      "content": "conteúdo",
      "size": "dimensões (W x H)",
      "attachment": "forma de fixação (string, plastic loop, etc.)",
      "attachmentPosition": "posição do furo/fixação",
      "notes": "observações"
    }
  ],

  "foldingInstructions": [
    {
      "step": "número do passo (1, 2, 3...)",
      "description": "descrição detalhada do passo em português",
      "dimensions": "dimensões resultantes se especificadas",
      "notes": "notas adicionais"
    }
  ],

  "packagingInstructions": [
    {
      "step": "número do passo",
      "description": "descrição do passo de embalagem",
      "material": "material usado (polybag, tissue, etc.)",
      "dimensions": "dimensões",
      "notes": "notas"
    }
  ],

  "careInstructions": [
    {
      "language": "idioma (English, Portuguese, French, etc.)",
      "instructions": ["lista de instruções"]
    }
  ],

  "careSymbols": ["símbolos de cuidado (wash, dry, iron, bleach, etc.)"],

  "packaging": [{"type": "tipo de embalagem", "material": "material", "dimensions": "dimensões", "quantity": "quantidade"}],

  "artwork": [
    {
      "type": "tipo de arte (Print, Embroidery, Patch, Heat Transfer, etc.)",
      "name": "nome/descrição da arte",
      "placement": "posição",
      "placementBySize": {
        "S": "posição para tamanho S",
        "M": "posição para tamanho M",
        "L": "posição para tamanho L"
      },
      "technique": "técnica",
      "colors": ["cores utilizadas"],
      "pantones": ["códigos Pantone"],
      "dimensions": "dimensões",
      "notes": "observações"
    }
  ],

  "sampleReview": [
    {
      "pomCode": "código POM",
      "pomName": "nome da medida",
      "targetValue": "valor esperado",
      "actualValue": "valor medido na amostra",
      "tolerance": "tolerância",
      "status": "status (OK, Fail, Adjust)",
      "notes": "observações/comentários de fit"
    }
  ],

  "fitComments": ["comentários de fit e ajustes necessários"],

  "imageRegions": [
    {
      "pageNumber": ${i + 1},
      "type": "tipo de imagem (sketch, measurement_diagram, label, hangtag, artwork, folding_diagram, fabric_swatch, color_reference, pattern, construction_detail, packing_diagram, etc.)",
      "description": "descrição do que mostra a imagem",
      "boundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
      "associatedField": "campo relacionado como foldingInstructions[0]"
    }
  ],

  "additionalInfo": {}
}

CRITICAL EXTRACTION RULES:

1. SIZE SPECIFICATIONS & MEASUREMENTS:
   - Extract EVERY size found (2XS, XS, S, M, L, XL, XXL, 3XL, or numeric sizes)
   - Include ALL measurements for EACH size - do not skip any sizes or measurements
   - Use the EXACT measurement names as shown in the document
   - If measurements have POM codes (like LT018, CH002B), extract them to "pointsOfMeasure"

2. TOLERANCES:
   - Extract tolerance values (+/-) for each measurement if shown
   - If there's a tolerance table, capture ALL tolerances
   - Format: tolerancePlus (positive number), toleranceMinus (positive number representing the absolute value)

3. BILL OF MATERIALS:
   - Extract EVERY item from trim lists, material lists, BOM tables
   - Include article/item codes, supplier codes, and supplier names
   - Use the actual category names shown in the document
   - Include weights, quantities, and units where shown

4. FOLDING & PACKING:
   - Extract ALL folding steps in order (step 1, 2, 3...)
   - Include dimensions for each fold step if specified
   - Extract packaging instructions separately

5. LABELS:
   - Extract the label sequence/order (which labels go first)
   - Include label types, sizes, materials, and placement

6. SAMPLE REVIEW:
   - If sample measurements are shown, extract actual vs target values
   - Include fit comments and adjustments

7. BE THOROUGH: If you see data that doesn't fit the standard fields, add it to "additionalInfo".
8. TRANSLATIONS: Translate descriptions, notes, and instructions to Portuguese. Keep technical codes, brand names, size labels, and POM codes unchanged.
9. Include only fields that have actual data - do not include empty arrays or null values.`;

        const completion = await this.openai.chat.completions.create({
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

        try {
          const batchData = JSON.parse(responseText);
          allExtractedData.push(batchData);
          console.log(`Batch ${batchNum} extracted:`, Object.keys(batchData).length, 'fields');
        } catch (parseError) {
          console.error(`Error parsing batch ${batchNum} response:`, parseError);
          // Retry the batch once with a smaller request
          console.log(`Retrying batch ${batchNum}...`);
          try {
            const retryCompletion = await this.openai.chat.completions.create({
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
            const retryText = retryCompletion.choices[0]?.message?.content || "{}";
            const retryData = JSON.parse(retryText);
            allExtractedData.push(retryData);
            console.log(`Batch ${batchNum} retry succeeded:`, Object.keys(retryData).length, 'fields');
          } catch (retryError) {
            console.error(`Batch ${batchNum} retry also failed:`, retryError);
          }
        }
      }

      // Merge all batch results
      const mergedData = this.mergeBatchResults(allExtractedData);

      // Add page images to the result (for region cropping)
      mergedData.pageImages = pageImages;

      // Add extracted images (full page images)
      mergedData.extractedImages = pageImages.map(img => ({
        base64: img.base64,
        mimeType: 'image/png',
        pageNumber: img.pageNumber,
        width: img.width,
        height: img.height,
      }));

      console.log('Final merged extraction result:', JSON.stringify({
        ...mergedData,
        extractedImages: `[${mergedData.extractedImages?.length || 0} images]`,
      }, null, 2));

      // Map size specifications to standardized measurement names
      if (mergedData.sizeSpecifications && Array.isArray(mergedData.sizeSpecifications) && mergedData.sizeSpecifications.length > 0) {
        console.log('Mapping size specifications to standard measurement names...');
        const garmentType = mergedData.productType || mergedData.garmentCategory;
        try {
          mergedData.sizeSpecifications = await this.mapSizeSpecificationsToStandard(
            mergedData.sizeSpecifications,
            garmentType,
          );
          console.log('Size specifications mapped successfully');
        } catch (mappingError) {
          console.error('Error mapping size specifications:', mappingError);
          // Continue with unmapped measurements
        }
      }

      return this.formatExtractionResult(mergedData);
    } catch (error) {
      console.error('PDF Vision extraction error:', error);
      throw new Error(`Failed to extract tech pack data from PDF: ${error.message}`);
    }
  }

  /**
   * Merge results from multiple batch extractions
   */
  private mergeBatchResults(batches: any[]): any {
    if (batches.length === 0) return {};
    if (batches.length === 1) return batches[0];

    const merged: any = {};

    // Merge header fields - take first non-empty value
    merged.header = {};
    const headerFields = ['styleReference', 'productName', 'productType', 'season', 'brand', 'designer'];
    for (const field of headerFields) {
      for (const batch of batches) {
        const value = batch.header?.[field] || batch[field];
        if (value) {
          merged.header[field] = value;
          break;
        }
      }
    }

    // Legacy simple fields - take first non-empty value (for backward compatibility)
    const simpleFields = ['styleReference', 'productName', 'productType', 'season', 'designer', 'sampleSize'];
    for (const field of simpleFields) {
      for (const batch of batches) {
        if (batch[field]) {
          merged[field] = batch[field];
          break;
        }
      }
    }

    // Merge department data
    this.mergeDepartments(batches, merged);

    // Legacy array fields - merge and deduplicate (for backward compatibility)
    // Also include imageRegions for cropping visual elements
    // Added new QC fields: pointsOfMeasure, labelSequence, packagingInstructions, sampleReview, fitComments, careSymbols
    const arrayFields = [
      'sizeRange', 'colorways', 'sizeSpecifications', 'constructionDetails',
      'artwork', 'fabricMap', 'labels', 'hangTags', 'packaging',
      'careInstructions', 'billOfMaterials', 'materialComposition', 'pageContents',
      'imageRegions', 'foldingInstructions',
      // New QC fields
      'pointsOfMeasure', 'labelSequence', 'packagingInstructions', 'sampleReview',
      'fitComments', 'careSymbols'
    ];

    for (const field of arrayFields) {
      const allItems: any[] = [];
      for (const batch of batches) {
        if (Array.isArray(batch[field])) {
          allItems.push(...batch[field]);
        }
      }
      if (allItems.length > 0) {
        // Simple deduplication based on JSON string
        const seen = new Set<string>();
        merged[field] = allItems.filter(item => {
          const key = JSON.stringify(item);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      }
    }

    // Object fields - merge (deep merge for nested objects)
    const objectFields = ['measurementTolerances', 'additionalInfo', 'grading'];
    for (const field of objectFields) {
      merged[field] = {};
      for (const batch of batches) {
        if (batch[field] && typeof batch[field] === 'object' && !Array.isArray(batch[field])) {
          Object.assign(merged[field], batch[field]);
        }
      }
      if (Object.keys(merged[field]).length === 0) {
        delete merged[field];
      }
    }

    return merged;
  }

  /**
   * Merge department data from multiple batch extractions
   */
  private mergeDepartments(batches: any[], merged: any): void {
    const departments = ['designDepartment', 'patternDepartment', 'productionDepartment',
                         'sourcingDepartment', 'qcDepartment', 'packagingDepartment'];

    for (const dept of departments) {
      const deptData: any = {};

      for (const batch of batches) {
        if (!batch[dept]) continue;

        // Merge each field in the department
        for (const [key, value] of Object.entries(batch[dept])) {
          if (value === null || value === undefined) continue;

          if (Array.isArray(value)) {
            // Merge arrays with deduplication
            if (!deptData[key]) {
              deptData[key] = [];
            }
            const seen = new Set(deptData[key].map((item: any) => JSON.stringify(item)));
            for (const item of value) {
              const itemKey = JSON.stringify(item);
              if (!seen.has(itemKey)) {
                seen.add(itemKey);
                deptData[key].push(item);
              }
            }
          } else if (typeof value === 'object') {
            // Merge objects deeply
            if (!deptData[key]) {
              deptData[key] = {};
            }
            Object.assign(deptData[key], value);
          } else {
            // Simple fields - take first non-empty value
            if (!deptData[key]) {
              deptData[key] = value;
            }
          }
        }
      }

      if (Object.keys(deptData).length > 0) {
        merged[dept] = deptData;
      }
    }
  }

  /**
   * Fallback method using OpenAI Assistants API for text-based extraction
   * Used when canvas is not available for Vision-based extraction
   */
  private async extractFromPDFWithAssistants(
    buffer: Buffer,
    fileName: string,
  ): Promise<TechPackExtractionResult> {
    if (!this.openai) {
      throw new Error("OpenAI API key not configured");
    }

    // Extract text from PDF
    let textContent = "";
    try {
      textContent = await this.extractTextFromPDF(buffer);
      console.log(`Extracted ${textContent.length} characters from PDF text`);
    } catch (e) {
      console.log("Could not extract text from PDF");
    }

    // Upload file to OpenAI
    const file = await this.openai.files.create({
      file: await OpenAI.toFile(buffer, fileName, { type: "application/pdf" }),
      purpose: "assistants",
    });

    console.log(`Uploaded PDF to OpenAI: ${file.id}`);

    // Create an assistant
    const assistant = await this.openai.beta.assistants.create({
      name: "Tech Pack Analyzer",
      instructions: `You are an expert tech pack analyzer for garment manufacturing. Analyze tech pack PDF documents thoroughly and extract all information.
ALWAYS respond with a valid JSON object containing the extracted data.`,
      model: "gpt-4o",
      tools: [{ type: "file_search" }],
    });

    // Create thread with file
    const thread = await this.openai.beta.threads.create({
      messages: [
        {
          role: "user",
          content: `Analyze this tech pack PDF thoroughly and extract ALL information into a JSON object with these fields:
- styleReference, productName, productType, season, designer, sampleSize, sizeRange
- colorways (array with name, pantone, hex, fabric, thread details)
- sizeSpecifications (array with size and measurements object)
- measurementTolerances, grading
- constructionDetails (array with area, description, stitchType, stitchCode, notes)
- artwork (array with type, placement, dimensions, colors, pantones, technique)
- fabricMap (array with zone, fabricType, areas)
- labels, hangTags, packaging (arrays with type, dimensions, material, placement)
- careInstructions (array with language and instructions array)
- billOfMaterials (array with category, item, description, supplier, color, quantity)
- materialComposition (array with fiber and percentage)

Be thorough - extract EVERY measurement, color, and detail.

${textContent ? `\nExtracted text:\n${textContent.substring(0, 8000)}` : ""}`,
          attachments: [
            {
              file_id: file.id,
              tools: [{ type: "file_search" }],
            },
          ],
        },
      ],
    });

    const threadId = thread.id;
    if (!threadId) {
      throw new Error(`Thread creation returned no id`);
    }

    let run = await this.openai.beta.threads.runs.create(threadId, {
      assistant_id: assistant.id,
    });

    // Wait for completion
    const startTime = Date.now();
    const timeout = 120000;

    while (run.status === "in_progress" || run.status === "queued") {
      if (Date.now() - startTime > timeout) {
        throw new Error("PDF processing timeout");
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
      run = await this.openai.beta.threads.runs.retrieve(run.id, { thread_id: threadId });
    }

    if (run.status !== "completed") {
      throw new Error(`Run failed with status: ${run.status}`);
    }

    // Get messages
    const messages = await this.openai.beta.threads.messages.list(threadId);
    const assistantMessage = messages.data.find(m => m.role === "assistant");

    // Cleanup
    try {
      await this.openai.beta.assistants.delete(assistant.id);
      await this.openai.files.delete(file.id);
    } catch (e) {
      console.log("Cleanup error:", e);
    }

    if (!assistantMessage) {
      throw new Error("No response from assistant");
    }

    let responseText = "";
    for (const content of assistantMessage.content) {
      if (content.type === "text") {
        responseText += content.text.value;
      }
    }

    // Parse JSON
    let jsonStr = responseText;
    const jsonMatch = responseText.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      jsonStr = jsonMatch[1];
    }

    const jsonStartIdx = jsonStr.indexOf("{");
    const jsonEndIdx = jsonStr.lastIndexOf("}");
    if (jsonStartIdx !== -1 && jsonEndIdx !== -1) {
      jsonStr = jsonStr.substring(jsonStartIdx, jsonEndIdx + 1);
    }

    const extractedData = JSON.parse(jsonStr);
    console.log('Assistants API extraction result:', JSON.stringify(extractedData, null, 2).substring(0, 500));

    return this.formatExtractionResult(extractedData);
  }

  private async extractFromExcel(
    buffer: Buffer,
  ): Promise<{ text: string; data: any }> {
    try {
      const workbook = XLSX.read(buffer, { type: "buffer" });
      let allText = "";
      const allData: Record<string, any> = {};

      workbook.SheetNames.forEach((sheetName) => {
        const sheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(sheet, { header: 1 });
        const textData = XLSX.utils.sheet_to_csv(sheet);

        allText += `\nSheet: ${sheetName}\n${textData}\n`;
        allData[sheetName] = jsonData;
      });

      return { text: allText, data: allData };
    } catch (error) {
      console.error("Error parsing Excel:", error);
      throw new Error("Failed to parse Excel file");
    }
  }

  private async extractFromImage(
    buffer: Buffer,
    mimeType: string,
  ): Promise<TechPackExtractionResult> {
    if (!this.openai) {
      throw new Error("OpenAI API key not configured");
    }

    const base64Image = buffer.toString("base64");
    const dataUri = `data:${mimeType};base64,${base64Image}`;

    const completion = await this.openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: "You are a technical expert in garment manufacturing and tech pack analysis. Extract structured data accurately from images.",
        },
        {
          role: "user",
          content: [
            {
              type: "text",
              text: `Extract the following information from this tech pack image:
1. Style Reference/SKU
2. Material Composition (fiber types and percentages)
3. Dye Lot information
4. Production Quantities
5. Color Information
6. Size Specifications and ALL Measurements (CRITICAL - extract every measurement for each size)
7. Technical Specifications

Return as JSON with size specifications in this format:
{
  "sizeSpecifications": [
    {
      "size": "S",
      "measurements": {
        "chest": 96,
        "length": 68,
        "sleeve": 60
      }
    }
  ]
}`,
            },
            {
              type: "image_url",
              image_url: {
                url: dataUri,
                detail: "high",
              },
            },
          ],
        },
      ],
      response_format: { type: "json_object" },
      temperature: 0,
      max_tokens: 4000,
    });

    const extractedData = JSON.parse(
      completion.choices[0]?.message?.content || "{}",
    );

    return this.formatExtractionResult(extractedData);
  }

  private formatExtractionResult(data: any): TechPackExtractionResult {
    // Extract header data (from new format or legacy flat fields)
    const header = data.header || {};

    // Build comprehensive extraction result
    const result: TechPackExtractionResult = {
      // Basic Info (from header or legacy flat fields)
      styleRef: header.styleReference || data.styleReference || data.styleRef || data.StyleReference_SKU || data.sku,
      productName: header.productName || data.productName || data.productDescription,
      productType: header.productType || data.productType,
      season: header.season || data.season,
      designer: header.designer || data.designer || data.factoryName || data.factory,
      brand: header.brand || data.brand,
      revision: data.revision,
      date: data.date,
      sampleSize: data.sampleSize,

      // Extracted Images from PDF pages
      extractedImages: data.extractedImages,

      // Image regions for cropping (from GPT-4 Vision detection)
      imageRegions: data.imageRegions,

      // Page images with dimensions (for cropping)
      pageImages: data.pageImages,

      // Department-Organized Data (new structure)
      departments: this.formatDepartments(data),

      // === NEW QC FIELDS ===
      // Points of Measure with POM codes and tolerances
      pointsOfMeasure: data.pointsOfMeasure,

      // Label sequence for QC verification
      labelSequence: data.labelSequence,

      // Packaging instructions (separate from folding)
      packagingInstructions: data.packagingInstructions,

      // Care symbols
      careSymbols: data.careSymbols,

      // Sample review data for QC
      sampleReview: data.sampleReview,

      // Fit comments from sample review
      fitComments: data.fitComments,

      // Size range
      sizeRange: data.sizeRange,

      // Measurement unit
      measurementUnit: data.measurementUnit,

      // Legacy flat fields (for backward compatibility)
      materialComposition: this.parseMaterialComposition(data),
      dyeLot: data.dyeLot || data.DyeLotInformation?.BodyColor || data.dyeLotNumber,
      productionQuantity: this.parseNumber(data.productionQuantity) || this.calculateTotalFromSizes(data.ProductionQuantities || data.productionQuantities),

      // Colors (from designDepartment or legacy)
      colorways: data.designDepartment?.colorways || data.colorways || this.formatColorwaysFromColors(data),

      // Size & Measurements (from patternDepartment or legacy)
      sizeSpecifications: data.patternDepartment?.sizeChart || this.parseSizeSpecifications(data),
      measurementTolerances: data.measurementTolerances,
      grading: data.grading,

      // Construction (from productionDepartment or legacy)
      constructionDetails: data.productionDepartment?.constructionDetails || data.constructionDetails,

      // Artwork (from designDepartment or legacy)
      artwork: data.designDepartment?.artwork || data.artwork,

      // Fabric Map (from productionDepartment or legacy)
      fabricMap: data.productionDepartment?.fabricMap || data.fabricMap,

      // Labels & Packaging (from packagingDepartment or legacy)
      labels: data.packagingDepartment?.labels || data.labels,
      hangTags: data.packagingDepartment?.hangTags || data.hangTags,
      packaging: data.packagingDepartment?.packaging || data.packaging,
      foldingInstructions: data.packagingDepartment?.foldingInstructions || data.foldingInstructions,

      // Care & BOM (from packagingDepartment/sourcingDepartment or legacy)
      careInstructions: this.formatCareInstructionsFromPackaging(data) || data.careInstructions || this.formatCareInstructionsFromWashCare(data),
      billOfMaterials: data.sourcingDepartment?.billOfMaterials || data.billOfMaterials,

      // Raw data for UI (include everything, but exclude large base64 images)
      rawExtractedData: {
        ...data,
        extractedImages: data.extractedImages?.length ? `[${data.extractedImages.length} images]` : undefined,
      },
    };

    // Remove undefined values
    Object.keys(result).forEach(key => {
      if (result[key as keyof TechPackExtractionResult] === undefined) {
        delete result[key as keyof TechPackExtractionResult];
      }
    });

    return result;
  }

  /**
   * Format department data from GPT-4 extraction into structured interface
   */
  private formatDepartments(data: any): TechPackExtractionResult['departments'] {
    const departments: TechPackExtractionResult['departments'] = {};

    // Design Department
    if (data.designDepartment) {
      departments.design = {
        silhouette: data.designDepartment.silhouette,
        fitType: data.designDepartment.fitType,
        garmentCategory: data.designDepartment.garmentCategory,
        colorways: data.designDepartment.colorways,
        artwork: data.designDepartment.artwork,
        sketches: data.designDepartment.sketches,
        technicalDrawings: data.designDepartment.technicalDrawings,
      };
      this.cleanUndefinedFields(departments.design);
    }

    // Pattern/Grading Department
    if (data.patternDepartment) {
      departments.pattern = {
        baseSize: data.patternDepartment.baseSize,
        measurementUnit: data.patternDepartment.measurementUnit,
        sizeRange: data.patternDepartment.sizeRange,
        pointsOfMeasure: data.patternDepartment.pointsOfMeasure,
        sizeChart: data.patternDepartment.sizeChart,
        gradeRules: data.patternDepartment.gradeRules,
        tolerances: data.patternDepartment.tolerances,
      };
      this.cleanUndefinedFields(departments.pattern);
    }

    // Production Department
    if (data.productionDepartment) {
      departments.production = {
        constructionDetails: data.productionDepartment.constructionDetails,
        fabricMap: data.productionDepartment.fabricMap,
        assemblySequence: data.productionDepartment.assemblySequence,
        specialOperations: data.productionDepartment.specialOperations,
      };
      this.cleanUndefinedFields(departments.production);
    }

    // Sourcing Department
    if (data.sourcingDepartment) {
      departments.sourcing = {
        billOfMaterials: data.sourcingDepartment.billOfMaterials,
        fabricSpecs: data.sourcingDepartment.fabricSpecs,
        trimSpecs: data.sourcingDepartment.trimSpecs,
      };
      this.cleanUndefinedFields(departments.sourcing);
    }

    // QC Department
    if (data.qcDepartment) {
      departments.qc = {
        inspectionPoints: data.qcDepartment.inspectionPoints,
        aqlSettings: data.qcDepartment.aqlSettings,
        visualStandards: data.qcDepartment.visualStandards,
        testingRequirements: data.qcDepartment.testingRequirements,
      };
      this.cleanUndefinedFields(departments.qc);
    }

    // Packaging Department
    if (data.packagingDepartment) {
      departments.packaging = {
        labels: data.packagingDepartment.labels,
        hangTags: data.packagingDepartment.hangTags,
        careInstructions: data.packagingDepartment.careInstructions,
        packaging: data.packagingDepartment.packaging,
        foldingInstructions: data.packagingDepartment.foldingInstructions,
        cartonSpecs: data.packagingDepartment.cartonSpecs,
      };
      this.cleanUndefinedFields(departments.packaging);
    }

    // Only return departments if there's data
    return Object.keys(departments).length > 0 ? departments : undefined;
  }

  /**
   * Remove undefined fields from an object
   */
  private cleanUndefinedFields(obj: any): void {
    for (const key of Object.keys(obj)) {
      if (obj[key] === undefined || obj[key] === null) {
        delete obj[key];
      } else if (Array.isArray(obj[key]) && obj[key].length === 0) {
        delete obj[key];
      } else if (typeof obj[key] === 'object' && !Array.isArray(obj[key]) && Object.keys(obj[key]).length === 0) {
        delete obj[key];
      }
    }
  }

  /**
   * Format care instructions from packaging department data
   */
  private formatCareInstructionsFromPackaging(data: any): TechPackExtractionResult['careInstructions'] {
    const packagingCare = data.packagingDepartment?.careInstructions;
    if (!packagingCare) return undefined;

    // If already in the legacy format, return as-is
    if (Array.isArray(packagingCare)) {
      return packagingCare;
    }

    // Convert from new structure
    const result: TechPackExtractionResult['careInstructions'] = [];

    if (packagingCare.instructions && Array.isArray(packagingCare.instructions)) {
      for (const instr of packagingCare.instructions) {
        result.push({
          language: instr.language || 'English',
          instructions: Array.isArray(instr.text) ? instr.text : [instr.text],
        });
      }
    }

    return result.length > 0 ? result : undefined;
  }

  private formatColorwaysFromColors(data: any): TechPackExtractionResult['colorways'] {
    // Convert old color format to new colorways format
    const colors = data.colors || this.formatColorsForUI(data);
    if (!colors || colors.length === 0) return undefined;

    return colors.map((color: any, index: number) => ({
      name: color.name || color,
      pantone: color.pantone,
      isMain: index === 0,
    }));
  }

  private formatCareInstructionsFromWashCare(data: any): TechPackExtractionResult['careInstructions'] {
    const washCare = this.formatWashCareForUI(data);
    if (!washCare || washCare.length === 0) return undefined;

    return [{
      language: 'English',
      instructions: washCare,
    }];
  }

  private formatMaterialCompositionForUI(data: any): any[] {
    // Handle both old format (like MaterialComposition object) and new format (array)
    if (data.materialComposition && Array.isArray(data.materialComposition)) {
      return data.materialComposition;
    }

    if (data.MaterialComposition && typeof data.MaterialComposition === 'object') {
      // Convert object format to array format
      return Object.entries(data.MaterialComposition).map(([component, composition]) => ({
        component,
        composition: composition as string,
      }));
    }

    return [];
  }

  private formatColorsForUI(data: any): any[] {
    if (data.colors && Array.isArray(data.colors)) {
      return data.colors;
    }

    if (data.ColorInformation) {
      const colors = [];
      const colorInfo = data.ColorInformation;

      if (colorInfo.MainColors && Array.isArray(colorInfo.MainColors)) {
        colorInfo.MainColors.forEach((color: string) => {
          const pantone = colorInfo.PantoneReferences?.[color];
          colors.push({
            name: color,
            pantone: pantone || undefined,
          });
        });
      }

      if (colorInfo.Variants && Array.isArray(colorInfo.Variants)) {
        colorInfo.Variants.forEach((variant: string) => {
          if (!colors.find(c => c.name === variant)) {
            colors.push({ name: variant });
          }
        });
      }

      return colors;
    }

    return [];
  }

  private formatSizeSpecificationsForUI(data: any): any[] {
    if (data.sizeSpecifications && Array.isArray(data.sizeSpecifications)) {
      return data.sizeSpecifications;
    }

    if (data.SizeSpecificationsAndMeasurements) {
      // Convert old format to new format
      return Object.entries(data.SizeSpecificationsAndMeasurements).map(([size, measurements]: [string, any]) => ({
        size,
        measurements: this.parseMeasurements(measurements),
      }));
    }

    return [];
  }

  private formatWashCareForUI(data: any): string[] {
    if (data.washCareInstructions && Array.isArray(data.washCareInstructions)) {
      return data.washCareInstructions;
    }

    if (data.TechnicalSpecifications?.WashCare) {
      // Split by comma if it's a string
      if (typeof data.TechnicalSpecifications.WashCare === 'string') {
        return data.TechnicalSpecifications.WashCare.split(',').map((s: string) => s.trim());
      }
      if (Array.isArray(data.TechnicalSpecifications.WashCare)) {
        return data.TechnicalSpecifications.WashCare;
      }
    }

    return [];
  }

  private calculateTotalFromSizes(quantities: any): number | null {
    if (!quantities) return null;

    if (typeof quantities === 'object') {
      return Object.values(quantities).reduce((sum: number, val: any) => {
        const num = this.parseNumber(val);
        return sum + (num || 0);
      }, 0) as number;
    }

    return null;
  }

  private parseMaterialComposition(data: any): Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }> | undefined {
    if (!data.materialComposition && !data.materials && !data.fabricComposition) {
      return undefined;
    }

    const composition = data.materialComposition || data.materials || data.fabricComposition;

    if (Array.isArray(composition)) {
      return composition.map((item: any) => ({
        fiber: item.fiber || item.material || item.name || "",
        percentage: this.parseNumber(item.percentage || item.percent || 0) || 0,
        properties: item.properties,
      }));
    }

    // Try to parse from string format like "100% Cotton" or "80% Cotton, 20% Polyester"
    if (typeof composition === "string") {
      const matches = composition.matchAll(/(\d+)%\s*([^,]+)/g);
      const result = [];
      for (const match of matches) {
        result.push({
          fiber: match[2].trim(),
          percentage: parseInt(match[1]),
        });
      }
      return result.length > 0 ? result : undefined;
    }

    return undefined;
  }

  private parseSizeSpecifications(data: any): Array<{
    size: string;
    measurements: Record<string, number>;
  }> | undefined {
    // Check various possible locations for size data
    const sizeData =
      data.sizeSpecifications ||
      data.sizes ||
      data.sizeChart ||
      data.measurements ||
      data.sizeMeasurements;

    if (!sizeData) {
      return undefined;
    }

    if (Array.isArray(sizeData)) {
      return sizeData.map((item: any) => ({
        size: item.size || item.sizeName || item.label || "",
        measurements: this.parseMeasurements(item.measurements || item),
      }));
    }

    // Handle object format where keys are sizes
    if (typeof sizeData === "object") {
      const result = [];
      for (const [size, measurements] of Object.entries(sizeData)) {
        if (typeof measurements === "object") {
          result.push({
            size,
            measurements: this.parseMeasurements(measurements),
          });
        }
      }
      return result.length > 0 ? result : undefined;
    }

    return undefined;
  }

  private parseMeasurements(data: any): Record<string, number> {
    const measurements: Record<string, number> = {};

    if (!data || typeof data !== "object") {
      return measurements;
    }

    // Common measurement field mappings
    const fieldMappings: Record<string, string[]> = {
      chest: ["chest", "bust", "chest_width", "chest_circumference"],
      length: ["length", "body_length", "front_length", "garment_length"],
      sleeve: ["sleeve", "sleeve_length", "arm_length"],
      shoulder: ["shoulder", "shoulder_width", "shoulder_to_shoulder"],
      waist: ["waist", "waist_width", "waist_circumference"],
      hip: ["hip", "hip_width", "hip_circumference"],
      inseam: ["inseam", "inseam_length", "inside_leg"],
      hem: ["hem", "hem_width", "bottom_width"],
      neck: ["neck", "neck_width", "collar"],
      cuff: ["cuff", "cuff_width", "wrist"],
    };

    // Extract measurements
    for (const [key, value] of Object.entries(data)) {
      if (key === "size" || key === "sizeName" || key === "label") {
        continue; // Skip size label fields
      }

      const numValue = this.parseNumber(value);
      if (numValue !== null) {
        // Try to normalize the field name
        const lowerKey = key.toLowerCase().replace(/[_\-\s]+/g, "_");
        let normalizedKey = lowerKey;

        // Check if this matches any of our known fields
        for (const [standard, variations] of Object.entries(fieldMappings)) {
          if (variations.some(v => lowerKey.includes(v))) {
            normalizedKey = standard;
            break;
          }
        }

        measurements[normalizedKey] = numValue;
      }
    }

    return measurements;
  }

  private parseNumber(value: any): number | null {
    if (value === null || value === undefined) {
      return null;
    }

    if (typeof value === "number") {
      return value;
    }

    if (typeof value === "string") {
      // Remove units and parse
      const cleaned = value.replace(/[^\d.-]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? null : parsed;
    }

    return null;
  }

  private async extractTextFromPDF(buffer: Buffer): Promise<string> {
    return new Promise((resolve, reject) => {
      const textParts: string[] = [];
      let currentPage = 0;
      const pageTexts: Map<number, string[]> = new Map();

      new PdfReader().parseBuffer(buffer, (err: any, item: any) => {
        if (err) {
          reject(err);
          return;
        }

        if (!item) {
          // End of file - combine all text
          const allText: string[] = [];
          for (let page = 0; page <= currentPage; page++) {
            const pageText = pageTexts.get(page);
            if (pageText) {
              allText.push(pageText.join(" "));
            }
          }
          resolve(allText.join("\n"));
          return;
        }

        if (item.page) {
          // New page
          currentPage = item.page - 1;
          if (!pageTexts.has(currentPage)) {
            pageTexts.set(currentPage, []);
          }
        }

        if (item.text) {
          // Text item
          const pageText = pageTexts.get(currentPage) || [];
          pageText.push(item.text);
          pageTexts.set(currentPage, pageText);
        }
      });
    });
  }

  /**
   * Download an image from URL and upload to S3
   */
  async downloadAndUploadImage(
    imageUrl: string,
    tenantId: string,
    techPackId: string,
    imageIndex: number,
  ): Promise<{
    url: string;
    key: string;
  } | null> {
    try {
      console.log(`Downloading image from: ${imageUrl}`);

      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`Failed to download image: ${response.status}`);
      }

      const contentType = response.headers.get("content-type") || "image/png";
      const extension = contentType.includes("jpeg") || contentType.includes("jpg") ? "jpg" : "png";
      const arrayBuffer = await response.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      const key = `tech-packs/${tenantId}/${techPackId}/image-${imageIndex}.${extension}`;

      await this.storageService.uploadFileWithKey(
        key,
        buffer,
        contentType,
        "photos",
      );

      const url = await this.storageService.getPresignedDownloadUrl(key, "photos");
      console.log(`Uploaded image to ${key}`);

      return { url, key };
    } catch (error) {
      console.error(`Error downloading/uploading image:`, error);
      return null;
    }
  }

  /**
   * Upload base64 image to S3
   */
  async uploadBase64Image(
    base64Data: string,
    mimeType: string,
    tenantId: string,
    techPackId: string,
    imageIndex: number,
  ): Promise<{
    url: string;
    key: string;
  } | null> {
    try {
      // Remove data URL prefix if present
      const base64Clean = base64Data.replace(/^data:image\/\w+;base64,/, "");
      const buffer = Buffer.from(base64Clean, "base64");

      const extension = mimeType.includes("jpeg") || mimeType.includes("jpg") ? "jpg" : "png";
      const key = `tech-packs/${tenantId}/${techPackId}/image-${imageIndex}.${extension}`;

      await this.storageService.uploadFileWithKey(
        key,
        buffer,
        mimeType,
        "photos",
      );

      const url = await this.storageService.getPresignedDownloadUrl(key, "photos");
      console.log(`Uploaded base64 image to ${key}`);

      return { url, key };
    } catch (error) {
      console.error(`Error uploading base64 image:`, error);
      return null;
    }
  }

  /**
   * Crop a region from an image using bounding box percentages
   * @param imageBase64 Base64 encoded image
   * @param boundingBox Bounding box as percentages (0-100)
   * @param imageWidth Original image width in pixels
   * @param imageHeight Original image height in pixels
   * @returns Cropped image as base64
   */
  async cropImageRegion(
    imageBase64: string,
    boundingBox: { x: number; y: number; width: number; height: number },
    imageWidth: number,
    imageHeight: number,
  ): Promise<string | null> {
    try {
      const buffer = Buffer.from(imageBase64, 'base64');

      // Convert percentage to pixels
      const left = Math.round((boundingBox.x / 100) * imageWidth);
      const top = Math.round((boundingBox.y / 100) * imageHeight);
      const width = Math.round((boundingBox.width / 100) * imageWidth);
      const height = Math.round((boundingBox.height / 100) * imageHeight);

      // Validate dimensions
      const safeLeft = Math.max(0, Math.min(left, imageWidth - 1));
      const safeTop = Math.max(0, Math.min(top, imageHeight - 1));
      const safeWidth = Math.min(width, imageWidth - safeLeft);
      const safeHeight = Math.min(height, imageHeight - safeTop);

      if (safeWidth < 10 || safeHeight < 10) {
        console.log('Region too small to crop:', { safeWidth, safeHeight });
        return null;
      }

      const croppedBuffer = await sharp(buffer)
        .extract({
          left: safeLeft,
          top: safeTop,
          width: safeWidth,
          height: safeHeight,
        })
        .png()
        .toBuffer();

      return croppedBuffer.toString('base64');
    } catch (error) {
      console.error('Error cropping image region:', error);
      return null;
    }
  }

  /**
   * Process image regions: crop and upload to S3
   * @param pageImages Array of page images with base64 and dimensions
   * @param imageRegions Array of detected image regions with bounding boxes
   * @param tenantId Tenant ID for S3 path
   * @param techPackId Tech Pack ID for S3 path
   * @returns Map of associatedField to uploaded image URL
   */
  async processImageRegions(
    pageImages: Array<{ pageNumber: number; base64: string; width: number; height: number }>,
    imageRegions: ImageRegion[],
    tenantId: string,
    techPackId: string,
  ): Promise<Map<string, string>> {
    const fieldToUrlMap = new Map<string, string>();

    if (!imageRegions || imageRegions.length === 0) {
      console.log('No image regions to process');
      return fieldToUrlMap;
    }

    console.log(`Processing ${imageRegions.length} image regions...`);

    let imageIndex = 0;
    for (const region of imageRegions) {
      // Find the page image for this region
      const pageImage = pageImages.find(p => p.pageNumber === region.pageNumber);
      if (!pageImage) {
        console.log(`Page ${region.pageNumber} not found for region: ${region.description}`);
        continue;
      }

      // Crop the region
      const croppedBase64 = await this.cropImageRegion(
        pageImage.base64,
        region.boundingBox,
        pageImage.width,
        pageImage.height,
      );

      if (!croppedBase64) {
        console.log(`Failed to crop region: ${region.description}`);
        continue;
      }

      // Generate a descriptive key for the image
      const regionType = region.type.replace(/_/g, '-');
      const key = `tech-packs/${tenantId}/${techPackId}/${regionType}-${imageIndex}.png`;

      try {
        // Upload to S3
        await this.storageService.uploadFileWithKey(
          key,
          Buffer.from(croppedBase64, 'base64'),
          'image/png',
          'photos',
        );

        const url = await this.storageService.getPresignedDownloadUrl(key, 'photos');
        console.log(`Uploaded cropped region (${region.type}): ${region.description} -> ${key}`);

        // Map the associated field to the URL
        if (region.associatedField) {
          fieldToUrlMap.set(region.associatedField, url);
        }

        imageIndex++;
      } catch (error) {
        console.error(`Error uploading cropped region:`, error);
      }
    }

    console.log(`Processed ${imageIndex} image regions, mapped ${fieldToUrlMap.size} fields`);
    return fieldToUrlMap;
  }

  /**
   * Associate image URLs with department data fields
   */
  associateImageUrls(
    departments: TechPackExtractionResult['departments'],
    fieldToUrlMap: Map<string, string>,
  ): void {
    if (!departments || fieldToUrlMap.size === 0) return;

    for (const [field, url] of fieldToUrlMap.entries()) {
      // Parse the field path, e.g., "foldingInstructions[0]", "hangTags[0].front", "labels[2]"
      const match = field.match(/^(\w+)\[(\d+)\](?:\.(\w+))?$/);
      if (!match) {
        console.log(`Could not parse field path: ${field}`);
        continue;
      }

      const [, arrayName, indexStr, subField] = match;
      const index = parseInt(indexStr, 10);

      // Find the right department and field
      if (arrayName === 'foldingInstructions' && departments.packaging?.foldingInstructions) {
        if (departments.packaging.foldingInstructions[index]) {
          departments.packaging.foldingInstructions[index].imageUrl = url;
        }
      } else if (arrayName === 'hangTags' && departments.packaging?.hangTags) {
        if (departments.packaging.hangTags[index]) {
          if (subField === 'front') {
            departments.packaging.hangTags[index].frontImageUrl = url;
          } else if (subField === 'back') {
            departments.packaging.hangTags[index].backImageUrl = url;
          }
        }
      } else if (arrayName === 'labels' && departments.packaging?.labels) {
        if (departments.packaging.labels[index]) {
          departments.packaging.labels[index].imageUrl = url;
        }
      } else if (arrayName === 'packaging' && departments.packaging?.packaging) {
        if (departments.packaging.packaging[index]) {
          if (subField === 'front') {
            departments.packaging.packaging[index].frontImageUrl = url;
          } else if (subField === 'back') {
            departments.packaging.packaging[index].backImageUrl = url;
          }
        }
      } else if (arrayName === 'billOfMaterials' && departments.sourcing?.billOfMaterials) {
        if (departments.sourcing.billOfMaterials[index]) {
          departments.sourcing.billOfMaterials[index].swatchImageUrl = url;
        }
      } else if (arrayName === 'colorways' && departments.design?.colorways) {
        if (departments.design.colorways[index]) {
          departments.design.colorways[index].swatchImageUrl = url;
        }
      } else if (arrayName === 'artwork' && departments.design?.artwork) {
        if (departments.design.artwork[index]) {
          departments.design.artwork[index].artworkImageUrl = url;
        }
      } else if (arrayName === 'fabricSpecs' && departments.sourcing?.fabricSpecs) {
        if (departments.sourcing.fabricSpecs[index]) {
          departments.sourcing.fabricSpecs[index].swatchImageUrl = url;
        }
      } else if (arrayName === 'trimSpecs' && departments.sourcing?.trimSpecs) {
        if (departments.sourcing.trimSpecs[index]) {
          departments.sourcing.trimSpecs[index].imageUrl = url;
        }
      } else if (arrayName === 'technicalDrawings' && departments.design?.technicalDrawings) {
        if (departments.design.technicalDrawings[index]) {
          departments.design.technicalDrawings[index].imageUrl = url;
        }
      } else if (arrayName === 'sketches' && departments.design) {
        // Handle sketches.front, sketches.back
        if (!departments.design.sketches) {
          departments.design.sketches = {};
        }
        if (subField === 'front') {
          departments.design.sketches.frontUrl = url;
        } else if (subField === 'back') {
          departments.design.sketches.backUrl = url;
        } else if (subField === 'side') {
          departments.design.sketches.sideUrl = url;
        }
      }
    }
  }
}