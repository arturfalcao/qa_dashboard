import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, MoreThan } from 'typeorm';
import { Inspection } from '../entities/inspection.entity';
import { StorageService } from '../../storage/storage.service';

@Injectable()
export class InspectionService {
  constructor(
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    private storageService: StorageService,
  ) {}

  async getInspections(
    tenantId: string,
    since?: string,
    limit = 50,
  ): Promise<Inspection[]> {
    const query = this.inspectionRepository
      .createQueryBuilder('inspection')
      .leftJoinAndSelect('inspection.garment', 'garment')
      .leftJoinAndSelect('garment.batch', 'batch')
      .leftJoinAndSelect('batch.vendor', 'vendor')
      .leftJoinAndSelect('batch.style', 'style')
      .where('inspection.tenantId = :tenantId', { tenantId })
      .orderBy('inspection.inspectedAt', 'DESC')
      .limit(limit);

    if (since) {
      query.andWhere('inspection.inspectedAt > :since', { since: new Date(since) });
    }

    const inspections = await query.getMany();

    // Add presigned URLs for photos
    for (const inspection of inspections) {
      if (inspection.photoKeyBefore) {
        try {
          inspection['photoUrlBefore'] = await this.storageService.getPresignedDownloadUrl(
            inspection.photoKeyBefore,
          );
        } catch (error) {
          console.error('Error getting presigned URL for before photo:', error);
        }
      }
      
      if (inspection.photoKeyAfter) {
        try {
          inspection['photoUrlAfter'] = await this.storageService.getPresignedDownloadUrl(
            inspection.photoKeyAfter,
          );
        } catch (error) {
          console.error('Error getting presigned URL for after photo:', error);
        }
      }
    }

    return inspections;
  }

  async createInspection(inspection: Partial<Inspection>): Promise<Inspection> {
    const newInspection = this.inspectionRepository.create(inspection);
    return await this.inspectionRepository.save(newInspection);
  }

  async getInspectionsByGarmentIds(garmentIds: string[]): Promise<Inspection[]> {
    if (garmentIds.length === 0) return [];
    
    return await this.inspectionRepository
      .createQueryBuilder('inspection')
      .leftJoinAndSelect('inspection.garment', 'garment')
      .leftJoinAndSelect('garment.batch', 'batch')
      .leftJoinAndSelect('batch.vendor', 'vendor')
      .leftJoinAndSelect('batch.style', 'style')
      .where('inspection.garmentId IN (:...garmentIds)', { garmentIds })
      .orderBy('inspection.inspectedAt', 'DESC')
      .getMany();
  }
}