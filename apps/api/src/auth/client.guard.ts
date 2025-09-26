import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from "@nestjs/common";

@Injectable()
export class ClientGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || !user.clientId) {
      throw new ForbiddenException("Invalid client access");
    }

    const requestedClientId = request.params.clientId || request.query.clientId;
    if (requestedClientId && requestedClientId !== user.clientId) {
      throw new ForbiddenException("Client mismatch");
    }

    request.clientId = user.clientId;
    return true;
  }
}
