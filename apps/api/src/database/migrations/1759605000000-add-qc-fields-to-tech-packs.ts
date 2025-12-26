import { MigrationInterface, QueryRunner } from "typeorm";

export class AddQcFieldsToTechPacks1759605000000 implements MigrationInterface {
  name = "AddQcFieldsToTechPacks1759605000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add new QC-specific columns to tech_packs table
    await queryRunner.query(`
      ALTER TABLE "tech_packs"
      ADD COLUMN IF NOT EXISTS "points_of_measure" jsonb,
      ADD COLUMN IF NOT EXISTS "label_sequence" jsonb,
      ADD COLUMN IF NOT EXISTS "packaging_instructions" jsonb,
      ADD COLUMN IF NOT EXISTS "care_symbols" jsonb,
      ADD COLUMN IF NOT EXISTS "sample_review" jsonb,
      ADD COLUMN IF NOT EXISTS "fit_comments" jsonb,
      ADD COLUMN IF NOT EXISTS "measurement_unit" varchar(20),
      ADD COLUMN IF NOT EXISTS "revision" varchar(50)
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "tech_packs"
      DROP COLUMN IF EXISTS "points_of_measure",
      DROP COLUMN IF EXISTS "label_sequence",
      DROP COLUMN IF EXISTS "packaging_instructions",
      DROP COLUMN IF EXISTS "care_symbols",
      DROP COLUMN IF EXISTS "sample_review",
      DROP COLUMN IF EXISTS "fit_comments",
      DROP COLUMN IF EXISTS "measurement_unit",
      DROP COLUMN IF EXISTS "revision"
    `);
  }
}
