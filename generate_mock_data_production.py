#!/usr/bin/env python3
"""
Generate mock data for QA Dashboard - Production Version
Connects directly to DigitalOcean PostgreSQL
"""

import psycopg2
import psycopg2.extras
import uuid
from datetime import datetime, timedelta
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
print("QA Dashboard - Mock Data Generator (Production)")
print("=" * 60)
print(f"Connected to: {conn.info.host}")
print(f"Database: {conn.info.dbname}")
print("")

# Fashion brands (tenants)
TENANTS = [
    {"name": "Luxe Atelier", "slug": "luxe-atelier"},
    {"name": "Urban Thread Co.", "slug": "urban-thread"},
    {"name": "Coastal Wear", "slug": "coastal-wear"},
    {"name": "Midnight Couture", "slug": "midnight-couture"},
    {"name": "Rebel Stitch", "slug": "rebel-stitch"},
    {"name": "Eco Textile Lab", "slug": "eco-textile"},
]

# Premium fashion clients
CLIENTS = [
    {"name": "Hermès Europe", "country": "France"},
    {"name": "Brunello Cucinelli", "country": "Italy"},
    {"name": "Nike EMEA", "country": "Netherlands"},
    {"name": "Uniqlo Global", "country": "Japan"},
    {"name": "H&M Conscious", "country": "Sweden"},
    {"name": "Patagonia", "country": "USA"},
    {"name": "Roxy International", "country": "USA"},
    {"name": "Yves Saint Laurent", "country": "France"},
    {"name": "Alexander McQueen", "country": "UK"},
    {"name": "Supreme", "country": "USA"},
    {"name": "Off-White™", "country": "Italy"},
    {"name": "Stella McCartney", "country": "UK"},
    {"name": "Reformation", "country": "USA"},
]

# Global factories
FACTORIES = [
    {"name": "Porto Premium Textiles", "city": "Porto", "country": "PT"},
    {"name": "Guimarães Couture Factory", "city": "Guimarães", "country": "PT"},
    {"name": "Firenze Fine Fabrics", "city": "Florence", "country": "IT"},
    {"name": "Milano Atelier Manifattura", "city": "Milan", "country": "IT"},
    {"name": "Istanbul Denim Works", "city": "Istanbul", "country": "TR"},
    {"name": "Izmir Textile Complex", "city": "Izmir", "country": "TR"},
    {"name": "Casablanca Fashion Factory", "city": "Casablanca", "country": "MA"},
    {"name": "Dhaka Textile Industries", "city": "Dhaka", "country": "BD"},
    {"name": "Chittagong Garment Export", "city": "Chittagong", "country": "BD"},
    {"name": "Ho Chi Minh Apparel Co.", "city": "Ho Chi Minh City", "country": "VN"},
    {"name": "Hanoi Fashion Manufacturing", "city": "Hanoi", "country": "VN"},
    {"name": "Mumbai Garment Hub", "city": "Mumbai", "country": "IN"},
    {"name": "Bangalore Textile", "city": "Bangalore", "country": "IN"},
    {"name": "Guangzhou Mega Textiles", "city": "Guangzhou", "country": "CN"},
    {"name": "Shenzhen Smart Manufacturing", "city": "Shenzhen", "country": "CN"},
]

# Defect types
DEFECT_TYPES = [
    {"name": "Hole", "severity": "critical"},
    {"name": "Stain", "severity": "major"},
    {"name": "Seam Puckering", "severity": "minor"},
    {"name": "Loose Thread", "severity": "minor"},
    {"name": "Color Bleeding", "severity": "major"},
    {"name": "Fabric Snag", "severity": "minor"},
    {"name": "Fabric Tear", "severity": "critical"},
    {"name": "Uneven Dyeing", "severity": "major"},
    {"name": "Wrong Measurement", "severity": "critical"},
    {"name": "Button Missing", "severity": "major"},
    {"name": "Zipper Malfunction", "severity": "critical"},
    {"name": "Needle Hole", "severity": "minor"},
    {"name": "Oil Spot", "severity": "major"},
    {"name": "Crease Mark", "severity": "minor"},
    {"name": "Print Misalignment", "severity": "major"},
    {"name": "Shade Variation", "severity": "major"},
    {"name": "Shrinkage", "severity": "critical"},
    {"name": "Pilling", "severity": "minor"},
]

