#!/usr/bin/env python3
"""
Add more finished lots with complete data for metrics and reporting
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
print("Add Finished Lots with Metrics (Production)")
print("=" * 60)
print("")

# ============================================================================
# STEP 1: Get reference data
# ============================================================================
print("Step 1: Loading reference data...")
print("-" * 60)

# Get tenants
cur.execute("SELECT id, name FROM tenants")
tenants = cur.fetchall()
print(f"Found {len(tenants)} tenants")

# Get clients
cur.execute("SELECT id, tenant_id, name FROM clients")
clients = cur.fetchall()
print(f"Found {len(clients)} clients")

# Get factories with their capabilities
cur.execute("""
    SELECT f.id, f.tenant_id, f.name, f.city, f.country
    FROM factories f
    JOIN factory_roles fr ON f.id = fr.factory_id
    GROUP BY f.id, f.tenant_id, f.name, f.city, f.country
    HAVING COUNT(fr.id) >= 6
    ORDER BY f.id
    LIMIT 30
""")
factories = cur.fetchall()
print(f"Found {len(factories)} factories with good capabilities")

# Get supply chain roles
cur.execute("SELECT id, name FROM supply_chain_roles ORDER BY name")
roles = {row['name']: row['id'] for row in cur.fetchall()}
print(f"Found {len(roles)} supply chain roles")

print("")

# ============================================================================
# STEP 2: Define lot configurations
# ============================================================================
STYLE_REFS = [
    {"code": "AW25-SLM-301", "garment": "DRESS_SHIRT", "material": "Organic Cotton Poplin"},
    {"code": "SS26-TSH-401", "garment": "T_SHIRT", "material": "Bamboo Jersey"},
    {"code": "FW25-POL-501", "garment": "POLO_SHIRT", "material": "Merino Wool"},
    {"code": "AW25-SWT-601", "garment": "SWEATER", "material": "Recycled Cashmere"},
    {"code": "SS26-HEN-701", "garment": "T_SHIRT", "material": "Hemp Cotton Blend"},
    {"code": "FW25-DNM-801", "garment": "JEANS", "material": "Organic Denim"},
    {"code": "AW25-CHN-901", "garment": "PANTS", "material": "Twill Organic"},
    {"code": "SS26-DRS-111", "garment": "DRESS", "material": "Tencel"},
    {"code": "FW25-BLZ-211", "garment": "JACKET", "material": "Recycled Wool"},
    {"code": "AW25-COT-311", "garment": "COAT", "material": "Wool Cashmere"},
    {"code": "SS26-SKR-411", "garment": "SKIRT", "material": "Linen"},
    {"code": "FW25-HOD-511", "garment": "HOODIE", "material": "Organic Cotton Fleece"},
    {"code": "AW25-SHR-611", "garment": "SHORTS", "material": "Cotton Canvas"},
    {"code": "SS26-ACT-711", "garment": "ACTIVEWEAR", "material": "Recycled Polyester"},
    {"code": "FW25-SWT-811", "garment": "SWEATSHIRT", "material": "French Terry"},
]

CERTIFICATIONS = ["GOTS", "OEKO-TEX", "Fair Trade", "BSCI", "ISO 9001", "WRAP", "SA8000"]

COLORS = [
    {"name": "Navy Blue", "pantone": "19-4028 TCX"},
    {"name": "Classic White", "pantone": "11-0601 TCX"},
    {"name": "Charcoal Gray", "pantone": "19-0000 TCX"},
    {"name": "Forest Green", "pantone": "19-0414 TCX"},
    {"name": "Burgundy", "pantone": "19-1525 TCX"},
    {"name": "Black", "pantone": "19-0303 TCX"},
    {"name": "Olive", "pantone": "18-0523 TCX"},
    {"name": "Camel", "pantone": "16-1139 TCX"},
]

WASH_CARE = [
    "Machine wash cold with like colors",
    "Use only non-chlorine bleach when needed",
    "Tumble dry low",
    "Cool iron if needed",
    "Do not dry clean",
]

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
    "JEANS": [
        {"size": "30", "measurements": {"waist": 76, "length": 104, "inseam": 81, "rise": 28}},
        {"size": "32", "measurements": {"waist": 81, "length": 106, "inseam": 81, "rise": 28}},
        {"size": "34", "measurements": {"waist": 86, "length": 108, "inseam": 81, "rise": 29}},
        {"size": "36", "measurements": {"waist": 91, "length": 110, "inseam": 81, "rise": 29}},
    ],
}

# Supply chain stages in typical order
SUPPLY_CHAIN_STAGES = [
    "Fiber Preparation",
    "Fabric Dye & Finish",
    "Fabric Inspection & Relax",
    "Marker Cutting",
    "Bundling & Sewing",
    "Inline QC",
    "Iron, Press & Dethread",
    "Final QA",
    "Pack, Tag & Bag",
    "Warehouse & Logistics",
]

# ============================================================================
# STEP 3: Create finished lots
# ============================================================================
print("Step 2: Creating finished lots...")
print("-" * 60)

lots_created = 0
TARGET_FINISHED_LOTS = 30

for i in range(TARGET_FINISHED_LOTS):
    # Select random tenant
    tenant = random.choice(tenants)
    tenant_id = tenant['id']

    # Get client from same tenant
    tenant_clients = [c for c in clients if c['tenant_id'] == tenant_id]
    if not tenant_clients:
        continue
    client = random.choice(tenant_clients)

    # Get factory from same tenant
    tenant_factories = [f for f in factories if f['tenant_id'] == tenant_id]
    if not tenant_factories:
        continue
    factory = random.choice(tenant_factories)

    # Select style
    style = random.choice(STYLE_REFS)

    # Create lot
    lot_id = str(uuid.uuid4())
    quantity = random.randint(1000, 5000)

    # Create certifications
    cert_list = [
        {"type": cert, "number": f"{cert[:3].upper()}-{random.randint(100000, 999999)}"}
        for cert in random.sample(CERTIFICATIONS, k=random.randint(2, 4))
    ]

    # Create material composition
    material_json = [{"fiber": style["material"], "percentage": 100, "properties": {}}]

    # Create tech pack data
    tech_pack_data = {
        "styleReference": style["code"],
        "productName": f"{style['garment'].replace('_', ' ').title()} - {style['code']}",
        "season": random.choice(["SS26", "FW25", "AW25"]),
        "colors": random.sample(COLORS, k=random.randint(1, 3)),
        "washCareInstructions": WASH_CARE,
        "fabricWeight": f"{random.randint(150, 300)}gsm",
        "additionalNotes": "Premium quality construction. Sustainable production with full traceability.",
    }

    # Get size specifications
    specs = SIZE_SPECS.get(style["garment"], SIZE_SPECS.get("T_SHIRT"))

    # Finished lots should be APPROVED or SHIPPED
    status = random.choice(["APPROVED", "APPROVED", "APPROVED", "SHIPPED"])

    # Create DPP metadata for finished lots
    dpp_metadata = {
        "dppId": f"DPP-{str(uuid.uuid4())[:8].upper()}",
        "version": "1.0",
        "status": "active",
        "publicUrl": f"https://dpp.packpolish.com/{lot_id}",
        "lastAudit": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "traceabilityScore": random.randint(88, 99),
        "co2FootprintKg": round(random.uniform(15.5, 75.3), 1),
        "sustainabilityHighlights": [
            "GOTS certified organic materials",
            "Fair Trade certified production",
            "Carbon neutral shipping",
            "Water-efficient dyeing process",
        ][:random.randint(2, 4)]
    }

    # Calculate dates (finished lots are in the past)
    created_at = datetime.now() - timedelta(days=random.randint(60, 120))
    approved_at = created_at + timedelta(days=random.randint(30, 50))

    try:
        cur.execute("""
            INSERT INTO lots (
                id, tenant_id, client_id, factory_id, style_ref,
                garment_type, quantity_total, status,
                material_composition, certifications,
                tech_pack_data, tech_pack_status,
                size_specifications, dpp_metadata,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, 'completed', %s::jsonb, %s::jsonb, %s, NOW())
            RETURNING id
        """, (
            lot_id, tenant_id, client['id'], factory['id'], style["code"],
            style["garment"], quantity, status,
            psycopg2.extras.Json(material_json),
            psycopg2.extras.Json(cert_list),
            psycopg2.extras.Json(tech_pack_data),
            psycopg2.extras.Json(specs),
            psycopg2.extras.Json(dpp_metadata),
            created_at
        ))

        if cur.fetchone():
            lots_created += 1
            print(f"  ✓ Lot {i+1}: {style['code']} - {factory['name']} ({status})")

    except Exception as e:
        print(f"  ✗ Error creating lot {i+1}: {e}")
        conn.rollback()
        continue

conn.commit()
print(f"\nCreated {lots_created} finished lots")
print("")

# ============================================================================
# STEP 4: Add lot_factories relationships
# ============================================================================
print("Step 3: Adding factory relationships...")
print("-" * 60)

cur.execute("""
    SELECT l.id as lot_id, l.factory_id
    FROM lots l
    WHERE l.status IN ('APPROVED', 'SHIPPED')
    AND NOT EXISTS (SELECT 1 FROM lot_factories lf WHERE lf.lot_id = l.id)
    ORDER BY l.created_at DESC
    LIMIT 50
