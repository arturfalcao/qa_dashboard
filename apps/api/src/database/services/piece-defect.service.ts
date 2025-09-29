import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { PieceDefect } from "../entities/piece-defect.entity";
import { ApparelPiece } from "../entities/apparel-piece.entity";

interface CreateDefectInput {
  pieceId: string;
  status: "pending_review" | "confirmed" | "rejected";
  audioTranscript?: string;
  flaggedAt: Date;
}

@Injectable()
export class PieceDefectService {
  constructor(
    @InjectRepository(PieceDefect)
    private readonly defectRepository: Repository<PieceDefect>,
    @InjectRepository(ApparelPiece)
    private readonly pieceRepository: Repository<ApparelPiece>,
  ) {}

  async findById(id: string): Promise<PieceDefect | null> {
    return this.defectRepository.findOne({
      where: { id },
      relations: ["piece", "piece.photos", "reviewer"],
    });
  }

  async findByPieceId(pieceId: string): Promise<PieceDefect[]> {
    return this.defectRepository.find({
      where: { pieceId },
      order: { flaggedAt: "DESC" },
    });
  }

  async findBySessionId(sessionId: string, status?: string): Promise<PieceDefect[]> {
    const query = this.defectRepository
      .createQueryBuilder("defect")
      .leftJoinAndSelect("defect.piece", "piece")
      .leftJoinAndSelect("piece.photos", "photos")
      .where("piece.inspection_session_id = :sessionId", { sessionId });

    if (status) {
      query.andWhere("defect.status = :status", { status });
    }

    return query.orderBy("defect.flagged_at", "DESC").getMany();
  }

  async findRecentByTenantId(tenantId: string, limit: number): Promise<PieceDefect[]> {
    return this.defectRepository
      .createQueryBuilder("defect")
      .leftJoinAndSelect("defect.piece", "piece")
      .leftJoinAndSelect("piece.photos", "photos")
      .leftJoinAndSelect("piece.session", "session")
      .leftJoinAndSelect("session.lot", "lot")
      .where("lot.tenant_id = :tenantId", { tenantId })
      .orderBy("defect.flagged_at", "DESC")
      .limit(limit)
      .getMany();
  }

  async create(input: CreateDefectInput): Promise<PieceDefect> {
    const defect = this.defectRepository.create(input);
    return this.defectRepository.save(defect);
  }

  async review(
    id: string,
    status: "confirmed" | "rejected",
    reviewedBy: string,
    notes?: string,
  ): Promise<PieceDefect> {
    await this.defectRepository.update(id, {
      status,
      reviewedBy,
      reviewedAt: new Date(),
      notes,
    });

    const defect = await this.findById(id);
    if (!defect) {
      throw new Error("Defect not found");
    }
    return defect;
  }

  async updatePieceStatusAfterReview(pieceId: string): Promise<void> {
    // Check if piece has any confirmed defects
    const confirmedDefects = await this.defectRepository.count({
      where: {
        pieceId,
        status: "confirmed",
      },
    });

    // Check if piece has any pending defects
    const pendingDefects = await this.defectRepository.count({
      where: {
        pieceId,
        status: "pending_review",
      },
    });

    let newStatus: "ok" | "defect" | "potential_defect" | "pending_review";

    if (confirmedDefects > 0) {
      newStatus = "defect";
    } else if (pendingDefects > 0) {
      newStatus = "pending_review";
    } else {
      newStatus = "ok";
    }

    await this.pieceRepository.update(pieceId, { status: newStatus });
  }
}