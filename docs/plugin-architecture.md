# NousViz Plugin Architecture

**Version:** 1.2 — authoritative for all v0.1.x development
**Status:** Canonical. Do not implement plugin features that contradict this document.

This document covers everything needed to build, integrate, and maintain plugins in NousViz:
the package format, the complete `plugin.yaml` schema, every extension point, plugin isolation
rules, how the install/uninstall lifecycle works, how the core platform discovers and loads plugin
code, the frontend integration model, and the rules for contributing to official plugin repos.

---

## Table of Contents

1. [Core principle](#1-core-principle)
2. [Plugin isolation model](#2-plugin-isolation-model)
3. [Plugin package structure](#3-plugin-package-structure)
4. [plugin.yaml — complete schema](#4-pluginyaml--complete-schema)
5. [Extension points](#5-extension-points)
   - 5.1 [API routes — api/routes.py](#51-api-routes--apiroutespy)
   - 5.2 [Sidebar navigation — plugin.yaml navigation](#52-sidebar-navigation--pluginyaml-navigation)
   - 5.3 [Data port — dataport.yaml](#53-data-port--dataportsyaml)
   - 5.4 [Insight cards — insights.yaml](#54-insight-cards--insightsyaml)
   - 5.5 [Dashboard specs — dashboards/*.yaml](#55-dashboard-specs--dashboardsyaml)
   - 5.6 [Sync scripts](#56-sync-scripts)
   - 5.7 [Plugin migrations — storage/migrations/](#57-plugin-migrations--storagemigrations)
6. [Cross-plugin data — the Data Explorer](#6-cross-plugin-data--the-data-explorer)
7. [Install lifecycle](#7-install-lifecycle)
8. [Uninstall lifecycle](#8-uninstall-lifecycle)
9. [Route loading model](#9-route-loading-model)
10. [Frontend integration model](#10-frontend-integration-model)
11. [Core vs. plugin boundary](#11-core-vs-plugin-boundary)
12. [Environment variables](#12-environment-variables)
13. [Official plugin development — branch and PR model](#13-official-plugin-development--branch-and-pr-model)
14. [Plugin starter template](#14-plugin-starter-template)
15. [Validation checklist](#15-validation-checklist)
16. [Security model](#16-security-model)

---

## 1. Core principle

**This repo ships zero plugin code.**

Plugin code lives in external repositories at `github.com/nousviz/plugin-{slug}`. This repo contains:

| Location | Purpose |
|----------|---------|
| `plugins/official/` | Marketplace catalogue — `plugin.yaml` stubs only, no code. Provides version tag and `requires:` metadata for the install flow. Only one stub per plugin; once a plugin is installed, the full copy in `plugins/installed/` takes precedence for all content lookups. |
| `plugins/installed/` | Populated at runtime by marketplace install — gitignored, never committed. Always takes precedence over `plugins/official/` stubs when serving dashboards, datasets, alerts, or manifests. |
| `plugins/community/` | Community-submitted manifests — code in author's repo |
| `plugins/utilities/` | Platform utility manifests — ClickHouse, Redis, etc. Installed as pre-requisites, not as analytics plugins. See section 4 (`requires:`). |
| `apps/api/src/plugin_loader.py` | Discovers installed plugins, registers their routes on startup and on install |

**Why:** Shipping plugin code in the core repo couples core release cycles to individual plugin teams, forces this repo to change every time a plugin is added or updated, and presents as bloatware to operators who don't use those plugins.

---

## 2. Plugin isolation model

**Plugins are fully isolated from each other.**

A plugin owns its own:
- API routes (under `/plugins/{slug}/`)
- Database tables (declared in `plugin.yaml databases`)
- SQL migrations (in `storage/migrations/`)
- Python dependencies (`requirements.txt`)
- Sync scripts

A plugin must **never**:
- Import Python modules from another plugin
- Read from or write to another plugin's database tables
- Call another plugin's API endpoints from its own backend code

**Why imports are forbidden:** If plugin A imports from plugin B's Python module and plugin B is uninstalled, the import fails at load time — which crashes the plugin loader and breaks every other installed plugin, not just plugin A.

**Why direct table access is forbidden:** Plugins may run their migrations in any order. A plugin querying another plugin's table creates a hidden runtime dependency: if the other plugin's table doesn't exist or its schema changes, the dependent plugin silently returns wrong data or raises unhandled errors. The correct mechanism is the Data Explorer (section 6).

**The only way plugins combine is through the Data Explorer, driven by the operator.**

---

## 2b. Runtime model and privilege boundary (v0.9.0)

**The plugin system is a two-process architecture with a Postgres role boundary and a Unix socket credential broker.**

### Processes

1. **API (`apps/api`, gunicorn)** — serves HTTP. Loads plugin routes at startup from `plugins/installed/{slug}/api/routes.py`. Holds `NOUSVIZ_ENCRYPTION_KEY` and connects as the high-privilege `nousviz` DB role.
2. **Worker (`apps/worker/src/run_jobs.py`, PM2)** — runs sync and hook subprocesses. Holds the same secrets as the API. Hosts the **credential broker** (new in v0.9.0) on a Unix domain socket at `<repo>/run/creds.sock`.
3. **Plugin subprocess** — what sync scripts and hook callables run inside. Spawned by the worker. Gets a minimal env: identity (plugin_id, run_id), socket path, one-shot broker token, non-secret connection fields. **No decryption key. No core DB password. No decrypted secrets in env.**

### How a plugin reads a credential (v0.9.0)

```
worker registers token T for plugin X
   ↓
subprocess starts, env has NOUSVIZ_CREDS_TOKEN=T
   ↓
plugin calls nousviz_sdk.get_credential("X", "password")
   ↓
SDK opens <repo>/run/creds.sock, sends AUTH T / PLUGIN X / GET
   ↓
broker (in worker process): validates T, decrypts credentials with NOUSVIZ_ENCRYPTION_KEY
   ↓
broker responds with JSON {password, api_token, ..., __db__}
   ↓
SDK caches in subprocess memory for its lifetime
   ↓
broker deletes T (single-use)
```

Subsequent `get_credential()` calls in the same subprocess hit the cache — no re-fetch.

### Postgres role matrix

Plugin subprocesses connect as `nousviz_plugin` (v0.9.0 migration 047). Not as `nousviz`.

| Scope | Access |
|-------|--------|
| This plugin's declared tables | full CRUD, granted at install |
| `job_runs`, `app_logs` | INSERT-heavy; write own runs and log events |
| `plugin_settings`, `schema_migrations`, `plugin_registry`, `plugin_modules` | SELECT (plugin_settings also writable) |
| `credentials`, `users`, `api_keys`, `deploy_keys`, `plugin_audit_log`, other plugins' tables | no access — `permission denied` |

A plugin attempting `SELECT * FROM credentials` or `DROP TABLE users` hits the Postgres permission system and fails loudly. The SDK boundary is enforced at the database, not by plugin-author convention.

### Observability

If your plugin's `api/routes.py` fails to import at API startup, the `GET /api/plugins/{id}` endpoint returns `load_status.routes_registered: false` with the exception class and message. The plugin detail page renders a red banner linking to `/system/logs`, where the full traceback lives under `source=plugin_loader`.

If your hook module fails to import, the worker's hook runner logs `source=hook_runner` with a hint pointing at the most common cause (wrong directory placement).

If your plugin's route raises a 500, the middleware logs the exception class, method, path, and traceback tail to `/system/logs` under `source=plugin_route` (rate-limited to 10/minute per endpoint).

### Failure modes plugin authors should expect

- `CredentialBrokerUnavailable` on standalone execution — don't run sync scripts manually against production. Use `nousviz plugin new` (v0.9.3) for a dev harness.
- `permission denied for table` — your plugin tried to touch a table outside its grant scope. Declare it in `databases.postgres.tables` if it's yours; use the Data Explorer if you need cross-plugin read.
- `ModuleNotFoundError: nousviz_sdk` — the SDK wasn't installed in the venv. Run `pip install -e ./sdk` (or re-run `scripts/setup.sh`).

---

## 3. Plugin package structure

Every installed plugin lives at `plugins/installed/{slug}/`. The slug is lowercase, hyphenated, matches the `name` field in `plugin.yaml`.

```
{slug}/
│
├── plugin.yaml                 # REQUIRED — manifest, schema in section 4
│
├── api/
│   └── routes.py               # Optional — FastAPI router(s) for this plugin's endpoints
│
├── src/
│   └── sync.py                 # Optional — ETL / data sync script
│
├── storage/
│   └── migrations/
│       ├── 001_initial.sql     # Optional — plugin-specific SQL, applied on install
│       ├── 001_initial_down.sql  # Required if 001_initial.sql exists — reverses it
│       └── 002_add_column.sql
│
├── dashboards/
│   └── overview.yaml           # Optional — dashboard tab specs (one file per tab)
│
├── datasets/
│   └── main.yaml               # Optional — query templates exposed via /api/query
│
├── alerts/
│   └── revenue_drop.yaml       # Optional — alert rule templates
│
├── dataport.yaml               # Optional — data port tab configuration
├── insights.yaml               # Optional — insight card SQL queries
├── requirements.txt            # Optional — Python dependencies installed on plugin install
└── README.md                   # Recommended — shown in marketplace plugin detail page
```

**Only `plugin.yaml` is required.** All other files are optional. The plugin loader checks for each file's existence before attempting to load it.

---

## 4. plugin.yaml — complete schema

```yaml
# ── Identity ─────────────────────────────────────────────────────────────────

name: my-plugin                  # REQUIRED. Lowercase, hyphenated slug. Must be globally unique.
display_name: My Plugin          # REQUIRED. Human-readable name shown in marketplace UI.
version: 1.0.0                   # REQUIRED. Semver. Bumped on every release.
description: >                   # REQUIRED. One paragraph. Shown in marketplace and plugin page.
  What this plugin does and why you would install it.
license: Sustainable Use         # REQUIRED. Values: MIT | Apache-2.0 | Sustainable Use | Commercial
icon: bar-chart-2                # REQUIRED. Lucide icon name. Used in sidebar and marketplace.
category: analytics              # REQUIRED. Values: analytics | content | monitoring | integration | productivity | compliance | premium | community | utility
type: utility                    # Optional. Set to "utility" for platform-services plugins (ClickHouse, future Redis/etc.) that other plugins can declare a capability requirement against. Regular analytics plugins omit this field.
tags: [tag1, tag2]               # REQUIRED. Used for marketplace filtering. Min 1 tag.
visibility: public               # REQUIRED. Values: public | public_premium | fully_private

# ── Publisher ────────────────────────────────────────────────────────────────

publisher:
  slug: nousviz                  # Publisher identifier. Used as namespace in marketplace.
  name: NousViz                  # Human-readable publisher name.
  website: https://nousviz.com
  contact_email: plugins@nousviz.com
  verified: true                 # Optional. Set only by NousViz for official plugins.

# ── Source ───────────────────────────────────────────────────────────────────

repository: https://github.com/nousviz/plugin-my-plugin
                                 # REQUIRED for public plugins. The git URL the marketplace
                                 # clones when a user installs this plugin.

homepage: https://nousviz.com/plugins/my-plugin
                                 # Optional. URL shown as "Learn more" in the marketplace card.

# ── Connections ──────────────────────────────────────────────────────────────
# External data source credentials this plugin needs.
# The core plugin settings UI generates a form from these fields.
# Values are stored encrypted in Postgres and exposed as env vars at runtime.
# Plugins only connect to THEIR OWN external data sources — never to other plugins.

connections:
  - name: source_api
    type: api_key                 # Values: mysql | postgres | clickhouse | api_key | oauth2 | http
    required: true
    env_prefix: HELLO_            # Env vars will be: HELLO_API_KEY, HELLO_BASE_URL
    label: Source API              # Shown as form section heading
    description: >                # Optional. Shown below the form section heading.
      API key for the external data source this plugin syncs from.
    fields:
      - { name: api_key,   label: "API Key",   type: password, required: true }
      - { name: base_url,  label: "Base URL",  type: text,     required: true, default: "https://api.example.com" }

# ── Databases ────────────────────────────────────────────────────────────────
# Tables this plugin creates and exclusively owns.
# Used by: uninstall confirmation UI (data impact warning).
# These tables belong to this plugin only — other plugins must not read from them.
# Cross-plugin data access happens only through the Data Explorer (see section 6).

databases:
  postgres:
    tables:
      - hello_items
      - hello_events

# ── Navigation ───────────────────────────────────────────────────────────────
# Sidebar nav entries this plugin contributes.
# Core Sidebar.tsx reads all installed plugins' navigation entries dynamically.
# No plugin is ever hardcoded in Sidebar.tsx.

navigation:
  - label: Starter Plugin           # Text shown in sidebar
    href: /plugin/starter-plugin       # /plugin/{slug} — singular, matches GenericPluginPage route
    icon: hand-wave               # Lucide icon name
    position: sidebar             # Only supported value: sidebar
    badge: items_count            # Optional. If set, sidebar queries GET /api/plugins/{slug}/badge/{badge}
                                  # and renders the returned count as a badge on the nav item.

# ── Dashboards ───────────────────────────────────────────────────────────────
# Tab definitions for the plugin page (/plugin/{slug}).
# Each entry maps to a dashboards/*.yaml file in the plugin package.
# GenericPluginPage renders all dashboards via DashboardRenderer — no frontend code needed.

dashboards:
  - name: overview                # Slug. Used in URL: /plugin/{slug}/overview
    label: Overview               # Tab label in UI
  - name: events
    label: Events

# ── Sync ─────────────────────────────────────────────────────────────────────

sync:
  script: src/sync.py             # Path relative to plugin root
  schedule: "0 */4 * * *"        # Cron expression. Worker uses this to schedule runs.
  supports_incremental: true      # If true, sync.py accepts --since argument for incremental runs.
  timeout_seconds: 3600           # Optional. Worker kills sync if it exceeds this. Default 3600.
```

### RBAC permissions — the permissions: field (B247, v0.9.10.6+)

`permissions:` binds your plugin's HTTP routes to per-plugin RBAC permission strings of the form `plugin.<slug>.<level>`. Operators see one row per (plugin × level) in `/system/permissions` and can grant/revoke per role without editing your code.

This is **distinct from** the capability registry described in `requires:` and `provides:` below — capability semantics are about install-time service availability ("clickhouse is present"), permissions are about who-can-call-what at request time.

See [Contributing a Plugin → Declaring permissions](contributing-a-plugin.md#declaring-permissions-b247-v09106) for the full schema with examples. Minimal version:

```yaml
permissions:
  default: read    # All plugin routes require viewer+ by default.
  routes:
    - path: /api/plugins/<slug>/admin/*
      level: admin
```

Plugins that omit `permissions:` fall back to the legacy method-derived defaults (`plugins.read` / `plugins.configure`) — flagged as "legacy" in the matrix UI so the operator knows the plugin author hasn't migrated yet.

### Infrastructure requirements — the requires: field

`requires:` declares what the plugin needs from the platform before it can install or run. Three kinds of requirement are supported:

```yaml
requires:
  # Capability requirements — checked against the utility plugin capability registry
  clickhouse: true               # a utility plugin with `provides: [clickhouse]` must be installed
  redis: true                    # another utility plugin must supply this (future example)

  # Postgres version
  postgres_version: "14"         # optional minimum Postgres version

  # Hardware requirements — validated by the plugin's install.sh at install time, not by the platform
  min_ram_mb: 4096
  min_disk_mb: 2048
  os: linux
```

**Capability requirements** are the most common. Any key other than the well-known postgres/hardware fields is treated as a capability name: the platform's install endpoint checks the capability registry (`GET /api/plugins/capabilities`) and blocks install until a utility plugin providing that capability is present. Utilities register their capabilities through the `provides:` field described below.

**What happens when a requirement is not met:**

The marketplace install endpoint calls `_validate_requires()` before cloning the plugin. If a required capability is missing, install returns:

```json
{
  "status": "requirement_not_met",
  "missing": [
    {
      "requirement": "clickhouse",
      "message": "This plugin requires ClickHouse. Install the ClickHouse utility plugin first."
    }
  ]
}
```

The marketplace UI shows this as a blocking dialog with a direct link to the matching utility plugin in the Utilities section.

Hardware fields (`min_ram_mb`, `min_disk_mb`, `os`) are **not** platform-enforced — they are validated by the utility's own `install.sh` script, since hardware checks are operator/host concerns and the platform doesn't know the target machine at install time.

### Platform utility plugins — plugins/utilities/

Some infrastructure components that analytics plugins depend on are themselves installable — ClickHouse is the primary example. These are declared as **utility plugins** in `plugins/utilities/`:

```
plugins/utilities/
├── clickhouse/
│   ├── plugin.yaml          # type: utility. Declares install/uninstall/health hooks and provides: [clickhouse].
│   └── scripts/             # install.sh, uninstall.sh, health.sh
└── redis/                   # Future example
    └── plugin.yaml
```

Utility plugins set `type: utility` in their manifest and appear in a dedicated "Utilities" section of the marketplace and in a dynamic "Utilities" section of the sidebar (when at least one utility is installed). Installing a utility plugin runs its `install_hook` script, registers its `provides:` capabilities in the in-process capability registry (accessible at `GET /api/plugins/capabilities`), and makes it available for analytics plugins to use via `requires: {capability_name}: true`.

#### Utility-specific manifest fields

```yaml
type: utility                   # Marks this plugin as a utility
provides:                       # Capabilities this utility registers.
  - clickhouse                  # Other plugins can `requires: {clickhouse: true}`.

install_hook: scripts/install.sh    # Required. Runs after clone + migrations.
uninstall_hook: scripts/uninstall.sh  # Required. Runs before plugin directory removal.
health_check: scripts/health.sh       # Required. Called by /api/health to report status.
```

Hook scripts receive these env vars:

| Env var | Set by | Purpose |
|---------|--------|---------|
| `NOUSVIZ_DIR` | platform | Absolute path to the repo root |
| `NOUSVIZ_REMOVE_DATA` | platform (uninstall only) | `1` if operator chose "delete data", `0` if "keep data" |

Utility uninstall hooks **must** honour `NOUSVIZ_REMOVE_DATA=1` by removing the utility's data directory under `{NOUSVIZ_DIR}/data/{slug}/`. When unset or `0`, preserve it so reinstall picks up existing data.

Health hooks must output JSON on stdout: `{"ok": bool, "version": "...", "error": "..."}`. `/api/health` surfaces this under `services.{slug}` so the topbar health dropdown and Connections page reflect utility status.

**This is the correct answer to "my plugin needs ClickHouse to be installed first":**
- The analytics plugin declares `requires: {clickhouse: true}`
- The install endpoint checks the capability registry (populated by installed utilities' `provides[]`)
- If no utility provides `clickhouse`, install returns `requirement_not_met` and the UI shows a direct link to the ClickHouse utility

**What is NOT in plugin.yaml:**

| Field | Reason not supported |
|-------|---------------------|
| `depends_on: [other-analytics-plugin]` | Analytics plugins are isolated from each other. Cross-plugin data flows through the Data Explorer at operator discretion, not via a dependency declaration. |
| `conflicts_with` | Not needed — isolated plugins cannot conflict at the code level. |

---

## 5. Extension points

### 5.1 API routes — api/routes.py

The plugin loader imports `api/routes.py` from each installed plugin on startup and after install. The file must export a `router` (FastAPI `APIRouter`).

```python
# plugins/installed/starter-plugin/api/routes.py

from fastapi import APIRouter, HTTPException
from apps.api.src.db import get_pg_conn

router = APIRouter()

@router.get("/plugins/starter-plugin/items")
async def list_items(limit: int = 50):
    """List recent items. Only reads from hello_items — this plugin's own table."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, status, created_at FROM hello_items "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return {"items": rows}
```

**Path convention — strictly enforced:**

```
CORRECT:  /plugins/starter-plugin/items
CORRECT:  /plugins/starter-plugin/items/{id}
CORRECT:  /plugins/starter-plugin/health-check

WRONG:    /items                ← collides with core namespace
WRONG:    /api/items            ← collides with core /api/* namespace
WRONG:    /hello/items          ← not under /plugins/{slug}
```

All plugin routes must be under `/plugins/{slug}/`. Core routes (`/api/health`, `/api/alerts`, `/api/connections`, etc.) are reserved. If a plugin's router has no `/api` prefix, the platform silently adds it — so a route declared as `/plugins/my-plugin/items` becomes `/api/plugins/my-plugin/items`. Routes under a different prefix (e.g. `/go/`, `/site/`) must use `extra_routers`.

**Extra routers** — for routes that need a different prefix (redirect handlers, public pages):

```python
redirect_router = APIRouter()

@redirect_router.get("/go/{code}")
async def handle_tracking_redirect(code: str):
    # Tracking link redirect — must be at root for short URLs
    ...

extra_routers = [
    # (name, router, include_router_kwargs)
    ("redirect_router", redirect_router, {}),           # mounted at root with no prefix
]
```

`extra_routers` is a list of `(name, router, kwargs)` tuples where `kwargs` is passed to `app.include_router()`. Use sparingly — only for routes that structurally cannot be under `/plugins/{slug}/`.

**Widget routes (deprecated)** — `api/widgets.py` is recognized by the plugin loader but no plugins currently ship widgets. This extension point may be removed in a future version. If you need widget-style endpoints, add them to `api/routes.py` instead.

### 5.2 Sidebar navigation — plugin.yaml navigation

Core `Sidebar.tsx` fetches the installed plugin list and renders navigation entries declared in each plugin's `plugin.yaml`. No plugin is ever hardcoded in the sidebar.

```yaml
# In plugin.yaml
navigation:
  - label: Starter Plugin
    href: /plugin/starter-plugin       # /plugin/{slug} — singular, matches GenericPluginPage
    icon: hand-wave
    position: sidebar
```

The sidebar renders these entries after the core nav items (Dashboard, Alerts, Datasets, Insights).

**Badge support** — if a navigation entry declares a `badge` key, the sidebar queries `GET /api/plugins/{slug}/badge/{badge_name}` and renders the count:

```python
# In the plugin's routes.py
@router.get("/plugins/starter-plugin/badge/items_count")
async def items_badge():
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM hello_items WHERE status = 'active'")
        return {"count": cur.fetchone()[0]}
```

### 5.3 Data port — dataport.yaml

The core Data Port view (`/data-port`) scans `plugins/installed/*/dataport.yaml` at request time. Any plugin can contribute read-only table views without core code changes.

```yaml
# plugins/installed/starter-plugin/dataport.yaml

tabs:
  - id: items
    label: Items
    table: hello_items            # Must be a table this plugin owns (declared in plugin.yaml databases)
    columns:
      - { key: id,          label: ID,      type: text }
      - { key: name,        label: Name,    type: text }
      - { key: status,      label: Status,  type: badge,
          values: { active: green, inactive: grey, archived: red } }
      - { key: created_at,  label: Date,    type: datetime }
    default_sort: created_at DESC
    page_size: 50
    filters:
      - { key: status,      label: Status,  type: select, options: [active, inactive, archived] }
      - { key: name,        label: Name,    type: text_search }

  - id: events
    label: Events
    table: hello_events           # Also owned by this plugin
    columns:
      - { key: event_type,  label: Type,   type: text }
      - { key: detail,      label: Detail, type: text }
      - { key: created_at,  label: Date,   type: datetime }
    default_sort: created_at DESC
    page_size: 100
```

**Column types:** `text` | `number` | `datetime` | `badge` | `boolean` | `json`

**Filter types:** `select` | `text_search` | `date_range` | `number_range`

**Rule:** A plugin's `dataport.yaml` may only reference tables declared in that plugin's `plugin.yaml databases` section. It must not reference tables owned by other plugins.

### 5.4 Insight cards — two tiers

The core Insights page (`GET /api/insights`) aggregates from two sources. Use whichever fits your plugin's needs.

---

#### Tier 1 — insights.yaml (simple SQL)

Drop an `insights.yaml` in your plugin package. Core runs each query and returns raw rows. Use this for simple count/sum/status queries.

```yaml
# plugins/installed/cloudflare/insights.yaml

queries:
  - id: zone_summary
    label: Zone Traffic Summary
    description: Request volume per zone over the last 24 hours
    sql: >
      SELECT zone_name,
             sum(requests) AS requests_24h,
             sum(threats) AS threats
      FROM cf_daily_metrics
      WHERE date >= now() - interval '1 day'
      GROUP BY zone_name
      ORDER BY requests_24h DESC
      LIMIT 10
    fallback_empty: true
    # fallback_empty: true — return [] instead of 500 if table doesn't exist.
    # Always set this. The operator may have installed the plugin but not
    # yet completed sync setup.
```

**When to use Tier 1:** The insight is a straight SQL result — count something, sum something, find the top N. The frontend displays the raw rows.

---

#### Tier 2 — GET /plugins/{slug}/insights (programmatic)

If your insight requires multiple queries, conditional logic, week-over-week comparisons, or computed natural-language messages, implement a route in `api/routes.py`:

```python
# plugins/installed/cloudflare/api/routes.py

@router.get("/plugins/cloudflare/insights")
def cloudflare_insights():
    """Rich programmatic insights — multi-query, conditional logic."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        if not _table_exists(cur, "cf_zones"):
            return {"insights": []}

        insights = []
        cur.execute("SELECT id, name FROM cf_zones ORDER BY name")
        for zone_id, zone_name in cur.fetchall():
            cur.execute("""
                SELECT sum(requests) AS req_tw,
                       sum(threats) AS threats_tw
                FROM cf_daily_metrics
                WHERE zone_id = %s AND date >= CURRENT_DATE - 7
            """, (zone_id,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

            if row["threats_tw"] and row["threats_tw"] > 1000:
                insights.append({
                    "severity": "warning",
                    "plugin": "cloudflare",
                    "title": f"{zone_name}: {row['threats_tw']:,} threats this week",
                    "body": "Review your WAF rules in the Cloudflare dashboard.",
                })
        return {"insights": insights}
```

Core calls `GET /plugins/{slug}/insights` on every installed plugin and merges the results with Tier 1 insights. If the endpoint doesn't exist, it's silently skipped.

**When to use Tier 2:** Multi-step computation, conditional branching, natural-language generation, anything that needs more than one SQL query to produce a single insight card.

**Response shape** (required):
```json
{"insights": [
  {
    "severity": "critical|warning|info|good|tip",
    "plugin": "your-plugin-slug",
    "title": "Short title shown in the card header",
    "body": "Explanation paragraph.",
    "action": "Optional CTA label",
    "action_url": "/optional/deep/link",
    "metric": "optional_metric_id",
    "value": 42,
    "trend": "up|down|flat"
  }
]}
```

**Rule:** Insight queries must only read from this plugin's own tables. Do not query other plugins' tables.

**Rule:** Insight queries must only read from tables owned by this plugin (declared in `plugin.yaml databases`). They must not query tables owned by other plugins.

### 5.5 Dashboard specs — dashboards/*.yaml

Dashboard YAML specs define what data to query and how to render it. The frontend `DashboardRenderer` component reads these specs and renders charts and tables with no plugin-specific frontend code.

```yaml
# plugins/installed/starter-plugin/dashboards/overview.yaml

title: Starter Plugin Overview
refresh_seconds: 300

panels:
  - id: items_total
    type: stat
    label: Total Items
    query: >
      SELECT count(*) AS value
      FROM hello_items

  - id: events_chart
    type: line_chart
    label: Events Over Time
    query: >
      SELECT date_trunc('day', created_at) AS x, count(*) AS y
      FROM hello_events
      WHERE created_at >= now() - interval '30 days'
      GROUP BY x
      ORDER BY x
    x_key: x
    y_key: y

  - id: recent_items
    type: table
    label: Recent Items
    query: >
      SELECT name, status, created_at
      FROM hello_items
      ORDER BY created_at DESC
      LIMIT 20
    columns:
      - { key: name,       label: Name }
      - { key: status,     label: Status,  type: text }
      - { key: created_at, label: Created, type: datetime }
```

**Panel types:** `stat` | `line_chart` | `bar_chart` | `table` | `pie_chart` | `heatmap`

**Rule:** Dashboard queries must only read from this plugin's own tables.

**Date range pickers:** `DashboardRenderer` does not provide a built-in date range control. Plugin authors who need one declare a `custom` panel that renders the picker UI and re-issues queries against a parameterised plugin route. Hardcode the desired window in your panel queries (e.g. `WHERE created_at >= now() - interval '30 days'`) until you ship a custom picker. (Removed in v0.9.7.5 — B222.)

### 5.6 Sync scripts

The sync script's path comes from the manifest's `sync.script` field. Default is `src/sync.py`; override to anything (e.g. `src/<slug>_sync.py`) if you need to avoid `sys.modules` collisions across sibling plugins.

```python
# plugins/installed/starter-plugin/src/sync.py
# (path declared in plugin.yaml as sync.script: src/sync.py)

"""
Starter Plugin sync — pulls items and events from the source API into Postgres.
Called by: POST /api/plugins/starter-plugin/sync
Schedule: every 4 hours (see plugin.yaml sync.schedule)
Incremental: accepts --since for incremental runs
"""

import os, sys, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from apps.api.src.db import get_pg_conn


def run(since: str | None = None) -> dict:
    """
    Main sync entry point.

    Args:
        since: ISO datetime string for incremental sync. None = full sync.

    Returns:
        {"rows_synced": int, "errors": list[str]}
    """
    rows_synced = 0
    errors = []

    try:
        # ... pull from external source, insert into this plugin's tables only
        pass
    except Exception as e:
        errors.append(str(e))

    return {"rows_synced": rows_synced, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="ISO datetime for incremental sync")
    args = parser.parse_args()
    result = run(since=args.since)
    print(f"Synced {result['rows_synced']} rows. Errors: {result['errors']}")
```

**Convention:** `run()` is the entry point. The worker calls `run(since=last_run_time)` for incremental syncs. The function must always return the dict shape shown — the worker logs these values to the `alert_events` table.

### 5.7 Plugin migrations — storage/migrations/

Plugin-specific SQL migrations run during plugin install (`POST /api/plugins/{slug}/setup`). They follow the same naming convention as core migrations. Shipping a matching `_down.sql` for every up migration is **strongly recommended** — it expresses the plugin author's intended cleanup and runs automatically when an operator uninstalls with **Remove data**. It is not, however, required by the platform: cores ≥ v0.9.11.25.1 (B278 + B285) handle up-only plugins as a first-class supported pattern. See "When `_down.sql` is omitted" below.

```sql
-- plugins/installed/starter-plugin/storage/migrations/001_initial.sql
-- Starter Plugin: initial schema

CREATE TABLE IF NOT EXISTS hello_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hello_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT NOT NULL,
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS hello_items_status_idx ON hello_items(status);
CREATE INDEX IF NOT EXISTS hello_events_type_idx ON hello_events(event_type);
```

```sql
-- plugins/installed/starter-plugin/storage/migrations/001_initial_down.sql
-- Reverses 001_initial.sql

DROP INDEX IF EXISTS hello_events_type_idx;
DROP INDEX IF EXISTS hello_items_status_idx;
DROP TABLE IF EXISTS hello_events;
DROP TABLE IF EXISTS hello_items;
```

Plugin migrations are tracked in the same `schema_migrations` table as core migrations, with the plugin slug as a namespace prefix: `starter-plugin/001_initial`.

**Rules:**
- Up migrations: use `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`
- Down migrations: use `DROP TABLE IF EXISTS`, `DROP INDEX IF EXISTS`
- When you ship a down migration, drop every object the up migration created in reverse dependency order. If you omit a down migration entirely, core falls back to `DROP TABLE … CASCADE` against the manifest's declared tables — defensive but blunt; an explicit down file lets you control ordering and drop indexes / views / fkeys before tables.
- Do not create tables that shadow core table names (`users`, `alerts`, `annotations`, `dashboards`, `connections`, etc.)

**When `_down.sql` is omitted (cores ≥ v0.9.11.25.1):**

If you ship up-only migrations, the platform handles uninstall + reinstall correctly:

- **Uninstall with `remove_data=true`** — `_drop_declared_tables` (B278, v0.9.11.14) drops every table listed in the manifest's `databases.postgres.tables[]` via `DROP TABLE … CASCADE`. `_purge_schema_migrations_rows` (B285, v0.9.11.25.1) then clears the plugin's tracking rows so the next install can re-run the up files cleanly. Symmetric to what `_run_down_migrations` does for plugins shipping `_down.sql`.
- **Reinstall after a `remove_data=true` uninstall** — `_run_plugin_migrations` (B285) checks `pg_class` for the manifest's declared tables before honoring a tracking-row "already applied" claim. If a declared table is missing, the runner deletes the stale row, logs a warning, and re-runs the migration. The same defense-in-depth recovers from any path that drops tables out-of-band (manual `psql`, future cleanup tooling, partial restore).

The recommendation to ship `_down.sql` stands because it makes authoring intent explicit, gives you control over cleanup ordering, and works on cores predating v0.9.11.14. But "omitting it leaks tables" — which earlier docs claimed — is no longer true.

**Plugin role and runtime DDL (P203, v0.9.0):**

Plugin migrations execute as the `nousviz_plugin` role. The role has CRUD on the plugin's declared tables but **no `CREATE` on schema `public`**. This is by design — it scopes plugin code to its own tables and prevents privilege creep.

Practical consequence: do **not** attempt `CREATE TABLE IF NOT EXISTS` from inside plugin code at runtime as a stopgap when something looks broken. The role can't do it (`permission denied for schema public`), and the symptom usually points at a core bug (e.g. a migration was skipped due to a stale tracking row — the B285 scenario). When you observe tables-don't-exist behavior, file a core ticket via `nousviz-plugin-authoring/scripts/file-core-ticket.sh`. Don't paper over it from the plugin side.

### 5.8 Lifecycle hooks — `hooks:` (v0.8.6 / P118)

Plugins can declare Python callbacks for four lifecycle events. Each target
is a `module:function` path resolved inside the plugin's own directory.

```yaml
hooks:
  on_install:             hooks.lifecycle:on_install
  on_credentials_saved:   hooks.lifecycle:on_credentials_saved
  on_first_run_success:   hooks.lifecycle:on_first_run_success
  on_uninstall:           hooks.lifecycle:on_uninstall
```

Contract:

```python
from nousviz_sdk.hooks import HookContext, HookResult

def on_credentials_saved(ctx: HookContext) -> HookResult:
    # ctx.plugin_id, ctx.hook_name, ctx.payload, ctx.run_id
    return HookResult(ok=True, message="Credentials acknowledged")
```

- `on_install`, `on_credentials_saved`, `on_first_run_success` run **async**
  in the jobs-worker subprocess. A failing hook does not undo its trigger
  (the credentials were still saved). Write hooks to be idempotent.
- `on_uninstall` runs **inline** in the API process (capped at 30s) because
  the plugin directory is removed immediately after. Keep this hook fast.
- All hooks run with the S107-hardened `plugin_sync_env()` — no access to
  `NOUSVIZ_ENCRYPTION_KEY` or other core secrets.
- Hook outcomes are recorded in `job_runs` (`kind=hook:<plugin>:<name>`) and
  surfaced in `/system/logs` with source=`hook`.

Coexists with the bash `install_hook:` / `uninstall_hook:` fields — both
fire (bash first, Python hook enqueued/inline second).

### 5.9 Declarative actions — `actions:` (v0.8.6 / P119)

Operator-facing buttons declared in manifest, rendered by core, wired to a
plugin-owned endpoint.

```yaml
actions:
  - id: test_connection
    label: Test Connection
    slot: settings_tab_footer          # settings_tab_footer | plugin_page_header | dashboard_header
    style: primary                     # primary | secondary | danger
    endpoint: POST /api/plugins/my-plugin/test-connection
    confirm: false                     # false | "prompt string"
    icon: check-circle                 # lucide icon name (optional)
    disabled_when: no_credentials      # predicate allowlist
    # visible_when: backfill_running

  - id: start_backfill
    label: Start Backfill
    slot: settings_tab_footer
    style: primary
    endpoint: POST /api/plugins/my-plugin/backfill
    confirm: "Backfill ~1M rows? This can take 20–40 minutes."
```

**Slots** — `settings_tab_footer`, `plugin_page_header`, `dashboard_header`.
Three deliberate surfaces. Do not petition for more without a proven need.

**Endpoint ownership** — must start with `/api/plugins/{plugin_id}/` or
`/plugins/{plugin_id}/`. Cross-plugin endpoints are rejected at install.

**Predicate allowlist** (closed) — used in `disabled_when` / `visible_when`:

| Predicate | True when |
|-----------|-----------|
| `no_credentials` / `has_credentials` | Plugin has / doesn't have saved credentials |
| `sync_in_progress` / `backfill_running` | A `sync:<plugin>` run is queued/running/cancelling |
| `no_prior_sync` / `first_sync_success` | No successful runs yet / at least one success |

**Response contract** — endpoint returns JSON with any combination:

```json
{
  "toast": "Connected · 5 tables",
  "enqueue_job": "sync:my-plugin",
  "navigate": "/plugin/my-plugin/dashboards/overview",
  "refetch": true,
  "level": "info"
}
```

Non-200 responses show an error toast with the response body. Action
endpoints should return in <3s — use `enqueue_job` for long work.

### 5.10 Setup checklist — `setup_checklist:` (v0.8.6 / P121)

Declarative post-install guide. Each item's `done_if` predicate is
resolved server-side; core renders ✓ / ○ and auto-hides when complete.

```yaml
setup_checklist:
  show_until: all_done                 # all_done | credentials_saved | dismissed
  items:
    - id: save_creds
      label: Enter credentials
      done_if: credentials_saved
    - id: first_sync
      label: Run the first sync
      done_if: first_sync_success
    - id: verify_schedule
      label: Confirm automatic sync is scheduled
      done_if: schedule_active
```

**`done_if` allowlist** — shares with action predicates plus these:
`credentials_saved`, `last_test_success`, `schedule_active`.

**`show_until`**:
- `all_done` (default) — hide when every item resolves true
- `credentials_saved` — hide once credentials are saved
- `dismissed` — show until operator explicitly dismisses

Dismissal is per-browser (localStorage). Operators restore via a "Show
setup guide" link that appears once dismissed.

### 5.11 Built-in field types (v0.8.6 / P120)

In addition to `text | number | password | toggle | select`, connections
and settings fields now accept these rendering types:

| Type | Rendering | Validation |
|------|-----------|------------|
| `file` | Drag-drop zone + paste-text fallback. Optional `accept:` (browser filter) and `format_hint:` (`pem` / `json` — shows ✓ tick when content matches). 1 MB soft cap. | Content stored as a string (same as textarea). |
| `port` | Number input with `min=1 max=65535` and "Privileged port" badge when value < 1024. | Integer, 1..65535. |
| `cron` | Text input with a human-readable preview ("Every 6 hours") and preset pills. Unknown patterns show "Advanced: <raw>". | Five-field cron shape. |
| `url` | `<input type="url">`. Optional `scheme:` constraint (e.g. `scheme: mysql`). Warns if `user:pass@` syntax is present when scheme is set. | Browser URL parse + scheme check. |

```yaml
connections:
  - name: default
    fields:
      - name: host
        type: url
        scheme: mysql
        description: "Example: mysql.internal:3306"
      - name: port
        type: port
        default: 3306
      - name: ssl_ca
        type: file
        accept: ".pem,.crt"
        format_hint: pem
        secret: true          # v0.8.6.2 — see below
      - name: sync_schedule
        type: cron
        default: "0 */6 * * *"
```

Unknown `type:` values fall back to `text` with a warning — existing
manifests declaring a type we haven't shipped yet continue to render.

**Secret fields — `secret: true` (v0.8.6.2 / B124)**

Any field with `secret: true` is encrypted and stored in the `credentials`
table. Fields without `secret:` (and without `type: password`) are written
to the project `.env` file as a `KEY=VALUE` line.

- Use `secret: true` on anything sensitive: API tokens, OAuth secrets,
  PEM certificates (via `type: file`), signed JWTs, database passwords.
- `type: password` is **implicitly secret** — existing v0.8.5 plugins
  continue to work unchanged. Setting `secret: true` on a password field
  is redundant but harmless.
- Multi-line values (PEMs, JSON keys) MUST be marked `secret: true` —
  otherwise they land in `.env` on a single line and corrupt the file.

### 5.12 OAuth callbacks — `oauth.callback_handler` (B312, v0.10.3)

Third-party OAuth providers (Google, Slack, GitHub, ...) redirect the
user's browser to a fixed URL after the user authorizes. That redirect
**cannot** carry a NousViz session token, so core owns the callback URL
and dispatches to a plugin-declared handler. Plugins never need to
expose a public route of their own.

**Provider redirect URI to register**:
```
https://<your-host>/api/oauth/callback/<plugin-slug>
```

**Manifest opt-in** (`plugin.yaml`):
```yaml
oauth:
  callback_handler: "api.oauth:handle_callback"
```

The value is a `module:function` target. The dotted module path is
resolved **against the plugin's installed directory**, not via
`sys.path`. So `api.oauth` means the file at
`plugins/installed/<slug>/api/oauth.py` (or
`plugins/installed/<slug>/api/oauth/__init__.py` if you want a package).
The same applies whether the file is one level deep (`api.oauth`) or
nested (`integrations.google.oauth`).

**Import caveat**: the handler file is loaded by core with
`importlib.util.spec_from_file_location` using a synthetic, slug-scoped
module name. That means **relative imports inside your handler file
won't work** (`from .common import x` → `ImportError`). Use absolute
imports only: `from nousviz_sdk.oauth import OAuthCallbackResult`,
`import google_analytics_xyz`, etc. Plugin loader's `api/routes.py`
loads the same way; if `routes.py` works, the handler file will too.

**Start the flow from an authenticated plugin route**:
```python
# plugins/installed/<slug>/api/routes.py
from fastapi import Depends, Request
from starlette.responses import RedirectResponse
from nousviz_sdk import router_for_plugin, start_oauth_flow
# plugin's own auth dependency, e.g. _require_analyst

router = router_for_plugin("my-plugin")

@router.get("/auth/start")
def start(request: Request, identity: str = Depends(_require_analyst)):
    state = start_oauth_flow(
        plugin_slug="my-plugin",
        user_id=request.state.real_user_id,
        return_to="/plugin/my-plugin/settings",
        ttl_seconds=600,
    )
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri=https://{HOST}/api/oauth/callback/my-plugin"
        f"&response_type=code&scope=...&state={state}"
        "&access_type=offline&prompt=consent"
    )
    return RedirectResponse(auth_url, status_code=302)
```

**Handle the redirect**:
```python
# plugins/installed/<slug>/api/oauth.py
from nousviz_sdk.oauth import OAuthCallbackResult

def handle_callback(code: str, user_id: str) -> OAuthCallbackResult:
    tokens = _exchange_code_for_tokens(code)   # your code; provider-specific
    return OAuthCallbackResult(
        credentials={
            "refresh_token": tokens["refresh_token"],
            "access_token":  tokens["access_token"],
        },
        return_to=None,            # use what start_oauth_flow set
        credential_type="oauth2",
    )
```

Credentials in the returned dict land in the encrypted `credentials`
table for this plugin and can be read back from sync scripts and route
handlers via `nousviz_sdk.get_credential(...)`.

**State semantics**:
- One-shot — replays miss the consumed-state guard.
- Bound to `(plugin_id, user_id, return_to)` — a state minted for
  plugin A can't be replayed against plugin B's callback URL.
- 10-minute default TTL (matches typical provider auth-code TTL).
- Stored as SHA256 hash; raw token only exists in the URL bar.

**Failure UX** — all failure paths 302 back to `return_to` with
`?oauth_error=<code>`. The plugin's settings page reads the param and
renders an inline banner. Error codes: `invalid_request`,
`invalid_state`, `provider_error`, `unknown_plugin`, `no_handler`,
`handler_failed`. Handler exception messages are **not** echoed to the
user — only logged server-side. The `&detail=...` param carries a
short opaque token (e.g. `import`, `exchange`, `store`) for UI to
switch on, never a stack trace or provider-specific string.

**Open-redirect prevention** — core constrains `return_to` to
same-origin path-style URLs (must start with a single `/`). Anything
else falls back to `/`.

---

## 6. Cross-plugin data — the Data Explorer

**Plugins do not communicate with each other directly.**

The only mechanism for combining data from multiple plugins is the **Data Explorer** — an operator-facing surface that lets the operator pick a connection (plugin or registered Postgres connection), browse its tables, drill into rows, and save a view as a widget. Combine across plugins happens inside the Data Explorer's authoring flow; under the hood it compiles down to SQL that joins across plugin tables.

### Why the Data Explorer and not direct access

| Direct table access from plugin code | Data Explorer (operator-driven) |
|--------------------------------------|---------------------------------|
| Creates hidden runtime dependencies | Operator-controlled, explicit |
| Breaks on uninstall of the source plugin | Compiled views simply return no data if source tables are gone |
| Schema changes in source plugin break the consumer plugin | Compiled views are operator-maintained, not plugin code |
| Requires install ordering | No install order required |
| Plugin A must know Plugin B's schema at development time | Schema is discovered at runtime in the Data Explorer |

### What an operator does to combine data

An operator who wants to see Starter Plugin items alongside Cloudflare zone data opens the Data Explorer, picks Starter Plugin as the base connection, adds a Cloudflare join on a shared key, saves the resulting view as a widget, and drops it onto a dashboard. Neither plugin knows the other exists — the operator is the integration point.

### Plugin code must not attempt cross-plugin queries

```python
# WRONG — plugin A reading plugin B's table
cur.execute("SELECT * FROM hello_items")  # in cloudflare routes.py

# WRONG — plugin A importing plugin B's module
from plugin_routes_starter_plugin import get_items

# CORRECT — plugin A reads only its own tables
cur.execute("SELECT * FROM cf_zones")
```

The platform's validation checklist (section 15) includes a check for cross-plugin table access in routes and insight queries.

---

## 7. Install lifecycle

### Full sequence

```
User clicks Install in marketplace
    │
    ▼
POST /api/plugins/{slug}/install
    │
    ├── 1. Validate plugin_id (regex: ^[a-z0-9][a-z0-9\-_]{0,63}$)
    │
    ├── 2. Check already installed → return {status: "already_installed"} if so
    │
    ├── 3. Read official stub (plugins/official/{slug}/plugin.yaml) for version tag + requires
    │       Clone from GitHub: git clone --depth=1 --branch v{version} <repository> plugins/installed/{slug}/
    │       (official stubs contain only plugin.yaml — no code is ever copied from official/)
    │
    ├── 4. Validate plugin.yaml exists in installed package
    │
    ├── 5. pip install -r requirements.txt (if present), using .venv python
    │
    ├── 6. POST /api/plugins/{slug}/setup
    │       → runs storage/migrations/*.sql in filename order, tracked in schema_migrations
    │
    ├── 7. load_plugin_routes(app) — hot-adds routes to running FastAPI app
    │
    └── 8. Return {status: "installed", plugin: {...}, routes_active: bool}

Frontend receives success response
    │
    ├── Dispatch window event: nousviz:plugins-changed
    ├── Sidebar re-fetches /api/plugins → shows new nav entries from plugin.yaml
    └── Navigate to /plugin/{slug}
```

### Error states

| Error | Response |
|-------|----------|
| Invalid slug | 400 `{status: "invalid_plugin_id"}` |
| Already installed | 200 `{status: "already_installed"}` |
| Plugin not in registry or GitHub | 404 `{status: "not_found"}` |
| plugin.yaml missing in package | 500 `{status: "invalid_package"}` |
| Migration failed | 500 `{status: "setup_failed", error: "..."}` |

---

## 8. Uninstall lifecycle

### Uninstall confirmation — what the UI shows

The frontend shows a multi-step modal (`UninstallPluginModal`) before any files are deleted:

1. **Dependency warning** — lists any installed plugins that list this plugin in their marketplace description as a recommended companion. (Note: hard `depends_on` does not exist — this is informational only, sourced from the `recommended_with` field if present in `plugin.yaml`.)
2. **Data removal choice** — lists tables owned by the plugin and asks: keep data or drop it?
3. **Progress** — shows real-time uninstall steps
4. **Done + restart reminder** — routes remain active until API restart

### Backend sequence

```
DELETE /api/plugins/{slug}/install?remove_data={true|false}
    │
    ├── 1. Validate plugin_id
    ├── 2. Check plugin is installed → 404 if not
    ├── 3. If remove_data=true: run storage/migrations/*_down.sql in reverse order
    ├── 4. Run uninstall_hook (if declared) with env NOUSVIZ_REMOVE_DATA={0|1}
    ├── 5. Remove plugins/installed/{slug}/ directory
    ├── 6. Routes remain active until API restart (FastAPI limitation)
    └── 7. Return {status: "uninstalled", data_removed: bool, restart_required: true}

Frontend receives success response
    │
    ├── Show restart required banner (persists until /api/health confirms restart)
    ├── Dispatch nousviz:plugins-changed
    └── Sidebar re-fetches /api/plugins — nav entries for this plugin disappear
```

### Utility uninstall hooks — data directory contract

Utility plugins that maintain a filesystem data directory under `{NOUSVIZ_DIR}/data/{slug}/`
**must** honour the `NOUSVIZ_REMOVE_DATA` env var in their `uninstall.sh`:

```bash
REMOVE_DATA="${NOUSVIZ_REMOVE_DATA:-0}"
if [ "$REMOVE_DATA" = "1" ]; then
  rm -rf "$DATA_DIR"
else
  : # preserve — reinstall picks up existing data
fi
```

`uninstall-check` reports the data directory to the UI (with size) so the operator can
make an informed keep/delete choice — the same flow regular plugins use for Postgres tables.

---

## 9. Route loading model

`apps/api/src/plugin_loader.py` handles plugin route discovery and registration.

### On API startup

`main.py` calls `load_plugin_routes(app)` after all core routes are registered. The loader:

1. Scans `plugins/installed/*/api/routes.py`
2. For each: dynamically imports the module, registers `router` at `/api` prefix
3. Registers `extra_routers` with their specified prefixes
4. Runs `setup(app)` if exported (used for static file mounts)
5. Registers `api/widgets.py` router if present (deprecated — no plugins currently ship widgets)

### On marketplace install

`install_plugin` calls `load_plugin_routes(app)` after the plugin files are in place. New routes are immediately active — no restart required for install.

### On uninstall

Routes **cannot** be hot-unregistered from a running FastAPI app. After uninstall, registered routes remain in the route table until restart. The uninstall API returns `restart_required: true` and the frontend shows a restart reminder.

### Module naming

Plugin modules use the name `plugin_routes_{slug}` (hyphens replaced with underscores), preventing collisions with core modules.

---

## 10. Frontend integration model

### Plugin pages

All installed plugins are rendered by `GenericPluginPage` at `/plugins/{slug}`. This component:

1. Calls `GET /api/plugins/{slug}` to fetch the manifest
2. Renders tab navigation from `plugin.yaml dashboards[]`
3. For each active tab, fetches the dashboard spec from `GET /api/plugins/{slug}/dashboards/{name}`
4. Passes the spec to `DashboardRenderer`, which renders panels based on `type`

**No plugin has a custom React page in this repo.** If a plugin needs custom React components, they are served as a widget bundle from the plugin's own package and loaded lazily via `COMPONENT_REGISTRY`.

### Sidebar navigation

`Sidebar.tsx` never hardcodes any plugin. Navigation entries come from `plugin.yaml navigation[]`:

```tsx
{installedPlugins
  .flatMap(p => p.navigation ?? [])
  .filter(n => n.position === "sidebar")
  .map(n => (
    <NavItem
      key={n.href}
      href={n.href}
      icon={<PluginIcon name={n.icon} />}
      label={n.label}
      badge={n.badge_count}
    />
  ))
}
```

### Frontend events

| Event | When fired | Who listens |
|-------|-----------|-------------|
| `nousviz:plugins-changed` | After install or uninstall completes | `Sidebar.tsx` — re-fetches plugin list |

---

## 11. Core vs. plugin boundary

| Core (`apps/api/src/routes/`) | Plugin (`plugins/installed/{slug}/api/routes.py`) |
|-------------------------------|--------------------------------------------------|
| `health.py` — platform health | Routes querying this plugin's own tables |
| `alerts.py` — alert rules engine | Plugin-specific dashboard data endpoints |
| `connections.py` — Data Explorer drilldown | Plugin-specific sync status endpoints |
| `annotations.py` — annotations | Plugin-specific configuration endpoints |
| `query.py` — SQL executor | Plugin-specific webhook receivers |
| `auth.py`, `settings.py`, `backups.py` | |
| `datasets.py`, `share.py` | |

**The Data Explorer is always core.** It is the only cross-plugin data layer. Moving it into a plugin creates a circular dependency.

---

## 12. Environment variables

### Core env vars

Documented in `.env.example`. Never plugin-specific.

### Plugin env vars

Convention: `{PLUGIN_ENV_PREFIX}_{FIELD_NAME}` where `env_prefix` is declared in `plugin.yaml connections[]`.

```env
# Starter Plugin — env_prefix: HELLO_
HELLO_API_KEY=sk-example-key-12345
HELLO_BASE_URL=https://api.example.com
```

Plugin env vars are not in this repo's `.env.example`. They are shown in the plugin settings UI (form generated from `connections[].fields`) and documented in the plugin's own README.

---

## 13. Official plugin development — branch and PR model

### Repositories

| Plugin | Repository |
|--------|-----------|
| Starter Plugin | `github.com/nousviz/plugin-starter-plugin` |
| Cloudflare | `github.com/nousviz/plugin-cloudflare` |
| Google Search Console | `github.com/nousviz/plugin-google-search-console` |
| Tracking Links | `github.com/nousviz/plugin-tracking-links` |
| PAM | `github.com/nousviz/plugin-pam` |
| iGaming Offers | `github.com/nousviz/plugin-igaming-offers` |
| iGaming Industry | `github.com/nousviz/plugin-igaming-industry` |

### Contributing a change to a plugin

1. **Never edit plugin code in this repo.** Canonical code lives in the plugin repo.
2. Clone: `git clone git@github.com:nousviz/plugin-{slug}.git`
3. Branch from `main`: `git checkout -b fix/description` or `feat/description`
4. Make changes following the package structure in section 3
5. Test: symlink or copy to `plugins/installed/{slug}/` in a local NousViz checkout
6. Open a PR to `main` in the plugin repo
7. After merge, tag: `git tag v1.0.1 && git push --tags`
8. Update `plugins/official/{slug}/plugin.yaml` in **this repo** — bump `version:`
9. Open a PR to `testing` in this repo with only the version bump

### What goes where

| This repo | Plugin repo |
|-----------|-------------|
| `plugins/official/{slug}/plugin.yaml` — catalogue manifest | Everything in section 3 |

The catalogue manifest in `plugins/official/` is a minimal version used for marketplace display before install. The full `plugin.yaml` lives inside the plugin package after install.

---

## 14. Plugin starter template

A complete starter lives at `sdk/examples/starter-plugin/`. See the in-app developer guide at `/build-a-plugin` for a full walkthrough.

```
sdk/examples/starter-plugin/
├── plugin.yaml                  # Full schema template with all fields annotated
├── api/
│   └── routes.py                # Router stub with one GET and one POST example
├── src/
│   └── sync.py                  # Sync script stub with run() and argparse
├── storage/
│   └── migrations/
│       ├── 001_initial.sql      # Table creation stub
│       └── 001_initial_down.sql # Down migration stub
├── dashboards/
│   └── overview.yaml            # Dashboard spec stub with stat + table panels
├── dataport.yaml                # Data port stub with one tab
├── insights.yaml                # Insight stub with one query and fallback_empty
└── README.md                    # Plugin README template
```

---

## 15. Validation checklist

Run through this before opening a PR for a plugin or submitting to the marketplace.

### plugin.yaml
- [ ] `name` is lowercase, hyphenated, unique across all official plugins
- [ ] `version` is bumped from the previous release (semver)
- [ ] `icon` is a valid Lucide icon name
- [ ] `databases.postgres.tables` and `databases.clickhouse.tables` list every table created by this plugin's migrations — no more, no less
- [ ] `navigation[].href` is `/plugin/{slug}`
- [ ] `repository` URL is the correct external plugin repo (not this repo)
- [ ] No `depends_on` field exists — plugins are isolated; cross-plugin data flows through the Data Explorer

### api/routes.py
- [ ] All routes are under `/plugins/{slug}/`
- [ ] All Postgres connections use `with get_pg_conn() as conn:`
- [ ] No imports from other plugin modules
- [ ] No SQL queries against tables not declared in this plugin's `plugin.yaml databases`
- [ ] All SQL uses parameterised queries — no f-string or `.format()` SQL

### dataport.yaml
- [ ] All `table:` values are tables declared in this plugin's `plugin.yaml databases`

### insights.yaml
- [ ] All SQL queries only reference tables declared in this plugin's `plugin.yaml databases`
- [ ] Every query has `fallback_empty: true`

### dashboard YAML
- [ ] All panel queries only reference tables declared in this plugin's `plugin.yaml databases`

### Migrations
- [ ] Each `NNN_name.sql` has a matching `NNN_name_down.sql`
- [ ] Up migrations use `CREATE TABLE IF NOT EXISTS`
- [ ] Down migrations use `DROP TABLE IF EXISTS`
- [ ] No table names shadow core tables (`users`, `alerts`, `annotations`, `dashboards`, `datasets`, `api_keys`, `schema_migrations`, `connections`)

### Sync
- [ ] `run()` exists and accepts `since: str | None`
- [ ] Returns `{"rows_synced": int, "errors": list[str]}`
- [ ] No unhandled exceptions — sync failure is caught and returned in `errors`

### End-to-end
- [ ] Fresh install on clean Postgres: `setup.sh` + install plugin → API starts without error
- [ ] `GET /api/plugins/{slug}/health-check` returns 200
- [ ] Uninstall with `remove_data=true` → tables dropped, no errors
- [ ] Uninstall with `remove_data=false` → tables remain, plugin directory removed
- [ ] Reinstall after uninstall → migrations reapply cleanly
- [ ] No residual routes active after API restart following uninstall

---

## 16. Security model

**Process-level trust** — plugins run in the same Python process as the core API. This is the most important security fact to understand before installing a plugin.

### What this means

A plugin's `api/routes.py` is loaded via `importlib` into the live API process. Once loaded, a plugin can:

- Read all environment variables (`os.environ`) including `NOUSVIZ_ENCRYPTION_KEY`, `NOUSVIZ_DB_PASSWORD`, and any API tokens
- Access the database connection pool (`from apps.api.src.db import get_pg_conn`)
- Access any loaded module in `sys.modules`
- Execute subprocesses, make outbound network calls, or read/write any file the API process can access

This is equivalent to granting the plugin the same trust level as core platform code.

### What the platform does to mitigate risk

| Control | Where | What it does |
|---------|-------|--------------|
| Rate limiting | `POST /api/plugins/install` | Max 5 installs per IP per 5 minutes. Prevents runaway installs from an authenticated attacker. |
| Version tag pinning | Install flow | All installs clone a specific `v{version}` git tag. Installing HEAD or a branch is rejected. |
| Commit SHA recording | `plugin_registry.installed_commit_sha` | The install endpoint records the cloned commit SHA. `plugin_loader.py` checks this on every restart and logs a `WARNING` if files have been modified since install. |
| pip environment isolation | Install flow | `pip install` runs with `NOUSVIZ_*` env vars stripped. Plugin install scripts cannot read the encryption key or credentials. |
| Public prefix audit | `main.py` startup | After plugin routes load, the API compares `PUBLIC_PREFIXES` against the canonical list. Any plugin that adds its own auth bypass is logged as a contract violation. |

### What the platform does NOT do (yet)

- **Process isolation** — plugins are not sandboxed in a separate subprocess. This would require an IPC proxy similar to Grafana's gRPC plugin model. Tracked as a future architectural change.
- **Signature verification** — git tags are not GPG/Sigstore-signed. A compromised plugin repo could publish a malicious tag. Official plugin signing is post-v0.2.0 scope.

### Implication for operators

Installing a community or private plugin is equivalent to running third-party code with your API server's permissions. Only install plugins from sources you explicitly trust.

The marketplace install flow shows a trust warning modal for community and private plugins before any install proceeds.

### Auth contract for plugin routes

All plugin routes registered via `api/routes.py` are covered by the global auth middleware. When `AUTH_REQUIRED=true`, every plugin route requires a valid session or API key unless the operator explicitly adds the route prefix to `PUBLIC_PREFIXES`.

Plugin authors must **not** patch `PUBLIC_PREFIXES` in their own code. If a plugin genuinely needs a public endpoint (e.g. a webhook receiver), document this requirement and instruct operators to add the prefix manually in `auth.py`.

`/api/data-port/` is **not** in the public prefix list. Data port tables may contain sensitive operator data. Embed widgets that call data port endpoints must authenticate with an API key (`X-API-Key` header). Use `AUTH_REQUIRED=false` in local development to allow unauthenticated access.
