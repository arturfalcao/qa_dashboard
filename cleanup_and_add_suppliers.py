#!/usr/bin/env python3
"""
1. Remove duplicate clients (keep older ones, reassign lots)
2. Add material suppliers (fabric, trim, packaging suppliers)
"""

import psycopg2
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

TENANT_ID = '1ad2510c-3503-4393-a643-1be7f94804ba'

# Material suppliers to add
SUPPLIERS = [
    {
        'name': 'Têxtil Manuel Gonçalves',
        'contact_email': 'sales@textilfmg.pt',
        'contact_phone': '+351 252 123 456',
        'address': 'Zona Industrial de Famalicão, Vila Nova de Famalicão',
        'country': 'Portugal',
        'notes': 'Supplier - Cotton and blended fabrics, GOTS certified'
    },
    {
        'name': 'Rhodia Portugal',
        'contact_email': 'portugal@rhodia.com',
        'contact_phone': '+351 21 987 6543',
        'address': 'Lisbon',
        'country': 'Portugal',
        'notes': 'Supplier - High-quality polyester and technical fabrics'
    },
    {
        'name': 'YKK Portugal',
        'contact_email': 'info@ykk.pt',
        'contact_phone': '+351 22 334 5678',
        'address': 'Porto',
        'country': 'Portugal',
        'notes': 'Supplier - Zippers, buttons, and fasteners'
    },
    {
        'name': 'Freudenberg Portugal',
        'contact_email': 'contact@freudenberg.pt',
        'contact_phone': '+351 256 789 012',
        'address': 'Trofa',
        'country': 'Portugal',
        'notes': 'Supplier - Interlinings and technical textiles'
    },
    {
        'name': 'Coats Thread Portugal',
        'contact_email': 'portugal@coats.com',
        'contact_phone': '+351 22 445 6789',
        'address': 'Matosinhos',
        'country': 'Portugal',
        'notes': 'Supplier - Sewing threads and yarns'
    },
    {
        'name': 'Embalпортугal Embalagens',
        'contact_email': 'comercial@embalportugal.pt',
        'contact_phone': '+351 21 334 5678',
        'address': 'Amadora',
        'country': 'Portugal',
        'notes': 'Supplier - Packaging materials, polybags, cartons'
    },
    {
        'name': 'Label Plus',
        'contact_email': 'orders@labelplus.pt',
        'contact_phone': '+351 244 567 890',
        'address': 'Leiria',
        'country': 'Portugal',
        'notes': 'Supplier - Woven labels, care labels, hang tags'
    }
]

def main():
    print("=" * 60)
    print("🧹 CLEANING DUPLICATE CLIENTS & ADDING SUPPLIERS")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Step 1: Find and remove duplicate clients
        print("\n🔍 Finding duplicate clients...")

        cursor.execute("""
            SELECT name, array_agg(id::text ORDER BY created_at) as ids, array_agg(created_at ORDER BY created_at) as dates
            FROM clients
            WHERE tenant_id = %s
            GROUP BY name
            HAVING COUNT(*) > 1
        """, (TENANT_ID,))

        duplicates = cursor.fetchall()

        if duplicates:
            print(f"\n📋 Found {len(duplicates)} duplicate client names:")

            for name, ids, dates in duplicates:
                print(f"\n  • {name}")
                print(f"    IDs: {len(ids)} duplicates")

                # Keep the oldest (first) ID
                keep_id = ids[0]
                remove_ids = ids[1:]

                print(f"    ✅ Keeping: {keep_id} (created: {dates[0]})")
                print(f"    🗑️  Removing: {len(remove_ids)} duplicate(s)")

                for remove_id in remove_ids:
                    # Update lots that reference the duplicate client
                    cursor.execute("""
                        UPDATE lots
                        SET client_id = %s
                        WHERE client_id = %s
                    """, (keep_id, remove_id))

                    updated_lots = cursor.rowcount
                    if updated_lots > 0:
                        print(f"       → Reassigned {updated_lots} lots from {remove_id} to {keep_id}")

                    # Delete the duplicate client
                    cursor.execute("""
                        DELETE FROM clients WHERE id = %s
                    """, (remove_id,))

                conn.commit()
                print(f"    ✅ Cleanup complete for {name}")
        else:
            print("  ✅ No duplicate clients found")

        # Step 2: Add material suppliers
        print("\n\n📦 Adding material suppliers...")

        added_count = 0

        for supplier in SUPPLIERS:
            # Check if supplier already exists
            cursor.execute("""
                SELECT id FROM clients
                WHERE tenant_id = %s AND name = %s
            """, (TENANT_ID, supplier['name']))

            if cursor.fetchone():
                print(f"  ⚠️  {supplier['name']} - already exists")
                continue

            # Add supplier
            supplier_id = str(uuid.uuid4())
            now = datetime.now()

            cursor.execute("""
                INSERT INTO clients (
                    id, tenant_id, name, contact_email, contact_phone,
                    address, country, notes, is_active, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                supplier_id, TENANT_ID, supplier['name'],
                supplier['contact_email'], supplier['contact_phone'],
                supplier['address'], supplier['country'], supplier['notes'],
                True, now, now
            ))

            conn.commit()
            added_count += 1
            print(f"  ✅ {supplier['name']} - {supplier['notes'][:40]}...")

        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)

        # Count total clients
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN notes LIKE 'Supplier %%' THEN 1 END) as suppliers,
                   COUNT(CASE WHEN notes NOT LIKE 'Supplier %%' OR notes IS NULL THEN 1 END) as buyers
            FROM clients
            WHERE tenant_id = %s
        """, (TENANT_ID,))

        result = cursor.fetchone()
        total = result[0] if result else 0
        suppliers = result[1] if result and len(result) > 1 else 0
        buyers = result[2] if result and len(result) > 2 else 0

        print(f"  Total Clients: {total}")
        print(f"  • Buyers (Customers): {buyers}")
        print(f"  • Suppliers (Materials): {suppliers}")
        print(f"  ✅ Suppliers Added: {added_count}")
        print()

        # List all clients by type
        print("📋 Current Clients:")

        cursor.execute("""
            SELECT name, country, CASE
                WHEN notes LIKE 'Supplier %%' THEN 'Supplier'
                ELSE 'Buyer'
            END as type
            FROM clients
            WHERE tenant_id = %s
            ORDER BY type DESC, name
        """, (TENANT_ID,))

        current_type = None
        for name, country, client_type in cursor.fetchall():
            if client_type != current_type:
                print(f"\n  {client_type}s:")
                current_type = client_type
            print(f"    • {name} ({country})")

        print()
        print("✅ Client cleanup and supplier addition complete!")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
