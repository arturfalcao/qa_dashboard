#!/usr/bin/env python3
"""
Verify the lot now has proper factory relationships
"""

import psycopg2
import psycopg2.extras

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
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

lot_id = "7d66a392-9093-442f-9d33-b5411172c996"

print("=" * 60)
print("Verify Lot Fix")
print("=" * 60)
print("")

# Check lot_factories
cur.execute("""
    SELECT
        lf.id, lf.lot_id, lf.factory_id, lf.sequence, lf.is_primary,
        f.name as factory_name, f.city, f.country,
        l.style_ref
    FROM lot_factories lf
    JOIN factories f ON lf.factory_id = f.id
    JOIN lots l ON lf.lot_id = l.id
    WHERE lf.lot_id = %s
    ORDER BY lf.sequence
""", (lot_id,))

lot_factories = cur.fetchall()

if lot_factories:
    print(f"✓ Found {len(lot_factories)} factory relationship(s):")
    print("")
    for lf in lot_factories:
        print(f"  Lot: {lf['style_ref']}")
        print(f"  Factory: {lf['factory_name']}")
        print(f"  Location: {lf['city']}, {lf['country']}")
        print(f"  Sequence: {lf['sequence']}")
        print(f"  Primary: {lf['is_primary']}")
        print(f"  Lot Factory ID: {lf['id']}")
        print("")
else:
    print("✗ No factory relationships found!")

print("=" * 60)

cur.close()
conn.close()
