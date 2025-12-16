import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
} from "typeorm";
import { LotStatus, GarmentType } from "@qa-dashboard/shared";
import { Tenant } from "./tenant.entity";
import { Client } from "./client.entity";
import { Factory } from "./factory.entity";
import { Inspection } from "./inspection.entity";
import { Approval } from "./approval.entity";
import { Activity } from "./activity.entity";
import { Report } from "./report.entity";
import { LotFactory } from "./lot-factory.entity";
import { LotUserAssignment } from "./lot-user-assignment.entity";
import { InspectionSession } from "./inspection-session.entity";
import { TechPack } from "./tech-pack.entity";

const numericTransformer = {
  to: (value?: number | null) => value ?? 0,
  from: (value?: string | null) => (value == null ? 0 : parseFloat(value)),
};

@Entity("lots")
export class Lot {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({ name: "client_id", nullable: true })
  clientId?: string | null;

  @Column({ name: "factory_id" })
  factoryId: string;

  @Column({ name: "style_ref", length: 120 })
  styleRef: string;

  @Column({
    name: "garment_type",
    type: "enum",
    enum: GarmentType,
    nullable: true,
  })
  garmentType: GarmentType | null;

  @Column({ name: "quantity_total", type: "int" })
  quantityTotal: number;

  @Column({
    type: "enum",
    enum: LotStatus,
    default: LotStatus.PLANNED,
  })
  status: LotStatus;

  @Column({
    name: "defect_rate",
    type: "numeric",
    precision: 5,
    scale: 2,
    default: 0,
    transformer: numericTransformer,
  })
  defectRate: number;

  @Column({
    name: "inspected_progress",
    type: "numeric",
    precision: 5,
    scale: 2,
    default: 0,
    transformer: numericTransformer,
  })
  inspectedProgress: number;

