"""
NousViz API Server

Core routes are hardcoded. Plugin routes are loaded dynamically
from plugins/installed/{slug}/api/routes.py — install a plugin
and restart to add its routes.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load .env on startup so pm2 restarts always pick up the latest values.
# os.environ takes precedence (override=False) so explicit env vars still win.
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=True)
from fastapi.middleware.cors import CORSMiddleware

from .plugin_loader import load_plugin_routes
from .middleware.auth import AuthMiddleware
from .middleware.errors import ErrorSanitizationMiddleware
from .middleware.nocache import NoCacheAPIMiddleware

# ── Core routes (always present, part of the platform) ────────────────
from .routes import (
    query, plugins, health, sync, annotations, alerts, notes,
    activity, share, jobs, datasets, auth, data_port,
    insights, settings, docs, launchpad, admin,
    connections as connections_routes, dashboards,
    widget_runtime,  # B156 (v0.9.4.7): host React shim for plugin widgets
    catalog,         # B170-rev2 (v0.9.5.3): data catalog (information_schema-driven)
    system as system_routes,  # B230 (v0.9.8.3): RBAC audit matrix endpoint
    resource_acls as resource_acls_routes,  # B248 (v0.9.10.7): per-resource ACL admin
    maintenance,     # B279 (v0.9.11.17): retention policies API
    oauth as oauth_routes,  # B312 (v0.10.3): core-owned OAuth callback for plugins
)

logger = logging.getLogger("nousviz.api")

from pathlib import Path as _Path
_VERSION_FILE = _Path(__file__).resolve().parents[3] / "VERSION"
try:
    _API_VERSION = _VERSION_FILE.read_text().strip()
except OSError:
    _API_VERSION = "unknown"

# P205 (v0.9.0): startup SDK import check. If nousviz_sdk can't be
# imported here, every plugin will silently 404. Record it so the
# health endpoint + install gate can surface the issue instead of
# letting it hide in pm2 stderr.
SDK_AVAILABLE: bool = False
SDK_VERSION: str | None = None
SDK_IMPORT_ERROR: str | None = None
try:
    import nousviz_sdk as _sdk
    SDK_AVAILABLE = True
    SDK_VERSION = getattr(_sdk, "__version__", "unknown")
    logger.info(f"nousviz_sdk v{SDK_VERSION} available")

    # P208 fix (v0.9.0): register an in-process credential resolver.
    # The credential broker is on a Unix socket inside the jobs-worker;
    # plugin api/routes.py handlers run in this API process and don't
    # have a broker token. They need a different resolution path —
    # decrypt directly using the encryption key the API already holds.
    #
    # The SDK calls our resolver instead of the broker when this is
    # registered. Subprocesses (worker-spawned) don't run main.py and
    # thus don't register, so they fall through to the broker.
    def _api_credential_resolver(plugin_id: str) -> dict:
        """Decrypt all credentials for a plugin in the API process.
        Returns the same shape the broker would: field_name -> value,
        plus __db__ for the SDK's get_pg_conn().

        Special plugin_id `__core__` means "I just want __db__" (used by
        SDK's get_pg_conn() when called from a context without a
        specific plugin_id — e.g., a plugin route handler that didn't
        set one). Skip the per-plugin decrypt in that case.
        """
        creds: dict = {}
        if plugin_id != "__core__":
            try:
                from .plugin_credentials import list_plugin_credentials_decrypted
                creds = list_plugin_credentials_decrypted(plugin_id) or {}
            except Exception as _exc:
                logger.warning(f"resolver: decrypt failed for {plugin_id}: {_exc}")
                creds = {}
        creds["__db__"] = {
            "user": os.environ.get("NOUSVIZ_PLUGIN_USER", "nousviz_plugin"),
            "password": os.environ.get("NOUSVIZ_PLUGIN_PASSWORD", ""),
        }
        return creds

    try:
        from nousviz_sdk._broker_client import register_resolver
        register_resolver(_api_credential_resolver)
        logger.info("registered in-process credential resolver for plugin route handlers")
    except Exception as _res_err:
        logger.warning(f"could not register API credential resolver: {_res_err}")

except ImportError as _sdk_err:
    SDK_IMPORT_ERROR = str(_sdk_err)
    logger.error(
        f"nousviz_sdk not importable: {SDK_IMPORT_ERROR}. "
        f"Plugins will not load routes until pip install -e sdk/ succeeds."
    )
    # Also surface in app_logs so operators see it in /system/logs, not
    # just pm2 stderr. Lazy import so this module stays usable even when
    # the import would fail.
    try:
        from .log_events import log_job_event
        log_job_event(
            "error",
            "API starting without nousviz_sdk — plugins will not load routes.",
            {"exception_message": SDK_IMPORT_ERROR, "source": "startup"},
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


# ── App ───────────────────────────────────────────────────────────────

# B211 (v0.9.7.0): top-level OpenAPI tags with operator-relevant descriptions.
# Every router below should declare its `tags=[...]` matching one of these.
# After the tag sweep, no operation in /openapi.json should be untagged.
OPENAPI_TAGS = [
    {"name": "auth", "description": "Login, sessions, password reset, API keys."},
    {"name": "health", "description": "Health checks and version info."},
    {"name": "plugins", "description": "Install, uninstall, configure, list installed plugins."},
    {"name": "sync", "description": "Manual sync triggers, schema setup, plugin health checks."},
    {"name": "jobs", "description": "Job runs (sync + hooks). Fire-now, cancel, pause, resume."},
    {"name": "dashboards", "description": "Dashboard CRUD, rendering, revisions."},
    {"name": "widget-runtime", "description": "Plugin-served widget execution context."},
    {"name": "insights", "description": "Generated insights and discovery."},
    {"name": "annotations", "description": "Per-table operator notes."},
    {"name": "alerts", "description": "Alert rules and trigger history."},
    {"name": "notes", "description": "Free-form operator notes."},
    {"name": "connections", "description": "Operator-defined database connections."},
    {"name": "data-port", "description": "Browse rows from any plugin table."},
    {"name": "datasets", "description": "Plugin-declared dataset registry."},
    {"name": "catalog", "description": "Catalog service for table metadata (B170-rev2)."},
    {"name": "query", "description": "Plugin-scoped SQL query execution."},
    {"name": "share", "description": "Shared link generation and access."},
    {"name": "launchpad", "description": "Operator landing page widgets."},
    {"name": "activity", "description": "Activity feed."},
    {"name": "admin", "description": "Admin CLI, /system/logs, recovery commands."},
    {"name": "settings", "description": "Platform settings, deploy keys, theme."},
    {"name": "docs", "description": "Internal documentation routes."},
]

OPENAPI_DESCRIPTION = """\
**NousViz API** — operator-facing platform API.

