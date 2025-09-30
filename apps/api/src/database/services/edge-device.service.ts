import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { EdgeDevice } from "../entities/edge-device.entity";

interface CreateEdgeDeviceInput {
  tenantId?: string | null;
  name: string;
  secretKey: string;
  workbenchNumber: number;
  status: "active" | "inactive" | "maintenance";
}

@Injectable()
export class EdgeDeviceService {
  constructor(
    @InjectRepository(EdgeDevice)
    private readonly edgeDeviceRepository: Repository<EdgeDevice>,
  ) {}

  async findAll(): Promise<EdgeDevice[]> {
    return this.edgeDeviceRepository.find({
      relations: ["tenant", "assignedOperator"],
      order: { workbenchNumber: "ASC" },
    });
  }

  async findByTenantId(tenantId: string): Promise<EdgeDevice[]> {
    return this.edgeDeviceRepository.find({
      where: { tenantId },
      relations: ["assignedOperator"],
      order: { workbenchNumber: "ASC" },
    });
  }

  async findById(id: string): Promise<EdgeDevice | null> {
    return this.edgeDeviceRepository.findOne({
      where: { id },
      relations: ["tenant", "assignedOperator"],
    });
  }

  async findBySecretKey(secretKey: string): Promise<EdgeDevice | null> {
    return this.edgeDeviceRepository.findOne({
      where: { secretKey },
      relations: ["tenant"],
    });
  }

  async create(input: CreateEdgeDeviceInput): Promise<EdgeDevice> {
    const device = this.edgeDeviceRepository.create(input);
    return this.edgeDeviceRepository.save(device);
  }

  async updateStatus(
    id: string,
    status: "active" | "inactive" | "maintenance",
  ): Promise<void> {
    await this.edgeDeviceRepository.update(id, { status });
  }

  async updateLastSeen(id: string): Promise<void> {
    await this.edgeDeviceRepository.update(id, { lastSeenAt: new Date() });
  }

  async assignOperator(id: string, operatorId: string | null): Promise<void> {
    await this.edgeDeviceRepository.update(id, { assignedOperatorId: operatorId });
  }

  async delete(id: string): Promise<void> {
    await this.edgeDeviceRepository.delete(id);
  }
}