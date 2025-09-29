import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  UseGuards,
} from "@nestjs/common";
import { UserRole } from "@qa-dashboard/shared";

import { AdminService } from "./admin.service";
import { JwtAuthGuard } from "../auth/jwt-auth.guard";
import { RolesGuard } from "../auth/roles.guard";
import { Roles } from "../auth/roles.decorator";
import { CreateUserDto } from "./dto/create-user.dto";
import { UpdateUserDto } from "./dto/update-user.dto";
import { CreateRoleDto } from "./dto/create-role.dto";
import { UpdateRoleDto } from "./dto/update-role.dto";
import { AssignRoleDto } from "./dto/assign-role.dto";

@Controller("admin")
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles(UserRole.ADMIN)
export class AdminController {
  constructor(private readonly adminService: AdminService) {}

  @Post("users")
  createUser(@Body() createUserDto: CreateUserDto) {
    return this.adminService.createUser(createUserDto);
  }

  @Get("users")
  getUsers() {
    return this.adminService.getUsers();
  }

  @Get("users/:id")
  getUser(@Param("id") id: string) {
    return this.adminService.getUser(id);
  }

  @Put("users/:id")
  updateUser(@Param("id") id: string, @Body() updateUserDto: UpdateUserDto) {
    return this.adminService.updateUser(id, updateUserDto);
  }

  @Delete("users/:id")
  deleteUser(@Param("id") id: string) {
    return this.adminService.deleteUser(id);
  }

  @Post("users/:id/roles")
  assignRole(@Param("id") userId: string, @Body() assignRoleDto: AssignRoleDto) {
    return this.adminService.assignRole(userId, assignRoleDto);
  }

  @Delete("users/:userId/roles/:roleId")
  removeRole(@Param("userId") userId: string, @Param("roleId") roleId: string) {
    return this.adminService.removeRole(userId, roleId);
  }

  @Post("roles")
  createRole(@Body() createRoleDto: CreateRoleDto) {
    return this.adminService.createRole(createRoleDto);
  }

  @Get("roles")
  getRoles() {
    return this.adminService.getRoles();
  }

  @Get("roles/:id")
  getRole(@Param("id") id: string) {
    return this.adminService.getRole(id);
  }

  @Put("roles/:id")
  updateRole(@Param("id") id: string, @Body() updateRoleDto: UpdateRoleDto) {
    return this.adminService.updateRole(id, updateRoleDto);
  }

  @Delete("roles/:id")
  deleteRole(@Param("id") id: string) {
    return this.adminService.deleteRole(id);
  }
}