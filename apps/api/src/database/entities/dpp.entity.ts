import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
  OneToMany,
  ManyToOne,
  JoinColumn,
} from "typeorm";
import { User } from "./user.entity";
import { Client } from "./client.entity";
import { DppEvent } from "./dpp-event.entity";
import { DppAccessLog } from "./dpp-access-log.entity";

export enum DppStatus {
  DRAFT = "DRAFT",
  PUBLISHED = "PUBLISHED",
  ARCHIVED = "ARCHIVED",
}

@Entity("dpps")
@Index("idx_dpp_sku", ["productSku"])
@Index("idx_dpp_gtin", ["gtin"])
@Index("idx_dpp_status", ["status"])
@Index("idx_dpp_client", ["clientId"])
export class Dpp {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "client_id" })
  clientId: string;

  @Column({ name: "schema_version", default: "textile.v0.1" })
  schemaVersion: string;

  @Column({ name: "product_sku" })
  productSku: string;

  @Column({ name: "gtin", nullable: true })
  gtin: string | null;

  @Column()
  brand: string;

  @Column({ name: "style_ref" })
  styleRef: string;

  @Column({ type: "jsonb", name: "public_payload" })
  publicPayload: Record<string, any>;

  @Column({ type: "jsonb", name: "restricted_payload", default: {} })
  restrictedPayload: Record<string, any>;

  @Column({
    type: "enum",
    enum: DppStatus,
    default: DppStatus.DRAFT,
  })
  status: DppStatus;

  @Column({ name: "created_by" })
  createdBy: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  // Relations
  @ManyToOne(() => Client)
  @JoinColumn({ name: "client_id" })
  client: Client;

  @ManyToOne(() => User)
  @JoinColumn({ name: "created_by" })
  creator: User;

  @OneToMany(() => DppEvent, (event) => event.dpp)
  events: DppEvent[];

  @OneToMany(() => DppAccessLog, (log) => log.dpp)
  accessLogs: DppAccessLog[];
}