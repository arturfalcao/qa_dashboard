import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Tenant } from '../database/entities/tenant.entity';
import { Batch } from '../database/entities/batch.entity';
import { Garment } from '../database/entities/garment.entity';
import { Inspection } from '../database/entities/inspection.entity';
import { InspectionService } from '../database/services/inspection.service';
import { BatchService } from '../database/services/batch.service';
import { EventService } from '../database/services/event.service';
import { StorageService } from '../storage/storage.service';
import { DefectType, BatchStatus, EventType } from '@qa-dashboard/shared';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class MockService {
  private isGenerating = false;
  private intervalId: NodeJS.Timeout | null = null;

  constructor(
    @InjectRepository(Tenant)
    private tenantRepository: Repository<Tenant>,
    @InjectRepository(Batch)
    private batchRepository: Repository<Batch>,
    @InjectRepository(Garment)
    private garmentRepository: Repository<Garment>,
    private inspectionService: InspectionService,
    private batchService: BatchService,
    private eventService: EventService,
    private storageService: StorageService,
  ) {}

  async startInspectionGenerator(): Promise<void> {
    if (this.isGenerating) {
      throw new Error('Mock generator is already running');
    }

    this.isGenerating = true;
    console.log('Starting mock inspection generator...');

    this.intervalId = setInterval(async () => {
      try {
        await this.generateRandomInspection();
      } catch (error) {
        console.error('Error generating inspection:', error);
      }
    }, 3000 + Math.random() * 2000); // 3-5 seconds

    return;
  }

  async stopInspectionGenerator(): Promise<void> {
    if (!this.isGenerating) {
      throw new Error('Mock generator is not running');
    }

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.isGenerating = false;
    console.log('Stopped mock inspection generator');
  }

  getGeneratorStatus(): { isRunning: boolean } {
    return { isRunning: this.isGenerating };
  }

  private async generateRandomInspection(): Promise<void> {
    // Get all active batches
    const activeBatches = await this.batchRepository.find({
      where: { status: BatchStatus.IN_PROGRESS },
      relations: ['garments'],
    });

    if (activeBatches.length === 0) {
      console.log('No active batches found for inspection generation');
      return;
    }

    // Pick a random batch
    const batch = activeBatches[Math.floor(Math.random() * activeBatches.length)];
    
    // Get uninspected garments from this batch
    const garments = await this.garmentRepository
      .createQueryBuilder('g')
      .leftJoin('g.inspections', 'i')
      .where('g.batchId = :batchId', { batchId: batch.id })
      .andWhere('i.id IS NULL')
      .getMany();

    if (garments.length === 0) {
      // If all garments are inspected, move batch to awaiting approval
      if (batch.status === BatchStatus.IN_PROGRESS) {
        await this.batchService.updateBatchStatus(batch.id, BatchStatus.AWAITING_APPROVAL);
        
        await this.eventService.createEvent(batch.tenantId, EventType.BATCH_AWAITING_APPROVAL, {
          batchId: batch.id,
          poNumber: batch.poNumber,
        });
        
        console.log(`Batch ${batch.poNumber} moved to awaiting approval`);
      }
      return;
    }

    // Pick a random garment
    const garment = garments[Math.floor(Math.random() * garments.length)];

    // Determine if this inspection has a defect (6-8% chance)
    const hasDefect = Math.random() < 0.07;
    let defectType: DefectType | undefined;
    
    if (hasDefect) {
      const defectTypes = Object.values(DefectType);
      // Weighted selection - stitching and measurement more common
      const weights = [0.15, 0.35, 0.15, 0.25, 0.10]; // stain, stitching, misprint, measurement, other
      const random = Math.random();
      let cumulative = 0;
      
      for (let i = 0; i < defectTypes.length; i++) {
        cumulative += weights[i];
        if (random <= cumulative) {
          defectType = defectTypes[i];
          break;
        }
      }
    }

    // Generate photos
    let photoKeyBefore: string | undefined;
    let photoKeyAfter: string | undefined;

    try {
      photoKeyBefore = await this.uploadSampleImage(batch.tenantId, hasDefect);
      if (hasDefect) {
        photoKeyAfter = await this.uploadSampleImage(batch.tenantId, false); // After photo without defect
      }
    } catch (error) {
      console.error('Error uploading sample images:', error);
    }

    // Create inspection
    const inspection = await this.inspectionService.createInspection({
      tenantId: batch.tenantId,
      garmentId: garment.id,
      hasDefect,
      defectType,
      notes: hasDefect ? `${defectType} detected during quality inspection` : undefined,
      photoKeyBefore,
      photoKeyAfter,
      inspectedAt: new Date(),
    });

    console.log(
      `Generated inspection for garment ${garment.serial} - ${
        hasDefect ? `DEFECT: ${defectType}` : 'PASS'
      }`
    );

    // Create event if defect detected
    if (hasDefect) {
      await this.eventService.createEvent(batch.tenantId, EventType.DEFECT_DETECTED, {
        inspectionId: inspection.id,
        garmentId: garment.id,
        batchId: batch.id,
        defectType,
        garmentSerial: garment.serial,
      });
    }
  }

  private async uploadSampleImage(tenantId: string, hasDefect: boolean): Promise<string> {
    // In a real implementation, you would have actual sample images
    // For now, we'll create a simple colored square
    const imageBuffer = this.generateSampleImageBuffer(hasDefect);
    const key = this.storageService.generateKey(tenantId);
    
    await this.storageService.uploadFileWithKey(key, imageBuffer);
    return key;
  }

  private generateSampleImageBuffer(hasDefect: boolean): Buffer {
    // Generate a simple 200x200 colored square as placeholder
    // In a real app, you'd use actual garment photos
    const width = 200;
    const height = 200;
    const channels = 3; // RGB
    const buffer = Buffer.alloc(width * height * channels);

    // Fill with base color (light gray)
    for (let i = 0; i < buffer.length; i += 3) {
      buffer[i] = 200;     // R
      buffer[i + 1] = 200; // G
      buffer[i + 2] = 200; // B
    }

    // Add a red dot if there's a defect
    if (hasDefect) {
      const centerX = Math.floor(width / 2);
      const centerY = Math.floor(height / 2);
      const radius = 15;

      for (let y = centerY - radius; y <= centerY + radius; y++) {
        for (let x = centerX - radius; x <= centerX + radius; x++) {
          const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
          if (distance <= radius && x >= 0 && x < width && y >= 0 && y < height) {
            const pixelIndex = (y * width + x) * 3;
            buffer[pixelIndex] = 255;     // R
            buffer[pixelIndex + 1] = 0;   // G
            buffer[pixelIndex + 2] = 0;   // B
          }
        }
      }
    }

    // Convert RGB to JPEG-like format (this is very simplified)
    // In a real implementation, you'd use a proper image library
    return buffer;
  }
}