import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  ManyToOne,
  JoinColumn,
  Index,
} from "typeorm";
import { Dpp } from "./dpp.entity";

export enum DppAccessView {
  PUBLIC = "PUBLIC",
  RESTRICTED = "RESTRICTED",
}

@Entity("dpp_access_logs")
@Index("idx_dpp_access_dpp", ["dppId"])
@Index("idx_dpp_access_view", ["view"])
@Index("idx_dpp_access_ts", ["timestamp"])
@Index("idx_dpp_access_ip", ["ip"])
export class DppAccessLog {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "dpp_id" })
  dppId: string;

  @Column({
    type: "enum",
    enum: DppAccessView,
  })
  view: DppAccessView;

  @Column({ length: 45 }) // IPv6 max length
  ip: string;

  @Column({ name: "user_agent", length: 1000, nullable: true })
  userAgent: string | null;

  @Column({ type: "timestamp with time zone" })
  timestamp: Date;

  @Column({ name: "user_id", nullable: true })
  userId: string | null;

  @Column({ nullable: true })
  endpoint: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  // Relations
  @ManyToOne(() => Dpp, (dpp) => dpp.accessLogs, { onDelete: "CASCADE" })
  @JoinColumn({ name: "dpp_id" })
  dpp: Dpp;
}