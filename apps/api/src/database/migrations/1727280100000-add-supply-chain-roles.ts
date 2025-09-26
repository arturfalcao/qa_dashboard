import { MigrationInterface, QueryRunner, Table, TableForeignKey, TableIndex } from "typeorm";

const defaultRoles = [
  {
    key: "FIBER_PREP",
    name: "Fiber Preparation",
    description: "Raw material sourcing, ginning, spinning, or knitting base fabrics",
    defaultSequence: 10,
    defaultCo2Kg: 12.5,
  },
  {
    key: "FABRIC_DYE_FINISH",
    name: "Fabric Dye & Finish",
    description: "Piece dyeing, finishing, and chemical treatments on greige fabric",
    defaultSequence: 20,
    defaultCo2Kg: 7.1,
  },
  {
    key: "FABRIC_WASH_PREP",
    name: "Fabric Wash & Prep",
    description: "Washing, mercerising, pre-shrinking and conditioning",
    defaultSequence: 30,
    defaultCo2Kg: 5.0,
  },
  {
    key: "FABRIC_INSPECTION_RELAX",
    name: "Fabric Inspection & Relaxing",
    description: "Inspection, relaxing and defect flagging before cutting",
    defaultSequence: 40,
    defaultCo2Kg: 2.2,
  },
  {
    key: "PATTERN_GRADING",
    name: "Pattern & Grading",
    description: "Pattern development, grading and tech pack validation",
    defaultSequence: 50,
    defaultCo2Kg: 1.0,
  },
  {
    key: "MARKER_CUTTING",
    name: "Marker Making & Cutting",
    description: "Marker optimization, spreading and cutting",
    defaultSequence: 60,
    defaultCo2Kg: 4.2,
  },
  {
    key: "EMBROIDERY_APPLIQUE_LASER",
    name: "Embroidery / Applique / Laser",
    description: "Embroidery, applique or laser work prior to assembly",
    defaultSequence: 70,
    defaultCo2Kg: 3.2,
  },
  {
    key: "BUNDLING_SEWING",
    name: "Bundling & Sewing",
    description: "Bundling cut parts and full garment assembly",
    defaultSequence: 80,
    defaultCo2Kg: 6.8,
  },
  {
    key: "INLINE_QC",
    name: "Inline Quality Control",
    description: "Inline inspections during sewing",
    defaultSequence: 90,
    defaultCo2Kg: 1.5,
  },
  {
    key: "SCREEN_PRINTING",
    name: "Screen Printing",
    description: "Silk-screen decoration on panels or finished garments",
    defaultSequence: 100,
    defaultCo2Kg: 2.4,
  },
  {
    key: "HEAT_TRANSFER",
    name: "Heat Transfer",
    description: "Heat transfer graphics and labels",
    defaultSequence: 110,
    defaultCo2Kg: 1.8,
  },
  {
    key: "SUBLIMATION",
    name: "Sublimation Printing",
    description: "Sublimation prints after or before assembly",
    defaultSequence: 120,
    defaultCo2Kg: 2.1,
  },
  {
    key: "DIGITAL_PRINTING",
    name: "Digital Printing",
    description: "Direct-to-garment or direct-to-film printing",
    defaultSequence: 130,
    defaultCo2Kg: 2.3,
  },
  {
    key: "TRIMS_EMBELLISH",
    name: "Trims & Embellishments",
    description: "Attachment of trims, hardware and embellishments",
    defaultSequence: 140,
    defaultCo2Kg: 1.9,
  },
  {
    key: "GARMENT_WASH_SOFTEN",
    name: "Garment Wash & Soften",
    description: "Post-assembly washing, softening and special finishes",
    defaultSequence: 150,
    defaultCo2Kg: 3.4,
  },
  {
    key: "FINAL_QA",
    name: "Final Quality Assurance",
    description: "Final inspection and approval gating",
    defaultSequence: 160,
    defaultCo2Kg: 1.6,
  },
  {
    key: "IRON_PRESS_DETHREAD",
    name: "Ironing, Pressing & Dethreading",
    description: "Pressing, ironing and removing loose threads",
    defaultSequence: 170,
    defaultCo2Kg: 1.2,
  },
  {
    key: "NEEDLE_METAL_DETECT",
    name: "Needle & Metal Detection",
    description: "Needle, metal detection and safety checks",
    defaultSequence: 180,
    defaultCo2Kg: 0.8,
  },
  {
    key: "PACK_TAG_BAG",
    name: "Pack, Tag & Bag",
    description: "Tagging, folding, bagging and boxing",
    defaultSequence: 190,
    defaultCo2Kg: 1.1,
  },
  {
    key: "WAREHOUSE_LOGISTICS",
    name: "Warehouse & Logistics",
    description: "Warehousing, staging and outbound logistics",
    defaultSequence: 200,
    defaultCo2Kg: 8.6,
  },
  {
    key: "FABRIC_LAB_TEST",
    name: "Fabric Lab Testing",
    description: "Lab dips, colorfastness and physical testing",
    defaultSequence: 905,
    defaultCo2Kg: 0.5,
  },
  {
    key: "FUNCTIONAL_COATING",
    name: "Functional Coating",
    description: "Water repellency, antimicrobial and technical coatings",
    defaultSequence: 910,
    defaultCo2Kg: 1.7,
  },
  {
    key: "REGULATORY_CHECKS",
    name: "Regulatory Checks",
    description: "Compliance audits and certification checks",
    defaultSequence: 920,
    defaultCo2Kg: 0.4,
  },
  {
    key: "SUSTAINABILITY_TRACK",
    name: "Sustainability Tracking",
    description: "Carbon, water and waste tracking",
    defaultSequence: 930,
    defaultCo2Kg: 0.3,
  },
  {
    key: "DOCUMENTATION_DPP",
    name: "Documentation & DPP",
    description: "Documentation, DPP and client reporting",
    defaultSequence: 940,
    defaultCo2Kg: 0.2,
  },
];

