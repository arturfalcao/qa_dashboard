#!/usr/bin/env python3
"""
Setup demo data for Pedrosa e Rodrigues client in production database
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

# Constants
CLIENT_ID = '6ba295de-b309-45e6-acf5-5d63e9fe0439'  # Pedrosa e Rodrigues
TENANT_ID = '6f16b1f3-6cd8-4b1b-a4f4-17c4a9d7c6c0'

# Portuguese factories
FACTORIES = [
    'c3747d35-003c-48e7-9bf3-9f5a65159be0',  # Vale do Ave Fibre Hub
    '65b5586f-22aa-49b4-9f6a-ad6cfcd7bbb9',  # Braga Cutting & Assembly
    'fcb418a6-fe9d-4f42-8407-e1412a957f8f',  # Vizela Laundry & Finishing
    '996017ef-31c1-4f2c-adfe-3c18e9ef6874',  # Porto Atelier & QA Lab
]

# Realistic lot data for a Portuguese textile company
LOTS_DATA = [
    {
        'style_ref': 'PR-SS25-001',
        'garment_type': 'T_SHIRT',
        'quantity': 5000,
        'status': 'APPROVED',
        'defect_rate': 0.8,
        'inspected_progress': 100.0,
        'days_ago': 45
    },
    {
        'style_ref': 'PR-SS25-002',
        'garment_type': 'POLO_SHIRT',
        'quantity': 3500,
        'status': 'SHIPPED',
        'defect_rate': 0.5,
        'inspected_progress': 100.0,
        'days_ago': 30
    },
    {
        'style_ref': 'PR-FW24-015',
        'garment_type': 'SWEATER',
        'quantity': 2000,
        'status': 'APPROVED',
        'defect_rate': 1.2,
        'inspected_progress': 100.0,
        'days_ago': 60
    },
    {
        'style_ref': 'PR-SS25-003',
        'garment_type': 'SHORTS',
        'quantity': 4200,
        'status': 'INSPECTION',
        'defect_rate': 1.5,
        'inspected_progress': 75.0,
        'days_ago': 5
    },
    {
        'style_ref': 'PR-SS25-004',
        'garment_type': 'DRESS',
        'quantity': 1800,
        'status': 'PENDING_APPROVAL',
        'defect_rate': 2.1,
        'inspected_progress': 100.0,
        'days_ago': 2
    },
    {
        'style_ref': 'PR-SS25-005',
        'garment_type': 'JACKET',
        'quantity': 1500,
        'status': 'IN_PRODUCTION',
        'defect_rate': 0.0,
        'inspected_progress': 0.0,
        'days_ago': 1
    },
    {
        'style_ref': 'PR-FW24-012',
        'garment_type': 'PANTS',
        'quantity': 3200,
        'status': 'SHIPPED',
        'defect_rate': 0.9,
        'inspected_progress': 100.0,
        'days_ago': 50
    },
    {
        'style_ref': 'PR-SS25-006',
        'garment_type': 'BLOUSE',
        'quantity': 2500,
        'status': 'APPROVED',
        'defect_rate': 1.1,
        'inspected_progress': 100.0,
        'days_ago': 20
    },
]

def create_lots(conn):
    """Create realistic lots for Pedrosa e Rodrigues"""
    cursor = conn.cursor()
    lot_ids = []

    print(f"\n📦 Creating {len(LOTS_DATA)} lots for Pedrosa e Rodrigues...")

    for lot_data in LOTS_DATA:
        lot_id = str(uuid.uuid4())
        factory_id = random.choice(FACTORIES)
        created_at = datetime.now() - timedelta(days=lot_data['days_ago'])

        # Material composition
        material_composition = {
            "cotton": random.randint(60, 100),
            "polyester": random.randint(0, 40)
        }

        # Size specifications
        size_specs = {
            "sizes": ["XS", "S", "M", "L", "XL"],
            "measurements": {
                "chest_width": {"XS": 45, "S": 48, "M": 51, "L": 54, "XL": 57},
                "body_length": {"XS": 66, "S": 68, "M": 70, "L": 72, "XL": 74}
            }
        }

        cursor.execute("""
            INSERT INTO lots (
                id, tenant_id, factory_id, client_id, style_ref,
                quantity_total, status, defect_rate, inspected_progress,
                garment_type, material_composition, size_specifications,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            lot_id, TENANT_ID, factory_id, CLIENT_ID, lot_data['style_ref'],
            lot_data['quantity'], lot_data['status'], lot_data['defect_rate'],
            lot_data['inspected_progress'], lot_data['garment_type'],
            str(material_composition).replace("'", '"'),
            str(size_specs).replace("'", '"'),
            created_at, created_at
        ))

        lot_ids.append({
            'id': lot_id,
            'style_ref': lot_data['style_ref'],
            'status': lot_data['status'],
            'quantity': lot_data['quantity'],
            'created_at': created_at
        })

        print(f"  ✓ Created lot {lot_data['style_ref']} - {lot_data['status']} ({lot_data['quantity']} units)")

    conn.commit()
    print(f"✅ Successfully created {len(lot_ids)} lots")
    return lot_ids

