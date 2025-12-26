#!/usr/bin/env python3
"""
Complete setup for Pedrosa e Rodrigues tenant (Portuguese textile manufacturer)
"""

import psycopg2
from datetime import datetime, timedelta
import random
import uuid

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
DEVICE_ID = 'c344ce0e-27b7-4af4-899e-b4fad95398ad'  # wb1

# Portuguese/European clients for a textile manufacturer
CLIENTS_DATA = [
    {
        'name': 'Zara Portugal',
        'email': 'supply@zara.pt',
        'phone': '+351 22 123 4567',
        'address': 'Av. da Boavista, Porto',
        'country': 'Portugal'
    },
    {
        'name': 'Mango Iberica',
        'email': 'procurement@mango.es',
        'phone': '+34 93 123 4567',
        'address': 'Barcelona, Spain',
        'country': 'Spain'
    },
    {
        'name': 'H&M Nordic',
        'email': 'sourcing@hm.se',
        'phone': '+46 8 123 4567',
        'address': 'Stockholm, Sweden',
        'country': 'Sweden'
    },
    {
        'name': 'Primark UK',
        'email': 'supply.chain@primark.co.uk',
        'phone': '+44 20 123 4567',
        'address': 'London, United Kingdom',
        'country': 'United Kingdom'
    },
    {
        'name': 'Decathlon France',
        'email': 'textile@decathlon.fr',
        'phone': '+33 1 23 45 67 89',
        'address': 'Lille, France',
        'country': 'France'
    }
]

# Portuguese factories
FACTORIES_DATA = [
    {'name': 'Pedrosa - Unidade Santo Tirso', 'city': 'Santo Tirso', 'country': 'PT'},
    {'name': 'Pedrosa - Unidade Guimarães', 'city': 'Guimarães', 'country': 'PT'},
    {'name': 'Rodrigues - Fábrica Barcelos', 'city': 'Barcelos', 'country': 'PT'},
    {'name': 'P&R - Centro Braga', 'city': 'Braga', 'country': 'PT'},
]

def create_clients(conn):
    """Create clients for Pedrosa e Rodrigues"""
    cursor = conn.cursor()
    client_ids = []

    print(f"\n👥 Creating {len(CLIENTS_DATA)} clients...")

    for client_data in CLIENTS_DATA:
        client_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO clients (
                id, tenant_id, name, contact_email, contact_phone,
                address, country, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            client_id, TENANT_ID, client_data['name'], client_data['email'],
            client_data['phone'], client_data['address'], client_data['country'], True
        ))

        client_ids.append({'id': client_id, 'name': client_data['name']})
        print(f"  ✓ Created client: {client_data['name']}")

    conn.commit()
    print(f"✅ Successfully created {len(client_ids)} clients")
    return client_ids

def create_factories(conn):
    """Create factories for Pedrosa e Rodrigues"""
    cursor = conn.cursor()
    factory_ids = []

    print(f"\n🏭 Creating {len(FACTORIES_DATA)} factories...")

    for factory_data in FACTORIES_DATA:
        factory_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO factories (
                id, tenant_id, name, city, country, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            factory_id, TENANT_ID, factory_data['name'], factory_data['city'],
            factory_data['country'], datetime.now(), datetime.now()
        ))

        factory_ids.append({'id': factory_id, 'name': factory_data['name']})
        print(f"  ✓ Created factory: {factory_data['name']}")

    conn.commit()
    print(f"✅ Successfully created {len(factory_ids)} factories")
    return factory_ids

