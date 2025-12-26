#!/usr/bin/env python3
"""
Assign capabilities (supply chain roles) to factories in production database
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
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 60)
print("Assign Factory Capabilities (Production)")
print("=" * 60)
print("")

# ============================================================================
# STEP 1: Get all supply chain roles
# ============================================================================
print("Step 1: Loading supply chain roles...")
print("-" * 60)

cur.execute("""
    SELECT id, name, description
    FROM supply_chain_roles
    ORDER BY name
""")
roles = {row['name']: row for row in cur.fetchall()}
print(f"Found {len(roles)} supply chain roles")
print("")

# ============================================================================
# STEP 2: Get all factories
# ============================================================================
print("Step 2: Loading factories...")
print("-" * 60)

cur.execute("""
    SELECT id, name, city, country
    FROM factories
    ORDER BY name
""")
factories = cur.fetchall()
print(f"Found {len(factories)} factories")
print("")

# ============================================================================
# STEP 3: Define capability profiles based on factory type
# ============================================================================
print("Step 3: Defining capability profiles...")
print("-" * 60)

# Core capabilities most factories should have
CORE_CAPABILITIES = [
    "Marker Cutting",
    "Bundling & Sewing",
    "Inline QC",
    "Iron, Press & Dethread",
    "Final QA",
    "Pack, Tag & Bag",
]

# Fabric-focused capabilities
FABRIC_CAPABILITIES = [
    "Fiber Preparation",
    "Fabric Dye & Finish",
    "Fabric Inspection & Relax",
    "Fabric Wash & Prep",
    "Fabric Lab Testing",
]

# Finishing capabilities
FINISHING_CAPABILITIES = [
    "Garment Wash & Soften",
    "Functional Coating",
    "Screen Printing",
    "Digital Printing",
    "Embroidery & Laser",
    "Heat Transfer",
    "Sublimation",
]

# Premium/specialized capabilities
PREMIUM_CAPABILITIES = [
    "Pattern & Grading",
    "Trims & Embellishment",
    "Needle & Metal Detection",
    "Regulatory Checks",
    "Sustainability Tracking",
    "Documentation & DPP",
]

# Logistics capabilities
LOGISTICS_CAPABILITIES = [
    "Warehouse & Logistics",
]

# Factory profiles by region/type
FACTORY_PROFILES = {
    # European factories: Premium with full capabilities
    "PT": {  # Portugal
        "core": 1.0,  # 100% chance of having core capabilities
        "fabric": 0.9,
        "finishing": 0.8,
        "premium": 0.9,
        "logistics": 0.7,
    },
    "IT": {  # Italy
        "core": 1.0,
        "fabric": 0.9,
        "finishing": 0.9,
        "premium": 1.0,
        "logistics": 0.7,
    },
    "ES": {  # Spain
        "core": 1.0,
        "fabric": 0.8,
        "finishing": 0.8,
        "premium": 0.8,
        "logistics": 0.7,
    },
    "FR": {  # France
        "core": 1.0,
        "fabric": 0.9,
        "finishing": 0.9,
        "premium": 1.0,
        "logistics": 0.7,
    },
    "CZ": {  # Czech Republic
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.7,
        "premium": 0.6,
        "logistics": 0.6,
    },
    "PL": {  # Poland
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.7,
        "premium": 0.6,
        "logistics": 0.6,
    },
    "GR": {  # Greece
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.6,
        "premium": 0.5,
        "logistics": 0.6,
    },
    "RO": {  # Romania
        "core": 1.0,
        "fabric": 0.6,
        "finishing": 0.6,
        "premium": 0.5,
        "logistics": 0.6,
    },
    "BG": {  # Bulgaria
        "core": 1.0,
        "fabric": 0.6,
        "finishing": 0.6,
        "premium": 0.5,
        "logistics": 0.6,
    },
    # Turkish factories: Strong in fabric and production
    "TR": {
        "core": 1.0,
        "fabric": 0.9,
        "finishing": 0.8,
        "premium": 0.6,
        "logistics": 0.7,
    },
    # North African factories: Cost-effective production
    "MA": {  # Morocco
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.6,
        "premium": 0.4,
        "logistics": 0.5,
    },
    "TN": {  # Tunisia
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.6,
        "premium": 0.4,
        "logistics": 0.5,
    },
    # Asian factories: High volume, good quality
    "BD": {  # Bangladesh
        "core": 1.0,
        "fabric": 0.8,
        "finishing": 0.7,
        "premium": 0.4,
        "logistics": 0.6,
    },
    "VN": {  # Vietnam
        "core": 1.0,
        "fabric": 0.8,
        "finishing": 0.7,
        "premium": 0.5,
        "logistics": 0.6,
    },
    "IN": {  # India
        "core": 1.0,
        "fabric": 0.9,
        "finishing": 0.8,
        "premium": 0.5,
        "logistics": 0.6,
    },
    "CN": {  # China
        "core": 1.0,
        "fabric": 0.9,
        "finishing": 0.9,
        "premium": 0.7,
        "logistics": 0.8,
    },
    "ID": {  # Indonesia
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.7,
        "premium": 0.4,
        "logistics": 0.6,
    },
    "PH": {  # Philippines
        "core": 1.0,
        "fabric": 0.7,
        "finishing": 0.7,
        "premium": 0.4,
        "logistics": 0.6,
    },
}

# Default profile for countries not explicitly listed
DEFAULT_PROFILE = {
    "core": 1.0,
    "fabric": 0.6,
    "finishing": 0.6,
    "premium": 0.4,
    "logistics": 0.5,
}

print("Capability profiles defined for different regions")
print("")

# ============================================================================
# STEP 4: Assign capabilities to each factory
# ============================================================================
print("Step 4: Assigning capabilities to factories...")
print("-" * 60)

assignments_made = 0
skipped = 0

for factory in factories:
    factory_id = factory['id']
    factory_name = factory['name']
    country = factory['country']

    # Get the profile for this factory's country
    profile = FACTORY_PROFILES.get(country, DEFAULT_PROFILE)

    # Build the list of capabilities this factory should have
    factory_capabilities = []

    # Core capabilities (almost always assigned)
    for cap in CORE_CAPABILITIES:
        if random.random() < profile['core']:
            factory_capabilities.append(cap)

    # Fabric capabilities
    for cap in FABRIC_CAPABILITIES:
        if random.random() < profile['fabric']:
            factory_capabilities.append(cap)

    # Finishing capabilities (select subset)
    finishing_subset = random.sample(FINISHING_CAPABILITIES, k=random.randint(2, 5))
    for cap in finishing_subset:
        if random.random() < profile['finishing']:
            factory_capabilities.append(cap)

    # Premium capabilities (select subset)
    premium_subset = random.sample(PREMIUM_CAPABILITIES, k=random.randint(2, 4))
    for cap in premium_subset:
        if random.random() < profile['premium']:
            factory_capabilities.append(cap)

    # Logistics capabilities
    for cap in LOGISTICS_CAPABILITIES:
        if random.random() < profile['logistics']:
            factory_capabilities.append(cap)

    # Remove duplicates
    factory_capabilities = list(set(factory_capabilities))

    # Assign each capability to the factory
    factory_assignments = 0
    for cap_name in factory_capabilities:
        if cap_name not in roles:
            continue

        role_id = roles[cap_name]['id']

        # Random CO2 override (some capabilities might have specific CO2 values)
        co2_override = None
        if random.random() < 0.3:  # 30% chance of having CO2 override
            co2_override = round(random.uniform(5.0, 50.0), 2)

        try:
            cur.execute("""
                INSERT INTO factory_roles (
                    id, factory_id, role_id, co2_override_kg, created_at, updated_at
                )
                VALUES (uuid_generate_v4(), %s, %s, %s, NOW(), NOW())
                ON CONFLICT (factory_id, role_id) DO NOTHING
            """, (factory_id, role_id, co2_override))

            if cur.rowcount > 0:
                factory_assignments += 1
                assignments_made += 1
        except Exception as e:
            print(f"  ✗ Error assigning {cap_name} to {factory_name}: {e}")
            conn.rollback()

    if factory_assignments > 0:
        print(f"  ✓ {factory_name} ({country}): {factory_assignments} capabilities")
    else:
        skipped += 1

conn.commit()
print("")
print(f"Total assignments: {assignments_made}")
print(f"Factories with existing capabilities (skipped): {skipped}")
print("")

# ============================================================================
# STEP 5: Show summary statistics
# ============================================================================
print("Step 5: Summary Statistics...")
print("-" * 60)

# Count factories by capability count
cur.execute("""
    SELECT
        f.country,
        COUNT(DISTINCT f.id) as factory_count,
        AVG(cap_count.count) as avg_capabilities
    FROM factories f
    LEFT JOIN (
        SELECT factory_id, COUNT(*) as count
        FROM factory_roles
        GROUP BY factory_id
    ) cap_count ON f.id = cap_count.factory_id
    GROUP BY f.country
    ORDER BY f.country
""")

country_stats = cur.fetchall()
for stat in country_stats:
    avg = stat['avg_capabilities'] or 0
    print(f"  {stat['country']}: {stat['factory_count']} factories, avg {avg:.1f} capabilities")

print("")

# Most common capabilities
cur.execute("""
    SELECT
        scr.name,
        COUNT(fr.id) as factory_count
    FROM supply_chain_roles scr
    LEFT JOIN factory_roles fr ON scr.id = fr.role_id
    GROUP BY scr.id, scr.name
    HAVING COUNT(fr.id) > 0
    ORDER BY factory_count DESC
    LIMIT 10
""")

print("Top 10 most common capabilities:")
top_caps = cur.fetchall()
for cap in top_caps:
    print(f"  • {cap['name']}: {cap['factory_count']} factories")

print("")

print("=" * 60)
print("✓ Factory Capabilities Assignment Complete!")
print("=" * 60)
print(f"Summary:")
print(f"  - {assignments_made} new capability assignments")
print(f"  - {len(factories)} factories processed")
print(f"  - {len(roles)} supply chain roles available")
print("")

cur.close()
conn.close()
