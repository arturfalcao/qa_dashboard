# Navigation & Layout

The responsive shell lives in `apps/web/src/components/navigation/app-shell.tsx` and centralises the sidebar, topbar, command palette, and mobile navigation sheet.

## Structure

| Piece | Responsibility |
| --- | --- |
| `AppShell` | Composes topbar + sidebar, provides skip link, command palette hotkeys, and handles mobile sheet state. |
| `Navbar` | Displays brand, tenant badge, breadcrumbs, search shortcut, and accessible account menu. |
| `Sidebar` | Tokenised primary nav with active indicators, icons, and optional footer slot. |
| `CommandMenu` | Cmd/Ctrl+K palette powered by Headless UI dialog; filters navigation + contextual destinations. |
| `Sheet` | Reused drawer for mobile navigation (`side="left"`). |

Example usage lives under `apps/web/src/app/(shell)/navigation-demo/page.tsx` and is reachable at `/navigation-demo` once authenticated.

## Key Behaviours

- **Responsive shell**: Desktop shows a fixed sidebar; mobile collapses into a sheet triggered from the topbar hamburger button (`IconButton`).
- **Breadcrumbs**: `Navbar` accepts a `BreadcrumbItem[]` so layouts can communicate hierarchy (`Workspace → Lots`). Defaults fall back to pathname-derived labels.
- **Keyboard support**: Skip link, ESC to close menus, Cmd/Ctrl+K opens the command palette, focus-visible styling on nav links.
- **Accessibility**: Landmark roles (`nav`, `header`, `main`), `aria-current` for active links, focus traps within modal/sheet, and an accessible account dropdown.

## Implementing in Layouts

1. Gather navigation items with absolute hrefs and icons (`SidebarItem[]`). Reuse role logic to conditionally include sections.
2. Provide breadcrumbs + tenant label when rendering `<AppShell />`.
3. Supply supplemental actions via `actions` and observability/help text via `sidebarFooter`.
4. To extend the command palette, merge additional destinations into the `navigation` array or inject future entity-specific handlers.

This foundation keeps layout concerns isolated, enabling future integrations (global search, quick actions) without rewriting every page layout.
