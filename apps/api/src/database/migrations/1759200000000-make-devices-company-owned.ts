import { MigrationInterface, QueryRunner } from "typeorm";

export class MakeDevicesCompanyOwned1759200000000 implements MigrationInterface {
  name = "MakeDevicesCompanyOwned1759200000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Drop the foreign key constraint
    await queryRunner.query(`
      ALTER TABLE edge_devices
      DROP CONSTRAINT IF EXISTS edge_devices_tenant_id_fkey;
    `);

    // Make tenant_id nullable (devices belong to Pack & Polish, not tenants)
    await queryRunner.query(`
      ALTER TABLE edge_devices
      ALTER COLUMN tenant_id DROP NOT NULL;
    `);

    // Set all existing devices to NULL tenant_id (they belong to Pack & Polish)
    await queryRunner.query(`
      UPDATE edge_devices SET tenant_id = NULL;
    `);

    // Drop the tenant_id index since we're not querying by tenant anymore
    await queryRunner.query(`
      DROP INDEX IF EXISTS idx_edge_devices_tenant_id;
    `);

    // Add a comment to clarify the architecture
    await queryRunner.query(`
      COMMENT ON COLUMN edge_devices.tenant_id IS
      'DEPRECATED: Devices belong to Pack & Polish company, not individual tenants. Should always be NULL.';
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // This migration is not easily reversible since we're changing the data model
    // If you need to roll back, you'll need to manually reassign devices to tenants
    await queryRunner.query(`
      ALTER TABLE edge_devices
      ALTER COLUMN tenant_id SET NOT NULL;
    `);

    await queryRunner.query(`
      ALTER TABLE edge_devices
      ADD CONSTRAINT edge_devices_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    `);

    await queryRunner.query(`
      CREATE INDEX idx_edge_devices_tenant_id ON edge_devices(tenant_id);
    `);
  }
}
