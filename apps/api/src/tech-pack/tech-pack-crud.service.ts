import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository, ILike } from "typeorm";
import { TechPack } from "../database/entities/tech-pack.entity";
import { Lot } from "../database/entities/lot.entity";
import { TechPackService } from "./tech-pack.service";
import { StorageService } from "../storage/storage.service";

interface FindAllOptions {
  status?: "pending" | "processing" | "completed" | "failed";
  search?: string;
  page?: number;
  limit?: number;
}

@Injectable()
export class TechPackCrudService {
  constructor(
    @InjectRepository(TechPack)
    private techPackRepository: Repository<TechPack>,
    @InjectRepository(Lot)
    private lotRepository: Repository<Lot>,
    private techPackService: TechPackService,
    private storageService: StorageService,
  ) {}

  async findAll(tenantId: string, options: FindAllOptions = {}) {
    const { status, search, page = 1, limit = 20 } = options;

    const queryBuilder = this.techPackRepository
      .createQueryBuilder("tp")
      .where("tp.tenant_id = :tenantId", { tenantId })
      .orderBy("tp.created_at", "DESC");

    if (status) {
      queryBuilder.andWhere("tp.status = :status", { status });
    }

    if (search) {
      queryBuilder.andWhere(
        "(tp.style_ref ILIKE :search OR tp.product_name ILIKE :search)",
        { search: `%${search}%` },
      );
    }

    const [items, total] = await queryBuilder
      .skip((page - 1) * limit)
      .take(limit)
      .getManyAndCount();

    return {
      items,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
    };
  }

  async findOne(tenantId: string, id: string): Promise<TechPack> {
    const techPack = await this.techPackRepository.findOne({
      where: { id, tenantId },
    });

    if (!techPack) {
      throw new NotFoundException(`Tech Pack with ID ${id} not found`);
    }

    return techPack;
  }

  async create(tenantId: string, data: Partial<TechPack>): Promise<TechPack> {
    const techPack = this.techPackRepository.create({
      ...data,
      tenantId,
      status: "pending",
    });

    return this.techPackRepository.save(techPack);
  }

  async update(
    tenantId: string,
    id: string,
    data: Partial<TechPack>,
  ): Promise<TechPack> {
    const techPack = await this.findOne(tenantId, id);

    Object.assign(techPack, data);

    return this.techPackRepository.save(techPack);
  }

  async delete(tenantId: string, id: string): Promise<void> {
    const techPack = await this.findOne(tenantId, id);

    // Check if any lots are using this tech pack
    const lotsCount = await this.lotRepository.count({
      where: { techPackId: id },
    });

    if (lotsCount > 0) {
      throw new Error(
        `Cannot delete Tech Pack: ${lotsCount} lot(s) are using it`,
      );
    }

    // Delete the file from storage if it exists
    if (techPack.fileKey) {
      try {
        await this.storageService.deleteFile(techPack.fileKey, "photos");
      } catch (error) {
        console.error("Error deleting tech pack file:", error);
      }
    }

    await this.techPackRepository.remove(techPack);
  }

  async uploadAndProcess(
    tenantId: string,
    file: Express.Multer.File,
    styleRef?: string,
  ): Promise<TechPack> {
    // Upload file to storage
    const fileKey = `tech-packs/${tenantId}/${Date.now()}-${file.originalname}`;
    await this.storageService.uploadFileWithKey(
      fileKey,
      file.buffer,
      file.mimetype,
      "photos",
    );

    // Create tech pack record
    const techPack = this.techPackRepository.create({
      tenantId,
      styleRef: styleRef || `TP-${Date.now()}`,
      fileKey,
      fileName: file.originalname,
      fileSize: file.size,
      status: "processing",
    });

    const savedTechPack = await this.techPackRepository.save(techPack);

    // Process the file asynchronously
    this.processFile(savedTechPack.id, tenantId, file.buffer, file.originalname, file.mimetype);

    return savedTechPack;
  }

