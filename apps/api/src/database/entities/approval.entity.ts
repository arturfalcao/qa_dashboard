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
import { Lot } from "./lot.entity";
import { User } from "./user.entity";

@Entity("approvals")
@Unique(["lotId"])
export class Approval {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ name: "approved_by", nullable: true })
  approvedBy?: string;

  @Column({
    type: "enum",
    enum: ApprovalDecision,
  })
  decision: ApprovalDecision;

  @Column({ type: "text", nullable: true })
  note?: string;

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

  @ManyToOne(() => Lot, (lot) => lot.approvals, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;

  @ManyToOne(() => User, (user) => user.approvals, { onDelete: "SET NULL" })
  @JoinColumn({ name: "approved_by" })
  user?: User | null;
}
