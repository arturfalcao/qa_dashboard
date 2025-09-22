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
import { CurrentTenant, TenantId, Public } from '../../common/decorators';
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
@UseGuards(JwtAuthGuard)
export class PhotoAnnotationController {
  constructor(private photoAnnotationService: PhotoAnnotationService) {}

  @Post()
  @Public()
  @ApiOperation({ summary: 'Create a new photo annotation' })
  @ApiResponse({ status: 201, description: 'Annotation created successfully' })
  async createAnnotation(
    @TenantId() tenantId: string,
    @Body(new ZodValidationPipe(CreateAnnotationSchema)) createDto: z.infer<typeof CreateAnnotationSchema>,
    @Request() req: any,
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    const annotationDto: CreatePhotoAnnotationDto = {
      photoId: createDto.photoId,
      x: createDto.x,
      y: createDto.y,
      comment: createDto.comment,
      defectType: createDto.defectType,
      defectSeverity: createDto.defectSeverity,
      createdBy: req.user?.id || 'demo-user',
    };

    return await this.photoAnnotationService.createAnnotation(finalTenantId, annotationDto);
  }

  @Get('photo/:photoId')
  @Public()
  @ApiOperation({ summary: 'Get all annotations for a photo' })
  @ApiResponse({ status: 200, description: 'Annotations retrieved successfully' })
  async getAnnotationsForPhoto(
    @TenantId() tenantId: string,
    @Param('photoId') photoId: string,
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return await this.photoAnnotationService.getAnnotationsForPhoto(finalTenantId, photoId);
  }

  @Get(':id')
  @Public()
  @ApiOperation({ summary: 'Get annotation by ID' })
  @ApiResponse({ status: 200, description: 'Annotation retrieved successfully' })
  async getAnnotationById(
    @TenantId() tenantId: string,
    @Param('id') annotationId: string,
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    const annotation = await this.photoAnnotationService.getAnnotationById(finalTenantId, annotationId);
    if (!annotation) {
      throw new Error('Annotation not found');
    }
    return annotation;
  }

  @Put(':id')
  @Public()
  @ApiOperation({ summary: 'Update an annotation' })
  @ApiResponse({ status: 200, description: 'Annotation updated successfully' })
  async updateAnnotation(
    @TenantId() tenantId: string,
    @Param('id') annotationId: string,
    @Body(new ZodValidationPipe(UpdateAnnotationSchema)) updateDto: z.infer<typeof UpdateAnnotationSchema>,
    @Request() req: any,
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return await this.photoAnnotationService.updateAnnotation(
      finalTenantId,
      annotationId,
      updateDto,
      req.user?.id || 'demo-user',
    );
  }

  @Delete(':id')
  @Public()
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete an annotation' })
  @ApiResponse({ status: 204, description: 'Annotation deleted successfully' })
  async deleteAnnotation(
    @TenantId() tenantId: string,
    @Param('id') annotationId: string,
    @Request() req: any,
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    await this.photoAnnotationService.deleteAnnotation(finalTenantId, annotationId, req.user?.id || 'demo-user');
  }
}