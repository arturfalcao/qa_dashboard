import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  UseGuards,
  Request,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantGuard } from '../../auth/tenant.guard';
import { CurrentTenant } from '../../common/decorators';
import { ZodValidationPipe } from '../../common/zod-validation.pipe';
import { PhotoAnnotationService, CreatePhotoAnnotationDto, UpdatePhotoAnnotationDto } from '../services/photo-annotation.service';
import { z } from 'zod';
import { DefectType, DefectSeverity } from '@qa-dashboard/shared';

const CreateAnnotationSchema = z.object({
  photoId: z.string().uuid(),
  x: z.number().min(0).max(100),
  y: z.number().min(0).max(100),
  comment: z.string().min(1),
  defectType: z.nativeEnum(DefectType).optional(),
  defectSeverity: z.nativeEnum(DefectSeverity).optional(),
});

const UpdateAnnotationSchema = z.object({
  x: z.number().min(0).max(100).optional(),
  y: z.number().min(0).max(100).optional(),
  comment: z.string().min(1).optional(),
  defectType: z.nativeEnum(DefectType).optional(),
  defectSeverity: z.nativeEnum(DefectSeverity).optional(),
});

@ApiTags('Photo Annotations')
@Controller('photo-annotations')
@UseGuards(JwtAuthGuard, TenantGuard)
export class PhotoAnnotationController {
  constructor(private photoAnnotationService: PhotoAnnotationService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new photo annotation' })
  @ApiResponse({ status: 201, description: 'Annotation created successfully' })
  async createAnnotation(
    @CurrentTenant() tenantId: string,
    @Body(new ZodValidationPipe(CreateAnnotationSchema)) createDto: z.infer<typeof CreateAnnotationSchema>,
    @Request() req: any,
  ) {
    const annotationDto: CreatePhotoAnnotationDto = {
      photoId: createDto.photoId,
      x: createDto.x,
      y: createDto.y,
      comment: createDto.comment,
      defectType: createDto.defectType,
      defectSeverity: createDto.defectSeverity,
      createdBy: req.user.id,
    };

    return await this.photoAnnotationService.createAnnotation(tenantId, annotationDto);
  }

  @Get('photo/:photoId')
  @ApiOperation({ summary: 'Get all annotations for a photo' })
  @ApiResponse({ status: 200, description: 'Annotations retrieved successfully' })
  async getAnnotationsForPhoto(
    @CurrentTenant() tenantId: string,
    @Param('photoId') photoId: string,
  ) {
    return await this.photoAnnotationService.getAnnotationsForPhoto(tenantId, photoId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get annotation by ID' })
  @ApiResponse({ status: 200, description: 'Annotation retrieved successfully' })
  async getAnnotationById(
    @CurrentTenant() tenantId: string,
    @Param('id') annotationId: string,
  ) {
    const annotation = await this.photoAnnotationService.getAnnotationById(tenantId, annotationId);
    if (!annotation) {
      throw new Error('Annotation not found');
    }
    return annotation;
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update an annotation' })
  @ApiResponse({ status: 200, description: 'Annotation updated successfully' })
  async updateAnnotation(
    @CurrentTenant() tenantId: string,
    @Param('id') annotationId: string,
    @Body(new ZodValidationPipe(UpdateAnnotationSchema)) updateDto: z.infer<typeof UpdateAnnotationSchema>,
    @Request() req: any,
  ) {
    return await this.photoAnnotationService.updateAnnotation(
      tenantId,
      annotationId,
      updateDto,
      req.user.id,
    );
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete an annotation' })
  @ApiResponse({ status: 204, description: 'Annotation deleted successfully' })
  async deleteAnnotation(
    @CurrentTenant() tenantId: string,
    @Param('id') annotationId: string,
    @Request() req: any,
  ) {
    await this.photoAnnotationService.deleteAnnotation(tenantId, annotationId, req.user.id);
  }
}