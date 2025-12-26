#!/usr/bin/env python3
"""
Upload mock lot images to S3/MinIO and update database with correct keys
"""

import psycopg2
import psycopg2.extras
import os
import sys
from minio import Minio
from minio.error import S3Error
from pathlib import Path
import io

# Register UUID adapter
psycopg2.extras.register_uuid()

# MinIO/S3 Configuration from environment variables
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'false').lower() == 'true'
MINIO_PHOTOS_BUCKET = os.getenv('MINIO_PHOTOS_BUCKET', 'pp-photos')

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5433'))
DB_NAME = os.getenv('DB_NAME', 'qa_dashboard')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# Local images directory
IMAGES_DIR = "/home/celso/projects/qa_dashboard/mock_lot_images"

def connect_to_minio():
    """Connect to MinIO/S3"""
    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")

    # Remove http:// or https:// if present
    endpoint = MINIO_ENDPOINT.replace('http://', '').replace('https://', '')

    client = Minio(
        endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL
    )

    # Ensure bucket exists
    try:
        if not client.bucket_exists(MINIO_PHOTOS_BUCKET):
            print(f"Creating bucket {MINIO_PHOTOS_BUCKET}...")
            client.make_bucket(MINIO_PHOTOS_BUCKET)
            print(f"✓ Bucket {MINIO_PHOTOS_BUCKET} created")
        else:
            print(f"✓ Bucket {MINIO_PHOTOS_BUCKET} exists")
    except S3Error as e:
        print(f"Error checking/creating bucket: {e}")
        sys.exit(1)

    return client

def connect_to_db():
    """Connect to PostgreSQL database"""
    print(f"Connecting to database {DB_NAME}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    print("✓ Connected to database")
    return conn

def get_tenant_id_for_photo(cur, photo_id):
    """Get tenant_id for a photo through its relationships"""
    cur.execute("""
        SELECT ap.tenant_id
        FROM piece_photos pp
        JOIN apparel_pieces ap ON pp.piece_id = ap.id
        WHERE pp.id = %s
    """, (photo_id,))
    result = cur.fetchone()
    return result[0] if result else None

def get_lot_and_piece_ids_for_photo(cur, photo_id):
    """Get lot_id and piece_id for a photo"""
    cur.execute("""
        SELECT ap.lot_id, pp.piece_id
        FROM piece_photos pp
        JOIN apparel_pieces ap ON pp.piece_id = ap.id
        WHERE pp.id = %s
    """, (photo_id,))
    result = cur.fetchone()
    return result if result else (None, None)

def upload_images_to_s3(minio_client, conn):
    """Upload images from local directory to S3 and update database"""
    cur = conn.cursor()

    # Get all photos from database
    cur.execute("""
        SELECT pp.id, pp.storage_key, pp.piece_id, ap.lot_id, ap.tenant_id
        FROM piece_photos pp
        JOIN apparel_pieces ap ON pp.piece_id = ap.id
        WHERE pp.storage_key LIKE 'mock_lot_images/%'
        ORDER BY pp.created_at
    """)

    photos = cur.fetchall()
    total_photos = len(photos)

    if total_photos == 0:
        print("No photos found with mock_lot_images paths")
        return

    print(f"\nFound {total_photos} photos to upload")
    print("=" * 60)

    uploaded = 0
    skipped = 0
    errors = 0

    for photo_id, old_key, piece_id, lot_id, tenant_id in photos:
        # Extract filename from old key
        filename = os.path.basename(old_key)
        local_path = os.path.join(IMAGES_DIR, filename)

        # Check if local file exists
        if not os.path.exists(local_path):
            print(f"✗ File not found: {local_path}")
            skipped += 1
            continue

        # Generate new S3 key following the pattern from StorageService
        # Pattern: clients/{tenantId}/lots/{lotId}/pieces/{pieceId}/{uuid}-{filename}
        new_key = f"clients/{tenant_id}/lots/{lot_id}/pieces/{piece_id}/{photo_id}-{filename}"

        try:
            # Upload file to MinIO
            with open(local_path, 'rb') as file_data:
                file_stat = os.stat(local_path)
                minio_client.put_object(
                    MINIO_PHOTOS_BUCKET,
                    new_key,
                    file_data,
                    file_stat.st_size,
                    content_type='image/jpeg'
                )

            # Update database with new key
            cur.execute("""
                UPDATE piece_photos
                SET storage_key = %s
                WHERE id = %s
            """, (new_key, photo_id))

            uploaded += 1
            if uploaded % 10 == 0:
                print(f"Uploaded {uploaded}/{total_photos} images...")

        except S3Error as e:
            print(f"✗ Error uploading {filename}: {e}")
            errors += 1
        except Exception as e:
            print(f"✗ Unexpected error with {filename}: {e}")
            errors += 1

    # Commit all database updates
    conn.commit()
    cur.close()

    print("=" * 60)
    print(f"\n✓ Upload complete!")
    print(f"  Uploaded: {uploaded}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")
    print(f"  Total:    {total_photos}")

    if uploaded > 0:
        print(f"\n✓ Database updated with new S3 keys")
        print(f"  Bucket: {MINIO_PHOTOS_BUCKET}")
        print(f"  Endpoint: {MINIO_ENDPOINT}")

def main():
    """Main execution"""
    print("=" * 60)
    print("Mock Images S3 Upload Script")
    print("=" * 60)

    # Check if images directory exists
    if not os.path.exists(IMAGES_DIR):
        print(f"✗ Images directory not found: {IMAGES_DIR}")
        print("Run generate_lot_images.py first to create mock images")
        sys.exit(1)

    # Count local images
    image_files = list(Path(IMAGES_DIR).glob("*.jpg"))
    print(f"\nFound {len(image_files)} local images in {IMAGES_DIR}")

    # Connect to services
    minio_client = connect_to_minio()
    conn = connect_to_db()

    try:
        # Upload images
        upload_images_to_s3(minio_client, conn)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    main()
