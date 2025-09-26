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
import { LotFactory } from "./lot-factory.entity";
import { SupplyChainRole } from "./supply-chain-role.entity";
import { SupplyChainStageStatus } from "@qa-dashboard/shared";

@Entity("lot_factory_roles")
@Unique(["lotFactoryId", "roleId"])
export class LotFactoryRole {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_factory_id" })
  lotFactoryId: string;

  @Column({ name: "role_id" })
  roleId: string;

  @Column({ type: "int", default: 0 })
  sequence: number;

  @Column({ name: "co2_kg", type: "numeric", precision: 10, scale: 3, nullable: true })
  co2Kg?: number | null;

  @Column({ nullable: true })
  notes?: string | null;

  @Column({
    type: "text",
    default: SupplyChainStageStatus.NOT_STARTED,
  })
  status: SupplyChainStageStatus;

  @Column({ name: "started_at", type: "timestamptz", nullable: true })
  startedAt?: Date | null;

  @Column({ name: "completed_at", type: "timestamptz", nullable: true })
  completedAt?: Date | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => LotFactory, (lotFactory) => lotFactory.roles, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_factory_id" })
  lotFactory: LotFactory;

  @ManyToOne(() => SupplyChainRole, (role) => role.lotFactoryRoles, { eager: true, onDelete: "CASCADE" })
  @JoinColumn({ name: "role_id" })
  role: SupplyChainRole;
}
