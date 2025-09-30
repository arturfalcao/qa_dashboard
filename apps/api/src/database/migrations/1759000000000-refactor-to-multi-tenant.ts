import { MigrationInterface, QueryRunner } from "typeorm";

export class RefactorToMultiTenant1759000000000 implements MigrationInterface {
  name = "RefactorToMultiTenant1759000000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Step 1: Create tenants table (this will replace the current clients table concept)
    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS tenants (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name text NOT NULL,
        slug text UNIQUE NOT NULL,
        logo_url text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    // Step 2: Migrate existing clients data to tenants table
    await queryRunner.query(`
      INSERT INTO tenants (id, name, slug, logo_url, created_at, updated_at)
      SELECT id, name, slug, logo_url, created_at, updated_at
      FROM clients;
    `);

    // Step 3: Recreate clients table for actual tenant customers
    // First, drop foreign key constraints that reference clients
    await queryRunner.query(`
      ALTER TABLE users DROP CONSTRAINT IF EXISTS users_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE factories DROP CONSTRAINT IF EXISTS factories_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE lots DROP CONSTRAINT IF EXISTS lots_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE events DROP CONSTRAINT IF EXISTS events_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_client_id_fkey;
    `);
    await queryRunner.query(`
      ALTER TABLE dpps DROP CONSTRAINT IF EXISTS fk_dpps_client;
    `);

    // Rename the old clients table to old_clients temporarily
    await queryRunner.query(`
      ALTER TABLE clients RENAME TO old_clients;
    `);

    // Create new clients table (for tenant's actual customers)
    await queryRunner.query(`
      CREATE TABLE clients (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name text NOT NULL,
        contact_email text,
        contact_phone text,
        address text,
        country text,
        notes text,
        is_active boolean DEFAULT true,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_clients_tenant_id ON clients(tenant_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_clients_tenant_name ON clients(tenant_id, name);
    `);

    // Step 4: Add tenant_id columns to tables that currently reference clients
    // Users: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE users RENAME COLUMN client_id TO tenant_id;
    `);
    await queryRunner.query(`
      ALTER TABLE users ADD CONSTRAINT users_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_client_email;
    `);
    await queryRunner.query(`
      ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email);
    `);

    // Factories: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE factories RENAME COLUMN client_id TO tenant_id;
    `);
    await queryRunner.query(`
      ALTER TABLE factories ADD CONSTRAINT factories_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
    `);

    // Lots: rename client_id to tenant_id AND add client_id for actual clients
    await queryRunner.query(`
      ALTER TABLE lots RENAME COLUMN client_id TO tenant_id;
    `);
    await queryRunner.query(`
      ALTER TABLE lots ADD COLUMN client_id uuid REFERENCES clients(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE lots ADD CONSTRAINT lots_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    `);
    await queryRunner.query(`
      DROP INDEX IF EXISTS idx_lots_client_status;
    `);
    await queryRunner.query(`
      CREATE INDEX idx_lots_tenant_status ON lots(tenant_id, status);
    `);
    await queryRunner.query(`
      CREATE INDEX idx_lots_client_id ON lots(client_id);
    `);

    // Events: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE events RENAME COLUMN client_id TO tenant_id;
    `);
    // Convert tenant_id to UUID type if it's not already
    await queryRunner.query(`
      ALTER TABLE events
      ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid;
    `);
    await queryRunner.query(`
      ALTER TABLE events ADD CONSTRAINT events_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    `);

    // Notifications: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE notifications RENAME COLUMN client_id TO tenant_id;
    `);
    // Convert tenant_id to UUID type if it's not already
    await queryRunner.query(`
      ALTER TABLE notifications
      ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid;
    `);
    await queryRunner.query(`
      ALTER TABLE notifications ADD CONSTRAINT notifications_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
    `);

    // Reports: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE reports RENAME COLUMN client_id TO tenant_id;
    `);
    // Convert tenant_id to UUID type if it's not already
    await queryRunner.query(`
      ALTER TABLE reports
      ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid;
    `);
    await queryRunner.query(`
      ALTER TABLE reports ADD CONSTRAINT reports_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL;
    `);

    // DPPs: rename client_id to tenant_id
    await queryRunner.query(`
      ALTER TABLE dpps RENAME COLUMN client_id TO tenant_id;
    `);
    // Convert tenant_id to UUID type if it's not already
    await queryRunner.query(`
      ALTER TABLE dpps
      ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid;
    `);
    await queryRunner.query(`
      ALTER TABLE dpps ADD CONSTRAINT dpps_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenants(id);
    `);

    // Drop the old_clients table
    // First drop any remaining foreign key constraints that might reference it
    await queryRunner.query(`
      ALTER TABLE factories DROP CONSTRAINT IF EXISTS FK_39fa445253769a08081a8b9485c;
    `);
    await queryRunner.query(`
      ALTER TABLE lots DROP CONSTRAINT IF EXISTS FK_52222ad1e6660451b31ea7e5780;
    `);
    await queryRunner.query(`
      ALTER TABLE users DROP CONSTRAINT IF EXISTS FK_0d1e90d75674c54f8660c4ed446;
    `);
    await queryRunner.query(`
      ALTER TABLE events DROP CONSTRAINT IF EXISTS FK_b4ea5a78d656e3c29835bf644e6;
    `);
    await queryRunner.query(`
      ALTER TABLE reports DROP CONSTRAINT IF EXISTS FK_bda44e16992191ff11ad8da01e2;
    `);
    await queryRunner.query(`
      ALTER TABLE dpps DROP CONSTRAINT IF EXISTS FK_8b619ab36496e04c1d67bfbc643;
    `);
    await queryRunner.query(`
      DROP TABLE old_clients;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Rollback: This is complex, so we'll recreate the original structure

    // Recreate old clients table structure
    await queryRunner.query(`
      CREATE TABLE old_clients AS SELECT * FROM tenants;
    `);

    // Drop new clients table
    await queryRunner.query(`
      DROP TABLE IF EXISTS clients CASCADE;
    `);

    // Rename tenants back to clients
    await queryRunner.query(`
      DROP TABLE IF EXISTS tenants CASCADE;
    `);

    await queryRunner.query(`
      ALTER TABLE old_clients RENAME TO clients;
    `);

    // Revert column renames
    await queryRunner.query(`
      ALTER TABLE users RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE factories RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE lots DROP COLUMN IF EXISTS client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE lots RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE events RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE notifications RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE reports RENAME COLUMN tenant_id TO client_id;
    `);
    await queryRunner.query(`
      ALTER TABLE dpps RENAME COLUMN tenant_id TO client_id;
    `);

    // Recreate original foreign keys
    await queryRunner.query(`
      ALTER TABLE users ADD CONSTRAINT users_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE factories ADD CONSTRAINT factories_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE lots ADD CONSTRAINT lots_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;
    `);
    await queryRunner.query(`
      ALTER TABLE events ADD CONSTRAINT events_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;
    `);
    await queryRunner.query(`
      ALTER TABLE notifications ADD CONSTRAINT notifications_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE reports ADD CONSTRAINT reports_client_id_fkey
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL;
    `);
    await queryRunner.query(`
      ALTER TABLE dpps ADD CONSTRAINT fk_dpps_client
        FOREIGN KEY (client_id) REFERENCES clients(id);
    `);

    // Recreate original indexes
    await queryRunner.query(`
      DROP INDEX IF EXISTS idx_lots_tenant_status;
    `);
    await queryRunner.query(`
      CREATE INDEX idx_lots_client_status ON lots(client_id, status);
    `);
    await queryRunner.query(`
      DROP INDEX IF EXISTS uq_users_tenant_email;
    `);
    await queryRunner.query(`
      ALTER TABLE users ADD CONSTRAINT uq_users_client_email UNIQUE (client_id, email);
    `);
  }
}