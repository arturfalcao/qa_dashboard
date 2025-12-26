#!/usr/bin/env python3
"""
Assign roles to users in production database
"""

import psycopg2
import psycopg2.extras
import uuid

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
print("Assign User Roles (Production)")
print("=" * 60)
print("")

# Get roles
cur.execute("SELECT id, name FROM roles")
roles_map = {row[1]: row[0] for row in cur.fetchall()}
print("Available roles:")
for name, role_id in roles_map.items():
    print(f"  - {name}: {role_id}")
print("")

# Email prefix to role mapping
EMAIL_TO_ROLE = {
    "admin": "ADMIN",
    "director": "CLEVEL",
    "manager": "OPS_MANAGER",
    "inspector": "INSPECTOR",
    "operator": "OPERATOR",
    "viewer": "CLIENT_VIEWER",
}

# Get all users
cur.execute("SELECT id, email FROM users ORDER BY email")
users = cur.fetchall()
print(f"Found {len(users)} users\n")

assigned_count = 0
skipped_count = 0

for user_id, email in users:
    # Extract prefix from email
    email_prefix = email.split('@')[0]

    # Determine role based on prefix
    role_name = EMAIL_TO_ROLE.get(email_prefix)

    if not role_name:
        print(f"  ✗ {email} - unknown prefix '{email_prefix}'")
        skipped_count += 1
        continue

    role_id = roles_map.get(role_name)
    if not role_id:
        print(f"  ✗ {email} - role '{role_name}' not found")
        skipped_count += 1
        continue

    # Check if user_role already exists
    cur.execute("""
        SELECT id FROM user_roles
        WHERE user_id = %s AND role_id = %s
    """, (user_id, role_id))

    if cur.fetchone():
        print(f"  - {email} → {role_name} (already assigned)")
        skipped_count += 1
        continue

    # Assign role
    try:
        user_role_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO user_roles (id, user_id, role_id, is_primary, created_at, updated_at)
            VALUES (%s, %s, %s, true, NOW(), NOW())
        """, (user_role_id, user_id, role_id))

        print(f"  ✓ {email} → {role_name}")
        assigned_count += 1
    except Exception as e:
        print(f"  ✗ {email} → {role_name} (error: {e})")
        conn.rollback()

conn.commit()

print("\n" + "=" * 60)
print("✓ Role Assignment Complete!")
print("=" * 60)
print(f"Assigned: {assigned_count}")
print(f"Skipped: {skipped_count}")
print(f"Total: {len(users)}")
print("")

cur.close()
conn.close()
