import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  JoinColumn,
} from "typeorm";
import { Lot } from "./lot.entity";

@Entity("activities")
export class Activity {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ type: "text" })
  kind: string;

  @Column({ type: "jsonb", nullable: true })
  payload?: Record<string, unknown> | null;

  @CreateDateColumn({ name: "ts" })
  timestamp: Date;

  @ManyToOne(() => Lot, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;
}
