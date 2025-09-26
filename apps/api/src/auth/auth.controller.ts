import { Controller, Post, Body, HttpCode, HttpStatus } from "@nestjs/common";
import { ApiTags, ApiOperation, ApiResponse } from "@nestjs/swagger";
import { AuthService } from "./auth.service";
import {
  LoginDto,
  RefreshTokenDto,
  AuthResponse,
  LoginSchema,
  RefreshTokenSchema,
} from "@qa-dashboard/shared";
import { ZodValidationPipe } from "../common/zod-validation.pipe";
import { Public } from "../common/decorators";

@ApiTags("auth")
@Controller("auth")
export class AuthController {
  constructor(private authService: AuthService) {}

  @Public()
  @Post("login")
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: "Login user" })
  @ApiResponse({ status: 200, description: "Login successful" })
  @ApiResponse({ status: 401, description: "Invalid credentials" })
  async login(
    @Body(new ZodValidationPipe(LoginSchema)) loginDto: LoginDto,
  ): Promise<AuthResponse> {
    console.log("Auth controller received login request:", loginDto.email);
    return this.authService.login(loginDto);
  }

  @Public()
  @Post("refresh")
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: "Refresh access token" })
  @ApiResponse({ status: 200, description: "Token refreshed successfully" })
  @ApiResponse({ status: 401, description: "Invalid refresh token" })
  async refresh(
    @Body(new ZodValidationPipe(RefreshTokenSchema))
    refreshDto: RefreshTokenDto,
  ): Promise<{ accessToken: string }> {
    return this.authService.refreshToken(refreshDto.refreshToken);
  }

  @Post("logout")
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: "Logout user" })
  @ApiResponse({ status: 200, description: "Logout successful" })
  async logout(): Promise<{ message: string }> {
    return { message: "Logout successful" };
  }
}
