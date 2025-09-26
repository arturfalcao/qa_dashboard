import { Injectable, Logger } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { In, Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { Client } from "../entities/client.entity";
import { User } from "../entities/user.entity";
import { Factory } from "../entities/factory.entity";
import { Lot } from "../entities/lot.entity";
import { Inspection } from "../entities/inspection.entity";
import { Defect } from "../entities/defect.entity";
import { Photo } from "../entities/photo.entity";
import { DefectType } from "../entities/defect-type.entity";
import { Role } from "../entities/role.entity";
import { UserRole as UserRoleEntity } from "../entities/user-role.entity";
import { Approval } from "../entities/approval.entity";
import { LotFactory } from "../entities/lot-factory.entity";
import { LotFactoryRole } from "../entities/lot-factory-role.entity";
import { SupplyChainRole } from "../entities/supply-chain-role.entity";
import { FactoryRole } from "../entities/factory-role.entity";
import {
  UserRole,
  LotStatus,
  ApprovalDecision,
  SupplyChainStageStatus,
} from "@qa-dashboard/shared";

interface SeedUser {
  email: string;
  password: string;
  roles: UserRole[];
}

interface SeedLotSupplierRole {
  key: string;
  co2Kg?: number;
  notes?: string;
  sequence?: number;
}

interface SeedLotSupplier {
  name: string;
  stage?: string;
  isPrimary?: boolean;
  roles?: SeedLotSupplierRole[];
}

interface SeedLot {
  clientSlug: string;
  factories?: SeedLotSupplier[];
  factoryName?: string;
  styleRef: string;
  quantityTotal: number;
  status: LotStatus;
  defectRate: number;
  inspectedProgress: number;
  approvals?: {
    approvedByEmail: string;
    decision: ApprovalDecision;
    note?: string;
  };
  inspections: Array<{
    inspectorEmail?: string;
    startedAt?: Date;
    finishedAt?: Date;
    defects: Array<{
      pieceCode?: string;
      note?: string;
      defectTypeName?: string;
      photos: string[];
    }>;
  }>;
}

const CLIENTS = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Hey Marly",
    slug: "heymarly",
    logoUrl: null,
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "Sample Brand",
    slug: "samplebrand",
    logoUrl: null,
  },
];

const FACTORIES = [
  {
    name: "Florence Factory",
    city: "Guimarães",
    country: "PT",
    clientSlug: "heymarly",
    roles: [
      "fibre-prep",
      "dyeing",
      "cutting",
      "sewing",
      "quality",
      "packaging",
    ],
  },
  {
    name: "Atlantic Apparel",
    city: "Braga",
    country: "PT",
    clientSlug: "heymarly",
    roles: [
      "sewing",
      "quality",
      "laundry",
      "packaging",
      "logistics",
    ],
  },
  {
    name: "Lusitano Textiles",
    city: "Porto",
    country: "PT",
    clientSlug: "samplebrand",
    roles: [
      "fibre-prep",
      "dyeing",
      "cutting",
      "sewing",
      "quality",
      "logistics",
    ],
  },
];

const SUPPLY_CHAIN_ROLE_SEEDS = [
  {
    key: "fibre-prep",
    name: "Fiber Preparation",
    description: "Raw material sourcing, spinning or knitting base fabrics",
    defaultSequence: 0,
    defaultCo2Kg: 12.5,
  },
  {
    key: "dyeing",
    name: "Dyeing & Finishing",
    description: "Fabric dyeing, finishing and treatments",
    defaultSequence: 1,
    defaultCo2Kg: 7.1,
  },
  {
    key: "cutting",
    name: "Cutting",
    description: "Cutting and marker optimization",
    defaultSequence: 2,
    defaultCo2Kg: 4.2,
  },
  {
    key: "sewing",
    name: "Sewing",
    description: "Assembly and stitching of the garment",
    defaultSequence: 3,
    defaultCo2Kg: 6.8,
  },
  {
    key: "laundry",
    name: "Laundry & Washing",
    description: "Laundry, washing and pre-shrink steps",
    defaultSequence: 4,
    defaultCo2Kg: 3.4,
  },
  {
    key: "quality",
    name: "Quality Control",
    description: "Final inspection and QA activities",
    defaultSequence: 5,
    defaultCo2Kg: 1.9,
  },
  {
    key: "packaging",
    name: "Packaging",
    description: "Final folding, packing and boxing",
    defaultSequence: 6,
    defaultCo2Kg: 1.1,
  },
  {
    key: "logistics",
    name: "Inbound Logistics",
    description: "Transport between factories and to the distribution hub",
    defaultSequence: 7,
    defaultCo2Kg: 8.6,
  },
];

