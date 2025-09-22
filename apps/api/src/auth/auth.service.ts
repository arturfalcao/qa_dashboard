import { Injectable, UnauthorizedException } from "@nestjs/common";
import { JwtService } from "@nestjs/jwt";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { User } from "../database/entities/user.entity";
import { Tenant } from "../database/entities/tenant.entity";
import { LoginDto, AuthResponse } from "@qa-dashboard/shared";

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
    @InjectRepository(Tenant)
    private tenantRepository: Repository<Tenant>,
    private jwtService: JwtService,
  ) {}

  async validateUser(email: string, password: string): Promise<User | null> {
    console.log(`Attempting to validate user: ${email}`);

    const user = await this.userRepository.findOne({
      where: { email, isActive: true },
      relations: ["tenant"],
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

    const payload = {
      sub: user.id,
      email: user.email,
      tenantId: user.tenantId,
      role: user.role,
    };

    const accessToken = this.jwtService.sign(payload);
    const refreshToken = this.jwtService.sign(payload, {
      secret: process.env.JWT_REFRESH_SECRET || "your-jwt-refresh-secret",
      expiresIn: "7d",
    });

    return {
      accessToken,
      refreshToken,
      user: {
        id: user.id,
        tenantId: user.tenantId,
        email: user.email,
        role: user.role,
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
      });

      if (!user) {
        throw new UnauthorizedException("User not found");
      }

      const newPayload = {
        sub: user.id,
        email: user.email,
        tenantId: user.tenantId,
        role: user.role,
      };

      return {
        accessToken: this.jwtService.sign(newPayload),
      };
    } catch (error) {
      throw new UnauthorizedException("Invalid refresh token");
    }
  }
}
