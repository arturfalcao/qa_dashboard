import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from "@nestjs/common";

@Injectable()
export class ClientGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || !user.tenantId) {
      throw new ForbiddenException("Invalid tenant access");
    }

    const requestedTenantId = request.params.tenantId || request.query.tenantId;
    if (requestedTenantId && requestedTenantId !== user.tenantId) {
      throw new ForbiddenException("Tenant mismatch");
    }

    request.tenantId = user.tenantId;
    return true;
  }
}
