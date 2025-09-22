import * as fs from "fs";
import * as path from "path";
import { DefectType } from "@qa-dashboard/shared";

export interface SampleImage {
  filename: string;
  buffer: Buffer;
  contentType: string;
  variant: "normal" | "defect";
  defectType?: DefectType;
}

export interface SampleImageCollection {
  normal: SampleImage[];
  defect: SampleImage[];
  byDefectType: Record<DefectType, SampleImage[]>;
}

let cachedImages: SampleImageCollection | null = null;

const DEFECT_TYPE_ALIASES: Record<string, DefectType> = {
  stain: DefectType.STAIN,
  stitching: DefectType.STITCHING,
  misprint: DefectType.MISPRINT,
  measurement: DefectType.MEASUREMENT,
  other: DefectType.OTHER,
  tear: DefectType.TEAR_DAMAGE,
  discoloration: DefectType.DISCOLORATION,
  "fabric-defect": DefectType.FABRIC_DEFECT,
  "hardware-issue": DefectType.HARDWARE_ISSUE,
};

const ALL_DEFECT_TYPES = Object.values(DefectType) as DefectType[];

function createEmptyDefectTypeMap(): Record<DefectType, SampleImage[]> {
  return ALL_DEFECT_TYPES.reduce<Record<DefectType, SampleImage[]>>(
    (acc, type) => {
      acc[type] = [];
      return acc;
    },
    {} as Record<DefectType, SampleImage[]>,
  );
}

function resolveContentType(filename: string): string {
  const ext = path.extname(filename).toLowerCase();
  switch (ext) {
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    default:
      return "application/octet-stream";
  }
}

function mapFileNameToDefectType(filename: string): DefectType | undefined {
  const key = filename
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  if (DEFECT_TYPE_ALIASES[key]) {
    return DEFECT_TYPE_ALIASES[key];
  }

  // try more specific replacements (remove prefix like defect-)
  const cleaned = key.replace(/^defect-/, "");
  return DEFECT_TYPE_ALIASES[cleaned];
}

export function loadSampleImages(): SampleImageCollection {
  if (cachedImages) {
    return cachedImages;
  }

  const baseDir = path.resolve(__dirname, "../../../../seed-images");
  let files: string[] = [];

  try {
    files = fs.readdirSync(baseDir);
  } catch (error) {
    console.warn("[sample-images] Seed images directory not found at", baseDir);
    const empty: SampleImageCollection = {
      normal: [],
      defect: [],
      byDefectType: createEmptyDefectTypeMap(),
    };
    cachedImages = empty;
    return empty;
  }

  const normal: SampleImage[] = [];
  const defect: SampleImage[] = [];
  const byDefectType = createEmptyDefectTypeMap();

  for (const file of files) {
    if (!file.match(/\.(png|jpg|jpeg)$/i)) {
      continue;
    }

    const fullPath = path.join(baseDir, file);
    const buffer = fs.readFileSync(fullPath);
    const contentType = resolveContentType(file);

    if (file.startsWith("garment-")) {
      const image: SampleImage = {
        filename: file,
        buffer,
        contentType,
        variant: "normal",
      };
      normal.push(image);
    } else if (file.startsWith("defect-")) {
      const defectType = mapFileNameToDefectType(
        file.replace(/\.(png|jpg|jpeg)$/i, ""),
      );
      const image: SampleImage = {
        filename: file,
        buffer,
        contentType,
        variant: "defect",
        defectType,
      };
      defect.push(image);
      if (defectType) {
        byDefectType[defectType].push(image);
      }
    }
  }

  cachedImages = { normal, defect, byDefectType };
  return cachedImages;
}

export function getRandomNormalImage(): SampleImage | undefined {
  const collection = loadSampleImages();
  if (!collection.normal.length) {
    return undefined;
  }
  return collection.normal[
    Math.floor(Math.random() * collection.normal.length)
  ];
}

export function getRandomDefectImage(
  defectType?: DefectType,
): SampleImage | undefined {
  const collection = loadSampleImages();
  if (defectType) {
    const matches = collection.byDefectType[defectType];
    if (matches && matches.length) {
      return matches[Math.floor(Math.random() * matches.length)];
    }
  }
  if (!collection.defect.length) {
    return undefined;
  }
  return collection.defect[
    Math.floor(Math.random() * collection.defect.length)
  ];
}
