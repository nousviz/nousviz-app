# NousViz

**The open-source data intelligence platform.**

Browse any data source, build dashboards on top of it, get alerted when the numbers move — all through a plugin ecosystem. Runs natively on Postgres. No Docker required.

> Your data. Finally visible.

## What is NousViz?

NousViz is a modular platform for ingesting, exploring, and visualizing data from any source. It's built around three surfaces:

- **Data Explorer** — Pick a connection, browse its tables, drill into rows. Save any view as a dashboard widget.
- **Plugin widgets** — Plugins ship pre-built widgets via their manifest. Drag them onto dashboards.
- **Dashboards** — Free-form grid that composes both. Share with a password-protected link.

Each data source is a self-contained plugin that:

- Defines its own datasets and schemas
- Syncs data on a schedule
- Provides dashboard widgets and alerts
- Exposes data via MCP for AI agents

The core platform runs entirely on PostgreSQL — no additional databases required to get started. Analytics plugins can bring their own storage dependencies (e.g. ClickHouse) and declare them in their manifest.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/nousviz/nousviz-app.git
cd nousviz-app

# 2. Run setup — installs Postgres natively, creates venv, runs migrations
./scripts/setup.sh

# 3. Set your encryption key in .env (required before first run)
#    Generate one: python3 -c "import secrets; print(secrets.token_hex(32))"
nano .env

# 4. Start the API server
source .venv/bin/activate
python3 -m uvicorn apps.api.src.main:app --reload --port 8000

# 5. Start the frontend (separate terminal)
cd apps/web
npm run dev
```

Visit `http://localhost:5173` to see the dashboard.

> **Requires:** Python 3.10–3.12, Node.js 18+. Python 3.13+ is not yet supported. `setup.sh` installs PostgreSQL automatically via your system package manager (Homebrew on macOS, apt/dnf on Linux).

## Architecture

```
External APIs → Plugins (sync scripts) → Storage → Dashboards / Alerts / MCP
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite + Tailwind | Dashboard UI, plugin marketplace |
| API | Python (FastAPI) | REST API, query proxy |
| Worker | Python | Background sync jobs, alerts |
| MCP | FastMCP | AI agent connectivity |
| Core DB | PostgreSQL | Configs, credentials, dashboards, alerts, annotations |
| Plugin DB | Plugin-declared | Each plugin declares its own storage (Postgres tables, ClickHouse, etc.) |

## Features

- **Data Explorer** — Connection → Table → Row drilldown across every installed plugin and every Postgres connection. Sort, filter, save any view as a widget.
- **Dashboard builder** — Free-form grid with drag-to-resize. Compose plugin-provided widgets and your own Data Explorer views side by side.
- **Multi-user accounts** — Per-user email + password auth, 4-role RBAC (viewer/analyst/admin/superadmin), invite flow, session management
- **Plugin ecosystem** — Install data sources from the marketplace, each with its own dashboards, alerts, and sync schedules
- **Alerts** — Threshold (drop, rise, absolute) and zero-check alerts on any numeric metric, with email and webhook delivery
- **Webhooks** — Inbound (receive data via generated URLs) and outbound (typed Slack messages, plus generic webhook POST to any URL for Discord, PagerDuty, custom integrations)
- **Annotations** — Tag events across datasets with notes and scoring
- **Shared links** — Password-protected public views of any dashboard
- **Admin CLI** — Web-based terminal for superadmins (user management, health checks, migrations, logs)
- **SMTP email** — Branded templates for invites, alerts, and password resets
- **Health monitoring** — System health checks with email alerts on state transitions
- **Dark mode** — Multiple color themes including sovereign dark

## Plugins

### Reference
- **[starter-plugin](sdk/examples/starter-plugin/)** — Annotated template demonstrating the full plugin contract (manifest, hooks, sync, dataport, dashboards). Use as the starting point for building your own plugin.

### Utility plugins (bundled)
- **ClickHouse** — Column-oriented analytics database
- **MySQL** — Shared MySQL connection for data plugins
- **Webhooks** — Inbound data ingestion + outbound alert delivery

### Build your own
Build plugins using the [Plugin SDK](sdk/). See the [plugin architecture docs](docs/plugin-architecture.md) and the [starter template](sdk/examples/starter-plugin/). Install from private repos via the [Install Plugin](/install-plugin) page.

## Plugin Marketplace

NousViz includes a built-in marketplace where you can discover, install, and manage plugins. Companies can publish their own plugins.

## Server Deploy (DigitalOcean, Hetzner, AWS, etc.)

**Server requirements**:
- Ubuntu 24.04+ (Debian 12+ also works) with `sudo` and SSH
- **2 GB RAM recommended.** The frontend production build peaks around 1 GB;
  on a 1 GB box the build is OOM-killed. If you're on 1 GB, build the frontend
  on your laptop and use [Push-deploy from your laptop](#push-deploy-from-your-laptop-optional)
  instead of running `setup.sh --server` on the box.
- 10 GB disk
- Postgres, Node 20, Python 3.10–3.12, and nginx are installed by `setup.sh`
  automatically — you don't need to pre-install them.

```bash
# 1. Clone and run server setup
#    (installs Postgres + Node + nginx, builds frontend, configures + reloads
#     nginx, starts pm2)
#    Install under /opt — nginx (running as www-data) needs traversal access,
#    which it doesn't have on /root.
sudo git clone https://github.com/nousviz/nousviz-app.git /opt/nousviz
cd /opt/nousviz
sudo ./scripts/setup.sh --server

