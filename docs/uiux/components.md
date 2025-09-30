# Component Library

Token-driven primitives live under `apps/web/src/components/ui` and share consistent props, focus management, and dark-mode support. Each component accepts a `className` override, merges with tokenised defaults, and exposes sensible ARIA attributes.

## Controls

- **Button / IconButton** (`button.tsx`): Variants `primary`, `secondary`, `subtle`, `ghost`, `danger`, `link` with loading + icon slots. Accessible focus rings and disabled states.
- **Input / TextArea / Field** (`input.tsx`): Support start/end icons, helper/error copy, and labelled fields via the `Field` wrapper.
- **Select** (`select.tsx`): Headless UI Listbox with description/disabled support, keyboard navigation, arrow rotation, and dark styling.
- **DateInput / DateRangeInput** (`date-input.tsx`): Native date inputs skinned with tokens, optional calendar icon, and range constraints.
- **Tabs** (`tabs.tsx`): Headless UI Tab.Group with pill triggers, keyboard focus, and card-like panels.

## Surfaces

- **Card** (`card.tsx`): Composed header/content/footer/title helpers using neutral surfaces in light/dark modes.
- **EmptyState** (`empty-state.tsx`): Tokenised dashed panel with optional icon and primary/secondary CTAs.
- **Modal** (`modal.tsx`) & **ModalFooter**: Headless UI Dialog with focus-trap, ESC/overlay close, size presets, and semantic headers.
- **Sheet** (`sheet.tsx`): Sliding panel from any edge, reusing dialog semantics, with responsive widths.
- **ToastProvider / useToast** (`toast.tsx`): Context-based notifications, variant styling, auto-dismiss timers, and a portal viewport.

## Data

- **Table primitives** (`table.tsx`): `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`, `TableCaption` for responsive containers and hover/focus feedback.
- **Pagination** (`pagination.tsx`): Numbered pager with ellipsis, keyboardable buttons, and previous/next helpers.

### Usage Guidelines

1. Always import from `@/components/ui` to keep the surface area consistent and enable future platform swaps.
2. Prefer token-backed classes (`bg-primary-600`, `rounded-lg`) over inline styles; components expose `className` for fine-tuning.
3. Wrap app roots with `ToastProvider` to enable `useToast()` and toasts—place it near the top-level layout.
4. Combine `Field` with controls for forms so labels, helper text, and errors stay aligned and accessible.
5. For sheets/modals, control open state at the parent and pass `onClose`. Use `initialFocus` on `Modal` when focusing a primary action.

These primitives are lightweight (Headless UI only) and ready to backfill existing screens before layering business-specific patterns.
