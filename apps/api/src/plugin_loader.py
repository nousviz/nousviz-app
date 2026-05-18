"""
Dynamic Plugin Route Loader

Scans plugins/installed/ for plugins with api/routes.py files and
registers their FastAPI routers automatically. Plugins don't need
to be hardcoded in main.py — just install them and restart.

Plugin route contract:
  - File: plugins/installed/{plugin-slug}/api/routes.py
  - Must export: router (FastAPI APIRouter)
  - Optional: extra_routers (list of additional APIRouter instances)
  - Optional: setup(app) function for custom mounts (static files, etc.)

Routes are prefixed with /api by default. Plugins can set their own
prefix in the router definition if needed.
"""
import importlib.util
import logging
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI

logger = logging.getLogger("nousviz.plugin_loader")

PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins" / "installed"


# P204 (v0.9.0): track plugin load outcomes so the detail endpoint can
# surface `load_status` to the UI. Populated by load_plugin_routes at
# API startup; read by the plugin detail route. Per-worker state —
# gunicorn's N workers each have their own dict, but they'll all have
# the same content because they load the same plugins on the same code.
LOAD_STATUS: dict[str, dict] = {}


def _record_load_failure(slug: str, exc: Exception, stage: str = "routes") -> None:
    """Record a plugin load failure in LOAD_STATUS and write an error-level
    entry to app_logs so operators see it in /system/logs (not just pm2
    stderr). stage is 'routes' or 'module' for granularity.

    B132 (v0.9.1): the explicit log_job_event call this function used to
    make has been replaced with a `logger.error(..., extra={...})` call.
    The DBLogHandler attached to nousviz.plugin_loader picks up the
    structured `detail` and writes a single app_logs row. Previously,
    both this function AND the existing `logger.error("Plugin X: failed
    to load — ...")` in load_plugin_routes wrote, producing two rows per
    failure (one with detail, one without).
    """
    detail = {
        "plugin_id": slug,
        "stage": stage,
        "exception_class": type(exc).__name__,
        "exception_message": str(exc)[:500],
        "traceback_tail": traceback.format_exc()[-1500:],
    }
    LOAD_STATUS[slug] = {
        "routes_registered": False,
        "stage": stage,
        "exception_class": detail["exception_class"],
        "exception_message": detail["exception_message"],
        "traceback_tail": detail["traceback_tail"],
    }
    # Single emit. DBLogHandler writes the row with structured detail.
    # The exception_message above and the message text below carry the
    # same info redundantly; the message is what shows in the Logs UI's
    # primary column, the detail is for filtering / scripting.
    logger.error(
        f"Plugin {slug} failed to load ({stage}): {detail['exception_class']}: {detail['exception_message']}",
        extra={"detail": detail},
    )


def _record_load_success(slug: str) -> None:
    LOAD_STATUS[slug] = {"routes_registered": True}


def _integrity_override_allows(slug: str) -> bool:
    """S109: check NOUSVIZ_ALLOW_UNVERIFIED_PLUGINS env var.

    Value:
        empty / unset    → no override; tampered plugins fail to load
        "all"            → bypass all integrity checks (noisy startup warn)
        "a,b,c"          → comma-separated slugs to bypass

    Intended for dev workflows where the operator intentionally edits
    installed plugin files. NOT a default-on setting.
    """
    raw = os.environ.get("NOUSVIZ_ALLOW_UNVERIFIED_PLUGINS", "").strip()
    if not raw:
        return False
    if raw.lower() == "all":
        return True
    allowed = {s.strip() for s in raw.split(",") if s.strip()}
    return slug in allowed


class IntegrityError(RuntimeError):
    """Raised when a plugin's files have been modified since install and no
    override is in place. Per-plugin — other plugins continue loading."""


