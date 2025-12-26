#!/usr/bin/env python3
"""
Convert JSON objects to arrays for frontend compatibility
- labels: object -> array
- hang_tags: object -> array
- packaging: object -> array
- bill_of_materials: object -> array
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

def object_to_array(obj_data, type_field='type'):
    """Convert JSON object to array format"""
    if not obj_data:
        return []

    result = []
    for key, value in obj_data.items():
        # Add type/name field
        item = {type_field: key.replace('_', ' ').title()}
        item.update(value)
        result.append(item)

    return result

def convert_packaging(pkg_data):
    """Convert packaging object to array"""
    if not pkg_data:
        return []

    result = []
    for key, value in pkg_data.items():
        item = {'type': key.replace('_', ' ').title()}

        # Map nested fields
        if isinstance(value, dict):
            for k, v in value.items():
                item[k] = v

        result.append(item)

    return result

def convert_bom(bom_data):
    """Convert bill of materials object to array"""
    if not bom_data:
        return []

    result = []
    for category, details in bom_data.items():
        item = {
            'category': category.replace('_', ' ').title(),
            'description': details.get('description', ''),
            'supplier': details.get('supplier', ''),
            'unit': details.get('unit', ''),
            'quantity_per_unit': details.get('quantity_per_unit', 0)
        }
        result.append(item)

    return result

def main():
    print("=" * 60)
    print("🔄 CONVERTING JSON OBJECTS TO ARRAYS")
    print("=" * 60)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get all lots with JSON data
        cursor.execute("""
            SELECT id, style_ref, labels, hang_tags, packaging, bill_of_materials
            FROM lots
            WHERE tenant_id = %s
            AND (labels IS NOT NULL OR hang_tags IS NOT NULL
                 OR packaging IS NOT NULL OR bill_of_materials IS NOT NULL)
        """, (TENANT_ID,))

        lots = cursor.fetchall()
        print(f"\n📦 Processing {len(lots)} lots...\n")

        converted = 0

        for lot_id, style_ref, labels, hang_tags, packaging, bom in lots:
            print(f"📦 {style_ref}")
            updates = []
            params = []

            # Convert labels
            if labels and isinstance(labels, dict):
                labels_array = object_to_array(labels, 'type')
                updates.append("labels = %s")
                params.append(json.dumps(labels_array))
                print(f"   ✓ Labels: {len(labels_array)} items")

            # Convert hang tags
            if hang_tags and isinstance(hang_tags, dict):
                tags_array = object_to_array(hang_tags, 'type')
                updates.append("hang_tags = %s")
                params.append(json.dumps(tags_array))
                print(f"   ✓ Hang tags: {len(tags_array)} items")

            # Convert packaging
            if packaging and isinstance(packaging, dict):
                pkg_array = convert_packaging(packaging)
                updates.append("packaging = %s")
                params.append(json.dumps(pkg_array))
                print(f"   ✓ Packaging: {len(pkg_array)} items")

            # Convert bill of materials
            if bom and isinstance(bom, dict):
                bom_array = convert_bom(bom)
                updates.append("bill_of_materials = %s")
                params.append(json.dumps(bom_array))
                print(f"   ✓ Bill of materials: {len(bom_array)} items")

            if updates:
                params.append(lot_id)
                update_sql = f"""
                    UPDATE lots
                    SET {', '.join(updates)}, updated_at = NOW()
                    WHERE id = %s
                """
                cursor.execute(update_sql, params)
                conn.commit()
                converted += 1
                print(f"   ✅ Converted\n")
            else:
                print(f"   ⚠️  No data to convert\n")

        print("=" * 60)
        print("📊 CONVERSION SUMMARY")
        print("=" * 60)
        print(f"  Total Lots: {len(lots)}")
        print(f"  ✅ Converted: {converted}")
        print()
        print("✅ Conversion complete!")

        conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
