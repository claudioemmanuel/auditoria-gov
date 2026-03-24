# Obsidian Color System — "Intelligence Vault" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the warm "Forensic Ledger" (beige/amber) palette with an Obsidian-inspired "Intelligence Vault" aesthetic — deep midnight purples in dark mode, cool purple-tinted white in light mode — across every file that touches color.

**Architecture:** Single source of truth stays in `globals.css` CSS custom properties (Tailwind v4 `@theme`). JS runtime color tables (graph nodes, edge types, role badges, entity types, event types) are updated to match. No new abstractions — minimal, targeted replacements only.

**Tech Stack:** Next.js 15, Tailwind CSS v4 (`@theme` syntax), CSS custom properties, React/TSX inline styles, `@xyflow/react`, Lucide icons.

---

## Design Direction

**Aesthetic:** Intelligence Vault — Obsidian-inspired knowledge graph aesthetic.
**DFII:** 14/15 (Excellent) — Impact: 5, Fit: 5, Feasibility: 5, Performance: 5, Consistency Risk: 3.
**Differentiation anchor:** Deep midnight `#0D0D17` background with electric violet `#8A63E8` accent. When screenshotted without the logo, it reads as a security/intelligence tool, not a generic SaaS dashboard.

---

## New Palette Reference

### Light Mode — "Parchment Vault"
| Token                  | Value     | Notes                            |
|------------------------|-----------|----------------------------------|
| `--color-bg`           | `#F5F5FC` | Ultra-subtle violet tint         |
| `--color-fg`           | `#0A0A1A` | Near-black with purple cast      |
| `--color-surface`      | `#EAEAF5` |                                  |
| `--color-border`       | `#CACAE0` |                                  |
| `--color-muted`        | `#5252A0` | 6:1 contrast                     |
| `--color-accent`       | `#6E3ED6` | Obsidian signature purple        |
| `--color-accent-dim`   | `#E8E0FA` |                                  |
| `--color-surface-base` | `#F5F5FC` |                                  |
| `--color-surface-card` | `#E2E2F0` |                                  |
| `--color-surface-subtle`| `#EBEBF8`|                                  |
| `--color-text-primary` | `#0A0A1A` |                                  |
| `--color-text-secondary`| `#3A3A70`|                                  |
| `--color-text-muted`   | `#6060A0` | 5.6:1 contrast                   |
| `--color-primary`      | `#0A0A1A` |                                  |
| `--color-secondary`    | `#3A3A70` |                                  |
| `--color-destructive`  | `#9B1616` | Keep (semantic, domain-critical) |
| `--color-accent-subtle`| `#E8E0FA` |                                  |
| `--color-critical`     | `#9B1616` | Keep                             |
| `--color-high`         | `#C94A0A` | Keep                             |
| `--color-medium`       | `#8A6400` | Slightly cooler amber            |
| `--color-low`          | `#1A6840` | Keep                             |
| `--color-success`      | `#1A6840` | Keep                             |
| `--color-warning`      | `#8A6400` |                                  |
| `--color-error`        | `#9B1616` | Keep                             |
| `--color-info`         | `#3848C8` | Indigo-blue                      |

