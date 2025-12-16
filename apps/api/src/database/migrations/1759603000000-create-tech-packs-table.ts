import { MigrationInterface, QueryRunner } from "typeorm";

export class CreateTechPacksTable1759603000000 implements MigrationInterface {
  name = "CreateTechPacksTable1759603000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Create tech_packs table
    await queryRunner.query(`
      CREATE TABLE "tech_packs" (
        "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
        "tenant_id" uuid NOT NULL,
        "style_ref" varchar(120) NOT NULL,
        "product_name" varchar(255),
        "season" varchar(50),
        "designer" varchar(120),
        "sample_size" varchar(50),
        "size_range" jsonb,
        "file_key" varchar(500),
        "file_name" varchar(255),
        "file_size" int,
        "status" varchar(50) NOT NULL DEFAULT 'pending',
        "processing_error" text,
        "material_composition" jsonb,
        "colorways" jsonb,
        "size_specifications" jsonb,
        "measurement_tolerances" jsonb,
        "grading" jsonb,
        "construction_details" jsonb,
        "artwork" jsonb,
        "fabric_map" jsonb,
        "labels" jsonb,
        "hang_tags" jsonb,
        "packaging" jsonb,
        "folding_instructions" jsonb,
        "care_instructions" jsonb,
        "bill_of_materials" jsonb,
        "raw_extracted_data" jsonb,
        "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        "processed_at" TIMESTAMP WITH TIME ZONE,
        CONSTRAINT "tech_packs_pkey" PRIMARY KEY ("id"),
        CONSTRAINT "tech_packs_tenant_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("id") ON DELETE CASCADE
      )
    `);

    // Create indexes
    await queryRunner.query(`
      CREATE INDEX "idx_tech_packs_tenant_id" ON "tech_packs" ("tenant_id")
    `);
    await queryRunner.query(`
      CREATE INDEX "idx_tech_packs_style_ref" ON "tech_packs" ("tenant_id", "style_ref")
    `);
    await queryRunner.query(`
      CREATE INDEX "idx_tech_packs_status" ON "tech_packs" ("status")
    `);

    // Add tech_pack_id to lots table
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "tech_pack_id" uuid,
      ADD CONSTRAINT "lots_tech_pack_fkey" FOREIGN KEY ("tech_pack_id") REFERENCES "tech_packs"("id") ON DELETE SET NULL
    `);

    // Create index for the foreign key
    await queryRunner.query(`
      CREATE INDEX "idx_lots_tech_pack_id" ON "lots" ("tech_pack_id")
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Remove foreign key and column from lots
    await queryRunner.query(`
      ALTER TABLE "lots" DROP CONSTRAINT IF EXISTS "lots_tech_pack_fkey"
    `);
    await queryRunner.query(`
      DROP INDEX IF EXISTS "idx_lots_tech_pack_id"
    `);
    await queryRunner.query(`
      ALTER TABLE "lots" DROP COLUMN IF EXISTS "tech_pack_id"
    `);

    // Drop tech_packs table
    await queryRunner.query(`
      DROP INDEX IF EXISTS "idx_tech_packs_status"
    `);
    await queryRunner.query(`
      DROP INDEX IF EXISTS "idx_tech_packs_style_ref"
    `);
    await queryRunner.query(`
      DROP INDEX IF EXISTS "idx_tech_packs_tenant_id"
    `);
    await queryRunner.query(`
      DROP TABLE IF EXISTS "tech_packs"
    `);
  }
}
