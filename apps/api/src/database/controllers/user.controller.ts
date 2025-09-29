import { Body, Controller, ForbiddenException, Post } from "@nestjs/common";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { z } from "zod";

import { UserRole } from "@qa-dashboard/shared";

import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import { CurrentUser } from "../../common/decorators";
import { UserService } from "../services/user.service";

const createClientUserSchema = z
  .object({
    email: z.string().email(),
    clientSlug: z.string().min(1).optional(),
    tenantId: z.string().uuid().optional(),
    roles: z
      .array(z.nativeEnum(UserRole))
      .min(1)
      .default([UserRole.CLIENT_VIEWER]),
    temporaryPassword: z.string().min(8).max(64).optional(),
  })
  .superRefine((value, ctx) => {
    if (!value.clientSlug && !value.tenantId) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Either clientSlug or tenantId must be provided",
        path: ["clientSlug"],
      });
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Either clientSlug or tenantId must be provided",
        path: ["tenantId"],
      });
    }
  });

type CreateClientUserDto = z.infer<typeof createClientUserSchema>;

@ApiTags("client-users")
@Controller("client-users")
export class UserController {
  constructor(private readonly userService: UserService) {}

  private assertAdmin(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    if (roles.length > 0 && !roles.includes(UserRole.ADMIN)) {
      throw new ForbiddenException(
        "Admin role required to manage client users",
      );
    }
  }

  @Post()
  @ApiOperation({ summary: "Create a new user for a client" })
  async createClientUser(
    @Body(new ZodValidationPipe(createClientUserSchema))
    body: CreateClientUserDto,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.assertAdmin(user);

    return this.userService.createClientUser({
      email: body.email,
      clientSlug: body.clientSlug,
      tenantId: body.tenantId,
      roles: body.roles,
      temporaryPassword: body.temporaryPassword,
    });
  }
}
