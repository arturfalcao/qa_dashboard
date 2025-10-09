import { Injectable } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import OpenAI from "openai";
import * as XLSX from "xlsx";
import { PdfReader } from "pdfreader";
import { StorageService } from "../storage/storage.service";

export interface TechPackExtractionResult {
  styleRef?: string;
  materialComposition?: Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }>;
  dyeLot?: string;
  productionQuantity?: number;
  colorInformation?: {
    mainColor?: string;
    colorVariants?: string[];
    pantoneReferences?: string[];
  };
  sizeSpecifications?: Array<{
    size: string;
    measurements: Record<string, number>;
  }>;
  technicalSpecs?: {
    fabricWeight?: string;
    fabricConstruction?: string;
    washCareInstructions?: string[];
    finishingDetails?: string[];
  };
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

  private async extractFromPDFDirect(
    buffer: Buffer,
    fileName: string,
  ): Promise<TechPackExtractionResult> {
    if (!this.openai) {
      throw new Error("OpenAI API key not configured");
    }

    try {
      // Extract text from PDF
      console.log(`Processing PDF: ${fileName}, size: ${buffer.length} bytes`);
      const textContent = await this.extractTextFromPDF(buffer);

      console.log(`Extracted ${textContent.length} characters from PDF`);

      if (!textContent || textContent.trim().length < 10) {
        throw new Error("Could not extract meaningful text from PDF. The PDF might be image-based or corrupted.");
      }

      const prompt = `You are a tech pack analyzer for garment manufacturing. Extract the following information from this tech pack PDF document:

1. Style Reference/SKU
2. Product Name/Description
3. Season
4. Factory Name
5. Material Composition (fiber types and percentages for each component like Body, Lining, Trim)
6. Dye Lot information
7. Production Quantities
8. Color Information (main colors, variants, Pantone references)
9. Size Specifications and Measurements (CRITICAL - extract ALL measurements for EVERY size)
10. Fabric Weight
11. Wash Care Instructions
12. Certifications

Tech Pack Content:
${textContent}

Return a JSON object with the extracted information in this EXACT format:
{
  "styleReference": "string",
  "productName": "string",
  "season": "string",
  "factoryName": "string",
  "dyeLot": "string",
  "fabricWeight": "string",
  "productionQuantity": number,
  "materialComposition": [
    {
      "component": "Body/Lining/etc",
      "composition": "65% Cotton, 35% Polyester"
    }
  ],
  "colors": [
    {
      "name": "Navy Blue",
      "pantone": "19-4023 TCX"
    }
  ],
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
  ],
  "washCareInstructions": ["instruction1", "instruction2"],
  "certifications": ["cert1", "cert2"]
}

Be thorough and extract ALL information present in the document. If a field is not found, omit it from the JSON.`;

      const response = await this.openai.chat.completions.create({
        model: "gpt-4o",
        messages: [
          {
            role: "system",
            content: "You are a technical expert in garment manufacturing and tech pack analysis. Extract complete and accurate structured data from tech pack documents.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        response_format: { type: "json_object" },
        temperature: 0,
        max_tokens: 4096,
      });

      const extractedData = JSON.parse(
        response.choices[0]?.message?.content || "{}",
      );

      console.log('OpenAI PDF extraction result:', JSON.stringify(extractedData, null, 2));

      // Return the properly formatted result
      return this.formatExtractionResult(extractedData);
    } catch (error) {
      console.error('PDF extraction error:', error);
      throw new Error(`Failed to extract tech pack data from PDF: ${error.message}`);
    }
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
    // First, ensure the raw data is properly structured for the UI
    const structuredData = {
      styleReference: data.styleReference || data.styleRef || data.StyleReference_SKU || data.sku,
      productName: data.productName || data.productDescription,
      season: data.season,
      factoryName: data.factoryName || data.factory,
      dyeLot: data.dyeLot || data.DyeLotInformation?.BodyColor || data.dyeLotNumber,
      fabricWeight: data.fabricWeight || data.TechnicalSpecifications?.FabricWeight || data.technicalSpecs?.fabricWeight,
      productionQuantity: this.parseNumber(data.productionQuantity) || this.calculateTotalFromSizes(data.ProductionQuantities || data.productionQuantities),
      materialComposition: this.formatMaterialCompositionForUI(data),
      colors: this.formatColorsForUI(data),
      sizeSpecifications: this.formatSizeSpecificationsForUI(data),
      washCareInstructions: this.formatWashCareForUI(data),
      certifications: data.certifications || [],
      technicalSpecs: data.technicalSpecs || {},
    };

    return {
      styleRef: structuredData.styleReference,
      materialComposition: this.parseMaterialComposition(data),
      dyeLot: structuredData.dyeLot,
      productionQuantity: structuredData.productionQuantity,
      colorInformation: {
        mainColor: data.mainColor || data.color,
        colorVariants: data.colorVariants || data.colors || [],
        pantoneReferences: data.pantoneReferences || data.pantones || [],
      },
      sizeSpecifications: this.parseSizeSpecifications(data),
      technicalSpecs: {
        fabricWeight: structuredData.fabricWeight,
        fabricConstruction: data.fabricConstruction || data.technicalSpecs?.fabricConstruction,
        washCareInstructions: Array.isArray(data.washCare)
          ? data.washCare
          : data.washCareInstructions || [],
        finishingDetails: Array.isArray(data.finishing)
          ? data.finishing
          : data.finishingDetails || [],
      },
      rawExtractedData: structuredData, // Use the structured data for the UI
    };
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
}