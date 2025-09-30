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
import { Tenant } from "./tenant.entity";
import { InspectionSession } from "./inspection-session.entity";
import { User } from "./user.entity";

@Entity("edge_devices")
export class EdgeDevice {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id", type: "uuid", nullable: true })
  tenantId?: string | null;

  @Column({ length: 255 })
  name: string;

  @Column({ name: "secret_key", length: 255, unique: true })
  secretKey: string;

  @Column({ name: "workbench_number", type: "int" })
  workbenchNumber: number;

  @Column({
    type: "enum",
    enum: ["active", "inactive", "maintenance"],
    default: "active",
  })
  status: "active" | "inactive" | "maintenance";

  @Column({ name: "last_seen_at", type: "timestamptz", nullable: true })
  lastSeenAt?: Date | null;

  @Column({ name: "assigned_operator_id", type: "uuid", nullable: true })
  assignedOperatorId?: string | null;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Tenant, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "tenant_id" })
  tenant?: Tenant | null;

  @ManyToOne(() => User, { nullable: true, onDelete: "SET NULL" })
  @JoinColumn({ name: "assigned_operator_id" })
  assignedOperator?: User | null;

  @OneToMany(() => InspectionSession, (session) => session.device)
  sessions: InspectionSession[];
}