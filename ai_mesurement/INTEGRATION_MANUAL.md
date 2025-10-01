# QA Dashboard Measurement Integration

## 🚀 Quick Start

### 1. Test the Integration

```bash
# Process all pending pieces once
python qa_dashboard_integration.py --process-once

# Run continuously (processes every 60 seconds)
python qa_dashboard_integration.py --continuous
```

### 2. Run as Background Service

```bash
# Start the service
./measurement_service.sh &

# Or use nohup to keep running after logout
nohup ./measurement_service.sh > measurement_service.log 2>&1 &
```

## 📊 How It Works

The integration automatically:

1. **Monitors the database** for new piece photos
2. **Takes the FIRST photo** of each piece
3. **Runs measurements** using the calibrated scale (34.32 px/cm for wooden ruler)
4. **Saves results** to the `piece_measurements` table
5. **Uploads annotated images** with measurement visualizations

## 🗄️ Database Integration

### Automatic Table Creation
The system automatically creates the `piece_measurements` table with:

- All garment measurements (length, chest, waist, hem, etc.)
- Garment type detection (shirt, trousers, dress, jacket)
- Size estimation
- Confidence scores
- Annotated image paths

### Query Measurements

```sql
-- View all measurements
SELECT
    ap.piece_number,
    l.style_ref,
    pm.garment_type,
    pm.body_length_cm,
    pm.chest_width_cm,
    pm.waist_width_cm,
    pm.size_estimate,
    pm.confidence
FROM piece_measurements pm
JOIN apparel_pieces ap ON ap.id = pm.piece_id
JOIN inspection_sessions isp ON isp.id = ap.inspection_session_id
JOIN lots l ON l.id = isp.lot_id
ORDER BY pm.measured_at DESC;

-- Get statistics
SELECT
    garment_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(chest_width_cm) as avg_chest,
    AVG(waist_width_cm) as avg_waist
FROM piece_measurements
GROUP BY garment_type;
```

## 🔧 Configuration

### Scale Calibration
The system uses **34.32 pixels/cm** for the wooden ruler. To adjust:

```python
# In qa_dashboard_integration.py
self.measurement_system = IntelligentGarmentMeasurement(
    ruler_length_cm=31.0,
    manual_scale=34.32,  # Adjust this value
    debug=False
)
```

### Processing Interval
Default: 60 seconds. To change:

```python
# In run_continuous_processing()
await asyncio.sleep(60)  # Change interval here
```

## 📋 Features

- ✅ Automatic measurement on first photo
- ✅ Garment type detection (CLIP-based)
- ✅ Size estimation
- ✅ Database integration
- ✅ Annotated image generation
- ✅ Confidence scoring
- ✅ Batch processing
- ✅ S3 image support

## 🖼️ Annotated Images

The system generates annotated images showing:
- Detected garment outline
- Measurement lines
- Measurement values
- Garment type
- Size estimate

Images are saved as: `clean_annotated_{piece_id}.png`

## 📈 Monitoring

Check processing status:

```bash
# View logs
tail -f measurement_service.log

# Check database
psql -h localhost -p 5433 -U postgres -d qa_dashboard -c "
SELECT COUNT(*) as total_measured,
       COUNT(DISTINCT piece_id) as unique_pieces,
       AVG(confidence)::numeric(3,1) as avg_confidence
FROM piece_measurements
WHERE measured_at > NOW() - INTERVAL '1 hour';
"
```

## 🛑 Stop Service

```bash
# Find process
ps aux | grep qa_dashboard_integration

# Kill process
kill <PID>
```

## 🔍 Troubleshooting

### Issue: Measurements seem off
- Check ruler is visible and 31cm
- Verify scale: should be ~34.32 px/cm for wooden ruler
- Ensure garment is laid flat

### Issue: Photos not found
- Check file paths in database
- Verify S3 URLs are accessible
- Check file permissions

### Issue: Database connection failed
- Verify PostgreSQL is running on port 5433
- Check credentials in script

## 📊 Expected Measurements

For a typical shirt:
- Length: 65-70 cm
- Chest width: 50-55 cm (100-110 cm circumference)
- Waist width: 45-52 cm
- Hem width: 50-57 cm

## 🚦 Status Codes

The system uses these confidence levels:
- > 80%: High confidence ✅
- 60-80%: Good confidence ⚠️
- < 60%: Low confidence ❌

## 📝 Notes

- Only the FIRST photo of each piece is measured
- Measurements are in centimeters
- Circumference = Width × 2 (for laid flat garments)
- The wooden ruler must be visible for accurate scale