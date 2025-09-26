import { MigrationInterface, QueryRunner } from "typeorm";

interface CatalogEntry {
  key: string;
  name: string;
  description: string;
  sequence: number;
  co2: number;
}

const catalog: CatalogEntry[] = [
  { key: "FIBER_PREP", name: "Fiber Preparation", description: "Raw material sourcing, ginning, spinning, or knitting base fabrics", sequence: 10, co2: 12.5 },
  { key: "FABRIC_DYE_FINISH", name: "Fabric Dye & Finish", description: "Piece dyeing, finishing, and chemical treatments on greige fabric", sequence: 20, co2: 7.1 },
  { key: "FABRIC_WASH_PREP", name: "Fabric Wash & Prep", description: "Washing, mercerising, pre-shrinking and conditioning", sequence: 30, co2: 5.0 },
  { key: "FABRIC_INSPECTION_RELAX", name: "Fabric Inspection & Relaxing", description: "Inspection, relaxing and defect flagging before cutting", sequence: 40, co2: 2.2 },
  { key: "PATTERN_GRADING", name: "Pattern & Grading", description: "Pattern development, grading and tech pack validation", sequence: 50, co2: 1.0 },
  { key: "MARKER_CUTTING", name: "Marker Making & Cutting", description: "Marker optimization, spreading and cutting", sequence: 60, co2: 4.2 },
  { key: "EMBROIDERY_APPLIQUE_LASER", name: "Embroidery / Applique / Laser", description: "Embroidery, applique or laser work prior to assembly", sequence: 70, co2: 3.2 },
  { key: "BUNDLING_SEWING", name: "Bundling & Sewing", description: "Bundling cut parts and full garment assembly", sequence: 80, co2: 6.8 },
  { key: "INLINE_QC", name: "Inline Quality Control", description: "Inline inspections during sewing", sequence: 90, co2: 1.5 },
  { key: "SCREEN_PRINTING", name: "Screen Printing", description: "Silk-screen decoration on panels or finished garments", sequence: 100, co2: 2.4 },
  { key: "HEAT_TRANSFER", name: "Heat Transfer", description: "Heat transfer graphics and labels", sequence: 110, co2: 1.8 },
  { key: "SUBLIMATION", name: "Sublimation Printing", description: "Sublimation prints after or before assembly", sequence: 120, co2: 2.1 },
  { key: "DIGITAL_PRINTING", name: "Digital Printing", description: "Direct-to-garment or direct-to-film printing", sequence: 130, co2: 2.3 },
  { key: "TRIMS_EMBELLISH", name: "Trims & Embellishments", description: "Attachment of trims, hardware and embellishments", sequence: 140, co2: 1.9 },
  { key: "GARMENT_WASH_SOFTEN", name: "Garment Wash & Soften", description: "Post-assembly washing, softening and special finishes", sequence: 150, co2: 3.4 },
  { key: "FINAL_QA", name: "Final Quality Assurance", description: "Final inspection and approval gating", sequence: 160, co2: 1.6 },
  { key: "IRON_PRESS_DETHREAD", name: "Ironing, Pressing & Dethreading", description: "Pressing, ironing and removing loose threads", sequence: 170, co2: 1.2 },
  { key: "NEEDLE_METAL_DETECT", name: "Needle & Metal Detection", description: "Needle, metal detection and safety checks", sequence: 180, co2: 0.8 },
  { key: "PACK_TAG_BAG", name: "Pack, Tag & Bag", description: "Tagging, folding, bagging and boxing", sequence: 190, co2: 1.1 },
  { key: "WAREHOUSE_LOGISTICS", name: "Warehouse & Logistics", description: "Warehousing, staging and outbound logistics", sequence: 200, co2: 8.6 },
  { key: "FABRIC_LAB_TEST", name: "Fabric Lab Testing", description: "Lab dips, colorfastness and physical testing", sequence: 905, co2: 0.5 },
  { key: "FUNCTIONAL_COATING", name: "Functional Coating", description: "Water repellency, antimicrobial and technical coatings", sequence: 910, co2: 1.7 },
  { key: "REGULATORY_CHECKS", name: "Regulatory Checks", description: "Compliance audits and certification checks", sequence: 920, co2: 0.4 },
  { key: "SUSTAINABILITY_TRACK", name: "Sustainability Tracking", description: "Carbon, water and waste tracking", sequence: 930, co2: 0.3 },
  { key: "DOCUMENTATION_DPP", name: "Documentation & DPP", description: "Documentation, DPP and client reporting", sequence: 940, co2: 0.2 },
];

const renameMap: Array<[string, string]> = [
  ["fibre-prep", "FIBER_PREP"],
  ["dyeing", "FABRIC_DYE_FINISH"],
  ["cutting", "MARKER_CUTTING"],
  ["sewing", "BUNDLING_SEWING"],
  ["laundry", "GARMENT_WASH_SOFTEN"],
  ["quality", "FINAL_QA"],
  ["packaging", "PACK_TAG_BAG"],
  ["logistics", "WAREHOUSE_LOGISTICS"],
];

export class AlignSupplyChainCatalog1727280400000 implements MigrationInterface {
  name = "AlignSupplyChainCatalog1727280400000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    for (const [from, to] of renameMap) {
      await queryRunner.query(
        `UPDATE supply_chain_roles SET key = $2 WHERE key = $1`,
        [from, to],
      );
    }

    for (const entry of catalog) {
      await queryRunner.query(
        `INSERT INTO supply_chain_roles (key, name, description, default_sequence, default_co2_kg)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (key) DO UPDATE
         SET name = EXCLUDED.name,
             description = EXCLUDED.description,
             default_sequence = EXCLUDED.default_sequence,
             default_co2_kg = EXCLUDED.default_co2_kg,
             updated_at = now();`,
        [entry.key, entry.name, entry.description, entry.sequence, entry.co2],
      );
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    const reverseMap: Array<[string, string]> = [
      ["FIBER_PREP", "fibre-prep"],
      ["FABRIC_DYE_FINISH", "dyeing"],
      ["MARKER_CUTTING", "cutting"],
      ["BUNDLING_SEWING", "sewing"],
      ["GARMENT_WASH_SOFTEN", "laundry"],
      ["FINAL_QA", "quality"],
      ["PACK_TAG_BAG", "packaging"],
      ["WAREHOUSE_LOGISTICS", "logistics"],
    ];

    const legacyKeys = new Set(reverseMap.map(([, legacy]) => legacy));
    const removable = catalog
      .map((entry) => entry.key)
      .filter((key) => !reverseMap.find(([modern]) => modern === key));

    if (removable.length) {
      await queryRunner.query(
        `DELETE FROM supply_chain_roles WHERE key = ANY($1::text[])`,
        [removable],
      );
    }

    for (const [from, to] of reverseMap) {
      await queryRunner.query(
        `UPDATE supply_chain_roles SET key = $2, name = INITCAP(REPLACE($2,'_',' ')) WHERE key = $1`,
        [from, to],
      );
    }

    for (const legacyKey of legacyKeys) {
      await queryRunner.query(
        `UPDATE supply_chain_roles
         SET default_sequence = 0
         WHERE key = $1`,
        [legacyKey],
      );
    }
  }
}
