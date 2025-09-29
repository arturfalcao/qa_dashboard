import {
  ConflictException,
  Injectable,
  NotFoundException,
} from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { User } from "../entities/user.entity";
import { Role } from "../entities/role.entity";
import { UserRole as UserRoleEntity } from "../entities/user-role.entity";
import { Client } from "../entities/client.entity";
import {
  CreateClientUserDto,
  ClientUser,
  UserRole,
} from "@qa-dashboard/shared";

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectRepository(Role)
    private readonly roleRepository: Repository<Role>,
    @InjectRepository(UserRoleEntity)
    private readonly userRoleRepository: Repository<UserRoleEntity>,
    @InjectRepository(Client)
    private readonly clientRepository: Repository<Client>,
  ) {}

  private mapToClientUser(user: User, roles: UserRole[]): ClientUser {
    return {
      id: user.id,
      clientId: user.clientId ?? null,
      email: user.email,
      isActive: user.isActive,
      createdAt: user.createdAt.toISOString(),
      updatedAt: user.updatedAt.toISOString(),
      roles,
    };
  }

  async listForClient(clientId: string): Promise<ClientUser[]> {
    const users = await this.userRepository.find({
      where: { clientId },
      relations: ["userRoles", "userRoles.role"],
      order: { createdAt: "DESC" },
    });

    return users.map((user) => {
      const roles =
        user.userRoles
          ?.map((userRole) => userRole.role?.name)
          .filter((name): name is UserRole =>
            name ? (Object.values(UserRole) as string[]).includes(name) : false,
          ) || [];

      return this.mapToClientUser(user, roles.length ? roles : [UserRole.CLIENT_VIEWER]);
    });
  }

  async createForClient(
    clientId: string,
    payload: CreateClientUserDto,
  ): Promise<ClientUser> {
    const client = await this.clientRepository.findOne({ where: { id: clientId } });
    if (!client) {
      throw new NotFoundException("Client not found");
    }

    const normalizedEmail = payload.email.toLowerCase();

    const existingUser = await this.userRepository.findOne({
      where: { clientId, email: normalizedEmail },
    });

    if (existingUser) {
      throw new ConflictException("A user with this email already exists for the client");
    }

    const passwordHash = await bcrypt.hash(payload.password, 10);

    const user = this.userRepository.create({
      clientId,
      email: normalizedEmail,
      passwordHash,
      isActive: payload.isActive ?? true,
    });

    const savedUser = await this.userRepository.save(user);

    const roles = payload.roles?.length ? payload.roles : [UserRole.CLIENT_VIEWER];

    await Promise.all(
      roles.map(async (roleName, index) => {
        const role = await this.roleRepository.findOne({ where: { name: roleName } });
        if (!role) {
          throw new NotFoundException(`Role ${roleName} not found`);
        }

        await this.userRoleRepository.save(
          this.userRoleRepository.create({
            userId: savedUser.id,
            roleId: role.id,
            isPrimary: index === 0,
          }),
        );
      }),
    );

    const createdUser = await this.userRepository.findOne({
      where: { id: savedUser.id },
      relations: ["userRoles", "userRoles.role"],
    });

    if (!createdUser) {
      throw new NotFoundException("Created user not found");
    }

    const assignedRoles =
      createdUser.userRoles
        ?.map((userRole) => userRole.role?.name)
        .filter((name): name is UserRole =>
          name ? (Object.values(UserRole) as string[]).includes(name) : false,
        ) || [];

    const effectiveRoles = assignedRoles.length
      ? assignedRoles
      : [UserRole.CLIENT_VIEWER];

    return this.mapToClientUser(createdUser, effectiveRoles);
  }
}
