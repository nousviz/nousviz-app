# NousViz Glossary

End-to-end reference for every concept, component, and term in the NousViz platform.

---

## Platform Overview

**NousViz** is an open-source data intelligence platform that enables users to explore, alert on, and visualize data from any source through a plugin ecosystem. It runs natively on PostgreSQL (no Docker required for core setup) and uses a modular architecture: React/Vite frontend, FastAPI backend, and a Python plugin SDK.

---

## Core Concepts

### Plugin

An independently-versioned package that extends NousViz with new data sources, visualizations, and functionality. Plugins are not shipped with the core platform — they live in external Git repositories and are installed at runtime into `plugins/installed/{slug}/`. Each plugin owns its own database tables, API routes, dashboards, sync scripts, and settings.

**Three categories:**

| Category | Location | Description |
|----------|----------|-------------|
| **Official** | `plugins/official/` | Maintained by NousViz. `verified: true` in manifest. |
| **Community** | `plugins/community/` | Third-party submissions with a `repository_url`. |
| **Private** | Installed via URL | Not listed in any catalog; installed by explicit repository URL. |

### Plugin Manifest (`plugin.yaml`)

The YAML file at the root of every plugin that declares its identity, schema, extension points, and metadata. Required fields: `name`, `display_name`, `version`, `description`, `license`, `icon`, `category`, `tags`, `visibility`.

### Dashboard

A declarative YAML specification (`dashboards/{name}.yaml`) that defines a collection of widgets for visualizing data. Each plugin can declare multiple dashboards. Dashboards are rendered by the `DashboardRenderer` component on the frontend, which fetches the YAML spec, builds SQL queries from widget configs, and renders the results as KPIs, charts, or tables.

**Not to be confused with the Home page** — the system-level landing page at `/` is a hardcoded status + activity snapshot, not a plugin dashboard. (Previously called "Overview" — renamed in v0.8.3 to reduce terminology collision.)

### Widget

A single visualization unit inside a dashboard. Each widget has a `type`, `position` (row/col/width on a grid), and `config` (data source, metric, formatting).

**Widget types:**

| Type | Description |
|------|-------------|
| `kpi` | Single numeric metric (count, sum, average) with optional formatting (currency, percent). |
| `bar_chart` | Categorical comparison with X-axis categories and Y-axis metrics. |
| `line_chart` | Time-series or trend visualization. |
| `stacked_bar_chart` | Multiple series stacked vertically for composition analysis. |
| `table` | Tabular row display with configurable columns, sorting, and alignment. |

### Panel

Legacy simplified format for declaring widgets in a dashboard YAML. Panels use a flatter structure (`type`, `label`, `query`, `fallback_empty`) and are auto-converted to widgets by the frontend. Stat panels go to row 0; charts/tables go to subsequent rows.

### Data Explorer

The primary authoring surface in NousViz. A three-level drilldown:

1. **Connection** — pick a data source (an installed plugin or a registered Postgres connection)
2. **Table** — browse the tables exposed by that connection
3. **Row** — drill into rows of a specific table, with sort and filter

Any view in the Data Explorer can be saved as a widget and dropped onto a dashboard. Cross-plugin combine (joining data from multiple plugins) happens inside the Data Explorer — there is no separate "join surface."

API: `GET /api/connections/{id}/tables/{schema}/{table}/rows`.

### Dataset

A named data table or query template exposed by a plugin via `datasets/{name}.yaml`. Datasets define the schema (columns, types) and default queries that widgets reference. Users can also upload CSV datasets via the Datasets page.

### Annotation

A timestamped event note (incident, deployment, campaign, etc.) with category, severity, and optional pinning. Annotations can be attached to specific time ranges and overlaid on dashboards. Managed at `/annotations`.

### Alert

A monitoring rule that evaluates a SQL condition on a schedule and triggers notifications when thresholds are met. Plugins can ship alert templates in `alerts/{name}.yaml`; operators configure actual alerts from these templates. The alert worker runs hourly via pm2 cron.

### Connection

A registered external data source (PostgreSQL, MySQL, API key, OAuth2, HTTP). Plugins declare required connections in their manifest under `connections[]`. Connection metadata is stored in the `connections` table. Managed at `/connections`.

