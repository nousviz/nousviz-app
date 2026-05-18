"""B312 (v0.10.3): /api/oauth/callback/{plugin_slug} — core-owned OAuth callback.

This is the public endpoint a third-party OAuth provider (Google, Slack,
GitHub, ...) redirects the user's browser to after they authorize. The
provider cannot attach a NousViz session token to that redirect, which
is why the route lives in core and is allowlisted in
:mod:`apps.api.src.middleware.auth`'s ``PUBLIC_PREFIXES``.

End-to-end flow
---------------
1. Plugin route (e.g. ``GET /api/plugins/<slug>/auth/start``) is gated by
   the operator's session. It calls :func:`nousviz_sdk.oauth.start_flow`
   to mint a one-shot ``state`` token bound to ``(plugin_id, user_id,
   return_to)``, then 302s the browser to the provider's auth URL with
   ``state=<token>&redirect_uri=https://<host>/api/oauth/callback/<slug>``.
2. User authorizes on the provider.
3. Provider redirects to this route with ``?code=...&state=...``.
4. We validate the ``state`` row (exists, not consumed, not expired,
   plugin_id matches the URL slug), mark it consumed, and dispatch to
   the plugin's manifest-declared ``oauth.callback_handler``.
5. The handler exchanges ``code`` for tokens (plugin owns this) and
   returns an :class:`OAuthCallbackResult`. core stores any returned
   credentials via
   :func:`apps.api.src.plugin_credentials.store_plugin_credential` and
   302s the browser to ``return_to`` (or the handler's override).

Failure UX is always a 302 back to ``return_to`` with an
``?oauth_error=<code>`` query param so the plugin's settings page can
render an inline error. The handler's exception message is **not** echoed
to the user; only a short, opaque ``detail`` token is included for the UI
to switch on.
"""

from __future__ import annotations

import hashlib
import logging
import secrets  # noqa: F401  (kept for parity with sdk/oauth.py; future timing-safe checks)
from typing import Optional
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from ..db import get_pg_conn

logger = logging.getLogger("nousviz.api.oauth")

router = APIRouter(prefix="/api/oauth", tags=["auth"])


# Opaque, UI-stable error codes. The plugin's settings page should switch
# on these to render a friendly banner; they do NOT leak server detail.
_ERR_INVALID_REQUEST = "invalid_request"
_ERR_INVALID_STATE = "invalid_state"
_ERR_PROVIDER_ERROR = "provider_error"
_ERR_UNKNOWN_PLUGIN = "unknown_plugin"
_ERR_HANDLER_FAILED = "handler_failed"
_ERR_NO_HANDLER = "no_handler"


def _safe_return_to(return_to: Optional[str]) -> str:
    """Constrain ``return_to`` to same-origin paths.

    Open-redirect prevention: the plugin's start_flow caller chose this
    string, but it lands on the user's browser via a public route, so we
    enforce same-origin shape here. Acceptable: a path beginning with a
    single ``/``. Anything else falls back to the platform landing page.
    """
    if not isinstance(return_to, str) or not return_to:
        return "/"
    # Reject scheme/host even if URL-encoded; only allow path-style.
    if return_to.startswith("//"):
        return "/"
    parsed = urlparse(return_to)
    if parsed.scheme or parsed.netloc:
        return "/"
    if not return_to.startswith("/"):
        return "/"
    return return_to


def _append_error(return_to: str, code: str, detail: Optional[str] = None) -> str:
    sep = "&" if "?" in return_to else "?"
    out = f"{return_to}{sep}oauth_error={quote(code)}"
    if detail:
        out += f"&detail={quote(detail)}"
    return out


