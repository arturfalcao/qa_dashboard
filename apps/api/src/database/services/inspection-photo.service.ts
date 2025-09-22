import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { InspectionPhoto } from "../entities/inspection-photo.entity";
import { Inspection } from "../entities/inspection.entity";
import { PhotoAngle } from "@qa-dashboard/shared";
import { StorageService } from "../../storage/storage.service";

export interface CreateInspectionPhotoDto {
  inspectionId: string;
  angle: PhotoAngle;
  photoKey: string;
  capturedAt?: Date;
}

@Injectable()
export class InspectionPhotoService {
  constructor(
    @InjectRepository(InspectionPhoto)
    private inspectionPhotoRepository: Repository<InspectionPhoto>,
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    private storageService: StorageService,
  ) {}

  async createPhoto(
    tenantId: string,
    createDto: CreateInspectionPhotoDto,
  ): Promise<InspectionPhoto> {
    // Verify the inspection exists and belongs to the tenant
    const inspection = await this.inspectionRepository.findOne({
      where: { id: createDto.inspectionId, tenantId },
    });

    if (!inspection) {
      throw new Error("Inspection not found or access denied");
    }

    const photo = this.inspectionPhotoRepository.create({
      tenantId,
      inspectionId: createDto.inspectionId,
      angle: createDto.angle,
      photoKey: createDto.photoKey,
      capturedAt: createDto.capturedAt || new Date(),
    });

    return await this.inspectionPhotoRepository.save(photo);
  }

  async getPhotosForInspection(
    tenantId: string,
    inspectionId: string,
  ): Promise<InspectionPhoto[]> {
    const photos = await this.inspectionPhotoRepository.find({
      where: { tenantId, inspectionId },
      relations: ["annotations", "annotations.user"],
      order: { capturedAt: "ASC" },
    });

    // Add presigned URLs for photos
    for (const photo of photos) {
      photo.photoUrl = await this.storageService.getPresignedUrl(
        photo.photoKey,
      );
    }

    return photos;
  }

  async getPhotoById(
    tenantId: string,
    photoId: string,
  ): Promise<InspectionPhoto | null> {
    const photo = await this.inspectionPhotoRepository.findOne({
      where: { id: photoId, tenantId },
      relations: ["annotations", "annotations.user", "inspection"],
    });

    if (photo) {
      photo.photoUrl = await this.storageService.getPresignedUrl(
        photo.photoKey,
      );
    }

    return photo;
  }

  async deletePhoto(tenantId: string, photoId: string): Promise<void> {
    const photo = await this.inspectionPhotoRepository.findOne({
      where: { id: photoId, tenantId },
    });

    if (!photo) {
      throw new Error("Photo not found or access denied");
    }

    // Delete the physical file from storage
    await this.storageService.deleteFile(photo.photoKey);

    // Delete the database record (this will cascade to annotations)
    await this.inspectionPhotoRepository.delete({ id: photoId, tenantId });
  }

  async getPhotosByAngle(
    tenantId: string,
    inspectionId: string,
    angle: PhotoAngle,
  ): Promise<InspectionPhoto[]> {
    const photos = await this.inspectionPhotoRepository.find({
      where: { tenantId, inspectionId, angle },
      relations: ["annotations", "annotations.user"],
      order: { capturedAt: "DESC" },
    });

    // Add presigned URLs for photos
    for (const photo of photos) {
      photo.photoUrl = await this.storageService.getPresignedUrl(
        photo.photoKey,
      );
    }

    return photos;
  }

  async updatePhoto(
    tenantId: string,
    photoId: string,
    updates: Partial<Pick<InspectionPhoto, "angle" | "capturedAt">>,
  ): Promise<InspectionPhoto> {
    const photo = await this.inspectionPhotoRepository.findOne({
      where: { id: photoId, tenantId },
    });

    if (!photo) {
      throw new Error("Photo not found or access denied");
    }

    Object.assign(photo, updates);
    return await this.inspectionPhotoRepository.save(photo);
  }
}