def _verify_plugin_integrity(slug: str, plugin_dir: Path) -> bool:
    """
    S109: Verify that a plugin's files have not been modified since install.

    Compares the current git HEAD SHA against the SHA recorded in plugin_registry
    at install time. A mismatch means files were modified after install — either
    legitimate (e.g. developer testing) or malicious (supply-chain tampering).

    Returns True if integrity check passes or cannot be performed (not a git
    repo, no recorded SHA). Raises IntegrityError on mismatch unless the
    operator has set NOUSVIZ_ALLOW_UNVERIFIED_PLUGINS=<slug> or =all.

    Previously only logged a WARNING — which was advisory, not enforced
    (audit finding H4). The loader now catches this and refuses to load
    the offending plugin, while other plugins continue loading normally.
    """
    result = subprocess.run(
        ["git", "-C", str(plugin_dir), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # Not a git repo (e.g. manually copied plugin) — skip check
        return True

    current_sha = result.stdout.strip()
    if not current_sha:
        return True

    try:
        from .db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT installed_commit_sha FROM plugin_registry WHERE slug = %s",
                (slug,),
            )
            row = cur.fetchone()
        if row and row[0] and row[0] != current_sha:
            if _integrity_override_allows(slug):
                logger.warning(
                    f"INTEGRITY OVERRIDE: Plugin '{slug}' SHA mismatch but "
                    f"NOUSVIZ_ALLOW_UNVERIFIED_PLUGINS allows loading. "
                    f"Recorded: {row[0][:12]}… Current: {current_sha[:12]}…"
                )
                return False
            raise IntegrityError(
                f"Plugin '{slug}' failed integrity check. "
                f"Recorded SHA: {row[0][:12]}… Current: {current_sha[:12]}…. "
                f"Files have been modified since install. "
                f"Reinstall the plugin, or to intentionally load a modified "
                f"plugin set NOUSVIZ_ALLOW_UNVERIFIED_PLUGINS={slug} "
                f"(or =all) and restart."
            )
    except IntegrityError:
        raise
    except Exception:
        # DB not available or table missing — skip check, don't block load.
        # This preserves behavior on fresh installs where plugin_registry
        # might not have the installed_commit_sha column yet.
        pass

    return True


def discover_plugins() -> list[dict]:
    """Find all installed plugins with API routes, including modules."""
    plugins = []
    if not PLUGINS_DIR.exists():
        return plugins

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        routes_file = plugin_dir / "api" / "routes.py"
        if not routes_file.exists():
            continue

        slug = plugin_dir.name

        # Discover modules
        modules = []
        modules_dir = plugin_dir / "modules"
        if modules_dir.exists():
            for module_dir in sorted(modules_dir.iterdir()):
                if not module_dir.is_dir():
                    continue
                module_yaml = module_dir / "module.yaml"
                if not module_yaml.exists():
                    continue
                modules.append({
                    "name": module_dir.name,
                    "dir": module_dir,
                    "routes_file": module_dir / "api" / "routes.py",
                    "manifest_file": module_yaml,
                })

        plugins.append({
            "slug": slug,
            "dir": plugin_dir,
            "routes_file": routes_file,
            "modules": modules,
        })

    return plugins


def is_admin_proxy_enabled(plugin_slug: str) -> bool:
    """B304 (v0.10.0.5): does this plugin opt into the path-scoped admin-session
    cookie auth path?

    Reads `frontend.admin_proxy` from the plugin's manifest. Returns False on
    any error (manifest missing, parse error, plugin not installed) — fail-closed
    so a typo or missing manifest can't accidentally loosen auth.

    Called from the auth middleware on requests under `/api/plugins/<slug>/admin/*`
    when a `nv_admin_<slug>` cookie is present. The path + cookie pre-checks make
    this rare enough that on-demand manifest reads are acceptable; the kernel page
    cache covers the I/O cost after the first read.
    """
    try:
        manifest_path = PLUGINS_DIR / plugin_slug / "plugin.yaml"
        if not manifest_path.exists():
            return False
        import yaml as _yaml
        manifest = _yaml.safe_load(manifest_path.read_text()) or {}
        return bool((manifest.get("frontend") or {}).get("admin_proxy", False))
    except Exception:
        return False


def get_oauth_callback_target(plugin_slug: str) -> str | None:
    """B312 (v0.10.3): resolve the dotted callback target for a plugin.

    Reads `oauth.callback_handler` from the plugin's manifest. Returns
    None when the plugin is missing, hasn't declared the block, or the
    manifest is unreadable. The string is in `module:function` form and
    is resolved against the plugin's directory by
    :func:`resolve_oauth_callback_handler`.

    The manifest validator (`plugin_validation.validate_oauth_block`)
    already enforces shape at install time; this getter trusts that
    invariant and treats anything malformed as "no declaration".
    """
    try:
        manifest_path = PLUGINS_DIR / plugin_slug / "plugin.yaml"
        if not manifest_path.exists():
            return None
        import yaml as _yaml
        manifest = _yaml.safe_load(manifest_path.read_text()) or {}
        target = (manifest.get("oauth") or {}).get("callback_handler")
        if isinstance(target, str) and ":" in target:
            return target
        return None
    except Exception:
        return None


_OAUTH_HANDLER_CACHE: dict[tuple[str, str], "object"] = {}


def resolve_oauth_callback_handler(plugin_slug: str, target: str):
    """B312 hotfix (v0.10.3.2): resolve `module:function` against the
    plugin's installed directory.

    The plugin loader doesn't add plugin directories to ``sys.path`` —
    it loads ``api/routes.py`` via
    :func:`importlib.util.spec_from_file_location` with a synthetic module
    name. That means ``importlib.import_module("api.oauth")`` from the
    API process can't find the plugin's ``api/oauth.py`` file, even
    though it exists on disk.

    This helper mirrors the loader's pattern: it converts the dotted
    module path to a file path under the plugin's installed dir, loads
    it via ``spec_from_file_location`` with a slug-scoped module name,
    and caches the result so repeated callbacks don't re-import.

    :param plugin_slug: The plugin's installed slug (e.g.
        ``"google-analytics"``).
    :param target: Manifest-declared ``module:function`` string (e.g.
        ``"api.oauth:handle_callback"``). The manifest validator already
        enforces shape; this function trusts the regex.

    :returns: The callable, or ``None`` on any failure (missing file,
        spec/exec error, missing function). Caller logs and 302s to
        ``oauth_error=handler_failed`` on ``None``.

    Limitation: relative imports inside the loaded module (e.g.
    ``from .common import x``) don't work — there's no synthetic parent
    package. Plugin authors must use absolute imports (the SDK's
    ``nousviz_sdk.*`` modules, or ``import google_analytics_xyz`` if
    they ``pip install`` their own dependencies). Documented in
    ``docs/plugin-architecture.md`` §5.12.
    """
    module_dotted, _, func_name = target.partition(":")
    if not module_dotted or not func_name:
        return None

    cache_key = (plugin_slug, target)
    cached = _OAUTH_HANDLER_CACHE.get(cache_key)
    if cached is not None:
        return cached

    plugin_dir = PLUGINS_DIR / plugin_slug
    if not plugin_dir.is_dir():
        return None

    # Convert "api.oauth" → "api/oauth.py" within the plugin dir.
    # The manifest validator's regex (^[a-zA-Z_][\w.]*$) already blocks
    # path traversal characters, so a simple dot→slash substitution is
    # safe. Also try "<module>/__init__.py" so plugins can split their
    # handler into a package.
    rel = module_dotted.replace(".", "/")
    candidates = [
        plugin_dir / f"{rel}.py",
        plugin_dir / rel / "__init__.py",
    ]
    handler_file: Path | None = next((c for c in candidates if c.is_file()), None)
    if handler_file is None:
        logger.warning(
            "[oauth] plugin %s: callback module %r not found under %s",
            plugin_slug, module_dotted, plugin_dir,
        )
        return None

    # Slug-scoped synthetic module name — collisions across plugins
    # impossible because the slug is unique, and uniqueness within a
    # plugin is provided by the dotted module path.
    module_name = (
        f"plugin_oauth_handler__{plugin_slug.replace('-', '_')}__"
        f"{module_dotted.replace('.', '_')}"
    )
    try:
        spec = importlib.util.spec_from_file_location(module_name, handler_file)
        if spec is None or spec.loader is None:
            logger.error(
                "[oauth] plugin %s: spec_from_file_location returned None for %s",
                plugin_slug, handler_file,
            )
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        logger.exception(
            "[oauth] plugin %s: importing %s failed: %s",
            plugin_slug, handler_file, exc,
        )
        # Don't poison the cache on import failure; let the plugin fix
        # the file and retry without an API restart.
        sys.modules.pop(module_name, None)
        return None

    handler = getattr(module, func_name, None)
    if handler is None or not callable(handler):
        logger.error(
            "[oauth] plugin %s: %s has no callable %r",
            plugin_slug, handler_file, func_name,
        )
        return None

    _OAUTH_HANDLER_CACHE[cache_key] = handler
    return handler


def _is_module_enabled(plugin_slug: str, module_name: str, module_dir: Path) -> bool:
    """Check if a module is enabled. Falls back to enabled_by_default from module.yaml."""
    try:
        from .db import get_pg_conn
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT enabled FROM plugin_modules WHERE plugin_id = %s AND module_name = %s",
                (plugin_slug, module_name),
            )
            row = cur.fetchone()
            if row:
                return bool(row[0])
    except Exception:
        pass  # DB not available yet (startup) — use default

    # No DB row — check module.yaml for enabled_by_default
    try:
        import yaml
        with open(module_dir / "module.yaml") as f:
            manifest = yaml.safe_load(f)
        return manifest.get("enabled_by_default", True)
    except Exception:
        return True  # Default to enabled


