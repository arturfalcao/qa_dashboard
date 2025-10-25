#!/usr/bin/env python3
"""
Generate realistic garment images for production lots
Creates inspection sessions, apparel pieces, and photos
"""

import psycopg2
import psycopg2.extras
import uuid
import os
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import random

# Register UUID adapter
psycopg2.extras.register_uuid()

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="qa_dashboard",
    user="postgres",
    password="postgres"
)
cur = conn.cursor()

# Create images directory
IMAGES_DIR = "/home/celso/projects/qa_dashboard/mock_lot_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Garment type mapping based on style refs
GARMENT_TYPES = {
    'SLM': 'Slim Shirt',
    'OXF': 'Oxford Shirt',
    'TSH': 'T-Shirt',
    'BLZ': 'Blazer',
    'POL': 'Polo',
    'SWT': 'Sweater',
    'HEN': 'Henley',
    'FLN': 'Flannel',
    'MXD': 'Maxi Dress',
    'EVD': 'Evening Dress',
    'MNS': 'Mini Skirt',
    'PLD': 'Pleated Skirt',
    'DNM': 'Denim Jeans',
    'CHN': 'Chinos',
    'CRG': 'Cargo Pants',
    'JGR': 'Joggers',
    'SHR': 'Shorts',
    'LEG': 'Leggings',
    'PCR': 'Peacoat',
    'DNC': 'Down Coat',
    'WBR': 'Windbreaker',
    'BOM': 'Bomber Jacket',
    'SPT': 'Sports Jacket',
    'YGA': 'Yoga Top',
    'JKT': 'Jacket',
    'KNT': 'Knitwear',
    'CDG': 'Cardigan',
    'TNK': 'Tank Top',
    'PUL': 'Pullover',
}

# Color palettes for different garment types
COLOR_PALETTES = {
    'shirt': ['#FFFFFF', '#87CEEB', '#FFE4E1', '#E6E6FA', '#F5F5DC'],
    'pants': ['#000080', '#2F4F4F', '#8B4513', '#696969', '#000000'],
    'dress': ['#FF69B4', '#DDA0DD', '#000000', '#8B0000', '#191970'],
    'jacket': ['#2F4F4F', '#000000', '#8B4513', '#556B2F', '#191970'],
    'activewear': ['#00BFFF', '#FF6347', '#32CD32', '#FFD700', '#FF1493'],
}

def get_garment_color(style_ref: str) -> str:
    """Get appropriate color for garment type"""
    if any(x in style_ref for x in ['SLM', 'OXF', 'TSH', 'POL', 'HEN', 'FLN']):
        return random.choice(COLOR_PALETTES['shirt'])
    elif any(x in style_ref for x in ['DNM', 'CHN', 'CRG', 'JGR', 'SHR']):
        return random.choice(COLOR_PALETTES['pants'])
    elif any(x in style_ref for x in ['MXD', 'EVD', 'MNS', 'PLD']):
        return random.choice(COLOR_PALETTES['dress'])
    elif any(x in style_ref for x in ['PCR', 'DNC', 'BOM', 'JKT', 'BLZ']):
        return random.choice(COLOR_PALETTES['jacket'])
    else:
        return random.choice(COLOR_PALETTES['activewear'])

