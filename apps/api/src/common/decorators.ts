import { SetMetadata } from "@nestjs/common";
import { createParamDecorator, ExecutionContext } from "@nestjs/common";

export const Public = () => SetMetadata("isPublic", true);

export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);

export const ClientId = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const headerClientId = request.headers?.["x-client-id"] ?? request.headers?.["x-client"];
    const queryClientId = request.query?.clientId ?? request.query?.client_id;

    const resolvedClientId =
      request.clientId ||
      request.user?.clientId ||
      (Array.isArray(headerClientId) ? headerClientId[0] : headerClientId) ||
      (Array.isArray(queryClientId) ? queryClientId[0] : queryClientId) ||
      null;

    console.log('🏢 ClientId Decorator - Debug:', {
      url: request.url,
      requestClientId: request.clientId,
      userClientId: request.user?.clientId,
      headerClientId,
      queryClientId,
      resolvedClientId,
      user: request.user,
      authHeader: request.headers?.authorization?.substring(0, 30) + '...',
      allHeaders: Object.keys(request.headers || {})
    });

    if (!request.clientId && resolvedClientId) {
      request.clientId = resolvedClientId;
    }

    return resolvedClientId;
  },
);

export const CurrentClient = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.clientId || request.user?.clientId || null;
  },
);
