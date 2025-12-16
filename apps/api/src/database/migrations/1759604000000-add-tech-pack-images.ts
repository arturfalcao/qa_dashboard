import { MigrationInterface, QueryRunner } from "typeorm";

export class AddTechPackImages1759604000000 implements MigrationInterface {
  name = "AddTechPackImages1759604000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "tech_packs"
      ADD COLUMN IF NOT EXISTS "images" jsonb DEFAULT NULL
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE "tech_packs"
      DROP COLUMN IF EXISTS "images"
    `);
  }
}
