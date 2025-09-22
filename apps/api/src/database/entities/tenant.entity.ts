import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
} from "typeorm";
import { User } from "./user.entity";
import { Vendor } from "./vendor.entity";
import { Style } from "./style.entity";
import { Batch } from "./batch.entity";
import { Garment } from "./garment.entity";
import { Inspection } from "./inspection.entity";
import { Approval } from "./approval.entity";
import { Event } from "./event.entity";

@Entity("tenants")
export class Tenant {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 100, unique: true })
  slug: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @OneToMany(() => User, (user) => user.tenant)
  users: User[];

  @OneToMany(() => Vendor, (vendor) => vendor.tenant)
  vendors: Vendor[];

  @OneToMany(() => Style, (style) => style.tenant)
  styles: Style[];

  @OneToMany(() => Batch, (batch) => batch.tenant)
  batches: Batch[];

  @OneToMany(() => Garment, (garment) => garment.tenant)
  garments: Garment[];

  @OneToMany(() => Inspection, (inspection) => inspection.tenant)
  inspections: Inspection[];

  @OneToMany(() => Approval, (approval) => approval.tenant)
  approvals: Approval[];

  @OneToMany(() => Event, (event) => event.tenant)
  events: Event[];
}
