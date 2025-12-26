#!/usr/bin/env python3
"""
Add quality inspection data and metrics to finished lots for Quality and Analytics tabs
"""

import psycopg2
import psycopg2.extras
import uuid
import random
from datetime import datetime, timedelta

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
print("Add Quality Metrics (Production)")
print("=" * 60)
print("")

# ============================================================================
# STEP 1: Get reference data
# ============================================================================
print("Step 1: Loading reference data...")
print("-" * 60)

# Get finished lots
cur.execute("""
    SELECT id, style_ref, quantity_total, tenant_id
    FROM lots
    WHERE status IN ('APPROVED', 'SHIPPED')
    ORDER BY created_at DESC
    LIMIT 50
""")
finished_lots = cur.fetchall()
print(f"Found {len(finished_lots)} finished lots")

# Get operators (INSPECTOR and OPERATOR roles)
cur.execute("""
    SELECT DISTINCT u.id, u.email, u.tenant_id
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE r.name IN ('INSPECTOR', 'OPERATOR')
    ORDER BY u.email
""")
operators = cur.fetchall()
print(f"Found {len(operators)} operators")

# Get edge devices
cur.execute("SELECT id, tenant_id FROM edge_devices")
devices = cur.fetchall()
print(f"Found {len(devices)} edge devices")

# If no devices, create some
if len(devices) == 0:
    print("Creating edge devices...")
    for i in range(5):
        device_id = str(uuid.uuid4())
        tenant_id = random.choice([lot['tenant_id'] for lot in finished_lots])

        cur.execute("""
            INSERT INTO edge_devices (
                id, tenant_id, device_name, serial_number, status,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'active', NOW(), NOW())
        """, (
            device_id,
            tenant_id,
            f"QC Station {i+1}",
            f"DEV-{random.randint(10000, 99999)}"
        ))

    conn.commit()

    # Reload devices
    cur.execute("SELECT id, tenant_id FROM edge_devices")
    devices = cur.fetchall()
    print(f"Created {len(devices)} edge devices")

# Get defect types
cur.execute("SELECT id, name, category FROM defect_types")
defect_types = cur.fetchall()
print(f"Found {len(defect_types)} defect types")

print("")

# ============================================================================
# STEP 2: Create inspection sessions for finished lots
# ============================================================================
print("Step 2: Creating inspection sessions...")
print("-" * 60)

sessions_created = 0

