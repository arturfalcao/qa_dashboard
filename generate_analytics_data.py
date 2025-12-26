#!/usr/bin/env python3
"""
Generate realistic analytics data for Cordeiro Campos demo
Creates inspection sessions, pieces, defects, and approvals for the last 30 days
"""

import psycopg2
from datetime import datetime, timedelta
import uuid
import random

# Database Configuration
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

TENANT_ID = '254226e3-a316-413e-aa05-d0dd47c8f855'
# Lot to exclude from modifications
EXCLUDE_LOT_ID = '0ac8675e-414c-42cb-afd4-8139dd229f40'

# Defect types for realistic data
DEFECT_TRANSCRIPTS = [
    "Hole found on left sleeve near cuff area",
    "Stitching defect on collar seam",
    "Color inconsistency on front panel",
    "Thread loose on right shoulder",
    "Small stain near bottom hem",
    "Button misaligned on front placket",
    "Fabric pilling on back panel",
    "Seam not straight on side panel",
    "Label sewn crooked",
    "Minor tear on pocket edge",
]

def main():
    print("=" * 60)
    print("🔧 GENERATING ANALYTICS DATA FOR CORDEIRO CAMPOS")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ Connected to database")

        # Get lots (excluding the protected one)
        cursor.execute("""
            SELECT DISTINCT ON (style_ref) id, style_ref, quantity_total, status, garment_type
            FROM lots
            WHERE tenant_id = %s AND id != %s
            ORDER BY style_ref, created_at DESC
        """, (TENANT_ID, EXCLUDE_LOT_ID))
        lots = cursor.fetchall()

        if not lots:
            print("❌ No lots found for Cordeiro Campos")
            return

        print(f"📦 Found {len(lots)} unique lots to process")

        # Get edge device
        cursor.execute("SELECT id FROM edge_devices WHERE tenant_id = %s LIMIT 1", (TENANT_ID,))
        device = cursor.fetchone()
        if not device:
            device_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO edge_devices (id, tenant_id, name, secret_key, workbench_number, status, created_at, updated_at)
                VALUES (%s, %s, 'Workbench Analytics', %s, 2, 'active', NOW(), NOW())
            """, (device_id, TENANT_ID, f'secret-{uuid.uuid4()}'))
            conn.commit()
            print(f"✅ Created edge device: {device_id}")
        else:
            device_id = device[0]
            print(f"✅ Using existing edge device")

        # Get operators (inspectors)
        cursor.execute("""
            SELECT id, email FROM users WHERE tenant_id = %s
        """, (TENANT_ID,))
        operators = cursor.fetchall()
        operator_ids = [op[0] for op in operators]
        print(f"👥 Found {len(operator_ids)} operators")

        # Get admin user for approvals
        cursor.execute("""
            SELECT id FROM users WHERE tenant_id = %s AND email LIKE %s LIMIT 1
        """, (TENANT_ID, '%admin%'))
        admin = cursor.fetchone()
        admin_id = admin[0] if admin else operator_ids[0]

        # Generate data for the last 30 days
        now = datetime.now()
        total_sessions = 0
        total_pieces = 0
        total_defects = 0
        total_approvals = 0

        print("\n📊 Generating inspection data...")

        for lot_id, style_ref, quantity_total, status, garment_type in lots:
            # Check if this lot already has inspection sessions (other than our excluded lot)
            cursor.execute("""
                SELECT COUNT(*) FROM inspection_sessions WHERE lot_id = %s
            """, (lot_id,))
            existing_sessions = cursor.fetchone()[0]

            if existing_sessions > 0:
                print(f"  ⏭️  {style_ref}: Already has {existing_sessions} sessions, skipping")
                continue

            # Determine how many sessions to create based on status
            if status == 'SHIPPED':
                num_sessions = random.randint(8, 15)  # Completed lots have more sessions
                days_spread = random.randint(20, 30)
            elif status == 'APPROVED':
                num_sessions = random.randint(6, 12)
                days_spread = random.randint(15, 25)
            elif status == 'PENDING_APPROVAL':
                num_sessions = random.randint(4, 8)
                days_spread = random.randint(10, 20)
            elif status == 'INSPECTION':
                num_sessions = random.randint(2, 5)
                days_spread = random.randint(5, 15)
            else:
                num_sessions = random.randint(1, 3)
                days_spread = random.randint(3, 10)

            pieces_per_session = quantity_total // (num_sessions * 2)  # Partial inspection

            print(f"  📝 {style_ref} ({status}): Creating {num_sessions} sessions...")

            for session_idx in range(num_sessions):
                session_id = str(uuid.uuid4())
                operator_id = random.choice(operator_ids)

                # Random date within the spread period
                days_ago = random.randint(1, days_spread)
                session_date = now - timedelta(days=days_ago, hours=random.randint(8, 17), minutes=random.randint(0, 59))
                session_end = session_date + timedelta(hours=random.randint(1, 4), minutes=random.randint(0, 59))

                # Pieces for this session
                pieces_in_session = random.randint(int(pieces_per_session * 0.8), int(pieces_per_session * 1.2))
                pieces_in_session = max(20, min(pieces_in_session, 200))  # Between 20-200 pieces

                # Defect rate varies by style (some styles have more issues)
                base_defect_rate = random.uniform(0.005, 0.03)  # 0.5% to 3%
                num_defects = int(pieces_in_session * base_defect_rate)
                num_potential = int(pieces_in_session * base_defect_rate * 0.5)
                num_ok = pieces_in_session - num_defects - num_potential

                # Create inspection session
                cursor.execute("""
                    INSERT INTO inspection_sessions
                    (id, lot_id, device_id, operator_id, started_at, ended_at,
                     pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, lot_id, device_id, operator_id, session_date, session_end,
                      pieces_in_session, num_ok, num_defects, num_potential, session_date, session_date))

                total_sessions += 1

                # Create apparel pieces
                for piece_num in range(1, pieces_in_session + 1):
                    piece_id = str(uuid.uuid4())

                    if piece_num <= num_defects:
                        piece_status = 'defect'
                    elif piece_num <= num_defects + num_potential:
                        piece_status = 'potential_defect'
                    else:
                        piece_status = 'ok'

                    piece_start = session_date + timedelta(minutes=piece_num * 2)
                    piece_end = piece_start + timedelta(seconds=random.randint(30, 120))

                    cursor.execute("""
                        INSERT INTO apparel_pieces
                        (id, inspection_session_id, piece_number, status,
                         inspection_started_at, inspection_completed_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (piece_id, session_id, piece_num, piece_status, piece_start, piece_end, piece_start, piece_start))

                    total_pieces += 1

                    # Create piece_defect records for defective pieces
                    if piece_status in ('defect', 'potential_defect'):
                        defect_id = str(uuid.uuid4())

                        # Determine defect status
                        if piece_status == 'defect':
                            defect_status = 'confirmed'
                            reviewed_by = admin_id
                            reviewed_at = piece_end + timedelta(hours=random.randint(1, 24))
                        else:
                            # Some potential defects confirmed, some rejected, some pending
                            rand = random.random()
                            if rand < 0.4:
                                defect_status = 'confirmed'
                                reviewed_by = admin_id
                                reviewed_at = piece_end + timedelta(hours=random.randint(1, 24))
                            elif rand < 0.7:
                                defect_status = 'rejected'
                                reviewed_by = admin_id
                                reviewed_at = piece_end + timedelta(hours=random.randint(1, 24))
                            else:
                                defect_status = 'pending_review'
                                reviewed_by = None
                                reviewed_at = None

                        transcript = random.choice(DEFECT_TRANSCRIPTS)

                        cursor.execute("""
                            INSERT INTO piece_defects
                            (id, piece_id, status, audio_transcript, flagged_at,
                             reviewed_by, reviewed_at, notes, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (defect_id, piece_id, defect_status, transcript, piece_end,
                              reviewed_by, reviewed_at,
                              'Auto-flagged by AI inspection' if defect_status == 'pending_review' else None,
                              piece_end, piece_end))

                        total_defects += 1

            conn.commit()

            # Create approval for APPROVED and SHIPPED lots
            if status in ('APPROVED', 'SHIPPED', 'PENDING_APPROVAL'):
                cursor.execute("SELECT id FROM approvals WHERE lot_id = %s", (lot_id,))
                if not cursor.fetchone():
                    approval_id = str(uuid.uuid4())

                    # Get lot creation date
                    cursor.execute("SELECT created_at FROM lots WHERE id = %s", (lot_id,))
                    lot_created = cursor.fetchone()[0]

                    # Approval happens 1-5 days after lot creation
                    if status == 'PENDING_APPROVAL':
                        # Skip pending approvals - they don't have decisions yet
                        continue
                    else:
                        decision = 'APPROVE'
                        decided_at = lot_created + timedelta(days=random.randint(1, 5), hours=random.randint(8, 17))

                    cursor.execute("""
                        INSERT INTO approvals (id, lot_id, approved_by, decision, decided_at, note, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (approval_id, lot_id, admin_id, decision, decided_at,
                          'Quality standards met. Approved for shipment.',
                          decided_at, decided_at))

                    total_approvals += 1
                    conn.commit()

        # Update lot defect_rate and inspected_progress based on inspection data
        print("\n📈 Updating lot statistics...")
        cursor.execute("""
            UPDATE lots l SET
                defect_rate = COALESCE((
                    SELECT ROUND((SUM(pieces_defect)::numeric / NULLIF(SUM(pieces_inspected), 0) * 100), 2)
                    FROM inspection_sessions WHERE lot_id = l.id
                ), 0),
                inspected_progress = COALESCE((
                    SELECT ROUND((SUM(pieces_inspected)::numeric / l.quantity_total * 100), 2)
                    FROM inspection_sessions WHERE lot_id = l.id
                ), 0),
                updated_at = NOW()
            WHERE tenant_id = %s AND id != %s
        """, (TENANT_ID, EXCLUDE_LOT_ID))
        conn.commit()

        print()
        print("=" * 60)
        print("📊 ANALYTICS DATA SUMMARY")
        print("=" * 60)
        print(f"  ✅ Inspection Sessions: {total_sessions}")
        print(f"  ✅ Apparel Pieces: {total_pieces}")
        print(f"  ✅ Piece Defects: {total_defects}")
        print(f"  ✅ Approvals: {total_approvals}")
        print()
        print("🎉 Done! Check the Analytics and Quality tabs at:")
        print("   https://app.packpolish.com/c/cordeiro-campos/analytics")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
