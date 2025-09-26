import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  JoinColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
} from "typeorm";
import { Factory } from "./factory.entity";
import { SupplyChainRole } from "./supply-chain-role.entity";

@Entity("factory_roles")
@Unique(["factoryId", "roleId"])
export class FactoryRole {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "factory_id" })
  factoryId: string;

  @Column({ name: "role_id" })
  roleId: string;

  @Column({ name: "co2_override_kg", type: "numeric", precision: 10, scale: 3, nullable: true })
  co2OverrideKg?: number | null;

  @Column({ nullable: true })
  notes?: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Factory, (factory) => factory.capabilities, { onDelete: "CASCADE" })
  @JoinColumn({ name: "factory_id" })
  factory: Factory;

  @ManyToOne(() => SupplyChainRole, (role) => role.factoryRoles, { eager: true, onDelete: "CASCADE" })
  @JoinColumn({ name: "role_id" })
  role: SupplyChainRole;
}