export class AddSupplyChainRoles1727280100000 implements MigrationInterface {
  name = "AddSupplyChainRoles1727280100000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.createTable(
      new Table({
        name: "supply_chain_roles",
        columns: [
          {
            name: "id",
            type: "uuid",
            isPrimary: true,
            generationStrategy: "uuid",
            default: "uuid_generate_v4()",
          },
          {
            name: "key",
            type: "text",
            isUnique: true,
          },
          {
            name: "name",
            type: "text",
          },
          {
            name: "description",
            type: "text",
            isNullable: true,
          },
          {
            name: "default_sequence",
            type: "integer",
            default: 0,
          },
          {
            name: "default_co2_kg",
            type: "numeric",
            precision: 10,
            scale: 3,
            default: 0,
          },
          {
            name: "created_at",
            type: "timestamptz",
            default: "now()",
          },
          {
            name: "updated_at",
            type: "timestamptz",
            default: "now()",
          },
        ],
      }),
      true,
    );

    await queryRunner.createTable(
      new Table({
        name: "factory_roles",
        columns: [
          {
            name: "id",
            type: "uuid",
            isPrimary: true,
            generationStrategy: "uuid",
            default: "uuid_generate_v4()",
          },
          {
            name: "factory_id",
            type: "uuid",
          },
          {
            name: "role_id",
            type: "uuid",
          },
          {
            name: "co2_override_kg",
            type: "numeric",
            precision: 10,
            scale: 3,
            isNullable: true,
          },
          {
            name: "notes",
            type: "text",
            isNullable: true,
          },
          {
            name: "created_at",
            type: "timestamptz",
            default: "now()",
          },
          {
            name: "updated_at",
            type: "timestamptz",
            default: "now()",
          },
        ],
      }),
      true,
    );

    await queryRunner.createTable(
      new Table({
        name: "lot_factory_roles",
        columns: [
          {
            name: "id",
            type: "uuid",
            isPrimary: true,
            generationStrategy: "uuid",
            default: "uuid_generate_v4()",
          },
          {
            name: "lot_factory_id",
            type: "uuid",
          },
          {
            name: "role_id",
            type: "uuid",
          },
          {
            name: "sequence",
            type: "integer",
            default: 0,
          },
          {
            name: "co2_kg",
            type: "numeric",
            precision: 10,
            scale: 3,
            isNullable: true,
          },
          {
            name: "notes",
            type: "text",
            isNullable: true,
          },
          {
            name: "created_at",
            type: "timestamptz",
            default: "now()",
          },
          {
            name: "updated_at",
            type: "timestamptz",
            default: "now()",
          },
        ],
      }),
      true,
    );

    await queryRunner.createForeignKey(
      "factory_roles",
      new TableForeignKey({
        columnNames: ["factory_id"],
        referencedTableName: "factories",
        referencedColumnNames: ["id"],
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createForeignKey(
      "factory_roles",
      new TableForeignKey({
        columnNames: ["role_id"],
        referencedTableName: "supply_chain_roles",
        referencedColumnNames: ["id"],
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createForeignKey(
      "lot_factory_roles",
      new TableForeignKey({
        columnNames: ["lot_factory_id"],
        referencedTableName: "lot_factories",
        referencedColumnNames: ["id"],
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createForeignKey(
      "lot_factory_roles",
      new TableForeignKey({
        columnNames: ["role_id"],
        referencedTableName: "supply_chain_roles",
        referencedColumnNames: ["id"],
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createIndex(
      "factory_roles",
      new TableIndex({ name: "uniq_factory_roles_factory_role", columnNames: ["factory_id", "role_id"], isUnique: true }),
    );

    await queryRunner.createIndex(
      "lot_factory_roles",
      new TableIndex({ name: "uniq_lot_factory_roles_fact_role", columnNames: ["lot_factory_id", "role_id"], isUnique: true }),
    );

    await queryRunner.query(`ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email`);
    await queryRunner.query(
      `ALTER TABLE users ADD CONSTRAINT uq_users_client_email UNIQUE (client_id, email)`,
    );

    for (const role of defaultRoles) {
      await queryRunner.query(
        `INSERT INTO supply_chain_roles (key, name, description, default_sequence, default_co2_kg)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (key) DO UPDATE SET
           name = EXCLUDED.name,
           description = EXCLUDED.description,
           default_sequence = EXCLUDED.default_sequence,
           default_co2_kg = EXCLUDED.default_co2_kg`,
        [role.key, role.name, role.description, role.defaultSequence, role.defaultCo2Kg],
      );
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_client_email`,
    );
    await queryRunner.query(`ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email)`);

    await queryRunner.dropIndex("lot_factory_roles", "uniq_lot_factory_roles_fact_role");
    await queryRunner.dropIndex("factory_roles", "uniq_factory_roles_factory_role");

    await queryRunner.dropTable("lot_factory_roles");
    await queryRunner.dropTable("factory_roles");
    await queryRunner.dropTable("supply_chain_roles");
  }
}
