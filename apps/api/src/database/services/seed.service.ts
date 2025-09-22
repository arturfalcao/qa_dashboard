import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { Tenant } from "../entities/tenant.entity";
import { User } from "../entities/user.entity";
import { Vendor } from "../entities/vendor.entity";
import { Style } from "../entities/style.entity";
import { Batch } from "../entities/batch.entity";
import { Garment } from "../entities/garment.entity";
import { Inspection } from "../entities/inspection.entity";
import { Event } from "../entities/event.entity";
import { Approval } from "../entities/approval.entity";
import { InspectionPhoto } from "../entities/inspection-photo.entity";
import { PhotoAnnotation } from "../entities/photo-annotation.entity";
import { BatchProcessProgress } from "../entities/batch-process-progress.entity";
import {
  UserRole,
  BatchStatus,
  DefectType,
  DefectSeverity,
  ProcessStation,
  EventType,
  ApprovalDecision,
  PhotoAngle,
} from "@qa-dashboard/shared";
import { StorageService } from "../../storage/storage.service";
import {
  loadSampleImages,
  getRandomNormalImage,
  getRandomDefectImage,
} from "../../common/sample-images";

interface ProcessTimelineEntry {
  station: ProcessStation;
  startOffsetHours: number;
  durationHours: number;
  notes?: string;
  qualityScore?: number;
}

interface BatchSeedConfig {
  poNumber: string;
  vendorCode: string;
  styleCode: string;
  quantity: number;
  status: BatchStatus;
  priority: "low" | "normal" | "high" | "urgent";
  currentStation: ProcessStation;
  estimatedCompletionOffsetHours: number;
  startDaysAgo: number;
  inspectionStartDaysAgo: number;
  inspectionSpanHours: number;
  coverage: number;
  defectRate: number;
  sampleGarments: number;
  awaitingApprovalEvent?: boolean;
  approval?: {
    decision: ApprovalDecision;
    comment: string;
    decidedDaysAgo: number;
  };
  processTimeline: ProcessTimelineEntry[];
  stationPool?: ProcessStation[];
  inspectorPool?: string[];
}

const INSPECTOR_NAMES = [
  "Ana Ribeiro",
  "Miguel Costa",
  "Sofia Martins",
  "João Almeida",
  "Rita Gomes",
  "Diogo Faria",
  "Beatriz Pires",
  "Inês Correia",
];

const PASS_NOTES = [
  "AI model confirmed stitches within tolerance levels.",
  "Measurement variance below 0.4 cm. Passed automatically.",
  "No color deviation detected. Fabric lot approved.",
  "Seam tension balanced across garment. Cleared for packing.",
  "Smart sensors report excellent finishing quality.",
  "Inspection matched reference sample with 99% confidence.",
];

const DEFECT_NOTES: Record<DefectType, string[]> = {
  [DefectType.STAIN]: [
    "Localized stain detected near front panel.",
    "Surface contamination visible on inspection camera.",
  ],
  [DefectType.STITCHING]: [
    "Irregular stitching pattern observed along side seam.",
    "Loose thread cluster triggered automatic rejection.",
  ],
  [DefectType.MISPRINT]: [
    "Logo placement deviates from reference artwork.",
    "Screen print misalignment detected on chest area.",
  ],
  [DefectType.MEASUREMENT]: [
    "Measurement variance exceeded tolerance on sleeve length.",
    "Graded size out of specification for waist circumference.",
  ],
  [DefectType.FABRIC_DEFECT]: [
    "Fabric snag recorded on upper torso panel.",
    "Inconsistent weave density detected on garment surface.",
  ],
  [DefectType.HARDWARE_ISSUE]: [
    "Zipper glide test failed near top stop.",
    "Button torque below expected threshold.",
  ],
  [DefectType.DISCOLORATION]: [
    "Color drift detected compared to control swatch.",
    "Slight discoloration along hem fold.",
  ],
  [DefectType.TEAR_DAMAGE]: [
    "Micro tear detected during stress test at seam junction.",
    "Fabric integrity compromised near care label.",
  ],
  [DefectType.OTHER]: [
    "General quality issue flagged for manual review.",
    "Anomaly detected outside standard categories.",
  ],
};

const DEFECT_DISTRIBUTION: Array<{ value: DefectType; weight: number }> = [
  { value: DefectType.STITCHING, weight: 0.28 },
  { value: DefectType.MEASUREMENT, weight: 0.22 },
  { value: DefectType.STAIN, weight: 0.18 },
  { value: DefectType.MISPRINT, weight: 0.14 },
  { value: DefectType.FABRIC_DEFECT, weight: 0.08 },
  { value: DefectType.HARDWARE_ISSUE, weight: 0.05 },
  { value: DefectType.DISCOLORATION, weight: 0.03 },
  { value: DefectType.TEAR_DAMAGE, weight: 0.02 },
];

const SEVERITY_DISTRIBUTION: Array<{ value: DefectSeverity; weight: number }> =
  [
    { value: DefectSeverity.CRITICAL, weight: 0.16 },
    { value: DefectSeverity.MAJOR, weight: 0.46 },
    { value: DefectSeverity.MINOR, weight: 0.38 },
  ];

const DEFAULT_STATION_POOL: ProcessStation[] = [
  ProcessStation.INITIAL_INSPECTION,
  ProcessStation.QUALITY_CHECK,
  ProcessStation.FINAL_INSPECTION,
  ProcessStation.PACKING,
];

const GARMENT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"];
const GARMENT_COLORS = [
  "Atlantic Navy",
  "Fog Grey",
  "Crimson",
  "Emerald",
  "Charcoal",
  "Ivory",
  "Ocean Blue",
  "Sunset Gold",
];

@Injectable()
export class SeedService {
  private sampleImagesLoaded = false;

