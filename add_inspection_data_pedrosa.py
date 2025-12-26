#!/usr/bin/env python3
"""
Add inspection sessions, pieces, defects and quality metrics for Pedrosa e Rodrigues
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

CLIENT_ID = '6ba295de-b309-45e6-acf5-5d63e9fe0439'  # Pedrosa e Rodrigues
DEVICE_ID = 'c344ce0e-27b7-4af4-899e-b4fad95398ad'  # wb1
OPERATOR_ID = '15b04d60-a2d9-46aa-a255-0b0df6f7046f'  # Operator user

def get_inspector(conn):
    """Get an inspector user"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'INSPECTOR'
        LIMIT 1
    """)
    result = cursor.fetchone()
    return result[0] if result else None

def create_inspection_sessions(conn, lots):
    """Create inspection sessions for lots"""
    cursor = conn.cursor()
    sessions = []

    print(f"\n🔍 Creating inspection sessions...")

    for lot in lots:
        lot_id, style_ref, status, created_at = lot

        # Only create sessions for lots that have been inspected
        if status in ['APPROVED', 'SHIPPED', 'INSPECTION', 'PENDING_APPROVAL', 'REJECTED']:
            session_id = str(uuid.uuid4())

            # Calculate pieces counts based on status
            pieces_inspected = random.randint(20, 50)
            pieces_defect = random.randint(0, int(pieces_inspected * 0.2))
            pieces_ok = pieces_inspected - pieces_defect

            cursor.execute("""
                INSERT INTO inspection_sessions (
                    id, lot_id, device_id, operator_id, started_at, ended_at,
                    pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                session_id, lot_id, DEVICE_ID, OPERATOR_ID,
                created_at, created_at if status in ['APPROVED', 'SHIPPED'] else None,
                pieces_inspected, pieces_ok, pieces_defect, 0,
                created_at, created_at
            ))

            sessions.append({
                'id': session_id,
                'lot_id': lot_id,
                'style_ref': style_ref,
                'status': status,
                'created_at': created_at
            })

            print(f"  ✓ Created inspection session for {style_ref}")

    conn.commit()
    print(f"✅ Successfully created {len(sessions)} inspection sessions")
    return sessions

def create_apparel_pieces_and_defects(conn, sessions):
    """Create apparel pieces and defects for inspection sessions"""
    cursor = conn.cursor()
    total_pieces = 0
    total_defects = 0

    print(f"\n👔 Creating apparel pieces and defects...")

    for session in sessions:
        # Create 10-30 pieces per session
        num_pieces = random.randint(10, 30)

        for i in range(num_pieces):
            piece_id = str(uuid.uuid4())
            has_defect = random.random() < 0.15  # 15% defect rate

            cursor.execute("""
                INSERT INTO apparel_pieces (
                    id, inspection_session_id, piece_number, status,
                    inspection_started_at, inspection_completed_at,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                piece_id, session['id'], i + 1,
                'defect' if has_defect else 'ok',
                session['created_at'], session['created_at'],
                session['created_at'], session['created_at']
            ))

            total_pieces += 1

            # Create defect if piece has defect
            if has_defect:
                defect_id = str(uuid.uuid4())

                cursor.execute("""
                    INSERT INTO piece_defects (
                        id, piece_id, status, audio_transcript, notes,
                        flagged_at, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    defect_id, piece_id, 'confirmed',
                    'Defect detected during quality inspection',
                    f'Quality issue found - piece {i+1}',
                    session['created_at'], session['created_at'], session['created_at']
                ))

                total_defects += 1

        print(f"  ✓ Created {num_pieces} pieces for {session['style_ref']} ({total_defects} defects so far)")

    conn.commit()
    print(f"✅ Successfully created {total_pieces} pieces with {total_defects} defects")

def update_lot_metrics(conn):
    """Update lot defect rates and inspected progress"""
    cursor = conn.cursor()

    print(f"\n📊 Updating lot metrics...")

    cursor.execute("""
        SELECT l.id, l.style_ref,
               COUNT(ap.id) as total_pieces,
               COUNT(CASE WHEN ap.status = 'defect' THEN 1 END) as defect_count
        FROM lots l
        JOIN inspection_sessions iss ON iss.lot_id = l.id
        JOIN apparel_pieces ap ON ap.inspection_session_id = iss.id
        WHERE l.client_id = %s
        GROUP BY l.id, l.style_ref
    """, (CLIENT_ID,))

    lots = cursor.fetchall()

    for lot_id, style_ref, total_pieces, defect_count in lots:
        defect_rate = (defect_count / total_pieces * 100) if total_pieces > 0 else 0
        inspected_progress = 100.0  # All pieces inspected

        cursor.execute("""
            UPDATE lots
            SET defect_rate = %s, inspected_progress = %s
            WHERE id = %s
        """, (round(defect_rate, 2), inspected_progress, lot_id))

        print(f"  ✓ Updated {style_ref}: {defect_rate:.2f}% defect rate ({defect_count}/{total_pieces})")

    conn.commit()
    print(f"✅ Successfully updated metrics for {len(lots)} lots")

def create_inspections(conn, lots, inspector_id):
    """Create formal inspections"""
    cursor = conn.cursor()

    print(f"\n🔎 Creating formal inspections...")

    inspection_count = 0

    for lot in lots:
        lot_id, style_ref, status, created_at = lot

        if status in ['APPROVED', 'SHIPPED', 'PENDING_APPROVAL', 'REJECTED']:
            inspection_id = str(uuid.uuid4())

            finished_at = created_at if status in ['APPROVED', 'SHIPPED'] else None

            cursor.execute("""
                INSERT INTO inspections (
                    id, lot_id, inspector_id, started_at, finished_at,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                inspection_id, lot_id, inspector_id, created_at, finished_at,
                created_at, created_at
            ))

            inspection_count += 1
            print(f"  ✓ Created inspection for {style_ref}")

    conn.commit()
    print(f"✅ Successfully created {inspection_count} formal inspections")

def main():
    print("=" * 60)
    print("🔍 PEDROSA E RODRIGUES - INSPECTION DATA SETUP")
    print("=" * 60)

    try:
        # Connect to database
        print("\n📡 Connecting to production database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully")

        # Get inspector
        inspector_id = get_inspector(conn)
        if not inspector_id:
            print("❌ No inspector found, cannot continue")
            return

        print(f"✅ Using inspector: {inspector_id}")

        # Get lots for Pedrosa e Rodrigues
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, style_ref, status, created_at
            FROM lots
            WHERE client_id = %s
            ORDER BY created_at DESC
        """, (CLIENT_ID,))

        lots = cursor.fetchall()
        print(f"✅ Found {len(lots)} lots for Pedrosa e Rodrigues")

        # Create inspection sessions
        sessions = create_inspection_sessions(conn, lots)

        # Create pieces and defects
        create_apparel_pieces_and_defects(conn, sessions)

        # Update lot metrics
        update_lot_metrics(conn)

        # Create formal inspections
        create_inspections(conn, lots, inspector_id)

        print("\n" + "=" * 60)
        print("✅ INSPECTION DATA SETUP COMPLETE!")
        print("=" * 60)

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
