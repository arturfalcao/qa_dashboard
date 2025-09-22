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
import {
  DefectType,
  DefectSeverity,
  ProcessStation,
} from "@qa-dashboard/shared";
import { Tenant } from "./tenant.entity";
import { Garment } from "./garment.entity";

@Entity("inspections")
export class Inspection {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({ name: "garment_id" })
  garmentId: string;

  @Column({ name: "has_defect", default: false })
  hasDefect: boolean;

  @Column({
    name: "defect_type",
    type: "enum",
    enum: DefectType,
    nullable: true,
  })
  defectType?: DefectType;

  @Column({
    name: "defect_severity",
    type: "enum",
    enum: DefectSeverity,
    nullable: true,
  })
  defectSeverity?: DefectSeverity;

  @Column({ type: "text", nullable: true })
  notes?: string;

  @Column({ name: "photo_key_before", length: 255, nullable: true })
  photoKeyBefore?: string;

  @Column({ name: "photo_key_after", length: 255, nullable: true })
  photoKeyAfter?: string;

  @Column({
    name: "process_station",
    type: "enum",
    enum: ProcessStation,
    default: ProcessStation.INITIAL_INSPECTION,
  })
  processStation: ProcessStation;

  @Column({ name: "assigned_worker", length: 255, nullable: true })
  assignedWorker?: string;

  @Column({
    name: "temperature",
    type: "decimal",
    precision: 4,
    scale: 1,
    nullable: true,
  })
  temperature?: number;

  @Column({
    name: "humidity",
    type: "decimal",
    precision: 4,
    scale: 1,
    nullable: true,
  })
  humidity?: number;

  @Column({
    name: "lighting_level",
    type: "decimal",
    precision: 6,
    scale: 1,
    nullable: true,
  })
  lightingLevel?: number;

  @Column({ name: "quality_score", type: "int", nullable: true })
  qualityScore?: number;

  @Column({
    name: "inspected_at",
    type: "timestamptz",
    default: () => "CURRENT_TIMESTAMP",
  })
  inspectedAt: Date;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.inspections, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @ManyToOne(() => Garment, (garment) => garment.inspections, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "garment_id" })
  garment: Garment;
}
