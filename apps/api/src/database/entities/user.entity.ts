import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
  JoinColumn,
} from "typeorm";
import { Client } from "./client.entity";
import { Approval } from "./approval.entity";
import { UserRole as UserRoleEntity } from "./user-role.entity";

@Entity("users")
@Unique(["clientId", "email"])
export class User {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "client_id", nullable: true })
  clientId?: string | null;

  @Column({ length: 255 })
  email: string;

  @Column({ name: "password_hash", length: 255 })
  passwordHash: string;

  @Column({ name: "is_active", default: true })
  isActive: boolean;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Client, (client) => client.users, {
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "client_id" })
  client?: Client | null;

  @OneToMany(() => Approval, (approval) => approval.user)
  approvals: Approval[];

  @OneToMany(() => UserRoleEntity, (userRole) => userRole.user)
  userRoles: UserRoleEntity[];
}
