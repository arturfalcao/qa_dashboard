#!/usr/bin/env python3
"""
Upload inspection photos to DigitalOcean Spaces (S3-compatible)
"""

import boto3
from botocore.client import Config
import psycopg2
from pathlib import Path
import sys

# DigitalOcean Spaces Configuration
SPACES_REGION = 'lon1'  # London
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

# Local photos directory
PHOTOS_DIR = Path('/tmp/qa_inspection_photos')

def upload_to_spaces(local_path, s3_key):
    """Upload file to DigitalOcean Spaces"""

    # Initialize S3 client for DigitalOcean Spaces
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
            'ACL': 'public-read',  # Make photos publicly accessible
            'ContentType': 'image/jpeg'
        }
    )

    # Return public URL
    public_url = f"https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/{s3_key}"
    return public_url

def update_photo_url(conn, photo_id, public_url):
    """Update piece_photos table with real S3 URL"""
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE piece_photos
        SET s3_url = %s
        WHERE id = %s
    """, (public_url, photo_id))

    conn.commit()

def main():
    if not SPACES_SECRET_KEY:
        print("❌ Error: SPACES_SECRET_KEY not configured!")
        print("Please edit the script and add your DigitalOcean Spaces secret key")
        sys.exit(1)

    print("=" * 60)
    print("📤 UPLOADING INSPECTION PHOTOS TO DIGITALOCEAN SPACES")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Region: {SPACES_REGION}")
    print(f"  Bucket: {SPACES_BUCKET}")
    print(f"  Endpoint: {SPACES_ENDPOINT}")
    print()

    try:
        # Connect to database
        print("📡 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected")

        # Get all photos that need upload
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, s3_url
            FROM piece_photos
            WHERE file_path LIKE '/tmp/qa_inspection_photos/%'
            ORDER BY created_at
        """)

        photos = cursor.fetchall()
        total = len(photos)

        if total == 0:
            print("⚠️  No photos found to upload")
            return

        print(f"📸 Found {total} photos to upload\n")

        uploaded = 0
        failed = 0

        for photo_id, file_path, s3_key in photos:
            local_path = Path(file_path)

            if not local_path.exists():
                print(f"  ⚠️  File not found: {local_path.name}")
                failed += 1
                continue

            try:
                # Upload to Spaces
                print(f"  📤 Uploading: {local_path.name}...", end=' ')
                public_url = upload_to_spaces(local_path, s3_key)

                # Update database
                update_photo_url(conn, photo_id, public_url)

                print(f"✅")
                uploaded += 1

            except Exception as e:
                print(f"❌ Error: {e}")
                failed += 1

        print()
        print("=" * 60)
        print("📊 UPLOAD SUMMARY")
        print("=" * 60)
        print(f"  Total photos: {total}")
        print(f"  ✅ Uploaded: {uploaded}")
        print(f"  ❌ Failed: {failed}")
        print()

        if uploaded > 0:
            print("🎉 Photos are now accessible via public URLs!")
            print(f"   Example: https://{SPACES_BUCKET}.{SPACES_REGION}.digitaloceanspaces.com/inspections/...")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
