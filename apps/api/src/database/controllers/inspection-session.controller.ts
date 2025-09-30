import { Controller, Get, Param, ForbiddenException } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { InspectionSessionService } from "../services/inspection-session.service";
import { StorageService } from "../../storage/storage.service";
import { ClientId, CurrentUser } from "../../common/decorators";
import { UserRole } from "@qa-dashboard/shared";

@ApiTags("inspection-sessions")
@Controller("inspection-sessions")
export class InspectionSessionController {
  constructor(
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly storageService: StorageService,
  ) {}

  @Get(":id")
  @ApiOperation({ summary: "Get inspection session with pieces and photos" })
  async getSession(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!tenantId) {
      throw new ForbiddenException("Missing client context");
    }

    // Get session with all relations
    const session = await this.inspectionSessionService.findByIdWithDetails(id);
    if (!session) {
      throw new ForbiddenException("Session not found");
    }

    // Verify session belongs to this tenant
    const sessionWithLot = await this.inspectionSessionService.findById(id, ["lot"]);
    if (!sessionWithLot || sessionWithLot.lot.tenantId !== tenantId) {
      throw new ForbiddenException("Access denied");
    }

    // Generate presigned URLs for all photos
    const piecesWithUrls = await Promise.all(
      (session.pieces || []).map(async (piece) => {
        const photosWithUrls = await Promise.all(
          (piece.photos || []).map(async (photo) => ({
            ...photo,
            url: await this.storageService.getPresignedDownloadUrl(photo.filePath, "photos"),
          }))
        );

        return {
          ...piece,
          photos: photosWithUrls,
        };
      })
    );

    return {
      ...session,
      pieces: piecesWithUrls,
    };
  }

  @Get(":id/gallery")
  @ApiOperation({ summary: "Get gallery view of all photos in session" })
  async getSessionGallery(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!tenantId) {
      throw new ForbiddenException("Missing client context");
    }

    // Get session with all relations
    const session = await this.inspectionSessionService.findByIdWithDetails(id);
    if (!session) {
      throw new ForbiddenException("Session not found");
    }

    // Verify session belongs to this tenant
    const sessionWithLot = await this.inspectionSessionService.findById(id, ["lot"]);
    if (!sessionWithLot || sessionWithLot.lot.tenantId !== tenantId) {
      throw new ForbiddenException("Access denied");
    }

    // Flatten all photos from all pieces with presigned URLs
    const allPhotos: any[] = [];

    for (const piece of session.pieces || []) {
      for (const photo of piece.photos || []) {
        const url = await this.storageService.getPresignedDownloadUrl(photo.filePath, "photos");
        allPhotos.push({
          id: photo.id,
          url,
          filePath: photo.filePath,
          capturedAt: photo.capturedAt,
          pieceId: piece.id,
          pieceNumber: piece.pieceNumber,
          pieceStatus: piece.status,
        });
      }
    }

    return {
      sessionId: session.id,
      lotId: session.lotId,
      startedAt: session.startedAt,
      endedAt: session.endedAt,
      piecesInspected: session.piecesInspected,
      photos: allPhotos.sort((a, b) =>
        new Date(b.capturedAt).getTime() - new Date(a.capturedAt).getTime()
      ),
    };
  }
}
