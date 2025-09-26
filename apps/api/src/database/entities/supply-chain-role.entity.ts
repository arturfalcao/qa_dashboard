import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  OneToMany,
} from "typeorm";
import { FactoryRole } from "./factory-role.entity";
import { LotFactoryRole } from "./lot-factory-role.entity";

@Entity("supply_chain_roles")
export class SupplyChainRole {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ unique: true })
  key: string;

  @Column()
  name: string;

  @Column({ nullable: true })
  description?: string | null;

  @Column({ name: "default_sequence", type: "int", default: 0 })
  defaultSequence: number;

  @Column({ name: "default_co2_kg", type: "numeric", precision: 10, scale: 3, default: 0 })
  defaultCo2Kg: number;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @OneToMany(() => FactoryRole, (factoryRole) => factoryRole.role)
  factoryRoles: FactoryRole[];

  @OneToMany(() => LotFactoryRole, (lotFactoryRole) => lotFactoryRole.role)
  lotFactoryRoles: LotFactoryRole[];
}
