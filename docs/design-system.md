# NousViz Design System

**Last verified:** 2026-04-14 (v0.1.5)

---

## Color Tokens

All colors use CSS custom properties defined in `apps/web/src/index.css`. Never hardcode hex values in components — use the semantic tokens.

| Token | Usage |
|-------|-------|
| `--background` | Page background |
| `--foreground` | Primary text |
| `--card` / `--card-foreground` | Card surfaces and text |
| `--primary` / `--primary-foreground` | Brand blue, CTAs, active states |
| `--secondary` / `--secondary-foreground` | Subtle backgrounds, secondary buttons |
| `--muted` / `--muted-foreground` | Disabled states, placeholder text |
| `--border` | Card borders, dividers |
| `--destructive` | Error states, delete buttons |

### Status colors (Tailwind utilities, not custom vars)
| Color | Usage |
|-------|-------|
| `text-green-400` / `bg-green-500/10` | Pass, connected, active |
| `text-yellow-400` / `bg-yellow-500/10` | Warning, attention needed |
| `text-red-400` / `bg-red-500/10` | Error, failure, critical |
| `text-blue-400` / `bg-blue-500/10` | Info, links |
| `text-orange-400` / `bg-orange-500/10` | Degraded, stale |

---

## Typography

Defined in `tailwind.config.ts` and `index.css`.

### Font families
| Class | Font | Usage |
|-------|------|-------|
| `font-display` | Instrument Sans 600 (Manrope 700 in Sovereign) | Headings, titles, labels |
| `font-body` | Instrument Sans 400 (Inter 400 in Sovereign) | Body text, descriptions |
| `font-mono-deck` | Geist Mono | Data values, code, IDs, timestamps |

### Text scale
| Class | Size | Usage |
|-------|------|-------|
| `text-page-title` | 32px / 600 | Page headings (rarely used — most pages use topbar title) |
| `text-section-header` | 20px / 600 | Section headings within a page |
| `text-card-title` | 16px / 600 | Card headings |
| `text-body` | 14px / 1.5 | Body text |
| `text-meta` | 12px / 1.4 | Metadata, timestamps, secondary info |
| `text-sm` | 14px | General small text (Tailwind default) |
| `text-xs` | 12px | Labels, badges, form hints |
| `text-[10px]` | 10px | Uppercase tracking labels |
| `text-[11px]` | 11px | Compact metadata in dropdowns |

### Heading patterns
- Page title: handled by Topbar `<h1>` — pages don't render their own `<h1>`
- Section heading: `<h2 className="font-display text-section-header text-foreground">`
- Card heading: `<h3 className="font-display text-sm text-foreground">`
- Uppercase label: `<span className="text-[10px] font-display uppercase tracking-wider text-muted-foreground">`

---

## Spacing

### Page layout
| Pattern | Class | Usage |
|---------|-------|-------|
| Page wrapper | `max-w-[1400px] space-y-6` | Standard page (datasets, alerts, data port) |
| Narrow page | `max-w-[1000px] space-y-6` | Settings, connections (single-column) |
| Dashboard | `max-w-[1200px] space-y-6` | Home overview |

### Component spacing
| Pattern | Class |
|---------|-------|
| Card padding | `p-5` (standard) or `p-4` (compact) |
| Card gap (grid) | `gap-3` or `gap-4` |
| Section gap | `space-y-6` |
| Within-card gap | `space-y-3` or `space-y-4` |
| Inline items | `gap-2` or `gap-3` |
| Form fields | `space-y-3` |

---

## Components

### Cards
```
bg-card rounded-lg border border-border p-5
```
- Always `rounded-lg` (not `rounded-xl`)
- Always `border border-border`
- Padding: `p-5` standard, `p-4` compact
- Status cards: add border color variant (e.g. `border-green-500/20 bg-green-500/5`)

### Buttons
| Variant | Class |
|---------|-------|
| Primary | `h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90` |
| Secondary | `h-9 px-4 rounded-md bg-secondary text-sm text-muted-foreground hover:text-foreground` |
| Destructive | `h-9 px-4 rounded-md bg-red-500/10 text-red-400 hover:bg-red-500/20` |
| Small | `h-8 px-3 rounded-md text-xs` (for filter pills, compact actions) |
| Icon | `h-9 w-9 rounded-md flex items-center justify-center` |

