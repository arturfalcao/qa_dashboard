import { Injectable, Logger } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { In, Repository } from "typeorm";
import * as bcrypt from "bcryptjs";

import { Tenant } from "../entities/tenant.entity";
import { User } from "../entities/user.entity";
import { Factory } from "../entities/factory.entity";
import { Lot } from "../entities/lot.entity";
import { Event } from "../entities/event.entity";
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
import { FactoryCertification } from "../entities/factory-certification.entity";
import { LotUserAssignment } from "../entities/lot-user-assignment.entity";
import { Dpp, DppStatus } from "../entities/dpp.entity";
import { DppService } from "../../dpp/dpp.service";
import { CreateDppDto } from "../../dpp/dpp-schemas";
import {
  UserRole,
  LotStatus,
  ApprovalDecision,
  SupplyChainStageStatus,
  EventType,
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
  status?: SupplyChainStageStatus;
  startedAt?: Date;
  completedAt?: Date;
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
  materialComposition?: Array<{
    fiber: string;
    percentage: number;
    properties?: Record<string, any>;
  }>;
  dyeLot?: string;
  certifications?: Array<{
    type: string;
    number?: string;
    auditLink?: string;
    validUntil?: string;
    issuer?: string;
  }>;
  dppMetadata?: Record<string, any>;
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
    id: "6f16b1f3-6cd8-4b1b-a4f4-17c4a9d7c6c0",
    name: "PA&CO Luxury Manufacturing",
    slug: "paco",
    logoUrl: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=320&h=320&fit=crop",
  },
];

const FACTORIES: Array<{
  name: string;
  city: string;
  country: string;
  clientSlug: string;
  roles: string[];
  certifications?: string[];
}> = [
  {
    name: "Vale do Ave Fibre Hub",
    city: "Guimarães",
    country: "PT",
    clientSlug: "paco",
    roles: [
      "FIBER_PREP",
      "FABRIC_DYE_FINISH",
      "FABRIC_WASH_PREP",
      "FABRIC_INSPECTION_RELAX",
      "FABRIC_LAB_TEST",
    ],
    certifications: ["GOTS", "ISO_14001"],
  },
  {
    name: "Braga Cutting & Assembly",
    city: "Braga",
    country: "PT",
    clientSlug: "paco",
    roles: [
      "PATTERN_GRADING",
      "MARKER_CUTTING",
      "EMBROIDERY_APPLIQUE_LASER",
      "BUNDLING_SEWING",
      "INLINE_QC",
      "TRIMS_EMBELLISH",
    ],
    certifications: ["OEKO_TEX_STANDARD_100", "AMFORI_BSCI"],
  },
  {
    name: "Vizela Laundry & Finishing",
    city: "Vizela",
    country: "PT",
    clientSlug: "paco",
    roles: [
      "SCREEN_PRINTING",
      "HEAT_TRANSFER",
      "GARMENT_WASH_SOFTEN",
      "IRON_PRESS_DETHREAD",
      "NEEDLE_METAL_DETECT",
    ],
    certifications: ["GRS", "BLUESIGN"],
  },
  {
    name: "Porto Atelier & QA Lab",
    city: "Porto",
    country: "PT",
    clientSlug: "paco",
    roles: [
      "BUNDLING_SEWING",
      "INLINE_QC",
      "TRIMS_EMBELLISH",
      "FINAL_QA",
      "DOCUMENTATION_DPP",
    ],
    certifications: ["GOTS", "OEKO_TEX_STANDARD_100"],
  },
  {
    name: "Lisbon Logistics Center",
    city: "Lisboa",
    country: "PT",
    clientSlug: "paco",
    roles: [
      "PACK_TAG_BAG",
      "WAREHOUSE_LOGISTICS",
      "SUSTAINABILITY_TRACK",
      "DOCUMENTATION_DPP",
    ],
    certifications: ["RCS", "ISO_14001"],
  },
];