### Dark Mode — "Midnight Vault" (Obsidian signature)
| Token                  | Value     | Notes                            |
|------------------------|-----------|----------------------------------|
| `--color-bg`           | `#0D0D17` | Deep midnight                    |
| `--color-fg`           | `#DCDDEE` | Catppuccin-inspired cool white   |
| `--color-surface`      | `#16162A` |                                  |
| `--color-border`       | `#2E2E50` |                                  |
| `--color-muted`        | `#9090C0` | 6:1 on dark bg                   |
| `--color-accent`       | `#8A63E8` | Lighter purple for dark bg       |
| `--color-accent-dim`   | `#1A0A38` |                                  |
| `--color-surface-base` | `#0D0D17` |                                  |
| `--color-surface-card` | `#1E1E35` |                                  |
| `--color-surface-subtle`| `#131325`|                                  |
| `--color-text-primary` | `#DCDDEE` |                                  |
| `--color-text-secondary`| `#A0A0C8`|                                  |
| `--color-text-muted`   | `#7070A8` | 6.0:1 contrast                   |
| `--color-primary`      | `#DCDDEE` |                                  |
| `--color-secondary`    | `#A0A0C8` |                                  |
| `--color-destructive`  | `#E05050` |                                  |
| `--color-accent-subtle`| `#1A0A38` |                                  |
| `--color-critical`     | `#E05050` |                                  |
| `--color-high`         | `#D46020` |                                  |
| `--color-medium`       | `#C89820` |                                  |
| `--color-low`          | `#30A060` |                                  |
| `--color-success`      | `#30A060` |                                  |
| `--color-warning`      | `#C89820` |                                  |
| `--color-error`        | `#E05050` |                                  |
| `--color-info`         | `#5870E0` |                                  |

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `web/src/app/globals.css` | Modify | CSS custom properties (core tokens + two React Flow rgba values) |
| `web/src/lib/design-tokens.ts` | Modify | SSR fallback hardcoded hex values |
| `web/src/components/GraphView.tsx` | Modify | `NODE_COLORS`, `EDGE_COLORS`, Handle + Background + MiniMap hardcoded values |
| `web/src/components/investigation/InvestigationCanvas.tsx` | Modify | `MINIMAP_NODE_COLOR`, arrow marker color, MiniMap `maskColor` |
| `web/src/components/EntityNetworkGraph.tsx` | Modify | `NODE_COLORS`, SVG stroke colors |
| `web/src/components/radar/RadarDetailPanel.tsx` | Modify | `ROLE_BADGE_STYLE` |
| `web/src/components/radar/DossierDetailPanel.tsx` | Modify | `ROLE_BADGE_STYLE` (duplicate) |
| `web/src/components/radar/RadarPreviewDrawer.tsx` | Modify | `ROLE_BADGE_STYLE` (duplicate) |
| `web/src/components/pages/CapituloPage.tsx` | Modify | `ENTITY_COL` |
| `web/src/components/pages/SinalPage.tsx` | Modify | `ENTITY_COL` |
| `web/src/components/pages/DossieRedePage.tsx` | Modify | `ENTITY_COL` |
| `web/src/components/pages/RadarDossierPage.tsx` | Modify | `EVENT_META` colors |
| `web/src/components/pages/DossieJuridicoPage.tsx` | Modify | Inline metric card colors |
| `web/src/components/ScoreBar.tsx` | Modify | Tailwind hardcoded classes → token-based |

---

## Task 1: Core CSS Tokens (`globals.css`)

**Files:**
- Modify: `web/src/app/globals.css`

- [ ] **Step 1: Replace the `@theme` light palette block**

  Replace everything inside `@theme { ... }` with:

  ```css
  @theme {
    --font-sans: 'DM Sans', sans-serif;
    --font-mono: 'IBM Plex Mono', monospace;

    /* Intelligence Vault — light palette */
    --color-bg:           #F5F5FC;
    --color-fg:           #0A0A1A;
    --color-surface:      #EAEAF5;
    --color-border:       #CACAE0;
    --color-muted:        #5252A0;
    --color-accent:       #6E3ED6;
    --color-accent-dim:   #E8E0FA;

    /* Severity */
    --color-critical:     #9B1616;
    --color-high:         #C94A0A;
    --color-medium:       #8A6400;
    --color-low:          #1A6840;

    /* Status */
    --color-success:      #1A6840;
    --color-warning:      #8A6400;
    --color-error:        #9B1616;
    --color-info:         #3848C8;

    /* Surface hierarchy */
    --color-surface-base:   #F5F5FC;
    --color-surface-card:   #E2E2F0;
    --color-surface-subtle: #EBEBF8;

    /* Typography variants */
    --color-text-primary:   #0A0A1A;
    --color-text-secondary: #3A3A70;
    --color-text-muted:     #6060A0;

    /* Semantic aliases */
    --color-primary:        #0A0A1A;
    --color-secondary:      #3A3A70;
    --color-destructive:    #9B1616;
    --color-accent-subtle:  #E8E0FA;

    /* ── Radius (zero — forensic ledger enforces sharp edges) ── */
    --radius-xs: 0px;
    --radius-sm: 0px;
    --radius-md: 0px;
    --radius-lg: 0px;
  }
  ```

