#!/usr/bin/env python3
"""
Fix material_composition format from object to array
"""

import psycopg2
import json

# Production database connection
DB_CONFIG = {
    'host': 'db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com',
    'port': 25060,
    'user': 'doadmin',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'defaultdb',
    'sslmode': 'require'
}

TENANT_ID = '1ad2510c-3503-4393-a643-1be7f94804ba'

def convert_material_composition(material_comp):
    """Convert material composition from object to array"""
    if not material_comp:
        return []

    if isinstance(material_comp, list):
        # Already an array
        return material_comp

    # Convert object to array
    result = []
    for fiber, percentage in material_comp.items():
        result.append({
            'fiber': fiber.capitalize(),
            'percentage': percentage
        })

    return result

def main():
    print("=" * 60)
    print("🔄 FIXING MATERIAL COMPOSITION FORMAT")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get all lots with material_composition
        cursor.execute("""
            SELECT id, style_ref, material_composition
            FROM lots
            WHERE tenant_id = %s
            AND material_composition IS NOT NULL
        """, (TENANT_ID,))

        lots = cursor.fetchall()
        print(f"\n📦 Processing {len(lots)} lots...\n")

        converted = 0

        for lot_id, style_ref, material_comp in lots:
            if isinstance(material_comp, dict) and not any(key in material_comp for key in ['fiber', 'percentage']):
                # This is an object format, need to convert
                material_array = convert_material_composition(material_comp)

                cursor.execute("""
                    UPDATE lots
                    SET material_composition = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(material_array), lot_id))

                conn.commit()
                converted += 1
                print(f"✅ {style_ref}: {len(material_array)} materials")
            else:
                print(f"⚠️  {style_ref}: Already in correct format")

        print()
        print("=" * 60)
        print("📊 CONVERSION SUMMARY")
        print("=" * 60)
        print(f"  Total Lots: {len(lots)}")
        print(f"  ✅ Converted: {converted}")
        print()
        print("✅ Material composition fix complete!")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