const SUPPLY_CHAIN_ROLE_SEEDS = [
  {
    key: "FIBER_PREP",
    name: "Fiber Preparation",
    description: "Raw material preparation, spinning and greige knitting",
    defaultSequence: 10,
    defaultCo2Kg: 12.5,
  },
  {
    key: "FABRIC_DYE_FINISH",
    name: "Fabric Dye & Finish",
    description: "Piece dyeing, finishing and chemical treatments",
    defaultSequence: 20,
    defaultCo2Kg: 7.1,
  },
  {
    key: "FABRIC_WASH_PREP",
    name: "Fabric Wash & Prep",
    description: "Pre-wash, softening and shrink control on fabric rolls",
    defaultSequence: 30,
    defaultCo2Kg: 4.3,
  },
  {
    key: "FABRIC_INSPECTION_RELAX",
    name: "Fabric Inspection & Relax",
    description: "Relaxation, defect scanning and shade control",
    defaultSequence: 40,
    defaultCo2Kg: 1.6,
  },
  {
    key: "PATTERN_GRADING",
    name: "Pattern & Grading",
    description: "Digital grading, marker making and fit validation",
    defaultSequence: 50,
    defaultCo2Kg: 0.9,
  },
  {
    key: "MARKER_CUTTING",
    name: "Marker Cutting",
    description: "Automated cutting, bundling and lay efficiency",
    defaultSequence: 60,
    defaultCo2Kg: 2.4,
  },
  {
    key: "EMBROIDERY_APPLIQUE_LASER",
    name: "Embroidery & Laser",
    description: "Value-add surface treatments pre-assembly",
    defaultSequence: 70,
    defaultCo2Kg: 3.2,
  },
  {
    key: "BUNDLING_SEWING",
    name: "Bundling & Sewing",
    description: "Assembly lines, hand stitching and QC gates",
    defaultSequence: 80,
    defaultCo2Kg: 6.5,
  },
  {
    key: "INLINE_QC",
    name: "Inline QC",
    description: "Needle guards, inline checkpoints and torque tests",
    defaultSequence: 90,
    defaultCo2Kg: 1.1,
  },
  {
    key: "SCREEN_PRINTING",
    name: "Screen Printing",
    description: "Silk-screen printing, colour matching and curing",
    defaultSequence: 100,
    defaultCo2Kg: 4.6,
  },
  {
    key: "HEAT_TRANSFER",
    name: "Heat Transfer",
    description: "Labels, foils and heat-sealed trims",
    defaultSequence: 110,
    defaultCo2Kg: 2.1,
  },
  {
    key: "SUBLIMATION",
    name: "Sublimation",
    description: "All-over sublimation printing for performance textiles",
    defaultSequence: 120,
    defaultCo2Kg: 4.1,
  },
  {
    key: "DIGITAL_PRINTING",
    name: "Digital Printing",
    description: "Direct-to-garment or transfer printing",
    defaultSequence: 130,
    defaultCo2Kg: 3.3,
  },
  {
    key: "TRIMS_EMBELLISH",
    name: "Trims & Embellishment",
    description: "Hand-applied trims, beadwork and finishes",
    defaultSequence: 140,
    defaultCo2Kg: 1.8,
  },
  {
    key: "GARMENT_WASH_SOFTEN",
    name: "Garment Wash & Soften",
    description: "Enzyme wash, softening and post-sew finishing",
    defaultSequence: 150,
    defaultCo2Kg: 2.7,
  },
  {
    key: "FINAL_QA",
    name: "Final QA",
    description: "Lot audit, measurement verification and AQL",
    defaultSequence: 160,
    defaultCo2Kg: 0.9,
  },
  {
    key: "IRON_PRESS_DETHREAD",
    name: "Iron, Press & Dethread",
    description: "Pressing, steaming and final thread removal",
    defaultSequence: 170,
    defaultCo2Kg: 0.7,
  },
  {
    key: "NEEDLE_METAL_DETECT",
    name: "Needle & Metal Detection",
    description: "Needle detection and safety scanning",
    defaultSequence: 180,
    defaultCo2Kg: 0.5,
  },
  {
    key: "PACK_TAG_BAG",
    name: "Pack, Tag & Bag",
    description: "Folding, tagging, polybagging and kit completion",
    defaultSequence: 190,
    defaultCo2Kg: 0.8,
  },
  {
    key: "WAREHOUSE_LOGISTICS",
    name: "Warehouse & Logistics",
    description: "Consolidation, palletising and outbound logistics",
    defaultSequence: 200,
    defaultCo2Kg: 5.6,
  },
  {
    key: "FABRIC_LAB_TEST",
    name: "Fabric Lab Testing",
    description: "Physical and chemical lab testing for fabric",
    defaultSequence: 905,
    defaultCo2Kg: 0.4,
  },
  {
    key: "FUNCTIONAL_COATING",
    name: "Functional Coating",
    description: "Waterproofing, anti-bacterial or performance coatings",
    defaultSequence: 910,
    defaultCo2Kg: 2.7,
  },
  {
    key: "REGULATORY_CHECKS",
    name: "Regulatory Checks",
    description: "Product safety, restricted substances and compliance",
    defaultSequence: 920,
    defaultCo2Kg: 0.3,
  },
  {
    key: "SUSTAINABILITY_TRACK",
    name: "Sustainability Tracking",
    description: "Carbon accounting and ESG evidence capture",
    defaultSequence: 930,
    defaultCo2Kg: 0.2,
  },
  {
    key: "DOCUMENTATION_DPP",
    name: "Documentation & DPP",
    description: "Final passport data assembly and customer hand-off",
    defaultSequence: 940,
    defaultCo2Kg: 0.2,
  },
];

