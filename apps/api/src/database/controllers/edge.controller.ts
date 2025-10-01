import {
  Body,
  Controller,
  Post,
  Get,
  Headers,
  UnauthorizedException,
  BadRequestException,
  UploadedFile,
  UseInterceptors,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiHeader } from "@nestjs/swagger";
import { FileInterceptor } from "@nestjs/platform-express";
import { Public } from "../../auth/public.decorator";
import { EdgeDeviceService } from "../services/edge-device.service";
import { ApparelPieceService } from "../services/apparel-piece.service";
import { PiecePhotoService } from "../services/piece-photo.service";
import { PieceDefectService } from "../services/piece-defect.service";
import { InspectionSessionService } from "../services/inspection-session.service";
import { StorageService } from "../../storage/storage.service";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";

const photoUploadSchema = z.object({
  sessionId: z.string().uuid(),
  pieceId: z.string().uuid().optional(),
});

const defectFlagSchema = z.object({
  pieceId: z.string().uuid(),
  audioTranscript: z.string().optional(),
});

const potentialDefectSchema = z.object({
  pieceId: z.string().uuid(),
  audioTranscript: z.string().optional(),
});

const pieceCompleteSchema = z.object({
  sessionId: z.string().uuid(),
  pieceId: z.string().uuid(),
  status: z.enum(["ok", "defect", "potential_defect"]),
});

@ApiTags("edge")
@Public()
@Controller("edge")
export class EdgeController {
  constructor(
    private readonly edgeDeviceService: EdgeDeviceService,
    private readonly apparelPieceService: ApparelPieceService,
    private readonly piecePhotoService: PiecePhotoService,
    private readonly pieceDefectService: PieceDefectService,
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly storageService: StorageService,
  ) {}

  private async validateDeviceSecret(secretKey?: string) {
    if (!secretKey) {
      throw new UnauthorizedException("Device secret required");
    }

    const device = await this.edgeDeviceService.findBySecretKey(secretKey);
    if (!device) {
      throw new UnauthorizedException("Invalid device secret");
    }

    // Update last seen
    await this.edgeDeviceService.updateLastSeen(device.id);

    return device;
  }

  @Get("ping")
  @ApiOperation({ summary: "Health check endpoint for edge devices" })
  @ApiHeader({ name: "X-Device-Secret", required: false })
  async ping(@Headers("x-device-secret") secretKey?: string) {
    if (secretKey) {
      try {
        const device = await this.validateDeviceSecret(secretKey);
        return {
          status: "ok",
          authenticated: true,
          deviceId: device.id,
          deviceName: device.name,
          timestamp: new Date().toISOString(),
        };
      } catch (error) {
        return {
          status: "ok",
          authenticated: false,
          error: "Invalid device secret",
          timestamp: new Date().toISOString(),
        };
      }
    }

    return {
      status: "ok",
      authenticated: false,
      timestamp: new Date().toISOString(),
    };
  }

