import { MigrationInterface, QueryRunner } from "typeorm";

export class AddTechPackFields1759601000000 implements MigrationInterface {
  name = "AddTechPackFields1759601000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add labels column
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "labels" jsonb NULL
    `);

    // Add hang_tags column
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "hang_tags" jsonb NULL
    `);

    // Add packaging column
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "packaging" jsonb NULL
    `);

    // Add folding_instructions column
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "folding_instructions" jsonb NULL
    `);

    // Add bill_of_materials column
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "bill_of_materials" jsonb NULL
    `);

    // Add comments
    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."labels" IS 'Label specifications from tech pack'
    `);

    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."hang_tags" IS 'Hang tag specifications from tech pack'
    `);

    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."packaging" IS 'Packaging specifications from tech pack'
    `);

    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."folding_instructions" IS 'Folding instructions from tech pack'
    `);

    await queryRunner.query(`
      COMMENT ON COLUMN "lots"."bill_of_materials" IS 'Bill of materials from tech pack'
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Drop columns
    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "bill_of_materials"
    `);

    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "folding_instructions"
    `);

    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "packaging"
    `);

    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "hang_tags"
    `);

    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "labels"
    `);
  }
}
