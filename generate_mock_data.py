#!/usr/bin/env python3
"""
Generate realistic mock data for QA Dashboard
Creates tenants, clients, factories, lots, and defect types with fashion industry data
"""

import psycopg2
import psycopg2.extras
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="qa_dashboard",
    user="postgres",
    password="postgres"
)
cur = conn.cursor()

# Cool fashion brands as tenants
TENANTS = [
    {"name": "Luxe Atelier", "slug": "luxe-atelier"},
    {"name": "Urban Thread Co.", "slug": "urban-thread"},
    {"name": "Coastal Wear", "slug": "coastal-wear"},
    {"name": "Midnight Couture", "slug": "midnight-couture"},
    {"name": "Rebel Stitch", "slug": "rebel-stitch"},
    {"name": "Eco Textile Lab", "slug": "eco-textile"},
]

# Fashion clients per tenant
CLIENTS = [
    # Luxe Atelier clients
    {"name": "Hermès Europe", "country": "France", "contact_email": "procurement@hermes-paris.fr"},
    {"name": "Brunello Cucinelli", "country": "Italy", "contact_email": "orders@brunello.it"},

    # Urban Thread clients
    {"name": "Nike EMEA", "country": "Netherlands", "contact_email": "supply@nike-emea.com"},
    {"name": "Uniqlo Global", "country": "Japan", "contact_email": "production@uniqlo.jp"},
    {"name": "H&M Conscious", "country": "Sweden", "contact_email": "sustainability@hm.se"},

    # Coastal Wear clients
    {"name": "Patagonia", "country": "USA", "contact_email": "sourcing@patagonia.com"},
    {"name": "Roxy International", "country": "USA", "contact_email": "production@roxy.com"},

    # Midnight Couture clients
    {"name": "Yves Saint Laurent", "country": "France", "contact_email": "atelier@ysl.fr"},
    {"name": "Alexander McQueen", "country": "UK", "contact_email": "studio@alexandermcqueen.com"},

    # Rebel Stitch clients
    {"name": "Supreme", "country": "USA", "contact_email": "production@supremenewyork.com"},
    {"name": "Off-White™", "country": "Italy", "contact_email": "manufacturing@off---white.com"},

    # Eco Textile clients
    {"name": "Stella McCartney", "country": "UK", "contact_email": "sustainable@stellamccartney.com"},
    {"name": "Reformation", "country": "USA", "contact_email": "greensupply@thereformation.com"},
]

# Manufacturing hubs with realistic factories
FACTORIES = [
    # Portugal (high-end manufacturing)
    {"name": "Porto Premium Textiles", "city": "Porto", "country": "Portugal"},
    {"name": "Guimarães Couture Factory", "city": "Guimarães", "country": "Portugal"},

    # Italy (luxury)
    {"name": "Firenze Fine Fabrics", "city": "Florence", "country": "Italy"},
    {"name": "Milano Atelier Manifattura", "city": "Milan", "country": "Italy"},

    # Bangladesh (volume production)
    {"name": "Dhaka Textile Industries Ltd", "city": "Dhaka", "country": "Bangladesh"},
    {"name": "Chittagong Garment Export", "city": "Chittagong", "country": "Bangladesh"},

    # Vietnam (quality & price balance)
    {"name": "Ho Chi Minh Apparel Co.", "city": "Ho Chi Minh City", "country": "Vietnam"},
    {"name": "Hanoi Fashion Manufacturing", "city": "Hanoi", "country": "Vietnam"},

    # Turkey (denim & casual)
    {"name": "Istanbul Denim Works", "city": "Istanbul", "country": "Turkey"},
    {"name": "Izmir Textile Complex", "city": "Izmir", "country": "Turkey"},

    # India (diverse capabilities)
    {"name": "Mumbai Garment Hub", "city": "Mumbai", "country": "India"},
    {"name": "Bangalore Textile Excellence", "city": "Bangalore", "country": "India"},

    # Morocco (fast fashion)
    {"name": "Casablanca Fashion Factory", "city": "Casablanca", "country": "Morocco"},

    # China (high volume)
    {"name": "Guangzhou Mega Textiles", "city": "Guangzhou", "country": "China"},
    {"name": "Shenzhen Smart Manufacturing", "city": "Shenzhen", "country": "China"},
]

