import { IsEmail, IsString, MinLength, IsOptional, IsUUID } from "class-validator";

export class CreateUserDto {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;

  @IsOptional()
  @IsUUID()
  tenantId?: string;
}