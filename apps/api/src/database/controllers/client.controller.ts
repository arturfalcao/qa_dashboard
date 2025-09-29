import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Put,
  ForbiddenException,
} from "@nestjs/common";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { ClientService } from "../services/client.service";
import { UserService } from "../services/user.service";
import { CurrentUser, ClientId } from "../../common/decorators";
import { z } from "zod";
import {
  UserRole,
  CreateClientUserDto,
  CreateClientUserSchema,
  UpdateClientUserLotsDto,
  UpdateClientUserLotsSchema,
} from "@qa-dashboard/shared";

const createClientSchema = z.object({
  name: z.string().min(1, "Name is required"),
  contactEmail: z.string().email().optional(),
  contactPhone: z.string().optional(),
  address: z.string().optional(),
  country: z.string().optional(),
  notes: z.string().optional(),
  isActive: z.boolean().optional(),
});

const updateClientSchema = createClientSchema.partial();

@ApiTags("clients")
@Controller("clients")
export class ClientController {
  constructor(
    private readonly clientService: ClientService,
    private readonly userService: UserService,
  ) {}

  private assertAdmin(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    if (roles.length > 0 && !roles.includes(UserRole.ADMIN)) {
      throw new ForbiddenException("Admin role required");
    }
  }

  private assertClientAccess(
    tenantId: string,
    user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    if (user?.tenantId && user.tenantId === tenantId) {
      return;
    }

    this.assertAdmin(user);
  }

  @Get()
  @ApiOperation({ summary: "List all clients for current tenant" })
  async listClients(
    @ClientId() tenantId: string,
    @CurrentUser() user?: { tenantId?: string | null }
  ) {
    if (!tenantId) {
      throw new ForbiddenException("No tenant context");
    }
    return this.clientService.findByTenantId(tenantId);
  }

  @Get(":id")
  @ApiOperation({ summary: "Get client by ID" })
  async getClient(
    @Param("id") id: string,
    @CurrentUser() user?: { tenantId?: string | null },
  ) {
    const client = await this.clientService.findById(id);

    // Verify client belongs to user's tenant
    if (user?.tenantId && client.tenantId !== user.tenantId) {
      throw new ForbiddenException("Access denied");
    }

    return client;
  }

  @Post()
  @ApiOperation({ summary: "Create a new client" })
  async createClient(
    @ClientId() tenantId: string,
    @Body(new ZodValidationPipe(createClientSchema)) body: z.infer<typeof createClientSchema>,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    // Only admins or ops managers can create clients
    const roles = user?.roles || [];
    const canCreate = roles.length === 0 || roles.some((role) =>
      [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)
    );

    if (!canCreate) {
      throw new ForbiddenException("Insufficient permissions to create clients");
    }

    if (!tenantId) {
      throw new ForbiddenException("No tenant context");
    }

    return this.clientService.create({ ...body, tenantId });
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update an existing client" })
  async updateClient(
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateClientSchema)) body: z.infer<typeof updateClientSchema>,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    // Verify client belongs to user's tenant
    const client = await this.clientService.findById(id);
    if (user?.tenantId && client.tenantId !== user.tenantId) {
      throw new ForbiddenException("Access denied");
    }

    // Only admins or ops managers can update clients
    const roles = user?.roles || [];
    const canUpdate = roles.some((role) =>
      [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)
    );

    if (!canUpdate) {
      throw new ForbiddenException("Insufficient permissions to update clients");
    }

    return this.clientService.update(id, body);
  }

  @Delete(":id")
  @ApiOperation({ summary: "Delete a client" })
  async deleteClient(
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    // Verify client belongs to user's tenant
    const client = await this.clientService.findById(id);
    if (user?.tenantId && client.tenantId !== user.tenantId) {
      throw new ForbiddenException("Access denied");
    }

    // Only admins can delete clients
    const roles = user?.roles || [];
    const canDelete = roles.includes(UserRole.ADMIN);

    if (!canDelete) {
      throw new ForbiddenException("Only admins can delete clients");
    }

    await this.clientService.delete(id);
    return { message: "Client deleted successfully" };
  }
}