def _redirect(url: str) -> RedirectResponse:
    # 302 is correct here — the browser must NOT cache the success page
    # under the callback URL (would replay state). The auth middleware
    # tags the response with no-cache headers anyway, but be explicit.
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback/{plugin_slug}", include_in_schema=True)
async def oauth_callback(plugin_slug: str, request: Request) -> RedirectResponse:
    """Public OAuth-provider redirect target. See module docstring."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    provider_error = request.query_params.get("error")

    # Step 1 — recover the flow row from `state` so we know where to
    # redirect on failure. Without a valid state we have no return_to;
    # send the user to "/" with an inline error.
    if not state or not isinstance(state, str):
        logger.warning("oauth callback (%s): missing state param", plugin_slug)
        return _redirect(_append_error("/", _ERR_INVALID_REQUEST))

    state_hash = hashlib.sha256(state.encode()).hexdigest()
    flow = _consume_flow(state_hash, plugin_slug)
    if flow is None:
        logger.warning(
            "oauth callback (%s): state not found / expired / replayed", plugin_slug,
        )
        return _redirect(_append_error("/", _ERR_INVALID_STATE))

    return_to = _safe_return_to(flow["return_to"])

    # Step 2 — provider may have redirected with an `error=` param
    # instead of a `code=` (user denied access, scope mismatch, ...).
    if provider_error:
        logger.info(
            "oauth callback (%s): provider returned error=%s", plugin_slug, provider_error,
        )
        return _redirect(_append_error(return_to, _ERR_PROVIDER_ERROR, provider_error))

    if not code or not isinstance(code, str):
        return _redirect(_append_error(return_to, _ERR_INVALID_REQUEST))

    # Step 3 — resolve the plugin's manifest-declared handler.
    # v0.10.3.2: the plugin loader doesn't put plugin dirs on sys.path
    # (it loads api/routes.py via spec_from_file_location), so a naive
    # importlib.import_module("api.oauth") can't find the plugin's
    # api/oauth.py file. resolve_oauth_callback_handler mirrors the
    # loader's pattern: dotted target → file under plugin's installed
    # directory → loaded with a slug-scoped synthetic module name.
    try:
        from ..plugin_loader import (
            get_oauth_callback_target,
            resolve_oauth_callback_handler,
        )
    except Exception as exc:  # pragma: no cover — only fires on broken import
        logger.exception("oauth callback (%s): plugin_loader import failed: %s", plugin_slug, exc)
        return _redirect(_append_error(return_to, _ERR_HANDLER_FAILED))

    target = get_oauth_callback_target(plugin_slug)
    if not target:
        logger.warning(
            "oauth callback (%s): no oauth.callback_handler declared in manifest", plugin_slug,
        )
        return _redirect(_append_error(return_to, _ERR_NO_HANDLER))

    handler = resolve_oauth_callback_handler(plugin_slug, target)
    if handler is None:
        logger.error(
            "oauth callback (%s): resolver returned None for target=%r "
            "(see prior log lines for the underlying cause)",
            plugin_slug, target,
        )
        return _redirect(_append_error(return_to, _ERR_HANDLER_FAILED, "import"))

    # Step 4 — dispatch. The handler owns the code-for-token exchange.
    try:
        result = handler(code=code, user_id=flow["user_id"])
    except Exception as exc:
        logger.exception("oauth callback (%s): handler raised: %s", plugin_slug, exc)
        return _redirect(_append_error(return_to, _ERR_HANDLER_FAILED, "exchange"))

    # Step 5 — store any returned credentials via the existing encrypted
    # credentials path. Empty creds dict is fine — plugin may store its
    # own state and just want the redirect.
    creds = getattr(result, "credentials", None) or {}
    credential_type = getattr(result, "credential_type", "oauth2") or "oauth2"
    if creds:
        try:
            from ..plugin_credentials import store_plugin_credential
            for field_name, plaintext in creds.items():
                if not isinstance(field_name, str) or not isinstance(plaintext, str):
                    logger.warning(
                        "oauth callback (%s): handler returned non-string credential %r",
                        plugin_slug, field_name,
                    )
                    continue
                store_plugin_credential(
                    plugin_id=plugin_slug,
                    field_name=field_name,
                    plaintext=plaintext,
                    credential_type=credential_type,
                    performed_by=f"oauth_callback:{flow['user_id']}",
                )
        except Exception as exc:
            logger.exception(
                "oauth callback (%s): credential store failed: %s", plugin_slug, exc,
            )
            return _redirect(_append_error(return_to, _ERR_HANDLER_FAILED, "store"))

    # Step 6 — redirect home. Handler may override the destination if it
    # needs to land the user on a follow-up step.
    override = getattr(result, "return_to", None)
    final = _safe_return_to(override) if override else return_to
    logger.info(
        "oauth callback (%s): success for user=%s → %s",
        plugin_slug, flow["user_id"], final,
    )
    return _redirect(final)


def _consume_flow(state_hash: str, plugin_slug: str) -> Optional[dict]:
    """Atomically mark the matching ``oauth_flows`` row consumed and
    return its ``user_id`` + ``return_to``. Returns ``None`` if no row
    matches — covering not-found, expired, wrong plugin, or already
    consumed (replay).

    Single round-trip ``UPDATE ... RETURNING`` so a concurrent replay
    gets zero rows. plugin_id binding prevents a state minted for plugin
    A from being replayed against plugin B's callback URL.
    """
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE oauth_flows
                SET consumed_at = NOW()
                WHERE state_token_hash = %s
                  AND plugin_id = %s
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
                RETURNING user_id::text, return_to
                """,
                (state_hash, plugin_slug),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {"user_id": row[0], "return_to": row[1]}
    except Exception as exc:
        logger.exception("oauth_flows consume failed: %s", exc)
        return None
