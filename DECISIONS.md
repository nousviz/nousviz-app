# Architecture Decisions

Key architectural decisions in NousViz — what was decided, why, and what was rejected.

---

## 1. Core Architecture

### Decision: Separate frontend (React/Vite) + backend (FastAPI)

**Why:** Two different concerns need two different tools:
- **Dashboard** (React/Vite at `:5173`) — rich interactive UI for data exploration, plugin management, alerts. Client-side rendering is fine because it's behind auth.
- **API** (FastAPI at `:8000`) — handles all data access, plugin routes, sync scripts. Python because ETL/sync scripts are Python and need tight integration.

**Alternatives considered:**
- Single React SPA with serverless functions — rejected because plugin sync scripts need a persistent Python process.
- Django / Flask — rejected because FastAPI is faster for API-first design with async.

---

## 2. Database Architecture

### Decision: Postgres as core; ClickHouse as optional analytics extension

**Why:**
- **Postgres** handles relational data: credentials, plugin metadata, dashboards, alerts, annotations, user config. Row-oriented, transactional, JSONB for flexible schemas. Required for all installs.
- **ClickHouse** handles time-series analytical queries at 2M+ rows with sub-second response. Column-oriented storage is optimal for aggregation. Only required if an installed plugin declares `requires: clickhouse: true`.

**Key insight:** Plugins choose their storage. A plugin that syncs relational data uses Postgres tables. A plugin with heavy analytics workloads declares ClickHouse. Both work through the same API.

### Decision: pgvector for semantic search (not a separate vector DB)

**Why:** One less service to manage. pgvector is a Postgres extension — same connection, same backups, same queries. For datasets with <100K entries, pgvector handles similarity search without Pinecone, Weaviate, or Qdrant.

---

## 3. Plugin Architecture

### Decision: Dynamic route loading from plugin directories

**Why:** Plugins should be installable without modifying core app code. The plugin loader scans `plugins/installed/*/api/routes.py` on startup and registers their FastAPI routers automatically.

**Plugin directory structure:**

```
plugins/installed/{slug}/
  ├── plugin.yaml              # manifest — metadata, nav, dashboards, requires
  ├── api/routes.py            # FastAPI routes (auto-loaded on startup)
  ├── storage/migrations/      # SQL migrations — run on install
  ├── src/sync.py              # data sync script (runs on schedule)
  ├── dashboards/              # YAML dashboard specs
  └── dataport.yaml            # data port tab definitions (legacy — see §6)
```

**Source tiers:**
- `plugins/community/` — third-party stubs with `repository_url`; clone from author's repo on install.
- `plugins/installed/` — runtime destination; always takes priority over stubs.
- Private repos — installed via the explicit `repository_url` form on the Install Plugin page.

**Alternatives considered:**
- Hardcoded imports in main.py — used initially, does not scale.
- Python entry points / setuptools — too complex for operator-managed installs.
- Docker-based plugins — too heavy, adds operational complexity.

### Decision: Plugins manage their own database connections

**Why:** Plugins may connect to different databases (MySQL replicas, external APIs, remote Postgres). They should not depend on the core app's connection pool. Each plugin creates its own connection using env vars injected at startup. Each plugin gets its own Postgres role (`nousviz_plugin_{slug}`) with permissions scoped to its declared tables.

---

## 4. Data Explorer as the Authoring Surface

### Decision: Data Explorer (Connection → Table → Row) is the single user-facing query path

**Why:** Prior to v1.0, NousViz exposed two cross-plugin query mechanisms: hand-written SQL Fusions and a visual Widget Builder. Operators repeatedly mistook one for the other. The Data Explorer collapses the two into a single drilldown: pick a connection (a Postgres connection or an installed plugin), browse its tables, drill into rows, save the view as a widget.

The fusion query engine still exists under the hood as the data explorer's compile target — it just isn't a user-facing concept any more.

**Alternatives considered:**
- Keeping Fusions and the Data Explorer side by side — rejected because two query surfaces means operators have to learn both before knowing which one to reach for.
- Removing cross-plugin combine entirely — rejected because cross-plugin join is the differentiator vs. point-tool dashboards.

---

## 5. Dashboard Builder

