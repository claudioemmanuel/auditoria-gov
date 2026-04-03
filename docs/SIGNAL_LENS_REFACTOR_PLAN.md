# Signal Lens UI Refactor Plan

## Audit Summary

The current `apps/web` UI already has a solid system foundation:
- reusable design tokens in `src/app/globals.css`
- shared React components (`Button`, `Card`, `Input`, `Badge`, `PageHeader`, etc.)
- dark-first information architecture suited to investigative workflows

### Current strengths
- Clear hierarchy and readable content-heavy layouts
- Mature component abstractions
- Strong support for data tables, graphs, filters, and dossier/radar flows
- Good base for accessibility and product scalability

### Main mismatch with the new logo
The current identity is **amber/editorial watchdog** while the new logo is **teal/navy signal intelligence**.

This creates a visual disconnect in:
- brand accents
- logo mark usage
- typography tone
- focus/hover styling
- landing-page first impression

## Recommendation

Do **not** rewrite the UI system.
Refactor it in-place as a **brand-layer upgrade**.

## Phase Plan

### Phase 1 — Foundation (start now)
- Replace brand palette with deep navy + teal Signal Lens tokens
- Keep legacy token aliases for backward compatibility
- Shift key focus/hover/active states from amber to teal
- Update global fonts from editorial-feeling display styling to more precise product styling

### Phase 2 — Brand System
- Replace placeholder `Eye` logo with a dedicated `OpenWatchLogo` component
- Update sidebar, mobile header, footer, and landing hero branding
- Add subtle glow/lens treatment consistent with the generated logo

### Phase 3 — Core UI Components
- Refine `Button`, `Card`, `Input`, `Badge`, `PageHeader`
- Introduce `signal`, `outline`, and glass-panel variants where useful
- Reduce visual warmth and reinforce investigative clarity

### Phase 4 — Product Surfaces
- `Radar`
- `Coverage`
- map/network/dossier flows
- clustering, heatmaps, and signal visualization polish

## Immediate implementation scope
This first pass should touch:
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/globals.css`
- `apps/web/src/lib/design-tokens.ts`
- brand surfaces using the old placeholder icon

## Design guardrails
- dark-first always
- teal glow used sparingly
- preserve seriousness and institutional trust
- avoid overly “cyberpunk” or gimmicky motion
- keep charts and severity colors functionally distinct from brand colors