# Style references for different garment types
STYLE_REFS = [
    # Shirts & Tops
    "SS25-SLM-001", "FW24-OXF-202", "SS25-TSH-105", "FW24-BLZ-301",
    "SS25-POL-088", "FW24-SWT-199", "SS25-HEN-042", "FW24-FLN-267",

    # Dresses & Skirts
    "SS25-MXD-311", "FW24-EVD-420", "SS25-MNS-156", "FW24-PLD-089",

    # Pants & Bottoms
    "SS25-DNM-501", "FW24-CHN-612", "SS25-CRG-305", "FW24-JGR-441",
    "SS25-SHR-223", "FW24-LEG-334",

    # Outerwear
    "FW24-PCR-701", "FW24-DNC-802", "SS25-WBR-115", "FW24-BOM-903",

    # Activewear
    "SS25-SPT-601", "SS25-YGA-502", "FW24-JKT-710", "SS25-LEG-405",

    # Knitwear
    "FW24-KNT-812", "FW24-CDG-923", "FW24-TNK-714", "FW24-PUL-625",
]

# Material compositions (realistic)
MATERIALS = [
    {"cotton": 100},
    {"cotton": 95, "elastane": 5},
    {"organic_cotton": 100},
    {"linen": 100},
    {"cotton": 70, "polyester": 30},
    {"polyester": 65, "cotton": 35},
    {"wool": 100},
    {"merino_wool": 90, "nylon": 10},
    {"cashmere": 100},
    {"silk": 100},
    {"viscose": 100},
    {"recycled_polyester": 100},
    {"hemp": 55, "cotton": 45},
    {"tencel": 100},
    {"cotton": 80, "linen": 20},
]

# Lot statuses
STATUSES = ["pending", "in_progress", "completed", "on_hold", "approved"]

# Defect types in textile QA
DEFECT_TYPES = [
    {"name": "Hole", "category": "Critical"},
    {"name": "Stain", "category": "Major"},
    {"name": "Color Bleeding", "category": "Major"},
    {"name": "Uneven Dyeing", "category": "Major"},
    {"name": "Seam Puckering", "category": "Minor"},
    {"name": "Loose Thread", "category": "Minor"},
    {"name": "Fabric Tear", "category": "Critical"},
    {"name": "Wrong Measurement", "category": "Critical"},
    {"name": "Button Missing", "category": "Major"},
    {"name": "Zipper Malfunction", "category": "Critical"},
    {"name": "Print Misalignment", "category": "Major"},
    {"name": "Fabric Snag", "category": "Minor"},
    {"name": "Needle Hole", "category": "Minor"},
    {"name": "Oil Spot", "category": "Major"},
    {"name": "Crease Mark", "category": "Minor"},
    {"name": "Shade Variation", "category": "Major"},
    {"name": "Pilling", "category": "Minor"},
    {"name": "Shrinkage", "category": "Critical"},
]

def insert_tenants() -> Dict[str, uuid.UUID]:
    """Insert tenants and return mapping of slug to ID"""
    print("🏢 Creating fashion brand tenants...")
    tenant_ids = {}

    for tenant in TENANTS:
        tenant_id = uuid.uuid4()
        cur.execute("""
            INSERT INTO tenants (id, name, slug, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (slug) DO NOTHING
            RETURNING id
        """, (tenant_id, tenant["name"], tenant["slug"]))

        result = cur.fetchone()
        if result:
            tenant_ids[tenant["slug"]] = result[0]
            print(f"  ✓ Created tenant: {tenant['name']}")
        else:
            # Get existing tenant ID
            cur.execute("SELECT id FROM tenants WHERE slug = %s", (tenant["slug"],))
            tenant_ids[tenant["slug"]] = cur.fetchone()[0]
            print(f"  ↻ Tenant already exists: {tenant['name']}")

    return tenant_ids

def insert_clients(tenant_ids: Dict[str, uuid.UUID]) -> List[uuid.UUID]:
    """Insert clients and return list of IDs"""
    print("\n👥 Creating fashion clients...")
    client_ids = []
    tenant_slugs = list(tenant_ids.keys())

    for i, client in enumerate(CLIENTS):
        # Distribute clients across tenants
        tenant_slug = tenant_slugs[i % len(tenant_slugs)]
        tenant_id = tenant_ids[tenant_slug]

        client_id = uuid.uuid4()
        cur.execute("""
            INSERT INTO clients (
                id, tenant_id, name, contact_email,
                country, is_active, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
        """, (
            client_id, tenant_id, client["name"],
            client["contact_email"], client["country"]
        ))

        client_ids.append(client_id)
        print(f"  ✓ Created client: {client['name']} ({client['country']})")

    return client_ids

