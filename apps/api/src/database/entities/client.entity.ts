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

@Entity("clients")
export class Client {
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

  @OneToMany(() => User, (user) => user.client)
  users: User[];

  @OneToMany(() => Lot, (lot) => lot.client)
  lots: Lot[];

  @OneToMany(() => Report, (report) => report.client)
  reports: Report[];

  @OneToMany(() => Factory, (factory) => factory.client)
  factories: Factory[];

  @OneToMany(() => Event, (event) => event.client)
  events: Event[];
}