# 2. Open http://your-server-ip — complete the setup wizard
#    Creates the first superadmin user and enables auth entirely in the
#    browser. No SSH required after this point.

# 3. Enable HTTPS (requires a real domain — point an A record at this server first)
sudo ./scripts/ssl-setup.sh app.example.com
```

`setup.sh --server` finishes the nginx install end-to-end: copies
`infra/nginx.conf` into `/etc/nginx/sites-available/nousviz`, symlinks it into
`sites-enabled/`, removes the default site, runs `nginx -t`, and reloads. No
manual nginx commands needed.

See [docs/startup.md](docs/startup.md) for detailed server setup instructions, the full [HTTPS setup section](docs/startup.md#https-setup-server-only--domain-required) with troubleshooting, common issues, and pm2 survive-reboot configuration.

### Push-deploy from your laptop (optional)

If your server can't pull from GitHub directly, use `scripts/deploy-local.sh` to build the frontend locally and rsync everything up. Set your target in one of three ways:

```bash
# Option A — positional arg
./scripts/deploy-local.sh user@your-server.example.com

# Option B — env var
export NOUSVIZ_DEPLOY_TARGET=user@your-server.example.com
./scripts/deploy-local.sh

# Option C — config file (recommended for repeated use)
mkdir -p ~/.config/nousviz
echo 'export NOUSVIZ_DEPLOY_TARGET=user@your-server.example.com' > ~/.config/nousviz/deploy.env
chmod 600 ~/.config/nousviz/deploy.env
./scripts/deploy-local.sh
```

Precedence: positional arg > env var > config file. Run with `--restart` to skip the build/sync and just restart server processes.

## Operator Recovery

Lost the only superadmin password? SMTP not configured (so the in-app "Forgot password?" flow doesn't work)? Use the recovery script:

```bash
# On the server (or wherever the project is checked out):
./scripts/reset-password.sh user@example.com
# Prompts for new password (no echo). Updates the user's password_hash
# directly via parameterized SQL — bypasses the API entirely.
```

The script:

- Prompts for the new password using `getpass` (won't echo, won't go in shell history)
- Hashes with bcrypt rounds=12 — same algorithm as the API
- Updates `users.password_hash` directly via `psycopg2` parameterized SQL (so bcrypt's `$` characters can't break out)
- Kills all active sessions for the user (so a hijacker with a stolen session can't keep using it after recovery)
- Writes an audit row to `rbac_config_audit` with `action='password_reset_cli'`

For everyday "I forgot my password" scenarios, use the in-app **Forgot password?** link on the login screen instead — that path requires SMTP configured and emails the user a one-hour reset link.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[Sustainable Use License](LICENSE) — free to self-host and modify. See [LICENSE](LICENSE) for full terms.

Community plugins, examples, and the SDK are licensed under MIT.

## Links

- Website: [nousviz.com](https://nousviz.com)
- GitHub: [github.com/nousviz/nousviz-app](https://github.com/nousviz/nousviz-app)
