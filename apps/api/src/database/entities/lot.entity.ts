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
