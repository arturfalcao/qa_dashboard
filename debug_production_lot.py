#!/usr/bin/env python3
"""
Debug production lot data structure
"""

import psycopg2
import psycopg2.extras
import json

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

print("=" * 60)
print("Production Lot Debug")
print("=" * 60)
print("")

lot_id = "7d66a392-9093-442f-9d33-b5411172c996"

# Get lot basic info
print("1. Lot Basic Info:")
print("-" * 60)
cur.execute("""
    SELECT
        l.id, l.style_ref, l.garment_type, l.status,
        l.quantity_total, l.material_composition, l.certifications,
        l.client_id, l.factory_id, l.tenant_id,
        c.name as client_name,
        f.name as factory_name
    FROM lots l
    LEFT JOIN clients c ON l.client_id = c.id
    LEFT JOIN factories f ON l.factory_id = f.id
    WHERE l.id = %s
""", (lot_id,))

lot = cur.fetchone()
if lot:
    print(f"ID: {lot['id']}")
    print(f"Style Ref: {lot['style_ref']}")
    print(f"Garment Type: {lot['garment_type']}")
    print(f"Status: {lot['status']}")
    print(f"Quantity: {lot['quantity_total']}")
    print(f"Client: {lot['client_name']} (ID: {lot['client_id']})")
    print(f"Factory: {lot['factory_name']} (ID: {lot['factory_id']})")
    print(f"Tenant ID: {lot['tenant_id']}")
    print(f"Material Composition: {lot['material_composition']}")
    print(f"Certifications: {lot['certifications']}")
else:
    print("✗ Lot not found!")
    exit(1)

print("")

# Check lot_factories table
print("2. Lot Factories (lot_factories table):")
print("-" * 60)
cur.execute("""
    SELECT
        lf.id, lf.lot_id, lf.factory_id, lf.sequence, lf.is_primary,
        f.name as factory_name, f.city, f.country
    FROM lot_factories lf
    LEFT JOIN factories f ON lf.factory_id = f.id
    WHERE lf.lot_id = %s
    ORDER BY lf.sequence
""", (lot_id,))

lot_factories = cur.fetchall()
if lot_factories:
    for lf in lot_factories:
        print(f"  Sequence {lf['sequence']}: {lf['factory_name']} (Primary: {lf['is_primary']})")
        print(f"    Location: {lf['city']}, {lf['country']}")
        print(f"    Factory ID: {lf['factory_id']}")
else:
    print("  (No factories assigned in lot_factories table)")

print("")

# Check lot_factory_roles table
print("3. Lot Factory Roles (lot_factory_roles table):")
print("-" * 60)
cur.execute("""
    SELECT
        lfr.id, lfr.lot_factory_id, lfr.role_id, lfr.sequence, lfr.status,
        r.name as role_name,
        lf.factory_id
    FROM lot_factory_roles lfr
    LEFT JOIN lot_factories lf ON lfr.lot_factory_id = lf.id
    LEFT JOIN roles r ON lfr.role_id = r.id
    WHERE lf.lot_id = %s
    ORDER BY lf.sequence, lfr.sequence
""", (lot_id,))

lot_factory_roles = cur.fetchall()
if lot_factory_roles:
    for lfr in lot_factory_roles:
        print(f"  Role: {lfr['role_name']}")
        print(f"    Sequence: {lfr['sequence']}")
        print(f"    Status: {lfr['status']}")
        print(f"    Factory ID: {lfr['factory_id']}")
else:
    print("  (No roles assigned)")

print("")

# Check inspections
print("4. Inspections:")
print("-" * 60)
cur.execute("""
    SELECT id, inspection_date, inspector_notes, status
    FROM inspections
    WHERE lot_id = %s
    ORDER BY inspection_date DESC
""", (lot_id,))

inspections = cur.fetchall()
if inspections:
    for insp in inspections:
        print(f"  Date: {insp['inspection_date']}, Status: {insp['status']}")
else:
    print("  (No inspections)")

print("")

# Check approvals
print("5. Approvals:")
print("-" * 60)
cur.execute("""
    SELECT id, created_at, is_approved, note
    FROM lot_approvals
    WHERE lot_id = %s
    ORDER BY created_at DESC
""", (lot_id,))

approvals = cur.fetchall()
if approvals:
    for appr in approvals:
        print(f"  Date: {appr['created_at']}, Approved: {appr['is_approved']}")
else:
    print("  (No approvals)")

print("")

# Check tech pack
print("6. Tech Pack:")
print("-" * 60)
cur.execute("""
    SELECT tech_pack_file_key, dpp_metadata
    FROM lots
    WHERE id = %s
""", (lot_id,))

tech_data = cur.fetchone()
if tech_data and tech_data['tech_pack_file_key']:
    print(f"  Tech Pack Key: {tech_data['tech_pack_file_key']}")
    print(f"  DPP Metadata: {tech_data['dpp_metadata']}")
else:
    print("  (No tech pack)")

print("")
print("=" * 60)
print("Debug Complete")
print("=" * 60)

cur.close()
conn.close()