""")
lots_without_factories = cur.fetchall()

factory_rels_added = 0
for lot_data in lots_without_factories:
    lot_factory_id = str(uuid.uuid4())

    try:
        cur.execute("""
            INSERT INTO lot_factories (
                id, lot_id, factory_id, sequence, is_primary, created_at, updated_at
            )
            VALUES (%s, %s, %s, 1, true, NOW(), NOW())
        """, (lot_factory_id, lot_data['lot_id'], lot_data['factory_id']))

        factory_rels_added += 1
    except Exception as e:
        print(f"  ✗ Error adding factory relationship: {e}")
        conn.rollback()

conn.commit()
print(f"Added {factory_rels_added} factory relationships")
print("")

# ============================================================================
# STEP 5: Add completed supply chain stages
# ============================================================================
print("Step 4: Adding completed supply chain stages...")
print("-" * 60)

cur.execute("""
    SELECT lf.id as lot_factory_id, lf.lot_id, l.style_ref
    FROM lot_factories lf
    JOIN lots l ON lf.lot_id = l.id
    WHERE l.status IN ('APPROVED', 'SHIPPED')
    AND lf.is_primary = true
    ORDER BY l.created_at DESC
    LIMIT 50
""")
lot_factories = cur.fetchall()

stages_added = 0
for lf_data in lot_factories:
    lot_factory_id = lf_data['lot_factory_id']

    # Add 6-9 stages (all completed for finished lots)
    num_stages = random.randint(6, 9)

    for i in range(num_stages):
        stage_name = SUPPLY_CHAIN_STAGES[i % len(SUPPLY_CHAIN_STAGES)]

        if stage_name not in roles:
            continue

        role_id = roles[stage_name]

        # All stages completed (in the past)
        days_ago = random.randint(30 + (num_stages - i) * 3, 60 + (num_stages - i) * 5)
        started_at = datetime.now() - timedelta(days=days_ago)
        completed_at = started_at + timedelta(days=random.randint(1, 3))

        try:
            role_entry_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO lot_factory_roles (
                    id, lot_factory_id, role_id, sequence, status,
                    started_at, completed_at, co2_kg,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 'COMPLETED', %s, %s, %s, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """, (
                role_entry_id, lot_factory_id, role_id, i + 1,
                started_at, completed_at, random.uniform(5.0, 50.0)
            ))

            if cur.rowcount > 0:
                stages_added += 1
        except Exception as e:
            print(f"  ✗ Error adding stage: {e}")
            conn.rollback()

