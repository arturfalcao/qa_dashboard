import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Defect } from "../entities/defect.entity";
import { Photo } from "../entities/photo.entity";

interface CreateDefectOptions {
  inspectionId: string;
  pieceCode?: string | null;
  note?: string | null;
  defectTypeId?: string | null;
  photos?: Array<{ url: string; annotation?: Record<string, unknown> | null }>;
}

@Injectable()
export class DefectService {
  constructor(
    @InjectRepository(Defect)
    private readonly defectRepository: Repository<Defect>,
    @InjectRepository(Photo)
    private readonly photoRepository: Repository<Photo>,
  ) {}

  async create(options: CreateDefectOptions): Promise<Defect> {
    const defect = this.defectRepository.create({
      inspectionId: options.inspectionId,
      pieceCode: options.pieceCode,
      note: options.note,
      defectTypeId: options.defectTypeId ?? null,
    });

    const saved = await this.defectRepository.save(defect);

    if (options.photos?.length) {
      const photos = options.photos.map((photo) =>
        this.photoRepository.create({
          defectId: saved.id,
          url: photo.url,
          annotation: photo.annotation ?? null,
        }),
      );
      await this.photoRepository.save(photos);
    }

    return this.defectRepository.findOne({
      where: { id: saved.id },
      relations: ["photos"],
    }) as Promise<Defect>;
  }

  async ensureBelongsToInspection(defectId: string, inspectionId: string): Promise<Defect> {
    const defect = await this.defectRepository.findOne({
      where: { id: defectId, inspectionId },
      relations: ["photos"],
    });
    if (!defect) {
      throw new NotFoundException("Defect not found");
    }
    return defect;
  }

  async countByTenantId(tenantId: string): Promise<number> {
    const count = await this.defectRepository
      .createQueryBuilder("defect")
      .innerJoin("defect.inspection", "inspection")
      .innerJoin("inspection.lot", "lot")
      .where("lot.clientId IN (SELECT id FROM clients WHERE tenantId = :tenantId)", { tenantId })
      .getCount();
    return count;
  }
}
