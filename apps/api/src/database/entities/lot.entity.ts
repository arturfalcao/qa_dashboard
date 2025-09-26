import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
} from "typeorm";
import { LotStatus } from "@qa-dashboard/shared";
import { Client } from "./client.entity";
import { Factory } from "./factory.entity";
import { Inspection } from "./inspection.entity";
import { Approval } from "./approval.entity";
import { Activity } from "./activity.entity";
import { Report } from "./report.entity";
import { LotFactory } from "./lot-factory.entity";

const numericTransformer = {
  to: (value?: number | null) => value ?? 0,
  from: (value?: string | null) => (value == null ? 0 : parseFloat(value)),
};

@Entity("lots")
export class Lot {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "client_id" })
  clientId: string;

  @Column({ name: "factory_id" })
  factoryId: string;

  @Column({ name: "style_ref", length: 120 })
  styleRef: string;

  @Column({ name: "quantity_total", type: "int" })
  quantityTotal: number;

  @Column({
    type: "enum",
    enum: LotStatus,
    default: LotStatus.PLANNED,
  })
  status: LotStatus;

  @Column({
    name: "defect_rate",
    type: "numeric",
    precision: 5,
    scale: 2,
    default: 0,
    transformer: numericTransformer,
  })
  defectRate: number;

  @Column({
    name: "inspected_progress",
    type: "numeric",
    precision: 5,
    scale: 2,
    default: 0,
    transformer: numericTransformer,
  })
  inspectedProgress: number;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Client, (client) => client.lots, { onDelete: "CASCADE" })
  @JoinColumn({ name: "client_id" })
  client: Client;

  @ManyToOne(() => Factory, (factory) => factory.lots, { onDelete: "CASCADE" })
  @JoinColumn({ name: "factory_id" })
  factory: Factory;

  @OneToMany(() => Inspection, (inspection) => inspection.lot)
  inspections: Inspection[];

  @OneToMany(() => LotFactory, (lotFactory) => lotFactory.lot, {
    cascade: true,
  })
  suppliers: LotFactory[];

  @OneToMany(() => Approval, (approval) => approval.lot)
  approvals: Approval[];

  @OneToMany(() => Activity, (activity) => activity.lot)
  activities: Activity[];

  @OneToMany(() => Report, (report) => report.lot)
  reports: Report[];
}
