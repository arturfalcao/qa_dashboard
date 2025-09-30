import {
  Body,
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Delete,
  ForbiddenException,
  Query,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiQuery } from "@nestjs/swagger";
import { EdgeDeviceService } from "../services/edge-device.service";
import { UserService } from "../services/user.service";
import { TenantService } from "../services/tenant.service";
import { LotService } from "../services/lot.service";
import { InspectionSessionService } from "../services/inspection-session.service";
import { MigratePhotosService } from "../services/migrate-photos.service";
import { CurrentUser } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { randomBytes } from "crypto";

const createDeviceSchema = z.object({
  name: z.string().min(1),
  workbenchNumber: z.number().int().positive(),
  tenantId: z.string().uuid().optional().nullable(),
});

const assignOperatorSchema = z.object({
  operatorId: z.string().uuid(),
});

const createOperatorSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  tenantId: z.string().uuid().optional().nullable(),
});

const updateDeviceStatusSchema = z.object({
  status: z.enum(["active", "inactive", "maintenance"]),
});

const assignLotToDeviceSchema = z.object({
  lotId: z.string().uuid(),
  operatorId: z.string().uuid().optional(),
});

@ApiTags("super-admin")
@Controller("super-admin")
export class SuperAdminController {
  constructor(
    private readonly edgeDeviceService: EdgeDeviceService,
    private readonly userService: UserService,
    private readonly tenantService: TenantService,
    private readonly lotService: LotService,
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly migratePhotosService: MigratePhotosService,
  ) {}

  private ensureSuperAdminAccess(user?: { email?: string }) {
    if (user?.email !== "celso.silva@packpolish.com") {
      throw new ForbiddenException("Super admin access required");
    }
  }

  @Get("tenants")
  @ApiOperation({ summary: "List all tenants" })
  async listTenants(@CurrentUser() user: any) {
    this.ensureSuperAdminAccess(user);

    const tenants = await this.tenantService.findAll();
    return {
      tenants: tenants.map((tenant) => ({
        id: tenant.id,
        name: tenant.name,
        slug: tenant.slug,
        logoUrl: tenant.logoUrl,
        createdAt: tenant.createdAt,
      })),
    };
  }

  @Get("devices")
  @ApiOperation({ summary: "List all Pack & Polish edge devices" })
  async listDevices(@CurrentUser() user: any) {
    this.ensureSuperAdminAccess(user);

    const devices = await this.edgeDeviceService.findAll();

    return {
      devices: devices.map((device) => ({
        id: device.id,
        name: device.name,
        secretKey: device.secretKey,
        workbenchNumber: device.workbenchNumber,
        status: device.status,
        lastSeenAt: device.lastSeenAt,
        tenantId: device.tenantId,
        tenant: device.tenant
          ? {
              id: device.tenant.id,
              name: device.tenant.name,
              slug: device.tenant.slug,
            }
          : null,
        assignedOperatorId: device.assignedOperatorId,
        assignedOperator: device.assignedOperator
          ? {
              id: device.assignedOperator.id,
              email: device.assignedOperator.email,
            }
          : null,
      })),
    };
  }

  @Post("devices")
  @ApiOperation({ summary: "Create new edge device for Pack & Polish (optionally assign to tenant)" })
  async createDevice(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(createDeviceSchema)) body: z.infer<typeof createDeviceSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // If tenantId provided, verify tenant exists
    let tenant = null;
    if (body.tenantId) {
      tenant = await this.tenantService.findById(body.tenantId);
      if (!tenant) {
        throw new ForbiddenException("Tenant not found");
      }
    }

    // Generate secret key: EDGE-{tenantSlug|PACKPOLISH}-{workbenchNumber}-{random}
    const randomSuffix = randomBytes(8).toString("hex");
    const prefix = tenant ? tenant.slug.toUpperCase() : "PACKPOLISH";
    const secretKey = `EDGE-${prefix}-${body.workbenchNumber.toString().padStart(3, "0")}-${randomSuffix}`;

    const device = await this.edgeDeviceService.create({
      tenantId: body.tenantId || null,
      name: body.name,
      secretKey,
      workbenchNumber: body.workbenchNumber,
      status: "active",
    });

