import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  HttpCode,
  HttpStatus,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiTags, ApiOperation, ApiResponse, ApiConsumes } from '@nestjs/swagger';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantGuard } from '../../auth/tenant.guard';
import { CurrentTenant } from '../../common/decorators';
import { ZodValidationPipe } from '../../common/zod-validation.pipe';
import { InspectionPhotoService, CreateInspectionPhotoDto } from '../services/inspection-photo.service';
import { StorageService } from '../../storage/storage.service';
import { z } from 'zod';
import { PhotoAngle } from '@qa-dashboard/shared';

const CreatePhotoSchema = z.object({
  inspectionId: z.string().uuid(),
  angle: z.nativeEnum(PhotoAngle),
  capturedAt: z.string().datetime().optional(),
});

const GetPhotosByAngleSchema = z.object({
  angle: z.nativeEnum(PhotoAngle),
});

@ApiTags('Inspection Photos')
@Controller('inspection-photos')
@UseGuards(JwtAuthGuard, TenantGuard)
export class InspectionPhotoController {
  constructor(
    private inspectionPhotoService: InspectionPhotoService,
    private storageService: StorageService,
  ) {}

  @Post('upload')
  @ApiOperation({ summary: 'Upload a new inspection photo' })
  @ApiConsumes('multipart/form-data')
  @ApiResponse({ status: 201, description: 'Photo uploaded successfully' })
  @UseInterceptors(FileInterceptor('photo'))
  async uploadPhoto(
    @CurrentTenant() tenantId: string,
    @UploadedFile() file: any,
    @Body(new ZodValidationPipe(CreatePhotoSchema)) createDto: z.infer<typeof CreatePhotoSchema>,
  ) {
    if (!file) {
      throw new Error('No file uploaded');
    }

    // Upload file to storage
    const photoKey = await this.storageService.uploadFile(
      file.buffer,
      file.originalname,
      file.mimetype,
      tenantId,
    );

    const photoDto: CreateInspectionPhotoDto = {
      inspectionId: createDto.inspectionId,
      angle: createDto.angle,
      photoKey,
      capturedAt: createDto.capturedAt ? new Date(createDto.capturedAt) : undefined,
    };

    return await this.inspectionPhotoService.createPhoto(tenantId, photoDto);
  }

  @Get('inspection/:inspectionId')
  @ApiOperation({ summary: 'Get all photos for an inspection' })
  @ApiResponse({ status: 200, description: 'Photos retrieved successfully' })
  async getPhotosForInspection(
    @CurrentTenant() tenantId: string,
    @Param('inspectionId') inspectionId: string,
  ) {
    return await this.inspectionPhotoService.getPhotosForInspection(tenantId, inspectionId);
  }

  @Get('inspection/:inspectionId/angle')
  @ApiOperation({ summary: 'Get photos for an inspection by angle' })
  @ApiResponse({ status: 200, description: 'Photos retrieved successfully' })
  async getPhotosByAngle(
    @CurrentTenant() tenantId: string,
    @Param('inspectionId') inspectionId: string,
    @Query(new ZodValidationPipe(GetPhotosByAngleSchema)) query: z.infer<typeof GetPhotosByAngleSchema>,
  ) {
    return await this.inspectionPhotoService.getPhotosByAngle(
      tenantId,
      inspectionId,
      query.angle,
    );
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get photo by ID' })
  @ApiResponse({ status: 200, description: 'Photo retrieved successfully' })
  async getPhotoById(
    @CurrentTenant() tenantId: string,
    @Param('id') photoId: string,
  ) {
    const photo = await this.inspectionPhotoService.getPhotoById(tenantId, photoId);
    if (!photo) {
      throw new Error('Photo not found');
    }
    return photo;
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete a photo' })
  @ApiResponse({ status: 204, description: 'Photo deleted successfully' })
  async deletePhoto(
    @CurrentTenant() tenantId: string,
    @Param('id') photoId: string,
  ) {
    await this.inspectionPhotoService.deletePhoto(tenantId, photoId);
  }

  @Get('inspection/:inspectionId/download-url')
  @ApiOperation({ summary: 'Get presigned URL for photo download' })
  @ApiResponse({ status: 200, description: 'Download URL generated successfully' })
  async getPhotoDownloadUrl(
    @CurrentTenant() tenantId: string,
    @Param('photoId') photoId: string,
  ) {
    const photo = await this.inspectionPhotoService.getPhotoById(tenantId, photoId);
    if (!photo) {
      throw new Error('Photo not found');
    }

    const downloadUrl = await this.storageService.getPresignedUrl(photo.photoKey, 3600); // 1 hour expiry
    return { downloadUrl };
  }
}