conn.commit()
print(f"Added {stages_added} completed supply chain stages")
print("")

# ============================================================================
# STEP 6: Update existing lots to APPROVED/SHIPPED status
# ============================================================================
print("Step 5: Converting existing lots to finished status...")
print("-" * 60)

# Update some IN_PRODUCTION and INSPECTION lots to APPROVED/SHIPPED
cur.execute("""
    UPDATE lots
    SET status = 'APPROVED',
        updated_at = NOW()
    WHERE status IN ('IN_PRODUCTION', 'INSPECTION', 'PENDING_APPROVAL')
    AND id IN (
        SELECT id FROM lots
        WHERE status IN ('IN_PRODUCTION', 'INSPECTION', 'PENDING_APPROVAL')
        ORDER BY RANDOM()
        LIMIT 15
    )
""")
approved_count = cur.rowcount

cur.execute("""
    UPDATE lots
    SET status = 'SHIPPED',
        updated_at = NOW()
    WHERE status = 'APPROVED'
    AND id IN (
        SELECT id FROM lots
        WHERE status = 'APPROVED'
        ORDER BY RANDOM()
        LIMIT 10
    )
""")
shipped_count = cur.rowcount

conn.commit()
print(f"  ✓ Converted {approved_count} lots to APPROVED")
print(f"  ✓ Converted {shipped_count} lots to SHIPPED")
print("")