def load_plugin_routes(app: FastAPI) -> list[str]:
    """Load and register routes from all installed plugins. Returns list of loaded plugin slugs."""
    loaded = []
    plugins = discover_plugins()

    for plugin in plugins:
        slug = plugin["slug"]
        routes_file = plugin["routes_file"]
        plugin_dir = plugin["dir"]

        try:
            # S109: integrity check before loading — blocking by default.
            # IntegrityError raised here is caught below and the plugin is
            # skipped (other plugins continue loading).
            _verify_plugin_integrity(slug, plugin_dir)

            # B211 (v0.9.7.0): plugin routes are private by default in the
            # platform's public OpenAPI spec. Plugin authors opt in via
            # `openapi_public: true` in plugin.yaml. The flag here governs
            # main + extra + widget + module routers — one decision per
            # plugin, not per-router.
            openapi_public = False
            try:
                import yaml as _yaml
                manifest_path = plugin_dir / "plugin.yaml"
                if manifest_path.exists():
                    manifest = _yaml.safe_load(manifest_path.read_text()) or {}
                    openapi_public = bool(manifest.get("openapi_public", False))
            except Exception:
                openapi_public = False  # Manifest parse error → private (safe default)

            # Load the module dynamically
            module_name = f"plugin_routes_{slug.replace('-', '_')}"
            spec = importlib.util.spec_from_file_location(module_name, routes_file)
            if not spec or not spec.loader:
                logger.warning(
                    "Plugin %s: could not load %s",
                    slug, routes_file,
                    extra={"plugin_id": slug},
                )
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Register the main router
            if hasattr(module, "router"):
                router = module.router
                # B211: include_in_schema as a kwarg propagates to every
                # route in the router. Setting `router.include_in_schema`
                # on the object before include_router() does NOT propagate
                # — verified empirically against FastAPI 0.x.
                if router.prefix and router.prefix.startswith("/api"):
                    app.include_router(router, include_in_schema=openapi_public)
                else:
                    app.include_router(router, prefix="/api", include_in_schema=openapi_public)
                logger.info(
                    "Plugin %s: registered router (prefix=%s, public=%s)",
                    slug, router.prefix or "/api", openapi_public,
                    extra={"plugin_id": slug},
                )

            # Run custom setup BEFORE extra routers (static mounts must come before catch-all routes)
            if hasattr(module, "setup"):
                module.setup(app)
                logger.info(
                    "Plugin %s: ran custom setup",
                    slug,
                    extra={"plugin_id": slug},
                )

            # Register extra routers (e.g. redirect_router, seo_router, pub_router)
            if hasattr(module, "extra_routers"):
                for name, extra_router, kwargs in module.extra_routers:
                    # B211: respect plugin author's explicit kwarg if they
                    # set include_in_schema themselves, otherwise force the
                    # plugin-level openapi_public flag.
                    kwargs.setdefault("include_in_schema", openapi_public)
                    app.include_router(extra_router, **kwargs)
                    logger.info(
                        "Plugin %s: registered extra router '%s'",
                        slug, name,
                        extra={"plugin_id": slug},
                    )

            # Check for widget routes
            widgets_file = plugin_dir / "api" / "widgets.py"
            if widgets_file.exists():
                w_module_name = f"plugin_widgets_{slug.replace('-', '_')}"
                w_spec = importlib.util.spec_from_file_location(w_module_name, widgets_file)
                if w_spec and w_spec.loader:
                    w_module = importlib.util.module_from_spec(w_spec)
                    sys.modules[w_module_name] = w_module
                    w_spec.loader.exec_module(w_module)
                    if hasattr(w_module, "router"):
                        w_router = w_module.router
                        # B211: kwarg propagation, see main-router note above.
                        if w_router.prefix and w_router.prefix.startswith("/api"):
                            app.include_router(w_router, include_in_schema=openapi_public)
                        else:
                            app.include_router(w_router, prefix="/api", include_in_schema=openapi_public)
                        logger.info(
                            "Plugin %s: registered widget router",
                            slug,
                            extra={"plugin_id": slug},
                        )

            # Load module routes
            for mod in plugin.get("modules", []):
                mod_name = mod["name"]
                mod_routes_file = mod["routes_file"]

                if not mod_routes_file.exists():
                    continue

                if not _is_module_enabled(slug, mod_name, mod["dir"]):
                    logger.info(
                        "Plugin %s: module '%s' disabled — skipping",
                        slug, mod_name,
                        extra={"plugin_id": slug},
                    )
                    continue

                try:
                    mod_module_name = f"plugin_module_{slug.replace('-', '_')}_{mod_name.replace('-', '_')}"
                    mod_spec = importlib.util.spec_from_file_location(mod_module_name, mod_routes_file)
                    if mod_spec and mod_spec.loader:
                        mod_module = importlib.util.module_from_spec(mod_spec)
                        sys.modules[mod_module_name] = mod_module
                        mod_spec.loader.exec_module(mod_module)

                        if hasattr(mod_module, "router"):
                            mod_router = mod_module.router
                            # B211: kwarg propagation, see main-router note above.
                            if mod_router.prefix and mod_router.prefix.startswith("/api"):
                                app.include_router(mod_router, include_in_schema=openapi_public)
                            else:
                                app.include_router(mod_router, prefix="/api", include_in_schema=openapi_public)
                            logger.info(
                                "Plugin %s: loaded module '%s' routes",
                                slug, mod_name,
                                extra={"plugin_id": slug},
                            )
                except Exception as me:
                    # B132 (v0.9.1): _record_load_failure logs via
                    # logger.error with structured extras — DBLogHandler
                    # writes one app_logs row. Don't log again here.
                    _record_load_failure(slug, me, stage=f"module:{mod_name}")

            loaded.append(slug)
            _record_load_success(slug)

        except IntegrityError as e:
            # S109: refuse to load this plugin, continue loading others.
            _record_load_failure(slug, e, stage="integrity")
        except Exception as e:
            _record_load_failure(slug, e, stage="routes")

    # B229 (v0.9.8.2): auto-register plugin routes. After all plugin routers
    # have been included into the app, walk the route table once and assign
    # default RBAC permissions to any plugin route the author didn't
    # explicitly register. Plugin authors override by importing
    # register_route from src.rbac and calling it themselves before their
    # router is loaded.
    _auto_register_plugin_routes(app)

    return loaded