### Sync

An ETL (Extract-Transform-Load) script inside a plugin that pulls data from external sources into the plugin's database tables. The script path comes from the manifest's `sync.script` field (default: `src/sync.py`; override e.g. `src/<slug>_sync.py` to avoid `sys.modules` collisions across sibling plugins). Syncs can be triggered manually (`POST /api/plugins/{slug}/sync`) or run on a cron schedule defined in `plugin.yaml`. The sync function must accept a `since` parameter for incremental sync and return `{"rows_synced": int, "errors": list}`.

### Data Port (SDK feature)

A read-only table-viewer **opt-in** that a plugin enables by shipping a `dataport.yaml` file. Each tab declares a database table with column definitions, formatting (badges, dates, numbers), and filter controls.

Row browsing is a drilldown leaf inside the Data Explorer: `/datasets/<plugin>/<table>`. The SDK contract (`dataport.yaml` filename, tab schema, `/api/data-port/*` backend endpoints) provides the formatting/filter metadata that the Data Explorer reads when rendering rows.

For plugins without a `dataport.yaml`, `/datasets/<plugin>/<table>` shows a generic table viewer using only the column types discovered from the database schema.

### Insight

A pre-defined SQL query shipped by a plugin in `insights.yaml`. Insights surface key findings or summaries aggregated across all installed plugins via `/api/insights`.

### Share

A public link to a dashboard or widget that can be accessed without authentication. Shares support optional password protection (bcrypt-hashed), expiry dates, and access logging. Managed at `/shares`.

### Embed

An iframe-friendly rendering of a dashboard, widget, or plugin page. Embed routes strip the sidebar and topbar for clean external integration:

| Route | Description |
|-------|-------------|
| `/embed/dashboard/:pluginId/:dashboardName` | Full dashboard |
| `/embed/widget/:pluginId/:dashboardName/:widgetIndex` | Single widget |
| `/embed/page/:pluginId/:pageName` | Plugin custom page |
| `/embed/plugin/:pluginId` | Multi-widget plugin embed |

### Canvas

A full-page custom rendering mode for plugins at `/canvas/:pluginId/:pageName`. No sidebar or topbar — the plugin controls the entire viewport.

### Publisher

The entity that maintains a plugin. Declared in `plugin.yaml` under `publisher:` with `slug`, `name`, `website`, `contact_email`, and `verified` flag. Tracked in the `publishers` database table.

### Marketplace

The plugin discovery and installation interface at `/marketplace`. Aggregates official, community, and installed plugin catalogs. Supports search, category filtering, and one-click install with trust warnings for community plugins.

---

## Plugin Structure

Every installed plugin follows this directory layout:

```
plugins/installed/{slug}/
├── plugin.yaml                    # REQUIRED — manifest
├── api/
│   └── routes.py                  # FastAPI router, exports `router`
├── src/
│   └── sync.py                    # ETL script with run(since=None) function
├── storage/
│   └── migrations/
│       ├── 001_initial.sql        # Up migration
│       └── 001_initial_down.sql   # Down migration
├── dashboards/
│   └── analytics.yaml             # Dashboard spec (data panels only)
├── datasets/
│   └── main.yaml                  # Query templates
├── alerts/
│   └── alert_name.yaml            # Alert rule templates
├── dataport.yaml                  # Optional — Data Explorer row formatting / filter metadata
├── insights.yaml                  # SQL queries for /api/insights
├── requirements.txt               # Python dependencies
└── README.md                      # Shown in marketplace
```

