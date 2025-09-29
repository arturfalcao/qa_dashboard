import { Injectable } from "@nestjs/common";
import { PassportStrategy } from "@nestjs/passport";
import { ExtractJwt, Strategy } from "passport-jwt";

export interface JwtPayload {
  sub: string;
  email: string;
  tenantId?: string;
  roles: string[];
  iat?: number;
  exp?: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    console.log('🔐 JWT Strategy Constructor - Using JWT_SECRET:', process.env.JWT_SECRET);
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: process.env.JWT_SECRET || "your-jwt-secret",
    });
  }

  async validate(payload: JwtPayload) {
    console.log('🔐 JWT Strategy - Validating payload:', JSON.stringify(payload, null, 2));

    const user = {
      userId: payload.sub,
      email: payload.email,
      tenantId: payload.tenantId,
      roles: payload.roles,
    };

    console.log('🔐 JWT Strategy - Returning user:', JSON.stringify(user, null, 2));
    return user;
  }
}
