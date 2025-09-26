const { Client } = require('pg');

async function updateReportsTable() {
  const client = new Client({
    host: 'localhost',
    port: 5432,
    database: 'qa_dashboard',
    user: 'qa_user',
    password: 'dev_password'
  });

  try {
    await client.connect();
    console.log('Connected to database');

    // Add missing columns to reports table
    const sql = `
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
    `;

    await client.query(sql);
    console.log('Successfully added missing columns to reports table');

    // Update existing reports to have file names
    await client.query(`
      UPDATE reports
      SET file_name = CONCAT(type, '_', id, '.pdf')
      WHERE file_name IS NULL;
    `);

    // Make file_name NOT NULL
    await client.query(`
      ALTER TABLE reports ALTER COLUMN file_name SET NOT NULL;
    `);

    console.log('Updated existing reports and made file_name NOT NULL');

    // Add indexes
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);
      CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
    `);

    console.log('Added indexes for user_id and status');

  } catch (error) {
    console.error('Error updating reports table:', error);
    process.exit(1);
  } finally {
    await client.end();
    console.log('Database connection closed');
  }
}

updateReportsTable();