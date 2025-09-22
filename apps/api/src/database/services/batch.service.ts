import {
  Injectable,
  NotFoundException,
  ForbiddenException,
} from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Batch } from "../entities/batch.entity";
import { Approval } from "../entities/approval.entity";
import { Inspection } from "../entities/inspection.entity";
import { Garment } from "../entities/garment.entity";
import {
  BatchStatus,
  ApprovalDecision,
  UserRole,
  EventType,
} from "@qa-dashboard/shared";
import { EventService } from "./event.service";

@Injectable()
export class BatchService {
  constructor(
    @InjectRepository(Batch)
    private batchRepository: Repository<Batch>,
    @InjectRepository(Approval)
    private approvalRepository: Repository<Approval>,
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    @InjectRepository(Garment)
    private garmentRepository: Repository<Garment>,
    private eventService: EventService,
  ) {}

  async getBatches(tenantId: string): Promise<any[]> {
    const batches = await this.batchRepository.find({
      where: { tenantId },
      relations: ["vendor", "style"],
      order: { createdAt: "DESC" },
    });

    // Get counts for each batch
    const batchesWithCounts = await Promise.all(
      batches.map(async (batch) => {
        const garmentCount = await this.garmentRepository.count({
          where: { batchId: batch.id },
        });

        const inspectionCount = await this.inspectionRepository.count({
          where: { tenantId, garment: { batchId: batch.id } },
        });

        const defectCount = await this.inspectionRepository.count({
          where: { tenantId, hasDefect: true, garment: { batchId: batch.id } },
        });

        return {
          ...batch,
          _count: {
            garments: garmentCount,
            inspections: inspectionCount,
            defects: defectCount,
          },
        };
      }),
    );

    return batchesWithCounts;
  }

  async getBatchById(tenantId: string, batchId: string): Promise<any> {
    const batch = await this.batchRepository.findOne({
      where: { id: batchId, tenantId },
      relations: ["vendor", "style", "approvals", "approvals.user"],
    });

    if (!batch) {
      throw new NotFoundException("Batch not found");
    }

    // Get aggregated data
    const garmentCount = await this.garmentRepository.count({
      where: { batchId: batch.id },
    });

    const inspectionCount = await this.inspectionRepository.count({
      where: { tenantId, garment: { batchId: batch.id } },
    });

    const defectCount = await this.inspectionRepository.count({
      where: { tenantId, hasDefect: true, garment: { batchId: batch.id } },
    });

    return {
      ...batch,
      _count: {
        garments: garmentCount,
        inspections: inspectionCount,
        defects: defectCount,
      },
    };
  }

  async approveBatch(
    tenantId: string,
    batchId: string,
    userId: string,
    userRole: UserRole,
    comment?: string,
  ): Promise<void> {
    if (userRole !== UserRole.CLIENT_ADMIN) {
      throw new ForbiddenException("Only client admins can approve batches");
    }

    const batch = await this.batchRepository.findOne({
      where: { id: batchId, tenantId },
    });

    if (!batch) {
      throw new NotFoundException("Batch not found");
    }

    if (batch.status !== BatchStatus.AWAITING_APPROVAL) {
      throw new ForbiddenException("Batch is not awaiting approval");
    }

    // Create approval record
    await this.approvalRepository.save({
      tenantId,
      batchId,
      decidedBy: userId,
      decision: ApprovalDecision.APPROVED,
      comment,
    });

    // Update batch status
    await this.batchRepository.update(batchId, {
      status: BatchStatus.APPROVED,
    });

    // Create event
    await this.eventService.createEvent(tenantId, EventType.BATCH_DECIDED, {
      batchId,
      decision: "approved",
      decidedBy: userId,
    });
  }

  async rejectBatch(
    tenantId: string,
    batchId: string,
    userId: string,
    userRole: UserRole,
    comment: string,
  ): Promise<void> {
    if (userRole !== UserRole.CLIENT_ADMIN) {
      throw new ForbiddenException("Only client admins can reject batches");
    }

    const batch = await this.batchRepository.findOne({
      where: { id: batchId, tenantId },
    });

    if (!batch) {
      throw new NotFoundException("Batch not found");
    }

    if (batch.status !== BatchStatus.AWAITING_APPROVAL) {
      throw new ForbiddenException("Batch is not awaiting approval");
    }

    // Create approval record
    await this.approvalRepository.save({
      tenantId,
      batchId,
      decidedBy: userId,
      decision: ApprovalDecision.REJECTED,
      comment,
    });

    // Update batch status
    await this.batchRepository.update(batchId, {
      status: BatchStatus.REJECTED,
    });

    // Create event
    await this.eventService.createEvent(tenantId, EventType.BATCH_DECIDED, {
      batchId,
      decision: "rejected",
      decidedBy: userId,
    });
  }

  async updateBatchStatus(batchId: string, status: BatchStatus): Promise<void> {
    await this.batchRepository.update(batchId, { status });
  }
}
