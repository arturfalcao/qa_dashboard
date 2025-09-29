import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  JoinColumn,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
} from "typeorm";
import { Tenant } from "./tenant.entity";
import { Lot } from "./lot.entity";

@Entity("clients")
export class Client {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id", type: "uuid" })
  tenantId: string;

  @ManyToOne(() => Tenant, (tenant) => tenant.clients, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @Column({ length: 255 })
  name: string;

  @Column({ name: "contact_email", nullable: true })
  contactEmail?: string;

  @Column({ name: "contact_phone", nullable: true })
  contactPhone?: string;

  @Column({ type: "text", nullable: true })
  address?: string;

  @Column({ nullable: true })
  country?: string;

  @Column({ type: "text", nullable: true })
  notes?: string;

  @Column({ name: "is_active", default: true })
  isActive: boolean;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @OneToMany(() => Lot, (lot) => lot.client)
  lots: Lot[];
}
