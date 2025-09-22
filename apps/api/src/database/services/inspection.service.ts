import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Inspection } from '../entities/inspection.entity';
import { StorageService } from '../../storage/storage.service';

type InspectionWithPhotoUrls = Inspection & {
  photoUrlBefore?: string;
  photoUrlAfter?: string;
};

@Injectable()
export class InspectionService {
  private readonly logger = new Logger(InspectionService.name);

  constructor(
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    private storageService: StorageService,
  ) {}

  async getInspections(
    tenantId: string,
    since?: string,
    limit = 50,
  ): Promise<InspectionWithPhotoUrls[]> {
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

    return Promise.all(
      inspections.map(async inspection => {
        const inspectionWithUrls = inspection as InspectionWithPhotoUrls;
        const [photoUrlBefore, photoUrlAfter] = await Promise.all([
          this.resolvePhotoUrl(inspection.photoKeyBefore),
          this.resolvePhotoUrl(inspection.photoKeyAfter),
        ]);

        inspectionWithUrls.photoUrlBefore = photoUrlBefore;
        inspectionWithUrls.photoUrlAfter = photoUrlAfter;

        return inspectionWithUrls;
      }),
    );
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

  private async resolvePhotoUrl(photoKey?: string): Promise<string | undefined> {
    if (!photoKey) {
      return undefined;
    }

    try {
      return await this.storageService.getPresignedDownloadUrl(photoKey);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logger.warn(`Failed to generate presigned URL for photo key "${photoKey}": ${message}`);
      return undefined;
    }
  }
}