- [ ] **Step 2: Replace the `html.dark` block**

  Replace everything inside `html.dark { ... }` with:

  ```css
  html.dark {
    --color-bg:           #0D0D17;
    --color-fg:           #DCDDEE;
    --color-surface:      #16162A;
    --color-border:       #2E2E50;
    --color-muted:        #9090C0;
    --color-accent:       #8A63E8;
    --color-accent-dim:   #1A0A38;

    /* Surface hierarchy */
    --color-surface-base:   #0D0D17;
    --color-surface-card:   #1E1E35;
    --color-surface-subtle: #131325;

    /* Severity — brighter for dark backgrounds */
    --color-critical:     #E05050;
    --color-high:         #D46020;
    --color-medium:       #C89820;
    --color-low:          #30A060;

    /* Status */
    --color-success:      #30A060;
    --color-warning:      #C89820;
    --color-error:        #E05050;
    --color-info:         #5870E0;

    /* Typography */
    --color-text-primary:   #DCDDEE;
    --color-text-secondary: #A0A0C8;
    --color-text-muted:     #7070A8;

    /* Semantic aliases */
    --color-primary:        #DCDDEE;
    --color-secondary:      #A0A0C8;
    --color-destructive:    #E05050;
    --color-accent-subtle:  #1A0A38;
  }
  ```

- [ ] **Step 3: Update the two hardcoded rgba values in the React Flow section**

  Find and replace:
  ```css
  box-shadow: 0 1px 3px rgba(12, 12, 10, 0.08);
  ```
  with:
  ```css
  box-shadow: 0 1px 3px rgba(13, 13, 23, 0.08);
  ```

  Find and replace:
  ```css
  filter: drop-shadow(0 4px 12px rgba(201, 74, 10, 0.20));
  ```
  with:
  ```css
  filter: drop-shadow(0 4px 12px rgba(110, 62, 214, 0.25));
  ```

- [ ] **Step 4: Verify build passes**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run lint && npm run build
  ```
  Expected: no errors.

- [ ] **Step 5: Commit**

  ```bash
  git add web/src/app/globals.css
  git commit -m "feat(ui): Intelligence Vault — replace Forensic Ledger tokens with Obsidian-inspired palette"
  ```

---

## Task 2: SSR Fallback Tokens (`design-tokens.ts`)

**Files:**
- Modify: `web/src/lib/design-tokens.ts`

- [ ] **Step 1: Replace `fallbackTokens` values**

  Replace the entire `fallbackTokens` object:

  ```ts
  const fallbackTokens: TokenSet = {
    bg:        "#F5F5FC",
    fg:        "#0A0A1A",
    surface:   "#EAEAF5",
    border:    "#CACAE0",
    muted:     "#5252A0",
    accent:    "#6E3ED6",
    accentDim: "#E8E0FA",
    critical:  "#9B1616",
    high:      "#C94A0A",
    medium:    "#8A6400",
    low:       "#1A6840",
    success:   "#1A6840",
    warning:   "#8A6400",
    error:     "#9B1616",
    info:      "#3848C8",
  };
  ```

  Also update the comment: `/** SSR fallback — Intelligence Vault light palette */`

- [ ] **Step 2: Verify build passes**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add web/src/lib/design-tokens.ts
  git commit -m "feat(ui): update SSR fallback tokens to Intelligence Vault palette"
  ```

---

## Task 3: Graph View Colors (`GraphView.tsx`)

**Files:**
- Modify: `web/src/components/GraphView.tsx`

- [ ] **Step 1: Replace `NODE_COLORS`**

  ```ts
  const NODE_COLORS: Record<string, string> = {
    person:  "#7C6AE0",  // violet — individual
    company: "#4A82D4",  // blue-indigo — company
    org:     "#3A90A0",  // teal — government organ
  };
  ```

- [ ] **Step 2: Replace `EDGE_COLORS`**

  ```ts
  const EDGE_COLORS: Record<string, string> = {
    compra_fornecimento:         "#4A82D4",  // blue-indigo
    agente_publico_favorecido:   "#E05050",  // red (risk)
    coparticipacao_evento:       "#7070A8",  // muted purple
    coparticipacao_fornecedores: "#9090C0",  // lighter muted
    coparticipacao_orgaos:       "#A080E0",  // purple
    sociedade:                   "#30A060",  // teal-green
    SAME_SOCIO:                  "#C89820",  // amber
    SAME_ADDRESS:                "#8090B0",  // slate-purple
    SHARES_PHONE:                "#7080A0",  // slate
    SAME_ACCOUNTANT:             "#8090B0",  // slate-purple
    SUBSIDIARY:                  "#8A63E8",  // violet
    HOLDING:                     "#8A63E8",  // violet
    same_cluster_entity:         "#D46020",  // orange-warning
  };
  ```

