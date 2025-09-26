import { Injectable, UnauthorizedException } from "@nestjs/common";
import { JwtService } from "@nestjs/jwt";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { User } from "../database/entities/user.entity";
import { LoginDto, AuthResponse, UserRole } from "@qa-dashboard/shared";

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
    private jwtService: JwtService,
  ) {}

  async validateUser(email: string, password: string): Promise<User | null> {
    console.log(`Attempting to validate user: ${email}`);

    const user = await this.userRepository.findOne({
      where: { email, isActive: true },
      relations: ["client", "userRoles", "userRoles.role"],
    });

    console.log(`User found:`, user ? `${user.email} (${user.id})` : "null");

    if (user && (await bcrypt.compare(password, user.passwordHash))) {
      console.log(`Password comparison successful for ${email}`);
      return user;
    }

    console.log(`Authentication failed for ${email}`);
    return null;
  }

  async login(loginDto: LoginDto): Promise<AuthResponse> {
    const user = await this.validateUser(loginDto.email, loginDto.password);
    if (!user) {
      throw new UnauthorizedException("Invalid credentials");
    }

    const assignedRoles =
      user.userRoles
        ?.map((userRole) => userRole.role?.name)
        .filter((name): name is string => Boolean(name)) || [];

    const roles = assignedRoles
      .map((name) => name as UserRole)
      .filter((name) => Object.values(UserRole).includes(name)) as UserRole[];
    const effectiveRoles = roles.length ? roles : [UserRole.CLIENT_VIEWER];
    const payload = {
      sub: user.id,
      email: user.email,
      clientId: user.clientId,
      roles: effectiveRoles,
    };

    console.log('🔐 Auth Service - Generating JWT with payload:', JSON.stringify(payload, null, 2));

    const accessToken = this.jwtService.sign(payload);
    const refreshToken = this.jwtService.sign(payload, {
      secret: process.env.JWT_REFRESH_SECRET || "your-jwt-refresh-secret",
      expiresIn: "7d",
    });

    console.log('🔐 Auth Service - Generated tokens:', {
      accessToken: accessToken.substring(0, 50) + '...',
      refreshToken: refreshToken.substring(0, 50) + '...'
    });

    return {
      accessToken,
      refreshToken,
      user: {
        id: user.id,
        clientId: user.clientId || null,
        email: user.email,
        roles: effectiveRoles,
        isActive: user.isActive,
        createdAt: user.createdAt.toISOString(),
        updatedAt: user.updatedAt.toISOString(),
      },
    };
  }

  async refreshToken(refreshToken: string): Promise<{ accessToken: string }> {
    try {
      const payload = this.jwtService.verify(refreshToken, {
        secret: process.env.JWT_REFRESH_SECRET || "your-jwt-refresh-secret",
      });

      const user = await this.userRepository.findOne({
        where: { id: payload.sub, isActive: true },
        relations: ["userRoles", "userRoles.role"],
      });

      if (!user) {
        throw new UnauthorizedException("User not found");
      }

      const assignedRoles =
        user.userRoles
          ?.map((userRole) => userRole.role?.name)
          .filter((name): name is string => Boolean(name)) || [];
      const roles = assignedRoles
        .map((name) => name as UserRole)
        .filter((name) => Object.values(UserRole).includes(name)) as UserRole[];
      const effectiveRoles = roles.length ? roles : [UserRole.CLIENT_VIEWER];
      const newPayload = {
        sub: user.id,
        email: user.email,
        clientId: user.clientId,
        roles: effectiveRoles,
      };

      return {
        accessToken: this.jwtService.sign(newPayload),
      };
    } catch (error) {
      throw new UnauthorizedException("Invalid refresh token");
    }
  }
}
