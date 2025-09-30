# Design Tokens

The QA Dashboard UI now consumes a single source of truth for theming and component design located at `apps/web/src/styles/tokens.ts`. Tokens are authored in TypeScript, distributed to Tailwind via the config, and hydrated into CSS variables for runtime theming (light, dark, and motion preferences).

## Token Families

| Domain | Keys | Notes |
| --- | --- | --- |
| `color.{primary,secondary,accent,success,warning,error,neutral}.{50..900}` | 7-step palettes anchored in current brand blues with accent/feedback hues. `danger` is aliased to `error` for backward compatibility. |
| `space.{xs,sm,md,lg,xl,2xl,3xl}` | 4/8px-derived spacing scale driving layout rhythm and component padding. |
| `radius.{sm,md,lg,2xl}` | Corner radii for chips → surfaces, exposed through Tailwind `rounded-*`. |
| `shadow.{sm,md,lg}` | Depth elevations tuned for both light/dark contexts and exposed via CSS variables for non-Tailwind usage. |
| `font.{sans,mono}` | Stacks for primary UI typography and code/metrics contexts. |
| `text.{xs..3xl}`, `leading`, `tracking` | Type scale + rhythm for headings, labels, and dense data. |

The exported `colorCssVars` helper converts color tokens into CSS variable definitions for non-Tailwind consumers if needed later.

## Tailwind Integration

- Config migrated to TypeScript (`apps/web/tailwind.config.ts`) to consume tokens directly.
- `theme.extend.colors` maps each semantic palette to CSS variables (e.g. `bg-primary-500` → `var(--color-primary-500)`), keeping runtime theming in sync.
- Spacing, radius, shadows, typography, and font families extend Tailwind utilities so components can rely on shorthand classes instead of ad-hoc values.
- Dark mode now uses the class strategy (`darkMode: 'class'`). Applying `.dark` to the `<html>` root switches the CSS variables, so Tailwind utilities automatically pick up the new values.

## Base Styles & Reduced Motion

`apps/web/src/app/globals.css` hydrates the token set for both light and dark themes:

```css
:root { --color-primary-500: #3b82f6; ... }
.dark  { --color-neutral-50: #0f172a; ... }
```

- Body/background/text colors now reference surface and neutral tokens, ensuring consistent contrast across pages.
- Component primitives (`.btn`, `.card`, `.input`) consume tokenised colors, shadows, and radii.
- A global `prefers-reduced-motion` guard throttles animation and transition durations, keeping the experience accessible.

## shadcn/ui & Future Consumers

When shadcn/ui components are added, point its theme file to the same CSS variables (`--color-primary-500`, etc.) or import `tokens` to generate the required config. This keeps Radix-based primitives aligned without duplicating palette definitions.

## Usage Guidelines

- Prefer Tailwind utilities tied to tokens (e.g. `bg-primary-600`, `px-sm`, and `gap-md`) instead of raw hex/px values.
- For bespoke CSS, reference the variables (`color: var(--color-neutral-700)`) to remain theme-aware.
- When introducing new color semantics, extend the token map first, then surface via Tailwind. Avoid inline `style` overrides.

This foundation supports incremental rollouts of the new design system while keeping bundle size in check and honouring branding constraints.
