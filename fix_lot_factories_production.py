#!/usr/bin/env python3
"""
Fix lot-factory relationships in production
Populates lot_factories table from lots.factory_id
"""

import psycopg2
import psycopg2.extras
import uuid

# Register UUID adapter
psycopg2.extras.register_uuid()

# Production Database connection
conn = psycopg2.connect(
    host="db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com",
    port=25060,
    database="defaultdb",
    user="doadmin",
    password="os.environ.get("DB_PASSWORD", "")",
    sslmode="require"
)
cur = conn.cursor()

print("=" * 60)
print("Fix Lot-Factory Relationships (Production)")
print("=" * 60)
print("")

# Get all lots that have a factory_id but no entry in lot_factories
cur.execute("""
    SELECT l.id, l.factory_id, l.style_ref, f.name as factory_name
    FROM lots l
    LEFT JOIN factories f ON l.factory_id = f.id
    WHERE l.factory_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM lot_factories lf
          WHERE lf.lot_id = l.id AND lf.factory_id = l.factory_id
      )
    ORDER BY l.created_at
""")

lots_to_fix = cur.fetchall()

print(f"Found {len(lots_to_fix)} lots that need lot_factories entries")
print("")

if len(lots_to_fix) == 0:
    print("✓ All lots already have lot_factories entries!")
    cur.close()
    conn.close()
    exit(0)

created_count = 0

for lot_id, factory_id, style_ref, factory_name in lots_to_fix:
    try:
        lot_factory_id = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO lot_factories (
                id, lot_id, factory_id, sequence, is_primary, created_at, updated_at
            )
            VALUES (%s, %s, %s, 1, true, NOW(), NOW())
        """, (lot_factory_id, lot_id, factory_id))

        print(f"  ✓ {style_ref} → {factory_name}")
        created_count += 1

    except Exception as e:
        print(f"  ✗ {style_ref} (error: {e})")
        conn.rollback()

conn.commit()

print("")
print("=" * 60)
print("✓ Lot-Factory Relationships Fixed!")
print("=" * 60)
print(f"Created: {created_count} lot_factories entries")
print("")

cur.close()
conn.close()
