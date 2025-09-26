import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  JoinColumn,
} from "typeorm";
import { EventType } from "@qa-dashboard/shared";
import { Client } from "./client.entity";
import { Lot } from "./lot.entity";

@Entity("events")
export class Event {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "client_id" })
  clientId: string;

  @Column({ name: "lot_id", nullable: true })
  lotId?: string | null;

  @Column({
    type: "enum",
    enum: EventType,
  })
  type: EventType;

  @Column({ type: "jsonb", default: {} })
  payload: any;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @ManyToOne(() => Client, (client) => client.events, { onDelete: "CASCADE" })
  @JoinColumn({ name: "client_id" })
  client: Client;

  @ManyToOne(() => Lot, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "lot_id" })
  lot?: Lot | null;
}
