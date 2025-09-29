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
import { EdgeDevice } from "./edge-device.entity";
import { User } from "./user.entity";
import { ApparelPiece } from "./apparel-piece.entity";

@Entity("inspection_sessions")
export class InspectionSession {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ name: "device_id" })
  deviceId: string;

  @Column({ name: "operator_id" })
  operatorId: string;

  @Column({ name: "started_at", type: "timestamptz" })
  startedAt: Date;

  @Column({ name: "ended_at", type: "timestamptz", nullable: true })
  endedAt?: Date | null;

  @Column({ name: "paused_at", type: "timestamptz", nullable: true })
  pausedAt?: Date | null;

  @Column({ name: "pieces_inspected", type: "int", default: 0 })
  piecesInspected: number;

  @Column({ name: "pieces_ok", type: "int", default: 0 })
  piecesOk: number;

  @Column({ name: "pieces_defect", type: "int", default: 0 })
  piecesDefect: number;

  @Column({ name: "pieces_potential_defect", type: "int", default: 0 })
  piecesPotentialDefect: number;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Lot, { onDelete: "CASCADE" })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;

  @ManyToOne(() => EdgeDevice, (device) => device.sessions, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "device_id" })
  device: EdgeDevice;

  @ManyToOne(() => User, { onDelete: "CASCADE" })
  @JoinColumn({ name: "operator_id" })
  operator: User;

  @OneToMany(() => ApparelPiece, (piece) => piece.session)
  pieces: ApparelPiece[];
}