const USERS: Record<string, SeedUser[]> = {
  heymarly: [
    {
      email: "admin@marly.example",
      password: "demo1234",
      roles: [UserRole.ADMIN, UserRole.OPS_MANAGER],
    },
    {
      email: "viewer@marly.example",
      password: "demo1234",
      roles: [UserRole.CLIENT_VIEWER],
    },
    {
      email: "clevel@marly.example",
      password: "demo1234",
      roles: [UserRole.CLEVEL],
    },
  ],
  samplebrand: [
    {
      email: "admin@brand.example",
      password: "demo1234",
      roles: [UserRole.ADMIN, UserRole.OPS_MANAGER],
    },
    {
      email: "viewer@brand.example",
      password: "demo1234",
      roles: [UserRole.CLIENT_VIEWER],
    },
  ],
};

const DEFECT_TYPES = [
  "Stitching",
  "Measurement",
  "Stain",
  "Misprint",
  "Fabric Defect",
  "Hardware Issue",
  "Discoloration",
  "Tear Damage",
  "Other",
];

const PHOTO_POOL = [
  "https://images.unsplash.com/photo-1521579777140-6a5b6c1f1135?w=800&h=600&fit=crop", // Textile close-up
  "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?w=800&h=600&fit=crop", // Clothing details
  "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=800&h=600&fit=crop", // Fabric texture
  "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&h=600&fit=crop", // Garment manufacturing
  "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=800&h=600&fit=crop", // Sewing details
  "https://images.unsplash.com/photo-1544966503-7cc5ac882d5f?w=800&h=600&fit=crop", // Quality inspection
  "https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&h=600&fit=crop", // Factory worker
  "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?w=800&h=600&fit=crop", // Fabric rolls
  "https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=800&h=600&fit=crop", // Textile machinery
  "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=800&h=600&fit=crop", // Clothing rack
];

const STYLE_PREFIXES = ["HM", "SB", "LX", "AT", "FL"];
const SEASONS = ["SS", "AW", "FW"];
const YEARS = ["24", "25"];
const DEFECT_NOTES = [
  "Minor stitch tension variance - within acceptable range",
  "Small fabric inconsistency on back panel",
  "Print alignment slightly off center",
  "Buttonhole too tight for standard button",
  "Seam puckering on shoulder",
  "Color bleeding on wash test",
  "Zipper malfunction - won't stay closed",
  "Excessive loose threads",
  "Minor measurement variance - within tolerance",
  "Thread color mismatch",
  "Fabric pilling detected",
  "Loose button attachment",
  "Uneven hem alignment",
  "Small tear in fabric",
  "Label placement incorrect"
];

function getRandomPhotos(count: number = 1): string[] {
  const shuffled = [...PHOTO_POOL].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, Math.min(count, PHOTO_POOL.length));
}

function getRandomStyleRef(clientSlug: string): string {
  const prefix = clientSlug === "heymarly" ? "HM" : "SB";
  const season = SEASONS[Math.floor(Math.random() * SEASONS.length)];
  const year = YEARS[Math.floor(Math.random() * YEARS.length)];
  const num = String(Math.floor(Math.random() * 999) + 1).padStart(3, '0');
  return `${prefix}-${season}${year}-${num}`;
}

function getRandomDefectNote(): string {
  return DEFECT_NOTES[Math.floor(Math.random() * DEFECT_NOTES.length)];
}

function getRandomDate(daysAgo: number): Date {
  const now = Date.now();
  const randomOffset = Math.random() * daysAgo * 24 * 60 * 60 * 1000;
  return new Date(now - randomOffset);
}

