#!/usr/bin/env python3
"""
Fix photo uploads - replace img3 with img4 for photo_2 files
"""

import boto3
from botocore.client import Config
import psycopg2
from pathlib import Path

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

# Source image
SOURCE_IMAGE = Path('/home/celso/projects/qa_dashboard/ai_withllm/img4.jpg')
SESSION_ID = 'a513d563-d465-4456-9fc6-be2cc2571531'

def upload_to_spaces(local_path, s3_key):
    """Upload file to DigitalOcean Spaces"""
    session = boto3.session.Session()
    client = session.client('s3',
                           region_name=SPACES_REGION,
                           endpoint_url=SPACES_ENDPOINT,
                           aws_access_key_id=SPACES_ACCESS_KEY,
                           aws_secret_access_key=SPACES_SECRET_KEY,
                           config=Config(signature_version='s3v4'))

    # Upload file
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
    print("🔧 FIXING PHOTO_2 FILES - REPLACING IMG3 WITH IMG4")
    print("=" * 60)

    if not SOURCE_IMAGE.exists():
        print(f"❌ Error: {SOURCE_IMAGE} not found!")
        return

    print(f"✅ Source image found: {SOURCE_IMAGE.name} ({SOURCE_IMAGE.stat().st_size / 1024 / 1024:.1f}MB)")

    try:
        # Connect to database
        print("\n📡 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected")

        # Get all photo_2 files from the inspection session
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pp.id, pp.file_path, pp.s3_url, ap.piece_number
            FROM piece_photos pp
            JOIN apparel_pieces ap ON ap.id = pp.piece_id
            JOIN inspection_sessions iss ON iss.id = ap.inspection_session_id
            WHERE iss.id = %s
            AND pp.file_path LIKE %s
            ORDER BY ap.piece_number
        """, (SESSION_ID, '%photo_2%'))

        photos = cursor.fetchall()
        total = len(photos)

        if total == 0:
            print("⚠️  No photo_2 files found")
            return

        print(f"\n📸 Found {total} photo_2 files to replace with img4.jpg\n")

        replaced = 0

        for photo_id, file_path, s3_url, piece_number in photos:
            try:
                # Extract S3 key from file_path
                s3_key = file_path

                print(f"  🔄 Piece #{piece_number:03d} - photo_2...", end=' ')

                # Upload img4.jpg with the same S3 key
                public_url = upload_to_spaces(SOURCE_IMAGE, s3_key)

                print(f"✅")
                replaced += 1

            except Exception as e:
                print(f"❌ Error: {e}")

        print()
        print("=" * 60)
        print("📊 REPLACEMENT SUMMARY")
        print("=" * 60)
        print(f"  Total photo_2 files: {total}")
        print(f"  ✅ Replaced with img4.jpg: {replaced}")
        print()

        if replaced > 0:
            print("🎉 All photo_2 files now use img4.jpg!")
            print(f"   Source: {SOURCE_IMAGE}")
            print()

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
