import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  JoinColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
  OneToMany,
} from "typeorm";
import { Lot } from "./lot.entity";
import { Factory } from "./factory.entity";
import { LotFactoryRole } from "./lot-factory-role.entity";

@Entity("lot_factories")
@Unique(["lotId", "factoryId"])
export class LotFactory {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ name: "factory_id" })
  factoryId: string;

  @Column({ type: "int", default: 0 })
  sequence: number;

  @Column({ name: "stage", type: "text", nullable: true })
  stage?: string | null;

  @Column({ name: "is_primary", type: "boolean", default: false })
  isPrimary: boolean;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Lot, (lot) => lot.suppliers, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;

  @ManyToOne(() => Factory, (factory) => factory.lotSuppliers, { onDelete: "CASCADE" })
  @JoinColumn({ name: "factory_id" })
  factory: Factory;

  @OneToMany(() => LotFactoryRole, (role) => role.lotFactory, { cascade: true })
  roles: LotFactoryRole[];
}
