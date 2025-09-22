import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  JoinColumn,
} from "typeorm";
import { EventType } from "@qa-dashboard/shared";
import { Tenant } from "./tenant.entity";

@Entity("events")
export class Event {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({
    type: "enum",
    enum: EventType,
  })
  type: EventType;

  @Column({ type: "jsonb", default: {} })
  payload: any;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.events, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;
}
