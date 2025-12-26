#!/usr/bin/env python3
"""
Add gallery photos to Cordeiro Campos lots
Stores photo URLs in the tech_pack_data JSONB field
"""

import psycopg2
import json
from datetime import datetime

# Production database connection
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

TENANT_ID = '254226e3-a316-413e-aa05-d0dd47c8f855'

# Photo URLs in DigitalOcean Spaces
PHOTO_URLS = [
    'https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img2.jpg',
    'https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img4.jpg'
]

def add_gallery_photos_to_lots(conn):
    """Add gallery photos to all Cordeiro Campos lots"""
    cursor = conn.cursor()

    print("📸 Adding gallery photos to Cordeiro Campos lots...\n")

    # Get all Cordeiro Campos lots
    cursor.execute("""
        SELECT id, style_ref, tech_pack_data
        FROM lots
        WHERE tenant_id = %s
        ORDER BY style_ref
    """, (TENANT_ID,))

    lots = cursor.fetchall()
    updated_count = 0

    for lot_id, style_ref, tech_pack_data in lots:
        # Parse existing tech_pack_data or create new
        if tech_pack_data:
            tech_data = tech_pack_data if isinstance(tech_pack_data, dict) else json.loads(tech_pack_data)
        else:
            tech_data = {}

        # Add gallery photos
        tech_data['gallery_photos'] = PHOTO_URLS
        tech_data['gallery_updated_at'] = datetime.now().isoformat()

        # Update the lot
        cursor.execute("""
            UPDATE lots
            SET tech_pack_data = %s,
                updated_at = %s
            WHERE id = %s
        """, (json.dumps(tech_data), datetime.now(), lot_id))

        updated_count += 1
        print(f"✓ Added gallery photos to lot {style_ref}")

    conn.commit()
    print(f"\n✅ Successfully added gallery photos to {updated_count} lots")

    return updated_count

def verify_photos(conn):
    """Verify photos were added correctly"""
    cursor = conn.cursor()

    print("\n🔍 Verifying gallery photos...\n")

    cursor.execute("""
        SELECT style_ref, tech_pack_data->'gallery_photos' as photos
        FROM lots
        WHERE tenant_id = %s
        AND tech_pack_data ? 'gallery_photos'
        ORDER BY style_ref
    """, (TENANT_ID,))

    results = cursor.fetchall()

    if results:
        print(f"✅ Found gallery photos in {len(results)} lots:")
        for style_ref, photos in results:
            photo_list = json.loads(photos) if isinstance(photos, str) else photos
            print(f"  • {style_ref}: {len(photo_list)} photos")
    else:
        print("⚠️ No gallery photos found in lots")

    return len(results)

def main():
    print("=" * 70)
    print("📸 ADD GALLERY PHOTOS TO CORDEIRO CAMPOS LOTS")
    print("=" * 70)
    print("\nPhotos to add:")
    for i, url in enumerate(PHOTO_URLS, 1):
        print(f"  {i}. {url}")
    print()

    try:
        # Connect to database
        print("📡 Connecting to production database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully\n")

        # Add photos to lots
        updated_count = add_gallery_photos_to_lots(conn)

        # Verify photos
        verified_count = verify_photos(conn)

        print("\n" + "=" * 70)
        print("✅ GALLERY PHOTOS SETUP COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Summary:")
        print(f"  • Photos added to: {updated_count} lots")
        print(f"  • Photos verified in: {verified_count} lots")
        print(f"  • Photo URLs: {len(PHOTO_URLS)}")
        print(f"\n🔗 Photo URLs:")
        for url in PHOTO_URLS:
            print(f"  • {url}")
        print()

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
