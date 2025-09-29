import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  ManyToOne,
  CreateDateColumn,
  UpdateDateColumn,
  Unique,
  JoinColumn,
} from "typeorm";
import { Lot } from "./lot.entity";
import { User } from "./user.entity";

@Entity("lot_user_assignments")
@Unique(["lotId", "userId"])
export class LotUserAssignment {
  @PrimaryGeneratedColumn("uuid")
  id: string;

  @Column({ name: "lot_id" })
  lotId: string;

  @Column({ name: "user_id" })
  userId: string;

  @CreateDateColumn({ name: "created_at" })
  createdAt: Date;

  @UpdateDateColumn({ name: "updated_at" })
  updatedAt: Date;

  @ManyToOne(() => Lot, (lot) => lot.assignments, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "lot_id" })
  lot: Lot;

  @ManyToOne(() => User, (user) => user.assignments, {
    onDelete: "CASCADE",
  })
  @JoinColumn({ name: "user_id" })
  user: User;
}