def create_apparel_pieces(conn, lot_ids):
    """Create apparel pieces for the lots"""
    cursor = conn.cursor()
    total_pieces = 0

    print(f"\n👔 Creating apparel pieces for lots...")

    for lot in lot_ids:
        # Create a sample of pieces (not all, just a representative sample)
        sample_size = min(lot['quantity'], 50)

        for i in range(sample_size):
            piece_id = str(uuid.uuid4())
            size = random.choice(['XS', 'S', 'M', 'L', 'XL'])

            cursor.execute("""
                INSERT INTO apparel_pieces (
                    id, lot_id, size, barcode, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                piece_id, lot['id'], size,
                f"PR-{lot['style_ref']}-{i+1:05d}",
                'INSPECTED', lot['created_at'], lot['created_at']
            ))

            total_pieces += 1

        print(f"  ✓ Created {sample_size} pieces for lot {lot['style_ref']}")

    conn.commit()
    print(f"✅ Successfully created {total_pieces} apparel pieces")

def create_inspections(conn, lot_ids):
    """Create inspections for lots that need them"""
    cursor = conn.cursor()

    # Get an inspector user
    cursor.execute("""
        SELECT u.id FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'INSPECTOR'
        LIMIT 1
    """)
    inspector = cursor.fetchone()

    if not inspector:
        print("⚠️ No inspector user found, skipping inspections")
        return []

    inspector_id = inspector[0]
    inspection_ids = []

    print(f"\n🔍 Creating inspections...")

    # Create inspections for lots that have been inspected
    inspected_lots = [lot for lot in lot_ids if lot['status'] in ['APPROVED', 'SHIPPED', 'INSPECTION', 'PENDING_APPROVAL', 'REJECTED']]

    for lot in inspected_lots:
        inspection_id = str(uuid.uuid4())

        # Inspection results based on defect rate
        cursor.execute("SELECT defect_rate FROM lots WHERE id = %s", (lot['id'],))
        defect_rate = cursor.fetchone()[0]

        sample_size = min(lot['quantity'], 200)
        defects_found = int(sample_size * float(defect_rate) / 100)

        cursor.execute("""
            INSERT INTO inspections (
                id, lot_id, inspector_id, inspection_date,
                sample_size, defects_found, aql_level, result,
                notes, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            inspection_id, lot['id'], inspector_id, lot['created_at'],
            sample_size, defects_found, '2.5',
            'PASS' if defect_rate < 2.5 else 'FAIL',
            f'AQL 2.5 inspection - {defects_found} defects found in {sample_size} pieces sample',
            lot['created_at'], lot['created_at']
        ))

        inspection_ids.append(inspection_id)
        print(f"  ✓ Created inspection for {lot['style_ref']} - {defects_found} defects in {sample_size} pieces")

    conn.commit()
    print(f"✅ Successfully created {len(inspection_ids)} inspections")
    return inspection_ids

def create_defects(conn, lot_ids):
    """Create realistic defects for the lots"""
    cursor = conn.cursor()

    # Common defect types
    defect_types = [
        'STITCHING_DEFECT',
        'FABRIC_DEFECT',
        'COLOR_VARIATION',
        'SIZING_ISSUE',
        'LOOSE_THREAD',
        'HOLE_TEAR',
        'STAIN_MARK'
    ]

    print(f"\n⚠️ Creating defects...")

    total_defects = 0

    # Get some pieces to add defects
    for lot in lot_ids:
        cursor.execute("SELECT defect_rate FROM lots WHERE id = %s", (lot['id'],))
        defect_rate = cursor.fetchone()[0]

        if float(defect_rate) > 0:
            # Get some pieces from this lot
            cursor.execute("""
                SELECT id FROM apparel_pieces
                WHERE lot_id = %s
                LIMIT 10
            """, (lot['id'],))

            pieces = cursor.fetchall()

            num_defects = min(len(pieces), int(len(pieces) * float(defect_rate) / 100) + 1)

            for i in range(num_defects):
                if i < len(pieces):
                    defect_id = str(uuid.uuid4())
                    defect_type = random.choice(defect_types)
                    severity = random.choice(['MINOR', 'MAJOR', 'CRITICAL'])

                    cursor.execute("""
                        INSERT INTO piece_defects (
                            id, piece_id, defect_type, severity, description,
                            detected_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        defect_id, pieces[i][0], defect_type, severity,
                        f'{defect_type.replace("_", " ").title()} detected during inspection',
                        lot['created_at'], lot['created_at'], lot['created_at']
                    ))

                    total_defects += 1

    conn.commit()
    print(f"✅ Successfully created {total_defects} defects")

def main():
    print("=" * 60)
    print("🏭 PEDROSA E RODRIGUES - DEMO DATA SETUP")
    print("=" * 60)

    try:
        # Connect to database
        print("\n📡 Connecting to production database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully")

        # Create lots
        lot_ids = create_lots(conn)

        # Create apparel pieces
        create_apparel_pieces(conn, lot_ids)

        # Create inspections
        create_inspections(conn, lot_ids)

        # Create defects
        create_defects(conn, lot_ids)

        print("\n" + "=" * 60)
        print("✅ DEMO SETUP COMPLETE!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  • Client: Pedrosa e Rodrigues")
        print(f"  • Lots created: {len(lot_ids)}")
        print(f"  • Total quantity: {sum(lot['quantity'] for lot in lot_ids):,} units")
        print(f"  • Inspections created")
        print(f"  • Defects added")
        print(f"  • Status distribution:")

        status_count = {}
        for lot in lot_ids:
            status = lot['status']
            status_count[status] = status_count.get(status, 0) + 1

        for status, count in sorted(status_count.items()):
            print(f"    - {status}: {count} lots")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