def _slug_from_route_path(path: str) -> Optional[str]:
    """Best-effort: derive the plugin slug from a route path.

    Only `/api/plugins/<slug>/...` routes are considered owned by a
    plugin for the purposes of B247 per-plugin permissions. Plugins
    that mount extra routers under unrelated prefixes (e.g.
    `/api/webhooks/...`) keep the legacy method-derived defaults
    until they migrate to declaring a `permissions:` block (a future
    enhancement may extend slug-derivation).
    """
    if not path.startswith("/api/plugins/"):
        return None
    rest = path[len("/api/plugins/"):]
    # First segment is the slug; reject templated `{plugin_id}` (those
    # are core endpoints, not plugin-owned).
    head = rest.split("/", 1)[0]
    if not head or head.startswith("{"):
        return None
    return head


def _load_plugin_manifests() -> dict[str, dict[str, Any]]:
    """Read every installed plugin's manifest. Returns {slug: manifest_dict}.

    Errors during read are logged and the plugin is omitted from the
    map — that means `_auto_register_plugin_routes` falls back to legacy
    defaults for it.
    """
    import yaml

    manifests: dict[str, dict[str, Any]] = {}
    for plugin in discover_plugins():
        slug = plugin["slug"]
        manifest_path = plugin["dir"] / "plugin.yaml"
        if not manifest_path.exists():
            continue
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
            manifests[slug] = data
        except Exception as exc:
            logger.warning(
                "[rbac] could not read manifest for plugin %s: %s — using legacy defaults",
                slug, exc,
            )
    return manifests


