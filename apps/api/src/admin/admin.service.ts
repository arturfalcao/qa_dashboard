import {
  Injectable,
  NotFoundException,
  ConflictException,
  BadRequestException,
} from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { User } from "../database/entities/user.entity";
import { Role } from "../database/entities/role.entity";
import { UserRole } from "../database/entities/user-role.entity";
import { CreateUserDto } from "./dto/create-user.dto";
import { UpdateUserDto } from "./dto/update-user.dto";
import { CreateRoleDto } from "./dto/create-role.dto";
import { UpdateRoleDto } from "./dto/update-role.dto";
import { AssignRoleDto } from "./dto/assign-role.dto";

@Injectable()
export class AdminService {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
    @InjectRepository(Role)
    private roleRepository: Repository<Role>,
    @InjectRepository(UserRole)
    private userRoleRepository: Repository<UserRole>,
  ) {}

  async createUser(createUserDto: CreateUserDto): Promise<User> {
    const existingUser = await this.userRepository.findOne({
      where: {
        email: createUserDto.email,
        clientId: createUserDto.clientId || null,
      },
    });

    if (existingUser) {
      throw new ConflictException(
        "User with this email already exists for this client",
      );
    }

    const passwordHash = await bcrypt.hash(createUserDto.password, 10);

    const user = this.userRepository.create({
      email: createUserDto.email,
      passwordHash,
      clientId: createUserDto.clientId,
      isActive: true,
    });

    return this.userRepository.save(user);
  }

  async getUsers(): Promise<User[]> {
    return this.userRepository.find({
      relations: ["client", "userRoles", "userRoles.role"],
      order: { createdAt: "DESC" },
    });
  }

  async getUser(id: string): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id },
      relations: ["client", "userRoles", "userRoles.role"],
    });

    if (!user) {
      throw new NotFoundException("User not found");
    }

    return user;
  }

  async updateUser(id: string, updateUserDto: UpdateUserDto): Promise<User> {
    const user = await this.getUser(id);

    if (updateUserDto.email) {
      const existingUser = await this.userRepository.findOne({
        where: {
          email: updateUserDto.email,
          clientId: updateUserDto.clientId || user.clientId || null,
        },
      });

      if (existingUser && existingUser.id !== id) {
        throw new ConflictException(
          "User with this email already exists for this client",
        );
      }
      user.email = updateUserDto.email;
    }

    if (updateUserDto.password) {
      user.passwordHash = await bcrypt.hash(updateUserDto.password, 10);
    }

    if (updateUserDto.isActive !== undefined) {
      user.isActive = updateUserDto.isActive;
    }

    if (updateUserDto.clientId !== undefined) {
      user.clientId = updateUserDto.clientId;
    }

    return this.userRepository.save(user);
  }

  async deleteUser(id: string): Promise<void> {
    const user = await this.getUser(id);
    await this.userRepository.remove(user);
  }

  async assignRole(userId: string, assignRoleDto: AssignRoleDto): Promise<UserRole> {
    const user = await this.getUser(userId);
    const role = await this.roleRepository.findOne({
      where: { id: assignRoleDto.roleId },
    });

    if (!role) {
      throw new NotFoundException("Role not found");
    }

    const existingUserRole = await this.userRoleRepository.findOne({
      where: { userId, roleId: assignRoleDto.roleId },
    });

    if (existingUserRole) {
      throw new ConflictException("User already has this role");
    }

    const userRole = this.userRoleRepository.create({
      userId,
      roleId: assignRoleDto.roleId,
      isPrimary: assignRoleDto.isPrimary || false,
    });

    return this.userRoleRepository.save(userRole);
  }

  async removeRole(userId: string, roleId: string): Promise<void> {
    const userRole = await this.userRoleRepository.findOne({
      where: { userId, roleId },
    });

    if (!userRole) {
      throw new NotFoundException("User does not have this role");
    }

    await this.userRoleRepository.remove(userRole);
  }

  async createRole(createRoleDto: CreateRoleDto): Promise<Role> {
    const existingRole = await this.roleRepository.findOne({
      where: { name: createRoleDto.name },
    });

    if (existingRole) {
      throw new ConflictException("Role with this name already exists");
    }

    const role = this.roleRepository.create(createRoleDto);
    return this.roleRepository.save(role);
  }

  async getRoles(): Promise<Role[]> {
    return this.roleRepository.find({
      order: { name: "ASC" },
    });
  }

  async getRole(id: string): Promise<Role> {
    const role = await this.roleRepository.findOne({
      where: { id },
      relations: ["userRoles", "userRoles.user"],
    });

    if (!role) {
      throw new NotFoundException("Role not found");
    }

    return role;
  }

  async updateRole(id: string, updateRoleDto: UpdateRoleDto): Promise<Role> {
    const role = await this.getRole(id);

    if (updateRoleDto.name) {
      const existingRole = await this.roleRepository.findOne({
        where: { name: updateRoleDto.name },
      });

      if (existingRole && existingRole.id !== id) {
        throw new ConflictException("Role with this name already exists");
      }
      role.name = updateRoleDto.name;
    }

    if (updateRoleDto.description !== undefined) {
      role.description = updateRoleDto.description;
    }

    return this.roleRepository.save(role);
  }

  async deleteRole(id: string): Promise<void> {
    const role = await this.getRole(id);
    await this.roleRepository.remove(role);
  }
}