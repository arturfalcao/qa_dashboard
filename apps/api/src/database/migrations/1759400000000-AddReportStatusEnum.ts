import { MigrationInterface, QueryRunner } from "typeorm";

export class AddReportStatusEnum1759400000000 implements MigrationInterface {
  name = "AddReportStatusEnum1759400000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // First, check if the enum exists and what values it has
    const checkEnum = await queryRunner.query(`
      SELECT enumlabel
      FROM pg_enum
      WHERE enumtypid = (
        SELECT oid FROM pg_type WHERE typname = 'reports_status_enum'
      )
    `);

    if (checkEnum.length === 0) {
      // If enum doesn't exist or has no values, create it with all values
      await queryRunner.query(`
        CREATE TYPE "public"."reports_status_enum" AS ENUM (
          'PENDING',
          'READY',
          'FAILED',
          'GENERATING',
          'COMPLETED',
          'EXPIRED'
        );
      `);
    } else {
      // Add missing values to existing enum
      // Check which values need to be added
      const existingValues = checkEnum.map((row: any) => row.enumlabel);
      const requiredValues = ['PENDING', 'READY', 'FAILED', 'GENERATING', 'COMPLETED', 'EXPIRED'];

      for (const value of requiredValues) {
        if (!existingValues.includes(value)) {
          await queryRunner.query(`
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = '${value}'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
              ) THEN
                ALTER TYPE "public"."reports_status_enum" ADD VALUE '${value}';
              END IF;
            END$$;
          `);
        }
      }
    }

    // Also ensure the report language enum exists
    const checkLangEnum = await queryRunner.query(`
      SELECT enumlabel
      FROM pg_enum
      WHERE enumtypid = (
        SELECT oid FROM pg_type WHERE typname = 'reports_language_enum'
      )
    `);

    if (checkLangEnum.length === 0) {
      await queryRunner.query(`
        CREATE TYPE "public"."reports_language_enum" AS ENUM (
          'PT',
          'EN',
          'ES',
          'FR',
          'IT',
          'DE'
        );
      `);
    }
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Note: PostgreSQL doesn't support removing values from enums easily
    // We would need to:
    // 1. Create a new enum without the values
    // 2. Update all columns using the old enum to use the new one
    // 3. Drop the old enum
    // 4. Rename the new enum to the old name
    // This is complex and risky, so we'll leave the down migration empty
    console.log('Warning: Cannot remove enum values in PostgreSQL. Manual intervention required if rollback is needed.');
  }
}