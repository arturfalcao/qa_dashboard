#!/usr/bin/env python3
"""
Create 20 pieces with photos for Cordeiro Campos lot CC-SS25-T001
"""

import boto3
from botocore.client import Config
import psycopg2
from pathlib import Path
import uuid
from datetime import datetime, timezone

# DigitalOcean Spaces Configuration
SPACES_REGION = 'lon1'
SPACES_ENDPOINT = f'https://{SPACES_REGION}.digitaloceanspaces.com'
SPACES_ACCESS_KEY = 'DO004MPHJC2PFZVQE23M'
SPACES_SECRET_KEY = 'WFoe83+YGGJkV/wQmtSJcxStddXp4pexdT7/0xXyvGQ'
SPACES_BUCKET = 'pp-photos'

# Database Configuration
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

# Source images
IMG2_PATH = Path('/home/celso/projects/qa_dashboard/ai_withllm/img2.jpg')
IMG4_PATH = Path('/home/celso/projects/qa_dashboard/ai_withllm/img4.jpg')

# Target lot
LOT_ID = '0ac8675e-414c-42cb-afd4-8139dd229f40'
TENANT_ID = '254226e3-a316-413e-aa05-d0dd47c8f855'
NUM_PIECES = 20

def upload_to_spaces(local_path, s3_key):
    """Upload file to DigitalOcean Spaces"""
    session = boto3.session.Session()
    client = session.client('s3',
                           region_name=SPACES_REGION,
                           endpoint_url=SPACES_ENDPOINT,
                           aws_access_key_id=SPACES_ACCESS_KEY,
                           aws_secret_access_key=SPACES_SECRET_KEY,
                           config=Config(signature_version='s3v4'))

    client.upload_file(
        str(local_path),
        SPACES_BUCKET,
        s3_key,
        ExtraArgs={
            'ACL': 'public-read',
            'ContentType': 'image/jpeg'
        }
    )

    public_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{s3_key}"
    return public_url

