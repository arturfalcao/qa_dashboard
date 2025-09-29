import { SetMetadata } from "@nestjs/common";
import { UserRole } from "@qa-dashboard/shared";

export const ROLES_KEY = "roles";
export const Roles = (...roles: UserRole[]) => SetMetadata(ROLES_KEY, roles);