# Style references and garment types (using valid enum values)
STYLE_REFS = [
    {"code": "SS25-SLM-101", "garment": "DRESS_SHIRT", "material": "Cotton"},
    {"code": "FW24-OXF-205", "garment": "DRESS_SHIRT", "material": "Oxford Cotton"},
    {"code": "SS25-TSH-312", "garment": "T_SHIRT", "material": "Organic Cotton"},
    {"code": "FW24-BLZ-450", "garment": "JACKET", "material": "Wool Blend"},
    {"code": "SS25-POL-156", "garment": "POLO_SHIRT", "material": "Pique Cotton"},
    {"code": "FW24-SWT-789", "garment": "SWEATER", "material": "Cashmere"},
    {"code": "SS25-HEN-223", "garment": "T_SHIRT", "material": "Cotton"},
    {"code": "FW24-FLN-334", "garment": "DRESS_SHIRT", "material": "Brushed Cotton"},
    {"code": "SS25-MXD-401", "garment": "DRESS", "material": "Silk"},
    {"code": "FW24-EVD-502", "garment": "DRESS", "material": "Velvet"},
    {"code": "SS25-MNS-603", "garment": "SKIRT", "material": "Denim"},
    {"code": "FW24-DNM-712", "garment": "JEANS", "material": "Stretch Denim"},
    {"code": "SS25-CHN-825", "garment": "PANTS", "material": "Cotton Twill"},
    {"code": "FW24-CRG-936", "garment": "PANTS", "material": "Canvas"},
    {"code": "SS25-JGR-147", "garment": "PANTS", "material": "French Terry"},
    {"code": "FW24-PCR-258", "garment": "COAT", "material": "Wool"},
    {"code": "SS25-WBR-369", "garment": "JACKET", "material": "Nylon"},
    {"code": "FW24-BOM-471", "garment": "JACKET", "material": "Leather"},
    {"code": "SS25-HOD-580", "garment": "HOODIE", "material": "Cotton Fleece"},
    {"code": "FW24-SWT-690", "garment": "SWEATSHIRT", "material": "Cotton"},
    {"code": "SS25-ACT-710", "garment": "ACTIVEWEAR", "material": "Polyester"},
    {"code": "SS25-SHR-820", "garment": "SHORTS", "material": "Cotton"},
]

print("Step 1: Creating Tenants...")
tenant_ids = []
for tenant in TENANTS:
    tenant_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO tenants (id, name, slug, created_at, updated_at)
        VALUES (%s, %s, %s, NOW(), NOW())
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
    """, (tenant_id, tenant["name"], tenant["slug"]))
    result = cur.fetchone()
    if result:
        tenant_ids.append(result[0])
        print(f"  ✓ {tenant['name']}")
    else:
        cur.execute("SELECT id FROM tenants WHERE slug = %s", (tenant["slug"],))
        tenant_ids.append(cur.fetchone()[0])
        print(f"  - {tenant['name']} (already exists)")

conn.commit()
print(f"Created {len(tenant_ids)} tenants\n")

print("Step 2: Creating Clients...")
client_ids = []
for client in CLIENTS[:len(tenant_ids) * 2]:  # 2 clients per tenant
    tenant_id = random.choice(tenant_ids)
    client_id = str(uuid.uuid4())

    try:
        cur.execute("""
            INSERT INTO clients (id, tenant_id, name, country, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (client_id, tenant_id, client["name"], client["country"]))
        result = cur.fetchone()
        if result:
            client_ids.append(result[0])
            print(f"  ✓ {client['name']}")
    except Exception as e:
        print(f"  - {client['name']} (error: {e})")
        conn.rollback()