def main():
    print("=" * 60)
    print("🔧 CREATING PIECES WITH PHOTOS FOR CORDEIRO CAMPOS")
    print("=" * 60)

    # Check source images exist
    if not IMG2_PATH.exists():
        print(f"❌ Error: {IMG2_PATH} not found!")
        return
    if not IMG4_PATH.exists():
        print(f"❌ Error: {IMG4_PATH} not found!")
        return

    print(f"✅ Source images found:")
    print(f"   - img2.jpg ({IMG2_PATH.stat().st_size / 1024:.1f}KB)")
    print(f"   - img4.jpg ({IMG4_PATH.stat().st_size / 1024:.1f}KB)")

    try:
        # Connect to database
        print("\n📡 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ Connected")

        # Get inspector user for operator
        cursor.execute("""
            SELECT id FROM users WHERE tenant_id = %s AND email LIKE %s LIMIT 1
        """, (TENANT_ID, '%inspector%'))
        operator = cursor.fetchone()
        if not operator:
            cursor.execute("SELECT id FROM users WHERE tenant_id = %s LIMIT 1", (TENANT_ID,))
            operator = cursor.fetchone()

        if not operator:
            print("❌ No user found for Cordeiro Campos tenant")
            return

        operator_id = operator[0]
        print(f"✅ Using operator: {operator_id}")

        # Create edge device if needed
        cursor.execute("SELECT id FROM edge_devices WHERE tenant_id = %s LIMIT 1", (TENANT_ID,))
        device = cursor.fetchone()

        if not device:
            print("\n📱 Creating edge device...")
            device_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO edge_devices (id, tenant_id, name, secret_key, workbench_number, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (device_id, TENANT_ID, 'Workbench 1', f'secret-{uuid.uuid4()}', 1, 'active'))
            device_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Created edge device: {device_id}")
        else:
            device_id = device[0]
            print(f"✅ Using existing edge device: {device_id}")

        # Check if inspection session already exists
        cursor.execute("SELECT id FROM inspection_sessions WHERE lot_id = %s LIMIT 1", (LOT_ID,))
        session = cursor.fetchone()

        if session:
            session_id = session[0]
            print(f"\n📋 Using existing inspection session: {session_id}")
            # Delete existing pieces for clean start
            cursor.execute("DELETE FROM apparel_pieces WHERE inspection_session_id = %s", (session_id,))
            conn.commit()
            print("   Cleared existing pieces")
        else:
            print("\n📋 Creating inspection session...")
            session_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO inspection_sessions (id, lot_id, device_id, operator_id, started_at, ended_at,
                                                  pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                                                  created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW() - INTERVAL '1 hour', NOW(), %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (session_id, LOT_ID, device_id, operator_id, NUM_PIECES, NUM_PIECES - 2, 1, 1))
            session_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Created inspection session: {session_id}")

        # Create pieces and upload photos
        print(f"\n📸 Creating {NUM_PIECES} pieces with photos...")

        s3_base_path = f"cordeiro-campos/{LOT_ID}"

        for i in range(1, NUM_PIECES + 1):
            piece_id = str(uuid.uuid4())

            # Determine piece status (most OK, some with issues)
            if i == 5:
                status = 'defect'
            elif i == 12:
                status = 'potential_defect'
            else:
                status = 'ok'

            # Create piece
            cursor.execute("""
                INSERT INTO apparel_pieces (id, inspection_session_id, piece_number, status,
                                           inspection_started_at, inspection_completed_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW() - INTERVAL '1 hour' + %s * INTERVAL '1 minute',
                        NOW() - INTERVAL '1 hour' + %s * INTERVAL '1 minute' + INTERVAL '30 seconds',
                        NOW(), NOW())
                RETURNING id
            """, (piece_id, session_id, i, status, i, i))

            # Upload and create photo records
            for photo_num, img_path in [(1, IMG2_PATH), (2, IMG4_PATH)]:
                s3_key = f"{s3_base_path}/piece_{i:03d}_photo_{photo_num}.jpg"

                print(f"  Piece #{i:02d} - photo_{photo_num}...", end=' ', flush=True)

                # Upload to S3
                public_url = upload_to_spaces(img_path, s3_key)

                # Create photo record
                cursor.execute("""
                    INSERT INTO piece_photos (id, piece_id, file_path, s3_url, captured_at, created_at)
                    VALUES (%s, %s, %s, %s, NOW() - INTERVAL '1 hour' + %s * INTERVAL '1 minute', NOW())
                """, (str(uuid.uuid4()), piece_id, s3_key, public_url, i))

                print("✅")

            conn.commit()

        # Update inspection session counts
        cursor.execute("""
            UPDATE inspection_sessions
            SET pieces_inspected = %s,
                pieces_ok = (SELECT COUNT(*) FROM apparel_pieces WHERE inspection_session_id = %s AND status = 'ok'),
                pieces_defect = (SELECT COUNT(*) FROM apparel_pieces WHERE inspection_session_id = %s AND status = 'defect'),
                pieces_potential_defect = (SELECT COUNT(*) FROM apparel_pieces WHERE inspection_session_id = %s AND status = 'potential_defect'),
                updated_at = NOW()
            WHERE id = %s
        """, (NUM_PIECES, session_id, session_id, session_id, session_id))
        conn.commit()

        # Update lot inspected progress
        cursor.execute("""
            UPDATE lots SET inspected_progress = %s, updated_at = NOW() WHERE id = %s
        """, (NUM_PIECES, LOT_ID))
        conn.commit()

        print()
        print("=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"  ✅ Created {NUM_PIECES} pieces")
        print(f"  ✅ Uploaded {NUM_PIECES * 2} photos ({NUM_PIECES} x img2.jpg + {NUM_PIECES} x img4.jpg)")
        print(f"  📁 S3 path: {s3_base_path}/")
        print()
        print("🎉 Done! Check https://app.packpolish.com/c/cordeiro-campos/lots/0ac8675e-414c-42cb-afd4-8139dd229f40/gallery")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
