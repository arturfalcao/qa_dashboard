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
import { Tenant } from "./tenant.entity";
import { Lot } from "./lot.entity";

@Entity("tech_packs")
export class TechPack {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  // Basic Info
  @Column({ name: "style_ref", length: 120 })
  styleRef: string;

  @Column({ name: "product_name", type: "varchar", length: 255, nullable: true })
  productName: string | null;

  @Column({ name: "season", type: "varchar", length: 50, nullable: true })
  season: string | null;

  @Column({ name: "designer", type: "varchar", length: 120, nullable: true })
  designer: string | null;

  @Column({ name: "sample_size", type: "varchar", length: 50, nullable: true })
  sampleSize: string | null;

  @Column({ name: "size_range", type: "jsonb", nullable: true })
  sizeRange: string[] | null;

  // File Storage
  @Column({ name: "file_key", type: "varchar", length: 500, nullable: true })
  fileKey: string | null;

  @Column({ name: "file_name", type: "varchar", length: 255, nullable: true })
  fileName: string | null;

  @Column({ name: "file_size", type: "int", nullable: true })
  fileSize: number | null;

  // Processing Status
  @Column({
    name: "status",
    type: "varchar",
    length: 50,
    default: "pending",
  })
  status: "pending" | "processing" | "completed" | "failed";

  @Column({ name: "processing_error", type: "text", nullable: true })
  processingError: string | null;

  // Materials
  @Column({
    name: "material_composition",
    type: "jsonb",
    nullable: true,
  })
  materialComposition: Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }> | null;

  // Colorways
  @Column({
    name: "colorways",
    type: "jsonb",
    nullable: true,
  })
  colorways: Array<{
    name: string;
    pantone?: string;
    fabric?: { name: string; weight?: string; finish?: string };
    thread?: { color: string; type?: string };
    trim?: { description: string; color?: string };
    isMain?: boolean;
  }> | null;

  // Size & Measurements
  @Column({
    name: "size_specifications",
    type: "jsonb",
    nullable: true,
  })
  sizeSpecifications: Array<{
    size: string;
    measurements: Record<string, number>;
  }> | null;

  @Column({
    name: "measurement_tolerances",
    type: "jsonb",
    nullable: true,
  })
  measurementTolerances: Record<string, number> | null;

  @Column({
    name: "grading",
    type: "jsonb",
    nullable: true,
  })
  grading: Array<{
    measurement: string;
    sizes: Record<string, number>;
  }> | null;

  // Construction
  @Column({
    name: "construction_details",
    type: "jsonb",
    nullable: true,
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

  // Artwork
  @Column({
    name: "artwork",
    type: "jsonb",
    nullable: true,
  })
  artwork: Array<{
    type: string;
    placement: string;
    width?: string;
    height?: string;
    colors?: string[];
    pantones?: string[];
    technique?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  // Fabric Map
  @Column({
    name: "fabric_map",
    type: "jsonb",
    nullable: true,
  })
  fabricMap: Array<{
    zone: string;
    fabricType: string;
    areas: string[];
  }> | null;

  // Labels
  @Column({
    name: "labels",
    type: "jsonb",
    nullable: true,
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

  // Hang Tags
  @Column({
    name: "hang_tags",
    type: "jsonb",
    nullable: true,
  })
  hangTags: Array<{
    width?: string;
    height?: string;
    material?: string;
    colors?: string[];
    attachment?: string;
    artworkUrl?: string;
    imageUrl?: string;
    notes?: string;
  }> | null;

  // Packaging
  @Column({
    name: "packaging",
    type: "jsonb",
    nullable: true,
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

  // Folding Instructions
  @Column({
    name: "folding_instructions",
    type: "jsonb",
    nullable: true,
  })
  foldingInstructions: Array<{
    step: number;
    description: string;
    imageUrl?: string;
  }> | null;

  // Care Instructions
  @Column({
    name: "care_instructions",
    type: "jsonb",
    nullable: true,
  })
  careInstructions: Array<{
    language: string;
    instructions: string[];
  }> | null;

  // Bill of Materials
  @Column({
    name: "bill_of_materials",
    type: "jsonb",
    nullable: true,
  })
  billOfMaterials: Array<{
    category: string;
    description: string;
    supplier?: string;
    articleNo?: string;
    color?: string;
    size?: string;
    placement?: string;
    cost?: number;
    quantity?: number;
    notes?: string;
  }> | null;

  // Extracted Images from the tech pack
  @Column({
    name: "images",
    type: "jsonb",
    nullable: true,
  })
  images: Array<{
    url: string;
    key: string;
    pageNumber?: number;
    width?: number;
    height?: number;
    description?: string;
    type?: string; // 'product', 'colorway', 'artwork', 'label', 'construction', 'other'
  }> | null;

  // Raw extracted data (for debugging/future use)
  @Column({
    name: "raw_extracted_data",
    type: "jsonb",
    nullable: true,
  })
  rawExtractedData: Record<string, any> | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @Column({ name: "processed_at", type: "timestamp", nullable: true })
  processedAt: Date | null;

  // Relations
  @ManyToOne(() => Tenant, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @OneToMany(() => Lot, (lot) => lot.techPack)
  lots: Lot[];
}