  @Get("session/current")
  @ApiOperation({ summary: "Get current active session for this device" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  async getCurrentSession(@Headers("x-device-secret") secretKey: string) {
    const device = await this.validateDeviceSecret(secretKey);

    // Find active session for this specific device
    const activeSession = await this.inspectionSessionService.findActiveByDeviceId(
      device.id,
    );

    if (!activeSession) {
      return {
        active: false,
        sessionId: null,
        currentPieceId: null,
        status: "inactive",
      };
    }

    // Get current piece (if any in-progress piece exists)
    const pieces = await this.apparelPieceService.findBySessionId(
      activeSession.id,
    );
    const currentPiece = pieces.find((p) => !p.inspectionCompletedAt);

    return {
      active: true,
      sessionId: activeSession.id,
      currentPieceId: currentPiece?.id || null,
      status: activeSession.pausedAt ? "paused" : "active",
      lotId: activeSession.lotId,
      piecesInspected: activeSession.piecesInspected,
      startedAt: activeSession.startedAt,
      pausedAt: activeSession.pausedAt,
    };
  }

  @Post("photo/upload")
  @ApiOperation({ summary: "Upload photo from edge device" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  @UseInterceptors(
    FileInterceptor("photo", {
      limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
    }),
  )
  async uploadPhoto(
    @Headers("x-device-secret") secretKey: string,
    @Body(new ZodValidationPipe(photoUploadSchema)) body: z.infer<typeof photoUploadSchema>,
    @UploadedFile() file: Express.Multer.File,
  ) {
    const device = await this.validateDeviceSecret(secretKey);

    if (!file) {
      throw new BadRequestException("Photo file required");
    }

    // Get session with lot relation to access tenantId
    const session = await this.inspectionSessionService.findById(body.sessionId, ["lot"]);
    if (!session) {
      throw new BadRequestException("Session not found");
    }

    // Get or create current piece
    let pieceId = body.pieceId;
    if (!pieceId) {
      // Create new piece
      const piece = await this.apparelPieceService.create({
        inspectionSessionId: body.sessionId,
        pieceNumber: session.piecesInspected + 1,
        status: "pending_review",
        inspectionStartedAt: new Date(),
      });
      pieceId = piece.id;
    }

    // Generate organized S3 key: clients/{tenantId}/lots/{lotId}/pieces/{pieceId}/{uuid}-{filename}
    const fileKey = this.storageService.generateKeyForPiece(
      session.lot.tenantId,
      session.lotId,
      pieceId,
      file.originalname
    );

    // Upload to S3/Spaces bucket
    await this.storageService.uploadFileWithKey(
      fileKey,
      file.buffer,
      file.mimetype || "image/jpeg",
      "photos"
    );

    // Save photo with S3 key
    const photo = await this.piecePhotoService.create({
      pieceId,
      filePath: fileKey,
      capturedAt: new Date(),
    });

    return {
      success: true,
      photoId: photo.id,
      pieceId,
      filePath: fileKey,
    };
  }

  @Post("defect/flag")
  @ApiOperation({ summary: "Flag defect from edge device" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  async flagDefect(
    @Headers("x-device-secret") secretKey: string,
    @Body(new ZodValidationPipe(defectFlagSchema)) body: z.infer<typeof defectFlagSchema>,
  ) {
    await this.validateDeviceSecret(secretKey);

    const defect = await this.pieceDefectService.create({
      pieceId: body.pieceId,
      status: "pending_review",
      audioTranscript: body.audioTranscript,
      flaggedAt: new Date(),
    });

    // Update piece status
    await this.apparelPieceService.updateStatus(body.pieceId, "defect");

    return {
      success: true,
      defectId: defect.id,
    };
  }

  @Post("defect/potential")
  @ApiOperation({ summary: "Flag potential defect from edge device" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  async flagPotentialDefect(
    @Headers("x-device-secret") secretKey: string,
    @Body(new ZodValidationPipe(potentialDefectSchema)) body: z.infer<typeof potentialDefectSchema>,
  ) {
    await this.validateDeviceSecret(secretKey);

    const defect = await this.pieceDefectService.create({
      pieceId: body.pieceId,
      status: "pending_review",
      audioTranscript: body.audioTranscript,
      flaggedAt: new Date(),
    });

    // Update piece status
    await this.apparelPieceService.updateStatus(body.pieceId, "potential_defect");

    return {
      success: true,
      defectId: defect.id,
    };
  }

  @Post("piece/complete")
  @ApiOperation({ summary: "Mark piece as complete and move to next" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  async completePiece(
    @Headers("x-device-secret") secretKey: string,
    @Body(new ZodValidationPipe(pieceCompleteSchema)) body: z.infer<typeof pieceCompleteSchema>,
  ) {
    await this.validateDeviceSecret(secretKey);

    // Complete current piece
    await this.apparelPieceService.complete(body.pieceId, body.status);

    // Update session stats
    await this.inspectionSessionService.incrementPiece(body.sessionId, body.status);

    return {
      success: true,
      message: "Piece completed",
    };
  }
}