def create_lots(conn, clients, factories):
    """Create realistic lots for various clients"""
    cursor = conn.cursor()
    lot_ids = []

    garment_types = ['T_SHIRT', 'POLO_SHIRT', 'SWEATER', 'HOODIE', 'DRESS', 'PANTS', 'SHORTS', 'JACKET', 'BLOUSE']
    statuses = ['PLANNED', 'IN_PRODUCTION', 'INSPECTION', 'PENDING_APPROVAL', 'APPROVED', 'SHIPPED']

    print(f"\n📦 Creating lots...")

    # Create 3-5 lots per client
    lot_count = 0
    for client in clients:
        num_lots = random.randint(3, 5)

        for i in range(num_lots):
            lot_id = str(uuid.uuid4())
            factory = random.choice(factories)
            garment_type = random.choice(garment_types)
            status = random.choice(statuses)
            quantity = random.randint(1000, 8000)
            days_ago = random.randint(1, 90)
            created_at = datetime.now() - timedelta(days=days_ago)

            # Style ref based on client initial
            client_initial = ''.join([word[0] for word in client['name'].split()[:2]])
            style_ref = f"{client_initial}-{random.choice(['SS25', 'FW24'])}-{random.randint(100, 999)}"

            # Defect rate and progress based on status
            if status in ['APPROVED', 'SHIPPED']:
                defect_rate = round(random.uniform(0.5, 2.5), 2)
                inspected_progress = 100.0
            elif status in ['INSPECTION', 'PENDING_APPROVAL']:
                defect_rate = round(random.uniform(1.0, 5.0), 2)
                inspected_progress = random.uniform(60.0, 100.0)
            else:
                defect_rate = 0.0
                inspected_progress = random.uniform(0.0, 30.0) if status == 'IN_PRODUCTION' else 0.0

            # Material composition
            material = {
                "cotton": random.randint(60, 100),
                "polyester": random.randint(0, 40)
            }

            cursor.execute("""
                INSERT INTO lots (
                    id, tenant_id, factory_id, client_id, style_ref,
                    quantity_total, status, defect_rate, inspected_progress,
                    garment_type, material_composition,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                lot_id, TENANT_ID, factory['id'], client['id'], style_ref,
                quantity, status, defect_rate, inspected_progress,
                garment_type, str(material).replace("'", '"'),
                created_at, created_at
            ))

            lot_ids.append({
                'id': lot_id,
                'client_name': client['name'],
                'style_ref': style_ref,
                'status': status,
                'quantity': quantity,
                'created_at': created_at,
                'defect_rate': defect_rate
            })

            lot_count += 1

        print(f"  ✓ Created {num_lots} lots for {client['name']}")

    conn.commit()
    print(f"✅ Successfully created {lot_count} lots total")
    return lot_ids

def create_inspection_data(conn, lots):
    """Create inspection sessions, pieces, and defects"""
    cursor = conn.cursor()

    # Get an operator
    cursor.execute("""
        SELECT id FROM users WHERE tenant_id = %s LIMIT 1
    """, (TENANT_ID,))
    operator_result = cursor.fetchone()

    if not operator_result:
        # Use any operator if none in this tenant
        cursor.execute("SELECT id FROM users LIMIT 1")
        operator_result = cursor.fetchone()

    if not operator_result:
        print("⚠️  No users found, skipping inspection data")
        return

    operator_id = operator_result[0]

    print(f"\n🔍 Creating inspection sessions and pieces...")

    # Only create inspection data for inspected lots
    inspected_lots = [lot for lot in lots if lot['status'] in ['APPROVED', 'SHIPPED', 'INSPECTION', 'PENDING_APPROVAL']]

    total_sessions = 0
    total_pieces = 0
    total_defects = 0

    for lot in inspected_lots:
        # Create 1-2 inspection sessions per lot
        num_sessions = random.randint(1, 2)

        for _ in range(num_sessions):
            session_id = str(uuid.uuid4())

            pieces_inspected = random.randint(20, 50)
            pieces_defect = int(pieces_inspected * lot['defect_rate'] / 100)
            pieces_ok = pieces_inspected - pieces_defect

            cursor.execute("""
                INSERT INTO inspection_sessions (
                    id, lot_id, device_id, operator_id, started_at, ended_at,
                    pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id, lot['id'], DEVICE_ID, operator_id,
                lot['created_at'], lot['created_at'] if lot['status'] in ['APPROVED', 'SHIPPED'] else None,
                pieces_inspected, pieces_ok, pieces_defect, 0,
                lot['created_at'], lot['created_at']
            ))

            total_sessions += 1

            # Create apparel pieces
            for i in range(pieces_inspected):
                piece_id = str(uuid.uuid4())
                has_defect = i < pieces_defect

                cursor.execute("""
                    INSERT INTO apparel_pieces (
                        id, inspection_session_id, piece_number, status,
                        inspection_started_at, inspection_completed_at,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    piece_id, session_id, i + 1,
                    'defect' if has_defect else 'ok',
                    lot['created_at'], lot['created_at'],
                    lot['created_at'], lot['created_at']
                ))

                total_pieces += 1

                # Create defect record if needed
                if has_defect:
                    defect_id = str(uuid.uuid4())

                    cursor.execute("""
                        INSERT INTO piece_defects (
                            id, piece_id, status, audio_transcript, notes,
                            flagged_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        defect_id, piece_id, 'confirmed',
                        'Quality defect detected',
                        f'Defect found in piece {i+1} during inspection',
                        lot['created_at'], lot['created_at'], lot['created_at']
                    ))

                    total_defects += 1

    conn.commit()
    print(f"✅ Created {total_sessions} inspection sessions")
    print(f"✅ Created {total_pieces} apparel pieces")
    print(f"✅ Created {total_defects} defect records")

