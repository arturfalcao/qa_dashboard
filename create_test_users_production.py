#!/usr/bin/env python3
"""
Create test users for QA Dashboard - Production Version
Connects directly to DigitalOcean PostgreSQL
"""

import psycopg2
import psycopg2.extras
import uuid
import bcrypt

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
print("QA Dashboard - Test Users Generator (Production)")
print("=" * 60)
print(f"Connected to: {conn.info.host}")
print(f"Database: {conn.info.dbname}")
print("")

# Password for all users
PASSWORD = "password123"
hashed_password = bcrypt.hashpw(PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# User roles
ROLES = [
    {"name": "ADMIN", "email_prefix": "admin"},
    {"name": "QUALITY_DIRECTOR", "email_prefix": "director"},
    {"name": "OPS_MANAGER", "email_prefix": "manager"},
    {"name": "INSPECTOR", "email_prefix": "inspector"},
    {"name": "OPERATOR", "email_prefix": "operator"},
    {"name": "CLIENT_VIEWER", "email_prefix": "viewer"},
]

print("Step 1: Fetching Tenants...")
cur.execute("SELECT id, name, slug FROM tenants ORDER BY name")
tenants = cur.fetchall()
print(f"Found {len(tenants)} tenants\n")

if len(tenants) == 0:
    print("✗ No tenants found. Run generate_mock_data_production.py first!")
    cur.close()
    conn.close()
    exit(1)

print("Step 2: Creating Users...")
user_count = 0

for tenant_id, tenant_name, tenant_slug in tenants:
    print(f"\n  Tenant: {tenant_name}")

    for role in ROLES:
        user_id = str(uuid.uuid4())
        email = f"{role['email_prefix']}@{tenant_slug}.com"

        try:
            # Check if user already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                print(f"    - {email} (already exists)")
                continue

            cur.execute("""
                INSERT INTO users (
                    id, tenant_id, email, password_hash,
                    is_active, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, true, NOW(), NOW())
                RETURNING id
            """, (user_id, tenant_id, email, hashed_password))

            result = cur.fetchone()
            if result:
                user_count += 1
                print(f"    ✓ {email}")

        except Exception as e:
            print(f"    ✗ Error creating {email}: {e}")
            conn.rollback()

conn.commit()

print("\n" + "=" * 60)
print("✓ Test Users Creation Complete!")
print("=" * 60)
print(f"Created {user_count} users")
print(f"Password for all users: {PASSWORD}")
print("")
print("Sample logins:")
print("  admin@luxe-atelier.com")
print("  director@urban-thread.com")
print("  manager@coastal-wear.com")
print("  inspector@midnight-couture.com")
print("  operator@rebel-stitch.com")
print("  viewer@eco-textile.com")
print("")

cur.close()
conn.close()