def create_placeholder_image(style_ref: str, piece_number: int) -> str:
    """Create a placeholder image for a garment piece"""
    # Image dimensions
    width, height = 800, 1000

    # Get garment type and color
    garment_code = style_ref.split('-')[1] if '-' in style_ref else 'TSH'
    garment_type = GARMENT_TYPES.get(garment_code, 'Garment')
    color = get_garment_color(style_ref)

    # Create image
    img = Image.new('RGB', (width, height), color='#F5F5F5')
    draw = ImageDraw.Draw(img)

    # Draw garment placeholder
    margin = 100
    garment_rect = [margin, margin, width - margin, height - margin]
    draw.rectangle(garment_rect, fill=color, outline='#888888', width=3)

    # Add some texture (seams, details)
    # Vertical seam
    center_x = width // 2
    draw.line([(center_x, margin), (center_x, height - margin)], fill='#666666', width=2)

    # Horizontal details
    for y in range(margin + 150, height - margin, 200):
        draw.line([(margin + 50, y), (width - margin - 50, y)], fill='#888888', width=1)

    # Add tag/label area
    tag_y = height - margin - 80
    draw.rectangle([margin + 50, tag_y, margin + 150, tag_y + 60], fill='#FFFFFF', outline='#000000')

    # Add text (style ref and piece number)
    try:
        # Try to use a nice font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw style ref at top
    text_y = margin + 20
    draw.text((center_x, text_y), style_ref, fill='#000000', font=font_large, anchor='mt')

    # Draw garment type
    draw.text((center_x, text_y + 60), garment_type, fill='#333333', font=font_small, anchor='mt')

    # Draw piece number at bottom
    piece_text = f"Piece #{piece_number}"
    draw.text((center_x, height - margin + 20), piece_text, fill='#000000', font=font_small, anchor='mt')

    # Add QA inspection markers (simulate measurement points)
    marker_positions = [
        (center_x, margin + 200),  # Shoulder
        (margin + 150, margin + 400),  # Left sleeve
        (width - margin - 150, margin + 400),  # Right sleeve
        (center_x, height - margin - 200),  # Bottom
    ]

    for x, y in marker_positions:
        draw.ellipse([x-10, y-10, x+10, y+10], fill='#FF0000', outline='#FFFFFF', width=2)

    # Save image
    filename = f"{style_ref}_piece_{piece_number}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    img.save(filepath, 'JPEG', quality=85)

    return filepath