def create_users(conn, clients):
    """Create demo users for Pedrosa e Rodrigues tenant"""
    cursor = conn.cursor()

    # Check if there are roles
    cursor.execute("SELECT id, name FROM roles")
    roles = cursor.fetchall()

    if not roles:
        print("⚠️  No roles found, skipping user creation")
        return

    print(f"\n👤 Creating demo users...")

    users_data = [
        {'name': 'João Silva', 'email': 'joao.silva@pedrosa-rodrigues.pt', 'role': 'ADMIN'},
        {'name': 'Maria Santos', 'email': 'maria.santos@pedrosa-rodrigues.pt', 'role': 'OPS_MANAGER'},
        {'name': 'Carlos Mendes', 'email': 'carlos.mendes@pedrosa-rodrigues.pt', 'role': 'INSPECTOR'},
        {'name': 'Ana Costa', 'email': 'ana.costa@pedrosa-rodrigues.pt', 'role': 'OPERATOR'},
    ]

    role_map = {role[1]: role[0] for role in roles}
    created = 0

    for user_data in users_data:
        if user_data['role'] not in role_map:
            continue

        user_id = str(uuid.uuid4())

        try:
            cursor.execute("""
                INSERT INTO users (
                    id, tenant_id, name, email, is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, TENANT_ID, user_data['name'], user_data['email'],
                True, datetime.now(), datetime.now()
            ))

            # Assign role
            cursor.execute("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
            """, (user_id, role_map[user_data['role']]))

            created += 1
            print(f"  ✓ Created user: {user_data['name']} ({user_data['role']})")

        except Exception as e:
            print(f"  ⚠️  Could not create user {user_data['name']}: {e}")
            conn.rollback()

    if created > 0:
        conn.commit()
        print(f"✅ Successfully created {created} users")

def main():
    print("=" * 60)
    print("🏭 PEDROSA E RODRIGUES - COMPLETE TENANT SETUP")
    print("=" * 60)

    try:
        print("\n📡 Connecting to production database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully")

        # Create clients
        clients = create_clients(conn)

        # Create factories
        factories = create_factories(conn)

        # Create lots
        lots = create_lots(conn, clients, factories)

        # Create inspection data
        create_inspection_data(conn, lots)

        # Create users
        create_users(conn, clients)

        print("\n" + "=" * 60)
        print("✅ TENANT SETUP COMPLETE!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  • Tenant: Pedrosa e Rodrigues")
        print(f"  • Clients: {len(clients)}")
        print(f"  • Factories: {len(factories)}")
        print(f"  • Lots: {len(lots)}")
        print(f"  • Total Units: {sum(lot['quantity'] for lot in lots):,}")

        # Status breakdown
        status_count = {}
        for lot in lots:
            status = lot['status']
            status_count[status] = status_count.get(status, 0) + 1

        print(f"\n  Lots by Status:")
        for status, count in sorted(status_count.items()):
            print(f"    - {status}: {count}")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
