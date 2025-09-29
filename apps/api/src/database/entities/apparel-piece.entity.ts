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
import { InspectionSession } from "./inspection-session.entity";
import { PiecePhoto } from "./piece-photo.entity";
import { PieceDefect } from "./piece-defect.entity";

@Entity("apparel_pieces")
export class ApparelPiece {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "inspection_session_id" })
  inspectionSessionId: string;

  @Column({ name: "piece_number", type: "int" })
  pieceNumber: number;

  @Column({
    type: "enum",
    enum: ["ok", "defect", "potential_defect", "pending_review"],
    default: "pending_review",
  })
  status: "ok" | "defect" | "potential_defect" | "pending_review";

  @Column({ name: "inspection_started_at", type: "timestamptz" })
  inspectionStartedAt: Date;

  @Column({ name: "inspection_completed_at", type: "timestamptz", nullable: true })
  inspectionCompletedAt?: Date | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => InspectionSession, (session) => session.pieces, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "inspection_session_id" })
  session: InspectionSession;

  @OneToMany(() => PiecePhoto, (photo) => photo.piece)
  photos: PiecePhoto[];

  @OneToMany(() => PieceDefect, (defect) => defect.piece)
  defects: PieceDefect[];
}