  constructor(
    @InjectRepository(Tenant)
    private tenantRepository: Repository<Tenant>,
    @InjectRepository(User)
    private userRepository: Repository<User>,
    @InjectRepository(Vendor)
    private vendorRepository: Repository<Vendor>,
    @InjectRepository(Style)
    private styleRepository: Repository<Style>,
    @InjectRepository(Batch)
    private batchRepository: Repository<Batch>,
    @InjectRepository(Garment)
    private garmentRepository: Repository<Garment>,
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    @InjectRepository(Event)
    private eventRepository: Repository<Event>,
    @InjectRepository(Approval)
    private approvalRepository: Repository<Approval>,
    @InjectRepository(InspectionPhoto)
    private inspectionPhotoRepository: Repository<InspectionPhoto>,
    @InjectRepository(PhotoAnnotation)
    private photoAnnotationRepository: Repository<PhotoAnnotation>,
    @InjectRepository(BatchProcessProgress)
    private processProgressRepository: Repository<BatchProcessProgress>,
    private storageService: StorageService,
  ) {}

  async seedData(): Promise<void> {
    console.log("Starting seed process...");
    this.ensureSampleImagesLoaded();

    const tenant1 = await this.createTenant("Hey Marly", "heymarly");
    const tenant2 = await this.createTenant("Sample Brand", "samplebrand");

    await this.seedTenant(tenant1, "heymarly");
    await this.seedTenant(tenant2, "samplebrand");

    console.log("Seed completed successfully!");
  }

  private ensureSampleImagesLoaded(): void {
    if (this.sampleImagesLoaded) {
      return;
    }

    const collection = loadSampleImages();
    if (collection.normal.length === 0 && collection.defect.length === 0) {
      console.warn(
        "[SeedService] No sample garment images found. Placeholder assets will be used.",
      );
    } else {
      console.log(
        `[SeedService] Loaded ${collection.normal.length} reference garments and ${collection.defect.length} defect samples.`,
      );
    }

    this.sampleImagesLoaded = true;
  }

  private async seedTenant(tenant: Tenant, slug: string): Promise<void> {
    await this.createUsers(tenant.id);
    const adminUser = await this.userRepository.findOne({
      where: { tenantId: tenant.id, role: UserRole.CLIENT_ADMIN },
    });

    const { vendors, styles } = await this.createVendorsAndStyles(tenant.id);
    const batchConfigs = this.getBatchSeedConfigs(slug);
    const batchMap = await this.createBatches(
      tenant.id,
      vendors,
      styles,
      batchConfigs,
    );

    await this.seedProcessTimelines(tenant.id, batchConfigs, batchMap);
    await this.seedGarmentsAndInspections(
      tenant,
      batchConfigs,
      batchMap,
      adminUser ?? null,
    );
    await this.seedBatchDecisions(
      tenant,
      batchConfigs,
      batchMap,
      adminUser ?? null,
    );
  }

  private async createTenant(name: string, slug: string): Promise<Tenant> {
    const existingTenant = await this.tenantRepository.findOne({
      where: { slug },
    });
    if (existingTenant) {
      console.log(`Tenant ${name} already exists`);
      return existingTenant;
    }

    const tenant = this.tenantRepository.create({ name, slug });
    await this.tenantRepository.save(tenant);
    console.log(`Created tenant: ${name}`);
    return tenant;
  }

  private async createUsers(tenantId: string): Promise<void> {
    const tenant = await this.tenantRepository.findOne({
      where: { id: tenantId },
    });
    const domain =
      tenant?.slug === "heymarly" ? "marly.example" : "brand.example";

    const users = [
      {
        email: `admin@${domain}`,
        password: "demo1234",
        role: UserRole.CLIENT_ADMIN,
      },
      {
        email: `viewer@${domain}`,
        password: "demo1234",
        role: UserRole.CLIENT_VIEWER,
      },
    ];

    for (const userData of users) {
      const existingUser = await this.userRepository.findOne({
        where: { email: userData.email, tenantId },
      });

      if (existingUser) {
        continue;
      }

      const passwordHash = await bcrypt.hash(userData.password, 10);
      const user = this.userRepository.create({
        tenantId,
        email: userData.email,
        passwordHash,
        role: userData.role,
        isActive: true,
      });

      await this.userRepository.save(user);
      console.log(`Created user: ${userData.email}`);
    }
  }

  private async createVendorsAndStyles(
    tenantId: string,
  ): Promise<{ vendors: Vendor[]; styles: Style[] }> {
    const vendorSeeds = [
      { name: "Premium Textiles Co.", code: "PTC" },
      { name: "Global Garments Ltd.", code: "GGL" },
      { name: "Fashion Forward Inc.", code: "FFI" },
      { name: "Lusitania Stitchworks", code: "LSW" },
      { name: "Atlantic Apparel Group", code: "AAG" },
    ];

    const styleSeeds = [
      { styleCode: "T-001", description: "Classic Cotton T-Shirt" },
      { styleCode: "H-002", description: "Premium Fleece Hoodie" },
      { styleCode: "J-003", description: "Heritage Denim Jacket" },
      { styleCode: "P-004", description: "Tailored Piqué Polo" },
      { styleCode: "D-005", description: "Lightweight Day Dress" },
      { styleCode: "S-006", description: "Fine Gauge Sweater" },
    ];

    const vendors: Vendor[] = [];
    for (const vendorSeed of vendorSeeds) {
      let vendor = await this.vendorRepository.findOne({
        where: { tenantId, code: vendorSeed.code },
      });

      if (vendor) {
        vendor.name = vendorSeed.name;
      } else {
        vendor = this.vendorRepository.create({ tenantId, ...vendorSeed });
      }

      vendor = await this.vendorRepository.save(vendor);
      vendors.push(vendor);
    }

    const styles: Style[] = [];
    for (const styleSeed of styleSeeds) {
      let style = await this.styleRepository.findOne({
        where: { tenantId, styleCode: styleSeed.styleCode },
      });

      if (style) {
        style.description = styleSeed.description;
      } else {
        style = this.styleRepository.create({ tenantId, ...styleSeed });
      }

      style = await this.styleRepository.save(style);
      styles.push(style);
    }

    return { vendors, styles };
  }

