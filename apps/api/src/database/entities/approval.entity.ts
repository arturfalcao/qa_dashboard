import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
  JoinColumn,
} from "typeorm";
import { ApprovalDecision } from "@qa-dashboard/shared";
import { Tenant } from "./tenant.entity";
import { Batch } from "./batch.entity";
import { User } from "./user.entity";

@Entity("approvals")
@Unique(["batchId"])
export class Approval {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({ name: "batch_id" })
  batchId: string;

  @Column({ name: "decided_by" })
  decidedBy: string;

  @Column({
    type: "enum",
    enum: ApprovalDecision,
  })
  decision: ApprovalDecision;

  @Column({ type: "text", nullable: true })
  comment?: string;

  @Column({
    name: "decided_at",
    type: "timestamptz",
    default: () => "CURRENT_TIMESTAMP",
  })
  decidedAt: Date;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.approvals, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @ManyToOne(() => Batch, (batch) => batch.approvals, { onDelete: "CASCADE" })
  @JoinColumn({ name: "batch_id" })
  batch: Batch;

  @ManyToOne(() => User, (user) => user.approvals, { onDelete: "CASCADE" })
  @JoinColumn({ name: "decided_by" })
  user: User;
}
