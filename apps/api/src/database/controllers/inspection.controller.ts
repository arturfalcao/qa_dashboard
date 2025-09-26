import { Body, Controller, Get, Param, Post, Query, ForbiddenException } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiQuery,
} from "@nestjs/swagger";
import { InspectionService } from "../services/inspection.service";
import { ClientId, CurrentUser } from "../../common/decorators";
import { LotService } from "../services/lot.service";
import { DefectService } from "../services/defect.service";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { UserRole } from "@qa-dashboard/shared";

const createInspectionSchema = z.object({
  lotId: z.string().uuid(),
  startedAt: z.string().datetime().optional(),
  finishedAt: z.string().datetime().optional(),
  inspectorId: z.string().uuid().optional(),
});

const createDefectSchema = z.object({
  pieceCode: z.string().optional(),
  note: z.string().optional(),
  defectTypeId: z.string().uuid().optional(),
  photos: z
    .array(
      z.object({
        url: z.string().url(),
        annotation: z.record(z.any()).optional(),
      }),
    )
    .optional(),
});

@ApiTags("inspections")
@Controller("inspections")
export class InspectionController {
  constructor(
    private readonly inspectionService: InspectionService,
    private readonly lotService: LotService,
    private readonly defectService: DefectService,
  ) {}

  private ensureWriteAccess(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    const allowed = [UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.INSPECTOR];
    if (roles.length > 0 && !roles.some((role) => allowed.includes(role))) {
      throw new ForbiddenException("Insufficient permissions");
    }
  }

  @Get()
  @ApiOperation({ summary: "Get inspections for client" })
  @ApiQuery({ name: "since", required: false, description: "ISO date string" })
  @ApiQuery({
    name: "limit",
    required: false,
    type: Number,
    description: "Limit results",
  })
  async getInspections(
    @ClientId() clientId: string,
    @Query("since") since?: string,
    @Query("limit") limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit) : 50;
    return this.inspectionService.getInspections(clientId, since, limitNum);
  }

  @Post()
  @ApiOperation({ summary: "Create inspection" })
  async createInspection(
    @ClientId() clientId: string,
    @Body(new ZodValidationPipe(createInspectionSchema)) body: z.infer<typeof createInspectionSchema>,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriteAccess(user);

    // Ensure lot belongs to client
    await this.lotService.getLot(clientId, body.lotId);

    const inspectorId = body.inspectorId ?? user?.userId ?? "demo-user";

    return this.inspectionService.createInspection({
      lotId: body.lotId,
      inspectorId,
      startedAt: body.startedAt ? new Date(body.startedAt) : undefined,
      finishedAt: body.finishedAt ? new Date(body.finishedAt) : undefined,
    });
  }

  @Post(":id/defects")
  @ApiOperation({ summary: "Add defect to inspection" })
  async createDefect(
    @ClientId() clientId: string,
    @Param("id") inspectionId: string,
    @Body(new ZodValidationPipe(createDefectSchema)) body: z.infer<typeof createDefectSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriteAccess(user);

    await this.inspectionService.ensureInspectionOwnership(clientId, inspectionId);
    return this.defectService.create({
      inspectionId,
      pieceCode: body.pieceCode,
      note: body.note,
      defectTypeId: body.defectTypeId,
      photos: body.photos?.map((photo) => ({
        url: photo.url,
        annotation: photo.annotation ?? undefined,
      })),
    });
  }
}
