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
import { Tenant } from "../entities/tenant.entity";
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
  tenantId?: string;
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
    @InjectRepository(Tenant)
    private readonly clientRepository: Repository<Tenant>,
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
      tenantId: user.tenantId ?? null,
      email: user.email,
      isActive: user.isActive,
      createdAt: user.createdAt.toISOString(),
      updatedAt: user.updatedAt.toISOString(),
      roles,
      assignedLotIds:
        user.assignments?.map((assignment) => assignment.lotId) ?? [],
    };
  }

  async listForTenant(tenantId: string): Promise<ClientUser[]> {
    const users = await this.userRepository.find({
      where: { tenantId },
      relations: ["userRoles", "userRoles.role", "assignments"],
      order: { createdAt: "DESC" },
    });

    return users.map((user) => this.mapToClientUser(user));
  }

  async createForTenant(
    tenantId: string,
    payload: CreateClientUserDto,
  ): Promise<ClientUser> {
    const client = await this.clientRepository.findOne({ where: { id: tenantId } });
    if (!client) {
      throw new NotFoundException("Tenant not found");
    }

    const normalizedEmail = payload.email.toLowerCase();

    const existingUser = await this.userRepository.findOne({
      where: { tenantId, email: normalizedEmail },
    });

    if (existingUser) {
      throw new ConflictException("A user with this email already exists for the tenant");
    }

    const passwordHash = await bcrypt.hash(payload.password, 10);

    const user = this.userRepository.create({
      tenantId,
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
    tenantId,
    roles = [UserRole.CLIENT_VIEWER],
    temporaryPassword,
  }: CreateClientUserInput) {
    if (!clientSlug && !tenantId) {
      throw new BadRequestException("Either clientSlug or tenantId must be provided");
    }

    const client = await this.clientRepository.findOne({
      where: tenantId ? { id: tenantId } : { slug: clientSlug },
    });
    if (!client) {
      throw new NotFoundException(
        `Tenant with ${tenantId ? `id ${tenantId}` : `slug ${clientSlug}`} not found`,
      );
    }

    const normalizedEmail = email.toLowerCase();

    const existing = await this.userRepository.findOne({
      where: { email: normalizedEmail, tenantId: client.id },
    });

    if (existing) {
      throw new ConflictException(
        "A user with this email already exists for the tenant",
      );
    }

    const password = temporaryPassword ?? randomBytes(16).toString("hex");
    const passwordHash = await bcrypt.hash(password, 10);

    const user = this.userRepository.create({
      email: normalizedEmail,
      tenantId: client.id,
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
      tenantId: savedUser.tenantId,
      clientSlug: client.slug,
      clientName: client.name,
      roles: uniqueRoles,
      temporaryPassword: password,
      createdAt: savedUser.createdAt.toISOString(),
      updatedAt: savedUser.updatedAt.toISOString(),
    };
  }

  async updateAssignedLots(
    tenantId: string,
    userId: string,
    payload: UpdateClientUserLotsDto,
  ): Promise<ClientUser> {
    const user = await this.userRepository.findOne({
      where: { id: userId, tenantId },
    });

    if (!user) {
      throw new NotFoundException("User not found");
    }

    const lotIds = payload.lotIds ?? [];
    const uniqueLotIds = Array.from(new Set(lotIds));

    if (uniqueLotIds.length) {
      const lots = await this.lotRepository.find({
        where: { tenantId, id: In(uniqueLotIds) },
        select: ["id"],
      });

      if (lots.length !== uniqueLotIds.length) {
        throw new BadRequestException("One or more lots do not belong to this tenant");
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

  async findById(id: string): Promise<User | null> {
    return this.userRepository.findOne({
      where: { id },
      relations: ["userRoles", "userRoles.role"],
    });
  }

  async findByRole(roleName: string, tenantId?: string): Promise<User[]> {
    const query = this.userRepository
      .createQueryBuilder("user")
      .leftJoinAndSelect("user.userRoles", "userRoles")
      .leftJoinAndSelect("userRoles.role", "role")
      .where("role.name = :roleName", { roleName });

    if (tenantId) {
      query.andWhere("user.tenant_id = :tenantId", { tenantId });
    }

    return query.getMany();
  }

  async createOperator(
    tenantId: string | null,
    email: string,
    password: string,
  ): Promise<User> {
    const normalizedEmail = email.toLowerCase();

    const existingUser = await this.userRepository.findOne({
      where: { tenantId, email: normalizedEmail },
    });

    if (existingUser) {
      throw new ConflictException("A user with this email already exists");
    }

    const passwordHash = await bcrypt.hash(password, 10);

    const user = this.userRepository.create({
      tenantId,
      email: normalizedEmail,
      passwordHash,
      isActive: true,
    });

    const savedUser = await this.userRepository.save(user);

    // Assign OPERATOR role
    const operatorRole = await this.roleRepository.findOne({
      where: { name: "OPERATOR" },
    });

    if (!operatorRole) {
      throw new BadRequestException("OPERATOR role not found");
    }

    await this.userRoleRepository.save(
      this.userRoleRepository.create({
        userId: savedUser.id,
        roleId: operatorRole.id,
        isPrimary: true,
      }),
    );

    return savedUser;
  }
}