  private async createBatches(
    tenantId: string,
    vendors: Vendor[],
    styles: Style[],
    configs: BatchSeedConfig[],
  ): Promise<Map<string, Batch>> {
    const vendorByCode = new Map(
      vendors.map((vendor) => [vendor.code, vendor]),
    );
    const styleByCode = new Map(
      styles.map((style) => [style.styleCode, style]),
    );
    const batchMap = new Map<string, Batch>();

    for (const config of configs) {
      const vendor = vendorByCode.get(config.vendorCode);
      const style = styleByCode.get(config.styleCode);

      if (!vendor || !style) {
        console.warn(`Missing vendor or style for batch ${config.poNumber}`);
        continue;
      }

      const estimatedCompletionTime = new Date(
        Date.now() + config.estimatedCompletionOffsetHours * 60 * 60 * 1000,
      );

      let batch = await this.batchRepository.findOne({
        where: { tenantId, poNumber: config.poNumber },
        relations: ["vendor", "style"],
      });

      if (batch) {
        batch.quantity = config.quantity;
        batch.status = config.status;
        batch.vendorId = vendor.id;
        batch.styleId = style.id;
        batch.currentStation = config.currentStation;
        batch.priority = config.priority;
        batch.estimatedCompletionTime = estimatedCompletionTime;
        batch.vendor = vendor;
        batch.style = style;
        batch = await this.batchRepository.save(batch);
        console.log(`Updated batch: ${config.poNumber}`);
      } else {
        batch = this.batchRepository.create({
          tenantId,
          vendorId: vendor.id,
          styleId: style.id,
          poNumber: config.poNumber,
          quantity: config.quantity,
          status: config.status,
          currentStation: config.currentStation,
          priority: config.priority,
          estimatedCompletionTime,
        });
        batch = await this.batchRepository.save(batch);
        batch.vendor = vendor;
        batch.style = style;
        console.log(`Created batch: ${config.poNumber}`);
      }

      batchMap.set(config.poNumber, batch);
    }

    return batchMap;
  }

  private async seedProcessTimelines(
    tenantId: string,
    configs: BatchSeedConfig[],
    batchMap: Map<string, Batch>,
  ): Promise<void> {
    for (const config of configs) {
      const batch = batchMap.get(config.poNumber);
      if (!batch || config.processTimeline.length === 0) {
        continue;
      }

      const existing = await this.processProgressRepository.count({
        where: { tenantId, batchId: batch.id },
      });

      if (existing > 0) {
        continue;
      }

      const startBase = new Date();
      startBase.setDate(startBase.getDate() - config.startDaysAgo);

      const entries = config.processTimeline.map((timeline) => {
        const startedAt = new Date(
          startBase.getTime() + timeline.startOffsetHours * 60 * 60 * 1000,
        );
        const completedAt = new Date(
          startedAt.getTime() + timeline.durationHours * 60 * 60 * 1000,
        );

        return this.processProgressRepository.create({
          tenantId,
          batchId: batch.id,
          station: timeline.station,
          startedAt,
          completedAt,
          notes: timeline.notes,
          qualityScore: timeline.qualityScore,
        });
      });

      if (entries.length) {
        await this.processProgressRepository.save(entries);
      }
    }
  }

  private async seedGarmentsAndInspections(
    tenant: Tenant,
    configs: BatchSeedConfig[],
    batchMap: Map<string, Batch>,
    adminUser: User | null,
  ): Promise<void> {
    for (const config of configs) {
      const batch = batchMap.get(config.poNumber);
      if (!batch) {
        continue;
      }

      const garments = await this.ensureGarments(
        tenant.id,
        batch.id,
        Math.min(config.sampleGarments, config.quantity),
      );

      const existingInspectionCount = await this.inspectionRepository
        .createQueryBuilder("inspection")
        .leftJoin("inspection.garment", "garment")
        .where("inspection.tenantId = :tenantId", { tenantId: tenant.id })
        .andWhere("garment.batchId = :batchId", { batchId: batch.id })
        .getCount();

      if (existingInspectionCount > 0) {
        console.log(
          `Inspections already exist for batch ${batch.poNumber}, skipping generation.`,
        );
        continue;
      }

      await this.generateInspectionsForBatch(
        tenant,
        batch,
        garments,
        config,
        adminUser,
      );
    }
  }

  private async ensureGarments(
    tenantId: string,
    batchId: string,
    targetCount: number,
  ): Promise<Garment[]> {
    const existingGarments = await this.garmentRepository.find({
      where: { batchId },
      order: { serial: "ASC" },
    });

    if (existingGarments.length >= targetCount) {
      return existingGarments;
    }

    const garmentsToCreate: Garment[] = [];
    for (let i = existingGarments.length + 1; i <= targetCount; i++) {
      const garment = this.garmentRepository.create({
        tenantId,
        batchId,
        serial: `G${String(i).padStart(4, "0")}`,
        size: this.randomChoice(GARMENT_SIZES),
        color: this.randomChoice(GARMENT_COLORS),
      });
      garmentsToCreate.push(garment);
    }

    const saved = await this.garmentRepository.save(garmentsToCreate);
    console.log(`Created ${saved.length} garments for batch ${batchId}`);
    return [...existingGarments, ...saved];
  }