### Plugin Manifest Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase, hyphenated slug (globally unique). |
| `display_name` | Yes | Human-readable name for the UI. |
| `version` | Yes | Semantic version (MAJOR.MINOR.PATCH). |
| `description` | Yes | 100-word summary for marketplace cards. |
| `license` | Yes | MIT, Apache-2.0, Sustainable Use, or Commercial. |
| `icon` | Yes | Lucide icon name. |
| `category` | Yes | analytics, content, monitoring, integration, productivity, compliance, premium, community, utility. |
| `tags` | Yes | Searchable metadata (min 1 tag). |
| `visibility` | Yes | public, public_premium, or fully_private. |
| `publisher` | No | Publisher identity (slug, name, website, verified). |
| `repository` | No* | HTTPS Git URL (*required for public plugins). |
| `requires` | No | Infrastructure requirements (postgres, postgres_version). Additional requirements rejected unless the corresponding utility plugin is installed. |
| `connections` | No | External API/DB credentials the plugin needs. |
| `databases` | No | Tables owned by this plugin (postgres). |
| `navigation` | No | Sidebar entries (label, href, icon, position, badge). |
| `dashboards` | No | Tab definitions (name, label) rendered on the plugin page. |
| `sync` | No | ETL config (script, schedule, supports_incremental, timeout). |
| `settings` | No | Operator-configurable fields (toggle, text, number, select). |
| `datasets` | No | Named query templates. |
| `alerts` | No | Alert rule templates. |
| `long_description` | No | Extended markdown description. |
| `screenshots` | No | Image URLs for marketplace listing. |
| `depends_on` | No | Other plugins this plugin requires. |
| `recommended_with` | No | Suggested companion plugins. |

---

## Plugin Page Tabs

When a user navigates to `/plugin/{slug}`, the plugin page renders tabs from the `navigation:` field in the plugin manifest. The plugin controls what tabs appear — nothing is hardcoded by the platform.

Common tab types:

| Tab type | How it renders | Description |
|----------|---------------|-------------|
| **About** | `PluginAboutTab` (manifest metadata) | Plugin info: version, publisher, requirements, tables. Not a dashboard. URL slug stays `overview` for backwards-compat; tab label changed to "About" in v0.8.3 (P111). |
| **Dashboard** | `DashboardRenderer` (YAML spec) | Data panels — charts, tables, stat cards. Must be declared in both `navigation:` and `dashboards:`. |
| **Alerts** | `PluginAlerts` component | Alert templates the plugin ships. Operators configure and activate. |
| **Settings** | `PluginSettingsTab` (auto-generated form) | Only appears if the plugin declares `settings:` fields in its manifest. |

The default tab is the first entry in `navigation:`. Dashboard tabs match entries in `dashboards:` by name — the `navigation:` href slug must match the `dashboards:` name.

---

## Frontend Pages

### Main App Pages (with sidebar + topbar)

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Landing page: health snapshot, KPI cards (alerts, plugins, dashboards, shares), database info, pinned annotations. |
| `/marketplace` | Marketplace | Browse and install plugins from the catalog. |
| `/build-a-plugin` | Build a Plugin | Plugin creation guide and resources. |
| `/connections` | Connections | Register and manage external data sources. |
| `/datasets` | Datasets | Upload, browse, and manage data tables. |
| `/shares` | Shares | Create and manage public shared links. |
| `/alerts` | Alerts | Configure and monitor data alert rules. |
| `/annotations` | Annotations | Create and manage event annotations. |
| `/plugins` | Installed Plugins | List and manage installed plugins. |
| `/plugins/:pluginId` | Plugin Detail | Marketplace detail view for a specific plugin. |
| `/settings` | Settings | System configuration (theme, database, SSL, jobs). |
| `/analytics` | Analytics | Usage metrics: sessions, page views, devices, browsers. |
| `/datasets/:plugin/:table` | Data Explorer row view | Drill into rows of a specific table. |
| `/plugin/:pluginId/*` | Plugin Page | Plugin dashboard container with tabs. |
| `/docs` | Docs | Platform documentation. |
| `/docs/:slug` | Doc Page | Specific documentation page. |

### Embed Pages (no chrome)

| Route | Description |
|-------|-------------|
| `/embed/dashboard/:pluginId/:dashboardName` | Full dashboard embed. |
| `/embed/widget/:pluginId/:dashboardName/:widgetIndex` | Single widget embed. |
| `/embed/page/:pluginId/:pageName` | Plugin custom page embed. |
| `/embed/plugin/:pluginId` | Multi-widget plugin embed. |

### Other

| Route | Description |
|-------|-------------|
| `/canvas/:pluginId/:pageName` | Full-page custom plugin rendering. |
| `/shared/:shareId` | Public shared view (password-protected). |

---

## Sidebar Navigation

The sidebar is dynamically built from installed plugins and core sections:

