# 🔐 Test Credentials for QA Dashboard

## Quick Start

All test users use the same password: **`password123`**

---

## Tenants & Users

### 1. Luxe Atelier (High-end Fashion)
**Tenant:** `luxe-atelier`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@luxe-atelier.com` | Full system access |
| Quality Director | `director@luxe-atelier.com` | Strategic QA oversight |
| Ops Manager | `manager@luxe-atelier.com` | Operations management |
| Inspector | `inspector@luxe-atelier.com` | Quality inspection |
| Operator | `operator@luxe-atelier.com` | Production floor operations |
| Viewer | `viewer@luxe-atelier.com` | Read-only access |

**Clients:** Hermès Europe, Roxy International

---

### 2. Urban Thread Co. (Contemporary Streetwear)
**Tenant:** `urban-thread`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@urban-thread.com` | Full system access |
| Quality Director | `director@urban-thread.com` | Strategic QA oversight |
| Ops Manager | `manager@urban-thread.com` | Operations management |
| Inspector | `inspector@urban-thread.com` | Quality inspection |
| Operator | `operator@urban-thread.com` | Production floor operations |
| Viewer | `viewer@urban-thread.com` | Read-only access |

**Clients:** Brunello Cucinelli, Yves Saint Laurent

---

### 3. Coastal Wear (Surf & Lifestyle)
**Tenant:** `coastal-wear`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@coastal-wear.com` | Full system access |
| Quality Director | `director@coastal-wear.com` | Strategic QA oversight |
| Ops Manager | `manager@coastal-wear.com` | Operations management |
| Inspector | `inspector@coastal-wear.com` | Quality inspection |
| Operator | `operator@coastal-wear.com` | Production floor operations |
| Viewer | `viewer@coastal-wear.com` | Read-only access |

**Clients:** Nike EMEA

---

### 4. Midnight Couture (Luxury Evening Wear)
**Tenant:** `midnight-couture`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@midnight-couture.com` | Full system access |
| Quality Director | `director@midnight-couture.com` | Strategic QA oversight |
| Ops Manager | `manager@midnight-couture.com` | Operations management |
| Inspector | `inspector@midnight-couture.com` | Quality inspection |
| Operator | `operator@midnight-couture.com` | Production floor operations |
| Viewer | `viewer@midnight-couture.com` | Read-only access |

**Clients:** Uniqlo Global

---

### 5. Rebel Stitch (Edgy Fashion)
**Tenant:** `rebel-stitch`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@rebel-stitch.com` | Full system access |
| Quality Director | `director@rebel-stitch.com` | Strategic QA oversight |
| Ops Manager | `manager@rebel-stitch.com` | Operations management |
| Inspector | `inspector@rebel-stitch.com` | Quality inspection |
| Operator | `operator@rebel-stitch.com` | Production floor operations |
| Viewer | `viewer@rebel-stitch.com` | Read-only access |

**Clients:** H&M Conscious

---

### 6. Eco Textile Lab (Sustainable Fashion)
**Tenant:** `eco-textile`

| Role | Email | Access Level |
|------|-------|--------------|
| Admin | `admin@eco-textile.com` | Full system access |
| Quality Director | `director@eco-textile.com` | Strategic QA oversight |
| Ops Manager | `manager@eco-textile.com` | Operations management |
| Inspector | `inspector@eco-textile.com` | Quality inspection |
| Operator | `operator@eco-textile.com` | Production floor operations |
| Viewer | `viewer@eco-textile.com` | Read-only access |

**Clients:** Patagonia

---

## Role Permissions Guide

### ADMIN
- Full access to all features
- User management
- System configuration
- Access all tenants' data

### QUALITY_DIRECTOR
- Strategic oversight
- View all reports and analytics
- Approve/reject quality standards
- Cannot modify users

### OPS_MANAGER
- Manage production operations
- Assign inspectors
- View/create lots and inspections
- Limited administrative access

### INSPECTOR
- Perform quality inspections
- Create defect reports
- View assigned lots
- Cannot modify lots or users

### OPERATOR
- Record production data
- View assigned tasks
- Basic inspection interface
- Limited system access

### CLIENT_VIEWER
- Read-only access
- View reports and dashboards
- Cannot create or modify anything
- Ideal for external stakeholders

---

## Testing Scenarios

### Scenario 1: Luxury Brand QA Flow
1. Login as `admin@luxe-atelier.com`
2. View Hermès Europe production lots
3. Check defect rates for cashmere items

### Scenario 2: Operator Workflow
1. Login as `operator@urban-thread.com`
2. Access operator dashboard
3. Perform quality inspections

### Scenario 3: Multi-role Testing
1. Login as different roles
2. Compare available features
3. Test permission boundaries

---

## Database Stats

- **Total Tenants:** 10
- **Total Clients:** 23
- **Total Factories:** 25
- **Total Production Lots:** 80
- **Total Users:** 51
- **Defect Types:** 26

---

## Quick Login Examples

```bash
# Example 1: Admin for luxury fashion
Email: admin@luxe-atelier.com
Password: password123

# Example 2: Inspector for streetwear
Email: inspector@urban-thread.com
Password: password123

# Example 3: Viewer for sustainable fashion
Email: viewer@eco-textile.com
Password: password123
```

---

## Scripts Reference

- **Generate Mock Data:** `python3 generate_mock_data.py`
- **Create Test Users:** `python3 create_test_users.py`

---

*Last updated: 2025-10-24*
