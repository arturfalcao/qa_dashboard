import { Body, Controller, Delete, Get, Param, Patch, Post, ForbiddenException } from "@nestjs/common";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { z } from "zod";
import { ClientId, CurrentUser } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { FactoryService } from "../services/factory.service";
import { UserRole } from "@qa-dashboard/shared";

const capabilitySchema = z.object({
  roleId: z.string().uuid(),
  co2OverrideKg: z.number().nonnegative().optional(),
  notes: z.string().max(250).optional(),
});

const certificationOptions = [
  "GOTS",
  "OEKO_TEX_STANDARD_100",
  "GRS",
  "RCS",
  "ISO_14001",
  "BLUESIGN",
  "AMFORI_BSCI",
] as const;

const certificationSchema = z.object({
  certification: z.enum(certificationOptions),
});

const createFactorySchema = z.object({
  name: z.string().min(1),
  city: z.string().optional(),
  country: z.string().min(2).max(2).default("PT"),
  capabilities: z.array(capabilitySchema).optional(),
  certifications: z.array(certificationSchema).optional(),
});

const updateFactorySchema = createFactorySchema.partial();

@ApiTags("factories")
@Controller("factories")
export class FactoryController {
  constructor(private readonly factoryService: FactoryService) {}

  private ensureWriter(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    if (roles.length === 0) {
      return;
    }

    if (!roles.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))) {
      throw new ForbiddenException("Insufficient permissions");
    }
  }

  @Get()
  @ApiOperation({ summary: "List factories for the current client" })
  async list(@ClientId() tenantId: string) {
    return this.factoryService.listByTenant(tenantId);
  }

  @Post()
  @ApiOperation({ summary: "Create a factory for the current client" })
  async create(
    @ClientId() tenantId: string,
    @CurrentUser() user: { roles?: UserRole[] },
    @Body(new ZodValidationPipe(createFactorySchema)) body: z.infer<typeof createFactorySchema>,
  ) {
    this.ensureWriter(user);
    const { capabilities, certifications, ...factoryData } = body;
    return this.factoryService.create(tenantId, {
      ...factoryData,
      capabilities: capabilities?.map((capability) => ({
        roleId: capability.roleId,
        co2OverrideKg: capability.co2OverrideKg,
        notes: capability.notes,
      })),
      certifications: certifications?.map((certification) => ({
        certification: certification.certification,
      })),
    });
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update a factory" })
  async update(
    @ClientId() tenantId: string,
    @CurrentUser() user: { roles?: UserRole[] },
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateFactorySchema)) body: z.infer<typeof updateFactorySchema>,
  ) {
    this.ensureWriter(user);
    const { capabilities, certifications, ...factoryData } = body;
    return this.factoryService.update(tenantId, id, {
      ...factoryData,
      capabilities: capabilities?.map((capability) => ({
        roleId: capability.roleId,
        co2OverrideKg: capability.co2OverrideKg,
        notes: capability.notes,
      })),
      certifications: certifications?.map((certification) => ({
        certification: certification.certification,
      })),
    });
  }

  @Delete(":id")
  @ApiOperation({ summary: "Delete a factory" })
  async delete(
    @ClientId() tenantId: string,
    @CurrentUser() user: { roles?: UserRole[] },
    @Param("id") id: string,
  ) {
    // Only admins can delete factories
    const roles = user?.roles || [];
    const canDelete = roles.includes(UserRole.ADMIN);

    if (!canDelete) {
      throw new ForbiddenException("Only admins can delete factories");
    }

    await this.factoryService.delete(tenantId, id);
    return { message: "Factory deleted successfully" };
  }
}
