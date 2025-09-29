# Paco Interoperability Playbook

This guide summarizes how to demonstrate and deliver full interoperability between the Paco manufacturing network, the Pack and Polish QC platform, and Paco's downstream brand customers. It is designed as a talking track for the upcoming meeting with Paco and as an implementation checklist for the product and engineering teams.

## Objectives for Wednesday's meeting

1. **Show Paco that they can self-manage their client portfolio** – they need to create downstream customers, invite stakeholders, and scope data access without depending on our team.
2. **Prove end-customer visibility** – Paco's clients must be able to log in and see their orders, live QA evidence, and all packaged documentation.
3. **Highlight frictionless data exchange** – demonstrate how the platform keeps packaging, Paco, and the end customer in sync through APIs, dashboards, and exports.

## Multi-tenant contract between Pack & Polish and Paco

- Every Paco program is represented as a `Client` record with its own slug, logo, and tenant-specific data. The API already supports creating and updating clients via `POST /clients` and `PATCH /clients/:id`, guarded so only Pack & Polish admins (or Paco admins once provisioned) can run them.【F:apps/api/src/database/controllers/client.controller.ts†L10-L64】
- Authentication payloads include the tenant identifier, and the `ClientGuard` enforces that requests only see data scoped to their tenant. This guarantees isolation when Paco team members operate alongside Pack & Polish staff or when Paco exposes access to their end customers.【F:apps/api/src/auth/auth.service.ts†L35-L60】【F:apps/api/src/auth/client.guard.ts†L1-L19】
- We already seed a Paco tenant with branded metadata, factory network, and users (admin, ops, C-level, and viewer) so the meeting demo can start from a Paco persona immediately.【F:apps/api/src/database/services/seed.service.ts†L67-L127】【F:apps/api/src/database/services/seed.service.ts†L360-L382】

## Empowering Paco to onboard their own customers

1. **Create a new downstream brand:** From an admin session, call `POST /clients` with the brand name, slug, and optional logo. This provisions the tenant shell and ties future lots, inspections, and reports to that brand.【F:apps/api/src/database/controllers/client.controller.ts†L10-L64】
   ```http
   POST /clients
   {
     "name": "Luxury Brand X",
     "slug": "lux-brand-x",
     "logoUrl": "https://cdn.paco.example/lux-brand-x.png"
   }
   ```
2. **Add brand users with the correct role:** Use the dedicated provisioning endpoint to mint credentials and enforce the viewer role for downstream customers. The API now accepts either a `clientSlug` or a `clientId`, so Paco can integrate with whichever identifier their internal systems prefer (and even send both for extra safety). If both are provided the platform will verify they refer to the same tenant before proceeding.【F:apps/api/src/database/controllers/user.controller.ts†L1-L62】【F:apps/api/src/database/services/user.service.ts†L19-L120】
   ```http
   POST /client-users
   {
     "email": "qa.lead@lux-brand-x.com",
     "clientSlug": "lux-brand-x",
     "clientId": "c87d0d39-4c67-4a75-bd54-84e483bcf900",
     "roles": ["CLIENT_VIEWER"]
   }
   ```
   The response returns the temporary password that Paco can forward securely to the customer contact.
3. **Share scoped dashboards:** When a viewer logs in, the dashboard automatically routes them into the `/c/[clientSlug]` workspace that filters all queries by their tenant, ensuring they only see their own orders, inspections, and reports.【F:apps/web/src/app/c/[clientSlug]/layout.tsx†L1-L83】
4. **Delegate lifecycle operations where safe:** Paco admins retain elevated roles (ADMIN, OPS_MANAGER) so they can approve batches, generate reports, and manage factory assignments for each brand they operate.【F:apps/api/src/database/services/seed.service.ts†L360-L375】【F:apps/web/src/app/c/[clientSlug]/lots/page.tsx†L1-L66】

### Access guarantees for Paco's clients