| Section | Items | Description |
|---------|-------|-------------|
| **Dashboards** | Home, Alerts, Annotations | Core platform pages (always visible). Home is the landing page at `/`. |
| **System** | Health, Jobs, Logs | Operator observability. All under `/system`. |
| **Your Plugins** | Dynamic per-plugin entries | Each installed plugin's navigation entries from its manifest. Collapsible groups with sub-items for dashboards + settings. |
| **Plugins** | Marketplace, Installed | Plugin discovery and management. |
| **Data** | Connections, Datasets, Usage, Shared Links | Data management and analytics. |
| **Resources** | Docs | Documentation. |

---

## API Reference

### Authentication

Three methods (checked by middleware in order):

| Method | Header | Storage | Description |
|--------|--------|---------|-------------|
| **API Key** | `X-API-Key` | SHA-256 hash in `api_keys` | Long-lived key for programmatic access. |
| **Session Token** | `X-Session-Token` | SHA-256 hash in `user_sessions` | 30-day browser session from login. |

Authentication can be disabled via `AUTH_REQUIRED=false` (local dev only).

**User Roles:** `superadmin` | `admin` | `analyst` | `viewer`

### Public Endpoints (no auth required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health (Postgres, SSL). |
| `/api/health/log` | GET | Health check history (last 7 days). |
| `/api/health/record` | POST | Record health check (localhost only, PM2 cron). |
| `/api/health/config` | GET | Security config status. |
| `/api/health/connections` | GET | Plugin connection health. |
| `/api/auth/status` | GET | Current auth state and user profile. |
| `/api/auth/login` | POST | Password login, returns session token. |
| `/api/auth/verify` | GET | Validate a session token. |
| `/api/auth/setup` | POST | First-run admin user creation (one-time). |
| `/api/auth/setup/config` | POST | First-run security setup (one-time). |
| `/api/query` | POST | SQL query proxy (unauthenticated: plugin tables only). |
| `/api/shares/{id}` | GET | Share metadata (checks expiry/revocation). |
| `/api/shares/{id}/access` | POST | Access share (password validated). |
| `/api/plugins` | GET | List installed plugins. |
| `/api/plugins/catalog` | GET | Full plugin catalog. |
| `/api/plugins/{id}` | GET | Plugin manifest. |
| `/api/plugins/{id}/dashboards/{name}` | GET | Dashboard YAML spec. |
| `/api/plugins/{id}/datasets/{name}` | GET | Dataset schema. |
| `/api/plugins/{id}/alerts/{name}` | GET | Alert definition. |
| `/api/docs` | GET | Documentation list. |
| `/api/docs/{slug}` | GET | Documentation content. |
| `/api/activity` | POST | Log activity event. |
| `/docs`, `/openapi.json`, `/redoc` | GET | API documentation. |

### Authenticated Endpoints

#### Auth Management (`/api/auth`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/me` | GET | Current user profile. |
| `/api/auth/users` | GET | List all users (admin only). |
| `/api/auth/users` | POST | Create user (admin only). |
| `/api/auth/users/{id}` | PUT | Update user role/status (admin only). |
| `/api/auth/users/{id}` | DELETE | Deactivate user (admin only). |
| `/api/auth/users/{id}/api-key` | POST | Generate/rotate API key (admin only). |
| `/api/auth/activity` | GET | User activity log (admin only). |

#### Plugins (`/api/plugins`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/plugins/{id}/settings` | GET | Get plugin settings. |
| `/api/plugins/{id}/settings` | POST | Save plugin settings. |
| `/api/plugins/{id}/install` | POST | Install plugin (rate limited: 5/5min/IP). |
| `/api/plugins/{id}/install` | DELETE | Uninstall plugin. |
| `/api/plugins/{id}/uninstall-check` | GET | Check uninstall dependencies. |
| `/api/plugins/{id}/sync` | POST | Trigger plugin sync. |
| `/api/plugins/{id}/sync/status` | GET | Last sync timestamp. |
| `/api/plugins/{id}/setup` | POST | Run plugin schema setup. |
| `/api/plugins/{id}/health-check` | POST | Run plugin health check. |

