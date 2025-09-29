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
import { CurrentUser } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { z } from "zod";
import { randomBytes } from "crypto";

const createDeviceSchema = z.object({
  tenantId: z.string().uuid(),
  name: z.string().min(1),
  workbenchNumber: z.number().int().positive(),
});

const assignOperatorSchema = z.object({
  operatorId: z.string().uuid(),
});

const createOperatorSchema = z.object({
  tenantId: z.string().uuid(),
  email: z.string().email(),
  password: z.string().min(8),
});

const updateDeviceStatusSchema = z.object({
  status: z.enum(["active", "inactive", "maintenance"]),
});

@ApiTags("super-admin")
@Controller("super-admin")
export class SuperAdminController {
  constructor(
    private readonly edgeDeviceService: EdgeDeviceService,
    private readonly userService: UserService,
    private readonly tenantService: TenantService,
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
  @ApiOperation({ summary: "List all edge devices" })
  @ApiQuery({ name: "tenantId", required: false })
  async listDevices(@CurrentUser() user: any, @Query("tenantId") tenantId?: string) {
    this.ensureSuperAdminAccess(user);

    const devices = tenantId
      ? await this.edgeDeviceService.findByTenantId(tenantId)
      : await this.edgeDeviceService.findAll();

    return {
      devices: devices.map((device) => ({
        id: device.id,
        tenantId: device.tenantId,
        name: device.name,
        secretKey: device.secretKey,
        workbenchNumber: device.workbenchNumber,
        status: device.status,
        lastSeenAt: device.lastSeenAt,
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
  @ApiOperation({ summary: "Create new edge device" })
  async createDevice(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(createDeviceSchema)) body: z.infer<typeof createDeviceSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // Verify tenant exists
    const tenant = await this.tenantService.findById(body.tenantId);
    if (!tenant) {
      throw new ForbiddenException("Tenant not found");
    }

    // Generate secret key: EDGE-{tenantSlug}-{workbenchNumber}-{random}
    const randomSuffix = randomBytes(8).toString("hex");
    const secretKey = `EDGE-${tenant.slug}-${body.workbenchNumber.toString().padStart(3, "0")}-${randomSuffix}`;

    const device = await this.edgeDeviceService.create({
      tenantId: body.tenantId,
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
  @ApiOperation({ summary: "List all operators" })
  @ApiQuery({ name: "tenantId", required: false })
  async listOperators(@CurrentUser() user: any, @Query("tenantId") tenantId?: string) {
    this.ensureSuperAdminAccess(user);

    const operators = await this.userService.findByRole("OPERATOR", tenantId);

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
  @ApiOperation({ summary: "Create operator user" })
  async createOperator(
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(createOperatorSchema))
    body: z.infer<typeof createOperatorSchema>,
  ) {
    this.ensureSuperAdminAccess(user);

    // Verify tenant exists
    const tenant = await this.tenantService.findById(body.tenantId);
    if (!tenant) {
      throw new ForbiddenException("Tenant not found");
    }

    const operator = await this.userService.createOperator(
      body.tenantId,
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
}