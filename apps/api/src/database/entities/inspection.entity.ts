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
import { Lot } from "./lot.entity";
import { User } from "./user.entity";
import { Defect } from "./defect.entity";

@Entity("inspections")
export class Inspection {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ name: "inspector_id", nullable: true })
  inspectorId?: string | null;

  @Column({ name: "started_at", type: "timestamptz", nullable: true })
  startedAt?: Date | null;

  @Column({ name: "finished_at", type: "timestamptz", nullable: true })
  finishedAt?: Date | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Lot, (lot) => lot.inspections, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;

  @ManyToOne(() => User, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "inspector_id" })
  inspector?: User | null;

  @OneToMany(() => Defect, (defect) => defect.inspection)
  defects: Defect[];
}
