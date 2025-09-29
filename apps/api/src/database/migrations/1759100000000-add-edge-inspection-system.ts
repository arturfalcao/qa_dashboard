import { MigrationInterface, QueryRunner } from "typeorm";

export class AddEdgeInspectionSystem1759100000000 implements MigrationInterface {
  name = "AddEdgeInspectionSystem1759100000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // 1. Create edge_devices table
    await queryRunner.query(`
      CREATE TABLE edge_devices (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        name varchar(255) NOT NULL,
        secret_key varchar(255) UNIQUE NOT NULL,
        workbench_number int NOT NULL,
        status varchar(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance')),
        last_seen_at timestamptz,
        assigned_operator_id uuid REFERENCES users(id) ON DELETE SET NULL,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_edge_devices_tenant_id ON edge_devices(tenant_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_edge_devices_secret_key ON edge_devices(secret_key);
    `);

    // 2. Create inspection_sessions table
    await queryRunner.query(`
      CREATE TABLE inspection_sessions (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        lot_id uuid NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
        device_id uuid NOT NULL REFERENCES edge_devices(id) ON DELETE CASCADE,
        operator_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        started_at timestamptz NOT NULL,
        ended_at timestamptz,
        paused_at timestamptz,
        pieces_inspected int DEFAULT 0,
        pieces_ok int DEFAULT 0,
        pieces_defect int DEFAULT 0,
        pieces_potential_defect int DEFAULT 0,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_inspection_sessions_lot_id ON inspection_sessions(lot_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_inspection_sessions_device_id ON inspection_sessions(device_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_inspection_sessions_operator_id ON inspection_sessions(operator_id);
    `);

    // 3. Create apparel_pieces table
    await queryRunner.query(`
      CREATE TABLE apparel_pieces (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        inspection_session_id uuid NOT NULL REFERENCES inspection_sessions(id) ON DELETE CASCADE,
        piece_number int NOT NULL,
        status varchar(20) DEFAULT 'pending_review' CHECK (status IN ('ok', 'defect', 'potential_defect', 'pending_review')),
        inspection_started_at timestamptz NOT NULL,
        inspection_completed_at timestamptz,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_apparel_pieces_session_id ON apparel_pieces(inspection_session_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_apparel_pieces_status ON apparel_pieces(status);
    `);

    // 4. Create piece_photos table
    await queryRunner.query(`
      CREATE TABLE piece_photos (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        piece_id uuid NOT NULL REFERENCES apparel_pieces(id) ON DELETE CASCADE,
        file_path text NOT NULL,
        s3_url text,
        captured_at timestamptz NOT NULL,
        created_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_piece_photos_piece_id ON piece_photos(piece_id);
    `);

    // 5. Create piece_defects table
    await queryRunner.query(`
      CREATE TABLE piece_defects (
        id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        piece_id uuid NOT NULL REFERENCES apparel_pieces(id) ON DELETE CASCADE,
        status varchar(20) DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'confirmed', 'rejected')),
        audio_transcript text,
        flagged_at timestamptz NOT NULL,
        reviewed_by uuid REFERENCES users(id) ON DELETE SET NULL,
        reviewed_at timestamptz,
        notes text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );
    `);

    await queryRunner.query(`
      CREATE INDEX idx_piece_defects_piece_id ON piece_defects(piece_id);
    `);

    await queryRunner.query(`
      CREATE INDEX idx_piece_defects_status ON piece_defects(status);
    `);

    // 6. Add OPERATOR role if it doesn't exist
    await queryRunner.query(`
      INSERT INTO roles (id, name, description, created_at, updated_at)
      VALUES (
        uuid_generate_v4(),
        'OPERATOR',
        'Edge inspection operator role',
        now(),
        now()
      )
      ON CONFLICT (name) DO NOTHING;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE IF EXISTS piece_defects CASCADE;`);
    await queryRunner.query(`DROP TABLE IF EXISTS piece_photos CASCADE;`);
    await queryRunner.query(`DROP TABLE IF EXISTS apparel_pieces CASCADE;`);
    await queryRunner.query(`DROP TABLE IF EXISTS inspection_sessions CASCADE;`);
    await queryRunner.query(`DROP TABLE IF EXISTS edge_devices CASCADE;`);
    await queryRunner.query(`DELETE FROM roles WHERE name = 'OPERATOR';`);
  }
}