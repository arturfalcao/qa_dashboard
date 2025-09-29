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
import { TenantService } from "../services/tenant.service";
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

const createTenantSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z
    .string()
    .min(1)
    .regex(/^[a-z0-9-]+$/, "Slug must contain lowercase letters, numbers or dashes"),
  logoUrl: z.string().url().optional(),
});

const updateTenantSchema = createTenantSchema.partial();

@ApiTags("tenants")
@Controller("tenants")
export class TenantController {
  constructor(
    private readonly tenantService: TenantService,
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

  @Get("me")
  @ApiOperation({ summary: "Retrieve the current tenant's profile" })
  async getCurrentTenant(@CurrentUser() user?: { tenantId?: string | null }) {
    if (user?.tenantId) {
      return this.tenantService.findById(user.tenantId);
    }

    const [first] = await this.tenantService.findAll();
    if (!first) {
      throw new ForbiddenException("No tenants configured in the system");
    }

    return first;
  }

  @Get()
  @ApiOperation({ summary: "List all tenants" })
  async listTenants(@CurrentUser() user?: { roles?: UserRole[] }) {
    this.assertAdmin(user);
    return this.tenantService.findAll();
  }

  @Get(":id")
  @ApiOperation({ summary: "Get tenant by ID" })
  async getTenant(
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    if (user.tenantId && user.tenantId === id) {
      return this.tenantService.findById(id);
    }

    this.assertAdmin(user);
    return this.tenantService.findById(id);
  }

  @Get(":id/users")
  @ApiOperation({ summary: "List tenant users" })
  async listTenantUsers(
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    this.assertClientAccess(id, user);
    return this.userService.listForTenant(id);
  }

  @Post(":id/users")
  @ApiOperation({ summary: "Create a new tenant user" })
  async createTenantUser(
    @Param("id") id: string,
    @Body(new ZodValidationPipe(CreateClientUserSchema)) body: CreateClientUserDto,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    this.assertClientAccess(id, user);
    return this.userService.createForTenant(id, body);
  }

  @Put(":id/users/:userId/lots")
  @ApiOperation({ summary: "Update which lots a client user can access" })
  async updateClientUserLots(
    @Param("id") id: string,
    @Param("userId") userId: string,
    @Body(new ZodValidationPipe(UpdateClientUserLotsSchema)) body: UpdateClientUserLotsDto,
    @CurrentUser() user?: { roles?: UserRole[]; tenantId?: string | null },
  ) {
    this.assertClientAccess(id, user);
    return this.userService.updateAssignedLots(id, userId, body);
  }

  @Post()
  @ApiOperation({ summary: "Create a new tenant" })
  async createTenant(
    @Body(new ZodValidationPipe(createTenantSchema)) body: z.infer<typeof createTenantSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.assertAdmin(user);
    return this.tenantService.create(body);
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update an existing tenant" })
  async updateTenant(
    @Param("id") id: string,
    @Body(new ZodValidationPipe(updateTenantSchema)) body: z.infer<typeof updateTenantSchema>,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.assertAdmin(user);
    return this.tenantService.update(id, body);
  }
}
