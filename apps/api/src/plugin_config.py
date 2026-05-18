"""
plugin_config — unified storage for plugin connection fields (B130, v0.8.6.5).

Replaces the legacy split where:
  - Secret fields         → credentials table (encrypted)
  - Non-secret fields     → .env file + os.environ mirror

Now:
  - Secret fields         → credentials table (encrypted) — unchanged
  - Non-secret fields     → plugin_settings table (JSONB, namespaced under `_conn.*`)
  - Legacy os.environ     → read-only fallback. On hit, logs a deprecation
                            warning and self-heals by copying the value
                            into plugin_settings for the next read.

The `_conn.*` key namespace keeps connection fields separate from
plugin-declared `settings:` fields that also live in plugin_settings.
Plugin authors who declare `settings:` never see `_conn.*` keys via
the /settings endpoint (filtered by namespace).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .db import get_pg_conn

logger = logging.getLogger("nousviz.api.plugin_config")


CONN_KEY_PREFIX = "_conn."

# Track which (plugin_id, field) pairs we've already warned about this
# process so /system/logs doesn't get spammed. Cleared on restart.
_legacy_warned: set[tuple[str, str]] = set()


def _conn_key(field_name: str) -> str:
    return f"{CONN_KEY_PREFIX}{field_name}"


def upsert_config_field(plugin_id: str, field_name: str, value: Any) -> None:
    """Write a non-secret plugin connection field to plugin_settings.

    Value is stored as JSONB. Strings, numbers, booleans all round-trip
    cleanly — no content restrictions (newlines, `=`, null bytes all fine
    because JSONB doesn't care).
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO plugin_settings (plugin_id, key, value, updated_at)
            VALUES (%s, %s, %s::jsonb, now())
            ON CONFLICT (plugin_id, key)
            DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """,
            (plugin_id, _conn_key(field_name), json.dumps(value)),
        )
        conn.commit()


def get_config_field(
    plugin_id: str,
    field_name: str,
    env_prefix: str = "",
    default: Any = "",
) -> Any:
    """Read a non-secret plugin connection field.

    Priority:
      1. plugin_settings row under `_conn.<field>` (source of truth)
      2. os.environ[<env_prefix><FIELD>] (legacy fallback; self-heals on hit)
      3. default (from plugin.yaml field spec)
    """
    # Primary: DB
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM plugin_settings WHERE plugin_id = %s AND key = %s",
                (plugin_id, _conn_key(field_name)),
            )
            row = cur.fetchone()
            if row is not None:
                val = row[0]
                # JSONB round-trip: strings come back as Python str already.
                # Dicts/lists come back as parsed objects. For connection
                # fields callers expect strings; coerce on the way out.
                if isinstance(val, (dict, list)):
                    return json.dumps(val)
                return val if val is not None else default
    except Exception as exc:
        logger.warning("get_config_field DB read failed for %s/%s: %s", plugin_id, field_name, exc)
        # Fall through to env — a degraded path is better than a 500.

    # Fallback: legacy os.environ. Self-heal on hit.
    env_key = f"{env_prefix.upper()}{field_name.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        _log_legacy_fallback(plugin_id, field_name)
        try:
            upsert_config_field(plugin_id, field_name, env_val)
            logger.info("plugin_config self-heal: copied %s/%s from env to DB", plugin_id, field_name)
        except Exception as exc:
            logger.warning("plugin_config self-heal failed for %s/%s: %s", plugin_id, field_name, exc)
        return env_val

    return default


def list_config_fields(plugin_id: str) -> dict[str, Any]:
    """Return {field_name: value} for all `_conn.*` entries of this plugin.
    Used by /GET connections to hydrate the form in one query."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM plugin_settings WHERE plugin_id = %s AND key LIKE %s",
                (plugin_id, f"{CONN_KEY_PREFIX}%"),
            )
            out: dict[str, Any] = {}
            for key, value in cur.fetchall():
                field_name = key[len(CONN_KEY_PREFIX):]
                if isinstance(value, (dict, list)):
                    out[field_name] = json.dumps(value)
                else:
                    out[field_name] = value
            return out
    except Exception as exc:
        logger.warning("list_config_fields failed for %s: %s", plugin_id, exc)
        return {}


def build_subprocess_env_for_plugin(plugin_id: str, manifest: dict) -> dict[str, str]:
    """Return a dict of NON-SECRET connection field env vars for a plugin
    subprocess. Pure function — does NOT mutate os.environ.

    B136 (v0.9.2): replaces the old `inject_config_env` parent-env-mutation
    pattern. Worker spawn paths build the subprocess env dict by composing
    the result of this function with `plugin_sync_env()` and the broker
    token / socket path. The parent (worker) os.environ is never written to,
    so plugin A's host can't leak into plugin B's spawn via the worker's env.

    Iterates plugin connection fields. For each NON-secret field, reads the
    value from plugin_settings and adds it to the returned dict. Skips every
    secret field entirely (subprocess fetches secrets via broker).
    """
    from .routes.plugins import _field_is_secret  # shared helper

    out: dict[str, str] = {}
    connections = manifest.get("connections") or []
    for conn_spec in connections:
        prefix = (conn_spec.get("env_prefix") or "").upper()
        fields = conn_spec.get("fields") or []
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_name = field.get("name")
            if not field_name:
                continue

            # SECRETS DO NOT GO TO ENV. Subprocess fetches via broker.
            if _field_is_secret(field):
                continue

            env_key = f"{prefix}{field_name.upper()}"
            val = get_config_field(plugin_id, field_name, env_prefix=prefix, default="")
            if val in (None, ""):
                continue
            cleaned = val.replace("\x00", "") if isinstance(val, str) else str(val)
            out[env_key] = cleaned

    return out


def inject_config_env(plugin_id: str, manifest: dict) -> None:
    """DEPRECATED in v0.9.2 (B136) — use `build_subprocess_env_for_plugin`.

    Kept as a thin shim that mutates os.environ for any caller still relying
    on the old contract (e.g., GET /api/plugins/<id>/connections hydration
    in the API process, where parent-env mutation is harmless because the
    API doesn't spawn plugin subprocesses).

    Worker spawn paths must NOT use this — they should use
    `build_subprocess_env_for_plugin` and add the result to the subprocess
    env dict directly.
    """
    env = build_subprocess_env_for_plugin(plugin_id, manifest)
    for k, v in env.items():
        try:
            os.environ[k] = v
        except (ValueError, TypeError, OSError) as exc:
            logger.warning("inject_config_env: env mirror skipped for %s: %s", k, exc)


# ── Internal: deprecation logging for legacy env fallback ─────────────


def _log_legacy_fallback(plugin_id: str, field_name: str) -> None:
    """Warn once per (plugin, field) per process when we fall back to env.
    Also emit to app_logs so operators see drift in /system/logs."""
    pair = (plugin_id, field_name)
    if pair in _legacy_warned:
        return
    _legacy_warned.add(pair)

    msg = (
        f"Plugin {plugin_id}: field {field_name!r} read from .env/os.environ fallback "
        f"instead of plugin_settings. This is pre-v0.8.6.5 legacy state; resaving "
        f"the plugin's settings will migrate the value into the DB."
    )
    logger.warning(msg)
    try:
        from .log_events import log_job_event
        log_job_event(
            "warning",
            f"Legacy env fallback for {plugin_id}/{field_name}",
            {
                "field_name": field_name,
                "hint": "Resave plugin settings to migrate this value to plugin_settings DB.",
                "source": "plugin_config",
            },
            plugin_id=plugin_id,
        )
    except Exception as exc:
        logger.debug("log_job_event for legacy fallback failed: %s", exc)
