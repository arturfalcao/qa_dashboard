#!/usr/bin/env python3
"""
Create demo users for Pedrosa e Rodrigues tenant with known passwords
"""

import psycopg2
import bcrypt
import uuid
from datetime import datetime

# Production database connection
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

TENANT_ID = '1ad2510c-3503-4393-a643-1be7f94804ba'  # Pedrosa e Rodrigues

# Demo users - password for all: "Demo2024!"
DEMO_PASSWORD = "Demo2024!"

USERS = [
    {
        'email': 'admin@pedrosa-rodrigues.pt',
        'role': 'ADMIN',
        'description': 'Administrator - Full access'
    },
    {
        'email': 'manager@pedrosa-rodrigues.pt',
        'role': 'OPS_MANAGER',
        'description': 'Operations Manager'
    },
    {
        'email': 'inspector@pedrosa-rodrigues.pt',
        'role': 'INSPECTOR',
        'description': 'Quality Inspector'
    },
    {
        'email': 'operator@pedrosa-rodrigues.pt',
        'role': 'OPERATOR',
        'description': 'Factory Operator'
    },
    {
        'email': 'cliente@pedrosa-rodrigues.pt',
        'role': 'CLIENT_VIEWER',
        'description': 'Client Viewer - Read-only access'
    }
]

def hash_password(password):
    """Generate bcrypt hash for password"""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_users(conn):
    """Create demo users"""
    cursor = conn.cursor()

    # Get role IDs
    cursor.execute("SELECT id, name FROM roles")
    roles = {name: id for id, name in cursor.fetchall()}

    print(f"\n👤 Creating demo users for Pedrosa e Rodrigues...")
    print(f"📧 Password for all users: {DEMO_PASSWORD}")
    print("=" * 60)

    password_hash = hash_password(DEMO_PASSWORD)
    created_users = []

    for user_data in USERS:
        if user_data['role'] not in roles:
            print(f"  ⚠️  Role {user_data['role']} not found, skipping {user_data['email']}")
            continue

        user_id = str(uuid.uuid4())

        try:
            # Create user
            cursor.execute("""
                INSERT INTO users (
                    id, tenant_id, email, password_hash, is_active,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, TENANT_ID, user_data['email'], password_hash, True,
                datetime.now(), datetime.now()
            ))

            # Assign role
            cursor.execute("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
            """, (user_id, roles[user_data['role']]))

            created_users.append(user_data)
            print(f"  ✅ {user_data['email']}")
            print(f"      Role: {user_data['role']}")
            print(f"      Description: {user_data['description']}")
            print()

        except Exception as e:
            print(f"  ❌ Error creating {user_data['email']}: {e}")
            conn.rollback()
            continue

    conn.commit()

    return created_users

def main():
    print("=" * 60)
    print("🔐 PEDROSA E RODRIGUES - DEMO USERS SETUP")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to database")

        created_users = create_users(conn)

        print("=" * 60)
        print("✅ USER CREATION COMPLETE!")
        print("=" * 60)
        print(f"\n📋 DEMO LOGIN CREDENTIALS:")
        print(f"{'='*60}")
        print(f"{'Email':<40} {'Role':<20}")
        print(f"{'-'*60}")

        for user in created_users:
            print(f"{user['email']:<40} {user['role']:<20}")

        print(f"{'-'*60}")
        print(f"Password for ALL users: {DEMO_PASSWORD}")
        print(f"{'='*60}")
        print(f"\n💡 Recommended for demo:")
        print(f"   • Use admin@pedrosa-rodrigues.pt for full demo")
        print(f"   • Use cliente@pedrosa-rodrigues.pt for client view demo")
        print()

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