  private async generateInspectionsForBatch(
    tenant: Tenant,
    batch: Batch,
    garments: Garment[],
    config: BatchSeedConfig,
    adminUser: User | null,
  ): Promise<void> {
    if (garments.length === 0) {
      return;
    }

    const coverageCount = Math.max(
      8,
      Math.floor(garments.length * config.coverage),
    );
    const shuffledGarments = [...garments];
    this.shuffleArray(shuffledGarments);
    const selectedGarments = shuffledGarments.slice(0, coverageCount);

    const inspectionStart = new Date();
    inspectionStart.setDate(
      inspectionStart.getDate() - config.inspectionStartDaysAgo,
    );
    const totalSpanMs = config.inspectionSpanHours * 60 * 60 * 1000;

    const defectTarget = Math.min(
      Math.max(1, Math.floor(selectedGarments.length * config.defectRate)),
      selectedGarments.length,
    );
    const defectIndices = new Set<number>();
    while (defectIndices.size < defectTarget) {
      defectIndices.add(Math.floor(Math.random() * selectedGarments.length));
    }

    const stationPool = config.stationPool ?? DEFAULT_STATION_POOL;
    const inspectorPool = config.inspectorPool ?? INSPECTOR_NAMES;

    const inspectionEntities: Inspection[] = [];
    const photoSeeds: Array<{
      inspectionIndex: number;
      angle: PhotoAngle;
      key: string;
      capturedAt: Date;
      annotation?: {
        x: number;
        y: number;
        comment: string;
        defectType: DefectType;
        severity: DefectSeverity;
      };
    }> = [];
    const defectEventSeeds: Array<{
      inspectionIndex: number;
      garmentId: string;
      garmentSerial: string;
      defectType: DefectType;
      severity: DefectSeverity;
      processStation: ProcessStation;
    }> = [];

    for (let index = 0; index < selectedGarments.length; index++) {
      const garment = selectedGarments[index];
      const hasDefect = defectIndices.has(index);

      let defectType: DefectType | undefined;
      let defectSeverity: DefectSeverity | undefined;

      if (hasDefect) {
        defectType = this.randomDefectType();
        defectSeverity = this.randomSeverity();
      }

      const progressRatio =
        selectedGarments.length > 1 ? index / (selectedGarments.length - 1) : 1;
      let inspectedAt = new Date(
        inspectionStart.getTime() + progressRatio * totalSpanMs,
      );
      inspectedAt = new Date(
        inspectedAt.getTime() + (Math.random() - 0.5) * 2 * 60 * 60 * 1000,
      );
      if (inspectedAt > new Date()) {
        inspectedAt = new Date(Date.now() - Math.random() * 60 * 60 * 1000);
      }

      const processStation = this.randomChoice(stationPool);
      const assignedWorker = this.randomChoice(inspectorPool);
      const temperature = Math.round((21 + Math.random() * 3) * 10) / 10;
      const humidity = Math.round((45 + Math.random() * 10) * 10) / 10;
      const lightingLevel = Math.round((650 + Math.random() * 120) * 10) / 10;
      const qualityScore = hasDefect
        ? Math.floor(65 + Math.random() * 18)
        : Math.floor(92 + Math.random() * 7);

      const notes =
        hasDefect && defectType && defectSeverity
          ? this.composeDefectNote(defectType, defectSeverity, garment.serial)
          : this.randomChoice(PASS_NOTES);

      const frontKey = await this.uploadSampleImage(
        tenant.id,
        hasDefect,
        defectType,
      );
      const backKey = await this.uploadSampleImage(tenant.id, false);
      const detailKey = hasDefect
        ? await this.uploadSampleImage(tenant.id, true, defectType)
        : undefined;

      const inspectionIndex = inspectionEntities.length;
      const inspection = this.inspectionRepository.create({
        tenantId: tenant.id,
        garmentId: garment.id,
        hasDefect,
        defectType,
        defectSeverity,
        notes,
        photoKeyBefore: frontKey,
        photoKeyAfter: hasDefect ? backKey : backKey,
        processStation,
        assignedWorker,
        temperature,
        humidity,
        lightingLevel,
        qualityScore,
        inspectedAt,
      });
      inspectionEntities.push(inspection);

      photoSeeds.push({
        inspectionIndex,
        angle: PhotoAngle.FRONT,
        key: frontKey,
        capturedAt: new Date(inspectedAt.getTime() - 5 * 60 * 1000),
      });
      photoSeeds.push({
        inspectionIndex,
        angle: PhotoAngle.BACK,
        key: backKey,
        capturedAt: new Date(inspectedAt.getTime() - 3 * 60 * 1000),
      });

      if (detailKey && defectType && defectSeverity) {
        const annotationChance = Math.random() < 0.65 && adminUser;
        photoSeeds.push({
          inspectionIndex,
          angle: PhotoAngle.DETAIL_MACRO,
          key: detailKey,
          capturedAt: new Date(inspectedAt.getTime() - 2 * 60 * 1000),
          annotation: annotationChance
            ? {
                x: Math.round((40 + Math.random() * 20) * 100) / 100,
                y: Math.round((40 + Math.random() * 20) * 100) / 100,
                comment: `Focus ${defectType.replace("_", " ")} (${defectSeverity.toLowerCase()})`,
                defectType,
                severity: defectSeverity,
              }
            : undefined,
        });
      }

      if (hasDefect && defectType && defectSeverity) {
        defectEventSeeds.push({
          inspectionIndex,
          garmentId: garment.id,
          garmentSerial: garment.serial,
          defectType,
          severity: defectSeverity,
          processStation,
        });
      }
    }

    if (inspectionEntities.length === 0) {
      return;
    }

    const savedInspections =
      await this.inspectionRepository.save(inspectionEntities);

    const events: Event[] = [];
    for (const eventSeed of defectEventSeeds) {
      const inspection = savedInspections[eventSeed.inspectionIndex];
      events.push(
        this.eventRepository.create({
          tenantId: tenant.id,
          type: EventType.DEFECT_DETECTED,
          payload: {
            inspectionId: inspection.id,
            garmentId: eventSeed.garmentId,
            garmentSerial: eventSeed.garmentSerial,
            batchId: batch.id,
            defectType: eventSeed.defectType,
            severity: eventSeed.severity,
            processStation: eventSeed.processStation,
          },
        }),
      );
    }
    if (events.length) {
      await this.eventRepository.save(events);
    }

    const photoEntities: InspectionPhoto[] = [];
    const annotationSeeds: Array<{
      photoEntityIndex: number;
      annotation: {
        x: number;
        y: number;
        comment: string;
        defectType: DefectType;
        severity: DefectSeverity;
      };
    }> = [];

    for (const seed of photoSeeds) {
      const inspection = savedInspections[seed.inspectionIndex];
      const photo = this.inspectionPhotoRepository.create({
        tenantId: tenant.id,
        inspectionId: inspection.id,
        angle: seed.angle,
        photoKey: seed.key,
        capturedAt: seed.capturedAt,
      });
      const photoEntityIndex = photoEntities.length;
      photoEntities.push(photo);

      if (seed.annotation) {
        annotationSeeds.push({ photoEntityIndex, annotation: seed.annotation });
      }
    }

    const savedPhotos =
      await this.inspectionPhotoRepository.save(photoEntities);

    if (adminUser && annotationSeeds.length) {
      const annotations: PhotoAnnotation[] = [];
      for (const seed of annotationSeeds) {
        const photo = savedPhotos[seed.photoEntityIndex];
        annotations.push(
          this.photoAnnotationRepository.create({
            tenantId: tenant.id,
            photoId: photo.id,
            createdBy: adminUser.id,
            x: seed.annotation.x,
            y: seed.annotation.y,
            comment: seed.annotation.comment,
            defectType: seed.annotation.defectType,
            defectSeverity: seed.annotation.severity,
          }),
        );
      }

      if (annotations.length) {
        await this.photoAnnotationRepository.save(annotations);
      }
    }

    console.log(
      `Generated ${savedInspections.length} inspections for batch ${batch.poNumber}`,
    );
  }

