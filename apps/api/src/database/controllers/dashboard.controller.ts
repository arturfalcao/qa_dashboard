import {
  Body,
  Controller,
  Get,
  Param,
  Patch,
  Query,
  ForbiddenException,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiQuery } from "@nestjs/swagger";
import { LotService } from "../services/lot.service";
import { PiecePhotoService } from "../services/piece-photo.service";
import { PieceDefectService } from "../services/piece-defect.service";
import { InspectionSessionService } from "../services/inspection-session.service";
import { StorageService } from "../../storage/storage.service";
import { CurrentUser, ClientId } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { UserRole } from "@qa-dashboard/shared";

const reviewDefectSchema = z.object({
  status: z.enum(["confirmed", "rejected"]),
  notes: z.string().optional(),
});

@ApiTags("dashboard")
@Controller("dashboard")
export class DashboardController {
  constructor(
    private readonly lotService: LotService,
    private readonly piecePhotoService: PiecePhotoService,
    private readonly pieceDefectService: PieceDefectService,
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly storageService: StorageService,
  ) {}

  private ensureReviewAccess(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    const allowed = [UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR];
    if (!roles.some((role) => allowed.includes(role))) {
      throw new ForbiddenException("Review access required");
    }
  }

  @Get("lots/:id/gallery")
  @ApiOperation({ summary: "Get all photos for a lot" })
  @ApiQuery({ name: "status", required: false })
  async getLotGallery(
    @CurrentUser() user: any,
    @ClientId() tenantId: string,
    @Param("id") lotId: string,
    @Query("status") status?: string,
  ) {
    // Verify lot belongs to tenant
    const lot = await this.lotService.findById(lotId);
    if (!lot || lot.tenantId !== tenantId) {
      throw new ForbiddenException("Lot not found");
    }

    const sessions = await this.inspectionSessionService.findByLotId(lotId);
    const allPhotos = [];

    for (const session of sessions) {
      const photos = await this.piecePhotoService.findBySessionId(session.id, status);
      allPhotos.push(...photos);
    }

    // Generate presigned URLs for all photos
    const photosWithUrls = await Promise.all(
      allPhotos.map(async (photo) => ({
        id: photo.id,
        pieceId: photo.pieceId,
        filePath: photo.filePath,
        url: await this.storageService.getPresignedDownloadUrl(photo.filePath, "photos"),
        capturedAt: photo.capturedAt,
        pieceNumber: photo.piece?.pieceNumber,
        pieceStatus: photo.piece?.status,
      }))
    );

    return {
      lotId,
      totalPhotos: photosWithUrls.length,
      photos: photosWithUrls,
    };
  }

  @Get("lots/:id/defects")
  @ApiOperation({ summary: "Get all defects for a lot" })
  @ApiQuery({ name: "status", required: false })
  async getLotDefects(
    @CurrentUser() user: any,
    @ClientId() tenantId: string,
    @Param("id") lotId: string,
    @Query("status") status?: string,
  ) {
    // Verify lot belongs to tenant
    const lot = await this.lotService.findById(lotId);
    if (!lot || lot.tenantId !== tenantId) {
      throw new ForbiddenException("Lot not found");
    }

    const sessions = await this.inspectionSessionService.findByLotId(lotId);
    const allDefects = [];

    for (const session of sessions) {
      const defects = await this.pieceDefectService.findBySessionId(session.id, status);
      allDefects.push(...defects);
    }

    return {
      lotId,
      totalDefects: allDefects.length,
      defects: allDefects.map((defect) => ({
        id: defect.id,
        pieceId: defect.pieceId,
        status: defect.status,
        audioTranscript: defect.audioTranscript,
        flaggedAt: defect.flaggedAt,
        reviewedBy: defect.reviewedBy,
        reviewedAt: defect.reviewedAt,
        notes: defect.notes,
        pieceNumber: defect.piece?.pieceNumber,
        photos: defect.piece?.photos?.map((p) => ({
          id: p.id,
          filePath: p.filePath,
          s3Url: p.s3Url,
        })),
      })),
    };
  }

  @Patch("defects/:id/review")
  @ApiOperation({ summary: "Review and confirm/reject defect" })
  async reviewDefect(
    @CurrentUser() user: any,
    @ClientId() tenantId: string,
    @Param("id") defectId: string,
    @Body(new ZodValidationPipe(reviewDefectSchema)) body: z.infer<typeof reviewDefectSchema>,
  ) {
    this.ensureReviewAccess(user);

    const defect = await this.pieceDefectService.review(
      defectId,
      body.status,
      user.id,
      body.notes,
    );

    // Update piece status if defect rejected
    if (body.status === "rejected") {
      await this.pieceDefectService.updatePieceStatusAfterReview(defect.pieceId);
    }

    return {
      success: true,
      defectId: defect.id,
      status: defect.status,
    };
  }

  @Get("feed/live")
  @ApiOperation({ summary: "Get live feed for polling" })
  async getLiveFeed(@CurrentUser() user: any, @ClientId() tenantId: string) {
    // Get active sessions for this tenant
    const activeSessions = await this.inspectionSessionService.findActiveByTenantId(tenantId);

    // Get recent defects (last 50)
    const recentDefects = await this.pieceDefectService.findRecentByTenantId(tenantId, 50);

    return {
      activeSessions: activeSessions.map((session) => ({
        id: session.id,
        lotId: session.lotId,
        operatorId: session.operatorId,
        startedAt: session.startedAt,
        piecesInspected: session.piecesInspected,
        piecesDefect: session.piecesDefect,
        piecesPotentialDefect: session.piecesPotentialDefect,
        lot: {
          styleRef: session.lot?.styleRef,
        },
      })),
      pendingDefects: recentDefects
        .filter((d) => d.status === "pending_review")
        .map((defect) => ({
          id: defect.id,
          pieceId: defect.pieceId,
          audioTranscript: defect.audioTranscript,
          flaggedAt: defect.flaggedAt,
          pieceNumber: defect.piece?.pieceNumber,
          sessionId: defect.piece?.inspectionSessionId,
        })),
    };
  }
}