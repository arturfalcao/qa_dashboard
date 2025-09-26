import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from "typeorm";
import { ReportStatus, ReportType, ReportLanguage } from "@qa-dashboard/shared";
import { Client } from "./client.entity";
import { Lot } from "./lot.entity";
import { User } from "./user.entity";

@Entity("reports")
export class Report {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ type: "enum", enum: ReportType })
  type: ReportType;

  @Column({ name: "client_id", type: "uuid" })
  clientId: string;

  @Column({ name: "user_id", type: "uuid", nullable: true })
  userId?: string;

  @Column({ name: "lot_id", type: "uuid", nullable: true })
  lotId?: string | null;

  @Column({
    type: "enum",
    enum: ReportLanguage,
    default: ReportLanguage.EN,
  })
  language: ReportLanguage;

  @Column({ type: "enum", enum: ReportStatus, default: ReportStatus.PENDING })
  status: ReportStatus;

  @Column({ name: "file_name" })
  fileName: string;

  @Column({ name: "file_path", nullable: true })
  filePath?: string;

  @Column({ name: "file_url", nullable: true })
  fileUrl?: string;

  @Column({ name: "file_size", type: "int", nullable: true })
  fileSize?: number;

  @Column({
    name: "parameters",
    type: "jsonb",
    comment: "Parameters used to generate the report",
  })
  parameters: Record<string, any>;

  @Column({
    name: "metadata",
    type: "jsonb",
    nullable: true,
    comment: "Additional metadata about the report",
  })
  metadata?: Record<string, any>;

  @Column({ name: "generated_at", type: "timestamp", nullable: true })
  generatedAt?: Date;

  @Column({ name: "expires_at", type: "timestamp", nullable: true })
  expiresAt?: Date;

  @Column({ name: "error_message", type: "text", nullable: true })
  errorMessage?: string;

  @Column({ name: "generation_time_ms", type: "int", nullable: true })
  generationTimeMs?: number;

  // Legacy fields for backward compatibility
  @Column({ type: "date", nullable: true })
  month?: string | null;

  @Column({ type: "text", nullable: true })
  url?: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  // Relations
  @ManyToOne(() => Client, (client) => client.reports, { onDelete: "CASCADE" })
  @JoinColumn({ name: "client_id" })
  client: Client;

  @ManyToOne(() => User, { nullable: true })
  @JoinColumn({ name: "user_id" })
  user?: User;

  @ManyToOne(() => Lot, (lot) => lot.reports, {
    nullable: true,
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "lot_id" })
  lot?: Lot | null;
}