  private async seedBatchDecisions(
    tenant: Tenant,
    configs: BatchSeedConfig[],
    batchMap: Map<string, Batch>,
    adminUser: User | null,
  ): Promise<void> {
    if (!adminUser) {
      console.warn(
        `No admin user found for tenant ${tenant.slug}. Skipping approval seeding.`,
      );
      return;
    }

    const existingApprovals = await this.approvalRepository.count({
      where: { tenantId: tenant.id },
    });
    if (existingApprovals > 0) {
      console.log(
        `Approvals already exist for tenant ${tenant.slug}, skipping decision generation.`,
      );
      return;
    }

    const approvals: Approval[] = [];
    const events: Event[] = [];

    for (const config of configs) {
      const batch = batchMap.get(config.poNumber);
      if (!batch) {
        continue;
      }

      if (config.awaitingApprovalEvent) {
        events.push(
          this.eventRepository.create({
            tenantId: tenant.id,
            type: EventType.BATCH_AWAITING_APPROVAL,
            payload: {
              batchId: batch.id,
              poNumber: batch.poNumber,
              vendor: batch.vendor?.name,
              quantity: batch.quantity,
            },
          }),
        );
      }

      if (config.approval) {
        const decidedAt = new Date();
        decidedAt.setDate(decidedAt.getDate() - config.approval.decidedDaysAgo);

        approvals.push(
          this.approvalRepository.create({
            tenantId: tenant.id,
            batchId: batch.id,
            decidedBy: adminUser.id,
            decision: config.approval.decision,
            comment: config.approval.comment,
            decidedAt,
          }),
        );

        events.push(
          this.eventRepository.create({
            tenantId: tenant.id,
            type: EventType.BATCH_DECIDED,
            payload: {
              batchId: batch.id,
              poNumber: batch.poNumber,
              decision: config.approval.decision,
              decidedBy: adminUser.email,
              comment: config.approval.comment,
            },
          }),
        );

        await this.batchRepository
          .createQueryBuilder()
          .update(Batch)
          .set({
            updatedAt: new Date(decidedAt.getTime() - 4 * 60 * 60 * 1000),
          })
          .where("id = :id", { id: batch.id })
          .execute();
      }
    }

    if (approvals.length) {
      await this.approvalRepository.save(approvals);
    }

    if (events.length) {
      await this.eventRepository.save(events);
    }
  }

  private randomChoice<T>(items: T[]): T {
    return items[Math.floor(Math.random() * items.length)];
  }

  private shuffleArray<T>(items: T[]): void {
    for (let i = items.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [items[i], items[j]] = [items[j], items[i]];
    }
  }

  private weightedRandom<T>(items: Array<{ value: T; weight: number }>): T {
    const totalWeight = items.reduce((sum, item) => sum + item.weight, 0);
    const target = Math.random() * totalWeight;

    let cumulative = 0;
    for (const item of items) {
      cumulative += item.weight;
      if (target <= cumulative) {
        return item.value;
      }
    }

    return items[items.length - 1].value;
  }

  private randomDefectType(): DefectType {
    return this.weightedRandom(DEFECT_DISTRIBUTION);
  }

  private randomSeverity(): DefectSeverity {
    return this.weightedRandom(SEVERITY_DISTRIBUTION);
  }

  private composeDefectNote(
    defectType: DefectType,
    severity: DefectSeverity,
    serial: string,
  ): string {
    const baseNotes =
      DEFECT_NOTES[defectType] ?? DEFECT_NOTES[DefectType.OTHER];
    const severityLabel =
      severity === DefectSeverity.CRITICAL
        ? "critical"
        : severity === DefectSeverity.MAJOR
          ? "major"
          : "minor";
    const base = this.randomChoice(baseNotes);
    return `${base} (${severityLabel} severity on ${serial}).`;
  }

