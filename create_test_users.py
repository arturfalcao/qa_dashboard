#!/usr/bin/env python3
"""
Create test users for the mock tenants with known credentials
"""

import psycopg2
import psycopg2.extras
import uuid
import bcrypt

# Register UUID adapter
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

def hash_password(password: str) -> str:
    """Hash password using bcrypt (same as the API)"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def get_role_id(role_name: str) -> uuid.UUID:
    """Get role ID by name"""
    cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
    result = cur.fetchone()
    if result:
        return result[0]
    raise ValueError(f"Role {role_name} not found")

def create_user(tenant_id: uuid.UUID, email: str, password: str, role_names: list):
    """Create a user with given roles"""
    user_id = uuid.uuid4()
    password_hash = hash_password(password)

    # Insert user
    cur.execute("""
        INSERT INTO users (id, tenant_id, email, password_hash, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, true, NOW(), NOW())
        ON CONFLICT (tenant_id, email) DO NOTHING
        RETURNING id
    """, (user_id, tenant_id, email.lower(), password_hash))

    result = cur.fetchone()
    if result:
        actual_user_id = result[0]

        # Assign roles
        for role_name in role_names:
            role_id = get_role_id(role_name)
            cur.execute("""
                INSERT INTO user_roles (id, user_id, role_id, is_primary, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id, role_id) DO NOTHING
            """, (uuid.uuid4(), actual_user_id, role_id, True))

        print(f"  ✓ Created user: {email} with roles: {', '.join(role_names)}")
        return actual_user_id
    else:
        print(f"  ↻ User already exists: {email}")
        return None

def main():
    print("=" * 70)
    print("🔐 CREATING TEST USERS WITH CREDENTIALS")
    print("=" * 70)

    try:
        # Get the newly created tenants
        cur.execute("""
            SELECT id, name, slug FROM tenants
            WHERE slug IN ('luxe-atelier', 'urban-thread', 'coastal-wear',
                          'midnight-couture', 'rebel-stitch', 'eco-textile')
            ORDER BY name
        """)
        tenants = cur.fetchall()

        if not tenants:
            print("❌ No mock tenants found! Run generate_mock_data.py first.")
            return

        # Standard password for all test users
        test_password = "password123"

        print(f"\n🔑 Using password: {test_password}")
        print("=" * 70)

        # Create users for each tenant
        for tenant_id, tenant_name, tenant_slug in tenants:
            print(f"\n👥 Creating users for {tenant_name} ({tenant_slug}):")

            # Admin user
            create_user(
                tenant_id,
                f"admin@{tenant_slug}.com",
                test_password,
                ["ADMIN"]
            )

            # Quality Director user
            create_user(
                tenant_id,
                f"director@{tenant_slug}.com",
                test_password,
                ["QUALITY_DIRECTOR"]
            )

            # Ops Manager user
            create_user(
                tenant_id,
                f"manager@{tenant_slug}.com",
                test_password,
                ["OPS_MANAGER"]
            )

            # Inspector user
            create_user(
                tenant_id,
                f"inspector@{tenant_slug}.com",
                test_password,
                ["INSPECTOR"]
            )

            # Operator user
            create_user(
                tenant_id,
                f"operator@{tenant_slug}.com",
                test_password,
                ["OPERATOR"]
            )

            # Client Viewer user
            create_user(
                tenant_id,
                f"viewer@{tenant_slug}.com",
                test_password,
                ["CLIENT_VIEWER"]
            )

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 70)
        print("✅ TEST USERS CREATED SUCCESSFULLY!")
        print("=" * 70)

        # Print credentials summary
        print("\n📋 CREDENTIALS SUMMARY:")
        print("=" * 70)
        print(f"Password for all users: {test_password}\n")

        for tenant_id, tenant_name, tenant_slug in tenants:
            print(f"\n{tenant_name.upper()} ({tenant_slug}):")
            print(f"  Admin:     admin@{tenant_slug}.com")
            print(f"  Director:  director@{tenant_slug}.com")
            print(f"  Manager:   manager@{tenant_slug}.com")
            print(f"  Inspector: inspector@{tenant_slug}.com")
            print(f"  Operator:  operator@{tenant_slug}.com")
            print(f"  Viewer:    viewer@{tenant_slug}.com")

        # Count total users
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        print(f"\n📊 Total users in database: {total_users}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
