import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { ApparelPiece } from "../entities/apparel-piece.entity";

interface CreatePieceInput {
  inspectionSessionId: string;
  pieceNumber: number;
  status: "ok" | "defect" | "potential_defect" | "pending_review";
  inspectionStartedAt: Date;
}

@Injectable()
export class ApparelPieceService {
  constructor(
    @InjectRepository(ApparelPiece)
    private readonly pieceRepository: Repository<ApparelPiece>,
  ) {}

  async findById(id: string): Promise<ApparelPiece | null> {
    return this.pieceRepository.findOne({
      where: { id },
      relations: ["photos", "defects"],
    });
  }

  async findBySessionId(sessionId: string): Promise<ApparelPiece[]> {
    return this.pieceRepository.find({
      where: { inspectionSessionId: sessionId },
      relations: ["photos", "defects"],
      order: { pieceNumber: "ASC" },
    });
  }

  async create(input: CreatePieceInput): Promise<ApparelPiece> {
    const piece = this.pieceRepository.create(input);
    return this.pieceRepository.save(piece);
  }

  async updateStatus(
    id: string,
    status: "ok" | "defect" | "potential_defect" | "pending_review",
  ): Promise<void> {
    await this.pieceRepository.update(id, { status });
  }

  async complete(
    id: string,
    status: "ok" | "defect" | "potential_defect",
  ): Promise<void> {
    await this.pieceRepository.update(id, {
      status,
      inspectionCompletedAt: new Date(),
    });
  }
}