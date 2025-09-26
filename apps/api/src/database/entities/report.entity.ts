import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from "typeorm";
import { ReportStatus, ReportType } from "@qa-dashboard/shared";
import { Client } from "./client.entity";
import { Lot } from "./lot.entity";

@Entity("reports")
export class Report {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ type: "enum", enum: ReportType })
  type: ReportType;

  @Column({ name: "client_id", type: "uuid", nullable: true })
  clientId?: string | null;

  @Column({ name: "lot_id", type: "uuid", nullable: true })
  lotId?: string | null;

  @Column({ type: "date", nullable: true })
  month?: string | null;

  @Column({ type: "text", nullable: true })
  url?: string | null;

  @Column({ type: "enum", enum: ReportStatus, default: ReportStatus.PENDING })
  status: ReportStatus;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Client, (client) => client.reports, {
    nullable: true,
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "client_id" })
  client?: Client | null;

  @ManyToOne(() => Lot, (lot) => lot.reports, {
    nullable: true,
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "lot_id" })
  lot?: Lot | null;
}