#### Alerts (`/api/alerts`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET | List all alerts. |
| `/api/alerts` | POST | Create alert rule. |
| `/api/alerts/sources` | GET | Available data sources for alerts. |
| `/api/alerts/{id}` | PUT | Update alert. |
| `/api/alerts/{id}` | DELETE | Delete alert. |
| `/api/alerts/{id}/test` | POST | Test-run alert query. |
| `/api/alerts/{id}/sparkline` | GET | Alert trigger history. |

#### Annotations (`/api/annotations`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/annotations` | GET | List annotations (filterable). |
| `/api/annotations` | POST | Create annotation. |
| `/api/annotations/{id}` | GET | Get single annotation. |
| `/api/annotations/{id}` | PUT | Update annotation. |
| `/api/annotations/{id}` | DELETE | Delete/archive annotation. |
| `/api/annotations/{id}/history` | GET | Change history. |
| `/api/annotations/{id}/undo` | POST | Restore previous state. |
| `/api/annotations/{id}/score` | POST | Quick-score annotation. |

#### Data Explorer (`/api/connections`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/connections` | GET | List connections (installed plugins + registered Postgres connections). |
| `/api/connections/{id}/tables` | GET | List tables exposed by a connection. |
| `/api/connections/{id}/tables/{schema}/{table}/rows` | GET | Drill into rows of a specific table (sort, filter, paginate). |

#### Notes (`/api/notes`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notes` | GET | List page notes. |
| `/api/notes` | POST | Create note. |
| `/api/notes/{id}` | PUT | Update note. |
| `/api/notes/{id}` | DELETE | Delete note. |

#### Shares (`/api/shares`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/shares` | GET | List all share links. |
| `/api/shares` | POST | Create share link. |
| `/api/shares/{id}` | PATCH | Update share title/notes. |
| `/api/shares/{id}` | DELETE | Revoke share link. |
| `/api/shares/{id}/log` | GET | Share access log. |

#### Datasets (`/api/datasets`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/datasets` | GET | List all datasets. |
| `/api/datasets/upload` | POST | Upload CSV dataset. |
| `/api/datasets/{slug}` | GET | Get dataset with data. |
| `/api/datasets/{slug}` | DELETE | Delete dataset. |

#### Data Port (`/api/data-port`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/data-port/plugins` | GET | List plugins with dataport configs. |
| `/api/data-port/plugins/{slug}` | GET | Get full dataport config. |
| `/api/data-port/plugins/{slug}/tab/{tab_id}` | GET | Query dataport tab data. |

#### Activity (`/api/activity`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/activity` | GET | List recent activity. |
| `/api/activity/dashboard-usage` | GET | Dashboard usage analytics (admin). |
| `/api/activity/analytics` | GET | User session analytics (admin). |

#### Settings (`/api/settings`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings/database` | GET | Postgres connection settings (no password). |
| `/api/settings/database` | POST | Update Postgres settings. |
| `/api/settings/api-keys` | GET | List API keys (prefix only). |
| `/api/settings/api-keys` | POST | Create API key (raw key returned once). |
| `/api/settings/api-keys/{id}` | DELETE | Revoke API key. |

#### Other

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List sync and alert jobs. |
| `/api/insights` | GET | Aggregated insights from all plugins. |
| `/api/admin/ssl/setup` | POST | Run SSL setup. |

---

## Query Security

The `/api/query` endpoint enforces these guardrails:

- **Blocked statements:** DROP, TRUNCATE, ALTER, DELETE, INSERT, UPDATE, CREATE
- **Row limit:** 10,000 rows per query
- **Timeout:** 30 seconds
- **Unauthenticated access:** Can only query plugin-declared tables
- **Blocked tables** (never queryable via API): `users`, `user_sessions`, `user_activity`, `api_keys`, `alert_rules`
- **Data Explorer queries** additionally block system tables via a server-side regex applied to the compiled SQL

---

## Database Schema (Core Tables)

