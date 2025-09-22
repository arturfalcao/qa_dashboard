import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, CreateDateColumn, JoinColumn } from 'typeorm';
import { DefectType, DefectSeverity } from '@qa-dashboard/shared';
import { Tenant } from './tenant.entity';
import { InspectionPhoto } from './inspection-photo.entity';
import { User } from './user.entity';

@Entity('photo_annotations')
export class PhotoAnnotation {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ name: 'tenant_id' })
  tenantId: string;

  @Column({ name: 'photo_id' })
  photoId: string;

  @Column({ name: 'created_by' })
  createdBy: string;

  @Column({ type: 'decimal', precision: 5, scale: 2 })
  x: number; // X coordinate as percentage

  @Column({ type: 'decimal', precision: 5, scale: 2 })
  y: number; // Y coordinate as percentage

  @Column({ type: 'text' })
  comment: string;

  @Column({
    name: 'defect_type',
    type: 'enum',
    enum: DefectType,
    nullable: true,
  })
  defectType?: DefectType;

  @Column({
    name: 'defect_severity',
    type: 'enum',
    enum: DefectSeverity,
    nullable: true,
  })
  defectSeverity?: DefectSeverity;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @ManyToOne(() => Tenant, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'tenant_id' })
  tenant: Tenant;

  @ManyToOne(() => InspectionPhoto, photo => photo.annotations, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'photo_id' })
  photo: InspectionPhoto;

  @ManyToOne(() => User, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'created_by' })
  user: User;
}