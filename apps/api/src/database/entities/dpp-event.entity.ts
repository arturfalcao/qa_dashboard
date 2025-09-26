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

export enum DppEventType {
  CREATED = "CREATED",
  PUBLISHED = "PUBLISHED",
  PRODUCTION = "PRODUCTION",
  INSPECTION = "INSPECTION",
  PACKING = "PACKING",
  SHIPMENT = "SHIPMENT",
  REPAIR = "REPAIR",
  RECYCLE = "RECYCLE",
  OTHER = "OTHER",
}

@Entity("dpp_events")
@Index("idx_dpp_event_dpp", ["dppId"])
@Index("idx_dpp_event_type", ["type"])
@Index("idx_dpp_event_ts", ["timestamp"])
export class DppEvent {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "dpp_id" })
  dppId: string;

  @Column({
    type: "enum",
    enum: DppEventType,
  })
  type: DppEventType;

  @Column()
  actor: string;

  @Column({ nullable: true })
  location: string | null;

  @Column({ type: "timestamp with time zone" })
  timestamp: Date;

  @Column({ type: "jsonb", default: {} })
  data: Record<string, any>;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  // Relations
  @ManyToOne(() => Dpp, (dpp) => dpp.events, { onDelete: "CASCADE" })
  @JoinColumn({ name: "dpp_id" })
  dpp: Dpp;
}