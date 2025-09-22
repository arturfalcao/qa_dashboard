import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
} from "typeorm";
import { ProcessStation } from "@qa-dashboard/shared";
import { Tenant } from "./tenant.entity";
import { Batch } from "./batch.entity";
import { User } from "./user.entity";

@Entity("batch_process_progress")
export class BatchProcessProgress {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({ name: "batch_id" })
  batchId: string;

  @Column({
    type: "enum",
    enum: ProcessStation,
  })
  station: ProcessStation;

  @Column({ name: "started_at", type: "timestamptz", nullable: true })
  startedAt?: Date;

  @Column({ name: "completed_at", type: "timestamptz", nullable: true })
  completedAt?: Date;

  @Column({ name: "assigned_worker", nullable: true })
  assignedWorker?: string;

  @Column({ type: "text", nullable: true })
  notes?: string;

  @Column({ name: "quality_score", type: "int", nullable: true })
  qualityScore?: number;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @ManyToOne(() => Batch, { onDelete: "CASCADE" })
  @JoinColumn({ name: "batch_id" })
  batch: Batch;

  @ManyToOne(() => User, { nullable: true })
  @JoinColumn({ name: "assigned_worker" })
  worker?: User;
}
