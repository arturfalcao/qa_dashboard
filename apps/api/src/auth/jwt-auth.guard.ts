import { Injectable, ExecutionContext, UnauthorizedException } from "@nestjs/common";
import { AuthGuard } from "@nestjs/passport";
import { Reflector } from "@nestjs/core";

@Injectable()
export class JwtAuthGuard extends AuthGuard("jwt") {
  constructor(private reflector: Reflector) {
    super();
  }

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const isPublic = this.reflector.getAllAndOverride<boolean>("isPublic", [
      context.getHandler(),
      context.getClass(),
    ]);

    console.log('🔐 JWT Auth Guard - Debug:', {
      url: request.url,
      method: request.method,
      isPublic,
      hasAuthHeader: !!request.headers?.authorization,
      authHeaderPrefix: request.headers?.authorization?.substring(0, 20) + '...'
    });

    if (isPublic) {
      console.log('🔐 JWT Auth Guard - Route is public, allowing access');
      return true;
    }

    console.log('🔐 JWT Auth Guard - Route requires authentication, checking JWT token');

    try {
      const result = await super.canActivate(context);
      console.log('🔐 JWT Auth Guard - JWT validation result:', result);
      return result as boolean;
    } catch (error) {
      console.log('🔐 JWT Auth Guard - JWT validation error:', error.message);
      throw error;
    }
  }

  handleRequest<TUser = any>(
    err: any,
    user: TUser,
    info: any,
    context: ExecutionContext,
    status?: any,
  ): TUser {
    if (err || !user) {
      throw err || new UnauthorizedException();
    }

    return user;
  }
}