- Standard height: `h-9` (36px)
- Compact height: `h-8` (32px) — only for filter pills and inline actions
- Never mix `h-8` and `h-9` buttons in the same row

### Tables
```
<div className="bg-card rounded-lg border border-border overflow-hidden">
  <table className="w-full text-sm">
    <thead>
      <tr className="border-b border-border">
        <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
```
- Header: `text-xs uppercase tracking-wider text-muted-foreground`
- Cells: `px-4 py-3`
- Data values: `font-mono-deck text-foreground`
- Secondary values: `text-muted-foreground`

### Badges
```
<span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500/10 text-green-400">
```
- Always `rounded-full`
- Size: `text-[10px]` or `text-xs`
- Padding: `px-1.5 py-0.5` (small) or `px-2 py-0.5` (standard)

### Modals
```
<div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm">
  <div className="bg-card border border-border rounded-2xl w-full max-w-[540px] shadow-2xl">
```
- Overlay: `bg-black/70 backdrop-blur-sm`
- Container: `rounded-2xl` (exception to the `rounded-lg` rule — modals are larger)
- z-index: `z-[70]` for modals, `z-[80]` for modals-on-modals

### Empty states
```
<div className="py-20 text-center border border-dashed border-border rounded-lg">
  <Package className="w-10 h-10 text-muted-foreground mx-auto mb-4" />
  <p className="text-sm text-muted-foreground">No items yet.</p>
</div>
```

---

## Icons

All icons from **Lucide React**. Standard sizes:
| Context | Size |
|---------|------|
| Inline with text | `w-3.5 h-3.5` |
| Card header | `w-4 h-4` |
| Empty state | `w-8 h-8` or `w-10 h-10` |
| Hero | `w-6 h-6` |

---

## Responsive breakpoints

| Breakpoint | Usage |
|-----------|-------|
| `< md` (< 768px) | Mobile — sidebar hidden, burger-triggered drawer, single-column layout |
| `md:` (768px) | Show sidebar, switch to multi-column grids |
| `lg:` (1024px) | Wider grids (3-5 columns) |

### Mobile layout rules (B192)

- **Sidebar** hidden below `md:`, slides in as a fixed drawer on burger tap, closes on backdrop click or route change
- **Topbar** shows: burger button (md:hidden) → NousViz N lettermark (md:hidden) → page title (hidden on `< sm`, visible `sm:+`)
- **Page title** hidden on very small screens (`< sm`) to prevent crowding the topbar
- **Sub-nav tab strips** (Settings tabs, Plugin tabs) get `overflow-x-auto scrollbar-hide` so tabs scroll horizontally inside their row rather than pushing the page wider. Tab items get `whitespace-nowrap shrink-0`.
- **Main content area** has `overflow-x-hidden` to contain any child that tries to exceed viewport width.
- **Scroll-to-top** on every route change — a `<ScrollToTop />` component inside `<BrowserRouter>` calls `window.scrollTo(0, 0)` on `pathname` change. Prevents landing mid-page after navigation.
- **No `user-scalable=no`** — pinch-zoom preserved for accessibility.
- **Touch targets** ≥ 44×44 px (iOS HIG minimum) on all primary interactive elements in the topbar.
- **No horizontal page scroll** at any breakpoint. If content overflows, it scrolls inside its own container (`overflow-x-auto`), never the `<html>` body.

### Testing matrix

Verify on real iOS Safari (operator's primary mobile environment), not just DevTools emulation:

- iPhone 14 baseline: 375×812
- iPhone SE (smallest): 320×568
- Android typical: 360×800
- iPad (tablet): 768×1024 (at this breakpoint, sidebar appears)

---

## Page description pattern

Every page (except dashboard) has a description line below the topbar title:
```
<p className="text-sm text-muted-foreground font-body">
  Description of what this page does.
</p>
```

---

## Exceptions

| Component | Exception | Reason |
|-----------|-----------|--------|
| Modals | `rounded-2xl` | Visual distinction from cards |
| Charts | Hardcoded hex colors | Recharts requires hex, not CSS vars |
