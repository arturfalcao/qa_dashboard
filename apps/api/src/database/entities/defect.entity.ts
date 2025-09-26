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
import { Inspection } from "./inspection.entity";
import { DefectType } from "./defect-type.entity";
import { Photo } from "./photo.entity";

@Entity("defects")
export class Defect {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "inspection_id" })
  inspectionId: string;

  @Column({ name: "piece_code", length: 120, nullable: true })
  pieceCode?: string | null;

  @Column({ name: "defect_type_id", type: "uuid", nullable: true })
  defectTypeId?: string | null;

  @Column({ type: "text", nullable: true })
  note?: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Inspection, (inspection) => inspection.defects, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "inspection_id" })
  inspection: Inspection;

  @ManyToOne(() => DefectType, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "defect_type_id" })
  defectType?: DefectType | null;

  @OneToMany(() => Photo, (photo) => photo.defect)
  photos: Photo[];
}
