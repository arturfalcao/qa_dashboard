#!/usr/bin/env python3
"""
Enrich demo data with tech packs, inspections, and supply chain stages
"""

import psycopg2
import psycopg2.extras
import uuid
import random
from datetime import datetime, timedelta

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
print("Enrich Demo Data (Production)")
print("=" * 60)
print("")

# ============================================================================
# STEP 1: Add more factories
# ============================================================================
print("Step 1: Adding More Factories...")
print("-" * 60)

NEW_FACTORIES = [
    {"name": "Barcelona Premium Knits", "city": "Barcelona", "country": "ES"},
    {"name": "Lyon Fine Textiles", "city": "Lyon", "country": "FR"},
    {"name": "Prague Fashion House", "city": "Prague", "country": "CZ"},
    {"name": "Krakow Garment Works", "city": "Krakow", "country": "PL"},
    {"name": "Athens Mediterranean Textiles", "city": "Athens", "country": "GR"},
    {"name": "Bucharest Fashion Factory", "city": "Bucharest", "country": "RO"},
    {"name": "Sofia Textile Manufacturing", "city": "Sofia", "country": "BG"},
    {"name": "Tunis Garment Export", "city": "Tunis", "country": "TN"},
    {"name": "Jakarta Fashion Industries", "city": "Jakarta", "country": "ID"},
    {"name": "Manila Apparel Complex", "city": "Manila", "country": "PH"},
]

cur.execute("SELECT id FROM tenants")
tenant_ids = [row['id'] for row in cur.fetchall()]

