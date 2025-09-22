import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
  JoinColumn,
} from "typeorm";
import { Tenant } from "./tenant.entity";
import { Batch } from "./batch.entity";

@Entity("vendors")
@Unique(["tenantId", "code"])
export class Vendor {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id" })
  tenantId: string;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 50 })
  code: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.vendors, { onDelete: "CASCADE" })
  @JoinColumn({ name: "tenant_id" })
  tenant: Tenant;

  @OneToMany(() => Batch, (batch) => batch.vendor)
  batches: Batch[];
}