    return {
      success: true,
      device: {
        id: device.id,
        secretKey: device.secretKey,
        workbenchNumber: device.workbenchNumber,
        name: device.name,
        tenantId: device.tenantId,
      },
    };
  }

  @Patch("devices/:id/status")
  @ApiOperation({ summary: "Update device status" })
  async updateDeviceStatus(
    @CurrentUser() user: any,
    @Param("id") deviceId: string,
    @Body(new ZodValidationPipe(updateDeviceStatusSchema))
    body: z.infer<typeof updateDeviceStatusSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    await this.edgeDeviceService.updateStatus(deviceId, body.status);

    return {
      success: true,
      message: "Device status updated",
    };
  }

  @Patch("devices/:id/assign")
  @ApiOperation({ summary: "Assign operator to workbench" })
  async assignOperator(
    @CurrentUser() user: any,
    @Param("id") deviceId: string,
    @Body(new ZodValidationPipe(assignOperatorSchema))
    body: z.infer<typeof assignOperatorSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // Verify operator has OPERATOR role
    const operator = await this.userService.findById(body.operatorId);
    if (!operator) {
      throw new ForbiddenException("Operator not found");
    }

    await this.edgeDeviceService.assignOperator(deviceId, body.operatorId);

    return {
      success: true,
      message: "Operator assigned to device",
    };
  }

  @Delete("devices/:id/assign")
  @ApiOperation({ summary: "Unassign operator from workbench" })
  async unassignOperator(@CurrentUser() user: any, @Param("id") deviceId: string) {
    this.ensureSuperAdminAccess(user);

    await this.edgeDeviceService.assignOperator(deviceId, null);

    return {
      success: true,
      message: "Operator unassigned from device",
    };
  }

  @Get("operators")
  @ApiOperation({ summary: "List all Pack & Polish operators" })
  async listOperators(@CurrentUser() user: any) {
    this.ensureSuperAdminAccess(user);

    // Get all operators (both assigned and unassigned to tenants)
    const operators = await this.userService.findByRole("OPERATOR");

    return {
      operators: operators.map((op) => ({
        id: op.id,
        email: op.email,
        tenantId: op.tenantId,
        isActive: op.isActive,
        createdAt: op.createdAt,
      })),
    };
  }

  @Post("operators")
  @ApiOperation({ summary: "Create operator user for Pack & Polish (optionally assign to tenant)" })
  async createOperator(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(createOperatorSchema))
    body: z.infer<typeof createOperatorSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // If tenantId provided, verify tenant exists
    if (body.tenantId) {
      const tenant = await this.tenantService.findById(body.tenantId);
      if (!tenant) {
        throw new ForbiddenException("Tenant not found");
      }
    }

    const operator = await this.userService.createOperator(
      body.tenantId || null,
      body.email,
      body.password,
    );

    return {
      success: true,
      operator: {
        id: operator.id,
        email: operator.email,
        tenantId: operator.tenantId,
      },
    };
  }

  @Get("tenants/:tenantId/lots")
  @ApiOperation({ summary: "List lots for a specific tenant" })
  async listLotsForTenant(
    @CurrentUser() user: any,
    @Param("tenantId") tenantId: string,
  ) {
    this.ensureSuperAdminAccess(user);

    // Verify tenant exists
    const tenant = await this.tenantService.findById(tenantId);
    if (!tenant) {
      throw new ForbiddenException("Tenant not found");
    }

    const lots = await this.lotService.listLots(tenantId, user);

    return {
      tenant: {
        id: tenant.id,
        name: tenant.name,
        slug: tenant.slug,
      },
      lots,
    };
  }

  @Post("devices/:deviceId/assign-lot")
  @ApiOperation({ summary: "Assign a lot to a device and optionally start inspection session" })
  async assignLotToDevice(
    @CurrentUser() user: any,
    @Param("deviceId") deviceId: string,
    @Body(new ZodValidationPipe(assignLotToDeviceSchema))
    body: z.infer<typeof assignLotToDeviceSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // Verify device exists
    const device = await this.edgeDeviceService.findById(deviceId);
    if (!device) {
      throw new ForbiddenException("Device not found");
    }

    // Verify lot exists
    const lot = await this.lotService.findById(body.lotId);
    if (!lot) {
      throw new ForbiddenException("Lot not found");
    }

    // Check for active session on this lot
    const activeSession = await this.inspectionSessionService.findActiveByLotId(body.lotId);
    if (activeSession) {
      throw new ForbiddenException("Lot already has an active inspection session");
    }

    // Determine operator: use provided operatorId, or use device's assigned operator, or use super admin
    let operatorId = body.operatorId;
    if (!operatorId && device.assignedOperatorId) {
      operatorId = device.assignedOperatorId;
    }
    if (!operatorId) {
      operatorId = user.id; // Use super admin as operator
    }

    // Update lot status to INSPECTION
    await this.lotService.updateStatus(body.lotId, "INSPECTION" as any);

    // Create inspection session
    const session = await this.inspectionSessionService.create({
      lotId: body.lotId,
      deviceId: deviceId,
      operatorId: operatorId,
      startedAt: new Date(),
    });

    return {
      success: true,
      message: "Lot assigned to device and inspection session started",
      session: {
        id: session.id,
        lotId: session.lotId,
        deviceId: session.deviceId,
        operatorId: session.operatorId,
        startedAt: session.startedAt,
      },
      lot: {
        id: lot.id,
        styleRef: lot.styleRef,
        status: "INSPECTION",
      },
      device: {
        id: device.id,
        name: device.name,
        workbenchNumber: device.workbenchNumber,
      },
    };
  }

  @Post("migrate-photos")
  @ApiOperation({ summary: "Migrate old photos to new organized structure" })
  async migratePhotos(@CurrentUser() user?: { email?: string }) {
    this.ensureSuperAdminAccess(user);

    const result = await this.migratePhotosService.migratePhotos();

    return {
      success: true,
      message: `Migration complete: ${result.migrated} migrated, ${result.failed} failed`,
      ...result,
    };
  }
}