factory_count = 0
for factory in NEW_FACTORIES:
    tenant_id = random.choice(tenant_ids)
    factory_id = str(uuid.uuid4())

    try:
        cur.execute("""
            INSERT INTO factories (id, tenant_id, name, city, country, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (factory_id, tenant_id, factory["name"], factory["city"], factory["country"]))

        if cur.fetchone():
            print(f"  ✓ {factory['name']} ({factory['city']}, {factory['country']})")
            factory_count += 1
    except Exception as e:
        print(f"  ✗ {factory['name']} (error: {e})")
        conn.rollback()

conn.commit()
print(f"Added {factory_count} new factories\n")

# ============================================================================
# STEP 2: Add supply chain roles to lots
# ============================================================================
print("Step 2: Adding Supply Chain Stages...")
print("-" * 60)

# Get all supply chain roles
cur.execute("SELECT id, name FROM supply_chain_roles WHERE name NOT LIKE 'Unknown%'")
roles = {row['name']: row['id'] for row in cur.fetchall()}
print(f"Found {len(roles)} supply chain roles in system")

# Common supply chain stages (using actual role names from the database)
SUPPLY_CHAIN_STAGES = [
    {"role": "Fabric Dye & Finish", "sequence": 1},
    {"role": "Fabric Inspection & Relax", "sequence": 2},
    {"role": "Marker Cutting", "sequence": 3},
    {"role": "Bundling & Sewing", "sequence": 4},
    {"role": "Inline QC", "sequence": 5},
    {"role": "Iron, Press & Dethread", "sequence": 6},
    {"role": "Final QA", "sequence": 7},
    {"role": "Pack, Tag & Bag", "sequence": 8},
    {"role": "Warehouse & Logistics", "sequence": 9},
]

# Get lots with factories
cur.execute("""
    SELECT l.id as lot_id, lf.id as lot_factory_id, lf.factory_id
    FROM lots l
    JOIN lot_factories lf ON lf.lot_id = l.id
    WHERE lf.is_primary = true
    ORDER BY l.created_at DESC
    LIMIT 30
""")
lots_with_factories = cur.fetchall()

stages_added = 0
for lot_data in lots_with_factories:
    lot_id = lot_data['lot_id']
    lot_factory_id = lot_data['lot_factory_id']

    # Add 3-6 supply chain stages
    num_stages = random.randint(3, 6)
    for i in range(num_stages):
        stage = SUPPLY_CHAIN_STAGES[i % len(SUPPLY_CHAIN_STAGES)]
        role_name = stage['role']

        # Skip if role doesn't exist
        if role_name not in roles:
            continue

        role_id = roles[role_name]
        role_sequence = i + 1

        # Determine status based on sequence
        if i == 0:
            status = "COMPLETED"
            started_at = datetime.now() - timedelta(days=random.randint(15, 30))
            completed_at = started_at + timedelta(days=random.randint(1, 3))
        elif i == 1:
            status = "IN_PROGRESS"
            started_at = datetime.now() - timedelta(days=random.randint(1, 5))
            completed_at = None
        else:
            status = "NOT_STARTED"
            started_at = None
            completed_at = None

        try:
            role_entry_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO lot_factory_roles (
                    id, lot_factory_id, role_id, sequence, status,
                    started_at, completed_at, co2_kg,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                role_entry_id, lot_factory_id, role_id, role_sequence, status,
                started_at, completed_at, random.uniform(5.0, 50.0)
            ))
            stages_added += 1
        except Exception as e:
            print(f"  ✗ Error adding stage for lot {lot_id}: {e}")
            conn.rollback()

conn.commit()
print(f"Added {stages_added} supply chain stages\n")

# ============================================================================
# STEP 3: Add size specifications to lots
# ============================================================================
print("Step 3: Adding Size Specifications...")
print("-" * 60)

SIZE_SPECS = {
    "T_SHIRT": [
        {"size": "XS", "measurements": {"chest": 86, "length": 66, "shoulder": 42, "sleeve": 18}},
        {"size": "S", "measurements": {"chest": 91, "length": 69, "shoulder": 44, "sleeve": 19}},
        {"size": "M", "measurements": {"chest": 96, "length": 72, "shoulder": 46, "sleeve": 20}},
        {"size": "L", "measurements": {"chest": 101, "length": 75, "shoulder": 48, "sleeve": 21}},
        {"size": "XL", "measurements": {"chest": 106, "length": 78, "shoulder": 50, "sleeve": 22}},
    ],
    "POLO_SHIRT": [
        {"size": "S", "measurements": {"chest": 92, "length": 70, "shoulder": 44, "sleeve": 20}},
        {"size": "M", "measurements": {"chest": 97, "length": 73, "shoulder": 46, "sleeve": 21}},
        {"size": "L", "measurements": {"chest": 102, "length": 76, "shoulder": 48, "sleeve": 22}},
        {"size": "XL", "measurements": {"chest": 107, "length": 79, "shoulder": 50, "sleeve": 23}},
    ],
    "DRESS_SHIRT": [
        {"size": "38", "measurements": {"chest": 96, "length": 76, "shoulder": 44, "sleeve": 62}},
        {"size": "39", "measurements": {"chest": 99, "length": 77, "shoulder": 45, "sleeve": 63}},
        {"size": "40", "measurements": {"chest": 102, "length": 78, "shoulder": 46, "sleeve": 64}},
        {"size": "41", "measurements": {"chest": 105, "length": 79, "shoulder": 47, "sleeve": 65}},
        {"size": "42", "measurements": {"chest": 108, "length": 80, "shoulder": 48, "sleeve": 66}},
    ],
    "PANTS": [
        {"size": "30", "measurements": {"waist": 76, "length": 104, "inseam": 81, "rise": 28}},
        {"size": "32", "measurements": {"waist": 81, "length": 106, "inseam": 81, "rise": 28}},
        {"size": "34", "measurements": {"waist": 86, "length": 108, "inseam": 81, "rise": 29}},
        {"size": "36", "measurements": {"waist": 91, "length": 110, "inseam": 81, "rise": 29}},
    ],
}

cur.execute("""
    SELECT id, garment_type
    FROM lots
    WHERE size_specifications IS NULL
    ORDER BY created_at DESC
    LIMIT 40
""")
lots_without_specs = cur.fetchall()

specs_added = 0
for lot in lots_without_specs:
    garment_type = lot['garment_type']

    # Get appropriate size specs
    specs = SIZE_SPECS.get(garment_type, SIZE_SPECS.get("T_SHIRT"))

    try:
        cur.execute("""
            UPDATE lots
            SET size_specifications = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
        """, (psycopg2.extras.Json(specs), lot['id']))
        specs_added += 1
    except Exception as e:
        print(f"  ✗ Error adding specs for lot {lot['id']}: {e}")
        conn.rollback()

conn.commit()
print(f"Added size specifications to {specs_added} lots\n")

# ============================================================================
# STEP 4: Add tech pack data
# ============================================================================
print("Step 4: Adding Tech Pack Data...")
print("-" * 60)

COLORS = [
    {"name": "Navy Blue", "pantone": "19-4028 TCX"},
    {"name": "Classic White", "pantone": "11-0601 TCX"},
    {"name": "Charcoal Gray", "pantone": "19-0000 TCX"},
    {"name": "Forest Green", "pantone": "19-0414 TCX"},
    {"name": "Burgundy", "pantone": "19-1525 TCX"},
]

WASH_CARE = [
    "Machine wash cold with like colors",
    "Use only non-chlorine bleach when needed",
    "Tumble dry low",
    "Cool iron if needed",
    "Do not dry clean",
]

cur.execute("""
    SELECT id, style_ref, garment_type
    FROM lots
    WHERE tech_pack_data IS NULL
    ORDER BY created_at DESC
    LIMIT 35
""")
lots_without_techpack = cur.fetchall()

techpack_added = 0
for lot in lots_without_techpack:
    # Skip if garment_type is None
    garment_name = lot['garment_type'].replace('_', ' ').title() if lot['garment_type'] else "Garment"

    tech_pack_data = {
        "styleReference": lot['style_ref'],
        "productName": f"{garment_name} - {lot['style_ref']}",
        "season": random.choice(["SS25", "FW24", "AW24", "SS24"]),
        "colors": random.sample(COLORS, k=random.randint(1, 3)),
        "washCareInstructions": WASH_CARE,
        "fabricWeight": f"{random.randint(150, 300)}gsm",
        "additionalNotes": "Premium quality construction with reinforced stress points. Follow care instructions carefully to maintain garment longevity.",
    }

    try:
        cur.execute("""
            UPDATE lots
            SET tech_pack_data = %s::jsonb,
                tech_pack_status = 'completed',
                updated_at = NOW()
            WHERE id = %s
        """, (psycopg2.extras.Json(tech_pack_data), lot['id']))
        techpack_added += 1
    except Exception as e:
        print(f"  ✗ Error adding tech pack for lot {lot['id']}: {e}")
        conn.rollback()

conn.commit()
print(f"Added tech pack data to {techpack_added} lots\n")

# ============================================================================
# STEP 5: Update lot statuses to be more realistic
# ============================================================================
print("Step 5: Updating Lot Statuses...")
print("-" * 60)

# Set some lots to INSPECTION status
cur.execute("""
    UPDATE lots
    SET status = 'INSPECTION',
        updated_at = NOW()
    WHERE id IN (
        SELECT id FROM lots
        WHERE status = 'IN_PRODUCTION'
        ORDER BY RANDOM()
        LIMIT 8
    )
""")
inspection_count = cur.rowcount

# Set some lots to PENDING_APPROVAL
cur.execute("""
    UPDATE lots
    SET status = 'PENDING_APPROVAL',
        updated_at = NOW()
    WHERE id IN (
        SELECT id FROM lots
        WHERE status = 'INSPECTION'
        ORDER BY RANDOM()
        LIMIT 5
    )
""")
pending_count = cur.rowcount

# Set some lots to APPROVED
cur.execute("""
    UPDATE lots
    SET status = 'APPROVED',
        updated_at = NOW()
    WHERE id IN (
        SELECT id FROM lots
        WHERE status = 'PENDING_APPROVAL'
        ORDER BY RANDOM()
        LIMIT 3
    )
""")
approved_count = cur.rowcount

conn.commit()
print(f"  ✓ Set {inspection_count} lots to INSPECTION")
print(f"  ✓ Set {pending_count} lots to PENDING_APPROVAL")
print(f"  ✓ Set {approved_count} lots to APPROVED")
print("")

# ============================================================================
# STEP 6: Add DPP metadata to approved lots
# ============================================================================
print("Step 6: Adding DPP Metadata to Approved Lots...")
print("-" * 60)

cur.execute("""
    SELECT id, style_ref
    FROM lots
    WHERE status = 'APPROVED' AND dpp_metadata IS NULL
    LIMIT 10
""")
approved_lots = cur.fetchall()

dpp_count = 0
for lot in approved_lots:
    dpp_metadata = {
        "dppId": f"DPP-{str(uuid.uuid4())[:8].upper()}",
        "version": "1.0",
        "status": "active",
        "publicUrl": f"https://dpp.packpolish.com/{lot['id']}",
        "lastAudit": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "traceabilityScore": random.randint(85, 98),
        "co2FootprintKg": round(random.uniform(15.5, 85.3), 1),
        "sustainabilityHighlights": [
            "GOTS certified organic cotton",
            "Fair Trade certified production",
            "Carbon neutral shipping",
            "Water-efficient dyeing process",
        ][:random.randint(2, 4)]
    }

    try:
        cur.execute("""
            UPDATE lots
            SET dpp_metadata = %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
        """, (psycopg2.extras.Json(dpp_metadata), lot['id']))
        print(f"  ✓ Added DPP to {lot['style_ref']}")
        dpp_count += 1
    except Exception as e:
        print(f"  ✗ Error adding DPP for {lot['style_ref']}: {e}")
        conn.rollback()

conn.commit()
print(f"Added DPP metadata to {dpp_count} lots\n")

print("=" * 60)
print("✓ Demo Data Enrichment Complete!")
print("=" * 60)
print(f"Summary:")
print(f"  - Added {factory_count} new factories")
print(f"  - Added {stages_added} supply chain stages")
print(f"  - Added size specs to {specs_added} lots")
print(f"  - Added tech pack data to {techpack_added} lots")
print(f"  - Updated statuses: {inspection_count + pending_count + approved_count} lots")
print(f"  - Added DPP metadata to {dpp_count} lots")
print("")

cur.close()
conn.close()
