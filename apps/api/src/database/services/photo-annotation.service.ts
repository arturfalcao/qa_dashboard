import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { PhotoAnnotation } from "../entities/photo-annotation.entity";
import { InspectionPhoto } from "../entities/inspection-photo.entity";
import { DefectType, DefectSeverity } from "@qa-dashboard/shared";

export interface CreatePhotoAnnotationDto {
  photoId: string;
  x: number;
  y: number;
  comment: string;
  defectType?: DefectType;
  defectSeverity?: DefectSeverity;
  createdBy: string;
}

export interface UpdatePhotoAnnotationDto {
  x?: number;
  y?: number;
  comment?: string;
  defectType?: DefectType;
  defectSeverity?: DefectSeverity;
}

@Injectable()
export class PhotoAnnotationService {
  constructor(
    @InjectRepository(PhotoAnnotation)
    private photoAnnotationRepository: Repository<PhotoAnnotation>,
    @InjectRepository(InspectionPhoto)
    private inspectionPhotoRepository: Repository<InspectionPhoto>,
  ) {}

  async createAnnotation(
    tenantId: string,
    createDto: CreatePhotoAnnotationDto,
  ): Promise<PhotoAnnotation> {
    // Verify the photo exists and belongs to the tenant
    const photo = await this.inspectionPhotoRepository.findOne({
      where: { id: createDto.photoId, tenantId },
    });

    if (!photo) {
      throw new Error("Photo not found or access denied");
    }

    const annotation = this.photoAnnotationRepository.create({
      tenantId,
      photoId: createDto.photoId,
      createdBy: createDto.createdBy,
      x: createDto.x,
      y: createDto.y,
      comment: createDto.comment,
      defectType: createDto.defectType,
      defectSeverity: createDto.defectSeverity,
    });

    return await this.photoAnnotationRepository.save(annotation);
  }

  async getAnnotationsForPhoto(
    tenantId: string,
    photoId: string,
  ): Promise<PhotoAnnotation[]> {
    return await this.photoAnnotationRepository.find({
      where: { tenantId, photoId },
      relations: ["user"],
      order: { createdAt: "ASC" },
    });
  }

  async updateAnnotation(
    tenantId: string,
    annotationId: string,
    updateDto: UpdatePhotoAnnotationDto,
    userId: string,
  ): Promise<PhotoAnnotation> {
    const annotation = await this.photoAnnotationRepository.findOne({
      where: { id: annotationId, tenantId, createdBy: userId },
    });

    if (!annotation) {
      throw new Error("Annotation not found or access denied");
    }

    Object.assign(annotation, updateDto);
    return await this.photoAnnotationRepository.save(annotation);
  }

  async deleteAnnotation(
    tenantId: string,
    annotationId: string,
    userId: string,
  ): Promise<void> {
    const result = await this.photoAnnotationRepository.delete({
      id: annotationId,
      tenantId,
      createdBy: userId,
    });

    if (result.affected === 0) {
      throw new Error("Annotation not found or access denied");
    }
  }

  async getAnnotationById(
    tenantId: string,
    annotationId: string,
  ): Promise<PhotoAnnotation | null> {
    return await this.photoAnnotationRepository.findOne({
      where: { id: annotationId, tenantId },
      relations: ["user", "photo"],
    });
  }
}