  private async uploadSampleImage(
    tenantId: string,
    hasDefect: boolean,
    defectType?: DefectType,
  ): Promise<string> {
    this.ensureSampleImagesLoaded();

    const image = hasDefect
      ? getRandomDefectImage(defectType) || getRandomNormalImage()
      : getRandomNormalImage();

    if (image) {
      const key = this.storageService.generateKey(tenantId, image.filename);
      await this.storageService.uploadFileWithKey(
        key,
        image.buffer,
        image.contentType,
      );
      return key;
    }

    const buffer = this.generatePlaceholderImage(hasDefect);
    const key = this.storageService.generateKey(tenantId);
    await this.storageService.uploadFileWithKey(key, buffer);
    return key;
  }

  private generatePlaceholderImage(hasDefect: boolean): Buffer {
    const width = 200;
    const height = 200;
    const channels = 3;
    const buffer = Buffer.alloc(width * height * channels);

    for (let i = 0; i < buffer.length; i += 3) {
      buffer[i] = 205;
      buffer[i + 1] = 205;
      buffer[i + 2] = 205;
    }

    if (hasDefect) {
      const centerX = Math.floor(width * 0.5);
      const centerY = Math.floor(height * 0.55);
      const radius = 28;

      for (let y = centerY - radius; y <= centerY + radius; y++) {
        for (let x = centerX - radius; x <= centerX + radius; x++) {
          const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2);
          if (
            distance <= radius &&
            x >= 0 &&
            x < width &&
            y >= 0 &&
            y < height
          ) {
            const idx = (y * width + x) * 3;
            buffer[idx] = 220;
            buffer[idx + 1] = 60;
            buffer[idx + 2] = 45;
          }
        }
      }
    }