function generateRandomLots(): SeedLot[] {
  const lotCount = Math.floor(Math.random() * 8) + 12; // 12-19 lots
  const lots: SeedLot[] = [];
  const usedStyleRefs = new Set<string>();

  for (let i = 0; i < lotCount; i++) {
    const clientSlug = Math.random() > 0.6 ? "heymarly" : "samplebrand";
    const factoryName = clientSlug === "heymarly"
      ? (Math.random() > 0.5 ? "Florence Factory" : "Atlantic Apparel")
      : "Lusitano Textiles";

    let styleRef: string;
    do {
      styleRef = getRandomStyleRef(clientSlug);
    } while (usedStyleRefs.has(styleRef));
    usedStyleRefs.add(styleRef);

    const status = getRandomLotStatus();
    const quantityTotal = Math.floor(Math.random() * 800) + 200; // 200-999
    const defectRate = status === LotStatus.PLANNED ? 0 : Math.random() * 10;
    const inspectedProgress = status === LotStatus.PLANNED ? 0 :
      status === LotStatus.INSPECTION ? Math.floor(Math.random() * 80) + 20 : 100;

    const lot: SeedLot = {
      clientSlug,
      factories: [{
        name: factoryName,
        isPrimary: true,
        stage: getRandomStage(),
        roles: getRandomFactoryRoles()
      }],
      styleRef,
      quantityTotal,
      status,
      defectRate,
      inspectedProgress,
      inspections: status !== LotStatus.PLANNED ? generateRandomInspections(clientSlug, styleRef) : []
    };

    if (status === LotStatus.APPROVED) {
      const adminEmail = clientSlug === "heymarly" ? "admin@marly.example" : "admin@brand.example";
      lot.approvals = {
        approvedByEmail: adminEmail,
        decision: ApprovalDecision.APPROVE,
        note: getRandomApprovalNote()
      };
    }

    lots.push(lot);
  }

  return lots;
}

function getRandomLotStatus(): LotStatus {
  const statuses = [LotStatus.PLANNED, LotStatus.INSPECTION, LotStatus.PENDING_APPROVAL, LotStatus.APPROVED];
  const weights = [0.2, 0.3, 0.25, 0.25]; // 20% planned, 30% inspection, 25% pending, 25% approved

  const random = Math.random();
  let sum = 0;
  for (let i = 0; i < weights.length; i++) {
    sum += weights[i];
    if (random <= sum) {
      return statuses[i];
    }
  }
  return statuses[0];
}

function getRandomStage(): string {
  const stages = [
    "Fabric prep & cutting", "Assembly & finishing", "Final assembly",
    "Cut & sew", "Full service", "Quality control", "Production", "Pre-production"
  ];
  return stages[Math.floor(Math.random() * stages.length)];
}

function getRandomFactoryRoles(): SeedLotSupplierRole[] {
  const roles = ["fibre-prep", "dyeing", "cutting", "sewing", "quality", "laundry", "packaging", "logistics"];
  const numRoles = Math.floor(Math.random() * 4) + 2; // 2-5 roles
  const selectedRoles = roles.sort(() => Math.random() - 0.5).slice(0, numRoles);

  return selectedRoles.map((key, index) => ({
    key,
    sequence: index
  }));
}

function generateRandomInspections(clientSlug: string, styleRef: string): SeedLot['inspections'] {
  const numInspections = Math.floor(Math.random() * 2) + 1; // 1-2 inspections
  const inspectorEmail = clientSlug === "heymarly" ? "viewer@marly.example" : "viewer@brand.example";

  return Array.from({length: numInspections}, (_, i) => {
    const startedAt = getRandomDate(7); // Within last 7 days
    const finishedAt = Math.random() > 0.3 ? new Date(startedAt.getTime() + Math.random() * 6 * 60 * 60 * 1000) : undefined;

    return {
      inspectorEmail,
      startedAt,
      finishedAt,
      defects: generateRandomDefects(styleRef)
    };
  });
}

