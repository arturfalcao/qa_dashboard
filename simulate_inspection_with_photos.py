#!/usr/bin/env python3
"""
Simulate real inspection session with photos upload
Simulates inspecting pieces on workbench, taking 2 photos per piece
"""

import psycopg2
import uuid
import shutil
import os
from datetime import datetime
from pathlib import Path

# Production database connection
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

# Configuration
LOT_ID = 'adb002da-571a-43e6-832d-75c9802aaa44'  # ZP-SS25-318 - Zara Portugal Dress
TENANT_ID = '1ad2510c-3503-4393-a643-1be7f94804ba'
DEVICE_ID = 'c344ce0e-27b7-4af4-899e-b4fad95398ad'
NUM_PIECES_TO_INSPECT = 10  # Simulate inspecting 10 pieces

# Photo sources (img2.jpg and img3.jpg will be used alternately)
PHOTO_DIR = Path('/home/celso/projects/qa_dashboard/ai_withllm')
PHOTO1 = PHOTO_DIR / 'img2.jpg'
PHOTO2 = PHOTO_DIR / 'img3.jpg'

# S3/Storage simulation - using local path for now
# In production this would upload to MinIO/S3
STORAGE_BASE = '/tmp/qa_inspection_photos'

def setup_storage():
    """Create storage directory"""
    storage_path = Path(STORAGE_BASE)
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path

def get_operator(conn):
    """Get operator for this tenant"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM users
        WHERE tenant_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (TENANT_ID,))

    result = cursor.fetchone()
    if not result:
        # Use any operator
        cursor.execute("SELECT id FROM users LIMIT 1")
        result = cursor.fetchone()

    return result[0] if result else None

def create_inspection_session(conn, operator_id):
    """Create a new inspection session"""
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    now = datetime.now()

    print(f"\n🔍 Creating inspection session...")

    cursor.execute("""
        INSERT INTO inspection_sessions (
            id, lot_id, device_id, operator_id, started_at,
            pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        session_id, LOT_ID, DEVICE_ID, operator_id, now,
        0, 0, 0, 0,  # Will be updated as we inspect
        now, now
    ))

    conn.commit()
    print(f"✅ Inspection session created: {session_id}")

    return session_id

def copy_photo_to_storage(source_photo, piece_number, photo_number, storage_path):
    """Copy photo to storage and return path"""
    # Create filename like: piece_001_photo_1_timestamp.jpg
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"piece_{piece_number:03d}_photo_{photo_number}_{timestamp}.jpg"

    dest_path = storage_path / filename
    shutil.copy2(source_photo, dest_path)

    # Return relative path that would be used in S3
    # In production: s3://bucket-name/inspections/LOT_ID/piece_XXX_photo_X.jpg
    s3_path = f"inspections/{LOT_ID}/{filename}"

    return str(dest_path), s3_path

def inspect_piece(conn, session_id, piece_number, storage_path, has_defect=False):
    """Simulate inspecting a single piece with 2 photos"""
    cursor = conn.cursor()
    piece_id = str(uuid.uuid4())
    now = datetime.now()

    # Create apparel piece
    cursor.execute("""
        INSERT INTO apparel_pieces (
            id, inspection_session_id, piece_number, status,
            inspection_started_at, inspection_completed_at,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        piece_id, session_id, piece_number,
        'defect' if has_defect else 'ok',
        now, now, now, now
    ))

    # Take 2 photos per piece
    photo1_local, photo1_s3 = copy_photo_to_storage(PHOTO1, piece_number, 1, storage_path)
    photo2_local, photo2_s3 = copy_photo_to_storage(PHOTO2, piece_number, 2, storage_path)

    # Save photo 1
    photo1_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO piece_photos (
            id, piece_id, file_path, s3_url, captured_at, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (photo1_id, piece_id, photo1_local, photo1_s3, now, now))

    # Save photo 2
    photo2_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO piece_photos (
            id, piece_id, file_path, s3_url, captured_at, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (photo2_id, piece_id, photo2_local, photo2_s3, now, now))

    # If piece has defect, create defect record
    if has_defect:
        defect_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO piece_defects (
                id, piece_id, status, audio_transcript, notes,
                flagged_at, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            defect_id, piece_id, 'confirmed',
            'Defect detected during visual inspection',
            f'Quality issue found on piece {piece_number}',
            now, now, now
        ))

    conn.commit()

    status_icon = '❌' if has_defect else '✅'
    print(f"  {status_icon} Piece #{piece_number:03d} - {2} photos captured - Status: {'DEFECT' if has_defect else 'OK'}")

    return piece_id

def update_session_stats(conn, session_id, pieces_inspected, pieces_ok, pieces_defect):
    """Update inspection session statistics"""
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE inspection_sessions
        SET pieces_inspected = %s,
            pieces_ok = %s,
            pieces_defect = %s,
            updated_at = %s
        WHERE id = %s
    """, (pieces_inspected, pieces_ok, pieces_defect, datetime.now(), session_id))

    conn.commit()

