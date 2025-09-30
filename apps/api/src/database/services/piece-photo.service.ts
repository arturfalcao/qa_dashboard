import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { PiecePhoto } from "../entities/piece-photo.entity";
import { StorageService } from "../../storage/storage.service";

interface CreatePhotoInput {
  pieceId: string;
  filePath: string;
  s3Url?: string;
  capturedAt: Date;
}

@Injectable()
export class PiecePhotoService {
  constructor(
    @InjectRepository(PiecePhoto)
    private readonly photoRepository: Repository<PiecePhoto>,
    private readonly storageService: StorageService,
  ) {}

  async findById(id: string): Promise<PiecePhoto | null> {
    return this.photoRepository.findOne({
      where: { id },
      relations: ["piece"],
    });
  }

  async findByPieceId(pieceId: string): Promise<PiecePhoto[]> {
    return this.photoRepository.find({
      where: { pieceId },
      order: { capturedAt: "ASC" },
    });
  }

  async findBySessionId(sessionId: string, status?: string): Promise<PiecePhoto[]> {
    const query = this.photoRepository
      .createQueryBuilder("photo")
      .leftJoinAndSelect("photo.piece", "piece")
      .where("piece.inspection_session_id = :sessionId", { sessionId });

    if (status) {
      query.andWhere("piece.status = :status", { status });
    }

    return query.orderBy("photo.captured_at", "DESC").getMany();
  }

  async create(input: CreatePhotoInput): Promise<PiecePhoto> {
    const photo = this.photoRepository.create(input);
    return this.photoRepository.save(photo);
  }

  async updateS3Url(id: string, s3Url: string): Promise<void> {
    await this.photoRepository.update(id, { s3Url });
  }

  async findBySessionIdWithUrls(sessionId: string, status?: string): Promise<Array<PiecePhoto & { presignedUrl: string }>> {
    const photos = await this.findBySessionId(sessionId, status);

    const photosWithUrls = await Promise.all(
      photos.map(async (photo) => {
        const presignedUrl = await this.storageService.getPresignedDownloadUrl(
          photo.filePath,
          "photos"
        );
        return {
          ...photo,
          presignedUrl,
        };
      })
    );

    return photosWithUrls;
  }

  async findByPieceIdWithUrls(pieceId: string): Promise<Array<PiecePhoto & { presignedUrl: string }>> {
    const photos = await this.findByPieceId(pieceId);

    const photosWithUrls = await Promise.all(
      photos.map(async (photo) => {
        const presignedUrl = await this.storageService.getPresignedDownloadUrl(
          photo.filePath,
          "photos"
        );
        return {
          ...photo,
          presignedUrl,
        };
      })
    );

    return photosWithUrls;
  }
}