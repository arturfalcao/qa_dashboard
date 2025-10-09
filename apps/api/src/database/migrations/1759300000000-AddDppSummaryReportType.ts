import { MigrationInterface, QueryRunner } from "typeorm";

export class AddDppSummaryReportType1759300000000 implements MigrationInterface {
  name = "AddDppSummaryReportType1759300000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // First, check if the enum exists and what values it has
    const checkEnum = await queryRunner.query(`
      SELECT enumlabel
      FROM pg_enum
      WHERE enumtypid = (
        SELECT oid FROM pg_type WHERE typname = 'reports_type_enum'
      )
    `);

    if (checkEnum.length === 0) {
      // If enum doesn't exist or has no values, create it with all values
      await queryRunner.query(`
        CREATE TYPE "public"."reports_type_enum" AS ENUM (
          'MONTHLY_SCORECARD',
          'LOT',
          'EXECUTIVE_QUALITY_SUMMARY',
          'LOT_INSPECTION_REPORT',
          'MEASUREMENT_COMPLIANCE_SHEET',
          'PACKAGING_READINESS_REPORT',
          'SUPPLIER_PERFORMANCE_SNAPSHOT',
          'CAPA_REPORT',
          'INLINE_QC_CHECKPOINTS',
          'DPP_SUMMARY'
        );
      `);
    } else {
      // Add missing values to existing enum
      // Note: ALTER TYPE ... ADD VALUE cannot be executed inside a transaction block
      // So we need to handle this differently
      await queryRunner.query(`
        -- Add INLINE_QC_CHECKPOINTS if it doesn't exist
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'INLINE_QC_CHECKPOINTS'
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
          ) THEN
            ALTER TYPE "public"."reports_type_enum" ADD VALUE 'INLINE_QC_CHECKPOINTS';
          END IF;
        END$$;
      `);

      await queryRunner.query(`
        -- Add DPP_SUMMARY if it doesn't exist
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_enum
            WHERE enumlabel = 'DPP_SUMMARY'
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
          ) THEN
            ALTER TYPE "public"."reports_type_enum" ADD VALUE 'DPP_SUMMARY';
          END IF;
        END$$;
      `);
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Note: PostgreSQL doesn't support removing values from enums
    // We would need to:
    // 1. Create a new enum without the values
    // 2. Update all columns using the old enum to use the new one
    // 3. Drop the old enum
    // 4. Rename the new enum to the old name
    // This is complex and risky, so we'll leave the down migration empty
    console.log('Warning: Cannot remove enum values in PostgreSQL. Manual intervention required if rollback is needed.');
  }
}