conn.commit()
print(f"Created {len(client_ids)} clients\n")

print("Step 3: Creating Factories...")
factory_ids = []
for factory in FACTORIES:
    tenant_id = random.choice(tenant_ids)
    factory_id = str(uuid.uuid4())

    try:
        cur.execute("""
            INSERT INTO factories (id, tenant_id, name, city, country, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (factory_id, tenant_id, factory["name"], factory["city"], factory["country"]))
        result = cur.fetchone()
        if result:
            factory_ids.append(result[0])
            print(f"  ✓ {factory['name']}")
    except Exception as e:
        print(f"  - {factory['name']} (error: {e})")
        conn.rollback()

conn.commit()
print(f"Created {len(factory_ids)} factories\n")

print("Step 4: Creating Defect Types...")
defect_type_ids = []
for defect in DEFECT_TYPES:
    defect_id = str(uuid.uuid4())

    try:
        cur.execute("""
            INSERT INTO defect_types (id, name, category, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (defect_id, defect["name"], defect["severity"]))
        result = cur.fetchone()
        if result:
            defect_type_ids.append(result[0])
            print(f"  ✓ {defect['name']} ({defect['severity']})")
    except Exception as e:
        print(f"  - {defect['name']} (error: {e})")
        conn.rollback()

conn.commit()
print(f"Created {len(defect_type_ids)} defect types\n")

print("Step 5: Creating Production Lots...")
statuses = ["PLANNED", "IN_PRODUCTION", "INSPECTION", "PENDING_APPROVAL", "APPROVED", "REJECTED", "SHIPPED"]
certifications = ["GOTS", "OEKO-TEX", "Fair Trade", "BSCI", "ISO 9001", "WRAP", "SA8000"]

lot_count = 0
for style in STYLE_REFS * 3:  # 3 lots per style = 54 lots
    if client_ids and factory_ids:
        tenant_id = random.choice(tenant_ids)
        lot_id = str(uuid.uuid4())

        # Get a client and factory from the same tenant
        cur.execute("SELECT id FROM clients WHERE tenant_id = %s LIMIT 1", (tenant_id,))
        client_result = cur.fetchone()
        if not client_result:
            continue

        cur.execute("SELECT id FROM factories WHERE tenant_id = %s LIMIT 1", (tenant_id,))
        factory_result = cur.fetchone()
        if not factory_result:
            continue

        client_id = client_result[0]
        factory_id = factory_result[0]

        quantity = random.randint(500, 10000)
        status = random.choice(statuses)

        # Certifications as array of objects
        cert_list = [{"type": cert, "number": f"{cert[:3].upper()}-{random.randint(100000, 999999)}"}
                     for cert in random.sample(certifications, k=random.randint(2, 4))]

        # Material composition as array of objects
        material_json = [{"fiber": style["material"], "percentage": 100, "properties": {}}]

        cur.execute("""
            INSERT INTO lots (
                id, tenant_id, client_id, factory_id, style_ref,
                garment_type, quantity_total, status, material_composition,
                certifications, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW(), NOW())
        """, (
            lot_id, tenant_id, client_id, factory_id, style["code"],
            style["garment"], quantity, status,
            psycopg2.extras.Json(material_json),
            psycopg2.extras.Json(cert_list)
        ))
        lot_count += 1

conn.commit()
print(f"Created {lot_count} production lots\n")

print("=" * 60)
print("✓ Mock Data Generation Complete!")
print("=" * 60)
print(f"Tenants: {len(tenant_ids)}")
print(f"Clients: {len(client_ids)}")
print(f"Factories: {len(factory_ids)}")
print(f"Defect Types: {len(defect_type_ids)}")
print(f"Lots: {lot_count}")
print("")

cur.close()
conn.close()