- [ ] **Step 3: Replace the Handle hardcoded color**

  Find:
  ```tsx
  style={{ background: "#4b5563", width: 8, height: 8, border: "none" }}
  ```
  Replace with:
  ```tsx
  style={{ background: "#2E2E50", width: 8, height: 8, border: "none" }}
  ```

- [ ] **Step 4: Replace the Background dots color**

  Find:
  ```tsx
  <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
  ```
  Replace with:
  ```tsx
  <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#2E2E50" />
  ```

- [ ] **Step 5: Replace the MiniMap fallback color**

  Find:
  ```tsx
  nodeColor={(n) => NODE_COLORS[(n.data as EntityNodeData).node_type] ?? "#6b7280"}
  ```
  Replace with:
  ```tsx
  nodeColor={(n) => NODE_COLORS[(n.data as EntityNodeData).node_type] ?? "#7070A8"}
  ```

- [ ] **Step 6: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add web/src/components/GraphView.tsx
  git commit -m "feat(ui): update GraphView node/edge colors to Intelligence Vault palette"
  ```

---

## Task 4: Investigation Canvas Colors (`InvestigationCanvas.tsx`)

**Files:**
- Modify: `web/src/components/investigation/InvestigationCanvas.tsx`

- [ ] **Step 1: Replace `MINIMAP_NODE_COLOR`**

  ```ts
  const MINIMAP_NODE_COLOR: Record<string, string> = {
    person:  "#7C6AE0",
    company: "#4A82D4",
    org:     "#3A90A0",
  };
  ```

- [ ] **Step 2: Replace arrow marker color**

  Find:
  ```ts
  color: "#94a3b8",
  ```
  Replace with:
  ```ts
  color: "#9090C0",
  ```

- [ ] **Step 3: Replace MiniMap maskColor**

  Find:
  ```tsx
  maskColor="rgba(247,248,252,0.75)"
  ```
  Replace with:
  ```tsx
  maskColor="rgba(13,13,23,0.75)"
  ```

- [ ] **Step 4: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add web/src/components/investigation/InvestigationCanvas.tsx
  git commit -m "feat(ui): update InvestigationCanvas colors to Intelligence Vault palette"
  ```

---

## Task 5: Entity Network Graph Colors (`EntityNetworkGraph.tsx`)

**Files:**
- Modify: `web/src/components/EntityNetworkGraph.tsx`

- [ ] **Step 1: Replace `NODE_COLORS`**

  Find:
  ```ts
  const NODE_COLORS: Record<string, string> = {
    person: "#3b82f6",
    company: "#10b981",
    org: "#8b5cf6",
  };
  ```
  Replace with:
  ```ts
  const NODE_COLORS: Record<string, string> = {
    person:  "#7C6AE0",
    company: "#4A82D4",
    org:     "#3A90A0",
  };
  ```

- [ ] **Step 2: Replace SVG edge stroke**

  Find:
  ```tsx
  stroke="#6b7280"
  ```
  Replace with:
  ```tsx
  stroke="#7070A8"
  ```