def _auto_register_plugin_routes(app: FastAPI) -> None:
    """Assign RBAC permissions to plugin-author routes.

    B247 (v0.9.10.6): plugins that declare `permissions:` in plugin.yaml
    get per-plugin permission strings (`plugin.<slug>.<level>`) derived
    from the manifest. Plugins that don't declare it keep the B229
    method-derived legacy defaults.

    B229 legacy defaults (still applied when no manifest declaration):
        GET    -> plugins.read       (viewer+)
        POST   -> plugins.configure  (admin+)
        PATCH  -> plugins.configure  (admin+)
        PUT    -> plugins.configure  (admin+)
        DELETE -> plugins.configure  (admin+)

    Routes the plugin author has already registered explicitly via
    register_route() are NOT overwritten — register_route raises on
    conflict for differing permissions, but the same-permission case
    is idempotent.

    "Plugin route" = any route under /api/plugins/<installed_slug>/* OR
    a route belonging to a plugin's extra_router (e.g. /api/webhooks/in/*
    from the webhooks plugin).
    """
    from .rbac import ROUTE_PERMISSIONS, PUBLIC_ROUTES, register_route
    from .rbac.plugin_permissions import register_all_plugin_levels
    from .plugin_manifest import (
        ManifestPermissionsError,
        parse as parse_permissions_block,
        permission_string,
    )

    DEFAULT_BY_METHOD = {
        "GET": "plugins.read",
        "POST": "plugins.configure",
        "PATCH": "plugins.configure",
        "PUT": "plugins.configure",
        "DELETE": "plugins.configure",
    }

    # Load manifests + parse `permissions:` blocks once.
    manifests = _load_plugin_manifests()
    plugin_perms: dict[str, Any] = {}
    for slug, manifest in manifests.items():
        try:
            cfg = parse_permissions_block(manifest.get("permissions"))
        except ManifestPermissionsError as exc:
            logger.error(
                "[rbac] plugin %s has invalid `permissions:` block: %s — falling back to legacy defaults",
                slug, exc,
            )
            cfg = None
        plugin_perms[slug] = cfg
        if cfg is None:
            logger.info(
                "[rbac] plugin %s has no `permissions:` declaration; using legacy defaults",
                slug,
            )
        else:
            logger.info(
                "[rbac] plugin %s declares permissions (default=%s, %d route override(s))",
                slug, cfg.default_level, len(cfg.route_rules),
            )
            # B247 phase 2: register the full plugin.<slug>.<level> set in
            # the PERMISSIONS catalog so the matrix UI sees them. Done
            # whether or not any route uses every level — operators can
            # grant levels even before a plugin route uses them.
            register_all_plugin_levels(slug)

    auto_count = 0
    per_plugin_count = 0
    legacy_count = 0
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        path = route.path
        if not path.startswith("/api/"):
            continue
        slug = _slug_from_route_path(path)
        cfg = plugin_perms.get(slug) if slug else None

        for method in route.methods:
            if method == "HEAD":
                continue
            key = (method, path)
            if key in ROUTE_PERMISSIONS or key in PUBLIC_ROUTES:
                continue

            if cfg is not None:
                # B247: per-plugin permission derived from the manifest.
                level = cfg.resolve(method, path)
                permission = permission_string(slug, level)
                register_route(method, path, permission)
                logger.info(
                    "[rbac] B247 plugin route: %s %s -> %s (level=%s)",
                    method, path, permission, level,
                )
                per_plugin_count += 1
            else:
                # B229 legacy: method-derived coarse default.
                permission = DEFAULT_BY_METHOD.get(method, "plugins.configure")
                register_route(method, path, permission)
                logger.info(
                    "[rbac] auto-registered plugin route (legacy): %s %s -> %s",
                    method, path, permission,
                )
                legacy_count += 1
            auto_count += 1

    if auto_count:
        logger.info(
            "[rbac] auto-registered %d plugin route(s) total (per-plugin: %d, legacy: %d)",
            auto_count, per_plugin_count, legacy_count,
        )