| Table | Description |
|-------|-------------|
| `users` | User accounts (email, role, auth method). |
| `user_sessions` | Session tokens (SHA-256 hashed in `token_hash` column). |
| `user_activity` | Audit trail of user actions (auth events). |
| `api_keys` | API key hashes and metadata. |
| `plugin_registry` | Installed plugin metadata, version, SHA, install tracking. |
| `publishers` | Plugin publisher identities. |
| `plugin_settings` | Per-plugin operator settings (JSONB values). |
| `schema_migrations` | Tracks applied migrations (format: `{slug}/{filename}`). |
| `alert_rules` | Alert rule definitions and state (migrated from JSON in v0.1.9). |
| `alert_triggers` | Alert trigger history with feedback (useful/neutral/useless). |
| `alert_events` | Alert evaluation log. |
| `annotations` | Event annotations with category, severity, pinning. |
| `annotation_history` | Annotation change snapshots for undo support. |
| `notes` | Page-scoped notes with pinning and resolved state. |
| `activity_events` | Frontend activity tracking (page views, actions, device info). |
| `shared_links` | Share link configs (bcrypt password hash, expiry). |
| `share_access_log` | Share access audit trail (IP, user agent, success). |
| `datasets` | Uploaded CSV datasets (JSONB storage). |
| `connections` | Registered external data source connections. |
| `dashboards` | Dashboard layouts and widget compositions. |

---

## Plugin Lifecycle

### Install

```
POST /api/plugins/{slug}/install
  1. Validate slug (regex: ^[a-z0-9][a-z0-9\-_]{0,63}$)
  2. Check not already installed
  3. Resolve source (official → community → explicit URL)
  4. Validate requirements (Postgres version? Utility plugins?)
  5. SSRF protection (block file://, ssh://, localhost, private IPs)
  6. git clone --depth=1 --branch v{version} <repo> plugins/installed/{slug}/
  7. Validate plugin.yaml exists
  8. pip install -r requirements.txt (env vars sanitized)
  9. Run storage/migrations/ (tracked in schema_migrations)
  10. Hot-load routes via plugin_loader
  11. Record in plugin_registry (slug, SHA, version, URL)
```

### Uninstall

```
DELETE /api/plugins/{slug}/install?remove_data={true|false}
  1. Validate installed
  2. Check dependents (warn if cascade needed)
  3. If remove_data=true: run down migrations in reverse
  4. Remove plugins/installed/{slug}/
  5. Routes remain active until API restart
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite 6, TypeScript 5, Tailwind CSS 3 |
| **Charting** | Recharts |
| **Icons** | Lucide React |
| **Animation** | Framer Motion |
| **Backend** | FastAPI, Uvicorn, Gunicorn |
| **Language** | Python 3.10–3.12 |
| **Core DB** | PostgreSQL 16+ (with pgvector) |
| **Analytics DB** | Plugin-declared (utility plugins can add additional databases) |
| **Process Manager** | pm2 |
| **Reverse Proxy** | nginx (with SSL via Let's Encrypt) |

---

## Rate Limits

| Action | Limit |
|--------|-------|
| Login attempts | 5 per 60 seconds per IP |
| Share password attempts | 5 per 60 seconds per share per IP |
| Plugin installs | 5 per 5 minutes per IP |

---

## Key Files

| File | Description |
|------|-------------|
| `apps/api/src/main.py` | API entry point, route registration, middleware stack. |
| `apps/api/src/plugin_loader.py` | Dynamic plugin route loading. |
| `apps/api/src/middleware/auth.py` | Authentication middleware (public prefix lists). |
| `apps/api/src/db.py` | Database connection pool. |
| `apps/api/src/routes/*.py` | All API route modules (17 files). |
| `apps/web/src/App.tsx` | Frontend route definitions. |
| `apps/web/src/components/layout/Sidebar.tsx` | Dynamic sidebar with plugin navigation. |
| `apps/web/src/components/layout/Topbar.tsx` | Header with search, health, notes. |
| `apps/web/src/pages/PluginPage.tsx` | Plugin dashboard container with tabs. |
| `apps/web/src/widgets/DashboardRenderer.tsx` | Dashboard YAML → widget rendering. |
| `apps/web/src/lib/api.ts` | Authenticated API fetch wrapper. |
| `storage/postgres/migrations/` | Core database migrations (15+ files). |
| `sdk/nousviz_sdk/` | Plugin SDK library. |
| `ecosystem.config.js` | pm2 process definitions. |
