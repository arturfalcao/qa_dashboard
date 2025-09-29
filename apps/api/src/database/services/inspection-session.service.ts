import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository, IsNull } from "typeorm";
import { InspectionSession } from "../entities/inspection-session.entity";

interface CreateSessionInput {
  lotId: string;
  deviceId: string;
  operatorId: string;
  startedAt: Date;
}

@Injectable()
export class InspectionSessionService {
  constructor(
    @InjectRepository(InspectionSession)
    private readonly sessionRepository: Repository<InspectionSession>,
  ) {}

  async findById(id: string): Promise<InspectionSession | null> {
    return this.sessionRepository.findOne({
      where: { id },
    });
  }

  async findByIdWithDetails(id: string): Promise<InspectionSession | null> {
    return this.sessionRepository.findOne({
      where: { id },
      relations: ["pieces", "pieces.photos", "pieces.defects"],
    });
  }

  async findByLotId(lotId: string): Promise<InspectionSession[]> {
    return this.sessionRepository.find({
      where: { lotId },
      relations: ["device", "operator"],
      order: { startedAt: "DESC" },
    });
  }

  async findActiveByLotId(lotId: string): Promise<InspectionSession | null> {
    return this.sessionRepository.findOne({
      where: {
        lotId,
        endedAt: IsNull(),
      },
    });
  }

  async findActiveByTenantId(tenantId: string): Promise<InspectionSession[]> {
    return this.sessionRepository
      .createQueryBuilder("session")
      .leftJoinAndSelect("session.lot", "lot")
      .leftJoinAndSelect("session.operator", "operator")
      .leftJoinAndSelect("session.device", "device")
      .where("lot.tenant_id = :tenantId", { tenantId })
      .andWhere("session.ended_at IS NULL")
      .orderBy("session.started_at", "DESC")
      .getMany();
  }

  async create(input: CreateSessionInput): Promise<InspectionSession> {
    const session = this.sessionRepository.create(input);
    return this.sessionRepository.save(session);
  }

  async pause(id: string): Promise<void> {
    await this.sessionRepository.update(id, { pausedAt: new Date() });
  }

  async resume(id: string): Promise<void> {
    await this.sessionRepository.update(id, { pausedAt: null });
  }

  async end(id: string): Promise<InspectionSession> {
    await this.sessionRepository.update(id, { endedAt: new Date() });
    const session = await this.findById(id);
    if (!session) {
      throw new NotFoundException("Session not found");
    }
    return session;
  }

  async incrementPiece(
    id: string,
    status: "ok" | "defect" | "potential_defect",
  ): Promise<void> {
    const session = await this.findById(id);
    if (!session) {
      throw new NotFoundException("Session not found");
    }

    const updates: any = {
      piecesInspected: session.piecesInspected + 1,
    };

    if (status === "ok") {
      updates.piecesOk = session.piecesOk + 1;
    } else if (status === "defect") {
      updates.piecesDefect = session.piecesDefect + 1;
    } else if (status === "potential_defect") {
      updates.piecesPotentialDefect = session.piecesPotentialDefect + 1;
    }

    await this.sessionRepository.update(id, updates);
  }
}