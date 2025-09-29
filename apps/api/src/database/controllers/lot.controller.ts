import { Controller, Get, Post, Param, Body, ForbiddenException, Patch } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { LotService } from "../services/lot.service";
import { ClientId, CurrentUser } from "../../common/decorators";
import { ApprovalDto, RejectDto, ApprovalSchema, RejectSchema, UserRole, LotStatus } from "@qa-dashboard/shared";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";

const supplierRoleSchema = z.object({
  roleId: z.string().uuid(),
  sequence: z.number().int().min(0).optional(),
  co2Kg: z.number().nonnegative().optional(),
  notes: z.string().max(250).optional(),
});

const supplierSchema = z.object({
  factoryId: z.string().uuid(),
  sequence: z.number().int().min(0).optional(),
  stage: z.string().max(120).optional(),
  isPrimary: z.boolean().optional(),
  roles: z.array(supplierRoleSchema).optional(),
});

// DPP Hub schemas
const materialCompositionSchema = z.object({
  fiber: z.string().min(1),
  percentage: z.number().min(0).max(100),
  properties: z.record(z.any()).optional(),
});

const certificationSchema = z.object({
  type: z.string().min(1),
  number: z.string().optional(),
  auditLink: z.string().optional(),
  validUntil: z.string().optional(),
  issuer: z.string().optional(),
});

const createLotSchema = z
  .object({
    suppliers: z.array(supplierSchema).min(1).optional(),
    factoryId: z.string().uuid().optional(),
    styleRef: z.string().min(1),
    quantityTotal: z.number().int().positive(),
    status: z.nativeEnum(LotStatus).optional(),
    // DPP Hub fields
    materialComposition: z.array(materialCompositionSchema).optional(),
    dyeLot: z.string().optional(),
    certifications: z.array(certificationSchema).optional(),
    dppMetadata: z.record(z.any()).optional(),
  })
  .refine((data) => (data.suppliers?.length ?? 0) > 0 || !!data.factoryId, {
    message: "At least one supplier must be selected",
    path: ["suppliers"],
  });

const updateLotSchema = z.object({
  suppliers: z.array(supplierSchema).optional(),
  factoryId: z.string().uuid().optional(),
  styleRef: z.string().min(1).optional(),
  quantityTotal: z.number().int().positive().optional(),
  status: z.nativeEnum(LotStatus).optional(),
  // DPP Hub fields
  materialComposition: z.array(materialCompositionSchema).optional(),
  dyeLot: z.string().optional(),
  certifications: z.array(certificationSchema).optional(),
  dppMetadata: z.record(z.any()).optional(),
});

@ApiTags("lots")
@Controller("lots")
export class LotController {
  constructor(private readonly lotService: LotService) {}

  private ensureWriter(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    const allowed = [UserRole.ADMIN, UserRole.OPS_MANAGER];
    if (roles.length > 0 && !roles.some((role) => allowed.includes(role))) {
      throw new ForbiddenException("User lacks permissions to modify lots");
    }
  }

  @Post()
  @ApiOperation({ summary: "Create lot" })
  async createLot(
    @ClientId() clientId: string,
    @Body(new ZodValidationPipe(createLotSchema)) body: z.infer<typeof createLotSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    console.log('🎯 CREATE LOT - Request received:', {
      clientId,
      body: JSON.stringify(body, null, 2),
      user: user?.roles || 'no user'
    });

    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriter(user);
    const { factoryId, styleRef, quantityTotal, status } = body;
    const suppliersPayload = body.suppliers?.map((supplier) => ({
      factoryId: supplier.factoryId,
      sequence: supplier.sequence,
      stage: supplier.stage,
      isPrimary: supplier.isPrimary,
      roles:
        supplier.roles?.map((role) => ({
          roleId: role.roleId,
          sequence: role.sequence,
          co2Kg: role.co2Kg,
          notes: role.notes,
        })) ?? [],
    }));

    console.log('🎯 CREATE LOT - DPP Hub data:', {
      materialComposition: body.materialComposition,
      dyeLot: body.dyeLot,
      certifications: body.certifications,
      dppMetadata: body.dppMetadata
    });

    return this.lotService.createLot(clientId, {
      factoryId,
      suppliers: suppliersPayload,
      styleRef,
      quantityTotal,
      status,
      materialComposition: body.materialComposition as any,
      dyeLot: body.dyeLot,
      certifications: body.certifications as any,
      dppMetadata: body.dppMetadata,
    });
  }

  @Get()
  @ApiOperation({ summary: "List lots for client" })
  async listLots(@ClientId() clientId: string, @CurrentUser() user: any) {
    console.log('🎯 Lots Controller - Debug:', {
      clientId,
      user,
      hasUser: !!user
    });

    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    return this.lotService.listLots(clientId, user);
  }

  @Get(":id")
  @ApiOperation({ summary: "Get lot by ID" })
  async getLot(
    @ClientId() clientId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { id?: string; roles?: UserRole[]; clientId?: string | null },
  ) {
    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    return this.lotService.getLot(clientId, id, user);
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update lot" })
  async updateLot(
    @ClientId() clientId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateLotSchema)) body: z.infer<typeof updateLotSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriter(user);
    const { factoryId, styleRef, quantityTotal, status } = body;
    const suppliersPayload = body.suppliers?.map((supplier) => ({
      factoryId: supplier.factoryId,
      sequence: supplier.sequence,
      stage: supplier.stage,
      isPrimary: supplier.isPrimary,
      roles:
        supplier.roles?.map((role) => ({
          roleId: role.roleId,
          sequence: role.sequence,
          co2Kg: role.co2Kg,
          notes: role.notes,
        })) ?? [],
    }));

    console.log('🎯 UPDATE LOT - DPP Hub data:', {
      materialComposition: body.materialComposition,
      dyeLot: body.dyeLot,
      certifications: body.certifications,
      dppMetadata: body.dppMetadata
    });

    return this.lotService.updateLot(clientId, id, {
      factoryId,
      suppliers: suppliersPayload,
      styleRef,
      quantityTotal,
      status,
      materialComposition: body.materialComposition as any,
      dyeLot: body.dyeLot,
      certifications: body.certifications as any,
      dppMetadata: body.dppMetadata,
    });
  }

  @Post(":id/supply-chain/advance")
  @ApiOperation({ summary: "Advance to the next supply-chain stage" })
  async advanceSupplyChain(
    @ClientId() clientId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!clientId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriter(user);
    return this.lotService.advanceSupplyChainStage(clientId, id);
  }

  @Post(":id/approve")
  @ApiOperation({ summary: "Approve lot" })
  async approveLot(
    @ClientId() clientId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(ApprovalSchema)) approvalDto: ApprovalDto,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    const roles = user?.roles || [];
    const canApprove =
      roles.length === 0 ||
      roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role));

    if (!canApprove) {
      throw new ForbiddenException("User lacks approval permissions");
    }

    const approverId = user?.userId ?? "demo-user";

    await this.lotService.approveLot(clientId, id, approverId, approvalDto.note);

    return { message: "Lot approved successfully" };
  }

  @Post(":id/reject")
  @ApiOperation({ summary: "Reject lot" })
  async rejectLot(
    @ClientId() clientId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(RejectSchema)) rejectDto: RejectDto,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    const roles = user?.roles || [];
    const canReject =
      roles.length === 0 ||
      roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role));

    if (!canReject) {
      throw new ForbiddenException("User lacks rejection permissions");
    }

    const approverId = user?.userId ?? "demo-user";

    await this.lotService.rejectLot(clientId, id, approverId, rejectDto.note);

    return { message: "Lot rejected successfully" };
  }
}