function generateRandomDefects(styleRef: string): Array<{
  pieceCode?: string;
  note?: string;
  defectTypeName?: string;
  photos: string[];
}> {
  const numDefects = Math.floor(Math.random() * 4) + 1; // 1-4 defects
  const prefix = styleRef.split('-')[0];

  return Array.from({length: numDefects}, () => {
    const pieceNum = String(Math.floor(Math.random() * 999) + 1).padStart(3, '0');
    const numPhotos = Math.floor(Math.random() * 3) + 1; // 1-3 photos

    return {
      pieceCode: `${prefix}-${pieceNum}`,
      note: getRandomDefectNote(),
      defectTypeName: DEFECT_TYPES[Math.floor(Math.random() * DEFECT_TYPES.length)],
      photos: getRandomPhotos(numPhotos)
    };
  });
}

function getRandomApprovalNote(): string {
  const notes = [
    "Meets golden sample tolerance levels. Quality standards exceeded.",
    "Excellent quality. Ready for shipment.",
    "Quality approved with minor observations noted.",
    "Meets all specifications. Approved for production.",
    "Good quality control. Within acceptable parameters."
  ];
  return notes[Math.floor(Math.random() * notes.length)];
}

@Injectable()
export class SeedService {
  private readonly logger = new Logger(SeedService.name);

  constructor(
    @InjectRepository(Client)
    private readonly clientRepository: Repository<Client>,
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectRepository(Factory)
    private readonly factoryRepository: Repository<Factory>,
    @InjectRepository(Lot)
    private readonly lotRepository: Repository<Lot>,
    @InjectRepository(Inspection)
    private readonly inspectionRepository: Repository<Inspection>,
    @InjectRepository(Defect)
    private readonly defectRepository: Repository<Defect>,
    @InjectRepository(Photo)
    private readonly photoRepository: Repository<Photo>,
    @InjectRepository(DefectType)
    private readonly defectTypeRepository: Repository<DefectType>,
    @InjectRepository(Role)
    private readonly roleRepository: Repository<Role>,
    @InjectRepository(UserRoleEntity)
    private readonly userRoleRepository: Repository<UserRoleEntity>,
    @InjectRepository(Approval)
    private readonly approvalRepository: Repository<Approval>,
    @InjectRepository(LotFactory)
    private readonly lotFactoryRepository: Repository<LotFactory>,
    @InjectRepository(LotFactoryRole)
    private readonly lotFactoryRoleRepository: Repository<LotFactoryRole>,
    @InjectRepository(SupplyChainRole)
    private readonly supplyChainRoleRepository: Repository<SupplyChainRole>,
    @InjectRepository(FactoryRole)
    private readonly factoryRoleRepository: Repository<FactoryRole>,
  ) {}

  async seedData(): Promise<void> {
    await this.seedRoles();
    const clients = await this.seedClients();
    const supplyChainRoles = await this.seedSupplyChainRoles();
    await this.seedFactories(clients, supplyChainRoles);
    const defectTypes = await this.seedDefectTypes();
    const users = await this.seedUsers(clients);
    await this.clearExistingData();
    await this.seedLots(clients, defectTypes, users, supplyChainRoles);
  }

  private async clearExistingData(): Promise<void> {
    this.logger.log('Clearing existing lot data...');

    await this.photoRepository.query('DELETE FROM photos');
    await this.defectRepository.query('DELETE FROM defects');
    await this.inspectionRepository.query('DELETE FROM inspections');
    await this.approvalRepository.query('DELETE FROM approvals');
    await this.lotFactoryRoleRepository.query('DELETE FROM lot_factory_roles');
    await this.lotFactoryRepository.query('DELETE FROM lot_factories');
    await this.lotRepository.query('DELETE FROM lots');

    this.logger.log('Existing data cleared');
  }

  private async seedRoles(): Promise<void> {
    for (const role of Object.values(UserRole)) {
      const existing = await this.roleRepository.findOne({ where: { name: role } });
      if (!existing) {
        await this.roleRepository.save(
          this.roleRepository.create({
            name: role,
            description: `${role.replace("_", " ")} role`,
          }),
        );
      }
    }
  }

