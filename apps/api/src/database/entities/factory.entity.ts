import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from "typeorm";
import { Lot } from "./lot.entity";
import { Tenant } from "./tenant.entity";
import { FactoryRole } from "./factory-role.entity";
import { LotFactory } from "./lot-factory.entity";
import { FactoryCertification } from "./factory-certification.entity";

@Entity("factories")
export class Factory {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id", type: "uuid", nullable: true })
  tenantId?: string | null;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 120, nullable: true })
  city?: string;

  @Column({ length: 2, default: "PT" })
  country: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, (tenant) => tenant.factories, {
    nullable: true,
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "tenant_id" })
  tenant?: Tenant | null;

  @OneToMany(() => Lot, (lot) => lot.factory)
  lots: Lot[];

  @OneToMany(() => LotFactory, (lotFactory) => lotFactory.factory)
  lotSuppliers: LotFactory[];

  @OneToMany(() => FactoryRole, (factoryRole) => factoryRole.factory, { cascade: true })
  capabilities: FactoryRole[];

  @OneToMany(() => FactoryCertification, (certification) => certification.factory, {
    cascade: true,
  })
  certifications: FactoryCertification[];
}
