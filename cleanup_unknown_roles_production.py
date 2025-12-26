#!/usr/bin/env python3
"""
Clean up "Unknown Role" garbage entries from production database
"""

import psycopg2
import psycopg2.extras

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
print("Clean Up Unknown Roles (Production)")
print("=" * 60)
print("")

# ============================================================================
# STEP 1: Find all "Unknown Role" entries
# ============================================================================
print("Step 1: Finding Unknown Role entries...")
print("-" * 60)

# Check supply_chain_roles table
cur.execute("""
    SELECT id, name, description
    FROM supply_chain_roles
    WHERE name LIKE 'Unknown%' OR name LIKE '%Unknown%'
    ORDER BY name
""")
unknown_supply_chain_roles = cur.fetchall()

if unknown_supply_chain_roles:
    print(f"Found {len(unknown_supply_chain_roles)} Unknown entries in supply_chain_roles:")
    for role in unknown_supply_chain_roles:
        print(f"  - {role['name']} ({role['id']})")
else:
    print("  ✓ No Unknown entries in supply_chain_roles")

print("")

# Check roles table
cur.execute("""
    SELECT id, name, description
    FROM roles
    WHERE name LIKE 'Unknown%' OR name LIKE '%Unknown%'
    ORDER BY name
""")
unknown_roles = cur.fetchall()

if unknown_roles:
    print(f"Found {len(unknown_roles)} Unknown entries in roles:")
    for role in unknown_roles:
        print(f"  - {role['name']} ({role['id']})")
else:
    print("  ✓ No Unknown entries in roles")

print("")

# ============================================================================
# STEP 2: Check for any lot_factory_roles using these Unknown entries
# ============================================================================
if unknown_supply_chain_roles:
    print("Step 2: Checking for lot_factory_roles using Unknown supply_chain_roles...")
    print("-" * 60)

    unknown_ids = [str(role['id']) for role in unknown_supply_chain_roles]

    cur.execute("""
        SELECT COUNT(*) as count
        FROM lot_factory_roles
        WHERE role_id = ANY(%s::uuid[])
    """, (unknown_ids,))

    result = cur.fetchone()
    usage_count = result['count'] if result else 0

    if usage_count > 0:
        print(f"  ⚠️  WARNING: {usage_count} lot_factory_roles entries are using these Unknown roles")
        print("  These will be deleted along with the Unknown roles")
    else:
        print("  ✓ No lot_factory_roles are using these Unknown roles")

    print("")

# ============================================================================
# STEP 3: Check for any user_roles using these Unknown entries
# ============================================================================
if unknown_roles:
    print("Step 3: Checking for user_roles using Unknown roles...")
    print("-" * 60)

    unknown_ids = [str(role['id']) for role in unknown_roles]

    cur.execute("""
        SELECT COUNT(*) as count
        FROM user_roles
        WHERE role_id = ANY(%s::uuid[])
    """, (unknown_ids,))

    result = cur.fetchone()
    usage_count = result['count'] if result else 0

    if usage_count > 0:
        print(f"  ⚠️  WARNING: {usage_count} user_roles entries are using these Unknown roles")
        print("  These will be deleted along with the Unknown roles")
    else:
        print("  ✓ No user_roles are using these Unknown roles")

    print("")

# ============================================================================
# STEP 4: Delete the Unknown entries
# ============================================================================
total_deleted = 0

if unknown_supply_chain_roles:
    print("Step 4: Deleting Unknown supply_chain_roles...")
    print("-" * 60)

    unknown_ids = [str(role['id']) for role in unknown_supply_chain_roles]

    # First delete any lot_factory_roles that reference them
    cur.execute("""
        DELETE FROM lot_factory_roles
        WHERE role_id = ANY(%s::uuid[])
    """, (unknown_ids,))

    deleted_lfr = cur.rowcount
    if deleted_lfr > 0:
        print(f"  ✓ Deleted {deleted_lfr} lot_factory_roles entries")

    # Then delete the Unknown supply_chain_roles
    cur.execute("""
        DELETE FROM supply_chain_roles
        WHERE id = ANY(%s::uuid[])
    """, (unknown_ids,))

    deleted_scr = cur.rowcount
    print(f"  ✓ Deleted {deleted_scr} Unknown supply_chain_roles")
    total_deleted += deleted_scr

    conn.commit()
    print("")

if unknown_roles:
    print("Step 5: Deleting Unknown roles...")
    print("-" * 60)

    unknown_ids = [str(role['id']) for role in unknown_roles]

    # First delete any user_roles that reference them
    cur.execute("""
        DELETE FROM user_roles
        WHERE role_id = ANY(%s::uuid[])
    """, (unknown_ids,))

    deleted_ur = cur.rowcount
    if deleted_ur > 0:
        print(f"  ✓ Deleted {deleted_ur} user_roles entries")

    # Then delete the Unknown roles
    cur.execute("""
        DELETE FROM roles
        WHERE id = ANY(%s::uuid[])
    """, (unknown_ids,))

    deleted_r = cur.rowcount
    print(f"  ✓ Deleted {deleted_r} Unknown roles")
    total_deleted += deleted_r

    conn.commit()
    print("")

# ============================================================================
# STEP 6: Verify cleanup
# ============================================================================
print("Step 6: Verifying cleanup...")
print("-" * 60)

cur.execute("""
    SELECT COUNT(*) as count
    FROM supply_chain_roles
    WHERE name LIKE 'Unknown%' OR name LIKE '%Unknown%'
""")
remaining_scr = cur.fetchone()['count']

cur.execute("""
    SELECT COUNT(*) as count
    FROM roles
    WHERE name LIKE 'Unknown%' OR name LIKE '%Unknown%'
""")
remaining_r = cur.fetchone()['count']

if remaining_scr == 0 and remaining_r == 0:
    print("  ✓ All Unknown entries have been removed!")
else:
    print(f"  ⚠️  Still found {remaining_scr} Unknown supply_chain_roles and {remaining_r} Unknown roles")

print("")

print("=" * 60)
print("✓ Cleanup Complete!")
print("=" * 60)
print(f"Deleted {total_deleted} Unknown role entries")
print("")

cur.close()
conn.close()