- [ ] **Step 3: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add web/src/components/EntityNetworkGraph.tsx
  git commit -m "feat(ui): update EntityNetworkGraph colors to Intelligence Vault palette"
  ```

---

## Task 6: Role Badge Styles (3 files)

These three files contain identical `ROLE_BADGE_STYLE` constants. Update all three.

**Files:**
- Modify: `web/src/components/radar/RadarDetailPanel.tsx`
- Modify: `web/src/components/radar/DossierDetailPanel.tsx`
- Modify: `web/src/components/radar/RadarPreviewDrawer.tsx`

The replacement `ROLE_BADGE_STYLE` to use in all three:

```ts
const ROLE_BADGE_STYLE: Record<string, React.CSSProperties> = {
  buyer:      { background: "rgba(74,130,212,0.12)",  borderColor: "rgba(74,130,212,0.35)",  color: "#7AAAF0" },
  supplier:   { background: "rgba(138,99,232,0.12)",  borderColor: "rgba(138,99,232,0.35)",  color: "#B090F8" },
  winner:     { background: "rgba(48,160,96,0.12)",   borderColor: "rgba(48,160,96,0.35)",   color: "#50D090" },
  bidder:     { background: "rgba(200,152,32,0.12)",  borderColor: "rgba(200,152,32,0.35)",  color: "#E8B840" },
  sanctioned: { background: "rgba(224,80,80,0.12)",   borderColor: "rgba(224,80,80,0.35)",   color: "#F08080" },
  owner:      { background: "rgba(212,96,32,0.12)",   borderColor: "rgba(212,96,32,0.35)",   color: "#F09050" },
  employee:   { background: "rgba(58,144,160,0.12)",  borderColor: "rgba(58,144,160,0.35)",  color: "#50C0D8" },
  manager:    { background: "rgba(110,62,214,0.12)",  borderColor: "rgba(110,62,214,0.35)",  color: "#A878F0" },
  _default:   { background: "rgba(112,112,168,0.12)", borderColor: "rgba(112,112,168,0.35)", color: "#9090C0" },
};
```

- [ ] **Step 1: Update `RadarDetailPanel.tsx`** — replace the `ROLE_BADGE_STYLE` block.

- [ ] **Step 2: Update `DossierDetailPanel.tsx`** — same replacement.

- [ ] **Step 3: Update `RadarPreviewDrawer.tsx`** — same replacement.

- [ ] **Step 4: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add web/src/components/radar/RadarDetailPanel.tsx web/src/components/radar/DossierDetailPanel.tsx web/src/components/radar/RadarPreviewDrawer.tsx
  git commit -m "feat(ui): update ROLE_BADGE_STYLE colors to Intelligence Vault palette"
  ```

---

## Task 7: Entity Color Tables in Page Components

**Files:**
- Modify: `web/src/components/pages/CapituloPage.tsx`
- Modify: `web/src/components/pages/SinalPage.tsx`
- Modify: `web/src/components/pages/DossieRedePage.tsx`

The replacement `ENTITY_COL` to use in all three:

```ts
const ENTITY_COL: Record<string, string> = {
  org:     "#3A90A0",  // teal
  company: "#4A82D4",  // blue-indigo
  person:  "#7C6AE0",  // violet
};
```

- [ ] **Step 1: Update `CapituloPage.tsx`** — replace `ENTITY_COL`.

- [ ] **Step 2: Update `SinalPage.tsx`** — replace `ENTITY_COL`.

- [ ] **Step 3: Update `DossieRedePage.tsx`** — replace `ENTITY_COL`.

- [ ] **Step 4: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add web/src/components/pages/CapituloPage.tsx web/src/components/pages/SinalPage.tsx web/src/components/pages/DossieRedePage.tsx
  git commit -m "feat(ui): update ENTITY_COL to Intelligence Vault palette in page components"
  ```

---

## Task 8: Timeline Event Colors (`RadarDossierPage.tsx`)

**Files:**
- Modify: `web/src/components/pages/RadarDossierPage.tsx`

- [ ] **Step 1: Replace `EVENT_META` colors**

  Find the `EVENT_META` block:
  ```ts
  const EVENT_META: Record<string, { Icon: ElementType; color: string; label: string }> = {
    licitacao:     { Icon: ShoppingCart,   color: "#3C8EA2", label: "Licitação"     },
    contrato:      { Icon: FileText,       color: "#a78bfa", label: "Contrato"      },
    sancao:        { Icon: ShieldOff,      color: "#F87171", label: "Sanção"        },
    transferencia: { Icon: ArrowRightLeft, color: "#FB923C", label: "Transferência" },
    emenda:        { Icon: Landmark,       color: "#34D399", label: "Emenda"        },
  };
  ```
  Replace with:
  ```ts
  const EVENT_META: Record<string, { Icon: ElementType; color: string; label: string }> = {
    licitacao:     { Icon: ShoppingCart,   color: "#4A82D4", label: "Licitação"     },
    contrato:      { Icon: FileText,       color: "#8A63E8", label: "Contrato"      },
    sancao:        { Icon: ShieldOff,      color: "#E05050", label: "Sanção"        },
    transferencia: { Icon: ArrowRightLeft, color: "#D46020", label: "Transferência" },
    emenda:        { Icon: Landmark,       color: "#30A060", label: "Emenda"        },
  };
  ```

- [ ] **Step 2: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add web/src/components/pages/RadarDossierPage.tsx
  git commit -m "feat(ui): update EVENT_META colors to Intelligence Vault palette"
  ```

