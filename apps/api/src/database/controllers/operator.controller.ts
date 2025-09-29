import {
  Body,
  Controller,
  Get,
  Param,
  Post,
  Patch,
  ForbiddenException,
} from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { InspectionSessionService } from "../services/inspection-session.service";
import { LotService } from "../services/lot.service";
import { CurrentUser } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { UserRole } from "@qa-dashboard/shared";

const startSessionSchema = z.object({
  lotId: z.string().uuid(),
  deviceId: z.string().uuid(),
});

const sessionIdSchema = z.object({
  sessionId: z.string().uuid(),
});

@ApiTags("operator")
@Controller("operator")
export class OperatorController {
  constructor(
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly lotService: LotService,
  ) {}

  private ensureOperatorAccess(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    if (!roles.includes(UserRole.OPERATOR)) {
      throw new ForbiddenException("Operator access required");
    }
  }

  @Post("session/start")
  @ApiOperation({ summary: "Start inspection session" })
  async startSession(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(startSessionSchema)) body: z.infer<typeof startSessionSchema>,
  ) {
    this.ensureOperatorAccess(user);

    // Check for active session on this lot
    const activeSession = await this.inspectionSessionService.findActiveByLotId(body.lotId);
    if (activeSession) {
      throw new ForbiddenException("Lot already has an active inspection session");
    }

    // Update lot status to INSPECTION
    await this.lotService.updateStatus(body.lotId, "INSPECTION" as any);

    // Create session
    const session = await this.inspectionSessionService.create({
      lotId: body.lotId,
      deviceId: body.deviceId,
      operatorId: user.id,
      startedAt: new Date(),
    });

    return {
      success: true,
      sessionId: session.id,
    };
  }

  @Patch("session/pause")
  @ApiOperation({ summary: "Pause inspection session" })
  async pauseSession(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(sessionIdSchema)) body: z.infer<typeof sessionIdSchema>,
  ) {
    this.ensureOperatorAccess(user);

    await this.inspectionSessionService.pause(body.sessionId);

    return {
      success: true,
      message: "Session paused",
    };
  }

  @Patch("session/resume")
  @ApiOperation({ summary: "Resume inspection session" })
  async resumeSession(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(sessionIdSchema)) body: z.infer<typeof sessionIdSchema>,
  ) {
    this.ensureOperatorAccess(user);

    await this.inspectionSessionService.resume(body.sessionId);

    return {
      success: true,
      message: "Session resumed",
    };
  }

  @Post("session/end")
  @ApiOperation({ summary: "End inspection session" })
  async endSession(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(sessionIdSchema)) body: z.infer<typeof sessionIdSchema>,
  ) {
    this.ensureOperatorAccess(user);

    const session = await this.inspectionSessionService.end(body.sessionId);

    // Update lot status back to previous state (e.g., IN_TRANSIT or COMPLETED)
    await this.lotService.updateStatus(session.lotId, "COMPLETED" as any);

    return {
      success: true,
      message: "Session ended",
    };
  }

  @Get("session/:id/live")
  @ApiOperation({ summary: "Get live session data (polling endpoint)" })
  async getLiveSession(@CurrentUser() user: any, @Param("id") sessionId: string) {
    this.ensureOperatorAccess(user);

    const session = await this.inspectionSessionService.findByIdWithDetails(sessionId);
    if (!session) {
      throw new ForbiddenException("Session not found");
    }

    return {
      session: {
        id: session.id,
        startedAt: session.startedAt,
        pausedAt: session.pausedAt,
        piecesInspected: session.piecesInspected,
        piecesOk: session.piecesOk,
        piecesDefect: session.piecesDefect,
        piecesPotentialDefect: session.piecesPotentialDefect,
      },
      currentPiece: session.pieces?.[session.pieces.length - 1] || null,
      recentPhotos: session.pieces
        ?.flatMap((p) => p.photos || [])
        .slice(-10)
        .map((photo) => ({
          id: photo.id,
          filePath: photo.filePath,
          capturedAt: photo.capturedAt,
        })),
    };
  }
}