import { MigrationInterface, QueryRunner } from "typeorm";

export class UpdateReportsTable1758852000000 implements MigrationInterface {
  name = "UpdateReportsTable1758852000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add new columns to reports table
    await queryRunner.query(`
      ALTER TABLE reports
      ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES users(id) ON DELETE SET NULL,
      ADD COLUMN IF NOT EXISTS language text DEFAULT 'EN',
      ADD COLUMN IF NOT EXISTS file_name text,
      ADD COLUMN IF NOT EXISTS file_path text,
      ADD COLUMN IF NOT EXISTS file_url text,
      ADD COLUMN IF NOT EXISTS file_size integer,
      ADD COLUMN IF NOT EXISTS parameters jsonb DEFAULT '{}',
      ADD COLUMN IF NOT EXISTS metadata jsonb,
      ADD COLUMN IF NOT EXISTS generated_at timestamptz,
      ADD COLUMN IF NOT EXISTS expires_at timestamptz,
      ADD COLUMN IF NOT EXISTS error_message text,
      ADD COLUMN IF NOT EXISTS generation_time_ms integer;
    `);

    // Update existing reports to have file names
    await queryRunner.query(`
      UPDATE reports
      SET file_name = CONCAT(type, '_', id, '.pdf')
      WHERE file_name IS NULL;
    `);

    // Add indexes
    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);
      CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX IF EXISTS idx_reports_status`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_reports_user_id`);

    await queryRunner.query(`
      ALTER TABLE reports
      DROP COLUMN IF EXISTS generation_time_ms,
      DROP COLUMN IF EXISTS error_message,
      DROP COLUMN IF EXISTS expires_at,
      DROP COLUMN IF EXISTS generated_at,
      DROP COLUMN IF EXISTS metadata,
      DROP COLUMN IF EXISTS parameters,
      DROP COLUMN IF EXISTS file_size,
      DROP COLUMN IF EXISTS file_url,
      DROP COLUMN IF EXISTS file_path,
      DROP COLUMN IF EXISTS file_name,
      DROP COLUMN IF EXISTS language,
      DROP COLUMN IF EXISTS user_id;
    `);
  }
}