def update_lot_metrics(conn):
    """Update lot defect rate and progress"""
    cursor = conn.cursor()

    # Calculate metrics from all pieces in all sessions for this lot
    cursor.execute("""
        SELECT
            COUNT(ap.id) as total_pieces,
            COUNT(CASE WHEN ap.status = 'defect' THEN 1 END) as defect_pieces
        FROM inspection_sessions iss
        JOIN apparel_pieces ap ON ap.inspection_session_id = iss.id
        WHERE iss.lot_id = %s
    """, (LOT_ID,))

    total, defects = cursor.fetchone()

    if total > 0:
        defect_rate = (defects / total * 100)

        cursor.execute("""
            UPDATE lots
            SET defect_rate = %s,
                inspected_progress = %s,
                updated_at = %s
            WHERE id = %s
        """, (round(defect_rate, 2), 100.0, datetime.now(), LOT_ID))

        conn.commit()

        print(f"\n📊 Lot metrics updated:")
        print(f"   Total pieces inspected: {total}")
        print(f"   Defects found: {defects}")
        print(f"   Defect rate: {defect_rate:.2f}%")

def main():
    print("=" * 60)
    print("📸 SIMULATION: WORKBENCH INSPECTION WITH PHOTOS")
    print("=" * 60)
    print(f"\nLot: ZP-SS25-318 (Zara Portugal - Dress)")
    print(f"Photos per piece: 2 (img2.jpg, img3.jpg)")
    print(f"Pieces to inspect: {NUM_PIECES_TO_INSPECT}")
    print()

    try:
        # Setup
        print("🔧 Setting up...")
        storage_path = setup_storage()
        print(f"✅ Storage directory: {storage_path}")

        # Check photos exist
        if not PHOTO1.exists() or not PHOTO2.exists():
            print(f"❌ Error: Photos not found!")
            print(f"   Expected: {PHOTO1}")
            print(f"   Expected: {PHOTO2}")
            return

        print(f"✅ Source photos found")

        # Connect to database
        print("\n📡 Connecting to production database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected")

        # Get operator
        operator_id = get_operator(conn)
        if not operator_id:
            print("❌ No operator found")
            return
        print(f"✅ Operator ID: {operator_id}")

        # Create inspection session
        session_id = create_inspection_session(conn, operator_id)

        # Inspect pieces
        print(f"\n👔 Inspecting {NUM_PIECES_TO_INSPECT} pieces...")
        print(f"{'='*60}")

        pieces_ok = 0
        pieces_defect = 0

        for i in range(1, NUM_PIECES_TO_INSPECT + 1):
            # Simulate: 20% chance of defect
            has_defect = (i % 5 == 0)  # Every 5th piece has a defect

            inspect_piece(conn, session_id, i, storage_path, has_defect)

            if has_defect:
                pieces_defect += 1
            else:
                pieces_ok += 1

        print(f"{'='*60}")

        # Update session statistics
        print(f"\n📊 Updating session statistics...")
        update_session_stats(conn, session_id, NUM_PIECES_TO_INSPECT, pieces_ok, pieces_defect)
        print(f"✅ Session updated")

        # Update lot metrics
        update_lot_metrics(conn)

        # Summary
        print("\n" + "=" * 60)
        print("✅ INSPECTION SIMULATION COMPLETE!")
        print("=" * 60)
        print(f"\n📋 Summary:")
        print(f"   Session ID: {session_id}")
        print(f"   Pieces inspected: {NUM_PIECES_TO_INSPECT}")
        print(f"   Pieces OK: {pieces_ok} ({pieces_ok/NUM_PIECES_TO_INSPECT*100:.1f}%)")
        print(f"   Pieces with defects: {pieces_defect} ({pieces_defect/NUM_PIECES_TO_INSPECT*100:.1f}%)")
        print(f"   Total photos: {NUM_PIECES_TO_INSPECT * 2}")
        print(f"   Photos stored in: {storage_path}")
        print()

        # List some photos
        print("📸 Sample photos created:")
        photos = sorted(storage_path.glob("*.jpg"))[:6]
        for photo in photos:
            print(f"   • {photo.name}")
        if len(photos) > 6:
            print(f"   ... and {len(list(storage_path.glob('*.jpg'))) - 6} more")
        print()

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
