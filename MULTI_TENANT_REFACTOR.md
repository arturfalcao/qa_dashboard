# Multi-Tenant Architecture Refactor

## Overview

This refactor implements a proper multi-tenant architecture by separating **Tenants** (organizations using the system) from **Clients** (customers of those tenants).

## Problem

Previously, the `clients` table was being used to represent both:
1. **Tenants** - Organizations using the QA Dashboard system (e.g., "Demo Client")
2. **Clients** - The actual customers/clients of those tenant organizations

This conflation made it impossible for a tenant to track multiple clients/customers.

## Solution

### Database Changes

#### New Structure

```
tenants (organizations using the system)
├── users
├── factories
├── lots
├── reports
├── events
├── dpps
└── clients (their actual customers)
    └── lots (assigned to specific clients)
```

#### Migration: `1759000000000-refactor-to-multi-tenant.ts`

**What it does:**

1. **Creates `tenants` table** - Replaces the concept of the old `clients` table
2. **Migrates existing data** - Copies all existing `clients` data to `tenants`
3. **Recreates `clients` table** - New structure for actual customer data with fields:
   - `tenant_id` (references tenants)
   - `name`
   - `contact_email`
   - `contact_phone`
   - `address`
   - `country`
   - `notes`
   - `is_active`

4. **Renames columns across all tables:**
   - `users.client_id` → `users.tenant_id`
   - `factories.client_id` → `factories.tenant_id`
   - `lots.client_id` → `lots.tenant_id` (also adds new `lots.client_id` for actual clients)
   - `events.client_id` → `events.tenant_id`
   - `notifications.client_id` → `notifications.tenant_id`
   - `reports.client_id` → `reports.tenant_id`
   - `dpps.client_id` → `dpps.tenant_id`

### Entity Changes

#### New Entities

- **`tenant.entity.ts`** - Represents organizations using the system

#### Updated Entities

All entities that previously referenced `Client` now reference `Tenant`:

1. **`client.entity.ts`** - Completely restructured:
   - Now represents actual customers of tenants
   - Belongs to a `Tenant`
   - Has contact information fields
   - Can be assigned to lots

2. **`user.entity.ts`**
   - `clientId` → `tenantId`
   - `client` → `tenant`

3. **`factory.entity.ts`**
   - `clientId` → `tenantId`
   - `client` → `tenant`

4. **`lot.entity.ts`**
   - `clientId` → `tenantId` (for tenant ownership)
   - Added new `clientId` (for assigning lots to actual clients)
   - `client` relation now references the new `Client` entity (tenant's customer)
   - Added `tenant` relation

5. **`report.entity.ts`**
   - `clientId` → `tenantId`
   - `client` → `tenant`

6. **`event.entity.ts`**
   - `clientId` → `tenantId`
   - `client` → `tenant`

7. **`notification.entity.ts`**
   - `clientId` → `tenantId`

8. **`dpp.entity.ts`**
   - `clientId` → `tenantId`
   - `client` → `tenant`

## Running the Migration

```bash
# Build the project
pnpm build

# Run migrations
npm run migration:run
```

## TODO: Code Updates Required

### Backend (API)

You'll need to update:

1. **Controllers** - Update all references from `clientId` to `tenantId`:
   - `apps/api/src/database/controllers/*.controller.ts`

2. **Services** - Update queries and business logic:
   - `apps/api/src/database/services/*.service.ts`

3. **DTOs** - Update data transfer objects:
   - Any DTOs that reference `clientId` should be updated to `tenantId`
   - Create new DTOs for the `Client` entity

4. **Authentication/Authorization** - Update tenant context:
   - JWT tokens or session data that store `clientId` should use `tenantId`
   - Multi-tenant data isolation logic

### Frontend (Web)

You'll need to update:

1. **API Client** - Update API calls:
   - `apps/web/src/lib/api.ts`
   - Any API calls using `clientId` should use `tenantId`

2. **Components** - Update UI components:
   - `apps/web/src/components/**/*.tsx`
   - Update any components that display or filter by client

3. **Pages** - Update page logic:
   - `apps/web/src/app/c/[clientSlug]/**/*.tsx`
   - Consider renaming route param from `clientSlug` to `tenantSlug`

4. **Types** - Update TypeScript interfaces:
   - Any types referencing `clientId` should use `tenantId`
   - Add new types for `Client` entity

5. **Forms** - Add UI for managing clients:
   - Create new forms/modals for adding tenant's clients
   - Update lot form to allow assigning to a client

## Benefits

1. **Proper separation of concerns** - Tenants and their clients are now distinct
2. **Scalability** - Each tenant can have multiple clients
3. **Data modeling** - Better represents real-world relationships
4. **Flexibility** - Can track client-specific information (contact details, etc.)

## Backward Compatibility

The migration preserves all existing data by:
- Moving existing `clients` data to `tenants`
- Maintaining all foreign key relationships
- Providing a rollback migration

## Example Use Cases

### Before
```
clients table:
- Demo Client (actually a tenant, but called "client")

lots table:
- lot_1 belongs to "Demo Client"
```

### After
```
tenants table:
- Demo Client (the organization using QA Dashboard)

clients table:
- PACO (Demo Client's actual customer)
- H&M (Demo Client's actual customer)

lots table:
- lot_1 belongs to tenant "Demo Client" and client "PACO"
- lot_2 belongs to tenant "Demo Client" and client "H&M"
```