for lot in finished_lots:
    lot_id = lot['id']
    tenant_id = lot['tenant_id']

    # Get operators from same tenant
    tenant_operators = [op for op in operators if op['tenant_id'] == tenant_id]
    if not tenant_operators:
        tenant_operators = operators  # Fallback to any operator

    if not tenant_operators:
        continue

    # Get devices from same tenant
    tenant_devices = [dev for dev in devices if dev['tenant_id'] == tenant_id]
    if not tenant_devices:
        tenant_devices = devices  # Fallback to any device

    # Create 1-3 inspection sessions per lot
    num_sessions = random.randint(1, 3)

    for session_num in range(num_sessions):
        operator = random.choice(tenant_operators)
        device = random.choice(tenant_devices)

        # Session timing (in the past)
        days_ago = random.randint(10, 60)
        started_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(8, 16))
        duration_hours = random.uniform(2.0, 8.0)
        ended_at = started_at + timedelta(hours=duration_hours)

        # Calculate pieces for this session
        # Each session inspects a portion of the lot
        total_pieces = lot['quantity_total']
        pieces_in_session = random.randint(50, min(500, total_pieces // num_sessions))

        # Quality distribution (most pieces are OK)
        pieces_ok = int(pieces_in_session * random.uniform(0.85, 0.98))
        pieces_defect = int(pieces_in_session * random.uniform(0.01, 0.10))
        pieces_potential = pieces_in_session - pieces_ok - pieces_defect

        session_id = str(uuid.uuid4())

        try:
            cur.execute("""
                INSERT INTO inspection_sessions (
                    id, lot_id, device_id, operator_id,
                    started_at, ended_at,
                    pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                session_id, lot_id, device['id'], operator['id'],
                started_at, ended_at,
                pieces_in_session, pieces_ok, pieces_defect, pieces_potential
            ))

            if cur.fetchone():
                sessions_created += 1

                # Create apparel pieces for this session
                pieces_created = 0
                defects_created = 0

                for piece_num in range(1, pieces_in_session + 1):
                    piece_id = str(uuid.uuid4())

                    # Determine piece status based on distribution
                    if piece_num <= pieces_ok:
                        status = 'ok'
                    elif piece_num <= pieces_ok + pieces_defect:
                        status = 'defect'
                    else:
                        status = 'potential_defect'

                    inspection_started = started_at + timedelta(
                        seconds=(duration_hours * 3600 / pieces_in_session) * (piece_num - 1)
                    )
                    inspection_completed = inspection_started + timedelta(
                        seconds=random.uniform(10, 60)
                    )

                    try:
                        cur.execute("""
                            INSERT INTO apparel_pieces (
                                id, inspection_session_id, piece_number, status,
                                inspection_started_at, inspection_completed_at,
                                created_at, updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            piece_id, session_id, piece_num, status,
                            inspection_started, inspection_completed
                        ))

                        pieces_created += 1

                        # If piece has defect, create defect record
                        if status in ['defect', 'potential_defect']:
                            defect_id = str(uuid.uuid4())
                            defect_status = 'confirmed' if status == 'defect' else 'pending_review'

                            # Random defect transcript
                            defect_type = random.choice(defect_types)
                            transcripts = [
                                f"Small {defect_type['name'].lower()} detected on front panel",
                                f"Minor {defect_type['name'].lower()} found near seam",
                                f"{defect_type['name']} observed on sleeve area",
                                f"Possible {defect_type['name'].lower()} requires review",
                                f"{defect_type['name']} detected during visual inspection",
                            ]

                            flagged_at = inspection_completed
                            reviewed_at = None
                            reviewed_by = None

                            if defect_status == 'confirmed':
                                reviewed_at = flagged_at + timedelta(minutes=random.randint(5, 30))
                                reviewed_by = operator['id']

                            cur.execute("""
                                INSERT INTO piece_defects (
                                    id, piece_id, status, audio_transcript,
                                    flagged_at, reviewed_by, reviewed_at,
                                    created_at, updated_at
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                            """, (
                                defect_id, piece_id, defect_status,
                                random.choice(transcripts),
                                flagged_at, reviewed_by, reviewed_at
                            ))

                            defects_created += 1

                    except Exception as e:
                        print(f"  ✗ Error creating piece {piece_num}: {e}")
                        conn.rollback()
                        continue

                if session_num == 0:  # Print only for first session of each lot
                    print(f"  ✓ {lot['style_ref']}: {num_sessions} session(s), {pieces_created} pieces, {defects_created} defects")

        except Exception as e:
            print(f"  ✗ Error creating session for {lot['style_ref']}: {e}")
            conn.rollback()
            continue

conn.commit()
print(f"\nCreated {sessions_created} inspection sessions")
print("")

# ============================================================================
# STEP 3: Add inspection summary stats to lots
# ============================================================================
print("Step 3: Calculating quality metrics...")
print("-" * 60)

# Calculate defect rates and update lot stats
cur.execute("""
    SELECT
        l.id as lot_id,
        l.style_ref,
        COUNT(DISTINCT iss.id) as session_count,
        COALESCE(SUM(iss.pieces_inspected), 0) as total_inspected,
        COALESCE(SUM(iss.pieces_ok), 0) as total_ok,
        COALESCE(SUM(iss.pieces_defect), 0) as total_defect,
        COALESCE(SUM(iss.pieces_potential_defect), 0) as total_potential,
        CASE
            WHEN SUM(iss.pieces_inspected) > 0
            THEN ROUND((SUM(iss.pieces_defect)::numeric / SUM(iss.pieces_inspected)::numeric * 100), 2)
            ELSE 0
        END as defect_rate
    FROM lots l
    LEFT JOIN inspection_sessions iss ON l.id = iss.lot_id
    WHERE l.status IN ('APPROVED', 'SHIPPED')
    GROUP BY l.id, l.style_ref
    HAVING COUNT(DISTINCT iss.id) > 0
    ORDER BY l.style_ref
""")

quality_stats = cur.fetchall()

print(f"Quality metrics summary:")
print(f"{'Style Ref':<20} {'Inspected':<10} {'OK':<10} {'Defect':<10} {'Rate %':<10}")
print("-" * 60)

for stat in quality_stats[:15]:  # Show first 15
    print(f"{stat['style_ref']:<20} {stat['total_inspected']:<10} {stat['total_ok']:<10} {stat['total_defect']:<10} {stat['defect_rate']:<10}%")

print(f"\n... and {len(quality_stats) - 15} more lots with quality data" if len(quality_stats) > 15 else "")
print("")

# ============================================================================
# STEP 4: Summary statistics
# ============================================================================
print("Step 4: Overall Statistics...")
print("-" * 60)

# Total pieces inspected
cur.execute("""
    SELECT
        COUNT(DISTINCT iss.id) as total_sessions,
        COALESCE(SUM(iss.pieces_inspected), 0) as total_pieces,
        COALESCE(SUM(iss.pieces_ok), 0) as total_ok,
        COALESCE(SUM(iss.pieces_defect), 0) as total_defect,
        COALESCE(SUM(iss.pieces_potential_defect), 0) as total_potential
    FROM inspection_sessions iss
""")
overall_stats = cur.fetchone()

if overall_stats['total_pieces'] > 0:
    defect_rate = (overall_stats['total_defect'] / overall_stats['total_pieces']) * 100
    ok_rate = (overall_stats['total_ok'] / overall_stats['total_pieces']) * 100
else:
    defect_rate = 0
    ok_rate = 0

print(f"Overall Quality Metrics:")
print(f"  • Total inspection sessions: {overall_stats['total_sessions']}")
print(f"  • Total pieces inspected: {overall_stats['total_pieces']}")
print(f"  • Pieces OK: {overall_stats['total_ok']} ({ok_rate:.2f}%)")
print(f"  • Pieces with defects: {overall_stats['total_defect']} ({defect_rate:.2f}%)")
print(f"  • Pieces pending review: {overall_stats['total_potential']}")

print("")

# Defect breakdown
cur.execute("""
    SELECT COUNT(*) as total_defects
    FROM piece_defects
""")
defect_count = cur.fetchone()['total_defects']

cur.execute("""
    SELECT status, COUNT(*) as count
    FROM piece_defects
    GROUP BY status
    ORDER BY status
""")
defect_status_breakdown = cur.fetchall()

print(f"Defect Records:")
print(f"  • Total defect records: {defect_count}")
for stat in defect_status_breakdown:
    print(f"  • {stat['status']}: {stat['count']}")

print("")

print("=" * 60)
print("✓ Quality Metrics Addition Complete!")
print("=" * 60)
print(f"Summary:")
print(f"  - {sessions_created} inspection sessions created")
print(f"  - {overall_stats['total_pieces']} pieces inspected")
print(f"  - {defect_count} defect records")
print(f"  - {len(quality_stats)} lots with quality metrics")
print(f"  - Overall defect rate: {defect_rate:.2f}%")
print(f"  - Overall pass rate: {ok_rate:.2f}%")
print("")

cur.close()
conn.close()
