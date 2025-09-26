import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
} from "typeorm";
import { Defect } from "./defect.entity";

@Entity("photos")
export class Photo {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "defect_id" })
  defectId: string;

  @Column({ type: "text" })
  url: string;

  @Column({ type: "jsonb", nullable: true })
  annotation?: Record<string, unknown> | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Defect, (defect) => defect.photos, { onDelete: "CASCADE" })
  @JoinColumn({ name: "defect_id" })
  defect: Defect;
}
