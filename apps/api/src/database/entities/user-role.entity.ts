import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  JoinColumn,
  Unique,
} from "typeorm";
import { User } from "./user.entity";
import { Role } from "./role.entity";

@Entity("user_roles")
@Unique(["userId", "roleId"])
export class UserRole {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "user_id" })
  userId: string;

  @Column({ name: "role_id" })
  roleId: string;

  @Column({ name: "is_primary", default: false })
  isPrimary: boolean;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => User, (user) => user.userRoles, { onDelete: "CASCADE" })
  @JoinColumn({ name: "user_id" })
  user: User;

  @ManyToOne(() => Role, (role) => role.userRoles, { onDelete: "CASCADE" })
  @JoinColumn({ name: "role_id" })
  role: Role;
}
