import { Injectable, ForbiddenException, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { In, Repository } from "typeorm";
import { Factory } from "../entities/factory.entity";
import { Client } from "../entities/client.entity";
import { FactoryRole } from "../entities/factory-role.entity";
import { SupplyChainRole } from "../entities/supply-chain-role.entity";
import { FactoryCertification } from "../entities/factory-certification.entity";

type FactoryCapabilityInput = {
  roleId: string;
  co2OverrideKg?: number | null;
  notes?: string | null;
};

type FactoryCertificationInput = {
  certification: string;
};

type FactoryPayload = {
  name?: string;
  city?: string | null;
  country?: string;
  clientId?: string | null;
  capabilities?: FactoryCapabilityInput[];
  certifications?: FactoryCertificationInput[];
};

@Injectable()
export class FactoryService {
  constructor(
    @InjectRepository(Factory)
    private readonly factoryRepository: Repository<Factory>,
    @InjectRepository(Client)
    private readonly clientRepository: Repository<Client>,
    @InjectRepository(FactoryRole)
    private readonly factoryRoleRepository: Repository<FactoryRole>,
    @InjectRepository(SupplyChainRole)
    private readonly supplyChainRoleRepository: Repository<SupplyChainRole>,
    @InjectRepository(FactoryCertification)
    private readonly factoryCertificationRepository: Repository<FactoryCertification>,
  ) {}

  async listByClient(clientId: string | null): Promise<Factory[]> {
    if (!clientId) {
      return this.factoryRepository.find({
        order: { name: "ASC" },
        relations: ["capabilities", "capabilities.role", "certifications"],
      });
    }

    await this.ensureClientExists(clientId);

    return this.factoryRepository.find({
      where: { clientId },
      order: { name: "ASC" },
      relations: ["capabilities", "capabilities.role", "certifications"],
    });
  }

  async create(clientId: string | null, data: FactoryPayload): Promise<Factory> {
    const effectiveClientId = clientId ? await this.ensureClientExists(clientId) : null;
    const { capabilities, certifications, ...factoryData } = data;
    const factory = this.factoryRepository.create({ ...factoryData, clientId: effectiveClientId });
    const saved = await this.factoryRepository.save(factory);

    if (Array.isArray(capabilities)) {
      await this.syncCapabilities(saved.id, capabilities);
    }

    if (Array.isArray(certifications)) {
      await this.syncCertifications(saved.id, certifications);
    }

    return this.getFactory(saved.id);
  }

  async update(clientId: string | null, factoryId: string, data: FactoryPayload): Promise<Factory> {
    const effectiveClientId = clientId ? await this.ensureClientExists(clientId) : null;

    const where = effectiveClientId ? { id: factoryId, clientId: effectiveClientId } : { id: factoryId };
    const factory = await this.factoryRepository.findOne({ where });
    if (!factory) {
      throw new NotFoundException("Factory not found");
    }

    if (effectiveClientId) {
      factory.clientId = effectiveClientId;
    }

    const { capabilities, certifications, ...factoryData } = data;

    this.factoryRepository.merge(factory, factoryData);
    const saved = await this.factoryRepository.save(factory);

    if (Array.isArray(capabilities)) {
      await this.syncCapabilities(saved.id, capabilities);
    }

    if (Array.isArray(certifications)) {
      await this.syncCertifications(saved.id, certifications);
    }

    return this.getFactory(saved.id);
  }

  async ensureBelongsToClient(clientId: string, factoryId: string): Promise<Factory> {
    const factory = await this.factoryRepository.findOne({ where: { id: factoryId, clientId } });
    if (!factory) {
      throw new ForbiddenException("Factory not found for client");
    }

    return factory;
  }

  private async ensureClientExists(clientId: string): Promise<string> {
    const existing = await this.clientRepository.findOne({ where: { id: clientId } });
    if (existing) {
      return existing.id;
    }

    const fallbackSlug = `demo-${clientId.slice(0, 8)}`;
    const client = this.clientRepository.create({
      id: clientId,
      name: "Demo Client",
      slug: fallbackSlug,
    });

    const saved = await this.clientRepository.save(client);
    return saved.id;
  }

  private async syncCapabilities(
    factoryId: string,
    capabilities: FactoryCapabilityInput[] = [],
  ): Promise<void> {
    if (!capabilities.length) {
      await this.factoryRoleRepository.delete({ factoryId });
      return;
    }

    const roleIds = capabilities.map((capability) => capability.roleId);
    const roles = await this.supplyChainRoleRepository.find({ where: { id: In(roleIds) } });
    if (roles.length !== roleIds.length) {
      const found = new Set(roles.map((role) => role.id));
      const missing = roleIds.filter((id) => !found.has(id));
      throw new NotFoundException(`Unknown supply chain role(s): ${missing.join(", ")}`);
    }

    await this.factoryRoleRepository.delete({ factoryId });

    const records = capabilities.map((capability) =>
      this.factoryRoleRepository.create({
        factoryId,
        roleId: capability.roleId,
        co2OverrideKg: capability.co2OverrideKg ?? null,
        notes: capability.notes ?? null,
      }),
    );

    await this.factoryRoleRepository.save(records);
  }

  private async getFactory(id: string): Promise<Factory> {
    return this.factoryRepository.findOneOrFail({
      where: { id },
      relations: ["capabilities", "capabilities.role", "certifications"],
    });
  }

  private async syncCertifications(
    factoryId: string,
    certifications: FactoryCertificationInput[] = [],
  ): Promise<void> {
    await this.factoryCertificationRepository.delete({ factoryId });

    if (!certifications.length) {
      return;
    }

    const records = certifications
      .map((certification) => certification.certification?.trim())
      .filter((value): value is string => Boolean(value))
      .map((value) =>
        this.factoryCertificationRepository.create({
          factoryId,
          certification: value,
        }),
      );

    if (records.length) {
      await this.factoryCertificationRepository.save(records);
    }
  }
}
