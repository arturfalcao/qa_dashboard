import { Body, Controller, Get, Param, Patch, Post, ForbiddenException } from "@nestjs/common";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { ClientService } from "../services/client.service";
import { CurrentUser } from "../../common/decorators";
import { z } from "zod";
import { UserRole } from "@qa-dashboard/shared";

const createClientSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z
    .string()
    .min(1)
    .regex(/^[a-z0-9-]+$/, "Slug must contain lowercase letters, numbers or dashes"),
  logoUrl: z.string().url().optional(),
});

const updateClientSchema = createClientSchema.partial();

@ApiTags("clients")
@Controller("clients")
export class ClientController {
  constructor(private readonly clientService: ClientService) {}

  private assertAdmin(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    if (roles.length > 0 && !roles.includes(UserRole.ADMIN)) {
      throw new ForbiddenException("Admin role required");
    }
  }

  @Get("me")
  @ApiOperation({ summary: "Retrieve the current client's profile" })
  async getCurrentClient(@CurrentUser() user?: { clientId?: string | null }) {
    if (user?.clientId) {
      return this.clientService.findById(user.clientId);
    }

    const [first] = await this.clientService.findAll();
    if (!first) {
      throw new ForbiddenException("No clients configured in the system");
    }

    return first;
  }

  @Get()
  @ApiOperation({ summary: "List all clients" })
  async listClients(@CurrentUser() user?: { roles?: UserRole[] }) {
    this.assertAdmin(user);
    return this.clientService.findAll();
  }

  @Get(":id")
  @ApiOperation({ summary: "Get client by ID" })
  async getClient(
    @Param("id") id: string,
    @CurrentUser() user?: { roles?: UserRole[]; clientId?: string | null },
  ) {
    if (user.clientId && user.clientId === id) {
      return this.clientService.findById(id);
    }

    this.assertAdmin(user);
    return this.clientService.findById(id);
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
