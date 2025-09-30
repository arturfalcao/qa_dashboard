# UI/UX Audit

| Issue | Location | Severity | Fix proposal |
| --- | --- | --- | --- |
| No design tokens or scalable theme structure | apps/web/tailwind.config.js; apps/web/src/app/globals.css | High | Introduce central token source (color, typography, spacing) and wire into Tailwind/shadcn to eliminate ad-hoc values. |
| Desktop-only sidebar shell | apps/web/src/components/ui/sidebar.tsx | High | Refactor shell to support responsive collapse, keyboard navigation, and aria landmarks without altering routes. |
| Account menu lacks accessibility semantics | apps/web/src/components/ui/navbar.tsx | Medium | Add `aria-expanded`, `aria-controls`, focus trap, and keyboard bindings; extract to reusable dropdown primitive. |
| Blocking browser alerts for critical flows | apps/web/src/app/c/[tenantSlug]/feed/page.tsx; apps/web/src/components/inspections/enhanced-inspection-card.tsx | High | Replace `alert/confirm` with non-blocking toast + modal patterns tied into react-query for optimistic UX. |
| No dark mode or reduced motion strategy | apps/web/src/app/globals.css | High | Add class-based dark mode, prefers-reduced-motion guards, and ensure components consume semantic tokens. |
| Inconsistent layout spacing and container widths | apps/web/src/app/c/[tenantSlug]/layout.tsx; apps/web/src/app/operator/layout.tsx | Medium | Define layout primitives with shared gutters/max-widths and reuse spacing scale tokens. |
| Hard-coded English copy with no i18n hooks | apps/web/src/app/login/page.tsx and other screens | Medium | Introduce message catalog (en/pt-PT), wrap components with translation hooks, and externalise strings. |
| Dozens of bespoke spinner implementations | apps/web/src/app/page.tsx; apps/web/src/app/c/[tenantSlug]/lots/page.tsx; apps/web/src/components/analytics/*.tsx | Medium | Create a single `Loader` primitive respecting motion preferences and swap all inline `animate-spin` divs. |
| Modal lacks focus management and escape handling | apps/web/src/app/c/[tenantSlug]/feed/page.tsx (DefectReviewModal) | High | Wrap modal with focus-lock/ARIA labelling, support ESC/overlay dismissal, and manage portal stacking. |
| Event banners miss announcement semantics & contrast | apps/web/src/components/events/event-banner.tsx | Medium | Use `role="status"/"alert"`, tokenised colors with sufficient contrast, and smarter dismiss/auto-expire behaviour. |
| Data tables dense and non-responsive | apps/web/src/components/lots/lot-table.tsx | Medium | Introduce responsive table patterns (card view on mobile, column controls) and surface primary actions inline. |
| Buttons/inputs reimplemented per screen | apps/web/src/components/inspections/enhanced-inspection-card.tsx; apps/web/src/components/lots/lot-filters.tsx | Medium | Consolidate buttons, selects, form controls into shared UI kit with consistent states, icons, and tokens. |
