import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { PiecePhoto } from "../entities/piece-photo.entity";
import { StorageService } from "../../storage/storage.service";

@Injectable()
export class MigratePhotosService {
  constructor(
    @InjectRepository(PiecePhoto)
    private readonly photoRepository: Repository<PiecePhoto>,
    private readonly storageService: StorageService,
  ) {}

  async migratePhotos(): Promise<{ migrated: number; failed: number; errors: Array<{ photoId: string; error: string }> }> {
    console.log("🔄 Starting photo migration...");

    // Find all photos with old path structure
    const oldPhotos = await this.photoRepository
      .createQueryBuilder("photo")
      .leftJoinAndSelect("photo.piece", "piece")
      .leftJoinAndSelect("piece.session", "session")
      .leftJoinAndSelect("session.lot", "lot")
      .where("photo.file_path LIKE :pattern", { pattern: "clients/edge-devices/%" })
      .getMany();

    console.log(`📊 Found ${oldPhotos.length} photos to migrate`);

    if (oldPhotos.length === 0) {
      console.log("✅ No photos to migrate");
      return;
    }

    let migrated = 0;
    let failed = 0;
    const errors: Array<{ photoId: string; error: string }> = [];

    for (const photo of oldPhotos) {
      try {
        // Validate we have all required data
        if (!photo.piece?.session?.lot?.tenantId) {
          throw new Error("Missing tenant context - photo might be orphaned");
        }

        const { tenantId, id: lotId } = photo.piece.session.lot;
        const { id: pieceId } = photo.piece;
        const oldPath = photo.filePath;

        // Extract original filename from old path
        const filename = oldPath.split("/").pop() || "photo.jpg";

        // Generate new path
        const newPath = this.storageService.generateKeyForPiece(
          tenantId,
          lotId,
          pieceId,
          filename
        );

        console.log(`  📦 Migrating photo ${photo.id}`);
        console.log(`    Old: ${oldPath}`);
        console.log(`    New: ${newPath}`);

        // Copy file in S3 to new location
        const fileBuffer = await this.storageService.getFileBuffer(oldPath, "photos");
        await this.storageService.uploadFileWithKey(
          newPath,
          fileBuffer,
          "image/jpeg",
          "photos"
        );

        // Update database record
        await this.photoRepository.update(photo.id, {
          filePath: newPath,
        });

        // Delete old file (optional - comment out if you want to keep as backup)
        // await this.storageService.deleteFile(oldPath, "photos");

        migrated++;
        console.log(`    ✅ Migrated successfully`);
      } catch (error: any) {
        failed++;
        const errorMsg = error.message || "Unknown error";
        errors.push({ photoId: photo.id, error: errorMsg });
        console.log(`    ❌ Failed: ${errorMsg}`);
      }
    }

    console.log("\n📊 Migration Summary:");
    console.log(`  ✅ Migrated: ${migrated}`);
    console.log(`  ❌ Failed: ${failed}`);

    if (errors.length > 0) {
      console.log("\n❌ Errors:");
      errors.forEach(({ photoId, error }) => {
        console.log(`  - Photo ${photoId}: ${error}`);
      });
    }

    console.log("\n✨ Migration complete!");
    console.log("💡 Old files are still in place as backup");
    console.log("💡 Run cleanup script later to remove old files");

    return { migrated, failed, errors };
  }
}