def download_real_garment_images():
    """Download some real garment images from Unsplash (free)"""
    print("\n📸 Downloading sample garment images from Unsplash...")

    # Unsplash API (free, no key needed for basic usage via source URL)
    garment_queries = [
        ('t-shirt', 1080, 1920),
        ('jeans', 1080, 1920),
        ('dress', 1080, 1920),
        ('jacket', 1080, 1920),
        ('sweater', 1080, 1920),
    ]

    downloaded = []
    for query, width, height in garment_queries:
        try:
            # Use Unsplash Source (no API key needed)
            url = f"https://source.unsplash.com/{width}x{height}/?{query},flatlay,fashion"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                filename = f"sample_{query.replace('-', '_')}.jpg"
                filepath = os.path.join(IMAGES_DIR, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                downloaded.append(filepath)
                print(f"  ✓ Downloaded: {query}")
            else:
                print(f"  ✗ Failed to download: {query}")
        except Exception as e:
            print(f"  ✗ Error downloading {query}: {e}")

    return downloaded

def create_edge_devices():
    """Create edge devices for inspection stations"""
    print("\n🖥️  Creating edge inspection devices...")

    cur.execute("SELECT id FROM tenants LIMIT 1")
    tenant_id = cur.fetchone()[0]

    devices = []
    for i in range(1, 6):
        device_id = uuid.uuid4()
        secret_key = f"device-secret-{uuid.uuid4()}"

        cur.execute("""
            INSERT INTO edge_devices (
                id, tenant_id, name, secret_key, workbench_number,
                status, last_seen_at, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, 'active', NOW(), NOW(), NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (device_id, tenant_id, f"Inspection Station {i}", secret_key, i))

        result = cur.fetchone()
        if result:
            devices.append(result[0])
            print(f"  ✓ Created device: Inspection Station {i}")

    # Get existing devices if any
    if not devices:
        cur.execute("SELECT id FROM edge_devices LIMIT 5")
        devices = [row[0] for row in cur.fetchall()]

    return devices

def create_inspection_data():
    """Create inspection sessions, pieces, and photos"""
    print("\n🔍 Creating inspection sessions and photos...")

    # Get operators (users with OPERATOR role)
    cur.execute("""
        SELECT u.id FROM users u
        JOIN user_roles ur ON u.id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'OPERATOR' AND u.is_active = true
        LIMIT 10
    """)
    operators = [row[0] for row in cur.fetchall()]

    if not operators:
        print("  ⚠️  No operators found. Creating inspection without operator assignment.")
        # Get any active user
        cur.execute("SELECT id FROM users WHERE is_active = true LIMIT 1")
        result = cur.fetchone()
        operators = [result[0]] if result else []

    if not operators:
        print("  ❌ No users found. Cannot create inspection sessions.")
        return

    # Get edge devices
    devices = create_edge_devices()
    if not devices:
        print("  ❌ No edge devices found. Cannot create inspection sessions.")
        return

    # Get lots to inspect
    cur.execute("""
        SELECT id, style_ref, status
        FROM lots
        WHERE status IN ('in_progress', 'completed')
        ORDER BY created_at DESC
        LIMIT 20
    """)
    lots = cur.fetchall()

    if not lots:
        print("  ⚠️  No lots found with appropriate status.")
        return

    total_photos = 0

    for lot_id, style_ref, lot_status in lots:
        # Create 1-2 inspection sessions per lot
        num_sessions = random.randint(1, 2)

        for session_num in range(num_sessions):
            session_id = uuid.uuid4()
            operator_id = random.choice(operators)
            device_id = random.choice(devices)

            # Session timing
            days_ago = random.randint(1, 30)
            started_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 8))
            ended_at = started_at + timedelta(hours=random.randint(2, 6))

            # Number of pieces inspected
            pieces_count = random.randint(5, 15)
            pieces_ok = random.randint(int(pieces_count * 0.7), pieces_count)
            pieces_defect = random.randint(0, pieces_count - pieces_ok)
            pieces_potential = pieces_count - pieces_ok - pieces_defect

            cur.execute("""
                INSERT INTO inspection_sessions (
                    id, lot_id, device_id, operator_id,
                    started_at, ended_at,
                    pieces_inspected, pieces_ok, pieces_defect, pieces_potential_defect,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                session_id, lot_id, device_id, operator_id,
                started_at, ended_at,
                pieces_count, pieces_ok, pieces_defect, pieces_potential
            ))

            # Create apparel pieces with photos
            for piece_num in range(1, pieces_count + 1):
                piece_id = uuid.uuid4()

                # Determine piece status
                if piece_num <= pieces_ok:
                    status = 'ok'
                elif piece_num <= pieces_ok + pieces_defect:
                    status = 'defect'
                else:
                    status = 'potential_defect'

                inspection_started = started_at + timedelta(minutes=piece_num * 10)
                inspection_completed = inspection_started + timedelta(minutes=random.randint(5, 15))

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

                # Create 2-3 photos per piece
                num_photos = random.randint(2, 3)
                for photo_num in range(num_photos):
                    # Generate placeholder image
                    image_path = create_placeholder_image(style_ref, piece_num)

                    # Store relative path for database
                    relative_path = f"mock_lot_images/{os.path.basename(image_path)}"
                    s3_url = f"https://qa-dashboard-mock.s3.amazonaws.com/{relative_path}"

                    cur.execute("""
                        INSERT INTO piece_photos (
                            id, piece_id, file_path, s3_url, captured_at, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (
                        uuid.uuid4(), piece_id, relative_path, s3_url,
                        inspection_started + timedelta(seconds=photo_num * 30)
                    ))

                    total_photos += 1

        if (lots.index((lot_id, style_ref, lot_status)) + 1) % 5 == 0:
            print(f"  ✓ Processed {lots.index((lot_id, style_ref, lot_status)) + 1} lots...")

    print(f"  ✓ Created {total_photos} photos for inspection pieces")

def main():
    print("=" * 70)
    print("📸 GENERATING LOT IMAGES & INSPECTION DATA")
    print("=" * 70)

    try:
        # Download some real sample images (optional)
        # download_real_garment_images()

        # Create inspection data with generated images
        create_inspection_data()

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 70)
        print("✅ IMAGE GENERATION COMPLETE!")
        print("=" * 70)

        # Show summary
        print("\n📊 Summary:")

        cur.execute("SELECT COUNT(*) FROM inspection_sessions")
        print(f"  • Inspection Sessions: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM apparel_pieces")
        print(f"  • Apparel Pieces: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM piece_photos")
        print(f"  • Photos: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM edge_devices")
        print(f"  • Edge Devices: {cur.fetchone()[0]}")

        print(f"\n📁 Images stored in: {IMAGES_DIR}")
        print(f"   Total image files: {len(os.listdir(IMAGES_DIR))}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
