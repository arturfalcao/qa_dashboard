import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn } from "typeorm";

@Entity("audit_log")
export class AuditLog {
  @PrimaryGeneratedColumn("increment", { type: "bigint" })
  id: string;

  @Column({ name: "user_id", type: "uuid", nullable: true })
  userId?: string | null;

  @Column()
  entity: string;

  @Column({ name: "entity_id" })
  entityId: string;

  @Column()
  action: string;

  @Column({ type: "jsonb", nullable: true })
  before?: Record<string, unknown> | null;

  @Column({ type: "jsonb", nullable: true })
  after?: Record<string, unknown> | null;

  @CreateDateColumn({ name: "ts" })
  timestamp: Date;
}
