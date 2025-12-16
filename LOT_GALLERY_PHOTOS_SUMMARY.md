# Lot Gallery Photos - Setup Summary

## Overview
Successfully uploaded images to DigitalOcean Spaces and added them to all Cordeiro Campos lot galleries.

## Images Uploaded

### Source Files
- **img2.jpg** (4.7 MB) - from `/home/celso/projects/qa_dashboard/ai_withllm/img2.jpg`
- **img4.jpg** (3.3 MB) - from `/home/celso/projects/qa_dashboard/ai_withllm/img4.jpg`

### DigitalOcean Spaces Location
- **Bucket**: `pp-photos`
- **Region**: `lon1` (London)
- **Endpoint**: `https://lon1.digitaloceanspaces.com`
- **Path**: `cordeiro-campos/lot-gallery/`

### Public URLs
1. `https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img2.jpg`
2. `https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img4.jpg`

## Database Integration

### Storage Method
Photos are stored in the `tech_pack_data` JSONB field of the `lots` table:
```json
{
  "gallery_photos": [
    "https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img2.jpg",
    "https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/img4.jpg"
  ],
  "gallery_updated_at": "2025-11-27T14:57:45.123456"
}
```

### Lots Updated
All **10 unique Cordeiro Campos lots** now have gallery photos:

| Style Reference | Garment Type | Status | Photo Count |
|----------------|--------------|--------|-------------|
| CC-AW25-J001 | JACKET | IN_PRODUCTION | 2 |
| CC-AW25-K001 | SWEATER | SHIPPED | 2 |
| CC-AW25-K002 | SWEATER | APPROVED | 2 |
| CC-AW25-K003 | SWEATER | INSPECTION | 2 |
| CC-AW25-P001 | PANTS | SHIPPED | 2 |
| CC-SS25-B001 | BLOUSE | APPROVED | 2 |
| CC-SS25-D001 | DRESS | APPROVED | 2 |
| CC-SS25-P001 | POLO_SHIRT | APPROVED | 2 |
| CC-SS25-SH001 | SHORTS | PENDING_APPROVAL | 2 |
| CC-SS25-T001 | T_SHIRT | SHIPPED | 2 |

## Verification Queries

### Check Gallery Photos
```sql
SELECT DISTINCT ON (style_ref)
    style_ref,
    garment_type,
    jsonb_array_length(tech_pack_data->'gallery_photos') as photo_count
FROM lots
WHERE tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
ORDER BY style_ref;
```

### View Photo URLs for a Lot
```sql
SELECT
    style_ref,
    tech_pack_data->'gallery_photos' as gallery_urls
FROM lots
WHERE tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
AND style_ref = 'CC-AW25-K001';
```

### Extract Individual URLs
```sql
SELECT
    style_ref,
    jsonb_array_elements_text(tech_pack_data->'gallery_photos') as photo_url
FROM lots
WHERE tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
AND style_ref = 'CC-AW25-K001';
```

## DigitalOcean Spaces Configuration

### Access Credentials
- **Access Key**: `DO00WB4PFRBMK7XB9UN7`
- **Secret Key**: `ANwfAsuQdEDr0l5jtF/JJE6cO0J10zW7KdNKoVnbLm0`

### AWS CLI Commands

#### List Bucket Contents
```bash
AWS_ACCESS_KEY_ID=DO00WB4PFRBMK7XB9UN7 \
AWS_SECRET_ACCESS_KEY=ANwfAsuQdEDr0l5jtF/JJE6cO0J10zW7KdNKoVnbLm0 \
aws s3 ls s3://pp-photos/cordeiro-campos/lot-gallery/ \
  --endpoint-url=https://lon1.digitaloceanspaces.com \
  --region=lon1
```

#### Upload New Photo
```bash
AWS_ACCESS_KEY_ID=DO00WB4PFRBMK7XB9UN7 \
AWS_SECRET_ACCESS_KEY=ANwfAsuQdEDr0l5jtF/JJE6cO0J10zW7KdNKoVnbLm0 \
aws s3 cp /path/to/image.jpg s3://pp-photos/cordeiro-campos/lot-gallery/image.jpg \
  --endpoint-url=https://lon1.digitaloceanspaces.com \
  --region=lon1 \
  --acl public-read
```

## Files Created

1. **add_lot_gallery_photos.py** - Script to add gallery photos to lots
   - Reads lot records from database
   - Updates `tech_pack_data` field with photo URLs
   - Verifies updates

## Access from Application

To access gallery photos in your application:

### TypeScript/JavaScript Example
```typescript
interface Lot {
  style_ref: string;
  tech_pack_data?: {
    gallery_photos?: string[];
    gallery_updated_at?: string;
  };
}

function getGalleryPhotos(lot: Lot): string[] {
  return lot.tech_pack_data?.gallery_photos || [];
}
```

### SQL Query in Application
```sql
SELECT
  l.id,
  l.style_ref,
  l.garment_type,
  l.tech_pack_data->'gallery_photos' as gallery_photos
FROM lots l
WHERE l.tenant_id = :tenantId
  AND l.tech_pack_data ? 'gallery_photos';
```

## Next Steps

### Adding More Photos
1. Upload images to DigitalOcean Spaces:
   ```bash
   aws s3 cp image.jpg s3://pp-photos/cordeiro-campos/lot-gallery/image.jpg \
     --endpoint-url=https://lon1.digitaloceanspaces.com \
     --region=lon1 --acl public-read
   ```

2. Update the lot in the database:
   ```sql
   UPDATE lots
   SET tech_pack_data = jsonb_set(
     COALESCE(tech_pack_data, '{}'::jsonb),
     '{gallery_photos}',
     tech_pack_data->'gallery_photos' || '["https://pp-photos.lon1.digitaloceanspaces.com/cordeiro-campos/lot-gallery/image.jpg"]'::jsonb
   )
   WHERE id = :lot_id;
   ```

### Photo Organization Best Practices
- Use consistent naming: `{tenant-slug}/lot-gallery/{style_ref}-{sequence}.jpg`
- Store thumbnails separately: `{tenant-slug}/lot-gallery/thumbs/`
- Consider organizing by garment type or collection
- Add metadata in tech_pack_data (captions, photographer, date, etc.)

## Summary

✅ **Images Uploaded**: 2 photos (8 MB total)
✅ **Storage Location**: DigitalOcean Spaces (lon1 region)
✅ **Lots Updated**: 10 unique lots
✅ **Access**: Public URLs configured
✅ **Verification**: All photos accessible and in database

---

**Setup Date**: 2025-11-27
**Status**: ✅ Complete and Ready for Use
