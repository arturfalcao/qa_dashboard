import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, OneToMany, CreateDateColumn, UpdateDateColumn, Unique, JoinColumn } from 'typeorm';
import { Tenant } from './tenant.entity';
import { Batch } from './batch.entity';
import { Inspection } from './inspection.entity';

@Entity('garments')
@Unique(['batchId', 'serial'])
export class Garment {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'tenant_id' })
  tenantId: string;

  @Column({ name: 'batch_id' })
  batchId: string;

  @Column({ length: 100 })
  serial: string;

  @Column({ length: 20 })
  size: string;

  @Column({ length: 50 })
  color: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @ManyToOne(() => Tenant, tenant => tenant.garments, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'tenant_id' })
  tenant: Tenant;

  @ManyToOne(() => Batch, batch => batch.garments, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'batch_id' })
  batch: Batch;

  @OneToMany(() => Inspection, inspection => inspection.garment)
  inspections: Inspection[];
}