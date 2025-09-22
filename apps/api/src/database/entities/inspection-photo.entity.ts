import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, OneToMany, CreateDateColumn, JoinColumn } from 'typeorm';
import { PhotoAngle } from '@qa-dashboard/shared';
import { Tenant } from './tenant.entity';
import { Inspection } from './inspection.entity';
import { PhotoAnnotation } from './photo-annotation.entity';

@Entity('inspection_photos')
export class InspectionPhoto {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'tenant_id' })
  tenantId: string;

  @Column({ name: 'inspection_id' })
  inspectionId: string;

  @Column({
    type: 'enum',
    enum: PhotoAngle,
  })
  angle: PhotoAngle;

  @Column({ name: 'photo_key', length: 255 })
  photoKey: string;

  @Column({ name: 'captured_at', type: 'timestamptz', default: () => 'CURRENT_TIMESTAMP' })
  capturedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @ManyToOne(() => Tenant, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'tenant_id' })
  tenant: Tenant;

  @ManyToOne(() => Inspection, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'inspection_id' })
  inspection: Inspection;

  @OneToMany(() => PhotoAnnotation, annotation => annotation.photo)
  annotations: PhotoAnnotation[];

  // Virtual property for presigned URL (not stored in database)
  photoUrl?: string;
}