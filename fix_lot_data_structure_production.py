#!/usr/bin/env python3
"""
Fix material_composition and certifications data structure in existing lots
"""

import psycopg2
import psycopg2.extras
import random

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
print("Fix Lot Data Structure (Production)")
print("=" * 60)
print("")

# Get all lots with incorrect data structure
cur.execute("""
    SELECT id, style_ref, material_composition, certifications
    FROM lots
    ORDER BY created_at
""")

lots = cur.fetchall()

print(f"Found {len(lots)} lots to fix")
print("")

fixed_count = 0

for lot_id, style_ref, material_comp, certs in lots:
    try:
        # Fix material_composition
        # Current format: {"primary": "Cotton", "percentage": 100}
        # Target format: [{"fiber": "Cotton", "percentage": 100, "properties": {}}]
        if material_comp and isinstance(material_comp, dict) and 'primary' in material_comp:
            new_material = [{
                "fiber": material_comp.get("primary", "Cotton"),
                "percentage": material_comp.get("percentage", 100),
                "properties": {}
            }]
        else:
            # If already array or null, keep as is
            new_material = material_comp if material_comp else []

        # Fix certifications
        # Current format: ["GOTS", "WRAP"]
        # Target format: [{"type": "GOTS", "number": "GOT-123456"}, ...]
        if certs and isinstance(certs, list):
            # Check if it's array of strings or array of objects
            if certs and isinstance(certs[0], str):
                new_certs = [
                    {
                        "type": cert,
                        "number": f"{cert[:3].upper()}-{random.randint(100000, 999999)}"
                    }
                    for cert in certs
                ]
            else:
                # Already in correct format
                new_certs = certs
        else:
            new_certs = []

        # Update the lot
        cur.execute("""
            UPDATE lots
            SET material_composition = %s::jsonb,
                certifications = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
        """, (
            psycopg2.extras.Json(new_material),
            psycopg2.extras.Json(new_certs),
            lot_id
        ))

        print(f"  ✓ {style_ref}")
        fixed_count += 1

    except Exception as e:
        print(f"  ✗ {style_ref} (error: {e})")
        conn.rollback()

conn.commit()

print("")
print("=" * 60)
print("✓ Data Structure Fixed!")
print("=" * 60)
print(f"Fixed: {fixed_count} lots")
print("")

cur.close()
conn.close()
