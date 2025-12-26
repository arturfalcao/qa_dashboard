#!/usr/bin/env python3
"""
Assign multiple factories to lots in lot_factories junction table
Simulates realistic production scenarios where lots may use multiple factories
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

def main():
    print("=" * 60)
    print("🏭 ASSIGNING FACTORIES TO LOTS")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("\n📊 Fetching data...")

        # Get all factories
        cursor.execute("""
            SELECT id, name FROM factories
            WHERE tenant_id = %s
            ORDER BY name
        """, (TENANT_ID,))
        factories = cursor.fetchall()

        print(f"\n🏭 Factories available: {len(factories)}")
        for factory_id, factory_name in factories:
            print(f"   • {factory_name}")

        # Get all lots
        cursor.execute("""
            SELECT l.id, l.style_ref, l.quantity_total, l.factory_id,
                   c.name as client_name, l.garment_type
            FROM lots l
            LEFT JOIN clients c ON c.id = l.client_id
            WHERE l.tenant_id = %s
            ORDER BY l.style_ref
        """, (TENANT_ID,))
        lots = cursor.fetchall()

        print(f"\n📦 Lots to process: {len(lots)}\n")

        factory_dict = {fid: fname for fid, fname in factories}
        now = datetime.now()

        assigned_count = 0

        for lot_id, style_ref, quantity, primary_factory_id, client_name, garment_type in lots:
            primary_factory_name = factory_dict.get(primary_factory_id, "Unknown")

            print(f"📦 {style_ref} ({client_name}) - {quantity:,} units")
            print(f"   Primary: {primary_factory_name}")

            # Check if lot already has entries in lot_factories
            cursor.execute("""
                SELECT COUNT(*) FROM lot_factories WHERE lot_id = %s
            """, (lot_id,))
            existing_count = cursor.fetchone()[0]

            if existing_count > 0:
                print(f"   ⚠️  Already has {existing_count} factory assignment(s), skipping")
                continue

            # Add primary factory to lot_factories
            cursor.execute("""
                INSERT INTO lot_factories (id, lot_id, factory_id, sequence, is_primary, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (lot_id, factory_id) DO NOTHING
            """, (
                str(uuid.uuid4()), lot_id, primary_factory_id,
                0, True, now, now
            ))

            factories_assigned = [primary_factory_name]

            # For larger lots (> 5000 units), add secondary factory
            if quantity > 5000:
                # Pick a different factory
                available_factories = [fid for fid, _ in factories if fid != primary_factory_id]
                if available_factories:
                    secondary_factory_id = available_factories[0]
                    secondary_factory_name = factory_dict[secondary_factory_id]

                    cursor.execute("""
                        INSERT INTO lot_factories (id, lot_id, factory_id, sequence, stage, is_primary, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (lot_id, factory_id) DO NOTHING
                    """, (
                        str(uuid.uuid4()), lot_id, secondary_factory_id,
                        1, 'finishing', False, now, now
                    ))

                    factories_assigned.append(f"{secondary_factory_name} (finishing)")

            # For very large lots (> 10000 units), add third factory
            if quantity > 10000:
                available_factories = [fid for fid, _ in factories
                                     if fid != primary_factory_id and fid not in [f[0] for f in factories[:2]]]
                if available_factories and len(available_factories) >= 2:
                    tertiary_factory_id = available_factories[1] if len(available_factories) > 1 else available_factories[0]
                    tertiary_factory_name = factory_dict[tertiary_factory_id]

                    cursor.execute("""
                        INSERT INTO lot_factories (id, lot_id, factory_id, sequence, stage, is_primary, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (lot_id, factory_id) DO NOTHING
                    """, (
                        str(uuid.uuid4()), lot_id, tertiary_factory_id,
                        2, 'packaging', False, now, now
                    ))

                    factories_assigned.append(f"{tertiary_factory_name} (packaging)")

            conn.commit()
            assigned_count += 1

            print(f"   ✅ Assigned: {' + '.join(factories_assigned)}")
            print()

        # Summary
        print("=" * 60)
        print("📊 ASSIGNMENT SUMMARY")
        print("=" * 60)

        cursor.execute("""
            SELECT
                COUNT(DISTINCT l.id) as total_lots,
                COUNT(lf.id) as total_assignments,
                ROUND(AVG(factory_count), 2) as avg_factories_per_lot
            FROM lots l
            LEFT JOIN lot_factories lf ON lf.lot_id = l.id
            LEFT JOIN (
                SELECT lot_id, COUNT(*) as factory_count
                FROM lot_factories
                GROUP BY lot_id
            ) fc ON fc.lot_id = l.id
            WHERE l.tenant_id = %s
        """, (TENANT_ID,))

        total_lots, total_assignments, avg_factories = cursor.fetchone()

        print(f"  Total Lots: {total_lots}")
        print(f"  Total Factory Assignments: {total_assignments}")
        print(f"  Average Factories per Lot: {avg_factories or 0}")
        print(f"  Lots Processed: {assigned_count}")
        print()

        # Show distribution
        cursor.execute("""
            SELECT factory_count, COUNT(*) as lots_count
            FROM (
                SELECT l.id, COUNT(lf.id) as factory_count
                FROM lots l
                LEFT JOIN lot_factories lf ON lf.lot_id = l.id
                WHERE l.tenant_id = %s
                GROUP BY l.id
            ) counts
            GROUP BY factory_count
            ORDER BY factory_count
        """, (TENANT_ID,))

        print("📈 Distribution:")
        for factory_count, lots_count in cursor.fetchall():
            if factory_count == 0:
                print(f"  • {lots_count} lots with no factories")
            elif factory_count == 1:
                print(f"  • {lots_count} lots with 1 factory")
            else:
                print(f"  • {lots_count} lots with {factory_count} factories")

        print()
        print("✅ Factory assignments complete!")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
