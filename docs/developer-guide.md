# Developer Guide

Patterns, conventions, and rules for developers extending NousViz — whether building plugins, adding core features, or contributing to the platform.

---

## API patterns

### Authenticated vs public endpoints

NousViz has two types of endpoints:

| Type | How to call | When to use |
|------|------------|-------------|
| **Authenticated** | `apiFetch("/api/...")` | Any endpoint that reads/writes user data, settings, or internal state |
| **Public** | `fetch("/api/...")` | Health checks, share access, plugin table queries (unauthenticated) |

`apiFetch()` (defined in `apps/web/src/lib/api.ts`) automatically attaches the `X-Session-Token` header. Use raw `fetch()` only for endpoints in the `PUBLIC_PREFIXES` list.

### Public endpoints (no auth required)

```
/api/health              — system health check
/api/health/log          — health check history
/api/shares/             — share link access and metadata
/api/query               — SQL queries (restricted to plugin-declared tables when unauthenticated)
/api/plugins/            — GET requests only (manifest, dashboards, settings)
```

These are defined in `apps/api/src/middleware/auth.py` as `PUBLIC_PREFIXES` and `PUBLIC_GET_PREFIXES`.

### Auth model

NousViz is multi-user only:

- Each user has their own email, bcrypt-hashed password, role, and session
- The setup wizard creates the first superadmin; subsequent users join via invite
- `AUTH_REQUIRED=true` in `.env` — enables authentication enforcement
- Login (`POST /api/auth/login`) returns a session token; clients include it as `X-Session-Token` on subsequent requests (not cookies)
- API keys can be issued for headless callers (`X-API-Key` header)

Session tokens are SHA-256 hashed in the `user_sessions` table; the raw token is shown only once at login. Step-up auth tightens write operations: sensitive endpoints require a recent password re-check (`POST /api/auth/step-up`).

---

## Database access

### Connection pattern

Always use the shared connection pool via context manager:

```python
from apps.api.src.db import get_pg_conn

# Correct — context manager handles commit/rollback/return to pool
with get_pg_conn() as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM my_table WHERE id = %s", (item_id,))
    rows = cur.fetchall()
```

Never use standalone `psycopg2.connect()` calls — they leak connections.

### SQL safety

Always use parameterised queries. Never use f-strings or `.format()` with user input:

```python
# WRONG — SQL injection
cur.execute(f"SELECT * FROM items WHERE name = '{name}'")

# CORRECT — parameterised
cur.execute("SELECT * FROM items WHERE name = %s", (name,))
```

### Blocked tables

The query API blocks access to internal tables regardless of authentication:

```
users, user_sessions, user_activity, credentials, api_keys, encryption_keys
```

These are enforced by `PG_BLOCKED_TABLES` in `apps/api/src/routes/query.py`.

---

## Routing

### React Router setup

The frontend uses React Router v6 with a flat route structure in `apps/web/src/App.tsx`. Routes are wrapped in `AuthGate` which handles login state.

Key routes:

```
/                          → DashboardPage (home)
/plugin/:slug/*            → PluginPage (generic plugin page with tab navigation)
/settings                  → SettingsPage
/marketplace               → MarketplacePage
/shared/:shareId           → SharedViewPage (bypasses AuthGate)
/docs/:slug?               → DocsPage
/build-a-plugin            → BuildAPluginPage
```

### Adding a new core page

1. Create the page component in `apps/web/src/pages/`
2. Add a route in `apps/web/src/App.tsx`
3. Add a sidebar entry in `apps/web/src/components/layout/Sidebar.tsx` (if navigable)

### Plugin routes

Plugin routes are auto-loaded by `apps/api/src/plugin_loader.py`. The loader:

1. Scans `plugins/installed/*/api/routes.py` on startup
2. Imports the `router` object from each file
3. Registers it with the FastAPI app

All plugin API routes must be under `/plugins/{slug}/`. The frontend renders plugin pages via `PluginPage.tsx` which fetches dashboard specs from `/api/plugins/{slug}/dashboards/{name}`.

---

## Plugin contract

### Required files

Only `plugin.yaml` is required. Everything else is optional:

| File | Purpose |
|------|---------|
| `plugin.yaml` | Manifest — identity, requirements, navigation, datasets, settings |
| `api/routes.py` | FastAPI router, auto-loaded on install |
| `src/sync.py` | ETL sync script (default; path is configurable via manifest's `sync.script`) |
| `storage/migrations/*.sql` | Schema creation/teardown |
| `dashboards/*.yaml` | Dashboard tab specs |
| `dataport.yaml` | Data Port table views |
| `insights.yaml` | Insight card queries |

### Key manifest fields

```yaml
name: my-plugin              # slug — lowercase, hyphenated, globally unique
datasets:                     # tables for Datasets page + query allowlist
  - name: my_table
    label: My Table
    db: postgres
    grain: record
settings:                     # auto-generates settings form
  - name: sync_enabled
    label: Enable sync
    type: toggle
    default: true
navigation:                   # one entry per sidebar tab
  - label: Overview
    href: /plugin/my-plugin/overview
    icon: bar-chart-2
    position: sidebar
dashboards:                   # maps to dashboards/*.yaml
  - name: overview
    label: Overview
```

### Table naming

Plugin tables must not shadow core tables. Use a prefix:

```
hello_items       ✓  (prefixed with plugin name)
items             ✗  (too generic, could conflict)
users             ✗  (core table)
alerts            ✗  (core table)
```

---

## Writing a utility plugin

Utility plugins provide platform-level services (databases, caches, credential vaults) that other plugins can declare a dependency on. They ship their own install/uninstall/health hooks and register capabilities in a platform-wide registry. ClickHouse is the reference implementation — see `plugins/utilities/clickhouse/`.

Canonical schema reference: **[`docs/plugin-architecture.md` — Platform utility plugins](plugin-architecture.md)**. This section is the author-facing walkthrough.

### When to build a utility vs a regular plugin

Build a **utility** when:
- You're installing a platform service other plugins will consume (a database, message broker, credential store, auth provider)
- You need to run an install script (binary download, daemon startup via PM2, config file generation)
- You want to be listed in the Marketplace Utilities section and the sidebar Utilities section

Build a **regular plugin** when:
- You're shipping analytics, integrations, dashboards, or workflows the operator uses directly
- You consume data — you don't host it

### Minimal utility plugin layout

```
plugins/utilities/my-utility/
├── plugin.yaml                      # type: utility, provides, hooks
└── scripts/
    ├── install.sh                   # runs on install
    ├── uninstall.sh                 # runs on uninstall
    └── health.sh                    # called by /api/health
```

### Manifest skeleton

```yaml
name: my-utility
display_name: My Utility
version: 1.0.0
description: One-paragraph explanation of the service this utility provides.
license: Apache-2.0
icon: database
category: utility
visibility: public

type: utility                       # Marks this plugin as a utility
provides:                           # Capabilities this utility registers
  - my_capability                   # Other plugins can `requires: {my_capability: true}`

install_hook: scripts/install.sh
uninstall_hook: scripts/uninstall.sh
health_check: scripts/health.sh

requires:
  min_ram_mb: 512                   # Validated by install.sh (not by the platform)
  os: linux

connections:                        # Exposed as the utility's Settings tab
  - name: my_utility
    env_prefix: MY_UTILITY_
    label: My Utility Configuration
    fields:
      - { name: host,     label: "Host",     type: text,     required: true,  default: "localhost" }
      - { name: port,     label: "Port",     type: number,   required: false, default: 6379 }
      - { name: password, label: "Password", type: password, required: false }
```

Notes:
- `type: utility` is the single marker the platform uses to route this plugin into the Utilities sidebar / marketplace section.
- `provides:` strings are the capability names. Other plugins opt in via `requires: {my_capability: true}` — the platform's install endpoint checks the capability registry before allowing those plugins to install.
- `connections[]` fields become the utility's own Settings tab (`/plugin/my-utility/settings`), with values stored in `.env` under `MY_UTILITY_HOST`, `MY_UTILITY_PORT`, etc.

### Install hook contract

`scripts/install.sh` runs once on install. Platform env vars passed:

| Env var | Purpose |
|---------|---------|
| `NOUSVIZ_DIR` | Absolute path to the repo root (use for `$NOUSVIZ_DIR/data/{slug}/`, `.env`, etc.) |

Responsibilities:
1. Check hardware requirements from the manifest (`min_ram_mb` etc.) and fail fast with a clear message
2. Download/install the underlying service binary
3. Write any config files under `$NOUSVIZ_DIR/plugins/installed/{slug}/` or `$NOUSVIZ_DIR/data/{slug}/`
4. Write `MY_UTILITY_*` env vars to `$NOUSVIZ_DIR/.env`
5. Start the service under PM2 if it's a long-running process (`pm2 start "<command>" --name my-utility`)
6. Exit 0 on success, non-zero with a clear stderr message on failure

### Uninstall hook contract

`scripts/uninstall.sh` runs on uninstall. Env vars:

| Env var | Purpose |
|---------|---------|
| `NOUSVIZ_DIR` | Absolute path to the repo root |
| `NOUSVIZ_REMOVE_DATA` | `1` if operator chose "delete data", `0` if "keep data" |

**You must honour `NOUSVIZ_REMOVE_DATA`.** The uninstall modal's keep-data / delete-data choice relies on this:

```bash
REMOVE_DATA="${NOUSVIZ_REMOVE_DATA:-0}"
if [ "$REMOVE_DATA" = "1" ]; then
  rm -rf "$NOUSVIZ_DIR/data/my-utility"
fi
```

Also: stop any PM2 process (`pm2 delete my-utility`), remove bin/config files, and scrub `MY_UTILITY_*` entries from `.env`.

### Health hook contract

`scripts/health.sh` is called by `/api/health` and surfaces under `services.{slug}` in the response (which the topbar and Connections page consume). Output **must** be valid JSON on stdout:

```json
{"ok": true, "version": "1.2.3"}
```

Or on failure:

```json
{"ok": false, "error": "Connection refused on port 6379"}
```

Keep the script fast (< 3 s). The platform enforces a 10 s timeout.

### Testing your utility plugin locally

1. Drop your utility into `plugins/utilities/my-utility/` on a dev instance
2. Install via marketplace at `/marketplace` — the Utilities section lists it
3. Verify the capability registered: `curl http://localhost:8000/api/plugins/capabilities` should return `["my_capability", ...]`
4. Check `/api/health` → `services.my-utility.status = "connected"`
5. Install a test analytics plugin that declares `requires: {my_capability: true}` — install should succeed. Uninstall the utility first and retry — install should fail with a clear "install the utility first" message
6. Uninstall with both "keep data" and "delete data" — confirm the data directory is preserved / removed as expected

---

## Frontend conventions

### Styling

- Dark theme only (for now)
- Font: Instrument Sans 600 (display), Instrument Sans 400 (body), Geist Mono (data/code)
- CSS utility classes: `font-display`, `font-body`, `font-mono-deck`
- Primary color: `hsl(210 100% 60%)` — see `apps/web/src/index.css` for all tokens
- Use `cn()` utility for conditional class merging (re-export of `clsx` + `tailwind-merge`)

### Component patterns

- Use Lucide React icons — import from `lucide-react`
- Data tables use `font-mono-deck` for numbers
- Empty states always include a call-to-action
- Loading states use skeleton placeholders, not spinners
- All hooks must come before any conditional `return` in React components

### State management

- No global state library — use React hooks (`useState`, `useEffect`)
- API calls via `apiFetch()` for authenticated endpoints
- No context providers except `AuthGate` at the root

---

## Testing

### Manual testing process

1. Make changes on `testing` branch
2. Test locally at `http://localhost:5173`
3. Deploy to server: `./scripts/deploy-local.sh`
4. Test on server at `http://{SERVER_IP}/`
5. Write test plan in `todo/{version}/testing/`

### Automated tests

| Tool | What it checks | How to run |
|------|---------------|------------|
| TypeScript check | Type errors | `cd apps/web && npx tsc --noEmit` |
| Smoke tests | 10 health/safety checks | `./scripts/smoke-test.sh` |
| Integration tests | 15 API contract tests | `pytest tests/test_api.py -v` |
| CI pipeline | All of the above | Push to `testing` branch |

### Deploy pipeline

```
TypeScript check → Build → rsync → Migrations → nginx reload → PM2 reload → Health check → Smoke tests
```

---

## Code style

### Python (backend)

- FastAPI for all API routes
- Type hints on function signatures
- `get_pg_conn()` context manager for all database access
- Parameterised SQL — never f-strings with user input
- Logging via `logging.getLogger("nousviz.api.{module}")`

### TypeScript (frontend)

- React 18 with functional components
- TypeScript strict mode
- Tailwind CSS for styling — no CSS modules or styled-components
- Named exports for page components (`export default function PageName()`)
- No unused imports (enforced by CI)
