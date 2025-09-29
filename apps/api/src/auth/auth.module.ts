import { Module } from "@nestjs/common";
import { JwtModule } from "@nestjs/jwt";
import { PassportModule } from "@nestjs/passport";
import { TypeOrmModule } from "@nestjs/typeorm";

import { AuthService } from "./auth.service";
import { AuthController } from "./auth.controller";
import { JwtStrategy } from "./jwt.strategy";
import { JwtAuthGuard } from "./jwt-auth.guard";
import { ClientGuard } from "./client.guard";

import { User } from "../database/entities/user.entity";
import { Tenant } from "../database/entities/tenant.entity";

@Module({
  imports: [
    TypeOrmModule.forFeature([User, Tenant]),
    PassportModule,
    JwtModule.registerAsync({
      useFactory: () => {
        const secret = process.env.JWT_SECRET || "your-jwt-secret";
        console.log('🔐 JWT Module - Using JWT_SECRET for signing:', secret);
        return {
          secret: secret,
          signOptions: { expiresIn: "15m" },
        };
      },
    }),
  ],
  providers: [AuthService, JwtStrategy, JwtAuthGuard, ClientGuard],
  controllers: [AuthController],
  exports: [AuthService, JwtAuthGuard, ClientGuard],
})
export class AuthModule {}
