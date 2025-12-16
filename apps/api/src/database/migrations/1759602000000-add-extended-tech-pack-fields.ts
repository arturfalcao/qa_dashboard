import { MigrationInterface, QueryRunner } from "typeorm";

export class AddExtendedTechPackFields1759602000000
  implements MigrationInterface
{
  name = "AddExtendedTechPackFields1759602000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add new tech pack metadata fields
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "season" varchar(50),
      ADD COLUMN IF NOT EXISTS "designer" varchar(120),
      ADD COLUMN IF NOT EXISTS "sample_size" varchar(50),
      ADD COLUMN IF NOT EXISTS "product_name" varchar(255)
    `);

    // Add colorways - detailed color specifications with materials
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "colorways" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."colorways" IS 'Color specifications with Pantone refs, fabric, thread, trim details'
    `);

    // Add construction details - stitching and assembly specs
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "construction_details" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."construction_details" IS 'Construction and stitching specifications per garment area'
    `);

    // Add artwork specifications
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "artwork" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."artwork" IS 'Artwork, prints, embroidery specifications with dimensions and colors'
    `);

    // Add fabric map - zones for different fabric types
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "fabric_map" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."fabric_map" IS 'Fabric placement map showing main/sub/trim/lining zones'
    `);

    // Add care instructions - multi-language
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "care_instructions" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."care_instructions" IS 'Care and wash instructions in multiple languages'
    `);

    // Add measurement tolerances
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "measurement_tolerances" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."measurement_tolerances" IS 'Tolerance specifications per measurement point'
    `);

    // Add grading specs for size scaling
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN IF NOT EXISTS "grading" jsonb
    `);
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."grading" IS 'Size grading specifications showing increments between sizes'
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN IF EXISTS "season",
      DROP COLUMN IF EXISTS "designer",
      DROP COLUMN IF EXISTS "sample_size",
      DROP COLUMN IF EXISTS "product_name",
      DROP COLUMN IF EXISTS "colorways",
      DROP COLUMN IF EXISTS "construction_details",
      DROP COLUMN IF EXISTS "artwork",
      DROP COLUMN IF EXISTS "fabric_map",
      DROP COLUMN IF EXISTS "care_instructions",
      DROP COLUMN IF EXISTS "measurement_tolerances",
      DROP COLUMN IF EXISTS "grading"
    `);
  }
}
