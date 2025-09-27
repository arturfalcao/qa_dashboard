import { Injectable, NotFoundException, BadRequestException, ForbiddenException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { In, Repository } from "typeorm";
import { Lot } from "../entities/lot.entity";
import { Approval } from "../entities/approval.entity";
import { Inspection } from "../entities/inspection.entity";
import { Defect } from "../entities/defect.entity";
import {
  LotStatus,
  ApprovalDecision,
  EventType,
  SupplyChainStageStatus,
} from "@qa-dashboard/shared";
import { EventService } from "./event.service";
import { Factory } from "../entities/factory.entity";
import { LotFactory } from "../entities/lot-factory.entity";
import { SupplyChainRole } from "../entities/supply-chain-role.entity";
import { LotFactoryRole } from "../entities/lot-factory-role.entity";
import { FactoryRole } from "../entities/factory-role.entity";

interface LotSupplierRoleInput {
  roleId: string;
  co2Kg?: number | null;
  notes?: string | null;
  sequence?: number;
  status?: SupplyChainStageStatus;
  startedAt?: Date | string | null;
  completedAt?: Date | string | null;
}

interface LotSupplierInput {
  factoryId: string;
  sequence?: number;
  stage?: string | null;
  isPrimary?: boolean;
  roles?: LotSupplierRoleInput[];
}

@Injectable()
export class LotService {
  constructor(
    @InjectRepository(Lot)
    private readonly lotRepository: Repository<Lot>,
    @InjectRepository(Approval)
    private readonly approvalRepository: Repository<Approval>,
    @InjectRepository(Inspection)
    private readonly inspectionRepository: Repository<Inspection>,
    @InjectRepository(Defect)
    private readonly defectRepository: Repository<Defect>,
    @InjectRepository(Factory)
    private readonly factoryRepository: Repository<Factory>,
    @InjectRepository(LotFactory)
    private readonly lotFactoryRepository: Repository<LotFactory>,
    @InjectRepository(LotFactoryRole)
    private readonly lotFactoryRoleRepository: Repository<LotFactoryRole>,
    @InjectRepository(SupplyChainRole)
    private readonly supplyChainRoleRepository: Repository<SupplyChainRole>,
    @InjectRepository(FactoryRole)
    private readonly factoryRoleRepository: Repository<FactoryRole>,
    private readonly eventService: EventService,
  ) {}

  async listLots(clientId: string): Promise<any[]> {
    // First get lots with basic relations
    const lots = await this.lotRepository.find({
      where: { clientId },
      relations: [
        "factory",
        "suppliers",
        "suppliers.factory",
        "approvals",
      ],
      order: { createdAt: "DESC" },
    });

    if (lots.length === 0) {
      return [];
    }

    // Get supplier roles and supply chain roles separately for efficiency
    const lotIds = lots.map(lot => lot.id);

    const supplierRoles = await this.lotFactoryRoleRepository
      .createQueryBuilder("lfr")
      .leftJoinAndSelect("lfr.role", "role")
      .leftJoin("lfr.lotFactory", "lf")
      .where("lf.lot_id IN (:...lotIds)", { lotIds })
      .getMany();

    // Group roles by lot factory ID
    const rolesByLotFactory = new Map<string, any[]>();
    supplierRoles.forEach(role => {
      const key = role.lotFactoryId;
      if (!rolesByLotFactory.has(key)) {
        rolesByLotFactory.set(key, []);
      }
      rolesByLotFactory.get(key)!.push(role);
    });

    // Attach roles to suppliers
    lots.forEach(lot => {
      lot.suppliers?.forEach(supplier => {
        supplier.roles = rolesByLotFactory.get(supplier.id) || [];
      });
    });

    return lots.map((lot) => this.toLotDto(lot));
  }

  async createLot(
    clientId: string,
    payload: {
      suppliers?: LotSupplierInput[];
      factoryId?: string;
      styleRef: string;
      quantityTotal: number;
      status?: LotStatus;
      materialComposition?: Array<{
        fiber: string;
        percentage: number;
        properties?: Record<string, any>;
      }>;
      dyeLot?: string;
      certifications?: Array<{
        type: string;
        number?: string;
        auditLink?: string;
        validUntil?: string;
        issuer?: string;
      }>;
      dppMetadata?: Record<string, any>;
    },
  ): Promise<any> {
    const { suppliers, primaryFactoryId } = await this.normalizeSuppliers(clientId, payload);

    const lot = this.lotRepository.create({
      clientId,
      factoryId: primaryFactoryId,
      styleRef: payload.styleRef,
      quantityTotal: payload.quantityTotal,
      status: payload.status ?? LotStatus.PLANNED,
      defectRate: 0,
      inspectedProgress: 0,
      materialComposition: payload.materialComposition || null,
      dyeLot: payload.dyeLot || null,
      certifications: payload.certifications || null,
      dppMetadata: payload.dppMetadata || null,
    });

    const saved = await this.lotRepository.save(lot);
    await this.syncSuppliers(saved.id, suppliers, primaryFactoryId);

    return this.getLot(clientId, saved.id);
  }

  async updateLot(
    clientId: string,
    lotId: string,
    payload: {
      suppliers?: LotSupplierInput[];
      factoryId?: string;
      styleRef?: string;
      quantityTotal?: number;
      status?: LotStatus;
      materialComposition?: Array<{
        fiber: string;
        percentage: number;
        properties?: Record<string, any>;
      }>;
      dyeLot?: string;
      certifications?: Array<{
        type: string;
        number?: string;
        auditLink?: string;
        validUntil?: string;
        issuer?: string;
      }>;
      dppMetadata?: Record<string, any>;
    },
  ): Promise<any> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId, clientId } });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    let normalizedSuppliers:
      | Array<{
          factoryId: string;
          sequence: number;
          stage: string | null;
          isPrimary: boolean;
          roles: LotSupplierRoleInput[];
        }>
      | undefined;
    let primaryFactoryId: string | undefined;

    if (payload.suppliers) {
      const normalized = await this.normalizeSuppliers(clientId, {
        suppliers: payload.suppliers,
        factoryId: payload.factoryId ?? lot.factoryId,
      });

      normalizedSuppliers = normalized.suppliers;
      primaryFactoryId = normalized.primaryFactoryId;
      lot.factoryId = primaryFactoryId;
    } else if (payload.factoryId && payload.factoryId !== lot.factoryId) {
      const normalized = await this.normalizeSuppliers(clientId, {
        suppliers: [{ factoryId: payload.factoryId, isPrimary: true }],
        factoryId: payload.factoryId,
      });

      normalizedSuppliers = normalized.suppliers;
      primaryFactoryId = normalized.primaryFactoryId;
      lot.factoryId = primaryFactoryId;
    }

    if (payload.status && payload.status !== lot.status) {
      this.validateTransition(lot.status, payload.status);
      lot.status = payload.status;
    }

    if (payload.styleRef) {
      lot.styleRef = payload.styleRef;
    }

    if (payload.quantityTotal !== undefined) {
      lot.quantityTotal = payload.quantityTotal;
    }

    if (payload.materialComposition !== undefined) {
      lot.materialComposition = payload.materialComposition;
    }

    if (payload.dyeLot !== undefined) {
      lot.dyeLot = payload.dyeLot;
    }

    if (payload.certifications !== undefined) {
      lot.certifications = payload.certifications;
    }

    if (payload.dppMetadata !== undefined) {
      lot.dppMetadata = payload.dppMetadata || null;
    }

    await this.lotRepository.save(lot);

    if (normalizedSuppliers && primaryFactoryId) {
      await this.syncSuppliers(lotId, normalizedSuppliers, primaryFactoryId);
    }

    await this.recalculateLotMetrics(lotId);
    return this.getLot(clientId, lotId);
  }

  async getLot(clientId: string, lotId: string): Promise<any> {
    const lot = await this.lotRepository.findOne({
      where: { id: lotId, clientId },
      relations: [
        "factory",
        "suppliers",
        "suppliers.factory",
        "suppliers.roles",
        "suppliers.roles.role",
        "approvals",
        "approvals.user",
        "inspections",
        "inspections.defects",
        "inspections.defects.photos",
      ],
    });

    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    return this.toLotDto(lot);
  }

  private async normalizeSuppliers(
    clientId: string,
    payload: { suppliers?: LotSupplierInput[]; factoryId?: string },
  ): Promise<{
    suppliers: Array<{
      factoryId: string;
      sequence: number;
      stage: string | null;
      isPrimary: boolean;
      roles: LotSupplierRoleInput[];
    }>;
    primaryFactoryId: string;
  }> {
    const baseSuppliers = [...(payload.suppliers ?? [])];
    const dedupe = new Map<string, LotSupplierInput>();

    const sanitizeRoles = (roles?: LotSupplierRoleInput[]): LotSupplierRoleInput[] => {
      if (!roles || roles.length === 0) {
        return [];
      }

      const map = new Map<string, LotSupplierRoleInput>();
      roles.forEach((role) => {
        if (!role?.roleId) {
          return;
        }

        const existing = map.get(role.roleId);
        if (!existing) {
          map.set(role.roleId, {
            roleId: role.roleId,
            sequence: role.sequence,
            co2Kg: role.co2Kg ?? null,
            notes: role.notes ?? null,
            status: role.status ?? SupplyChainStageStatus.NOT_STARTED,
            startedAt: role.startedAt ?? null,
            completedAt: role.completedAt ?? null,
          });
        } else {
          existing.sequence = existing.sequence ?? role.sequence;
          existing.co2Kg = existing.co2Kg ?? role.co2Kg ?? null;
          existing.notes = existing.notes ?? role.notes ?? null;
          existing.status = existing.status ?? role.status ?? SupplyChainStageStatus.NOT_STARTED;
          existing.startedAt = existing.startedAt ?? role.startedAt ?? null;
          existing.completedAt = existing.completedAt ?? role.completedAt ?? null;
        }
      });

      return Array.from(map.values());
    };

    if (!baseSuppliers.length && payload.factoryId) {
      baseSuppliers.push({ factoryId: payload.factoryId, isPrimary: true });
    }

    if (!baseSuppliers.length) {
      throw new BadRequestException("At least one supplier factory is required");
    }

    baseSuppliers.forEach((supplier, index) => {
      const key = supplier.factoryId;
      if (!dedupe.has(key)) {
        dedupe.set(key, {
          factoryId: supplier.factoryId,
          sequence: supplier.sequence ?? index,
          stage: supplier.stage,
          isPrimary: supplier.isPrimary ?? false,
          roles: sanitizeRoles(supplier.roles),
        });
      } else {
        const existing = dedupe.get(key)!;
        if (existing.sequence === undefined) {
          existing.sequence = supplier.sequence ?? index;
        }
        existing.stage = existing.stage ?? supplier.stage;
        existing.isPrimary = existing.isPrimary || supplier.isPrimary === true;
        existing.roles = sanitizeRoles([...(existing.roles ?? []), ...(supplier.roles ?? [])]);
      }
    });

    const dedupedSuppliers = Array.from(dedupe.values());
    const roleIds = Array.from(
      new Set(
        dedupedSuppliers.flatMap((supplier) => (supplier.roles ?? []).map((role) => role.roleId)),
      ),
    );

    const roleEntities = roleIds.length
      ? await this.supplyChainRoleRepository.find({ where: { id: In(roleIds) } })
      : [];
    const orderMap = new Map(roleEntities.map((role) => [role.id, role.defaultSequence ?? 0]));

    const normalizedBase = dedupedSuppliers.map((supplier, index) => {
      const trimmedStage = supplier.stage?.trim?.() || null;
      const roles = (supplier.roles ?? [])
        .slice()
        .sort(
          (a, b) =>
            (orderMap.get(a.roleId) ?? Number.MAX_SAFE_INTEGER) -
            (orderMap.get(b.roleId) ?? Number.MAX_SAFE_INTEGER),
        )
        .map((role, roleIndex) => ({
          ...role,
          sequence: roleIndex,
        }));

      const minRoleSequence = roles.length
        ? Math.min(...roles.map((role) => orderMap.get(role.roleId) ?? Number.MAX_SAFE_INTEGER))
        : Number.MAX_SAFE_INTEGER;

      return {
        factoryId: supplier.factoryId,
        rawSequence: supplier.sequence ?? index,
        sequence: supplier.sequence ?? index,
        stage: trimmedStage,
        isPrimary: supplier.isPrimary ?? false,
        minRoleSequence,
        roles,
      };
    });

    normalizedBase.sort((a, b) => {
      if (a.minRoleSequence !== b.minRoleSequence) {
        return a.minRoleSequence - b.minRoleSequence;
      }
      return a.rawSequence - b.rawSequence;
    });

    normalizedBase.forEach((supplier, index) => {
      supplier.sequence = index;
    });

    let primaryFactoryId =
      normalizedBase.find((supplier) => supplier.isPrimary)?.factoryId ??
      payload.factoryId ??
      normalizedBase[0].factoryId;

    normalizedBase.forEach((supplier) => {
      supplier.isPrimary = supplier.factoryId === primaryFactoryId;
    });

    const factoryIds = normalizedBase.map((supplier) => supplier.factoryId);
    const factories = await this.factoryRepository.find({
      where: { id: In(factoryIds), clientId },
    });

    if (factories.length !== factoryIds.length) {
      throw new ForbiddenException("One or more selected factories are not available for this client");
    }

    const suppliers = normalizedBase.map((supplier) => ({
      factoryId: supplier.factoryId,
      sequence: supplier.sequence,
      stage: supplier.stage,
      isPrimary: supplier.isPrimary,
      roles: supplier.roles,
    }));

    return {
      suppliers,
      primaryFactoryId,
    };
  }

  private async syncSuppliers(
    lotId: string,
    suppliers: Array<{
      factoryId: string;
      sequence: number;
      stage: string | null;
      isPrimary: boolean;
      roles: LotSupplierRoleInput[];
    }>,
    primaryFactoryId: string,
  ): Promise<void> {
    const existingSuppliers = await this.lotFactoryRepository.find({
      where: { lotId },
      relations: ["roles"],
    });

    const previousRolesByFactory = new Map<string, LotFactoryRole[]>(
      existingSuppliers.map((supplier) => [supplier.factoryId, supplier.roles ?? []]),
    );

    await this.lotFactoryRepository.delete({ lotId });

    const records = suppliers.map((supplier) =>
      this.lotFactoryRepository.create({
        lotId,
        factoryId: supplier.factoryId,
        sequence: supplier.sequence,
        stage: supplier.stage,
        isPrimary: supplier.factoryId === primaryFactoryId,
      }),
    );

    const saved = await this.lotFactoryRepository.save(records);

    await Promise.all(
      saved.map((record, index) =>
        this.syncSupplierRoles(
          record.id,
          record.factoryId,
          suppliers[index]?.roles ?? [],
          previousRolesByFactory.get(record.factoryId) ?? [],
        ),
      ),
    );

    await this.ensureLotSupplyChainProgress(lotId);
  }

  private async syncSupplierRoles(
    lotFactoryId: string,
    factoryId: string,
    roles: LotSupplierRoleInput[],
    previousRoles: LotFactoryRole[],
  ): Promise<void> {
    await this.lotFactoryRoleRepository.delete({ lotFactoryId });

    if (!roles || roles.length === 0) {
      return;
    }

    const uniqueRoleIds = Array.from(new Set(roles.map((role) => role.roleId)));
    const roleEntities = await this.supplyChainRoleRepository.find({ where: { id: In(uniqueRoleIds) } });

    if (roleEntities.length !== uniqueRoleIds.length) {
      const foundIds = new Set(roleEntities.map((role) => role.id));
      const missing = uniqueRoleIds.filter((id) => !foundIds.has(id));
      throw new BadRequestException(
        `Unknown supply chain role(s): ${missing.join(", ")}`,
      );
    }

    const roleMap = new Map(roleEntities.map((role) => [role.id, role]));

    const factoryCapabilities = await this.factoryRoleRepository.find({ where: { factoryId } });
    const allowedRoleIds = new Set(factoryCapabilities.map((capability) => capability.roleId));
    const unsupportedRoles = uniqueRoleIds.filter((roleId) => !allowedRoleIds.has(roleId));

    if (unsupportedRoles.length) {
      const names = unsupportedRoles
        .map((roleId) => roleMap.get(roleId)?.name || roleId)
        .join(", ");
      throw new BadRequestException(
        `Factory is not configured for the selected roles: ${names}. Update factory capabilities first.`,
      );
    }

    const previousRoleMap = new Map(previousRoles.map((prev) => [prev.roleId, prev]));

    const entries = roles.map((role, index) => {
      const roleEntity = roleMap.get(role.roleId)!;
      const previous = previousRoleMap.get(role.roleId);
      return this.lotFactoryRoleRepository.create({
        lotFactoryId,
        roleId: role.roleId,
        sequence: role.sequence ?? index,
        co2Kg: role.co2Kg ?? previous?.co2Kg ?? roleEntity.defaultCo2Kg ?? null,
        notes: role.notes ?? previous?.notes ?? null,
        status: role.status ?? previous?.status ?? SupplyChainStageStatus.NOT_STARTED,
        startedAt: role.startedAt
          ? new Date(role.startedAt)
          : previous?.startedAt ?? null,
        completedAt: role.completedAt
          ? new Date(role.completedAt)
          : previous?.completedAt ?? null,
      });
    });

    await this.lotFactoryRoleRepository.save(entries);
  }

  private async ensureLotSupplyChainProgress(lotId: string): Promise<void> {
    const roles = await this.lotFactoryRoleRepository
      .createQueryBuilder("role")
      .innerJoin("role.lotFactory", "lf")
      .where("lf.lot_id = :lotId", { lotId })
      .orderBy("lf.sequence", "ASC")
      .addOrderBy("role.sequence", "ASC")
      .getMany();

    if (!roles.length) {
      return;
    }

    if (roles.every((role) => role.status === SupplyChainStageStatus.COMPLETED)) {
      return;
    }

    let inProgressFound = false;
    const updates: LotFactoryRole[] = [];

    roles.forEach((role) => {
      if (role.status === SupplyChainStageStatus.IN_PROGRESS) {
        if (!inProgressFound) {
          inProgressFound = true;
          if (!role.startedAt) {
            role.startedAt = new Date();
            updates.push(role);
          }
        } else {
          role.status = SupplyChainStageStatus.NOT_STARTED;
          role.startedAt = null;
          role.completedAt = null;
          updates.push(role);
        }
      }
    });

    if (updates.length) {
      await this.lotFactoryRoleRepository.save(updates);
    }
  }

  private toLotDto(lot: Lot): any {
    const suppliers = (lot.suppliers ?? [])
      .map((supplier) => ({
        id: supplier.id,
        factoryId: supplier.factoryId,
        sequence: supplier.sequence,
        stage: supplier.stage ?? null,
        isPrimary: supplier.isPrimary,
        factory: supplier.factory,
        roles: (supplier.roles ?? [])
          .map((role) => ({
            id: role.id,
            roleId: role.roleId,
            sequence: role.sequence,
            co2Kg: role.co2Kg ?? role.role?.defaultCo2Kg ?? null,
            notes: role.notes ?? null,
            role: role.role,
            status: role.status,
            startedAt: role.startedAt,
            completedAt: role.completedAt,
          }))
          .sort((a, b) => a.sequence - b.sequence),
      }))
      .sort((a, b) => a.sequence - b.sequence);

    const primaryFactoryId = suppliers.find((supplier) => supplier.isPrimary)?.factoryId ?? lot.factoryId;

    // Get the latest inspection (most recent by createdAt)
    const latestInspection = lot.inspections && lot.inspections.length > 0
      ? lot.inspections.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0]
      : null;

    return {
      ...lot,
      suppliers,
      primaryFactoryId,
      latestInspection,
    };
  }

  async advanceSupplyChainStage(clientId: string, lotId: string): Promise<any> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId, clientId } });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    const roles = await this.lotFactoryRoleRepository
      .createQueryBuilder("role")
      .innerJoinAndSelect("role.lotFactory", "lf")
      .where("lf.lot_id = :lotId", { lotId })
      .orderBy("lf.sequence", "ASC")
      .addOrderBy("role.sequence", "ASC")
      .getMany();

    if (!roles.length) {
      throw new BadRequestException("No supply chain roles configured for this lot");
    }

    const now = new Date();
    const currentIndex = roles.findIndex((role) => role.status === SupplyChainStageStatus.IN_PROGRESS);

    if (currentIndex < 0) {
      const next = roles.find((role) => role.status !== SupplyChainStageStatus.COMPLETED);
      if (!next) {
        return this.getLot(clientId, lotId);
      }

      next.status = SupplyChainStageStatus.IN_PROGRESS;
      next.startedAt = next.startedAt ?? now;
      next.completedAt = null;
      await this.lotFactoryRoleRepository.save(next);

      await this.ensureLotSupplyChainProgress(lotId);
      return this.getLot(clientId, lotId);
    }

    const current = roles[currentIndex];
    current.status = SupplyChainStageStatus.COMPLETED;
    current.completedAt = now;
    await this.lotFactoryRoleRepository.save(current);

    const next = roles
      .slice(currentIndex + 1)
      .find((role) => role.status !== SupplyChainStageStatus.COMPLETED);

    if (next) {
      next.status = SupplyChainStageStatus.IN_PROGRESS;
      next.startedAt = next.startedAt ?? now;
      next.completedAt = null;
      await this.lotFactoryRoleRepository.save(next);
    }

    await this.ensureLotSupplyChainProgress(lotId);

    const refreshedRoles = await this.lotFactoryRoleRepository
      .createQueryBuilder("role")
      .innerJoin("role.lotFactory", "lf")
      .where("lf.lot_id = :lotId", { lotId })
      .getMany();

    const anyInProgress = refreshedRoles.some(
      (role) => role.status === SupplyChainStageStatus.IN_PROGRESS,
    );
    const allCompleted =
      refreshedRoles.length > 0 &&
      refreshedRoles.every((role) => role.status === SupplyChainStageStatus.COMPLETED);

    if (allCompleted && [LotStatus.PLANNED, LotStatus.IN_PRODUCTION].includes(lot.status)) {
      await this.lotRepository.update(lotId, { status: LotStatus.INSPECTION });
    } else if (anyInProgress && lot.status === LotStatus.PLANNED) {
      await this.lotRepository.update(lotId, { status: LotStatus.IN_PRODUCTION });
    }

    return this.getLot(clientId, lotId);
  }

  private validateTransition(current: LotStatus, next: LotStatus) {
    const allowed: Record<LotStatus, LotStatus[]> = {
      [LotStatus.PLANNED]: [LotStatus.IN_PRODUCTION],
      [LotStatus.IN_PRODUCTION]: [LotStatus.INSPECTION],
      [LotStatus.INSPECTION]: [LotStatus.PENDING_APPROVAL],
      [LotStatus.PENDING_APPROVAL]: [LotStatus.APPROVED, LotStatus.REJECTED],
      [LotStatus.APPROVED]: [LotStatus.SHIPPED],
      [LotStatus.REJECTED]: [],
      [LotStatus.SHIPPED]: [],
    };

    if (!allowed[current]?.includes(next)) {
      throw new BadRequestException(
        `Invalid status transition from ${current} to ${next}`,
      );
    }
  }

  async transitionToPendingApproval(lotId: string): Promise<void> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId }, relations: ["factory"] });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    this.validateTransition(lot.status, LotStatus.PENDING_APPROVAL);

    await this.lotRepository.update(lotId, { status: LotStatus.PENDING_APPROVAL });

    await this.eventService.createEvent(
      lot.clientId,
      EventType.LOT_AWAITING_APPROVAL,
      { lotId, styleRef: lot.styleRef, factory: lot.factory?.name },
      lotId,
    );
  }

  async approveLot(
    clientId: string,
    lotId: string,
    approvedBy: string,
    note?: string,
  ): Promise<void> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId, clientId } });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    this.validateTransition(lot.status, LotStatus.APPROVED);

    await this.approvalRepository.save({
      lotId,
      approvedBy,
      decision: ApprovalDecision.APPROVE,
      note,
    });

    await this.lotRepository.update(lotId, { status: LotStatus.APPROVED });

    await this.eventService.createEvent(
      clientId,
      EventType.LOT_DECIDED,
      {
        lotId,
        styleRef: lot.styleRef,
        decision: ApprovalDecision.APPROVE,
        approvedBy,
      },
      lotId,
    );
  }

  async rejectLot(
    clientId: string,
    lotId: string,
    approvedBy: string,
    note: string,
  ): Promise<void> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId, clientId } });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    this.validateTransition(lot.status, LotStatus.REJECTED);

    await this.approvalRepository.save({
      lotId,
      approvedBy,
      decision: ApprovalDecision.REJECT,
      note,
    });

    await this.lotRepository.update(lotId, { status: LotStatus.REJECTED });

    await this.eventService.createEvent(
      clientId,
      EventType.LOT_DECIDED,
      {
        lotId,
        styleRef: lot.styleRef,
        decision: ApprovalDecision.REJECT,
        approvedBy,
      },
      lotId,
    );
  }

  async recalculateLotMetrics(lotId: string): Promise<void> {
    const lot = await this.lotRepository.findOne({ where: { id: lotId } });
    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    const inspections = await this.inspectionRepository.count({ where: { lotId } });
    const defects = await this.defectRepository.count({ where: { inspection: { lotId } } });

    if (!inspections) {
      await this.lotRepository.update(lotId, {
        inspectedProgress: 0,
        defectRate: 0,
      });
      return;
    }

    const defectRate = (defects / inspections) * 100;
    const inspectedProgress = lot.quantityTotal
      ? Math.min(100, (inspections / lot.quantityTotal) * 100)
      : 0;

    await this.lotRepository.update(lotId, {
      defectRate: Math.round(defectRate * 100) / 100,
      inspectedProgress: Math.round(inspectedProgress * 100) / 100,
    });
  }
}