- **Tenant isolation is automatic.** Every API request includes `clientId` metadata, and the client guard filters queries so a Paco brand can never see another brand's data—even when Paco HQ staff work inside the same session.【F:apps/api/src/auth/client.guard.ts†L1-L19】
- **Role-based UI shielding.** The App Router layout reads the role from the session and hides actions (approvals, editing suppliers, etc.) when the user is a `CLIENT_VIEWER`, ensuring the end customer can only observe, not mutate, production data.【F:apps/web/src/app/c/[clientSlug]/layout.tsx†L1-L83】
- **Credential hand-off is secure.** Temporary passwords are hashed before storage and never logged, but the plaintext is returned once so Paco can share it via their chosen secure channel.【F:apps/api/src/database/services/user.service.ts†L44-L107】
- **Per-tenant uniqueness.** The database enforces a unique constraint on `(clientId, email)`, guaranteeing that customer logins cannot bleed into another brand tenant.【F:apps/api/src/database/entities/user.entity.ts†L15-L38】
- **Operational traceability.** The event service captures production hand-offs, and the same infrastructure can be extended to fire access-grant events once Paco standardises their downstream workflows.【F:apps/api/src/database/services/event.service.ts†L1-L37】

## What the end customer experiences

Once Paco invites a brand contact with the viewer role, that customer can:

- **Monitor production lots** – filter by status or factory, inspect progress, and open the lot modal (read-only for viewers) to track approvals and readiness.【F:apps/web/src/app/c/[clientSlug]/lots/page.tsx†L1-L66】
- **Watch live QA evidence** – the Live Feed performs 5-second polling for inspections and events, rendering Enhanced Inspection Cards with annotated defect photos so customers can see packaging quality in near real time.【F:apps/web/src/app/c/[clientSlug]/feed/page.tsx†L1-L86】【F:apps/web/src/components/inspections/enhanced-inspection-card.tsx†L1-L124】
- **Download reports and photo books** – the Reports workspace groups generated PDFs by type, allows on-demand generation, and streams downloads via presigned URLs produced by the storage service.【F:apps/web/src/app/c/[clientSlug]/reports/page.tsx†L1-L120】【F:apps/api/src/storage/storage.service.ts†L1-L109】
- **Access sustainability & DPP data** – Paco can toggle Digital Product Passport pages that surface traceability metadata and attachments for each lot, extending transparency all the way to the final customer.【F:apps/web/src/app/dpp/[id]/page.tsx†L1-L160】【F:apps/api/src/dpp/dpp.service.ts†L1-L160】

## Demo flow for the meeting

1. **Login as Paco operations lead** – use the seeded credentials to show Paco-branded workspace immediately after authentication.【F:apps/api/src/database/services/seed.service.ts†L360-L372】
2. **Create a new downstream brand** – run a short API call (or use an admin UI stub) to add a sample luxury customer, highlighting how logo and slug branding appear instantly in the sidebar.【F:apps/api/src/database/controllers/client.controller.ts†L10-L64】
3. **Invite the brand contact** – demonstrate how assigning `CLIENT_VIEWER` results in a scoped experience: share the login flow, the tenant-aware layout, and the restricted actions versus Paco's admin screen.【F:apps/api/src/auth/auth.service.ts†L35-L60】【F:apps/web/src/app/c/[clientSlug]/layout.tsx†L1-L83】
4. **Walk through the customer portal** – navigate Lots, Live Feed, Reports, and a DPP page to show orders, imagery, documentation, and sustainability evidence all synchronized.【F:apps/web/src/app/c/[clientSlug]/lots/page.tsx†L1-L66】【F:apps/web/src/app/c/[clientSlug]/feed/page.tsx†L1-L86】【F:apps/web/src/app/c/[clientSlug]/reports/page.tsx†L1-L120】【F:apps/web/src/app/dpp/[id]/page.tsx†L1-L160】
5. **Highlight data hand-offs** – close by describing how MinIO-backed storage keeps photo and report assets separated per client and distributed through presigned URLs, ensuring compliance and easy sharing.【F:apps/api/src/storage/storage.service.ts†L1-L109】

## Next steps after the meeting

- Automate a UI for client and user provisioning so Paco can perform steps 1–3 without Postman.
- Add audit trails for invitations and access grants so Paco can prove compliance to their own customers.
- Expand webhook support to notify Paco's ERP when lots reach specific gates, further tightening the integration loop.

With these talking points and the underlying capabilities already in the codebase, we can confidently commit to full interoperability between Pack & Polish, Paco, and the end customer network during Wednesday's presentation.