  private async processFile(
    techPackId: string,
    tenantId: string,
    buffer: Buffer,
    fileName: string,
    mimeType: string,
  ): Promise<void> {
    try {
      // Extract structured data from file using OpenAI
      const extractedData = await this.techPackService.extractFromFile(
        buffer,
        fileName,
        mimeType,
      );

      // If OpenAI returned image URLs or base64 images, download and store them
      let images: Array<{
        url: string;
        key: string;
        pageNumber?: number;
        description?: string;
        type?: string;
      }> | undefined;

      if (extractedData.extractedImages && extractedData.extractedImages.length > 0) {
        console.log(`Processing ${extractedData.extractedImages.length} extracted images...`);
        images = [];

        for (let i = 0; i < extractedData.extractedImages.length; i++) {
          const img = extractedData.extractedImages[i];

          // If it's a base64 image, upload it to S3
          if (img.base64) {
            const result = await this.techPackService.uploadBase64Image(
              img.base64,
              img.mimeType || "image/png",
              tenantId,
              techPackId,
              i + 1,
            );
            if (result) {
              images.push({
                url: result.url,
                key: result.key,
                pageNumber: img.pageNumber,
                description: img.description,
                type: img.type,
              });
            }
          }
        }

        console.log(`Uploaded ${images.length} images to S3`);
      }

      // Process image regions (crop specific areas and associate with data)
      if (extractedData.imageRegions && extractedData.imageRegions.length > 0 && extractedData.pageImages) {
        console.log(`Processing ${extractedData.imageRegions.length} image regions...`);

        const fieldToUrlMap = await this.techPackService.processImageRegions(
          extractedData.pageImages,
          extractedData.imageRegions,
          tenantId,
          techPackId,
        );

        // Associate cropped image URLs with department data
        if (extractedData.departments && fieldToUrlMap.size > 0) {
          this.techPackService.associateImageUrls(extractedData.departments, fieldToUrlMap);
          console.log(`Associated ${fieldToUrlMap.size} cropped images with department data`);
        }

        // Also update the legacy flat fields (since they're what gets saved to DB)
        for (const [field, url] of fieldToUrlMap.entries()) {
          const match = field.match(/^(\w+)\[(\d+)\](?:\.(\w+))?$/);
          if (!match) continue;

          const [, arrayName, indexStr, subField] = match;
          const index = parseInt(indexStr, 10);

          // Update legacy flat fields
          if (arrayName === 'foldingInstructions' && extractedData.foldingInstructions?.[index]) {
            extractedData.foldingInstructions[index].imageUrl = url;
          } else if (arrayName === 'hangTags' && extractedData.hangTags?.[index]) {
            if (subField === 'front') {
              extractedData.hangTags[index].frontImageUrl = url;
            } else if (subField === 'back') {
              extractedData.hangTags[index].backImageUrl = url;
            } else {
              extractedData.hangTags[index].imageUrl = url;
            }
          } else if (arrayName === 'labels' && extractedData.labels?.[index]) {
            extractedData.labels[index].imageUrl = url;
          } else if (arrayName === 'packaging' && extractedData.packaging?.[index]) {
            if (subField === 'front') {
              extractedData.packaging[index].frontImageUrl = url;
            } else if (subField === 'back') {
              extractedData.packaging[index].backImageUrl = url;
            } else {
              extractedData.packaging[index].imageUrl = url;
            }
          } else if (arrayName === 'artwork' && extractedData.artwork?.[index]) {
            extractedData.artwork[index].imageUrl = url;
          } else if (arrayName === 'billOfMaterials' && extractedData.billOfMaterials?.[index]) {
            extractedData.billOfMaterials[index].swatchImageUrl = url;
          }
        }
      }

      await this.techPackRepository.update(techPackId, {
        status: "completed",
        processedAt: new Date(),
        styleRef: extractedData.styleRef || undefined,
        productName: extractedData.productName || undefined,
        season: extractedData.season || undefined,
        designer: extractedData.designer || undefined,
        sampleSize: extractedData.sampleSize || undefined,
        materialComposition: extractedData.materialComposition || undefined,
        colorways: extractedData.colorways || undefined,
        sizeSpecifications: extractedData.sizeSpecifications || undefined,
        measurementTolerances: extractedData.measurementTolerances || undefined,
        grading: extractedData.grading || undefined,
        constructionDetails: extractedData.constructionDetails || undefined,
        artwork: extractedData.artwork || undefined,
        fabricMap: extractedData.fabricMap || undefined,
        labels: extractedData.labels || undefined,
        hangTags: extractedData.hangTags || undefined,
        packaging: extractedData.packaging || undefined,
        foldingInstructions: extractedData.foldingInstructions || undefined,
        careInstructions: extractedData.careInstructions || undefined,
        billOfMaterials: extractedData.billOfMaterials || undefined,
        rawExtractedData: extractedData.rawExtractedData || undefined,
        images: images && images.length > 0 ? images : undefined,
      });

      console.log(`Tech Pack ${techPackId} processed successfully`);
    } catch (error) {
      console.error(`Error processing Tech Pack ${techPackId}:`, error);

      await this.techPackRepository.update(techPackId, {
        status: "failed",
        processingError: error.message,
      });
    }
  }

  async reprocess(tenantId: string, id: string): Promise<TechPack> {
    const techPack = await this.findOne(tenantId, id);

    if (!techPack.fileKey) {
      throw new Error("No file associated with this Tech Pack");
    }

    // Get the file from storage
    const fileBuffer = await this.storageService.getFileBuffer(techPack.fileKey, "photos");

    // Update status to processing
    await this.techPackRepository.update(id, {
      status: "processing",
      processingError: null,
    });

    // Determine mime type from file name
    const mimeType = techPack.fileName?.endsWith(".pdf")
      ? "application/pdf"
      : techPack.fileName?.endsWith(".xlsx")
      ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      : "application/octet-stream";

    // Process the file
    this.processFile(id, tenantId, fileBuffer, techPack.fileName || "unknown", mimeType);

    return this.findOne(tenantId, id);
  }

  async getLotsUsingTechPack(tenantId: string, id: string) {
    // Verify tech pack exists
    await this.findOne(tenantId, id);

    return this.lotRepository.find({
      where: { techPackId: id, tenantId },
      select: ["id", "styleRef", "status", "quantityTotal", "createdAt"],
      order: { createdAt: "DESC" },
    });
  }
}
