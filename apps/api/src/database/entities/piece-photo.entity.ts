import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  JoinColumn,
} from "typeorm";
import { ApparelPiece } from "./apparel-piece.entity";

@Entity("piece_photos")
export class PiecePhoto {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "piece_id" })
  pieceId: string;

  @Column({ name: "file_path", type: "text" })
  filePath: string;

  @Column({ name: "s3_url", type: "text", nullable: true })
  s3Url?: string | null;

  @Column({ name: "captured_at", type: "timestamptz" })
  capturedAt: Date;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @ManyToOne(() => ApparelPiece, (piece) => piece.photos, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "piece_id" })
  piece: ApparelPiece;
}