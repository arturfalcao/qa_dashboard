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
import { Tenant } from "./tenant.entity";
import { Approval } from "./approval.entity";
import { UserRole as UserRoleEntity } from "./user-role.entity";
import { LotUserAssignment } from "./lot-user-assignment.entity";

@Entity("users")
@Unique(["tenantId", "email"])
export class User {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "tenant_id", nullable: true })
  tenantId?: string | null;

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

  @ManyToOne(() => Tenant, (tenant) => tenant.users, {
    onDelete: "SET NULL",
  })
  @JoinColumn({ name: "tenant_id" })
  tenant?: Tenant | null;

  @OneToMany(() => Approval, (approval) => approval.user)
  approvals: Approval[];

  @OneToMany(() => UserRoleEntity, (userRole) => userRole.user)
  userRoles: UserRoleEntity[];

  @OneToMany(() => LotUserAssignment, (assignment) => assignment.user)
  assignments: LotUserAssignment[];
}
