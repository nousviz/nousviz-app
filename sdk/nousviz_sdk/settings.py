"""
nousviz_sdk.settings — Read and write plugin settings & connection fields.

Plugin settings live in the core `plugin_settings` table (JSONB keyed by
(plugin_id, key)). Two namespaces share the table:

  - Plugin-declared `settings:` fields → stored at top-level keys
  - Connection fields (host, port, etc.) → stored under `_conn.<name>`

This module is the supported interface; plugins must not query
`plugin_settings` directly.

    from nousviz_sdk.settings import get_setting, set_setting, get_connection_field

    # Plugin-declared settings (`settings:` in plugin.yaml):
    endpoint = get_setting("my-plugin", "api_endpoint", default="")
    set_setting("my-plugin", "api_endpoint", "https://api.example.com")

    # Connection fields (`connections:` in plugin.yaml):
    host = get_connection_field("my-plugin", "host", default="localhost")

Values must be JSON-serialisable (str, int, float, bool, None, list, dict).
Setting a value of None stores None — use delete_setting() to remove a key.

# Why a separate function for connection fields?

v0.9.2 (B136) removed the env-as-transport pattern for non-secret connection
fields. Plugins used to read `os.environ["MYSQL_HOST"]`; now they call
`get_connection_field("my-plugin", "host")`. The function exists so plugin
authors don't need to know about the `_conn.*` namespace convention.
"""

from __future__ import annotations

import json
from typing import Any

_CONN_KEY_PREFIX = "_conn."


def get_setting(plugin_id: str, key: str, default: Any = None) -> Any:
    """Return the stored value for (plugin_id, key), or `default` if missing.

    JSONB column is auto-decoded by psycopg2 so the return value is
    whatever Python type the original JSON document represented (dict,
    list, str, int, bool, None).
    """
    from . import get_pg_conn
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT value FROM plugin_settings WHERE plugin_id = %s AND key = %s",
                (plugin_id, key),
            )
            row = cur.fetchone()
        return row[0] if row else default
    except Exception:
        return default


def set_setting(plugin_id: str, key: str, value: Any) -> None:
    """Upsert (plugin_id, key) → value.

    Updates updated_at on conflict so the plugin_settings audit view
    reflects the change.
    """
    from . import get_pg_conn
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO plugin_settings (plugin_id, key, value, updated_at)
            VALUES (%s, %s, %s::jsonb, now())
            ON CONFLICT (plugin_id, key) DO UPDATE
              SET value = EXCLUDED.value, updated_at = now()
            """,
            (plugin_id, key, json.dumps(value)),
        )
        conn.commit()


def list_settings(plugin_id: str) -> dict[str, Any]:
    """Return {key: value} for all settings of a plugin."""
    from . import get_pg_conn
    result: dict[str, Any] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT key, value FROM plugin_settings WHERE plugin_id = %s",
                (plugin_id,),
            )
            for k, v in cur.fetchall():
                result[k] = v
    except Exception:
        pass
    return result


def delete_setting(plugin_id: str, key: str) -> None:
    """Remove the row for (plugin_id, key). No-op if absent."""
    from . import get_pg_conn
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM plugin_settings WHERE plugin_id = %s AND key = %s",
            (plugin_id, key),
        )
        conn.commit()


def get_connection_field(plugin_id: str, field_name: str, default: Any = None) -> Any:
    """Read a non-secret connection field for a plugin.

    Connection fields (host, port, database name, username, etc.) are stored
    under the `_conn.<field_name>` key namespace in `plugin_settings`. This
    helper hides that convention from plugin authors.

    For SECRET fields (password, api_token, ssl_ca), use `get_credential()`
    from `nousviz_sdk` — those are encrypted in a separate table and
    delivered via the credential broker.

    Args:
        plugin_id: Your plugin's declared id.
        field_name: The connection field name as declared in plugin.yaml
                    `connections.fields` (e.g., "host", "port", "database").
        default: Value to return if the field has not been saved.

    Returns:
        The stored value (typically a string), or `default` if missing.
    """
    return get_setting(plugin_id, _CONN_KEY_PREFIX + field_name, default=default)


__all__ = [
    "get_setting",
    "set_setting",
    "list_settings",
    "delete_setting",
    "get_connection_field",
]
