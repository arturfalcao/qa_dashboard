import {
  BadRequestException,
  ConflictException,
  Injectable,
  NotFoundException,
} from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository, In } from "typeorm";
import * as bcrypt from "bcryptjs";
import { randomBytes } from "crypto";

import { UserRole } from "@qa-dashboard/shared";

import { User } from "../entities/user.entity";
import { Role } from "../entities/role.entity";
import { UserRole as UserRoleEntity } from "../entities/user-role.entity";
import { ClientService } from "./client.service";

interface CreateClientUserInput {
  email: string;
  clientSlug: string;
  roles?: UserRole[];
  temporaryPassword?: string;
}

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectRepository(Role)
    private readonly roleRepository: Repository<Role>,
    @InjectRepository(UserRoleEntity)
    private readonly userRoleRepository: Repository<UserRoleEntity>,
    private readonly clientService: ClientService,
  ) {}

  async createClientUser({
    email,
    clientSlug,
    roles = [UserRole.CLIENT_VIEWER],
    temporaryPassword,
  }: CreateClientUserInput) {
    const client = await this.clientService.findBySlug(clientSlug);
    if (!client) {
      throw new NotFoundException(`Client with slug ${clientSlug} not found`);
    }

    const existing = await this.userRepository.findOne({
      where: { email, clientId: client.id },
    });

    if (existing) {
      throw new ConflictException(
        "A user with this email already exists for the client",
      );
    }

    const password = temporaryPassword ?? this.generateTemporaryPassword();
    const passwordHash = await bcrypt.hash(password, 10);

    const user = this.userRepository.create({
      email,
      clientId: client.id,
      passwordHash,
      isActive: true,
    });

    const savedUser = await this.userRepository.save(user);

    const uniqueRoles = Array.from(
      new Set(roles.length ? roles : [UserRole.CLIENT_VIEWER]),
    );

    const roleRecords = await this.roleRepository.find({
      where: { name: In(uniqueRoles) },
    });

    if (roleRecords.length !== uniqueRoles.length) {
      throw new BadRequestException("One or more roles are invalid");
    }

    const userRoles = roleRecords.map((role) =>
      this.userRoleRepository.create({
        userId: savedUser.id,
        roleId: role.id,
        isPrimary: role.name === uniqueRoles[0],
      }),
    );

    await this.userRoleRepository.save(userRoles);

    return {
      id: savedUser.id,
      email: savedUser.email,
      clientId: savedUser.clientId,
      clientSlug: client.slug,
      clientName: client.name,
      roles: uniqueRoles,
      temporaryPassword: password,
      createdAt: savedUser.createdAt.toISOString(),
      updatedAt: savedUser.updatedAt.toISOString(),
    };
  }

  private generateTemporaryPassword(): string {
    const raw = randomBytes(12)
      .toString("base64")
      .replace(/[^a-zA-Z0-9]/g, "");

    const candidate = raw.slice(0, 12);
    if (candidate.length >= 8) {
      return candidate;
    }

    return `${candidate}${randomBytes(4).toString("hex")}`.slice(0, 12);
  }
}
