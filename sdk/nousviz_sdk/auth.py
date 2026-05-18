"""B304 (v0.10.0.5): plugin admin-session cookie helper.

Plugins that bundle a vendor admin SPA (Strapi, Outline, Ghost, Mattermost
admin, embedded BI dashboards, etc.) and declare ``frontend.admin_proxy: true``
in their manifest can call :func:`issue_admin_session_cookie` from a bridge
endpoint to mint a path-scoped cookie. The auth middleware then accepts that
cookie on requests under ``/api/plugins/<slug>/admin/*``, alongside the
existing header-based auth.

Usage from a plugin route::

    from fastapi import Depends, Response
    from nousviz_sdk.auth import issue_admin_session_cookie
    # plugin's own auth dependency, e.g. _require_admin

    @router.post("/api/plugins/my-plugin/admin/_bridge")
    def bridge(response: Response, identity: str = Depends(_require_admin)):
        issue_admin_session_cookie(
            response,
            plugin_slug="my-plugin",
            user_id=identity,
        )
        return {"ok": True}

The plugin's frontend (e.g. an "Open admin" button) calls this endpoint via
``apiFetch()`` first, then navigates the browser to the admin URL. The
cookie is automatically attached by the browser because it's path-scoped to
``/api/plugins/<slug>/admin``.

Security model
--------------
- Cookie is **HttpOnly** (XSS can't steal it), **Secure** (HTTPS only),
  **SameSite=Strict** (CSRF mitigated), and **Path-scoped** to the
  plugin's admin path (no leak to other NousViz surfaces).
- The cookie's raw token is opaque random ``secrets.token_urlsafe(32)``
  output. The DB stores only its SHA256 hash (mirrors the user_sessions
  pattern). Revocation = ``DELETE FROM plugin_admin_sessions WHERE ...``.
- Slug binding: the cookie's encoded ``plugin_id`` is checked against
  the request URL's slug, so a cookie minted for plugin A is rejected on
  plugin B's admin path even if both use ``admin_proxy: true``.
- The plugin author MUST gate the bridge endpoint with their own auth
  dependency (typically ``Depends(_require_admin)``). This helper assumes
  the operator's identity has already been verified.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Response

from .db import get_pg_conn

COOKIE_PREFIX = "nv_admin_"
DEFAULT_TTL_SECONDS = 3600  # 1 hour


def issue_admin_session_cookie(
    response: Response,
    *,
    plugin_slug: str,
    user_id: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    request_ip: str | None = None,
    request_ua: str | None = None,
) -> None:
    """Mint a path-scoped admin-session cookie for the calling plugin.

    Inserts a row in ``plugin_admin_sessions`` and sets the cookie on the
    response. The plugin route handler MUST gate the call on its own auth
    check (typically ``Depends(_require_admin)``) — this helper assumes
    the operator's identity has already been verified.

    The cookie:

    - Name: ``nv_admin_<plugin_slug>``
    - Value: opaque random 32-byte url-safe token (raw token only here;
      DB stores only the SHA256 hash)
    - Path: ``/api/plugins/<plugin_slug>/admin`` (browser sends ONLY on
      requests under that prefix)
    - HttpOnly, Secure, SameSite=Strict, Max-Age=ttl_seconds

    :param response: FastAPI ``Response`` object the cookie will be set on.
    :param plugin_slug: The calling plugin's slug. If ``NOUSVIZ_PLUGIN_ID``
        env var is set (subprocess contexts), MUST match it; otherwise the
        caller's slug is trusted (api-process context).
    :param user_id: The operator's user ID (UUID string).
    :param ttl_seconds: Cookie / row lifetime in seconds. Default 3600.
    :param request_ip: Optional IP address for the audit row.
    :param request_ua: Optional User-Agent string for the audit row.

    :raises ValueError: if ``NOUSVIZ_PLUGIN_ID`` env var is set AND
        ``plugin_slug`` doesn't match it (cross-plugin minting blocked
        when running in a context that publishes the env var — e.g.
        jobs-worker subprocesses). In the api-process context where
        plugin routes run, the env var is NOT set and the SDK trusts
        the caller's ``plugin_slug``; the real protection is the
        manifest ``frontend.admin_proxy`` opt-in plus plugin review.

    v0.10.0.5.2 (B304 hotfix): originally required NOUSVIZ_PLUGIN_ID
    to be set unconditionally; that broke every plugin's bridge route
    because the api process doesn't set the env var on a per-plugin
    basis (it's a process-global, not request-scoped). Relaxed to
    "enforce slug match IF env var is set; trust the caller otherwise."
    """
    expected_slug = os.environ.get("NOUSVIZ_PLUGIN_ID")
    if expected_slug and plugin_slug != expected_slug:
        raise ValueError(
            f"issue_admin_session_cookie: plugin_slug={plugin_slug!r} does "
            f"not match NOUSVIZ_PLUGIN_ID={expected_slug!r}. A plugin "
            f"cannot mint cookies for another plugin."
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    path_scope = f"/api/plugins/{plugin_slug}/admin"

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO plugin_admin_sessions
                 (plugin_id, user_id, token_hash, path_scope, expires_at,
                  ip_address, user_agent)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                plugin_slug,
                user_id,
                token_hash,
                path_scope,
                expires_at,
                request_ip,
                request_ua,
            ),
        )

    response.set_cookie(
        key=f"{COOKIE_PREFIX}{plugin_slug}",
        value=raw_token,
        max_age=ttl_seconds,
        path=path_scope,
        httponly=True,
        secure=True,
        samesite="strict",
    )
