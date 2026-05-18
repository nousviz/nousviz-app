import { useState } from "react";
import {
  Package,
  FileCode2,
  Database,
  Zap,
  GitBranch,
  CheckCircle2,
  Copy,
  Check,
  ExternalLink,
  AlertTriangle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Code block with copy button ───────────────────────────────────────────────

function CodeBlock({ code, language = "python" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <div className="relative group rounded-lg bg-[#0d1117] border border-border overflow-hidden my-3">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-secondary/30">
        <span className="text-[10px] font-mono-deck text-muted-foreground uppercase tracking-wider">
          {language}
        </span>
        <button
          onClick={copy}
          className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 text-[10px] font-mono-deck text-muted-foreground hover:text-foreground"
        >
          {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-[12px] leading-relaxed font-mono-deck text-slate-300 whitespace-pre">
        {code.trim()}
      </pre>
    </div>
  );
}

// ── Callout ───────────────────────────────────────────────────────────────────

function Callout({
  type = "info",
  children,
}: {
  type?: "info" | "warning" | "rule";
  children: React.ReactNode;
}) {
  const styles = {
    info: "bg-blue-500/5 border-blue-500/20 text-blue-300",
    warning: "bg-orange-500/5 border-orange-500/20 text-orange-300",
    rule: "bg-primary/5 border-primary/20 text-primary",
  };
  const Icon = type === "warning" ? AlertTriangle : type === "rule" ? CheckCircle2 : Info;
  return (
    <div className={cn("flex gap-3 p-4 rounded-lg border my-4 text-sm font-body", styles[type])}>
      <Icon className="w-4 h-4 shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  );
}

// ── Section (always visible) ─────────────────────────────────────────────────

function Section({
  id,
  icon: Icon,
  title,
  badge,
  children,
}: {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  badge?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <div id={id} className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="flex items-center gap-3 p-5">
        <div className="h-8 w-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-display text-sm text-foreground">{title}</span>
            {badge && (
              <span className="text-[10px] font-mono-deck px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                {badge}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="px-5 pb-5 border-t border-border pt-4">{children}</div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const TOC_ITEMS = [
  ["#structure", "1. Package structure"],
  ["#plugin-yaml", "2. plugin.yaml"],
  ["#routes", "3. API routes"],
  ["#migrations", "4. Migrations"],
  ["#sync", "5. Sync script"],
  ["#dashboards", "6. Dashboards"],
  ["#settings", "7. Plugin settings"],
  ["#extension-points", "8. Extension points"],
  ["#isolation", "9. Isolation rules"],
  ["#fusions", "10. Cross-plugin data"],
  ["#publish", "11. Publishing"],
  ["#limits", "12. Limitations"],
  ["#checklist", "13. Validation checklist"],
];

export default function BuildAPluginPage() {
  return (
    <div className="flex gap-6 max-w-[1200px]">
      {/* Sticky sidebar TOC */}
      <nav className="hidden lg:block w-48 shrink-0">
        <div className="sticky top-[calc(var(--topbar-h)+var(--banner-h,0px)+24px)] space-y-1">
          <p className="text-[10px] font-mono-deck text-muted-foreground uppercase tracking-wider mb-2">On this page</p>
          {TOC_ITEMS.map(([href, label]) => (
            <a
              key={href}
              href={href}
              className="block text-xs text-muted-foreground hover:text-foreground transition-colors py-1 font-body"
            >
              {label}
            </a>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 min-w-0 space-y-6">
      {/* Hero */}
      <div className="bg-card rounded-lg border border-border p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl text-foreground mb-2">Build a Plugin</h2>
            <p className="text-sm text-muted-foreground font-body max-w-xl">
              NousViz plugins connect external data sources to your dashboards, alerts, and fusions.
              This guide covers everything from file structure to publishing.
            </p>
          </div>
          <a
            href="https://github.com/nousviz/nousviz-app/tree/testing/sdk/examples/starter-plugin"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <GitBranch className="w-4 h-4" />
            Starter Template
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-4 gap-3 mt-5">
          {[
            { label: "Files required", value: "1" },
            { label: "Hot-reload on install", value: "Yes" },
            { label: "Restart on uninstall", value: "Required" },
            { label: "Frontend code needed", value: "No" },
          ].map((s) => (
            <div key={s.label} className="bg-secondary/40 rounded-md p-3">
              <div className="text-lg font-display text-foreground">{s.value}</div>
              <div className="text-[11px] text-muted-foreground font-body mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 1. Package structure */}
      <Section id="structure" icon={Package} title="1. Package structure" defaultOpen>
        <p className="text-sm text-muted-foreground font-body mb-3">
          A plugin is a self-contained package that lives in its own GitHub repository at{" "}
          <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">
            github.com/{"<org>"}/plugin-{"<slug>"}
          </code>
          . The Marketplace installs it by cloning into{" "}
          <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">
            plugins/installed/{"{slug}"}/
          </code>{" "}
          — you never commit installed plugins to this repo. Only{" "}
          <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">plugin.yaml</code> is
          required. Everything else is optional.
        </p>
        <CodeBlock
          language="text"
          code={`plugin-{slug}/               ← your GitHub repo root
├── plugin.yaml                 ← REQUIRED — manifest, version, requirements
│
├── api/
│   └── routes.py               ← FastAPI routes, auto-loaded on install
│
├── src/
│   └── sync.py                 ← ETL / data sync script
│
├── storage/
│   └── migrations/
│       ├── 001_initial.sql     ← Schema creation (run on install)
│       └── 001_initial_down.sql ← Schema teardown (run on uninstall)
│
├── dashboards/
│   └── overview.yaml           ← Dashboard tab specs for /plugin/{slug}
│
├── dataport.yaml               ← Data Port table views
├── insights.yaml               ← Insight card queries
├── requirements.txt            ← Python dependencies
└── README.md                   ← Plugin documentation`}
        />
        <Callout type="info">
          The slug is lowercase and hyphenated. It becomes the plugin's URL (
          <code className="font-mono-deck text-xs">/plugin/{"{slug}"}</code>), its install directory name, and
          API prefix. Choose it carefully — it cannot change after publish.
        </Callout>
      </Section>

      {/* 2. plugin.yaml */}
      <Section id="plugin-yaml" icon={FileCode2} title="2. plugin.yaml — the manifest">
        <p className="text-sm text-muted-foreground font-body mb-3">
          The manifest describes your plugin to the marketplace and tells the platform what
          infrastructure it needs, what tables it creates, and how to navigate to it.
        </p>
        <CodeBlock
          language="yaml"
          code={`# Required identity fields
name: my-plugin                  # lowercase-hyphenated, globally unique
display_name: My Plugin
version: 1.0.0                   # semver, bump on every release
description: >
  What your plugin does and why someone would install it.
license: MIT                     # MIT | Apache-2.0 | Sustainable Use | Commercial
icon: bar-chart-2                # any Lucide icon name
category: analytics              # analytics | content | monitoring | integration | productivity | compliance | premium
tags: [analytics, example]
visibility: public               # public | public_premium | fully_private

publisher:
  slug: your-org
  name: Your Name
  website: https://example.com
  contact_email: you@example.com

repository: https://github.com/your-org/plugin-my-plugin

# Infrastructure requirements
# Checked before install — shows a clear error if not met
requires:
  postgres: true                 # needs Postgres (default true)
  postgres_version: "14"         # optional minimum version

# External data sources (generates the settings form in the UI)
connections:
  - name: source_db
    type: mysql
    required: true
    env_prefix: MYPLUGIN_
    label: Source Database
    fields:
      - { name: host,     label: Host,     type: text,     required: true }
      - { name: port,     label: Port,     type: number,   default: 3306 }
      - { name: user,     label: Username, type: text,     required: true }
      - { name: password, label: Password, type: password, required: true }

# Tables this plugin creates — must match your migrations exactly
databases:
  postgres:
    tables: [my_plugin_items, my_plugin_events]

# Datasets — declares tables for the Datasets page and query allowlist
datasets:
  - name: my_plugin_items
    label: My Plugin Items
    db: postgres
    grain: record
    description: Items managed by my plugin
  - name: my_plugin_events
    label: My Plugin Events
    db: postgres
    grain: event
    description: Lifecycle events from my plugin

# Sidebar navigation — one entry per tab
navigation:
  - label: Overview
    href: /plugin/my-plugin/overview
    icon: bar-chart-2
    position: sidebar
  - label: Settings
    href: /plugin/my-plugin/settings
    icon: settings
    position: sidebar

# Dashboard tabs shown at /plugin/my-plugin
dashboards:
  - name: overview              # maps to dashboards/overview.yaml and route /plugin/{slug}/overview
    label: Overview

# Configurable settings (rendered as a form on the Settings tab)
settings:
  - name: sync_enabled
    label: Enable sync
    type: toggle
    default: true
    description: When disabled, Sync Now exits immediately.
  - name: item_limit
    label: Items per sync
    type: number
    default: 5
    description: Number of items to insert per sync run.
  - name: event_label
    label: Event label
    type: text
    default: "sync_run"
    description: The event_type value written on each sync.

# Sync — script path is read from this manifest. Default: src/sync.py.
# Override with sync.script: src/<your-name>.py if your plugin needs a different filename
# (e.g. to avoid sys.modules collisions with sibling plugins also using src/sync.py).`}
        />
        <Callout type="rule">
          <strong>No depends_on for other plugins.</strong> Plugins are fully isolated from each
          other. Cross-plugin data access happens through Fusions created by the operator — not
          through plugin-to-plugin dependencies. Use <code className="font-mono-deck text-xs">requires:</code> only
          for platform infrastructure (Postgres).
        </Callout>
      </Section>

      {/* 3. API routes */}
      <Section id="routes" icon={Zap} title="3. API routes — api/routes.py">
        <p className="text-sm text-muted-foreground font-body mb-3">
          Export a <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">router</code>{" "}
          (FastAPI <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">APIRouter</code>).
          The plugin loader registers it automatically on install and on startup.
        </p>
        <CodeBlock
          language="python"
          code={`from fastapi import APIRouter, HTTPException, Query
from apps.api.src.db import get_pg_conn

router = APIRouter()

# ✓ All plugin API routes are under /api/plugins/{slug}/
#   (the plugin loader mounts them under /api automatically)
@router.get("/plugins/my-plugin/items")
async def list_items(limit: int = Query(default=50, ge=1, le=500)):
    # ✓ get_pg_conn() is a context manager — handles pool return,
    #   commit on success, and rollback on exception automatically
    with get_pg_conn() as conn:
        cur = conn.cursor()
        # ✓ Parameterised query — never f-strings or .format() with user input
        cur.execute(
            "SELECT id, name, status FROM my_plugin_items "
            "ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        cols = [d[0] for d in cur.description]
        return {"items": [dict(zip(cols, row)) for row in cur.fetchall()]}

# Health check — every plugin should implement this
@router.get("/plugins/my-plugin/health-check")
async def health_check():
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM my_plugin_items")
            return {"status": "ok", "items": cur.fetchone()[0]}
    except Exception as e:
        raise HTTPException(500, f"Health check failed: {e}")`}
        />
        <Callout type="warning">
          <strong>Routes outside /plugins/{"{slug}"}/</strong> — if you need a route at a different
          path (e.g. <code className="font-mono-deck text-xs">/go/{"{code}"}</code> for redirect
          handling), use <code className="font-mono-deck text-xs">extra_routers</code>. Do not
          register routes in the core <code className="font-mono-deck text-xs">/api/*</code>{" "}
          namespace.
        </Callout>
        <CodeBlock
          language="python"
          code={`# Extra routers — only for routes that cannot be under /plugins/{slug}/
redirect_router = APIRouter()

@redirect_router.get("/go/{code}")
async def handle_redirect(code: str):
    ...

extra_routers = [
    ("redirect_router", redirect_router, {}),           # mounted at root
    ("pub_router",      pub_router,      {"prefix": "/site"}),  # at /site
]`}
        />
      </Section>

      {/* 4. Migrations */}
      <Section id="migrations" icon={Database} title="4. Migrations — storage/migrations/">
        <p className="text-sm text-muted-foreground font-body mb-3">
          Migrations run automatically when the operator installs your plugin. Every up migration
          must have a matching down migration for clean uninstall.
        </p>
        <CodeBlock
          language="sql"
          code={`-- 001_initial.sql — create tables
-- Rules: IF NOT EXISTS, prefixed table names, no shadowing core tables

CREATE TABLE IF NOT EXISTS my_plugin_items (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL UNIQUE,
    status     TEXT        NOT NULL DEFAULT 'active'
                           CHECK (status IN ('active', 'inactive')),
    metadata   JSONB       NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS my_plugin_items_status_idx ON my_plugin_items(status);`}
        />
        <CodeBlock
          language="sql"
          code={`-- 001_initial_down.sql — reverse 001_initial.sql exactly
-- Run when operator uninstalls with "Remove data" option selected

DROP INDEX IF EXISTS my_plugin_items_status_idx;
DROP TABLE IF EXISTS my_plugin_items;`}
        />
        <Callout type="rule">
          Table names must not shadow core tables:{" "}
          <code className="font-mono-deck text-xs">users</code>,{" "}
          <code className="font-mono-deck text-xs">alerts</code>,{" "}
          <code className="font-mono-deck text-xs">fusions</code>,{" "}
          <code className="font-mono-deck text-xs">annotations</code>,{" "}
          <code className="font-mono-deck text-xs">datasets</code>,{" "}
          <code className="font-mono-deck text-xs">api_keys</code>,{" "}
          <code className="font-mono-deck text-xs">schema_migrations</code>. Use a prefix like{" "}
          <code className="font-mono-deck text-xs">mp_</code> or{" "}
          <code className="font-mono-deck text-xs">myplugin_</code>.
        </Callout>
      </Section>

      {/* 5. Sync script */}
      <Section id="sync" icon={Zap} title="5. Sync script">
        <p className="text-sm text-muted-foreground font-body mb-3">
          The sync script pulls data from your external source into your plugin's tables. The worker
          calls it on your declared schedule and on manual "Sync Now" triggers. The path comes from
          your manifest's <code className="font-mono-deck text-xs">sync.script</code> field —
          default <code className="font-mono-deck text-xs">src/sync.py</code>, overridable to
          anything (e.g. <code className="font-mono-deck text-xs">src/&lt;slug&gt;_sync.py</code>
          if you want to avoid <code className="font-mono-deck text-xs">sys.modules</code>
          collisions with sibling plugins).
        </p>
        <CodeBlock
          language="python"
          code={`import sys, argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from apps.api.src.db import get_pg_conn

def run(since: str | None = None) -> dict:
    """
    Required signature. Called by the worker.
    Returns {"rows_synced": int, "errors": list[str]}.
    Must not raise unhandled exceptions.
    """
    errors = []
    rows_synced = 0
    try:
        with get_pg_conn() as conn:
            # 1. Fetch from your external source
            records = fetch_from_source(since=since)

            # 2. Write to YOUR tables only — never other plugins' tables
            cur = conn.cursor()
            for r in records:
                cur.execute(
                    "INSERT INTO my_plugin_items (name, status) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET status = EXCLUDED.status",
                    (r["name"], r["status"])
                )
                rows_synced += 1
            # context manager commits on exit — no explicit conn.commit() needed
    except Exception as e:
        errors.append(str(e))
        # context manager rolls back on exception — no explicit conn.rollback() needed

    return {"rows_synced": rows_synced, "errors": errors}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since")  # ISO datetime for incremental sync
    args = parser.parse_args()
    result = run(since=args.since)
    sys.exit(1 if result["errors"] else 0)`}
        />
      </Section>

      {/* 6. Dashboards */}
      <Section id="dashboards" icon={FileCode2} title="6. Dashboards — dashboards/*.yaml">
        <p className="text-sm text-muted-foreground font-body mb-3">
          Dashboard specs are rendered by{" "}
          <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">
            DashboardRenderer
          </code>{" "}
          in the frontend. No React code required.
        </p>
        <CodeBlock
          language="yaml"
          code={`# dashboards/overview.yaml
title: My Plugin Overview
db_engine: postgres               # REQUIRED for Postgres-backed plugins
refresh_seconds: 60

panels:
  # Single number
  - id: total_items
    type: stat
    label: Total Items
    query: SELECT count(*) AS value FROM my_plugin_items
    fallback_empty: true          # ← always set this

  # Line chart — query must return 'x' and 'y' columns
  - id: items_over_time
    type: line_chart
    label: Items Over Time
    query: >
      SELECT date_trunc('day', created_at) AS x, count(*) AS y
      FROM my_plugin_items
      WHERE created_at >= now() - interval '30 days'
      GROUP BY 1 ORDER BY 1
    fallback_empty: true

  # Table
  - id: recent_items
    type: table
    label: Recent Items
    query: SELECT name, status, created_at FROM my_plugin_items ORDER BY created_at DESC LIMIT 20
    columns:
      - { key: name,       label: Name }
      - { key: status,     label: Status,  type: badge,
          values: { active: green, inactive: grey } }
      - { key: created_at, label: Created, type: datetime }
    fallback_empty: true`}
        />
        <div className="mt-3 bg-secondary/30 rounded-md p-3">
          <p className="text-xs font-mono-deck text-muted-foreground mb-2">Panel types</p>
          <div className="grid grid-cols-3 gap-2">
            {["stat", "line_chart", "bar_chart", "table", "pie_chart", "heatmap"].map((t) => (
              <code
                key={t}
                className="text-[11px] font-mono-deck bg-secondary px-2 py-1 rounded text-foreground"
              >
                {t}
              </code>
            ))}
          </div>
        </div>
      </Section>

      {/* 7. Plugin settings */}
      <Section id="settings" icon={FileCode2} title="7. Plugin settings">
        <p className="text-sm text-muted-foreground font-body mb-3">
          Declare a <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">settings:</code>{" "}
          field in your <code className="font-mono-deck text-xs bg-secondary px-1.5 py-0.5 rounded">plugin.yaml</code>{" "}
          to get an auto-generated settings form on the Settings tab. No custom routes needed.
        </p>
        <CodeBlock
          language="yaml"
          code={`settings:
  - name: sync_enabled
    label: Enable sync
    type: toggle          # toggle | text | number | select
    default: true
    description: When disabled, Sync Now exits immediately.
  - name: mode
    label: Sync mode
    type: select
    default: full
    options: [full, incremental, dry_run]
    description: How the sync script runs.`}
        />
        <p className="text-sm text-muted-foreground font-body mt-3 mb-2">
          Settings are stored and retrieved via generic API endpoints:
        </p>
        <CodeBlock
          language="text"
          code={`GET  /api/plugins/{slug}/settings     → { "settings": { "sync_enabled": true, ... } }
POST /api/plugins/{slug}/settings     → { "sync_enabled": false }  → saves to Postgres`}
        />
        <Callout type="info">
          Settings persist in the <code className="font-mono-deck text-xs">plugin_settings</code> table.
          Your sync script can read them via the API or directly from the table.
        </Callout>
      </Section>

      {/* 8. Extension points */}
      <Section id="extension-points" icon={Package} title="8. Extension points — dataport & insights">
        <p className="text-sm text-muted-foreground font-body mb-4">
          Drop these files in your plugin package to contribute to core platform views.
          No core code changes required.
        </p>

        <h4 className="text-sm font-display text-foreground mb-2">dataport.yaml</h4>
        <p className="text-xs text-muted-foreground font-body mb-2">
          Adds read-only table views to the Data Port page.
        </p>
        <CodeBlock
          language="yaml"
          code={`tabs:
  - id: items
    label: Items
    table: my_plugin_items        # must be in plugin.yaml datasets
    columns:
      - { key: name,   label: Name }
      - { key: status, label: Status, type: badge,
          values: { active: green, inactive: grey } }
    default_sort: created_at DESC
    page_size: 50
    filters:
      - { key: status, label: Status, type: select, options: [active, inactive] }`}
        />

        <h4 className="text-sm font-display text-foreground mt-4 mb-2">insights.yaml</h4>
        <p className="text-xs text-muted-foreground font-body mb-2">
          Adds cards to the Insights page. Queries run on every page load — keep them fast.
        </p>
        <CodeBlock
          language="yaml"
          code={`queries:
  - id: summary
    label: My Plugin Summary
    description: Item counts and last sync status
    sql: >
      SELECT count(*) AS total,
             count(*) FILTER (WHERE status = 'active') AS active
      FROM my_plugin_items
    fallback_empty: true          # ← always set this`}
        />
      </Section>

      {/* 9. Isolation rules */}
      <Section id="isolation" icon={AlertTriangle} title="9. Plugin isolation rules" badge="Strict">
        <Callout type="rule">
          These rules are strictly enforced. Violating them will cause plugin rejection during
          marketplace review.
        </Callout>
        <div className="space-y-3 mt-2">
          {[
            {
              title: "Never import from other plugins",
              bad: `from plugin_routes_other import get_data  # WRONG`,
              good: `# Read from your own tables only`,
            },
            {
              title: "Never query other plugins' tables",
              bad: `cur.execute("SELECT * FROM other_plugin_items")  # WRONG`,
              good: `cur.execute("SELECT * FROM my_plugin_items")  # CORRECT`,
            },
            {
              title: "Always close Postgres connections",
              bad: `conn = get_pg_conn()\ncur.execute(...)  # AttributeError: no .close() — get_pg_conn() is a context manager`,
              good: `with get_pg_conn() as conn:\n    cur.execute(...)  # commits on exit, rolls back on exception`,
            },
            {
              title: "Always use parameterised queries",
              bad: `cur.execute(f"SELECT * FROM t WHERE name = '{name}'")  # SQL injection`,
              good: `cur.execute("SELECT * FROM t WHERE name = %s", (name,))`,
            },
          ].map((rule) => (
            <div key={rule.title} className="rounded-md border border-border overflow-hidden">
              <div className="px-3 py-2 bg-secondary/30 text-xs font-display text-foreground">
                {rule.title}
              </div>
              <div className="grid grid-cols-2 divide-x divide-border">
                <div>
                  <div className="px-3 pt-2 pb-1 text-[10px] font-mono-deck text-red-400">wrong</div>
                  <pre className="px-3 pb-3 text-[11px] font-mono-deck text-red-300/70 whitespace-pre-wrap">
                    {rule.bad}
                  </pre>
                </div>
                <div>
                  <div className="px-3 pt-2 pb-1 text-[10px] font-mono-deck text-green-400">correct</div>
                  <pre className="px-3 pb-3 text-[11px] font-mono-deck text-green-300/70 whitespace-pre-wrap">
                    {rule.good}
                  </pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* 10. Cross-plugin data / Fusions */}
      <Section id="fusions" icon={GitBranch} title="10. Cross-plugin data — use Fusions">
        <p className="text-sm text-muted-foreground font-body mb-3">
          Plugins are fully isolated. If an operator wants to combine data from two plugins —
          for example, data from Plugin A alongside data from Plugin B — they create a{" "}
          <strong className="text-foreground">Fusion</strong>.
        </p>
        <p className="text-sm text-muted-foreground font-body mb-3">
          A Fusion is a named SQL query defined in the Fusions UI. It runs against any installed
          plugin's tables. Neither plugin needs to know about the other.
        </p>
        <CodeBlock
          language="sql"
          code={`-- Example Fusion: combining data from two plugins
-- Neither plugin imports from or queries the other.
-- The operator writes this in the Fusions UI.

SELECT
    hi.name,
    hi.status,
    he.event_count
FROM hello_items hi
LEFT JOIN (
    SELECT date_trunc('day', created_at) AS day, count(*) AS event_count
    FROM hello_events
    GROUP BY 1
) he ON he.day = date_trunc('day', hi.created_at)
ORDER BY hi.created_at DESC
LIMIT 90`}
        />
        <Callout type="info">
          Your plugin only needs to expose its own data cleanly. The operator handles cross-plugin
          joins through Fusions. Do not try to implement cross-plugin logic inside your plugin code.
        </Callout>
      </Section>

      {/* 11. Publishing */}
      <Section id="publish" icon={GitBranch} title="11. Publishing your plugin">
        <div className="space-y-4 text-sm font-body text-muted-foreground">
          <div>
            <p className="font-display text-foreground text-xs mb-1">Official plugins (NousViz org)</p>
            <ol className="space-y-1 list-decimal list-inside text-xs">
              <li>Open an issue in the NousViz repo requesting a plugin repo under the nousviz org</li>
              <li>We create <code className="font-mono-deck">github.com/nousviz/plugin-{"{slug}"}</code> and give you access</li>
              <li>You develop and publish the full plugin package to that repo, tagged with <code className="font-mono-deck">v{"{version}"}</code></li>
              <li>Open a PR to this repo adding a <code className="font-mono-deck">plugin.yaml</code> stub to <code className="font-mono-deck">plugins/official/{"{slug}"}/</code> — the stub contains only identity, version, requires, and repository fields. No code.</li>
              <li>We review the stub and the plugin repo for isolation compliance and security</li>
              <li>On merge, the plugin appears in the Marketplace and installs by cloning from the tagged release</li>
            </ol>
          </div>
          <div>
            <p className="font-display text-foreground text-xs mb-1">Community plugins</p>
            <ol className="space-y-1 list-decimal list-inside text-xs">
              <li>Publish your plugin repo publicly on GitHub with a version tag (<code className="font-mono-deck">v1.0.0</code>)</li>
              <li>Open a PR to the NousViz repo adding a manifest stub to <code className="font-mono-deck">plugins/community/{"{slug}"}/</code></li>
              <li>Stub must include <code className="font-mono-deck">repository:</code> pointing to your public repo and <code className="font-mono-deck">version:</code> matching your tag</li>
              <li>We review the manifest only — your plugin code stays in your repo</li>
            </ol>
          </div>
          <div>
            <p className="font-display text-foreground text-xs mb-1">Private plugins</p>
            <p className="text-xs">
              Add a <code className="font-mono-deck">plugin.yaml</code> stub to <code className="font-mono-deck">plugins/community/</code> on your local install with <code className="font-mono-deck">visibility: fully_private</code> and your private repo URL. The install endpoint will clone from it using your machine's git credentials. No marketplace listing required.
            </p>
          </div>
        </div>
      </Section>

      {/* 12. Limitations */}
      <Section id="limits" icon={AlertTriangle} title="12. Limitations">
        <div className="space-y-2">
          {[
            ["Route hot-reload", "Routes are added on install without restart. They cannot be removed without an API restart — uninstall requires a restart to fully deactivate routes."],
            ["No plugin-to-plugin imports", "Plugins cannot import each other's Python modules. Cross-plugin data flows only through Fusions."],
            ["No shared state", "Plugins cannot share in-memory state. Use Postgres tables for any state that needs to outlive a request."],
            ["requirements.txt is global", "Python dependencies from requirements.txt are installed into the shared .venv — not isolated per plugin. Avoid version pinning that conflicts with other packages."],
            ["No frontend code in this repo", "Plugins cannot ship custom React components into this repo. Use DashboardRenderer for data visualisation. Custom widgets must be pre-registered in COMPONENT_REGISTRY if they already exist in apps/web/src/widgets/."],
          ].map(([title, body]) => (
            <div key={title as string} className="flex gap-3 p-3 rounded-md bg-secondary/30 border border-border">
              <AlertTriangle className="w-3.5 h-3.5 text-orange-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-display text-foreground mb-0.5">{title}</p>
                <p className="text-xs font-body text-muted-foreground">{body}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* 13. Checklist */}
      <Section id="checklist" icon={CheckCircle2} title="13. Validation checklist" badge="Before publishing">
        <p className="text-xs text-muted-foreground font-body mb-3">
          Run through this before opening a PR or submitting to the marketplace.
        </p>
        <div className="space-y-2">
          {[
            ["plugin.yaml", [
              "name is lowercase-hyphenated and globally unique",
              "version is bumped from previous release",
              "datasets: field lists all tables your plugin creates",
              "navigation declares one entry per tab (e.g. /plugin/{slug}/overview, /plugin/{slug}/settings)",
              "repository URL is your external plugin repo",
              "No depends_on field — plugins are isolated",
            ]],
            ["api/routes.py", [
              "All routes under /plugins/{slug}/ (served as /api/plugins/{slug}/)",
              "All Postgres connections use `with get_pg_conn() as conn:` (context manager)",
              "No imports from other plugin modules",
              "No SQL queries against tables not in this plugin's databases",
              "All SQL uses parameterised queries — no f-string SQL",
            ]],
            ["Migrations", [
              "Every NNN_name.sql has a matching NNN_name_down.sql",
              "Up migrations use CREATE TABLE IF NOT EXISTS",
              "Down migrations use DROP TABLE IF EXISTS",
              "No table names shadow core tables",
            ]],
            ["End-to-end", [
              "Fresh install → API starts without error",
              "GET /api/plugins/{slug}/health-check returns 200",
              "Uninstall with remove_data=true → tables dropped cleanly",
              "Reinstall after uninstall → migrations reapply cleanly",
            ]],
          ].map(([section, items]) => (
            <div key={section as string} className="rounded-md border border-border overflow-hidden">
              <div className="px-3 py-2 bg-secondary/30 text-xs font-display text-foreground">
                {section as string}
              </div>
              <ul className="p-3 space-y-1.5">
                {(items as string[]).map((item) => (
                  <li key={item} className="flex items-start gap-2 text-xs font-body text-muted-foreground">
                    <div className="w-3.5 h-3.5 rounded border border-border shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      {/* Footer CTA */}
      <div className="bg-card rounded-lg border border-border p-6 text-center">
        <h3 className="font-display text-lg text-foreground mb-2">Ready to build?</h3>
        <p className="text-sm text-muted-foreground font-body mb-4 max-w-md mx-auto">
          Clone the starter template and follow the guide above. Join the community for help.
        </p>
        <div className="flex items-center justify-center gap-3">
          <a
            href="https://github.com/nousviz/nousviz-app/tree/testing/sdk/examples/starter-plugin"
            target="_blank"
            rel="noopener noreferrer"
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-body hover:bg-primary/90 transition-colors flex items-center gap-2"
          >
            <GitBranch className="w-4 h-4" />
            Starter Template
            <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href="https://github.com/nousviz/nousviz-app/tree/testing/docs/plugin-architecture.md"
            target="_blank"
            rel="noopener noreferrer"
            className="h-9 px-4 rounded-md bg-secondary text-foreground text-sm font-body hover:bg-secondary/80 transition-colors flex items-center gap-2"
          >
            Full Spec
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
    </div>
  );
}