# ============================================================================
# STEP 7: Add DPP metadata to finished lots without it
# ============================================================================
print("Step 6: Adding DPP metadata to finished lots...")
print("-" * 60)

cur.execute("""
    SELECT id, style_ref
    FROM lots
    WHERE status IN ('APPROVED', 'SHIPPED')
    AND dpp_metadata IS NULL
    LIMIT 30
""")
lots_without_dpp = cur.fetchall()

dpp_added = 0
for lot in lots_without_dpp:
    dpp_metadata = {
        "dppId": f"DPP-{str(uuid.uuid4())[:8].upper()}",
        "version": "1.0",
        "status": "active",
        "publicUrl": f"https://dpp.packpolish.com/{lot['id']}",
        "lastAudit": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "traceabilityScore": random.randint(88, 99),
        "co2FootprintKg": round(random.uniform(15.5, 75.3), 1),
        "sustainabilityHighlights": [
            "GOTS certified organic materials",
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

        dpp_added += 1
    except Exception as e:
        print(f"  ✗ Error adding DPP: {e}")
        conn.rollback()

conn.commit()
print(f"Added DPP metadata to {dpp_added} lots")
print("")

# ============================================================================
# STEP 8: Summary statistics
# ============================================================================
print("Step 7: Summary Statistics...")
print("-" * 60)

# Count lots by status
cur.execute("""
    SELECT status, COUNT(*) as count
    FROM lots
    GROUP BY status
    ORDER BY status
""")
status_stats = cur.fetchall()

print("Lots by status:")
for stat in status_stats:
    print(f"  • {stat['status']}: {stat['count']} lots")

print("")

# Count lots with complete supply chain
cur.execute("""
    SELECT COUNT(DISTINCT l.id) as count
    FROM lots l
    JOIN lot_factories lf ON l.id = lf.lot_id
    JOIN (
        SELECT lot_factory_id, COUNT(*) as stage_count
        FROM lot_factory_roles
        WHERE status = 'COMPLETED'
        GROUP BY lot_factory_id
        HAVING COUNT(*) >= 6
    ) stages ON lf.id = stages.lot_factory_id
    WHERE l.status IN ('APPROVED', 'SHIPPED')
""")
complete_supply_chain = cur.fetchone()['count']

print(f"Lots with complete supply chain (6+ stages): {complete_supply_chain}")

# Count lots with DPP
cur.execute("""
    SELECT COUNT(*) as count
    FROM lots
    WHERE dpp_metadata IS NOT NULL
""")
dpp_count = cur.fetchone()['count']

print(f"Lots with DPP metadata: {dpp_count}")

print("")

print("=" * 60)
print("✓ Finished Lots Creation Complete!")
print("=" * 60)
print(f"Summary:")
print(f"  - {lots_created} new finished lots created")
print(f"  - {factory_rels_added} factory relationships added")
print(f"  - {stages_added} completed supply chain stages added")
print(f"  - {approved_count} lots converted to APPROVED")
print(f"  - {shipped_count} lots converted to SHIPPED")
print(f"  - {dpp_added} DPP metadata records added")
print(f"  - {complete_supply_chain} lots with complete supply chain")
print(f"  - {dpp_count} total lots with DPP metadata")
print("")

cur.close()
conn.close()
