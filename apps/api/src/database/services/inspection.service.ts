import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Inspection } from "../entities/inspection.entity";

@Injectable()
export class InspectionService {
  constructor(
    @InjectRepository(Inspection)
    private readonly inspectionRepository: Repository<Inspection>,
  ) {}

  async getInspections(
    tenantId: string,
    since?: string,
    limit = 50,
  ): Promise<Inspection[]> {
    const query = this.inspectionRepository
      .createQueryBuilder("inspection")
      .innerJoinAndSelect("inspection.lot", "lot")
      .leftJoinAndSelect("lot.factory", "factory")
      .leftJoinAndSelect("inspection.defects", "defect")
      .leftJoinAndSelect("defect.defectType", "defectType")
      .leftJoinAndSelect("defect.photos", "photo")
      .leftJoinAndSelect("inspection.inspector", "inspector")
      .where("lot.tenantId = :tenantId", { tenantId })
      .orderBy("inspection.createdAt", "DESC")
      .take(limit);

    if (since) {
      query.andWhere("inspection.createdAt >= :since", { since: new Date(since) });
    }

    return query.getMany();
  }

  async createInspection(inspection: Partial<Inspection>): Promise<Inspection> {
    const newInspection = this.inspectionRepository.create(inspection);
    const saved = await this.inspectionRepository.save(newInspection);

    return this.inspectionRepository.findOne({
      where: { id: saved.id },
      relations: [
        "lot",
        "lot.factory",
        "defects",
        "defects.photos",
        "defects.defectType",
        "inspector",
      ],
    }) as Promise<Inspection>;
  }

  async ensureInspectionOwnership(tenantId: string, inspectionId: string): Promise<Inspection> {
    const inspection = await this.inspectionRepository.findOne({
      where: { id: inspectionId },
      relations: ["lot"],
    });

    if (!inspection || inspection.lot.tenantId !== tenantId) {
      throw new NotFoundException("Inspection not found for tenant");
    }

    return inspection;
  }
}
