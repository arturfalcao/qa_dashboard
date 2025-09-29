import {
  Body,
  Controller,
  Post,
  Headers,
  UnauthorizedException,
  BadRequestException,
  UploadedFile,
  UseInterceptors,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiHeader } from "@nestjs/swagger";
import { FileInterceptor } from "@nestjs/platform-express";
import { EdgeDeviceService } from "../services/edge-device.service";
import { ApparelPieceService } from "../services/apparel-piece.service";
import { PiecePhotoService } from "../services/piece-photo.service";
import { PieceDefectService } from "../services/piece-defect.service";
import { InspectionSessionService } from "../services/inspection-session.service";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { diskStorage } from "multer";
import { extname } from "path";

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
@Controller("edge")
export class EdgeController {
  constructor(
    private readonly edgeDeviceService: EdgeDeviceService,
    private readonly apparelPieceService: ApparelPieceService,
    private readonly piecePhotoService: PiecePhotoService,
    private readonly pieceDefectService: PieceDefectService,
    private readonly inspectionSessionService: InspectionSessionService,
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

  @Post("photo/upload")
  @ApiOperation({ summary: "Upload photo from edge device" })
  @ApiHeader({ name: "X-Device-Secret", required: true })
  @UseInterceptors(
    FileInterceptor("photo", {
      storage: diskStorage({
        destination: "./uploads/edge-photos",
        filename: (req, file, cb) => {
          const uniqueSuffix = Date.now() + "-" + Math.round(Math.random() * 1e9);
          cb(null, `photo-${uniqueSuffix}${extname(file.originalname)}`);
        },
      }),
      limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
    }),
  )
  async uploadPhoto(
    @Headers("x-device-secret") secretKey: string,
    @Body(new ZodValidationPipe(photoUploadSchema)) body: z.infer<typeof photoUploadSchema>,
    @UploadedFile() file: Express.Multer.File,
  ) {
    await this.validateDeviceSecret(secretKey);

    if (!file) {
      throw new BadRequestException("Photo file required");
    }

    // Get or create current piece
    let pieceId = body.pieceId;
    if (!pieceId) {
      const session = await this.inspectionSessionService.findById(body.sessionId);
      if (!session) {
        throw new BadRequestException("Session not found");
      }

      // Create new piece
      const piece = await this.apparelPieceService.create({
        inspectionSessionId: body.sessionId,
        pieceNumber: session.piecesInspected + 1,
        status: "pending_review",
        inspectionStartedAt: new Date(),
      });
      pieceId = piece.id;
    }

    // Save photo
    const photo = await this.piecePhotoService.create({
      pieceId,
      filePath: file.path,
      capturedAt: new Date(),
    });

    return {
      success: true,
      photoId: photo.id,
      pieceId,
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