def insert_factories(tenant_ids: Dict[str, uuid.UUID]) -> List[uuid.UUID]:
    """Insert factories and return list of IDs"""
    print("\n🏭 Creating manufacturing factories...")
    factory_ids = []
    tenant_list = list(tenant_ids.values())

    for factory in FACTORIES:
        # Assign factories to random tenants
        tenant_id = random.choice(tenant_list)
        factory_id = uuid.uuid4()

        cur.execute("""
            INSERT INTO factories (
                id, tenant_id, name, city, country, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """, (
            factory_id, tenant_id, factory["name"],
            factory["city"], factory["country"]
        ))

        factory_ids.append(factory_id)
        print(f"  ✓ Created factory: {factory['name']} - {factory['city']}, {factory['country']}")

    return factory_ids

def insert_lots(tenant_ids: Dict[str, uuid.UUID], client_ids: List[uuid.UUID],
                factory_ids: List[uuid.UUID]):
    """Insert production lots with realistic data"""
    print("\n📦 Creating production lots...")

    tenant_list = list(tenant_ids.values())
    lot_count = 50  # Generate 50 lots

    for i in range(lot_count):
        tenant_id = random.choice(tenant_list)
        client_id = random.choice(client_ids)
        factory_id = random.choice(factory_ids)
        style_ref = random.choice(STYLE_REFS)
        quantity = random.choice([500, 1000, 1500, 2000, 2500, 3000, 5000, 8000, 10000])
        status = random.choice(STATUSES)

        # Generate realistic defect rates based on status
        if status == "completed":
            defect_rate = round(random.uniform(0.5, 3.5), 2)
            inspected_progress = 100.0
        elif status == "in_progress":
            defect_rate = round(random.uniform(1.0, 4.0), 2)
            inspected_progress = round(random.uniform(30, 90), 2)
        else:
            defect_rate = 0.0
            inspected_progress = 0.0

        # Random material composition
        material = random.choice(MATERIALS)

        # Random certifications
        certifications = []
        if random.random() > 0.6:
            certifications.extend(random.sample([
                "GOTS", "OEKO-TEX", "Fair Trade", "BSCI",
                "ISO 9001", "WRAP", "SA8000"
            ], k=random.randint(1, 3)))

        # Created date in the last 6 months
        days_ago = random.randint(1, 180)
        created_at = datetime.now() - timedelta(days=days_ago)

        cur.execute("""
            INSERT INTO lots (
                id, tenant_id, factory_id, client_id, style_ref,
                quantity_total, status, defect_rate, inspected_progress,
                material_composition, certifications,
                created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            uuid.uuid4(), tenant_id, factory_id, client_id, style_ref,
            quantity, status, defect_rate, inspected_progress,
            psycopg2.extras.Json(material),
            psycopg2.extras.Json(certifications) if certifications else None,
            created_at, created_at
        ))

        if (i + 1) % 10 == 0:
            print(f"  ✓ Created {i + 1} lots...")

    print(f"  ✓ Total lots created: {lot_count}")

def insert_defect_types():
    """Insert defect types"""
    print("\n🔍 Creating defect types...")

    for defect in DEFECT_TYPES:
        cur.execute("""
            INSERT INTO defect_types (id, name, category, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
        """, (uuid.uuid4(), defect["name"], defect["category"]))

    print(f"  ✓ Created {len(DEFECT_TYPES)} defect types")

def main():
    """Main execution"""
    print("=" * 60)
    print("🎨 GENERATING COOL MOCK DATA FOR QA DASHBOARD")
    print("=" * 60)

    try:
        # Insert data in order (respecting foreign keys)
        tenant_ids = insert_tenants()
        client_ids = insert_clients(tenant_ids)
        factory_ids = insert_factories(tenant_ids)
        insert_defect_types()
        insert_lots(tenant_ids, client_ids, factory_ids)

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        print("✅ MOCK DATA GENERATION COMPLETE!")
        print("=" * 60)

        # Show summary
        print("\n📊 Summary:")
        cur.execute("SELECT COUNT(*) FROM tenants")
        print(f"  • Tenants: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM clients")
        print(f"  • Clients: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM factories")
        print(f"  • Factories: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM lots")
        print(f"  • Lots: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM defect_types")
        print(f"  • Defect Types: {cur.fetchone()[0]}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
