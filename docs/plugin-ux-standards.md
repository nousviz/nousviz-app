# Plugin UX Standards

**Last updated:** 2026-04-12  
**Status:** Living document — update when a new pattern is established.

This document defines the expected UX patterns for the plugin system: how plugins appear to operators, what metadata drives which UI components, and how the install/uninstall/detail flows work. It is a companion to [plugin-architecture.md](plugin-architecture.md).

---

## 1. Plugin detail page

Every plugin in the catalog has a full-page detail view at:

- `/marketplace/:pluginId` — from the Marketplace
- `/plugins/:pluginId` — from the Installed Plugins page

Both routes render `PluginDetailPage.tsx`. The page loads from `GET /api/plugins/catalog` and filters by slug. If the plugin is not in the catalog (unlikely), it falls back to `GET /api/plugins/:id`.

### What the detail page shows

| Section | plugin.yaml field | Notes |
|---------|-------------------|-------|
| Name + badges | `display_name`, `publisher.verified`, `visibility`, `installed` | Verified = blue badge; Premium = orange; Installed = green |
| Version + byline | `version`, `publisher.name`, `license`, `category` | One line below the title |
| Short description | `description` | 100-word limit; shown on cards and at the top of the detail page |
| Long description | `long_description` | Full markdown; shown in "About this plugin" section |
| Tags | `tags` | Pill badges; used for search |
| Requirements | `requires` | Infrastructure dependencies: `postgres: true`, `clickhouse: true` |
| External connections | `connections[]` | Connection type, label, required/optional, description |
| Data tables | `databases.postgres.tables`, `databases.clickhouse.tables` | Tables this plugin creates and owns |
| Dashboards | `dashboards[]` | Tab names and labels |
| Datasets | `datasets[]` | Declared tables with labels and grain |
| Publisher | `publisher` | Name, verified badge, website, contact email |
| Links | `homepage`, `repository`, `changelog_url`, `support_url` | Button row at bottom |

### CTA logic

| State | Primary CTA | Secondary CTA |
|-------|-------------|---------------|
| Not installed, not premium | "Install plugin" | — |
| Not installed, premium | "Premium only" (disabled) | — |
| Installed | "Open" → `/plugin/:id/dashboards/:first` | "Uninstall" (opens UninstallPluginModal) |

After uninstall completes, the page navigates back to `/plugins`.

---

## 2. Marketplace page (`/marketplace`)

The marketplace is a card grid with three sections in fixed order:

1. **Installed** — plugins currently in `plugins/installed/` (green ring, green icon)
2. **Official** — `publisher.verified = true`, non-premium, not installed (primary blue border when `featured`)
3. **More plugins** — everything else

Cards show: name, version, publisher, short description, tags (up to 4), dashboard count, and an action button in the footer (Install / Installed+Trash / Premium).

Clicking a card navigates to `/marketplace/:pluginId`. The card footer action buttons (`Install`, trash) do not navigate — they act in place.

### Search and filter

Search filters by `display_name` and `description` (case-insensitive substring). Category filter matches `plugin.category`. The "Premium" category tab filters by `visibility === "public_premium" || "fully_private"`.

---

## 3. Installed plugins page (`/plugins`)

A simple list of active plugins (from `GET /api/plugins` — installed + community only, not catalog). Each row shows:

- Plugin icon, name, version, description
- **Details** button → `/plugins/:id` (plugin detail page)
- **Refresh** button (re-fetches the list)
- **Uninstall** button (opens UninstallPluginModal)

This page does not show catalog metadata (requires, connections, etc.) — click Details for the full view.

---

## 4. plugin.yaml metadata hierarchy

Fields by visual importance (what operators see first):

```
display_name          ← largest text, the name
description           ← one-paragraph summary, on cards and detail hero
long_description      ← full prose, detail page only
tags                  ← searchable pill badges
category              ← filter tab grouping
license               ← one word shown in the byline
version               ← shown everywhere
publisher.name        ← "by X" in bylines
publisher.verified    ← blue "Verified" badge
requires              ← infrastructure gates (shown prominently before install)
connections           ← what external APIs/DBs the plugin connects to
databases             ← what Postgres/ClickHouse tables it creates
dashboards            ← tab nav items on the plugin page
homepage              ← external link, detail page footer
repository            ← external link, detail page footer
changelog_url         ← external link, detail page footer
support_url           ← external link, detail page footer
```

**Minimum required for a useful catalog entry:**
`display_name`, `description`, `version`, `license`, `category`, `tags`, `visibility`, `publisher`, `repository`

**Minimum for the install flow to work:**
`repository` (for GitHub clone) + `databases` (for uninstall confirmation)

---

## 5. Annotations — archive vs. delete

The annotations system has two distinct delete paths:

| Action | Endpoint | Effect |
|--------|----------|--------|
| **Archive** | `PUT /annotations/:id { archived: true }` | Soft-delete. Row stays in DB, hidden from default list. Reversible. |
| **Delete (live row)** | `DELETE /annotations/:id` | Soft-delete (moves to archive). Shows as archived in "Show archived" view. |
| **Delete (archived row)** | `DELETE /annotations/:id?permanent=true` | Hard delete. Row removed from DB. Irreversible. |

The `deleteAnnotation(id, permanent?)` function in `apps/web/src/lib/annotations.ts` passes `?permanent=true` when called from an already-archived row.

UI confirmation:
- First click on Delete → `confirmDelete = true`, button label changes to "Confirm delete" with red styling
- Second click → executes the delete
- Clicking away (`onBlur`) resets the confirm state

---

## 6. What still needs building

| Item | Where | Why |
|------|-------|-----|
| Icon rendering | `PluginDetailPage`, `PluginCard` | `plugin.yaml icon` field is a Lucide icon name but the UI always renders `<Package />`. Should dynamically render the declared icon. Requires an icon registry or dynamic import. |
| Screenshot gallery | `PluginDetailPage` | `screenshots` field added to `_plugin_entry()` and skeleton but not yet rendered in the detail page. Add an image carousel when `screenshots[]` is non-empty. |
| Long description as Markdown | `PluginDetailPage` | Currently rendered as `whitespace-pre-line` plain text. Should use `react-markdown` + `remark-gfm` for proper heading/list/code rendering. |
| `requires` pre-install check | `plugins.py` | P17 ticket: marketplace install should check `requires` fields against actual platform capabilities before cloning. |
| Live badge counts | `Sidebar.tsx` | `navigation[].badge` field declared in spec and skeleton but not implemented. |
