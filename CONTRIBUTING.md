# Contributing to NousViz

Thanks for your interest in contributing. This document covers how to get set up and what we expect from contributions.

## Prerequisites

- Python 3.10+
- Node.js 18+

`setup.sh` handles everything else — it installs PostgreSQL natively via your system package manager and sets up the virtual environment.

## Running locally

1. Clone the repo:
   ```bash
   git clone https://github.com/nousviz/nousviz-app.git
   cd nousviz-app
   ```

2. Run setup:
   ```bash
   ./scripts/setup.sh
   ```
   This installs and starts Postgres, creates the `nousviz` database, runs all migrations, and installs Python and Node dependencies.

3. Set your encryption key in `.env`:
   ```bash
   # .env.example is already copied by setup.sh
   # Generate a key and paste it in:
   python3 -c "import secrets; print(secrets.token_hex(32))"
   nano .env  # set NOUSVIZ_ENCRYPTION_KEY
   ```

4. Start the API (port 8000):
   ```bash
   source .venv/bin/activate
   python3 -m uvicorn apps.api.src.main:app --reload --port 8000
   ```

5. Start the frontend in a separate terminal (port 5173):
   ```bash
   cd apps/web
   npm run dev
   ```

Visit http://localhost:5173

## Project structure

- `apps/api/` — FastAPI backend
- `apps/web/` — React/Vite frontend
- `apps/worker/` — background sync jobs and alert runner
- `apps/mcp/` — MCP server for AI agent connectivity
- `core/` — shared libraries (encryption, connections)
- `plugins/` — plugin system (see Plugin Development below)
- `sdk/` — plugin development SDK
- `storage/` — database migrations and schema

## Plugin development

Plugins are the primary extension point. Each plugin provides its own datasets, dashboards, sync scripts, and API routes.

Plugins declare their own storage dependencies in `plugin.yaml` — core Postgres is always available; plugins can additionally declare ClickHouse, MySQL, or other connections. These are installed and configured when the plugin is installed, not during core setup.

Start with the starter template: `sdk/examples/starter-plugin/`

See the SDK in `sdk/` for full documentation.

## Pull requests

- Branch from `main`, name your branch `feature/...` or `fix/...`
- Open PRs against `main`
- One logical change per PR
- Include a description of what changed and why
- Run `npm run lint` in `apps/web` before submitting frontend changes
- Add a `## [Unreleased]` entry to `CHANGELOG.md` describing your change

## Code conventions

- Single responsibility per file
- SQL queries built from dashboard YAML specs — not hardcoded in frontend
- All data tables use monospace numbers (`font-mono-deck` class)
- Empty states always include a CTA
- Credentials never returned to the browser in plaintext

## License

The platform is licensed under the [Sustainable Use License](LICENSE) — free to self-host and modify.

Plugin examples, the SDK, and community plugins are MIT licensed.
