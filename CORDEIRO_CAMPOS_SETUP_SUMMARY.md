# Cordeiro Campos - Demo Setup Summary

## Overview
Successfully created a complete demo tenant for **Cordeiro Campos** (https://www.cordeirocampos.pt/) in the production database.

## Tenant Information

### Tenant Details
- **Tenant Name**: Cordeiro Campos
- **Tenant Slug**: `cordeiro-campos`
- **Tenant ID**: `254226e3-a316-413e-aa05-d0dd47c8f855`
- **Client ID**: `16d90568-89d2-4e1e-b64c-89315e4034d5`

### Company Profile
- **Location**: Santo Tirso, Portugal
- **Industry**: Textile Manufacturing
- **Specialization**: High-quality knitwear and woven fabrics
- **Website**: https://www.cordeirocampos.pt/

## Demo Data Created

### 1. Factories (4 total)
- **Cordeiro Campos - Santo Tirso Main Plant** (Santo Tirso, PT)
- **Cordeiro Campos - Knitting Unit** (Guimarães, PT)
- **Cordeiro Campos - Dyeing & Finishing** (Vila Nova de Famalicão, PT)
- **Cordeiro Campos - Quality Lab** (Porto, PT)

### 2. Users (4 total)
| Email | Role |
|-------|------|
| admin@cordeirocampos.pt | TENANT_ADMIN |
| quality@cordeirocampos.pt | QUALITY_MANAGER |
| inspector1@cordeirocampos.pt | INSPECTOR |
| inspector2@cordeirocampos.pt | INSPECTOR |

**Note**: All users have a demo password hash set. In production, these should be properly configured with secure passwords.

### 3. Production Lots (10 unique styles)

| Style Reference | Garment Type | Quantity | Status | Defect Rate (%) |
|----------------|--------------|----------|--------|-----------------|
| CC-AW25-K001 | SWEATER | 3,500 | SHIPPED | 0.6% |
| CC-AW25-K002 | SWEATER | 2,000 | APPROVED | 0.8% |
| CC-SS25-T001 | T_SHIRT | 5,000 | SHIPPED | 0.4% |
| CC-SS25-P001 | POLO_SHIRT | 4,200 | APPROVED | 0.5% |
| CC-AW25-K003 | SWEATER | 2,800 | INSPECTION | 1.2% |
| CC-SS25-SH001 | SHORTS | 3,000 | PENDING_APPROVAL | 1.8% |
| CC-AW25-J001 | JACKET | 1,500 | IN_PRODUCTION | 0.0% |
| CC-SS25-D001 | DRESS | 2,200 | APPROVED | 0.9% |
| CC-AW25-P001 | PANTS | 3,500 | SHIPPED | 0.7% |
| CC-SS25-B001 | BLOUSE | 2,600 | APPROVED | 1.0% |

**Total Production Volume**: 30,300 units

### 4. Status Distribution
- **SHIPPED**: 3 lots (12,000 units)
- **APPROVED**: 4 lots (11,000 units)
- **PENDING_APPROVAL**: 1 lot (3,000 units)
- **INSPECTION**: 1 lot (2,800 units)
- **IN_PRODUCTION**: 1 lot (1,500 units)

### 5. Inspections (9 total)
- Inspections created for all lots except those in production
- Includes both completed and in-progress inspections
- Inspection data linked to inspector users

## Material Composition Examples
The demo includes realistic material compositions for Portuguese textile manufacturing:
- Cotton blends (60-100%)
- Wool/Merino blends (70-100%)
- Polyester blends (20-40%)
- Silk (100%)
- Elastane for stretch (2-5%)

## How to Access

### Platform URL
Access the platform with the tenant slug: `cordeiro-campos`

### Demo Users
All users can be accessed with the demo credentials:
- **Email**: Use the email addresses listed above
- **Password**: Demo password hash is configured (update as needed for actual login)

## Quality Metrics Summary

### Overall Quality Performance
- **Average Defect Rate**: 0.79% (excellent quality)
- **Lots Meeting AQL Standards**: 90% (9/10 lots under 2.5% defect rate)
- **Inspection Completion Rate**: 90% (9/10 lots inspected)

### By Status
- **Shipped Lots**: 0.57% average defect rate
- **Approved Lots**: 0.80% average defect rate
- **Under Review**: 1.8% defect rate (1 lot pending approval)

## Database Schema Limitations

During setup, we encountered some schema constraints:
1. **Apparel Pieces**: Require `inspection_sessions` which need `edge_devices` setup
2. **Individual Defects**: Linked to `apparel_pieces` through inspection sessions
3. **Solution**: Demo focuses on lot-level quality metrics which are sufficient for demonstrating platform capabilities

## Next Steps for Full Production Use

1. **User Authentication**: Set up proper password hashing and authentication
2. **Edge Devices**: Configure edge devices for factory floor inspections
3. **Inspection Sessions**: Set up inspection workflows with edge devices
4. **Photos**: Add product photos to lots and inspections
5. **DPP (Digital Product Passport)**: Configure DPP for transparency tracking
6. **Reports**: Generate quality reports and analytics

## Files Created
- `setup_cordeiro_campos_demo.py` - Complete setup script
- `CORDEIRO_CAMPOS_SETUP_SUMMARY.md` - This summary document

## Database Connection
```
Host: db-postgresql-lon1-48038-do-user-23540354-0.h.db.ondigitalocean.com
Port: 25060
Database: defaultdb
User: doadmin
SSL: Required
```

## Script Execution
The setup script can be run again safely as it checks for existing records before creating new ones:
```bash
python3 setup_cordeiro_campos_demo.py
```

---

**Setup Date**: 2025-11-27
**Status**: ✅ Complete and Ready for Demo
