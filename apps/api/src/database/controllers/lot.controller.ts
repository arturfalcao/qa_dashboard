import { Controller, Get, Post, Param, Body, ForbiddenException, Patch, UseInterceptors, UploadedFile, BadRequestException } from "@nestjs/common";
import { ApiTags, ApiOperation, ApiConsumes, ApiBody } from "@nestjs/swagger";
import { FileInterceptor } from "@nestjs/platform-express";
import { LotService } from "../services/lot.service";
import { ClientService } from "../services/client.service";
import { ClientId, CurrentUser } from "../../common/decorators";
import { ApprovalDto, RejectDto, ApprovalSchema, RejectSchema, UserRole, LotStatus } from "@qa-dashboard/shared";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { TechPackService } from "../../tech-pack/tech-pack.service";
import { StorageService } from "../../storage/storage.service";

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

const sizeSpecificationSchema = z.object({
  size: z.string().min(1),
  quantity: z.number().int().nonnegative().optional(),
  measurements: z.record(z.number()).optional(),
});

const createLotSchema = z
  .object({
    tenantId: z.string().uuid().optional(),
    clientId: z.string().uuid().optional(),
    suppliers: z.array(supplierSchema).optional(),
    factoryId: z.string().uuid().optional(),
    styleRef: z.string().min(1),
    quantityTotal: z.number().int().positive(),
    status: z.nativeEnum(LotStatus).optional(),
    // Tech Pack reference
    techPackId: z.string().uuid().optional(),
    // DPP Hub fields
    materialComposition: z.array(materialCompositionSchema).optional(),
    dyeLot: z.string().optional(),
    certifications: z.array(certificationSchema).optional(),
    dppMetadata: z.record(z.any()).optional(),
    sizeSpecifications: z.array(sizeSpecificationSchema).optional(),
  })
  .refine(
    (data) =>
      // Skip validation for PLANNED status (can add suppliers later)
      data.status === LotStatus.PLANNED ||
      (data.suppliers?.length ?? 0) > 0 ||
      !!data.factoryId,
    {
      message: "At least one supplier or factory must be selected",
      path: ["suppliers"],
    }
  );

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
  sizeSpecifications: z.array(sizeSpecificationSchema).optional(),
});

@ApiTags("lots")
@Controller("lots")
export class LotController {
  constructor(
    private readonly lotService: LotService,
    private readonly clientService: ClientService,
    private readonly techPackService: TechPackService,
    private readonly storageService: StorageService,
  ) {}

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
    @ClientId() defaultTenantId: string,
    @Body(new ZodValidationPipe(createLotSchema)) body: z.infer<typeof createLotSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.ensureWriter(user);

    const isAdmin = user?.roles?.includes(UserRole.ADMIN) ?? false;

    let tenantId: string;
    let clientId: string | undefined;

    if (isAdmin && body.clientId) {
      // Admin selected a specific client, get the client's tenant
      const client = await this.clientService.findById(body.clientId);
      tenantId = client.tenantId;
      clientId = client.id;
    } else if (isAdmin && body.tenantId) {
      // Legacy support: admin specified tenantId directly
      tenantId = body.tenantId;
    } else {
      // Non-admin user, use their tenant context
      tenantId = defaultTenantId;
    }

    console.log('🎯 CREATE LOT - Request received:', {
      defaultTenantId,
      requestedClientId: body.clientId,
      requestedTenantId: body.tenantId,
      finalTenantId: tenantId,
      finalClientId: clientId,
      isAdmin,
      body: JSON.stringify(body, null, 2),
      user: user?.roles || 'no user'
    });

