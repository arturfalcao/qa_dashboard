# Cordeiro Campos - Quick Start Guide

## Access Information

### Tenant Access
- **Tenant Slug**: `cordeiro-campos`
- **Tenant ID**: `254226e3-a316-413e-aa05-d0dd47c8f855`
- **Client Name**: Cordeiro Campos
- **Website**: https://www.cordeirocampos.pt/

## Demo Users

| Email | Role | Use Case |
|-------|------|----------|
| `admin@cordeirocampos.pt` | TENANT_ADMIN | Full platform administration |
| `quality@cordeirocampos.pt` | QUALITY_MANAGER | Quality oversight and reporting |
| `inspector1@cordeirocampos.pt` | INSPECTOR | Conduct inspections |
| `inspector2@cordeirocampos.pt` | INSPECTOR | Conduct inspections |

## Demo Data Overview

### Production Summary
- **10 Production Lots** across different garment types
- **30,300 Total Units** in production
- **4 Portuguese Factories** (Santo Tirso, Guimarães, Vila Nova de Famalicão, Porto)
- **9 Quality Inspections** completed or in progress

### Lot Status Breakdown
```
✅ SHIPPED (3 lots)          - 12,000 units
✅ APPROVED (4 lots)          - 11,000 units
⏳ PENDING_APPROVAL (1 lot)  - 3,000 units
🔍 INSPECTION (1 lot)         - 2,800 units
🏭 IN_PRODUCTION (1 lot)      - 1,500 units
```

### Quality Performance
- **Average Defect Rate**: 0.79%
- **Best Performance**: CC-SS25-T001 (T-Shirt) - 0.4% defects
- **Needs Attention**: CC-SS25-SH001 (Shorts) - 1.8% defects

## Key Demo Features to Showcase

### 1. Multi-Factory Operations
Cordeiro Campos operates 4 facilities:
- Main production plant in Santo Tirso
- Specialized knitting unit in Guimarães
- Dyeing & finishing in Vila Nova de Famalicão
- Quality control lab in Porto

### 2. Product Variety
Demo includes various garment types:
- Knitwear (Sweaters) - 3 lots
- T-shirts and Polo Shirts - 2 lots
- Pants and Shorts - 2 lots
- Dresses and Blouses - 2 lots
- Jackets - 1 lot

### 3. Quality Workflow
- Lots in different stages of the quality pipeline
- Real-time inspection tracking
- Defect rate monitoring
- Approval workflows

### 4. Realistic Data
- Material compositions (cotton, wool, silk, polyester)
- Size specifications (XS - XXL)
- Portuguese factory locations
- Seasonal collections (AW25, SS25)

## Database Queries for Verification

### Check Tenant Setup
```sql
SELECT t.name, t.slug, c.name as client_name
FROM tenants t
JOIN clients c ON c.tenant_id = t.id
WHERE t.slug = 'cordeiro-campos';
```

### View All Lots
```sql
SELECT l.style_ref, l.garment_type, l.quantity_total, l.status, l.defect_rate
FROM lots l
WHERE l.tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
ORDER BY l.created_at DESC;
```

### Check Factory Assignments
```sql
SELECT f.name, f.city, COUNT(l.id) as lot_count
FROM factories f
LEFT JOIN lots l ON l.factory_id = f.id
WHERE f.tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
GROUP BY f.id, f.name, f.city;
```

### View Inspection Status
```sql
SELECT l.style_ref, l.status,
       CASE WHEN i.finished_at IS NOT NULL THEN 'Completed'
            WHEN i.started_at IS NOT NULL THEN 'In Progress'
            ELSE 'Not Started' END as inspection_status
FROM lots l
LEFT JOIN inspections i ON i.lot_id = l.id
WHERE l.tenant_id = '254226e3-a316-413e-aa05-d0dd47c8f855'
ORDER BY l.style_ref;
```

## Demo Scenarios

### Scenario 1: Quality Manager Review
**User**: quality@cordeirocampos.pt
1. Review overall quality metrics (0.79% avg defect rate)
2. Identify lot needing attention (CC-SS25-SH001 - 1.8% defects)
3. Check inspection status across all lots
4. Review factory performance

### Scenario 2: Inspector Workflow
**User**: inspector1@cordeirocampos.pt or inspector2@cordeirocampos.pt
1. View assigned inspections
2. Track in-progress inspection (CC-AW25-K003)
3. Review completed inspections
4. Access lot details and specifications

### Scenario 3: Admin Dashboard
**User**: admin@cordeirocampos.pt
1. Overview of all 4 factories
2. Production pipeline visibility (all statuses)
3. User management (4 users across 3 roles)
4. Client management (Cordeiro Campos profile)

## Setup Script

To re-run or update the demo:
```bash
python3 setup_cordeiro_campos_demo.py
```

The script is idempotent and checks for existing records before creating new ones.

## Notes

- **Duplicate Records**: Script was run multiple times initially; unique lots are identified by `style_ref`
- **Missing Features**: Individual piece tracking requires edge device setup
- **Defect Details**: Stored at lot level (defect_rate field) for this demo

## Support Files

- `setup_cordeiro_campos_demo.py` - Complete setup script
- `CORDEIRO_CAMPOS_SETUP_SUMMARY.md` - Detailed setup documentation
- `CORDEIRO_CAMPOS_QUICK_START.md` - This quick reference

---

**Ready for Demo**: ✅ All data created and verified
**Setup Date**: 2025-11-27