  // DPP Hub Data
  @Column({
    name: "material_composition",
    type: "jsonb",
    nullable: true,
    comment: "Array of materials with fiber type, percentage, and optional properties",
  })
  materialComposition: Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }> | null;

  @Column({
    name: "dye_lot",
    type: "varchar",
    length: 120,
    nullable: true,
    comment: "Dye lot identifier for traceability",
  })
  dyeLot: string | null;

  @Column({
    name: "certifications",
    type: "jsonb",
    nullable: true,
    comment: "Array of certifications with type, number, and audit links",
  })
  certifications: Array<{
    type: string;
    number?: string;
    auditLink?: string;
    validUntil?: string;
    issuer?: string;
  }> | null;

  @Column({
    name: "dpp_metadata",
    type: "jsonb",
    nullable: true,
    comment: "Additional DPP-specific metadata",
  })
  dppMetadata: Record<string, any> | null;

  // Tech Pack Fields
  @Column({
    name: "tech_pack_file_key",
    type: "varchar",
    length: 500,
    nullable: true,
    comment: "Storage key for the uploaded tech pack file",
  })
  techPackFileKey: string | null;

  @Column({
    name: "tech_pack_data",
    type: "jsonb",
    nullable: true,
    comment: "AI-extracted structured data from tech pack",
  })
  techPackData: Record<string, any> | null;

  @Column({
    name: "size_specifications",
    type: "jsonb",
    nullable: true,
    comment: "Size specifications with quantities and measurements per size",
  })
  sizeSpecifications: Array<{
    size: string;
    quantity?: number;
    measurements?: Record<string, number>;
  }> | null;

  @Column({
    name: "tech_pack_status",
    type: "varchar",
    length: 50,
    nullable: true,
    comment: "Status of tech pack processing: pending, processing, completed, failed",
  })
  techPackStatus: "pending" | "processing" | "completed" | "failed" | null;

  @Column({
    name: "tech_pack_uploaded_at",
    type: "timestamp",
    nullable: true,
    comment: "Timestamp when tech pack was uploaded",
  })
  techPackUploadedAt: Date | null;

  @Column({
    name: "labels",
    type: "jsonb",
    nullable: true,
    comment: "Label specifications from tech pack",
  })
  labels: Array<{
    type: string;
    width?: string;
    height?: string;
    material?: string;
    placement?: string;
    colors?: string[];
    artworkUrl?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  @Column({
    name: "hang_tags",
    type: "jsonb",
    nullable: true,
    comment: "Hang tag specifications from tech pack",
  })
  hangTags: Array<{
    width?: string;
    height?: string;
    material?: string;
    colors?: string[];
    artworkUrl?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  @Column({
    name: "packaging",
    type: "jsonb",
    nullable: true,
    comment: "Packaging specifications from tech pack",
  })
  packaging: Array<{
    type: string;
    width?: string;
    height?: string;
    material?: string;
    artworkUrl?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  @Column({
    name: "folding_instructions",
    type: "jsonb",
    nullable: true,
    comment: "Folding instructions from tech pack",
  })
  foldingInstructions: Array<{
    step: number;
    description: string;
    imageUrl?: string;
  }> | null;

  @Column({
    name: "bill_of_materials",
    type: "jsonb",
    nullable: true,
    comment: "Bill of materials from tech pack",
  })
  billOfMaterials: Array<{
    category: string;
    description: string;
    supplier?: string;
    color?: string;
    size?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  // Extended Tech Pack Fields
  @Column({
    name: "season",
    type: "varchar",
    length: 50,
    nullable: true,
    comment: "Season/collection e.g. S/S 2025, F/W 2024",
  })
  season: string | null;

  @Column({
    name: "designer",
    type: "varchar",
    length: 120,
    nullable: true,
    comment: "Designer or brand name",
  })
  designer: string | null;

  @Column({
    name: "sample_size",
    type: "varchar",
    length: 50,
    nullable: true,
    comment: "Base sample size for measurements",
  })
  sampleSize: string | null;

  @Column({
    name: "product_name",
    type: "varchar",
    length: 255,
    nullable: true,
    comment: "Full product name/description",
  })
  productName: string | null;

  @Column({
    name: "colorways",
    type: "jsonb",
    nullable: true,
    comment: "Color specifications with Pantone refs, fabric, thread, trim details",
  })
  colorways: Array<{
    name: string;
    pantone?: string;
    fabric?: { name: string; weight?: string; finish?: string };
    thread?: { color: string; type?: string };
    trim?: { description: string; color?: string };
    isMain?: boolean;
  }> | null;

  @Column({
    name: "construction_details",
    type: "jsonb",
    nullable: true,
    comment: "Construction and stitching specifications per garment area",
  })
  constructionDetails: Array<{
    area: string;
    description: string;
    stitchType?: string;
    stitchCode?: string;
    needleType?: string;
    seamsPerInch?: number;
    notes?: string;
  }> | null;

  @Column({
    name: "artwork",
    type: "jsonb",
    nullable: true,
    comment: "Artwork, prints, embroidery specifications",
  })
  artwork: Array<{
    type: string; // print, embroidery, flockprint, etc.
    placement: string;
    width?: string;
    height?: string;
    colors?: string[];
    pantones?: string[];
    technique?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  @Column({
    name: "fabric_map",
    type: "jsonb",
    nullable: true,
    comment: "Fabric placement map showing main/sub/trim/lining zones",
  })
  fabricMap: Array<{
    zone: string; // main, sub, trim, lining, etc.
    fabricType: string;
    areas: string[];
  }> | null;

  @Column({
    name: "care_instructions",
    type: "jsonb",
    nullable: true,
    comment: "Care and wash instructions in multiple languages",
  })
  careInstructions: Array<{
    language: string;
    instructions: string[];
  }> | null;

  @Column({
    name: "measurement_tolerances",
    type: "jsonb",
    nullable: true,
    comment: "Tolerance specifications per measurement point",
  })
  measurementTolerances: Record<string, number> | null;

  @Column({
    name: "grading",
    type: "jsonb",
    nullable: true,
    comment: "Size grading specifications showing increments between sizes",
  })
  grading: Array<{
    measurement: string;
    sizes: Record<string, number>;
  }> | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.lots, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @ManyToOne(() => Client, (client) => client.lots, {
    nullable: true,
    onDelete: "SET NULL"
  })
  @JoinColumn({ name: "client_id" })
  client?: Client | null;

  @ManyToOne(() => Factory, (factory) => factory.lots, { onDelete: "CASCADE" })
  @JoinColumn({ name: "factory_id" })
  factory: Factory;

  @Column({ name: "tech_pack_id", nullable: true })
  techPackId?: string | null;

  @ManyToOne(() => TechPack, (techPack) => techPack.lots, {
    nullable: true,
    onDelete: "SET NULL"
  })
  @JoinColumn({ name: "tech_pack_id" })
  techPack?: TechPack | null;

  @OneToMany(() => Inspection, (inspection) => inspection.lot)
  inspections: Inspection[];

  @OneToMany(() => LotFactory, (lotFactory) => lotFactory.lot, {
    cascade: true,
  })
  suppliers: LotFactory[];

  @OneToMany(() => Approval, (approval) => approval.lot)
  approvals: Approval[];

  @OneToMany(() => Activity, (activity) => activity.lot)
  activities: Activity[];

  @OneToMany(() => Report, (report) => report.lot)
  reports: Report[];

  @OneToMany(() => LotUserAssignment, (assignment) => assignment.lot)
  assignments: LotUserAssignment[];
}
