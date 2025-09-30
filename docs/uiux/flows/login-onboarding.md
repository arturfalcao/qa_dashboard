# Login & Onboarding Flow

## Current Experience

1. User hits `/login` and sees marketing hero + credential copier.
2. Form submission triggers `apiClient.login`; upon success, client fetches tenant metadata and redirects based on role (operator vs. client workspace vs. admin email hard-code).
3. Errors surface as inline text, but success relies on blocking redirects and full page repaint; there is no loading indicator on redirect.
4. Demo credential copier copies `<email>\t<password>` to clipboard without feedback beyond a transient state.

```mermaid
flowchart TD
  A[Landing /login] --> B[Enter email/password]
  B --> C{Valid?}
  C -- No --> D[Inline error]
  C -- Yes --> E[Fetch tenant metadata]
  E --> F{Role routing}
  F -- Operator --> G[/operator]
  F -- Client roles --> H[/c/{tenant}/feed]
  F -- Admin email literal --> I[/admin]
```

## Pain Points

- Role routing is brittle (string comparison for admin email, no support for multi-tenant admins).
- No progressive disclosure of next steps post-login; users land on live feed without orientation.
- Demo credential copier lacks accessibility (no button focus, screen reader feedback, or password toggle).
- No MFA or session expiration warnings; refresh token logic hidden from UI.

## Proposed Experience

1. Introduce an onboarding hand-off screen (`/welcome`) that summarises tenant status, active alerts, and primary CTA (e.g. “Review Live Feed”).
2. Replace hard-coded admin email check with role-based permissions (e.g. `SUPER_ADMIN`).
3. Add `AppShell`-based auth layout with right panel for demo accounts, keyboard-friendly copy buttons (`aria-live` success toast).
4. Expose session status (expires in X) with ability to extend session using refresh token API.
5. Support SSO + MFA via magic link and show spinner/toast while routing to workspace.

```mermaid
flowchart TD
  A[/login] --> B[Authenticate]
  B --> C{Success?}
  C -- No --> D[Toast + inline error]
  C -- Yes --> E[Fetch tenant profile]
  E --> F[Determine landing context by role]
  F --> G[/welcome overview]
  G --> H{Choose CTA}
  H -- QA Ops --> I[/c/{tenant}/feed]
  H -- Exec --> J[/c/{tenant}/analytics]
  H -- Super Admin --> K[/admin]
```

## Implementation Notes

- Reuse new Button/Input tokens; create `AuthLayout` variant with `AppShell` header removed.
- Persist onboarding completion flag in user profile to skip `/welcome` when not needed.
- Add `useToast` success state on login and for clipboard copy to align with reduced-motion guidelines.
- Provide integration hooks for future SSO providers (e.g. configure via `.env`).