  private async seedClients(): Promise<Map<string, Client>> {
    const map = new Map<string, Client>();

    for (const clientSeed of CLIENTS) {
      let client = await this.clientRepository.findOne({
        where: { slug: clientSeed.slug },
      });

      if (!client) {
        client = this.clientRepository.create(clientSeed);
        client = await this.clientRepository.save(client);
        this.logger.log(`Created client ${client.name}`);
      }

      map.set(client.slug, client);
    }

    return map;
  }

  private async seedSupplyChainRoles(): Promise<Map<string, SupplyChainRole>> {
    const map = new Map<string, SupplyChainRole>();

    for (const roleSeed of SUPPLY_CHAIN_ROLE_SEEDS) {
      let role = await this.supplyChainRoleRepository.findOne({ where: { key: roleSeed.key } });
      if (!role) {
        role = this.supplyChainRoleRepository.create(roleSeed);
        role = await this.supplyChainRoleRepository.save(role);
      } else {
        role.name = roleSeed.name;
        role.description = roleSeed.description;
        role.defaultSequence = roleSeed.defaultSequence;
        role.defaultCo2Kg = roleSeed.defaultCo2Kg;
        role = await this.supplyChainRoleRepository.save(role);
      }
      map.set(role.key, role);
    }

    return map;
  }