    if (!tenantId) {
      throw new ForbiddenException(isAdmin ? "Admin must specify a client" : "Missing client context");
    }
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
      dppMetadata: body.dppMetadata,
      sizeSpecifications: body.sizeSpecifications
    });

    return this.lotService.createLot(tenantId, {
      clientId,
      factoryId,
      suppliers: suppliersPayload,
      styleRef,
      quantityTotal,
      status,
      techPackId: body.techPackId,
      materialComposition: body.materialComposition as any,
      dyeLot: body.dyeLot,
      certifications: body.certifications as any,
      dppMetadata: body.dppMetadata,
      sizeSpecifications: body.sizeSpecifications as any,
    });
  }

  @Get()
  @ApiOperation({ summary: "List lots for client" })
  async listLots(@ClientId() tenantId: string, @CurrentUser() user: any) {
    console.log('🎯 Lots Controller - Debug:', {
      tenantId,
      user,
      hasUser: !!user
    });

    if (!tenantId) {
      throw new ForbiddenException("Missing client context");
    }

    return this.lotService.listLots(tenantId, user);
  }

  @Get(":id")
  @ApiOperation({ summary: "Get lot by ID" })
  async getLot(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { id?: string; roles?: UserRole[]; tenantId?: string | null },
  ) {
    if (!tenantId) {
      throw new ForbiddenException("Missing client context");
    }

    return this.lotService.getLot(tenantId, id, user);
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update lot" })
  async updateLot(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateLotSchema)) body: z.infer<typeof updateLotSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!tenantId) {
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
      dppMetadata: body.dppMetadata,
      sizeSpecifications: body.sizeSpecifications
    });

    return this.lotService.updateLot(tenantId, id, {
      factoryId,
      suppliers: suppliersPayload,
      styleRef,
      quantityTotal,
      status,
      materialComposition: body.materialComposition as any,
      dyeLot: body.dyeLot,
      certifications: body.certifications as any,
      dppMetadata: body.dppMetadata,
      sizeSpecifications: body.sizeSpecifications as any,
    });
  }

  @Post(":id/supply-chain/advance")
  @ApiOperation({ summary: "Advance to the next supply-chain stage" })
  async advanceSupplyChain(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    if (!tenantId) {
      throw new ForbiddenException("Missing client context");
    }

    this.ensureWriter(user);
    return this.lotService.advanceSupplyChainStage(tenantId, id);
  }

  @Post(":id/approve")
  @ApiOperation({ summary: "Approve lot" })
  async approveLot(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(ApprovalSchema)) approvalDto: ApprovalDto,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    const roles = user?.roles || [];
    const canApprove =
      roles.length === 0 ||
      roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.QUALITY_DIRECTOR].includes(role));

    if (!canApprove) {
      throw new ForbiddenException("User lacks approval permissions");
    }

    const approverId = user?.userId ?? "demo-user";

    await this.lotService.approveLot(tenantId, id, approverId, approvalDto.note);

    return { message: "Lot approved successfully" };
  }

  @Post(":id/reject")
  @ApiOperation({ summary: "Reject lot" })
  async rejectLot(
    @ClientId() tenantId: string,
    @Param("id") id: string,
    @Body(new ZodValidationPipe(RejectSchema)) rejectDto: RejectDto,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    const roles = user?.roles || [];
    const canReject =
      roles.length === 0 ||
      roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.QUALITY_DIRECTOR].includes(role));

    if (!canReject) {
      throw new ForbiddenException("User lacks rejection permissions");
    }

    const approverId = user?.userId ?? "demo-user";

    await this.lotService.rejectLot(tenantId, id, approverId, rejectDto.note);

    return { message: "Lot rejected successfully" };
  }

  @Post(":id/tech-pack")
  @ApiOperation({ summary: "Upload and process tech pack file" })
  @ApiConsumes("multipart/form-data")
  @ApiBody({
    schema: {
      type: "object",
      properties: {
        file: {
          type: "string",
          format: "binary",
        },
      },
    },
  })
  @UseInterceptors(FileInterceptor("file", {
    limits: {
      fileSize: 50 * 1024 * 1024, // 50MB limit
    },
  }))
  async uploadTechPack(
    @ClientId() tenantId: string,
    @Param("id") lotId: string,
    @UploadedFile() file: Express.Multer.File,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.ensureWriter(user);

    if (!file) {
      throw new BadRequestException("No file uploaded");
    }

    // Validate file type
    const allowedMimeTypes = [
      "application/pdf",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "text/csv",
      "image/jpeg",
      "image/png",
      "image/gif",
      "text/plain",
    ];

    if (!allowedMimeTypes.includes(file.mimetype)) {
      throw new BadRequestException("Invalid file type. Please upload PDF, Excel, CSV, or image files");
    }

    try {
      // Upload file to storage
      const fileKey = await this.storageService.uploadFile(
        file.buffer,
        file.originalname,
        file.mimetype,
        tenantId,
        "reports", // Using reports bucket for tech packs
      );

      // Update lot with file key and set status to processing
      await this.lotService.updateLot(tenantId, lotId, {
        techPackFileKey: fileKey,
        techPackStatus: "processing" as any,
        techPackUploadedAt: new Date(),
      } as any);

      // Extract data from tech pack using AI
      const extractionResult = await this.techPackService.extractFromFile(
        file.buffer,
        file.originalname,
        file.mimetype,
      );

      console.log('Tech pack extraction result:', JSON.stringify(extractionResult, null, 2));

      // Update lot with extracted data
      const updateData: any = {
        techPackData: extractionResult.rawExtractedData,
        techPackStatus: "completed",
      };

      console.log('Update data before DPP fields:', JSON.stringify(updateData, null, 2));

      // Update DPP Hub fields if extracted
      if (extractionResult.styleRef) {
        updateData.styleRef = extractionResult.styleRef;
      }
      if (extractionResult.materialComposition) {
        updateData.materialComposition = extractionResult.materialComposition;
      }
      if (extractionResult.dyeLot) {
        updateData.dyeLot = extractionResult.dyeLot;
      }
      if (extractionResult.productionQuantity) {
        updateData.quantityTotal = extractionResult.productionQuantity;
      }
      if (extractionResult.sizeSpecifications) {
        updateData.sizeSpecifications = extractionResult.sizeSpecifications;
      }

      console.log('Final update data to be saved:', JSON.stringify(updateData, null, 2));
      console.log('Calling updateLot with tenantId:', tenantId, 'lotId:', lotId);

      await this.lotService.updateLot(tenantId, lotId, updateData);
      console.log('UpdateLot completed successfully');

      // Return the lot with updated tech pack data
      const updatedLot = await this.lotService.getLot(tenantId, lotId);

      return {
        message: "Tech pack uploaded and processed successfully",
        lot: updatedLot,
        extractedData: extractionResult,
      };
    } catch (error: any) {
      console.error('Tech pack upload error:', error);
      console.error('Error stack:', error.stack);

      // Update lot with failed status
      await this.lotService.updateLot(tenantId, lotId, {
        techPackStatus: "failed" as any,
      } as any);

      throw new BadRequestException(`Failed to process tech pack: ${error.message}`);
    }
  }

  @Get(":id/tech-pack/download")
  @ApiOperation({ summary: "Download tech pack file" })
  async downloadTechPack(
    @ClientId() tenantId: string,
    @Param("id") lotId: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    const lot = await this.lotService.getLot(tenantId, lotId);

    if (!lot.techPackFileKey) {
      throw new BadRequestException("No tech pack file available for this lot");
    }

    const downloadUrl = await this.storageService.getPresignedDownloadUrl(
      lot.techPackFileKey,
      "reports",
    );

    return {
      downloadUrl,
      fileName: lot.techPackFileKey.split("/").pop(),
    };
  }

  @Get(":id/tech-pack")
  @ApiOperation({ summary: "Get tech pack data" })
  async getTechPackData(
    @ClientId() tenantId: string,
    @Param("id") lotId: string,
  ) {
    const lot = await this.lotService.getLot(tenantId, lotId);

    return {
      techPackStatus: lot.techPackStatus,
      techPackUploadedAt: lot.techPackUploadedAt,
      techPackData: lot.techPackData,
      sizeSpecifications: lot.sizeSpecifications,
      hasFile: !!lot.techPackFileKey,
    };
  }
}