### Decision: Free-form grid with plugin-rendered + operator-built widgets

**Why:** Two widget sources need to coexist on the same dashboard:
- **Plugin-rendered** — declared in `plugin.yaml`, rendered by the plugin's own JS bundle.
- **Operator-built** — composed from a Data Explorer view (a saved table / KPI / metric configuration).

A free-form grid (drag-to-resize, inline heading and text edits) allows both to be placed on the same canvas without forcing operators into a fixed grid system.

**Rendering modes for operator-built widgets:**
- **Table** — rows and columns with formatting, sorting, color-coded values.
- **KPI** — horizontal cards showing key metrics.
- **Metric** — single large number with subtitle.

---

## 6. Theming for Embeddable Widgets

### Decision: Widgets use CSS variables for theming, not hardcoded colors

**Why:** When a widget renders inside NousViz it uses the platform's theme. When the same widget is embedded externally, it should adapt to the host's theme. CSS custom properties (`var(--primary)`, `var(--foreground)`, etc.) cascade through the DOM — the widget reads the host's variables automatically.

**Three distribution modes:**
1. **Native** — rendered inside NousViz, inherits platform CSS.
2. **Script embed** — `<script>` tag for external sites, reads host CSS vars with fallbacks.
3. **iframe** — full isolation for legacy or unknown host environments.

---

## 7. Deployment Architecture

### Decision: pm2 + nginx as the default deploy stack

**Why:**
- **pm2** — process manager with auto-restart, memory limits, log rotation, cluster mode for zero-downtime restarts.
- **nginx** — reverse proxy routing `/api/*` to FastAPI, everything else to React static build.

`scripts/setup.sh --server` installs both end-to-end and configures the nginx site. HTTPS is added by `scripts/ssl-setup.sh` (Let's Encrypt) once a domain is pointed at the server.

**Optional:** Operators behind a CDN (Cloudflare, CloudFront, Fastly, Netlify) can put the deploy behind a tunnel or reverse proxy. `scripts/ssl-setup.sh` detects common CDNs and guides the operator accordingly.

### Decision: Push-deploy fallback for low-RAM servers

**Why:** The frontend production build peaks around 1 GB; on a 1 GB box, on-server builds get OOM-killed. `scripts/deploy-local.sh` builds the frontend locally and rsyncs everything up — no server build needed.

---

## 8. Authentication

### Decision: Per-user accounts with 4-role RBAC

**Why:** A single shared password could not enforce who can install plugins, edit dashboards, or read sensitive data. Plugin-installed dashboards routinely contain customer / financial data; viewer-grade users should never see plugin install or RBAC management surfaces.

**Model:**
- Per-user email + bcrypt-hashed password.
- 4 roles: `viewer` (read-only), `analyst` (write dashboards / annotations), `admin` (install plugins / manage users), `superadmin` (system config / RBAC overrides).
- Setup wizard creates the first superadmin in the browser on first visit. Subsequent users join via admin-issued invites.
- Session tokens in `X-Session-Token` header for the dashboard; API keys via `X-API-Key` for programmatic / agent access.
- API keys are SHA-256 hashed at rest, revealed once on creation, revocable from Settings → API Keys.

**Recovery:** Lost-superadmin recovery via `scripts/reset-password.sh` (writes a new bcrypt hash directly to the DB and kills active sessions). Day-to-day "I forgot my password" handled by the in-app reset link (requires SMTP).

**`AUTH_REQUIRED` env var** is the dev escape hatch. Set to `false` for local development; the setup wizard sets it to `true` automatically on first browser visit so production deploys cannot accidentally ship unauthenticated.

---

## 9. License Model

### Decision: Core under Sustainable Use License; SDK and plugins under MIT

**Why:** Two audiences with different needs:
- **Operators** — should be free to self-host, modify, and run NousViz. The SUL permits all non-commercial-resale uses.
- **Plugin authors and SDK consumers** — need permissive reuse. Anything under `sdk/`, `plugins/community/`, `plugins/examples/`, and the bundled utility plugins under `plugins/utilities/` is MIT.

See [LICENSE](LICENSE) for the full scope. See [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md) for dependency licenses.
