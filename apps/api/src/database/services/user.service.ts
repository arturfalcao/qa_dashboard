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

import { User } from "../entities/user.entity";
import { Role } from "../entities/role.entity";
import { UserRole as UserRoleEntity } from "../entities/user-role.entity";
import { Client } from "../entities/client.entity";
import { Lot } from "../entities/lot.entity";
import { LotUserAssignment } from "../entities/lot-user-assignment.entity";
import {
  CreateClientUserDto,
  ClientUser,
  UserRole,
  UpdateClientUserLotsDto,
} from "@qa-dashboard/shared";

interface CreateClientUserInput {
  email: string;
  clientSlug?: string;
  clientId?: string;
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
    @InjectRepository(Client)
    private readonly clientRepository: Repository<Client>,
    @InjectRepository(Lot)
    private readonly lotRepository: Repository<Lot>,
    @InjectRepository(LotUserAssignment)
    private readonly lotUserAssignmentRepository: Repository<LotUserAssignment>,
  ) {}

  private resolveRoles(user: User): UserRole[] {
    const assignedRoles =
      user.userRoles
        ?.map((userRole) => userRole.role?.name)
        .filter((name): name is UserRole =>
          name ? (Object.values(UserRole) as string[]).includes(name) : false,
        ) || [];

    return assignedRoles.length ? assignedRoles : [UserRole.CLIENT_VIEWER];
  }

  private mapToClientUser(user: User): ClientUser {
    const roles = this.resolveRoles(user);

    return {
      id: user.id,
      clientId: user.clientId ?? null,
      email: user.email,
      isActive: user.isActive,
      createdAt: user.createdAt.toISOString(),
      updatedAt: user.updatedAt.toISOString(),
      roles,
      assignedLotIds:
        user.assignments?.map((assignment) => assignment.lotId) ?? [],
    };
  }

  async listForClient(clientId: string): Promise<ClientUser[]> {
    const users = await this.userRepository.find({
      where: { clientId },
      relations: ["userRoles", "userRoles.role", "assignments"],
      order: { createdAt: "DESC" },
    });

    return users.map((user) => this.mapToClientUser(user));
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
    const uniqueRoles = Array.from(new Set(roles));

    const roleRecords = await this.roleRepository.find({
      where: { name: In(uniqueRoles) },
    });

    if (roleRecords.length !== uniqueRoles.length) {
      throw new BadRequestException("One or more roles are invalid");
    }

    await Promise.all(
      roleRecords.map(async (role, index) => {
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
      relations: ["userRoles", "userRoles.role", "assignments"],
    });

    if (!createdUser) {
      throw new NotFoundException("Created user not found");
    }

    return this.mapToClientUser(createdUser);
  }

  async createClientUser({
    email,
    clientSlug,
    clientId,
    roles = [UserRole.CLIENT_VIEWER],
    temporaryPassword,
  }: CreateClientUserInput) {
    if (!clientSlug && !clientId) {
      throw new BadRequestException("Either clientSlug or clientId must be provided");
    }

    const client = await this.clientRepository.findOne({
      where: clientId ? { id: clientId } : { slug: clientSlug },
    });
    if (!client) {
      throw new NotFoundException(
        `Client with ${clientId ? `id ${clientId}` : `slug ${clientSlug}`} not found`,
      );
    }

    const normalizedEmail = email.toLowerCase();

    const existing = await this.userRepository.findOne({
      where: { email: normalizedEmail, clientId: client.id }, 
    });

    if (existing) {
      throw new ConflictException(
        "A user with this email already exists for the client",
      );
    }

    const password = temporaryPassword ?? randomBytes(16).toString("hex");
    const passwordHash = await bcrypt.hash(password, 10);

    const user = this.userRepository.create({
      email: normalizedEmail,
      clientId: client.id,
      passwordHash,
      isActive: true,
    });

    const savedUser = await this.userRepository.save(user);

    const uniqueRoles = Array.from(new Set(roles.length ? roles : [UserRole.CLIENT_VIEWER]));

    const roleRecords = await this.roleRepository.find({
      where: { name: In(uniqueRoles) },
    });

    if (roleRecords.length !== uniqueRoles.length) {
      throw new BadRequestException("One or more roles are invalid");
    }

    const userRoles = roleRecords.map((role, index) =>
      this.userRoleRepository.create({
        userId: savedUser.id,
        roleId: role.id,
        isPrimary: index === 0,
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

  async updateAssignedLots(
    clientId: string,
    userId: string,
    payload: UpdateClientUserLotsDto,
  ): Promise<ClientUser> {
    const user = await this.userRepository.findOne({
      where: { id: userId, clientId },
    });

    if (!user) {
      throw new NotFoundException("User not found");
    }

    const lotIds = payload.lotIds ?? [];
    const uniqueLotIds = Array.from(new Set(lotIds));

    if (uniqueLotIds.length) {
      const lots = await this.lotRepository.find({
        where: { clientId, id: In(uniqueLotIds) },
        select: ["id"],
      });

      if (lots.length !== uniqueLotIds.length) {
        throw new BadRequestException("One or more lots do not belong to this client");
      }
    }

    await this.lotUserAssignmentRepository.delete({ userId });

    if (uniqueLotIds.length) {
      const assignments = uniqueLotIds.map((lotId) =>
        this.lotUserAssignmentRepository.create({ lotId, userId }),
      );
      await this.lotUserAssignmentRepository.save(assignments);
    }

    const refreshedUser = await this.userRepository.findOne({
      where: { id: userId },
      relations: ["userRoles", "userRoles.role", "assignments"],
    });

    if (!refreshedUser) {
      throw new NotFoundException("User not found after updating assignments");
    }

    return this.mapToClientUser(refreshedUser);
  }
}