    return buffer;
  }

  private getBatchSeedConfigs(slug: string): BatchSeedConfig[] {
    if (slug === "samplebrand") {
      return [
        {
          poNumber: "SB-PO-2405",
          vendorCode: "AAG",
          styleCode: "S-006",
          quantity: 980,
          status: BatchStatus.IN_PROGRESS,
          priority: "high",
          currentStation: ProcessStation.QUALITY_CHECK,
          estimatedCompletionOffsetHours: 18,
          startDaysAgo: 9,
          inspectionStartDaysAgo: 7,
          inspectionSpanHours: 150,
          coverage: 0.64,
          defectRate: 0.058,
          sampleGarments: 140,
          processTimeline: [
            {
              station: ProcessStation.RECEIVING,
              startOffsetHours: 0,
              durationHours: 6,
              notes: "Yarn lots verified and logged.",
              qualityScore: 90,
            },
            {
              station: ProcessStation.INITIAL_INSPECTION,
              startOffsetHours: 8,
              durationHours: 16,
              notes: "Knitting tension adjustments completed.",
              qualityScore: 92,
            },
            {
              station: ProcessStation.IRONING,
              startOffsetHours: 30,
              durationHours: 12,
              notes: "Light steam finish applied for softness.",
              qualityScore: 91,
            },
            {
              station: ProcessStation.FOLDING,
              startOffsetHours: 50,
              durationHours: 10,
              notes: "Fold templates matched to retail spec.",
              qualityScore: 93,
            },
            {
              station: ProcessStation.QUALITY_CHECK,
              startOffsetHours: 72,
              durationHours: 30,
              notes: "High priority QC with dual operators.",
              qualityScore: 94,
            },
          ],
          stationPool: [
            ProcessStation.INITIAL_INSPECTION,
            ProcessStation.QUALITY_CHECK,
            ProcessStation.PACKING,
            ProcessStation.FINAL_INSPECTION,
          ],
        },
        {
          poNumber: "SB-PO-2406",
          vendorCode: "LSW",
          styleCode: "D-005",
          quantity: 720,
          status: BatchStatus.AWAITING_APPROVAL,
          priority: "urgent",
          currentStation: ProcessStation.FINAL_INSPECTION,
          estimatedCompletionOffsetHours: -4,
          startDaysAgo: 15,
          inspectionStartDaysAgo: 12,
          inspectionSpanHours: 210,
          coverage: 0.97,
          defectRate: 0.089,
          sampleGarments: 150,
          awaitingApprovalEvent: true,
          processTimeline: [
            {
              station: ProcessStation.RECEIVING,
              startOffsetHours: 0,
              durationHours: 7,
              notes: "Delicate fabrics inspected for flaws.",
              qualityScore: 92,
            },
            {
              station: ProcessStation.INITIAL_INSPECTION,
              startOffsetHours: 9,
              durationHours: 18,
              notes: "Laser measurement validation in progress.",
              qualityScore: 94,
            },
            {
              station: ProcessStation.IRONING,
              startOffsetHours: 34,
              durationHours: 14,
              notes: "Garments conditioned for smooth drape.",
              qualityScore: 92,
            },
            {
              station: ProcessStation.FOLDING,
              startOffsetHours: 58,
              durationHours: 9,
              notes: "Automated folding configured for boutique packaging.",
              qualityScore: 93,
            },
            {
              station: ProcessStation.QUALITY_CHECK,
              startOffsetHours: 80,
              durationHours: 24,
              notes: "Defect review triggered for escalation.",
              qualityScore: 88,
            },
            {
              station: ProcessStation.PACKING,
              startOffsetHours: 110,
              durationHours: 12,
              notes: "Packing paused pending approvals.",
              qualityScore: 90,
            },
            {
              station: ProcessStation.FINAL_INSPECTION,
              startOffsetHours: 134,
              durationHours: 20,
              notes: "Executive review awaiting sign-off.",
              qualityScore: 91,
            },
          ],
          stationPool: [
            ProcessStation.QUALITY_CHECK,
            ProcessStation.FINAL_INSPECTION,
            ProcessStation.PACKING,
          ],
        },
        {
          poNumber: "SB-PO-2403",
          vendorCode: "GGL",
          styleCode: "T-001",
          quantity: 860,
          status: BatchStatus.APPROVED,
          priority: "normal",
          currentStation: ProcessStation.DISPATCH,
          estimatedCompletionOffsetHours: -30,
          startDaysAgo: 21,
          inspectionStartDaysAgo: 18,
          inspectionSpanHours: 240,
          coverage: 0.99,
          defectRate: 0.047,
          sampleGarments: 160,
          approval: {
            decision: ApprovalDecision.APPROVED,
            comment:
              "All metrics within KPI bands. Ready for multi-store drop.",
            decidedDaysAgo: 3,
          },
          processTimeline: [
            {
              station: ProcessStation.RECEIVING,
              startOffsetHours: 0,
              durationHours: 8,
              notes: "Bulk tees received for regional deployment.",
              qualityScore: 93,
            },
            {
              station: ProcessStation.INITIAL_INSPECTION,
              startOffsetHours: 12,
              durationHours: 22,
              notes: "Inline AI inspection at 97% precision.",
              qualityScore: 95,
            },
            {
              station: ProcessStation.IRONING,
              startOffsetHours: 40,
              durationHours: 14,
              notes: "Wrinkle reduction cycle complete.",
              qualityScore: 94,
            },
            {
              station: ProcessStation.FOLDING,
              startOffsetHours: 62,
              durationHours: 11,
              notes: "Folding spec adjusted for e-commerce orders.",
              qualityScore: 96,
            },
            {
              station: ProcessStation.QUALITY_CHECK,
              startOffsetHours: 84,
              durationHours: 32,
              notes: "Quality gates cleared with minor notes.",
              qualityScore: 95,
            },
            {
              station: ProcessStation.PACKING,
              startOffsetHours: 120,
              durationHours: 16,
              notes: "Eco-packaging applied for export.",
              qualityScore: 94,
            },
            {
              station: ProcessStation.FINAL_INSPECTION,
              startOffsetHours: 150,
              durationHours: 18,
              notes: "Final checklist signed off by QA lead.",
              qualityScore: 96,
            },
            {
              station: ProcessStation.DISPATCH,
              startOffsetHours: 180,
              durationHours: 24,
              notes: "Shipment prepared for distribution center.",
              qualityScore: 95,
            },
          ],
          stationPool: [
            ProcessStation.QUALITY_CHECK,
            ProcessStation.FINAL_INSPECTION,
            ProcessStation.DISPATCH,
            ProcessStation.PACKING,
          ],
        },
        {
          poNumber: "SB-PO-2401",
          vendorCode: "PTC",
          styleCode: "P-004",
          quantity: 540,
          status: BatchStatus.IN_PROGRESS,
          priority: "normal",
          currentStation: ProcessStation.IRONING,
          estimatedCompletionOffsetHours: 48,
          startDaysAgo: 6,
          inspectionStartDaysAgo: 5,
          inspectionSpanHours: 120,
          coverage: 0.52,
          defectRate: 0.055,
          sampleGarments: 120,
          processTimeline: [
            {
              station: ProcessStation.RECEIVING,
              startOffsetHours: 0,
              durationHours: 5,
              notes: "PO received from Northern supplier.",
              qualityScore: 91,
            },
            {
              station: ProcessStation.INITIAL_INSPECTION,
              startOffsetHours: 6,
              durationHours: 14,
              notes: "Initial seam checks underway.",
              qualityScore: 92,
            },
            {
              station: ProcessStation.IRONING,
              startOffsetHours: 26,
              durationHours: 20,
              notes: "Pressing crew working through backlog.",
              qualityScore: 90,
            },
          ],
          stationPool: [
            ProcessStation.INITIAL_INSPECTION,
            ProcessStation.IRONING,
            ProcessStation.QUALITY_CHECK,
          ],
        },
      ];
    }

    return [
      {
        poNumber: "HM-PO-2401",
        vendorCode: "PTC",
        styleCode: "T-001",
        quantity: 1200,
        status: BatchStatus.IN_PROGRESS,
        priority: "high",
        currentStation: ProcessStation.QUALITY_CHECK,
        estimatedCompletionOffsetHours: 36,
        startDaysAgo: 12,
        inspectionStartDaysAgo: 10,
        inspectionSpanHours: 180,
        coverage: 0.68,
        defectRate: 0.065,
        sampleGarments: 160,
        processTimeline: [
          {
            station: ProcessStation.RECEIVING,
            startOffsetHours: 0,
            durationHours: 8,
            notes: "Bulk fabric received and logged.",
            qualityScore: 91,
          },
          {
            station: ProcessStation.INITIAL_INSPECTION,
            startOffsetHours: 10,
            durationHours: 20,
            notes: "Vision system calibration validated.",
            qualityScore: 93,
          },
          {
            station: ProcessStation.IRONING,
            startOffsetHours: 40,
            durationHours: 16,
            notes: "Steam finish applied to reduce creases.",
            qualityScore: 92,
          },
          {
            station: ProcessStation.FOLDING,
            startOffsetHours: 62,
            durationHours: 12,
            notes: "Automated folding for retail presentation.",
            qualityScore: 94,
          },
          {
            station: ProcessStation.QUALITY_CHECK,
            startOffsetHours: 84,
            durationHours: 36,
            notes: "Inline AI quality review in progress.",
            qualityScore: 95,
          },
        ],
        stationPool: [
          ProcessStation.INITIAL_INSPECTION,
          ProcessStation.QUALITY_CHECK,
          ProcessStation.PACKING,
          ProcessStation.FINAL_INSPECTION,
        ],
      },
      {
        poNumber: "HM-PO-2402",
        vendorCode: "GGL",
        styleCode: "H-002",
        quantity: 680,
        status: BatchStatus.AWAITING_APPROVAL,
        priority: "urgent",
        currentStation: ProcessStation.FINAL_INSPECTION,
        estimatedCompletionOffsetHours: -6,
        startDaysAgo: 18,
        inspectionStartDaysAgo: 14,
        inspectionSpanHours: 220,
        coverage: 0.96,
        defectRate: 0.082,
        sampleGarments: 150,
        awaitingApprovalEvent: true,
        processTimeline: [
          {
            station: ProcessStation.RECEIVING,
            startOffsetHours: 0,
            durationHours: 9,
            notes: "Hoodies unpacked for inspection.",
            qualityScore: 92,
          },
          {
            station: ProcessStation.INITIAL_INSPECTION,
            startOffsetHours: 12,
            durationHours: 22,
            notes: "Stitch analysis flagged variances.",
            qualityScore: 90,
          },
          {
            station: ProcessStation.IRONING,
            startOffsetHours: 42,
            durationHours: 18,
            notes: "Final shaping before packing.",
            qualityScore: 91,
          },
          {
            station: ProcessStation.FOLDING,
            startOffsetHours: 68,
            durationHours: 10,
            notes: "Fold automation tuned for bulky garments.",
            qualityScore: 93,
          },
          {
            station: ProcessStation.QUALITY_CHECK,
            startOffsetHours: 90,
            durationHours: 28,
            notes: "Several garments held for rework.",
            qualityScore: 87,
          },
          {
            station: ProcessStation.PACKING,
            startOffsetHours: 122,
            durationHours: 14,
            notes: "Packing on hold awaiting approval.",
            qualityScore: 89,
          },
          {
            station: ProcessStation.FINAL_INSPECTION,
            startOffsetHours: 150,
            durationHours: 20,
            notes: "Leadership review requested.",
            qualityScore: 90,
          },
        ],
        stationPool: [
          ProcessStation.QUALITY_CHECK,
          ProcessStation.FINAL_INSPECTION,
          ProcessStation.PACKING,
        ],
      },
      {
        poNumber: "HM-PO-2397",
        vendorCode: "FFI",
        styleCode: "J-003",
        quantity: 940,
        status: BatchStatus.APPROVED,
        priority: "normal",
        currentStation: ProcessStation.DISPATCH,
        estimatedCompletionOffsetHours: -48,
        startDaysAgo: 27,
        inspectionStartDaysAgo: 23,
        inspectionSpanHours: 260,
        coverage: 0.98,
        defectRate: 0.052,
        sampleGarments: 170,
        approval: {
          decision: ApprovalDecision.APPROVED,
          comment: "Meets premium denim tolerances. Release to retail.",
          decidedDaysAgo: 2,
        },
        processTimeline: [
          {
            station: ProcessStation.RECEIVING,
            startOffsetHours: 0,
            durationHours: 10,
            notes: "Denim lot tracked with RFID pallets.",
            qualityScore: 94,
          },
          {
            station: ProcessStation.INITIAL_INSPECTION,
            startOffsetHours: 14,
            durationHours: 24,
            notes: "Grading measurements confirmed.",
            qualityScore: 95,
          },
          {
            station: ProcessStation.IRONING,
            startOffsetHours: 46,
            durationHours: 16,
            notes: "Heat treatment for fabric memory.",
            qualityScore: 93,
          },
          {
            station: ProcessStation.FOLDING,
            startOffsetHours: 72,
            durationHours: 12,
            notes: "Fold spec for premium packaging.",
            qualityScore: 94,
          },
          {
            station: ProcessStation.QUALITY_CHECK,
            startOffsetHours: 96,
            durationHours: 34,
            notes: "QC backlog cleared with high accuracy.",
            qualityScore: 95,
          },
          {
            station: ProcessStation.PACKING,
            startOffsetHours: 134,
            durationHours: 18,
            notes: "Packaged with sustainability inserts.",
            qualityScore: 96,
          },
          {
            station: ProcessStation.FINAL_INSPECTION,
            startOffsetHours: 162,
            durationHours: 20,
            notes: "Final sign-off completed by QA director.",
            qualityScore: 96,
          },
          {
            station: ProcessStation.DISPATCH,
            startOffsetHours: 192,
            durationHours: 24,
            notes: "Shipment consolidated for export.",
            qualityScore: 95,
          },
        ],
        stationPool: [
          ProcessStation.QUALITY_CHECK,
          ProcessStation.FINAL_INSPECTION,
          ProcessStation.DISPATCH,
          ProcessStation.PACKING,
        ],
      },
      {
        poNumber: "HM-PO-2394",
        vendorCode: "PTC",
        styleCode: "P-004",
        quantity: 420,
        status: BatchStatus.REJECTED,
        priority: "high",
        currentStation: ProcessStation.QUALITY_CHECK,
        estimatedCompletionOffsetHours: -72,
        startDaysAgo: 21,
        inspectionStartDaysAgo: 17,
        inspectionSpanHours: 180,
        coverage: 0.9,
        defectRate: 0.12,
        sampleGarments: 120,
        approval: {
          decision: ApprovalDecision.REJECTED,
          comment: "Measurement variance exceeded spec. Rework required.",
          decidedDaysAgo: 1,
        },
        processTimeline: [
          {
            station: ProcessStation.RECEIVING,
            startOffsetHours: 0,
            durationHours: 7,
            notes: "Polo shipment unpacked.",
            qualityScore: 92,
          },
          {
            station: ProcessStation.INITIAL_INSPECTION,
            startOffsetHours: 10,
            durationHours: 18,
            notes: "Collar stitching issues identified.",
            qualityScore: 88,
          },
          {
            station: ProcessStation.QUALITY_CHECK,
            startOffsetHours: 40,
            durationHours: 26,
            notes: "Batch halted due to sizing anomalies.",
            qualityScore: 82,
          },
        ],
        stationPool: [
          ProcessStation.QUALITY_CHECK,
          ProcessStation.FINAL_INSPECTION,
        ],
      },
    ];
  }
}
