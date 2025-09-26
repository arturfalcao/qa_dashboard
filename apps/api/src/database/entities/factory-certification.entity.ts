import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  JoinColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
} from "typeorm";
import { Factory } from "./factory.entity";

@Entity("factory_certifications")
@Unique(["factoryId", "certification"])
export class FactoryCertification {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "factory_id" })
  factoryId: string;

  @Column()
  certification: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Factory, (factory) => factory.certifications, { onDelete: "CASCADE" })
  @JoinColumn({ name: "factory_id" })
  factory: Factory;
}
