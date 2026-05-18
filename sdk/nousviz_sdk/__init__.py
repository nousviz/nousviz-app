"""
nousviz_sdk — Plugin development SDK for NousViz.

Quick start:

    from nousviz_sdk import get_pg_conn, router_for_plugin, get_credential

    router = router_for_plugin("my-plugin")

    @router.get("/data")
    def get_data():
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM my_table LIMIT 10")
            return {"rows": cur.fetchall()}
"""

from .db import get_pg_conn, dict_cursor, DictCursor
from .routing import router_for_plugin
from .credentials import (
    get_credential,
    CredentialBrokerUnavailable,
    CredentialBrokerError,
)
from . import jobs
from . import progress
from . import schedule
from . import settings
from . import hooks
from . import auth
from . import oauth
from . import logging as _logging  # noqa: F401  # re-export — avoid shadowing stdlib logging
from .hooks import HookContext, HookResult
from .settings import get_setting, set_setting, get_connection_field
from .logging import log_event
from .auth import issue_admin_session_cookie
from .oauth import OAuthCallbackResult, start_flow as start_oauth_flow

# v0.9.0 → 0.6.0: SDK packaging fix (P201) + SDK owns its DB path (P202) +
# credential broker delivery (P208) + dict_cursor in SDK.
# v0.9.2 → 0.6.2: nousviz_sdk.testing harness for plugin-author tests (B138);
# nousviz_sdk.logging.log_event for structured logging into /system/logs (B140);
# settings.get_connection_field as the SDK contract for non-secret connection
# fields (B136 — env-as-transport removed).
# v0.9.6 → 0.6.3: nousviz_sdk.progress.report for live sync progress (B205) —
# friendly wrapper over jobs.heartbeat(progress=...) that powers the unified
# Sync card in the plugin Settings tab and /system/jobs row expansion.
# v0.10.0.5 → 0.6.4: nousviz_sdk.auth.issue_admin_session_cookie for plugin
# admin-proxy auth path (B304) — path-scoped opaque-token cookie minted by
# plugin bridge endpoints; auth middleware accepts alongside existing headers.
# v0.10.0.5.2 → 0.6.5: issue_admin_session_cookie no longer requires
# NOUSVIZ_PLUGIN_ID env var unconditionally (api-process context doesn't
# set per-plugin env vars). Slug match check now conditional on env var.
# v0.10.3 → 0.6.6: nousviz_sdk.oauth.start_flow + OAuthCallbackResult for
# the core-owned OAuth callback contract (B312). Plugins mint a one-shot
# state token before redirecting to the provider; core's public
# /api/oauth/callback/<slug> route validates state and dispatches to the
# plugin's manifest-declared callback_handler.
# v0.10.3.1 → 0.6.7: start_oauth_flow now logs DB failures at ERROR
# (B312 hotfix) — pairs with migration 079 which grants nousviz_plugin
# the CRUD needed to persist state rows. Pre-079, every start failed
# silently with InsufficientPrivilege and the callback hit invalid_state.
__version__ = "0.6.7"
__all__ = [
    "get_pg_conn",
    "dict_cursor",
    "DictCursor",
    "router_for_plugin",
    "get_credential",
    "CredentialBrokerUnavailable",
    "CredentialBrokerError",
    "jobs",
    "progress",
    "schedule",
    "settings",
    "get_setting",
    "set_setting",
    "get_connection_field",
    "hooks",
    "HookContext",
    "HookResult",
    "log_event",
    "auth",
    "issue_admin_session_cookie",
    "oauth",
    "OAuthCallbackResult",
    "start_oauth_flow",
]
