import { z } from "zod";

// Public payload schema
export const MaterialSchema = z.object({
  fiber: z.string(),
  percent: z.number().min(0).max(100),
  certs: z.array(z.string()).default([]),
});

export const CareSchema = z.object({
  wash: z.string().optional(),
  dry: z.string().optional(),
  iron: z.string().optional(),
  repair: z.string().optional(),
});

export const SustainabilitySchema = z.object({
  highlights: z.array(z.string()).default([]),
  certifications: z.array(z.string()).default([]),
});

export const EndOfLifeSchema = z.object({
  reuse: z.string().optional(),
  recycle: z.string().optional(),
  contact: z.string().optional(),
});

export const ProductSchema = z.object({
  brand: z.string(),
  styleRef: z.string(),
  sku: z.string(),
  gtin: z.string().nullable().optional(),
  images: z.array(z.string()).default([]),
});

export const PublicPayloadSchema = z.object({
  product: ProductSchema,
  materials: z.array(MaterialSchema).default([]),
  care: CareSchema.default({}),
  sustainability: SustainabilitySchema.default({}),
  end_of_life: EndOfLifeSchema.default({}),
});

// Restricted payload schema
export const FactorySchema = z.object({
  name: z.string(),
  country: z.string(),
  address: z.string().optional(),
});

export const SupplyChainRoleSchema = z.object({
  role: z.enum([
    "CUTTING",
    "DYEING",
    "SEWING",
    "SCREEN_PRINTING",
    "PACKING_EXT",
    "FIBRE_PREP",
    "QUALITY",
    "LAUNDRY",
    "LOGISTICS",
    "PACKAGING",
  ]),
  factory: FactorySchema,
});

export const InspectionSchema = z.object({
  lotId: z.string(),
  defectRate: z.number(),
  topDefects: z.array(z.object({
    type: z.string(),
    count: z.number(),
  })).default([]),
  reportUrl: z.string().optional(),
});

export const MeasurementSchema = z.object({
  lotId: z.string(),
  garmentType: z.string(),
  measures: z.record(z.number()), // key-value pairs for measurements
  overlayUrl: z.string().optional(),
});

export const QualitySchema = z.object({
  inspections: z.array(InspectionSchema).default([]),
  measurements: z.array(MeasurementSchema).default([]),
});

export const ComplianceDocumentSchema = z.object({
  type: z.string(),
  url: z.string(),
});

export const ComplianceSchema = z.object({
  documents: z.array(ComplianceDocumentSchema).default([]),
});

export const RestrictedPayloadSchema = z.object({
  supply_chain: z.array(SupplyChainRoleSchema).default([]),
  quality: QualitySchema.default({}),
  compliance: ComplianceSchema.default({}),
});

// Main DPP creation/update schemas
export const CreateDppSchema = z.object({
  productSku: z.string().min(1),
  gtin: z.string().nullable().optional(),
  brand: z.string().min(1),
  styleRef: z.string().min(1),
  publicPayload: PublicPayloadSchema,
  restrictedPayload: RestrictedPayloadSchema.optional().default({}),
  schemaVersion: z.string().default("textile.v0.1"),
});

export const UpdateDppSchema = z.object({
  productSku: z.string().min(1).optional(),
  gtin: z.string().nullable().optional(),
  brand: z.string().min(1).optional(),
  styleRef: z.string().min(1).optional(),
  publicPayload: PublicPayloadSchema.optional(),
  restrictedPayload: RestrictedPayloadSchema.optional(),
  schemaVersion: z.string().optional(),
});

export const CreateEventSchema = z.object({
  type: z.enum([
    "CREATED",
    "PUBLISHED",
    "PRODUCTION",
    "INSPECTION",
    "PACKING",
    "SHIPMENT",
    "REPAIR",
    "RECYCLE",
    "OTHER",
  ]),
  actor: z.string(),
  location: z.string().optional(),
  timestamp: z.date().optional(),
  data: z.record(z.any()).default({}),
});

// Export types
export type CreateDppDto = z.infer<typeof CreateDppSchema>;
export type UpdateDppDto = z.infer<typeof UpdateDppSchema>;
export type CreateEventDto = z.infer<typeof CreateEventSchema>;
export type PublicPayload = z.infer<typeof PublicPayloadSchema>;
export type RestrictedPayload = z.infer<typeof RestrictedPayloadSchema>;