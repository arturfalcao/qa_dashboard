import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
} from "typeorm";

@Entity("notifications")
export class Notification {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "client_id", nullable: true })
  clientId?: string | null;

  @Column({ name: "user_id", nullable: true })
  userId?: string | null;

  @Column({ type: "text" })
  channel: string;

  @Column({ type: "text" })
  template: string;

  @Column({ type: "jsonb", nullable: true })
  payload?: Record<string, unknown> | null;

  @Column({ type: "text", default: "pending" })
  status: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;
}
