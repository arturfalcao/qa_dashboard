import { MigrationInterface, QueryRunner } from "typeorm";

export class AddMissingReportTypes1758853000000 implements MigrationInterface {
  name = "AddMissingReportTypes1758853000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'EXECUTIVE_QUALITY_SUMMARY';
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'LOT_INSPECTION_REPORT';
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'MEASUREMENT_COMPLIANCE_SHEET';
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'PACKAGING_READINESS_REPORT';
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'SUPPLIER_PERFORMANCE_SNAPSHOT';
      ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'CAPA_REPORT';
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
  }
}