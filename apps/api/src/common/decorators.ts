import { SetMetadata } from "@nestjs/common";
import { createParamDecorator, ExecutionContext } from "@nestjs/common";

export const Public = () => SetMetadata("isPublic", true);

export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);

export const TenantId = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const headerTenantId = request.headers?.["x-tenant-id"] ?? request.headers?.["x-tenant"];
    const queryTenantId = request.query?.tenantId ?? request.query?.tenant_id;

    const resolvedTenantId =
      request.tenantId ||
      request.user?.tenantId ||
      (Array.isArray(headerTenantId) ? headerTenantId[0] : headerTenantId) ||
      (Array.isArray(queryTenantId) ? queryTenantId[0] : queryTenantId) ||
      null;

    console.log('🏢 TenantId Decorator - Debug:', {
      url: request.url,
      requestTenantId: request.tenantId,
      userTenantId: request.user?.tenantId,
      headerTenantId,
      queryTenantId,
      resolvedTenantId,
      user: request.user,
      authHeader: request.headers?.authorization?.substring(0, 30) + '...',
      allHeaders: Object.keys(request.headers || {})
    });

    if (!request.tenantId && resolvedTenantId) {
      request.tenantId = resolvedTenantId;
    }

    return resolvedTenantId;
  },
);

export const CurrentTenant = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.tenantId || request.user?.tenantId || null;
  },
);

// Backward compatibility alias
export const ClientId = TenantId;
