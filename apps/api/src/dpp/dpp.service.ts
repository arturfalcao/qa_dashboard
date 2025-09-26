import { Injectable, NotFoundException, ForbiddenException, BadRequestException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as QRCode from "qrcode";
import { Dpp, DppStatus } from "../database/entities/dpp.entity";
import { DppEvent, DppEventType } from "../database/entities/dpp-event.entity";
import { DppAccessLog, DppAccessView } from "../database/entities/dpp-access-log.entity";
import { Lot } from "../database/entities/lot.entity";
import { CreateDppDto, UpdateDppDto, CreateEventDto } from "./dpp-schemas";
import { UserRole } from "@qa-dashboard/shared";

export interface DppAccessLogData {
  ip: string;
  userAgent?: string;
  userId?: string;
  endpoint?: string;
}

@Injectable()
export class DppService {
  constructor(
    @InjectRepository(Dpp)
    private dppRepository: Repository<Dpp>,
    @InjectRepository(DppEvent)
    private eventRepository: Repository<DppEvent>,
    @InjectRepository(DppAccessLog)
    private accessLogRepository: Repository<DppAccessLog>,
    @InjectRepository(Lot)
    private lotRepository: Repository<Lot>,
  ) {}

  async createDpp(clientId: string, userId: string, data: CreateDppDto): Promise<Dpp> {
    const dpp = this.dppRepository.create({
      clientId,
      createdBy: userId,
      ...data,
    });

    const savedDpp = await this.dppRepository.save(dpp);

    // Create initial event
    await this.createEvent(savedDpp.id, {
      type: DppEventType.CREATED,
      actor: userId,
      timestamp: new Date(),
    });

    return savedDpp;
  }

  async updateDpp(id: string, clientId: string, data: UpdateDppDto): Promise<Dpp> {
    const dpp = await this.getDppForClient(id, clientId);

    if (dpp.status === DppStatus.PUBLISHED) {
      throw new BadRequestException("Cannot update published DPP");
    }

    Object.assign(dpp, data);
    return await this.dppRepository.save(dpp);
  }

  async publishDpp(id: string, clientId: string, userId: string): Promise<Dpp> {
    const dpp = await this.getDppForClient(id, clientId);

    if (dpp.status !== DppStatus.DRAFT) {
      throw new BadRequestException("Only draft DPPs can be published");
    }

    dpp.status = DppStatus.PUBLISHED;
    const savedDpp = await this.dppRepository.save(dpp);

    // Create publish event
    await this.createEvent(id, {
      type: DppEventType.PUBLISHED,
      actor: userId,
      timestamp: new Date(),
    });

    return savedDpp;
  }

  async getDppForClient(id: string, clientId: string): Promise<Dpp> {
    const dpp = await this.dppRepository.findOne({
      where: { id, clientId },
      relations: ["client", "creator"],
    });

    if (!dpp) {
      throw new NotFoundException("DPP not found");
    }

    return dpp;
  }

  async getPublicDpp(id: string): Promise<{ dpp: Dpp; publicData: any } | null> {
    const dpp = await this.dppRepository.findOne({
      where: { id, status: DppStatus.PUBLISHED },
    });

    if (!dpp) {
      return null;
    }

    const publicData = {
      id: dpp.id,
      schemaVersion: dpp.schemaVersion,
      productSku: dpp.productSku,
      gtin: dpp.gtin,
      brand: dpp.brand,
      styleRef: dpp.styleRef,
      ...dpp.publicPayload,
      createdAt: dpp.createdAt,
      updatedAt: dpp.updatedAt,
    };

    return { dpp, publicData };
  }

  async getRestrictedDpp(id: string, clientId: string, userRoles: UserRole[]): Promise<any> {
    const dpp = await this.getDppForClient(id, clientId);

    // Check if user has restricted access permissions
    const canViewRestricted = userRoles.some(role =>
      [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)
    );

    if (!canViewRestricted) {
      throw new ForbiddenException("Insufficient permissions to view restricted data");
    }

    const restrictedData = {
      id: dpp.id,
      schemaVersion: dpp.schemaVersion,
      productSku: dpp.productSku,
      gtin: dpp.gtin,
      brand: dpp.brand,
      styleRef: dpp.styleRef,
      status: dpp.status,
      ...dpp.publicPayload,
      ...dpp.restrictedPayload,
      createdAt: dpp.createdAt,
      updatedAt: dpp.updatedAt,
    };

    return restrictedData;
  }

  async generateQrCode(id: string, baseUrl: string): Promise<Buffer> {
    const url = `${baseUrl}/dpp/${id}`;

    const qrBuffer = await QRCode.toBuffer(url, {
      width: 1024,
      margin: 4,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      },
      errorCorrectionLevel: 'M'
    });

    return qrBuffer;
  }

  async ingestFromLot(dppId: string, lotId: string, clientId: string): Promise<{ dpp: Dpp; warnings: string[] }> {
    const dpp = await this.getDppForClient(dppId, clientId);
    const lot = await this.lotRepository.findOne({
      where: { id: lotId, clientId },
      relations: [
        "suppliers",
        "suppliers.factory",
        "suppliers.roles",
        "suppliers.roles.role",
        "inspections",
        "inspections.defects",
        "inspections.defects.defectType",
      ],
    });

    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    const warnings: string[] = [];
    const restrictedPayload = { ...dpp.restrictedPayload };
    const publicPayload = { ...dpp.publicPayload };

    // Map supply chain
    if (lot.suppliers && lot.suppliers.length > 0) {
      const supplyChain = lot.suppliers
        .sort((a, b) => (a.sequence || 0) - (b.sequence || 0))
        .map(supplier => {
          const roles = supplier.roles?.map(role => role.role?.key?.toUpperCase()).filter(Boolean) || [];

          if (roles.length === 0) {
            warnings.push(`Supplier ${supplier.factory?.name || 'Unknown'} has no roles defined`);
          }

          return roles.map(roleKey => ({
            role: roleKey,
            factory: {
              name: supplier.factory?.name || "Unknown Factory",
              country: supplier.factory?.country || "Unknown",
              address: `${supplier.factory?.city || ""}, ${supplier.factory?.country || ""}`.trim(),
            }
          }));
        })
        .flat();

      restrictedPayload.supply_chain = supplyChain;
    } else {
      warnings.push("No suppliers found for lot");
    }

    // Map quality data
    if (lot.inspections && lot.inspections.length > 0) {
      const inspections = lot.inspections.map(inspection => ({
        lotId: lot.id,
        defectRate: lot.defectRate || 0,
        topDefects: inspection.defects?.map(defect => ({
          type: defect.defectType?.name || "Unknown",
          count: 1, // Could be enhanced with actual count
        })) || [],
        reportUrl: undefined, // Could be added later
      }));

      if (!restrictedPayload.quality) {
        restrictedPayload.quality = {};
      }
      restrictedPayload.quality.inspections = inspections;
    }

    // Map DPP Hub data to public payload
    if (lot.materialComposition && lot.materialComposition.length > 0) {
      publicPayload.materials = lot.materialComposition.map(material => ({
        fiber: material.fiber,
        percentage: material.percentage,
        properties: material.properties || {}
      }));
    } else {
      warnings.push("No material composition data found for lot");
    }

    if (lot.dyeLot) {
      if (!publicPayload.production) {
        publicPayload.production = {};
      }
      publicPayload.production.dye_lot = lot.dyeLot;
    }

    if (lot.certifications && lot.certifications.length > 0) {
      publicPayload.certifications = lot.certifications.map(cert => ({
        type: cert.type
      }));
    } else {
      warnings.push("No certifications found for lot");
    }

    // Include DPP metadata if available
    if (lot.dppMetadata) {
      publicPayload.metadata = {
        ...publicPayload.metadata,
        ...lot.dppMetadata
      };
    }

    // Update measurements if available (placeholder for future implementation)
    if (!restrictedPayload.quality) {
      restrictedPayload.quality = {};
    }
    if (!restrictedPayload.quality.measurements) {
      restrictedPayload.quality.measurements = [];
    }

    // Update the DPP with both public and restricted data
    dpp.publicPayload = publicPayload;
    dpp.restrictedPayload = restrictedPayload;
    const savedDpp = await this.dppRepository.save(dpp);

    return { dpp: savedDpp, warnings };
  }

  async createEvent(dppId: string, data: CreateEventDto): Promise<DppEvent> {
    const event = this.eventRepository.create({
      dppId,
      type: data.type as DppEventType,
      actor: data.actor,
      location: data.location || null,
      timestamp: data.timestamp || new Date(),
      data: data.data || {},
    });

    return await this.eventRepository.save(event);
  }

  async getDppEvents(dppId: string, clientId: string): Promise<DppEvent[]> {
    // Verify the DPP belongs to the client
    await this.getDppForClient(dppId, clientId);

    return await this.eventRepository.find({
      where: { dppId },
      order: { timestamp: "DESC" },
    });
  }

  async logAccess(dppId: string, view: DppAccessView, accessData: DppAccessLogData): Promise<void> {
    const log = this.accessLogRepository.create({
      dppId,
      view,
      ip: accessData.ip,
      userAgent: accessData.userAgent,
      userId: accessData.userId,
      endpoint: accessData.endpoint,
      timestamp: new Date(),
    });

    await this.accessLogRepository.save(log);
  }

  async getDppAccessLogs(dppId: string, clientId: string, limit = 100): Promise<DppAccessLog[]> {
    // Verify the DPP belongs to the client
    await this.getDppForClient(dppId, clientId);

    return await this.accessLogRepository.find({
      where: { dppId },
      order: { timestamp: "DESC" },
      take: limit,
    });
  }

  async listDpps(clientId: string, status?: DppStatus): Promise<Dpp[]> {
    const where: any = { clientId };
    if (status) {
      where.status = status;
    }

    return await this.dppRepository.find({
      where,
      order: { createdAt: "DESC" },
    });
  }

  async archiveDpp(id: string, clientId: string): Promise<Dpp> {
    const dpp = await this.getDppForClient(id, clientId);
    dpp.status = DppStatus.ARCHIVED;
    return await this.dppRepository.save(dpp);
  }
}