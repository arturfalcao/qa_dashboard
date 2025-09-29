import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
} from "typeorm";
import { ApparelPiece } from "./apparel-piece.entity";
import { User } from "./user.entity";

@Entity("piece_defects")
export class PieceDefect {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "piece_id" })
  pieceId: string;

  @Column({
    type: "enum",
    enum: ["pending_review", "confirmed", "rejected"],
    default: "pending_review",
  })
  status: "pending_review" | "confirmed" | "rejected";

  @Column({ name: "audio_transcript", type: "text", nullable: true })
  audioTranscript?: string | null;

  @Column({ name: "flagged_at", type: "timestamptz" })
  flaggedAt: Date;

  @Column({ name: "reviewed_by", type: "uuid", nullable: true })
  reviewedBy?: string | null;

  @Column({ name: "reviewed_at", type: "timestamptz", nullable: true })
  reviewedAt?: Date | null;

  @Column({ type: "text", nullable: true })
  notes?: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => ApparelPiece, (piece) => piece.defects, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "piece_id" })
  piece: ApparelPiece;

  @ManyToOne(() => User, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "reviewed_by" })
  reviewer?: User | null;
}