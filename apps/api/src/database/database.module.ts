import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';

import { Tenant } from './entities/tenant.entity';
import { User } from './entities/user.entity';
import { Vendor } from './entities/vendor.entity';
import { Style } from './entities/style.entity';
import { Batch } from './entities/batch.entity';
import { Garment } from './entities/garment.entity';
import { Inspection } from './entities/inspection.entity';
import { Approval } from './entities/approval.entity';
import { Event } from './entities/event.entity';
import { InspectionPhoto } from './entities/inspection-photo.entity';
import { PhotoAnnotation } from './entities/photo-annotation.entity';
import { BatchProcessProgress } from './entities/batch-process-progress.entity';

import { InspectionService } from './services/inspection.service';
import { BatchService } from './services/batch.service';
import { AnalyticsService } from './services/analytics.service';
import { EventService } from './services/event.service';
import { SeedService } from './services/seed.service';
import { InspectionPhotoService } from './services/inspection-photo.service';
import { PhotoAnnotationService } from './services/photo-annotation.service';

import { InspectionController } from './controllers/inspection.controller';
import { BatchController } from './controllers/batch.controller';
import { AnalyticsController } from './controllers/analytics.controller';
import { EventController } from './controllers/event.controller';
import { AdminController } from './controllers/admin.controller';
import { InspectionPhotoController } from './controllers/inspection-photo.controller';
import { PhotoAnnotationController } from './controllers/photo-annotation.controller';
import { StorageModule } from '../storage/storage.module';

@Module({
  imports: [
    TypeOrmModule.forFeature([
      Tenant,
      User,
      Vendor,
      Style,
      Batch,
      Garment,
      Inspection,
      Approval,
      Event,
      InspectionPhoto,
      PhotoAnnotation,
      BatchProcessProgress,
    ]),
    StorageModule,
  ],
  providers: [
    InspectionService,
    BatchService,
    AnalyticsService,
    EventService,
    SeedService,
    InspectionPhotoService,
    PhotoAnnotationService,
  ],
  controllers: [
    InspectionController,
    BatchController,
    AnalyticsController,
    EventController,
    AdminController,
    InspectionPhotoController,
    PhotoAnnotationController,
  ],
  exports: [
    InspectionService,
    BatchService,
    AnalyticsService,
    EventService,
    SeedService,
    InspectionPhotoService,
    PhotoAnnotationService,
    TypeOrmModule,
  ],
})
export class DatabaseModule {}