const USERS: Record<string, SeedUser[]> = {
  paco: [
    {
      email: "carlos.martins@paco.example",
      password: "demo1234",
      roles: [UserRole.ADMIN, UserRole.OPS_MANAGER],
    },
    {
      email: "ines.azevedo@paco.example",
      password: "demo1234",
      roles: [UserRole.CLEVEL],
    },
    {
      email: "joana.costa@paco.example",
      password: "demo1234",
      roles: [UserRole.OPS_MANAGER],
    },
    {
      email: "miguel.lopes@paco.example",
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
  "https://images.unsplash.com/photo-1596727147705-61a532a659bd?w=1200&h=900&fit=crop", // Indigo dye bath detail
  "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=1200&h=900&fit=crop", // Luxury atelier finishing neckline
  "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=1200&h=900&fit=crop", // Premium tailoring close-up
  "https://images.unsplash.com/photo-1618337587011-3fb44e40f6f3?w=1200&h=900&fit=crop", // Needle detection control
  "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=1200&h=900&fit=crop", // Measuring seam allowance
  "https://images.unsplash.com/photo-1550831106-0994e11a06b7?w=1200&h=900&fit=crop", // Inline QC with clipboard
  "https://images.unsplash.com/photo-1521572163474-a839d81e12c1?w=1200&h=900&fit=crop", // Hand-stitched embellishment
  "https://images.unsplash.com/photo-1582719478250-bd35fa037f73?w=1200&h=900&fit=crop", // Pressing and finishing line
  "https://images.unsplash.com/photo-1564489563601-9b5a0e671ce2?w=1200&h=900&fit=crop", // Sustainability analytics on tablet
  "https://images.unsplash.com/photo-1578768079051-9b5c2ef5d44f?w=1200&h=900&fit=crop", // Fabric inventory wall
  "https://images.unsplash.com/photo-1542293787938-4d2226c24d4c?w=1200&h=900&fit=crop", // Screen printing luxury motif
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=1200&h=900&fit=crop", // QA instrumentation desk
  "https://images.unsplash.com/photo-1582719478489-99c8ed571edc?w=1200&h=900&fit=crop", // Lab testing swatches
  "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=1200&h=900&fit=crop", // Luxury garment rack ready for shipment
  "https://images.unsplash.com/photo-1618354691437-1d4481a0e327?w=1200&h=900&fit=crop", // Sustainability dashboard monitoring
];

function getRandomPhotos(count: number = 1): string[] {
  const shuffled = [...PHOTO_POOL].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, Math.min(count, PHOTO_POOL.length));
}
const CURATED_LOTS: SeedLot[] = [
  {
    clientSlug: "paco",
    styleRef: "PA-SS25-CAPRI",
    quantityTotal: 420,
    status: LotStatus.IN_PRODUCTION,
    defectRate: 1.8,
    inspectedProgress: 62.5,
    materialComposition: [
      {
        fiber: "Organic Cotton (GOTS)",
        percentage: 92,
        properties: { region: "Vale do Ave", certification: "GOTS" },
      },
      {
        fiber: "Regenerated Elastane",
        percentage: 8,
        properties: { supplier: "Northern Portugal" },
      },
    ],
    dyeLot: "INDIGO-CAPRI-07",
    certifications: [
      { type: "GOTS", number: "GOTS-PT-2219", issuer: "Control Union" },
      { type: "OEKO_TEX_STANDARD_100", number: "2025OK8901", issuer: "OEKO-TEX" },
    ],
    dppMetadata: {
      dppId: "DPP-PA-SS25-CAPRI",
      version: "0.7-draft",
      status: "material-stage",
      publicUrl: "http://localhost:3000/dpp/PA-SS25-CAPRI",
      lastAudit: "2025-07-10T14:30:00Z",
      traceabilityScore: 88,
      co2FootprintKg: 1860,
      sustainabilityHighlights: [
        "GOTS-certified cotton prepared with 40% water reuse",
        "Real-time CO₂ capture feeding PA&CO ESG dashboard",
      ],
    },
    factories: [
      {
        name: "Vale do Ave Fibre Hub",
        stage: "Organic cotton prep & indigo approval",
        roles: [
          {
            key: "FIBER_PREP",
            co2Kg: 11.8,
            notes: "Lot A45 humidity balanced and contamination screened",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-07-01T08:15:00Z"),
            completedAt: new Date("2025-07-06T18:30:00Z"),
          },
          {
            key: "FABRIC_DYE_FINISH",
            co2Kg: 6.9,
            notes: "Low-liquor indigo bath – Capri blue shade",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-07-07T07:40:00Z"),
            completedAt: new Date("2025-07-09T19:10:00Z"),
          },
          {
            key: "FABRIC_INSPECTION_RELAX",
            co2Kg: 1.2,
            notes: "Shade banding < DeltaE 0.8",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-07-10T09:00:00Z"),
            completedAt: new Date("2025-07-10T14:30:00Z"),
          },
        ],
      },
      {
        name: "Braga Cutting & Assembly",
        stage: "Marker optimisation & pilot assembly",
        isPrimary: true,
        roles: [
          {
            key: "PATTERN_GRADING",
            co2Kg: 0.8,
            notes: "Digital fit aligned to Milan run-of-show size curve",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-07-11T08:20:00Z"),
            completedAt: new Date("2025-07-11T17:10:00Z"),
          },
          {
            key: "MARKER_CUTTING",
            co2Kg: 3.9,
            notes: "Gerber efficiency 89%, waste tracked in PowerBI",
            status: SupplyChainStageStatus.IN_PROGRESS,
            startedAt: new Date("2025-07-12T08:20:00Z"),
          },
          {
            key: "BUNDLING_SEWING",
            co2Kg: 6.6,
            notes: "Luxury piping attachment – 3 needle positions",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "INLINE_QC",
            co2Kg: 1.1,
            notes: "Inline QC gate every 25 units",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
      {
        name: "Vizela Laundry & Finishing",
        stage: "Print lab prep & enzyme booking",
        roles: [
          {
            key: "SCREEN_PRINTING",
            co2Kg: 4.4,
            notes: "Metallic crest screens ready, awaiting sew-off",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "GARMENT_WASH_SOFTEN",
            co2Kg: 2.9,
            notes: "Enzyme soft wash scheduled post sewing",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "IRON_PRESS_DETHREAD",
            co2Kg: 0.6,
            notes: "Steam tunnels reserved for 21 July",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
      {
        name: "Lisbon Logistics Center",
        stage: "Export consolidation",
        roles: [
          {
            key: "PACK_TAG_BAG",
            co2Kg: 0.9,
            notes: "White tissue + hanger kit reserved",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "WAREHOUSE_LOGISTICS",
            co2Kg: 5.2,
            notes: "Air consolidation to Milan Fashion Week",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "DOCUMENTATION_DPP",
            co2Kg: 0.2,
            notes: "Awaiting inline QC evidence",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
    ],
    inspections: [
      {
        inspectorEmail: "joana.costa@paco.example",
        startedAt: new Date("2025-07-14T09:30:00Z"),
        finishedAt: new Date("2025-07-14T12:00:00Z"),
        defects: [
          {
            pieceCode: "CAPRI-047",
            note: "Seam overlock tension tightened by 0.2Nm",
            defectTypeName: "Stitching",
            photos: getRandomPhotos(2),
          },
          {
            pieceCode: "CAPRI-052",
            note: "Replaced zipper puller with rhodium-plated batch",
            defectTypeName: "Hardware Issue",
            photos: getRandomPhotos(1),
          },
        ],
      },
    ],
  },
  {
    clientSlug: "paco",
    styleRef: "PA-SS25-PORTO-LINEN",
    quantityTotal: 320,
    status: LotStatus.PENDING_APPROVAL,
    defectRate: 0.7,
    inspectedProgress: 100,
    materialComposition: [
      {
        fiber: "Belgian Linen",
        percentage: 96,
        properties: { region: "Flanders", process: "dew-retted" },
      },
      {
        fiber: "Peace Silk Lining",
        percentage: 4,
        properties: { certification: "GRS" },
      },
    ],
    dyeLot: "LINEN-IVORY-03",
    certifications: [
      {
        type: "GRS",
        number: "GRS-PT-1176",
        issuer: "Textile Exchange",
        validUntil: "2026-02-01T00:00:00Z",
      },
      {
        type: "AMFORI_BSCI",
        number: "BSCI-PT-7788",
      },
    ],
    dppMetadata: {
      dppId: "DPP-PA-SS25-PORTO-LINEN",
      version: "1.0-rc",
      status: "ready-for-signoff",
      publicUrl: "http://localhost:3000/dpp/PA-SS25-PORTO-LINEN",
      lastAudit: "2025-06-18T13:10:00Z",
      traceabilityScore: 94,
      co2FootprintKg: 1420,
      sustainabilityHighlights: [
        "Closed-loop water recycling on linen bleaching",
        "Digital passport already pre-validated for Gruppo Florence",
      ],
    },
    factories: [
      {
        name: "Vale do Ave Fibre Hub",
        stage: "Linen yarn bleaching & lab approval",
        roles: [
          {
            key: "FIBER_PREP",
            co2Kg: 10.4,
            notes: "Flax fibre combing + humidity conditioning",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-05-28T07:45:00Z"),
            completedAt: new Date("2025-06-04T17:20:00Z"),
          },
          {
            key: "FABRIC_DYE_FINISH",
            co2Kg: 5.6,
            notes: "Plant-based ivory dye run with pH buffered",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-05T08:10:00Z"),
            completedAt: new Date("2025-06-06T19:00:00Z"),
          },
          {
            key: "FABRIC_WASH_PREP",
            co2Kg: 4.8,
            notes: "Relaxation tunnel 48h",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-07T06:20:00Z"),
            completedAt: new Date("2025-06-08T18:00:00Z"),
          },
          {
            key: "FABRIC_LAB_TEST",
            co2Kg: 0.5,
            notes: "Colour deltaE 0.7 vs golden sample",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-09T09:00:00Z"),
            completedAt: new Date("2025-06-09T12:45:00Z"),
          },
        ],
      },
      {
        name: "Porto Atelier & QA Lab",
        stage: "Hand-finishing & embellishment",
        isPrimary: true,
        roles: [
          {
            key: "BUNDLING_SEWING",
            co2Kg: 6.2,
            notes: "Hand-rolled lapel & AMF stitching",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-10T08:00:00Z"),
            completedAt: new Date("2025-06-15T18:10:00Z"),
          },
          {
            key: "TRIMS_EMBELLISH",
            co2Kg: 1.4,
            notes: "Mother of pearl buttons with laser engraving",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-16T08:30:00Z"),
            completedAt: new Date("2025-06-17T15:00:00Z"),
          },
          {
            key: "FINAL_QA",
            co2Kg: 0.9,
            notes: "100% inline QC — no critical defects",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-18T09:15:00Z"),
            completedAt: new Date("2025-06-18T14:20:00Z"),
          },
          {
            key: "DOCUMENTATION_DPP",
            co2Kg: 0.2,
            notes: "Digital passport compiled for PA&CO board",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-18T15:10:00Z"),
            completedAt: new Date("2025-06-18T16:45:00Z"),
          },
        ],
      },
      {
        name: "Lisbon Logistics Center",
        stage: "Export staging",
        roles: [
          {
            key: "PACK_TAG_BAG",
            co2Kg: 0.8,
            notes: "Sustainable hanger sets + recycled tissue",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-19T08:30:00Z"),
            completedAt: new Date("2025-06-19T12:45:00Z"),
          },
          {
            key: "WAREHOUSE_LOGISTICS",
            co2Kg: 4.8,
            notes: "Temperature-controlled transport booked for Milan",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-06-20T07:10:00Z"),
            completedAt: new Date("2025-06-20T11:30:00Z"),
          },
        ],
      },
    ],
    inspections: [
      {
        inspectorEmail: "joana.costa@paco.example",
        startedAt: new Date("2025-06-18T08:00:00Z"),
        finishedAt: new Date("2025-06-18T12:15:00Z"),
        defects: [
          {
            pieceCode: "LINEN-112",
            note: "Resewn armhole pick stitch for symmetry",
            defectTypeName: "Stitching",
            photos: getRandomPhotos(2),
          },
          {
            pieceCode: "LINEN-145",
            note: "Pressed out micro-crease on lapel facing",
            defectTypeName: "Fabric Defect",
            photos: getRandomPhotos(1),
          },
        ],
      },
    ],
  },
  {
    clientSlug: "paco",
    styleRef: "PA-FW24-BLACK-TUX",
    quantityTotal: 180,
    status: LotStatus.APPROVED,
    defectRate: 0.4,
    inspectedProgress: 100,
    materialComposition: [
      {
        fiber: "Super 150s Merino Wool",
        percentage: 88,
        properties: { region: "Biella", micron: 17.5 },
      },
      {
        fiber: "Mulberry Silk Lapel",
        percentage: 12,
        properties: { finish: "gloss", supplier: "Porto Atelier & QA Lab" },
      },
    ],
    dyeLot: "NOIR-ATELIER-11",
    certifications: [
      { type: "ISO_14001", issuer: "DNV" },
      { type: "AMFORI_BSCI", number: "BSCI-PT-5511" },
    ],
    dppMetadata: {
      dppId: "DPP-PA-FW24-BLACK-TUX",
      version: "1.0",
      status: "published",
      publicUrl: "http://localhost:3000/dpp/PA-FW24-BLACK-TUX",
      lastAudit: "2025-05-21T09:00:00Z",
      traceabilityScore: 96,
      co2FootprintKg: 980,
      sustainabilityHighlights: [
        "Metallic trims tracked with RFID for circularity",
        "CO₂ per unit reduced 12% vs FW23 tux capsule",
      ],
    },
    factories: [
      {
        name: "Vale do Ave Fibre Hub",
        stage: "Worsted prep & dye",
        roles: [
          {
            key: "FIBER_PREP",
            co2Kg: 9.8,
            notes: "Worsted spinning with 100% renewable energy",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-02T07:10:00Z"),
            completedAt: new Date("2025-04-05T19:30:00Z"),
          },
          {
            key: "FABRIC_DYE_FINISH",
            co2Kg: 6.1,
            notes: "Jet-black dye with cationic fixers",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-06T06:40:00Z"),
            completedAt: new Date("2025-04-07T18:45:00Z"),
          },
        ],
      },
      {
        name: "Braga Cutting & Assembly",
        stage: "Precision tailoring",
        isPrimary: true,
        roles: [
          {
            key: "PATTERN_GRADING",
            co2Kg: 0.9,
            notes: "Made-to-measure adjustments for VIP fittings",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-08T08:10:00Z"),
            completedAt: new Date("2025-04-08T18:30:00Z"),
          },
          {
            key: "BUNDLING_SEWING",
            co2Kg: 6.0,
            notes: "Hand pad-stitched lapels, black silk facings",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-09T07:50:00Z"),
            completedAt: new Date("2025-04-12T20:15:00Z"),
          },
          {
            key: "INLINE_QC",
            co2Kg: 1.0,
            notes: "Needle policy enforced, 0 broken needles",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-10T09:30:00Z"),
            completedAt: new Date("2025-04-12T20:15:00Z"),
          },
        ],
      },
      {
        name: "Porto Atelier & QA Lab",
        stage: "Detailing & QA",
        roles: [
          {
            key: "TRIMS_EMBELLISH",
            co2Kg: 1.2,
            notes: "Rhodium-plated buttons installed on line 2",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-13T08:40:00Z"),
            completedAt: new Date("2025-04-14T12:00:00Z"),
          },
          {
            key: "FINAL_QA",
            co2Kg: 0.8,
            notes: "AQL 1.0 passed, 0 critical defects",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-15T07:30:00Z"),
            completedAt: new Date("2025-04-15T13:45:00Z"),
          },
          {
            key: "DOCUMENTATION_DPP",
            co2Kg: 0.2,
            notes: "DPP published with Milan-specific annex",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-16T09:15:00Z"),
            completedAt: new Date("2025-04-16T11:10:00Z"),
          },
        ],
      },
      {
        name: "Lisbon Logistics Center",
        stage: "Distribution",
        roles: [
          {
            key: "PACK_TAG_BAG",
            co2Kg: 0.7,
            notes: "Monogram garment bags & RFID hang tags",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-17T06:30:00Z"),
            completedAt: new Date("2025-04-17T10:00:00Z"),
          },
          {
            key: "WAREHOUSE_LOGISTICS",
            co2Kg: 4.2,
            notes: "Shipment to Milan boutique delivered",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-04-17T12:00:00Z"),
            completedAt: new Date("2025-04-18T08:30:00Z"),
          },
        ],
      },
    ],
    approvals: {
      approvedByEmail: "carlos.martins@paco.example",
      decision: ApprovalDecision.APPROVE,
      note: "Approved for Gruppo Florence VIP fittings",
    },
    inspections: [
      {
        inspectorEmail: "joana.costa@paco.example",
        startedAt: new Date("2025-04-15T07:30:00Z"),
        finishedAt: new Date("2025-04-15T13:00:00Z"),
        defects: [
          {
            pieceCode: "TUX-076",
            note: "Pressed lapel sheen variance resolved (steam 14s)",
            defectTypeName: "Discoloration",
            photos: getRandomPhotos(2),
          },
        ],
      },
    ],
  },
  {
    clientSlug: "paco",
    styleRef: "PA-FW24-GALA-DRESS",
    quantityTotal: 150,
    status: LotStatus.INSPECTION,
    defectRate: 2.3,
    inspectedProgress: 78.0,
    materialComposition: [
      { fiber: "Silk Satin", percentage: 85, properties: { origin: "Como" } },
      { fiber: "Recycled Polyamide Mesh", percentage: 15, properties: { certification: "RCS" } },
    ],
    dyeLot: "SCARLET-GALA-05",
    certifications: [
      { type: "RCS", number: "RCS-IT-4401" },
      { type: "BLUESIGN", number: "BLUESIGN-PT-330" },
    ],
    dppMetadata: {
      dppId: "DPP-PA-FW24-GALA-DRESS",
      version: "0.5",
      status: "inspection",
      publicUrl: "http://localhost:3000/dpp/PA-FW24-GALA-DRESS",
      lastAudit: "2025-05-30T11:20:00Z",
      traceabilityScore: 81,
      co2FootprintKg: 1345,
      sustainabilityHighlights: [
        "Hand-beaded bodice tracked with artisan ledger",
        "Paris couture customer can reference inline photos live",
      ],
    },
    factories: [
      {
        name: "Vale do Ave Fibre Hub",
        stage: "Silk prep",
        roles: [
          {
            key: "FIBER_PREP",
            co2Kg: 12.9,
            notes: "Silk satin pre-shrunk and colour matched",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-05-05T07:00:00Z"),
            completedAt: new Date("2025-05-08T18:45:00Z"),
          },
        ],
      },
      {
        name: "Braga Cutting & Assembly",
        stage: "Corsetry assembly",
        isPrimary: true,
        roles: [
          {
            key: "PATTERN_GRADING",
            co2Kg: 1.0,
            notes: "Grade adjusted for couture fittings",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-05-09T08:10:00Z"),
            completedAt: new Date("2025-05-09T17:40:00Z"),
          },
          {
            key: "EMBROIDERY_APPLIQUE_LASER",
            co2Kg: 3.4,
            notes: "Laser-cut mesh appliqués ready",
            status: SupplyChainStageStatus.COMPLETED,
            startedAt: new Date("2025-05-10T07:20:00Z"),
            completedAt: new Date("2025-05-12T18:00:00Z"),
          },
          {
            key: "BUNDLING_SEWING",
            co2Kg: 6.8,
            notes: "Corset assembly 78% complete",
            status: SupplyChainStageStatus.IN_PROGRESS,
            startedAt: new Date("2025-05-13T08:30:00Z"),
          },
          {
            key: "INLINE_QC",
            co2Kg: 1.3,
            notes: "Interim inspection scheduled once corsetry signed off",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
      {
        name: "Porto Atelier & QA Lab",
        stage: "Hand embellishment",
        roles: [
          {
            key: "TRIMS_EMBELLISH",
            co2Kg: 1.9,
            notes: "Hand-beaded bodice line 2",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "FINAL_QA",
            co2Kg: 0.9,
            notes: "Final inspection booked for 28 May",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
      {
        name: "Vizela Laundry & Finishing",
        stage: "Soft drape finishing",
        roles: [
          {
            key: "GARMENT_WASH_SOFTEN",
            co2Kg: 2.5,
            notes: "Silk softening schedule reserved",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
          {
            key: "NEEDLE_METAL_DETECT",
            co2Kg: 0.5,
            notes: "Post-embellishment scan required",
            status: SupplyChainStageStatus.NOT_STARTED,
          },
        ],
      },
    ],
    inspections: [
      {
        inspectorEmail: "joana.costa@paco.example",
        startedAt: new Date("2025-05-20T10:00:00Z"),
        finishedAt: new Date("2025-05-20T14:30:00Z"),
        defects: [
          {
            pieceCode: "GALA-032",
            note: "Corset bone adjusted 1.5mm for symmetry",
            defectTypeName: "Measurement",
            photos: getRandomPhotos(2),
          },
          {
            pieceCode: "GALA-044",
            note: "Mesh overlay re-aligned to avoid puckering",
            defectTypeName: "Fabric Defect",
            photos: getRandomPhotos(1),
          },
        ],
      },
    ],
  },
];

function cloneSeedLots(lots: SeedLot[]): SeedLot[] {
  return lots.map((lot) => ({
    ...lot,
    factories: lot.factories?.map((factory) => ({
      ...factory,
      roles: factory.roles?.map((role) => ({
        ...role,
        startedAt: role.startedAt ? new Date(role.startedAt) : undefined,
        completedAt: role.completedAt ? new Date(role.completedAt) : undefined,
      })),
    })),
    approvals: lot.approvals ? { ...lot.approvals } : undefined,
    inspections: lot.inspections.map((inspection) => ({
      ...inspection,
      startedAt: inspection.startedAt ? new Date(inspection.startedAt) : undefined,
      finishedAt: inspection.finishedAt ? new Date(inspection.finishedAt) : undefined,
      defects: inspection.defects.map((defect) => ({
        ...defect,
        photos: [...defect.photos],
      })),
    })),
  }));
}

function generateRandomLots(): SeedLot[] {
  return cloneSeedLots(CURATED_LOTS);
}

const FEED_EVENTS: Array<{
  clientSlug: string;
  styleRef?: string;
  type: EventType;
  timestamp: string;
  payload: Record<string, any>;
}> = [
  {
    clientSlug: "paco",
    styleRef: "PA-SS25-CAPRI",
    type: EventType.DEFECT_DETECTED,
    timestamp: "2025-07-14T12:05:00Z",
    payload: {
      garmentSerial: "CAPRI-052",
      defectType: "Hardware Issue",
      supplier: "Braga Cutting & Assembly",
      summary: "Rhodium zipper pull swapped after inline QC alert.",
    },
  },
  {
    clientSlug: "paco",
    styleRef: "PA-SS25-CAPRI",
    type: EventType.LOT_AWAITING_APPROVAL,
    timestamp: "2025-07-18T09:40:00Z",
    payload: {
      factory: "Lisbon Logistics Center",
      quantityReady: 420,
      comment: "Capri capsule at 62% production – awaiting inline approval to publish DPP.",
    },
  },
  {
    clientSlug: "paco",
    styleRef: "PA-SS25-PORTO-LINEN",
    type: EventType.LOT_AWAITING_APPROVAL,
    timestamp: "2025-06-20T07:30:00Z",
    payload: {
      factory: "Porto Atelier & QA Lab",
      quantityReady: 320,
      comment: "Passport compiled, ready for PA&CO sign-off.",
    },
  },
  {
    clientSlug: "paco",
    styleRef: "PA-FW24-BLACK-TUX",
    type: EventType.LOT_DECIDED,
    timestamp: "2025-04-18T09:05:00Z",
    payload: {
      decision: ApprovalDecision.APPROVE,
      reason: "Approved for Gruppo Florence VIP fittings.",
    },
  },
  {
    clientSlug: "paco",
    styleRef: "PA-FW24-GALA-DRESS",
    type: EventType.DEFECT_DETECTED,
    timestamp: "2025-05-20T14:40:00Z",
    payload: {
      garmentSerial: "GALA-032",
      defectType: "Measurement",
      supplier: "Braga Cutting & Assembly",
      summary: "Corset bone adjusted 1.5mm for couture fit.",
    },
  },
];

@Injectable()
export class SeedService {
  private readonly logger = new Logger(SeedService.name);

  constructor(
    @InjectRepository(Tenant)
    private readonly clientRepository: Repository<Tenant>,
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
    @InjectRepository(FactoryCertification)
    private readonly factoryCertificationRepository: Repository<FactoryCertification>,
    @InjectRepository(Event)
    private readonly eventRepository: Repository<Event>,
    @InjectRepository(LotUserAssignment)
    private readonly lotUserAssignmentRepository: Repository<LotUserAssignment>,
    private readonly dppService: DppService,
  ) {}

  async seedData(): Promise<void> {
    await this.seedRoles();
    const clients = await this.seedClients();
    const supplyChainRoles = await this.seedSupplyChainRoles();
    await this.seedFactories(clients, supplyChainRoles);
    const defectTypes = await this.seedDefectTypes();
    const users = await this.seedUsers(clients);
    await this.clearExistingData();
    const seededLots = await this.seedLots(clients, defectTypes, users, supplyChainRoles);
    await this.assignLotsToClientViewers(users, seededLots);
    await this.seedDpps(clients, users, seededLots);
    await this.seedEvents(clients, seededLots);
  }

  private async clearExistingData(): Promise<void> {
    this.logger.log('Clearing existing lot and DPP data...');

    await this.eventRepository.query('DELETE FROM events');
    await this.photoRepository.query('DELETE FROM photos');
    await this.defectRepository.query('DELETE FROM defects');
    await this.inspectionRepository.query('DELETE FROM inspections');
    await this.approvalRepository.query('DELETE FROM approvals');
    await this.lotUserAssignmentRepository.query('DELETE FROM lot_user_assignments');
    await this.lotFactoryRoleRepository.query('DELETE FROM lot_factory_roles');
    await this.lotFactoryRepository.query('DELETE FROM lot_factories');
    // DPPs will be handled by the DppService
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

  private async seedClients(): Promise<Map<string, Tenant>> {
    const map = new Map<string, Tenant>();

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
    clients: Map<string, Tenant>,
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<void> {
    for (const factorySeed of FACTORIES) {
      const client = clients.get(factorySeed.clientSlug);
      if (!client) {
        continue;
      }

      let factory = await this.factoryRepository.findOne({
        where: { name: factorySeed.name, tenantId: client.id },
        relations: ["capabilities", "capabilities.role"],
      });

      if (!factory) {
        factory = this.factoryRepository.create({
          tenantId: client.id,
          name: factorySeed.name,
          city: factorySeed.city,
          country: factorySeed.country,
        });
        factory = await this.factoryRepository.save(factory);
      }

      await this.syncFactoryCapabilities(factory.id, factorySeed.roles ?? [], supplyChainRoles);
      await this.syncFactoryCertifications(factory.id, factorySeed.certifications ?? []);
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

  private async syncFactoryCertifications(
    factoryId: string,
    certifications: string[] = [],
  ): Promise<void> {
    await this.factoryCertificationRepository.delete({ factoryId });

    if (!certifications.length) {
      return;
    }

    const entries = certifications
      .map((certification) => certification?.trim())
      .filter((value): value is string => Boolean(value))
      .map((value) =>
        this.factoryCertificationRepository.create({
          factoryId,
          certification: value,
        }),
      );

    if (entries.length) {
      await this.factoryCertificationRepository.save(entries);
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
        const status = roleSeed.status ?? SupplyChainStageStatus.NOT_STARTED;

        return this.lotFactoryRoleRepository.create({
          lotFactoryId,
          roleId: role.id,
          sequence,
          co2Kg: co2,
          notes: roleSeed.notes ?? null,
          status,
          startedAt: roleSeed.startedAt ?? null,
          completedAt: roleSeed.completedAt ?? null,
        });
      })
      .filter((value): value is LotFactoryRole => Boolean(value));

    if (entries.length) {
      await this.lotFactoryRoleRepository.save(entries);
    }
  }

  private async seedUsers(clients: Map<string, Tenant>): Promise<Map<string, User>> {
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
            tenantId: client.id,
          });
          user = await this.userRepository.save(user);
        } else if (!user.tenantId) {
          user.tenantId = client.id;
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
    clients: Map<string, Tenant>,
    defectTypes: Map<string, DefectType>,
    users: Map<string, User>,
    supplyChainRoles: Map<string, SupplyChainRole>,
  ): Promise<Map<string, Lot>> {
    const lots = generateRandomLots();
    const seededLots = new Map<string, Lot>();
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
          tenantId: client.id,
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
        where: { tenantId: client.id, styleRef: lotSeed.styleRef },
      });

      if (!lot) {
        lot = this.lotRepository.create({
          tenantId: client.id,
          factoryId: primaryFactoryId,
          styleRef: lotSeed.styleRef,
          quantityTotal: lotSeed.quantityTotal,
          status: lotSeed.status,
          defectRate: lotSeed.defectRate,
          inspectedProgress: lotSeed.inspectedProgress,
          materialComposition: lotSeed.materialComposition ?? null,
          dyeLot: lotSeed.dyeLot ?? null,
          certifications: lotSeed.certifications ?? null,
          dppMetadata: lotSeed.dppMetadata ?? null,
        });
        lot = await this.lotRepository.save(lot);
      } else {
        lot.status = lotSeed.status;
        lot.defectRate = lotSeed.defectRate;
        lot.inspectedProgress = lotSeed.inspectedProgress;
        lot.factoryId = primaryFactoryId;
        lot.materialComposition = lotSeed.materialComposition ?? null;
        lot.dyeLot = lotSeed.dyeLot ?? null;
        lot.certifications = lotSeed.certifications ?? null;
        lot.dppMetadata = lotSeed.dppMetadata ?? null;
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
      seededLots.set(lotSeed.styleRef, lot);
    }
    return seededLots;
  }

  private async assignLotsToClientViewers(
    users: Map<string, User>,
    lots: Map<string, Lot>,
  ): Promise<void> {
    const viewerEmails = Object.values(USERS)
      .flat()
      .filter((seedUser) => seedUser.roles.includes(UserRole.CLIENT_VIEWER))
      .map((seedUser) => seedUser.email);

    if (!viewerEmails.length) {
      return;
    }

    const seededLotIds = Array.from(lots.values())
      .sort((a, b) => a.styleRef.localeCompare(b.styleRef))
      .slice(0, 5)
      .map((lot) => lot.id);

    for (const email of viewerEmails) {
      const viewer = users.get(email);
      if (!viewer) {
        continue;
      }

      await this.lotUserAssignmentRepository.delete({ userId: viewer.id });

      if (!seededLotIds.length) {
        continue;
      }

      await this.lotUserAssignmentRepository.save(
        seededLotIds.map((lotId) =>
          this.lotUserAssignmentRepository.create({ lotId, userId: viewer.id }),
        ),
      );
    }
  }

  private async seedDpps(
    clients: Map<string, Tenant>,
    users: Map<string, User>,
    seededLots: Map<string, Lot>,
  ): Promise<void> {
    this.logger.log('Seeding DPPs...');

    for (const [styleRef, lot] of seededLots) {
      if (lot.dppMetadata?.dppId) {
        const client = Array.from(clients.values()).find(c => c.id === lot.tenantId);
        const adminUser = Array.from(users.values()).find(u =>
          u.tenantId === lot.tenantId && u.userRoles?.some(ur => ur.role?.name === UserRole.ADMIN)
        );

        if (!client || !adminUser) continue;

        // Check if DPP already exists by styleRef
        const existing = await this.dppService.getPublicDpp(styleRef);

        if (!existing) {
          // Create materials from lot composition
          const materials = lot.materialComposition?.map(material => ({
            fiber: material.fiber,
            percent: material.percentage,
            certs: material.properties?.certifications || []
          })) || [];

          // Create sustainability highlights
          const sustainabilityHighlights = lot.dppMetadata?.sustainabilityHighlights || [
            "Sustainable cotton sourcing",
            "Low water impact dyeing"
          ];

          // Create certifications
          const certifications = lot.certifications?.map(cert => cert.type) || [];

          // Create the public payload following the schema
          const publicPayload = {
            product: {
              brand: 'PA&CO',
              styleRef: lot.styleRef,
              sku: lot.styleRef,
              gtin: null,
              images: []
            },
            materials,
            care: {},
            sustainability: {
              highlights: sustainabilityHighlights,
              certifications
            },
            end_of_life: {}
          };

          // Create the DTO
          const createDppDto: CreateDppDto = {
            productSku: lot.styleRef,
            gtin: null,
            brand: 'PA&CO',
            styleRef: lot.styleRef,
            publicPayload,
            restrictedPayload: {}
          };

          try {
            const dpp = await this.dppService.createDpp(lot.tenantId, adminUser.id, createDppDto);

            // Publish if lot is approved
            if (lot.status === LotStatus.APPROVED) {
              await this.dppService.publishDpp(dpp.id, lot.tenantId, adminUser.id);
            }

            this.logger.log(`Created DPP for: ${styleRef}`);
          } catch (error) {
            this.logger.error(`Failed to create DPP for ${styleRef}:`, error);
          }
        }
      }
    }
  }

  private async seedEvents(
    clients: Map<string, Tenant>,
    seededLots: Map<string, Lot>,
  ): Promise<void> {
    if (!FEED_EVENTS.length) {
      return;
    }

    const entries = FEED_EVENTS
      .map((feedEvent) => {
        const client = clients.get(feedEvent.clientSlug);
        if (!client) {
          return null;
        }

        const lot = feedEvent.styleRef ? seededLots.get(feedEvent.styleRef) : undefined;
        const timestamp = new Date(feedEvent.timestamp);

        return this.eventRepository.create({
          tenantId: client.id,
          lotId: lot?.id ?? null,
          type: feedEvent.type,
          payload: {
            ...feedEvent.payload,
            lotId: lot?.id ?? feedEvent.payload?.lotId ?? null,
            styleRef: feedEvent.styleRef ?? lot?.styleRef ?? null,
          },
          createdAt: timestamp,
        });
      })
      .filter((value): value is Event => Boolean(value));

    if (entries.length) {
      entries.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
      await this.eventRepository.save(entries);
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

    const existingProgress = roles.some(
      (role) => role.status !== SupplyChainStageStatus.NOT_STARTED,
    );

    if (existingProgress) {
      return;
    }

    const first = roles[0];
    first.status = SupplyChainStageStatus.IN_PROGRESS;
    first.startedAt = new Date();
    first.completedAt = null;
    await this.lotFactoryRoleRepository.save(first);
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