## Authentication

Most endpoints require a session token in the `X-Session-Token` header. Get
one via `POST /api/auth/login`. Some endpoints accept an API key via
`X-API-Key` instead.

## Where to find what

- [/docs/api](/docs/api) — interactive native reference (operators)
- [/openapi.json](/openapi.json) — raw spec, JSON (tooling, generated SDK clients)
- [/openapi.yaml](/openapi.yaml) — same spec, YAML-encoded (LLM context, PR diffs)
- SDK reference — `docs/sdk-reference.md` *(arrives in v0.9.7.4)*

## Plugin routes

Plugins can register their own HTTP routes. By default these are NOT shown
here (the spec only documents the **platform** API, not individual plugins).
Plugin authors can opt in by setting `openapi_public: true` in their
`plugin.yaml`.

## Versioning

The platform is pre-1.0. Breaking changes are documented in the
[CHANGELOG](https://github.com/nousviz/nousviz-app/blob/main/CHANGELOG.md).
"""

app = FastAPI(
    title="NousViz API",
    description=OPENAPI_DESCRIPTION,
    version=_API_VERSION,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    docs_url=None,
    redoc_url=None,
    contact={
        "name": "NousViz",
        "url": "https://github.com/nousviz/nousviz-app",
    },
    license_info={
        "name": "Sustainable Use License v1.0",
        "url": "https://github.com/nousviz/nousviz-app/blob/main/LICENSE",
    },
    servers=[
        {"url": "https://nousviz.online", "description": "Production"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ],
)


# B211 (v0.9.7.0): custom OpenAPI override to inject securitySchemes.
# FastAPI's default emission doesn't declare securitySchemes unless they're
# applied as `Security()` dependencies on routes — which would tightly couple
# the auth declaration to every route. We use the documented FastAPI pattern
# of overriding `app.openapi()` to add the schemes at spec-generation time.
# The actual auth enforcement happens via Depends(requires("...")) on each
# route reading the X-Session-Token header; this is documentation, not
# enforcement.
def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
        contact=app.contact,
        license_info=app.license_info,
        servers=app.servers,
    )
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "sessionToken": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Session-Token",
            "description": (
                "Session token from `POST /api/auth/login`. "
                "Required for most endpoints."
            ),
        },
        "apiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": (
                "Programmatic API key. Alternative to session token "
                "for scripted automation."
            ),
        },
    }
    schema["security"] = [{"sessionToken": []}, {"apiKey": []}]
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi


# B211: serve the same spec as YAML for LLM context (more token-efficient
# than JSON) and for PR reviews that diff better in YAML.
@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml():
    """B211 (v0.9.7.0): YAML-encoded OpenAPI spec.

    Serves the same content as /openapi.json but YAML-encoded. Useful for:
      - LLM context windows (YAML is more token-efficient)
      - PR review diffs (YAML reads better in code review tools)
      - Tooling that prefers YAML over JSON

    The spec content is identical between the two formats — both come
    from the same _custom_openapi() generator.
    """
    import yaml as _yaml
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        _yaml.safe_dump(_custom_openapi(), sort_keys=False),
        media_type="application/x-yaml",
    )

# Build default CORS origins from WEB_PORT so multi-instance setups work (B103).
# Explicit CORS_ORIGINS env var takes priority when set.
_web_port = os.environ.get("WEB_PORT", "5173")
_default_origins = f"http://localhost:{_web_port}"
_cors_origins = os.environ.get("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Session-Token", "X-Modeler-Key"],
)

# Auth middleware — set AUTH_REQUIRED=true in .env to enable
app.add_middleware(AuthMiddleware)

# Error sanitization — catches unhandled exceptions, returns safe messages
app.add_middleware(ErrorSanitizationMiddleware)

# No-cache headers on every /api/* response (B194 — stale-cache bug on /api/jobs
# triggered this during v0.3.0 dev; defence in depth alongside nginx edge headers)
app.add_middleware(NoCacheAPIMiddleware)

# ── Core routes ───────────────────────────────────────────────────────
# These are platform features, not plugins. Always available.

app.include_router(query.router, prefix="/api")
app.include_router(plugins.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(share.router, prefix="/api")
app.include_router(jobs.router)          # /api/jobs prefix built-in
app.include_router(datasets.router)      # /api/datasets prefix built-in
app.include_router(auth.router)          # /api/auth prefix built-in
app.include_router(data_port.router)     # /api/data-port prefix built-in
app.include_router(catalog.router)       # /api/catalog prefix built-in (B170-rev2)
app.include_router(insights.router)     # /api/insights prefix built-in
app.include_router(settings.router)    # /api/settings prefix built-in
app.include_router(docs.router, prefix="/api")     # /api/docs
app.include_router(launchpad.router)   # /api/launchpad prefix built-in
app.include_router(admin.router)      # /api/admin prefix built-in
app.include_router(connections_routes.router)  # /api/connections prefix built-in
app.include_router(dashboards.router)  # /api/dashboards prefix built-in
app.include_router(widget_runtime.router)  # /api/widget-runtime prefix built-in (B156)
app.include_router(system_routes.router)  # /api/system prefix built-in (B230)
app.include_router(resource_acls_routes.router)  # /api/resource-acls prefix built-in (B248)
app.include_router(maintenance.router)  # /api/maintenance prefix built-in (B279)
app.include_router(oauth_routes.router)  # /api/oauth prefix built-in (B312)

# ── Plugin routes (dynamically loaded) ────────────────────────────────
# Scans plugins/installed/*/api/routes.py and registers their routers.
# Install a plugin → restart → its routes are live.

# Set up operator-visible DB logging (P104)
try:
    from .log_handler import setup_db_logging
    setup_db_logging()
except Exception as e:
    logger.warning(f"DB log handler setup failed (table may not exist yet): {e}")

loaded_plugins = load_plugin_routes(app)
logger.info(f"Loaded {len(loaded_plugins)} plugin(s): {loaded_plugins}")

# Refresh utility plugin capability registry
from .routes.plugins import refresh_capabilities
refresh_capabilities()

# ── Auth contract startup check (P22-G4) ──────────────────────────────
# Log the canonical PUBLIC_PREFIXES immediately after plugin routes are loaded.
# Any plugin that mutates this list at import time will show the diff in logs,
# making auth-bypass tampering visible without requiring runtime enforcement.
# AUTH_REQUIRED=true must be set in production .env.

def _check_auth_contract() -> None:
    from .middleware.auth import PUBLIC_PREFIXES, PUBLIC_GET_PATTERNS

    CANONICAL_PUBLIC_PREFIXES = [
        "/api/health", "/api/auth/status", "/api/auth/setup",
        "/api/auth/login", "/api/auth/register", "/api/auth/accept-invite",
        "/api/auth/verify", "/api/auth/setup/config",
        "/api/auth/forgot-password", "/api/auth/reset-password",  # B251
        "/api/shares/",
        "/api/query",
        "/api/activity",
        "/api/webhooks/in/",
        "/api/oauth/callback/",  # B312 (v0.10.3): plugin OAuth callback
        "/openapi.json", "/openapi.yaml",
    ]

    unexpected = [p for p in PUBLIC_PREFIXES if p not in CANONICAL_PUBLIC_PREFIXES]
    if unexpected:
        logger.warning(
            f"AUTH CONTRACT VIOLATION: PUBLIC_PREFIXES contains unexpected entries "
            f"(possibly injected by a plugin): {unexpected}. "
            "Review installed plugin routes and restart the API.",
        )
    else:
        logger.info(
            f"Auth contract OK — {len(PUBLIC_PREFIXES)} public prefixes, "
            f"{len(PUBLIC_GET_PATTERNS)} public-GET patterns, none modified by plugins"
        )

    auth_required = os.environ.get("AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
    if not auth_required:
        logger.warning(
            "AUTH_REQUIRED is not set — all routes are publicly accessible. "
            "Set AUTH_REQUIRED=true in .env for production deployments."
        )


_check_auth_contract()


# ── B228: RBAC coverage check ─────────────────────────────────────────
# Logs any routes that aren't registered AND aren't in PUBLIC_ROUTES.
# In v0.9.8.1 this is informational; in v0.9.8.2 (B229) the default-deny
# middleware will return 403 RBAC_NOT_REGISTERED for these. Catch
# coverage gaps here so they don't ship as silent 403s.

def _check_rbac_coverage() -> None:
    from .rbac import ROUTE_PERMISSIONS, PUBLIC_ROUTES
    unregistered: list[tuple[str, str]] = []
    for r in app.routes:
        if not hasattr(r, "methods"):
            continue
        for m in r.methods:
            if m == "HEAD":
                continue
            key = (m, r.path)
            if key not in ROUTE_PERMISSIONS and key not in PUBLIC_ROUTES:
                unregistered.append(key)
    if unregistered:
        logger.warning(
            "[rbac] %d route(s) are unregistered (will 403 after B229's default-deny flip):",
            len(unregistered),
        )
        for m, p in sorted(unregistered):
            logger.warning("  unregistered: %s %s", m, p)
    else:
        logger.info(
            "[rbac] coverage check: all %d core routes registered (%d gated, %d public)",
            sum(1 for r in app.routes if hasattr(r, "methods")),
            len(ROUTE_PERMISSIONS),
            len(PUBLIC_ROUTES),
        )


_check_rbac_coverage()


# ── Query role startup check (S104) ──────────────────────────────────
# The `nousviz_query` Postgres role is the robust defense for the public
# /api/query endpoint. Regex-based table guards are known-bypassable via
# CTEs, subqueries, information_schema reflection, etc. The role is the
# only layer that stops `SELECT * FROM credentials` cold.
#
# We refuse to start if the role is missing. Alternative (silent fallback
# to regex-only) makes production risk invisible.

def _check_query_role_exists() -> None:
    """Fail loudly on startup if migration 033 hasn't been applied."""
    try:
        from .db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'nousviz_query'")
            if not cur.fetchone():
                raise RuntimeError(
                    "nousviz_query Postgres role is missing. "
                    "Apply migration 033 (readonly_query_role.sql) as the "
                    "postgres superuser:\n"
                    "  sudo -u postgres psql -d nousviz -f "
                    "storage/postgres/migrations/033_readonly_query_role.sql"
                )
    except RuntimeError:
        raise
    except Exception as e:
        # DB unreachable at startup is fatal for a different reason; let
        # the app fail naturally on the first request rather than hiding
        # the real cause.
        logger.warning(f"Could not verify nousviz_query role: {e}")


_check_query_role_exists()


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("API_PORT", "8000")))
