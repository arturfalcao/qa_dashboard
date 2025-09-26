import { MigrationInterface, QueryRunner } from "typeorm";

export class Foundations0011719158120000 implements MigrationInterface {
  name = "Foundations0011719158120000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS clients (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name text NOT NULL,
        slug text UNIQUE NOT NULL,
        logo_url text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS factories (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        client_id uuid REFERENCES clients(id) ON DELETE SET NULL,
        name text NOT NULL,
        city text,
        country text DEFAULT 'PT',
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS roles (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name text UNIQUE NOT NULL,
        description text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS users (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        client_id uuid REFERENCES clients(id) ON DELETE SET NULL,
        email text NOT NULL,
        password_hash text NOT NULL,
        is_active boolean DEFAULT true,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now(),
        CONSTRAINT uq_users_email UNIQUE (email)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS user_roles (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        is_primary boolean DEFAULT false,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now(),
        CONSTRAINT uq_user_role UNIQUE (user_id, role_id)
      );
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS defect_types (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name text UNIQUE NOT NULL,
        category text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS lots (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        factory_id uuid NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
        style_ref text NOT NULL,
        quantity_total integer NOT NULL,
        status text NOT NULL,
        defect_rate numeric(5,2) DEFAULT 0,
        inspected_progress numeric(5,2) DEFAULT 0,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_lots_client_status ON lots(client_id, status);
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_lots_factory ON lots(factory_id);
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS inspections (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        lot_id uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        inspector_id uuid REFERENCES users(id) ON DELETE SET NULL,
        started_at timestamptz,
        finished_at timestamptz,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS defects (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        inspection_id uuid NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
        piece_code text,
        defect_type_id uuid REFERENCES defect_types(id) ON DELETE SET NULL,
        note text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_defects_type ON defects(defect_type_id);
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS photos (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        defect_id uuid NOT NULL REFERENCES defects(id) ON DELETE CASCADE,
        url text NOT NULL,
        annotation jsonb,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS approvals (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        lot_id uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        approved_by uuid REFERENCES users(id) ON DELETE SET NULL,
        decision text NOT NULL,
        note text,
        decided_at timestamptz DEFAULT now(),
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now(),
        CONSTRAINT uq_approvals_lot UNIQUE (lot_id)
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS reports (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        type text NOT NULL,
        client_id uuid REFERENCES clients(id) ON DELETE SET NULL,
        lot_id uuid REFERENCES lots(id) ON DELETE SET NULL,
        month date,
        url text,
        status text DEFAULT 'PENDING',
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_reports_client_month ON reports(client_id, month);
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS activities (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        lot_id uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        kind text NOT NULL,
        payload jsonb,
        ts timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX IF NOT EXISTS idx_activities_lot_ts ON activities(lot_id, ts DESC);
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS events (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        lot_id uuid REFERENCES lots(id) ON DELETE SET NULL,
        type text NOT NULL,
        payload jsonb,
        created_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS notifications (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        client_id uuid REFERENCES clients(id) ON DELETE SET NULL,
        user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        channel text NOT NULL,
        template text NOT NULL,
        payload jsonb,
        status text DEFAULT 'pending',
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE TABLE IF NOT EXISTS audit_log (
        id bigserial PRIMARY KEY,
        user_id uuid,
        entity text NOT NULL,
        entity_id text NOT NULL,
        action text NOT NULL,
        before jsonb,
        after jsonb,
        ts timestamptz DEFAULT now()
      );
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE IF EXISTS audit_log`);
    await queryRunner.query(`DROP TABLE IF EXISTS notifications`);
    await queryRunner.query(`DROP TABLE IF EXISTS events`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_activities_lot_ts`);
    await queryRunner.query(`DROP TABLE IF EXISTS activities`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_reports_client_month`);
    await queryRunner.query(`DROP TABLE IF EXISTS reports`);
    await queryRunner.query(`DROP TABLE IF EXISTS approvals`);
    await queryRunner.query(`DROP TABLE IF EXISTS photos`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_defects_type`);
    await queryRunner.query(`DROP TABLE IF EXISTS defects`);
    await queryRunner.query(`DROP TABLE IF EXISTS inspections`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_lots_factory`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_lots_client_status`);
    await queryRunner.query(`DROP TABLE IF EXISTS lots`);
    await queryRunner.query(`DROP TABLE IF EXISTS defect_types`);
    await queryRunner.query(`DROP INDEX IF EXISTS idx_user_roles_user`);
    await queryRunner.query(`DROP TABLE IF EXISTS user_roles`);
    await queryRunner.query(`DROP TABLE IF EXISTS users`);
    await queryRunner.query(`DROP TABLE IF EXISTS roles`);
    await queryRunner.query(`DROP TABLE IF EXISTS factories`);
    await queryRunner.query(`DROP TABLE IF EXISTS clients`);
  }
}