  private async seedFactories(
    clients: Map<string, Client>,
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<void> {
    for (const factorySeed of FACTORIES) {
      const client = clients.get(factorySeed.clientSlug);
      if (!client) {
        continue;
      }

      let factory = await this.factoryRepository.findOne({
        where: { name: factorySeed.name, clientId: client.id },
        relations: ["capabilities", "capabilities.role"],
      });

      if (!factory) {
        factory = this.factoryRepository.create({
          clientId: client.id,
          name: factorySeed.name,
          city: factorySeed.city,
          country: factorySeed.country,
        });
        factory = await this.factoryRepository.save(factory);
      }

      await this.syncFactoryCapabilities(factory.id, factorySeed.roles ?? [], supplyChainRoles);
    }
  }

  private async seedDefectTypes(): Promise<Map<string, DefectType>> {
    const map = new Map<string, DefectType>();

    for (const name of DEFECT_TYPES) {
      let defectType = await this.defectTypeRepository.findOne({ where: { name } });
      if (!defectType) {
        defectType = this.defectTypeRepository.create({ name });
        defectType = await this.defectTypeRepository.save(defectType);
      }
      map.set(name, defectType);
    }

    return map;
  }

  private async syncFactoryCapabilities(
    factoryId: string,
    roleKeys: string[],
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<void> {
    const uniqueKeys = Array.from(new Set(roleKeys));

    await this.factoryRoleRepository.delete({ factoryId });

    if (!uniqueKeys.length) {
      return;
    }

    const records = uniqueKeys
      .map((key) => supplyChainRoles.get(key))
      .filter((role): role is SupplyChainRole => Boolean(role))
      .map((role) =>
        this.factoryRoleRepository.create({
          factoryId,
          roleId: role.id,
          co2OverrideKg: null,
          notes: null,
        }),
      );

    if (records.length) {
      await this.factoryRoleRepository.save(records);
    }
  }

  private async syncLotFactoryRoles(
    lotFactoryId: string,
    roles: SeedLotSupplierRole[] = [],
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<void> {
    await this.lotFactoryRoleRepository.delete({ lotFactoryId });

    if (!roles.length) {
      return;
    }

    const entries = roles
      .map((roleSeed, index) => {
        const role = supplyChainRoles.get(roleSeed.key);
        if (!role) {
          this.logger.warn(`Unknown supply chain role ${roleSeed.key} for seeded lot supplier ${lotFactoryId}`);
          return null;
        }

        const sequence = roleSeed.sequence ?? role.defaultSequence ?? index;
        const co2 = roleSeed.co2Kg ?? role.defaultCo2Kg ?? null;

        return this.lotFactoryRoleRepository.create({
          lotFactoryId,
          roleId: role.id,
          sequence,
          co2Kg: co2,
          notes: roleSeed.notes ?? null,
          status: SupplyChainStageStatus.NOT_STARTED,
        });
      })
      .filter((value): value is LotFactoryRole => Boolean(value));

    if (entries.length) {
      await this.lotFactoryRoleRepository.save(entries);
    }
  }

  private async seedUsers(clients: Map<string, Client>): Promise<Map<string, User>> {
    const userMap = new Map<string, User>();

    for (const [clientSlug, users] of Object.entries(USERS)) {
      const client = clients.get(clientSlug);
      if (!client) {
        continue;
      }

      for (const seedUser of users) {
        let user = await this.userRepository.findOne({
          where: { email: seedUser.email },
          relations: ["userRoles", "userRoles.role"],
        });

        if (!user) {
          const passwordHash = await bcrypt.hash(seedUser.password, 10);
          user = this.userRepository.create({
            email: seedUser.email,
            passwordHash,
            clientId: client.id,
          });
          user = await this.userRepository.save(user);
        } else if (!user.clientId) {
          user.clientId = client.id;
          user = await this.userRepository.save(user);
        }

        await this.assignRoles(user, seedUser.roles);
        userMap.set(seedUser.email, user);
      }
    }

    return userMap;
  }

  private async assignRoles(user: User, roles: UserRole[]): Promise<void> {
    const existingRoles = new Set(
      (await this.userRoleRepository.find({
        where: { userId: user.id },
        relations: ["role"],
      })).map((ur) => ur.role.name as UserRole),
    );

    for (const roleName of roles) {
      if (!existingRoles.has(roleName)) {
        const role = await this.roleRepository.findOneOrFail({
          where: { name: roleName },
        });
        await this.userRoleRepository.save(
          this.userRoleRepository.create({
            userId: user.id,
            roleId: role.id,
            isPrimary: roleName === roles[0],
          }),
        );
      }
    }
  }

  private async seedLots(
    clients: Map<string, Client>,
    defectTypes: Map<string, DefectType>,
    users: Map<string, User>,
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<void> {
    const lots = generateRandomLots();
    for (const lotSeed of lots) {
      const client = clients.get(lotSeed.clientSlug);
      if (!client) {
        continue;
      }

      const supplierSeeds = lotSeed.factories?.length
        ? lotSeed.factories
        : lotSeed.factoryName
        ? [{ name: lotSeed.factoryName, isPrimary: true }]
        : [];

      if (!supplierSeeds.length) {
        this.logger.warn(`Skipping lot ${lotSeed.styleRef} - no supplier factories configured`);
        continue;
      }

      const factoryRecords = await this.factoryRepository.find({
        where: {
          clientId: client.id,
          name: In(supplierSeeds.map((supplier) => supplier.name)),
        },
      });

      if (!factoryRecords.length) {
        this.logger.warn(`Skipping lot ${lotSeed.styleRef} - factories not found for client ${client.name}`);
        continue;
      }

      const factoryMap = new Map(factoryRecords.map((factory) => [factory.name, factory]));

      const supplierRows = supplierSeeds
        .map((seedSupplier, index) => {
          const factory = factoryMap.get(seedSupplier.name);
          if (!factory) {
            this.logger.warn(`Factory ${seedSupplier.name} not found for lot ${lotSeed.styleRef}`);
            return null;
          }
          return {
            factory,
            factoryId: factory.id,
            sequence: index,
            stage: seedSupplier.stage ?? null,
            isPrimary: seedSupplier.isPrimary ?? false,
            roles: seedSupplier.roles ?? [],
          };
        })
        .filter((value): value is {
          factory: Factory;
          factoryId: string;
          sequence: number;
          stage: string | null;
          isPrimary: boolean;
          roles: SeedLotSupplierRole[];
        } => value !== null);

      if (!supplierRows.length) {
        continue;
      }

      if (!supplierRows.some((supplier) => supplier.isPrimary)) {
        supplierRows[0].isPrimary = true;
      }

      const primaryFactoryId = supplierRows.find((supplier) => supplier.isPrimary)?.factoryId ?? supplierRows[0].factoryId;

      let lot = await this.lotRepository.findOne({
        where: { clientId: client.id, styleRef: lotSeed.styleRef },
      });

      if (!lot) {
        lot = this.lotRepository.create({
          clientId: client.id,
          factoryId: primaryFactoryId,
          styleRef: lotSeed.styleRef,
          quantityTotal: lotSeed.quantityTotal,
          status: lotSeed.status,
          defectRate: lotSeed.defectRate,
          inspectedProgress: lotSeed.inspectedProgress,
        });
        lot = await this.lotRepository.save(lot);
      } else {
        lot.status = lotSeed.status;
        lot.defectRate = lotSeed.defectRate;
        lot.inspectedProgress = lotSeed.inspectedProgress;
        lot.factoryId = primaryFactoryId;
        lot = await this.lotRepository.save(lot);
      }

      await this.lotFactoryRepository.delete({ lotId: lot.id });
      for (const supplier of supplierRows) {
        const savedSupplier = await this.lotFactoryRepository.save(
          this.lotFactoryRepository.create({
            lotId: lot.id,
            factoryId: supplier.factoryId,
            sequence: supplier.sequence,
            stage: supplier.stage,
            isPrimary: supplier.factoryId === primaryFactoryId,
          }),
        );

        await this.syncLotFactoryRoles(savedSupplier.id, supplier.roles, supplyChainRoles);
      }

      await this.initializeLotSupplyChainStatus(lot.id);

      if (lotSeed.approvals) {
        const approver = users.get(lotSeed.approvals.approvedByEmail);
        if (approver) {
          const existingApproval = await this.approvalRepository.findOne({
            where: { lotId: lot.id },
          });
          if (!existingApproval) {
            await this.approvalRepository.save(
              this.approvalRepository.create({
                lotId: lot.id,
                approvedBy: approver.id,
                decision: lotSeed.approvals.decision,
                note: lotSeed.approvals.note,
              }),
            );
          }
        }
      }

      await this.seedInspections(lot, lotSeed, users, defectTypes);
    }
  }

  private async initializeLotSupplyChainStatus(lotId: string): Promise<void> {
    const roles = await this.lotFactoryRoleRepository
      .createQueryBuilder("role")
      .innerJoin("role.lotFactory", "lf")
      .where("lf.lot_id = :lotId", { lotId })
      .orderBy("lf.sequence", "ASC")
      .addOrderBy("role.sequence", "ASC")
      .getMany();

    if (!roles.length) {
      return;
    }

    const first = roles[0];
    if (first.status !== SupplyChainStageStatus.IN_PROGRESS) {
      first.status = SupplyChainStageStatus.IN_PROGRESS;
      first.startedAt = new Date();
      first.completedAt = null;
      await this.lotFactoryRoleRepository.save(first);
    }
  }

  private async seedInspections(
    lot: Lot,
    lotSeed: SeedLot,
    users: Map<string, User>,
    defectTypes: Map<string, DefectType>,
  ): Promise<void> {
    await this.inspectionRepository.delete({ lotId: lot.id });

    for (const inspectionSeed of lotSeed.inspections) {
      const inspector = inspectionSeed.inspectorEmail
        ? users.get(inspectionSeed.inspectorEmail)
        : undefined;

      const inspection = await this.inspectionRepository.save(
        this.inspectionRepository.create({
          lotId: lot.id,
          inspectorId: inspector?.id,
          startedAt: inspectionSeed.startedAt,
          finishedAt: inspectionSeed.finishedAt,
        }),
      );

      for (const defectSeed of inspectionSeed.defects) {
        const defectType = defectSeed.defectTypeName
          ? defectTypes.get(defectSeed.defectTypeName)
          : undefined;

        const defect = await this.defectRepository.save(
          this.defectRepository.create({
            inspectionId: inspection.id,
            pieceCode: defectSeed.pieceCode,
            note: defectSeed.note,
            defectTypeId: defectType?.id,
          }),
        );

        for (const photoUrl of defectSeed.photos) {
          await this.photoRepository.save(
            this.photoRepository.create({
              defectId: defect.id,
              url: photoUrl,
            }),
          );
        }
      }
    }
  }
}
