import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, OneToMany, CreateDateColumn, UpdateDateColumn, JoinColumn } from 'typeorm';
import { BatchStatus, ProcessStation } from '@qa-dashboard/shared';
import { Tenant } from './tenant.entity';
import { Vendor } from './vendor.entity';
import { Style } from './style.entity';
import { Garment } from './garment.entity';
import { Approval } from './approval.entity';

@Entity('batches')
export class Batch {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'tenant_id' })
  tenantId: string;

  @Column({ name: 'vendor_id' })
  vendorId: string;

  @Column({ name: 'style_id' })
  styleId: string;

  @Column({ name: 'po_number', length: 100 })
  poNumber: string;

  @Column({ type: 'int' })
  quantity: number;

  @Column({
    type: 'enum',
    enum: BatchStatus,
    default: BatchStatus.DRAFT,
  })
  status: BatchStatus;

  @Column({
    name: 'current_station',
    type: 'enum',
    enum: ProcessStation,
    default: ProcessStation.RECEIVING,
  })
  currentStation: ProcessStation;

  @Column({ name: 'estimated_completion_time', type: 'timestamptz', nullable: true })
  estimatedCompletionTime?: Date;

  @Column({
    type: 'enum',
    enum: ['low', 'normal', 'high', 'urgent'],
    default: 'normal',
  })
  priority: 'low' | 'normal' | 'high' | 'urgent';

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @ManyToOne(() => Tenant, tenant => tenant.batches, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'tenant_id' })
  tenant: Tenant;

  @ManyToOne(() => Vendor, vendor => vendor.batches, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'vendor_id' })
  vendor: Vendor;

  @ManyToOne(() => Style, style => style.batches, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'style_id' })
  style: Style;

  @OneToMany(() => Garment, garment => garment.batch)
  garments: Garment[];

  @OneToMany(() => Approval, approval => approval.batch)
  approvals: Approval[];
}