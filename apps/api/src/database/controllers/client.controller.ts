import {
  Body,
  Controller,
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
import { CurrentUser } from "../../common/decorators";
import { z } from "zod";
import {
  UserRole,
  CreateClientUserDto,
  CreateClientUserSchema,
  UpdateClientUserLotsDto,
  UpdateClientUserLotsSchema,
} from "@qa-dashboard/shared";

const createClientSchema = z.object({
  tenantId: z.string().uuid(),
  name: z.string().min(1, "Name is required"),
  contactEmail: z.string().email().optional(),
  contactPhone: z.string().optional(),
  address: z.string().optional(),
  country: z.string().optional(),
  notes: z.string().optional(),
  isActive: z.boolean().optional(),
});

const updateClientSchema = createClientSchema.partial().omit({ tenantId: true });

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
  async listClients(@CurrentUser() user?: { tenantId?: string | null }) {
    if (!user?.tenantId) {
      throw new ForbiddenException("No tenant context");
    }
    return this.clientService.findByTenantId(user.tenantId);
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
    @Body(new ZodValidationPipe(createClientSchema)) body: z.infer<typeof createClientSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.assertAdmin(user);
    return this.clientService.create(body);
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update an existing client" })
  async updateClient(
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateClientSchema)) body: z.infer<typeof updateClientSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.assertAdmin(user);
    return this.clientService.update(id, body);
  }
}