---

## Task 9: Metric Card Colors (`DossieJuridicoPage.tsx`)

**Files:**
- Modify: `web/src/components/pages/DossieJuridicoPage.tsx`

- [ ] **Step 1: Replace the inline metric array colors**

  Find:
  ```tsx
  { label: "Total Hipoteses", val: hypotheses.length, color: "#a78bfa" },
  { label: "Leis Referenciadas", val: uniqueLaws, color: "#34D399" },
  { label: "Tipologias Ativas", val: activeTypologies, color: "#FB923C" },
  { label: "Sinais no Caso", val: data.signals.length, color: "#60A5FA" },
  ```
  Replace with:
  ```tsx
  { label: "Total Hipoteses", val: hypotheses.length, color: "#8A63E8" },
  { label: "Leis Referenciadas", val: uniqueLaws, color: "#30A060" },
  { label: "Tipologias Ativas", val: activeTypologies, color: "#D46020" },
  { label: "Sinais no Caso", val: data.signals.length, color: "#4A82D4" },
  ```

- [ ] **Step 2: Verify build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run build
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add web/src/components/pages/DossieJuridicoPage.tsx
  git commit -m "feat(ui): update DossieJuridico metric card colors to Intelligence Vault palette"
  ```

---

## Task 10: ScoreBar — Replace Hardcoded Tailwind Classes

**Files:**
- Modify: `web/src/components/ScoreBar.tsx`

- [ ] **Step 1: Replace Tailwind default color classes with token-based styles**

  Current file uses `bg-blue-500`, `bg-amber-500`, `bg-red-500`, `text-gray-600`, `bg-gray-200` which bypass the token system.

  Replace the entire component:

  ```tsx
  interface ScoreBarProps {
    label: string;
    value: number; // 0–100
    color?: "accent" | "warning" | "error";
  }

  export function ScoreBar({ label, value, color = "accent" }: ScoreBarProps) {
    const barColor = {
      accent:  "var(--color-accent)",
      warning: "var(--color-warning)",
      error:   "var(--color-error)",
    }[color];
    const clamped = Math.max(0, Math.min(100, value));
    return (
      <div className="flex flex-col gap-1">
        <div className="flex justify-between text-xs" style={{ color: "var(--color-text-muted)" }}>
          <span className="data-value">{label}</span>
          <span className="data-value">{clamped}/100</span>
        </div>
        <div className="h-2 w-full" style={{ background: "var(--color-surface-card)" }}>
          <div className="h-2" style={{ width: `${clamped}%`, background: barColor }} />
        </div>
      </div>
    );
  }
  ```

  > **Note:** The prop type changes from `"blue" | "amber" | "red"` to `"accent" | "warning" | "error"`. Callers need to be updated. Check for all usages first.

- [ ] **Step 2: Find all ScoreBar usages**

  ```bash
  grep -rn 'color="blue"\|color="amber"\|color="red"' /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web/src --include="*.tsx"
  ```

- [ ] **Step 3: Update each caller site** — replace `color="blue"` → `color="accent"`, `color="amber"` → `color="warning"`, `color="red"` → `color="error"`.

- [ ] **Step 4: Verify lint and build**

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run lint && npm run build
  ```
  Expected: no errors.

- [ ] **Step 5: Commit**

  ```bash
  git add web/src/components/ScoreBar.tsx
  git commit -m "feat(ui): migrate ScoreBar from hardcoded Tailwind colors to design tokens"
  ```

---

## Final Validation

- [ ] Run full lint + build:

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run lint && npm run build
  ```
  Expected: clean output, zero errors.

- [ ] Visual check: open the dev server and verify dark mode shows `#0D0D17` background and `#8A63E8` accent. Light mode shows `#F5F5FC` background and `#6E3ED6` accent.

  ```bash
  cd /Users/claudioemmanuel/Documents/GitHub/OpenWatch/openwatch/web && npm run dev
  ```

---

## Anti-patterns Avoided

- **No per-page color overrides** — the pattern removed in the previous session is NOT re-introduced.
- **No new CSS abstractions** — existing token system extended, not replaced.
- **No design-by-committee compromises** — one dominant tone (midnight purple), one accent (violet), one neutral system (cool purple-gray). No warm tones survive.
