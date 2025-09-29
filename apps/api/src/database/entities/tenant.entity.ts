import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  OneToMany,
  CreateDateColumn,
  UpdateDateColumn,
} from "typeorm";
import { User } from "./user.entity";
import { Lot } from "./lot.entity";
import { Report } from "./report.entity";
import { Event } from "./event.entity";
import { Factory } from "./factory.entity";
import { Client } from "./client.entity";

@Entity("tenants")
export class Tenant {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 120, unique: true })
  slug: string;

  @Column({ name: "logo_url", nullable: true })
  logoUrl?: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @OneToMany(() => User, (user) => user.tenant)
  users: User[];

  @OneToMany(() => Lot, (lot) => lot.tenant)
  lots: Lot[];

  @OneToMany(() => Report, (report) => report.tenant)
  reports: Report[];

  @OneToMany(() => Factory, (factory) => factory.tenant)
  factories: Factory[];

  @OneToMany(() => Event, (event) => event.tenant)
  events: Event[];

  @OneToMany(() => Client, (client) => client.tenant)
  clients: Client[];
}