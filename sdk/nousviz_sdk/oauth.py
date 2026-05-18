"""B312 (v0.10.3): plugin OAuth callback helpers.

Plugins that need a third-party OAuth dance (Google, Slack, GitHub, ...)
hand the **redirect URI** to the provider, then let core handle the
provider's redirect at a public route. The provider can't carry a NousViz
session token on its redirect — that's why the platform owns the callback.

Two pieces live on the plugin side:

1. **Start the flow.** Before redirecting the user's browser to the
   provider's auth URL, call :func:`start_flow` to mint a one-shot
   ``state`` token. Pass that token to the provider as the ``state``
   query param. core records the binding (state → plugin → user →
   return_to) and the provider echoes it back unmodified.

2. **Handle the redirect.** Declare a callback in ``plugin.yaml``::

       oauth:
         callback_handler: "api.oauth:handle_callback"

   The dotted target must be ``module:function``. Signature::

       from nousviz_sdk.oauth import OAuthCallbackResult

       def handle_callback(code: str, user_id: str) -> OAuthCallbackResult:
           tokens = exchange_code(code)                  # plugin's own logic
           return OAuthCallbackResult(
               credentials={"refresh_token": tokens.refresh_token,
                            "access_token":  tokens.access_token},
               return_to=None,  # use the URL the plugin passed to start_flow
           )

   core imports the target in-process when the provider redirects back,
   calls the handler, stores any returned credentials via the existing
   encrypted-credentials table, and 302s the browser to ``return_to``.

Provider configuration: register
``https://<your-host>/api/oauth/callback/<plugin-slug>`` as the redirect
URI in the provider's dashboard. The path is plugin-stable; only the
``<plugin-slug>`` segment varies per plugin.

Failure UX
----------
- Invalid / expired / replayed state → 302 to ``return_to`` with
  ``?oauth_error=invalid_state``. The plugin's settings page should
  surface the param as an inline error banner.
- Handler raises → 302 to ``return_to`` with ``?oauth_error=handler_failed``
  and ``&detail=<short>``. The exception message is **not** echoed to the
  user — only logged server-side.
- Provider sent an ``error=`` param instead of ``code=`` → 302 to
  ``return_to`` with ``?oauth_error=provider_error&detail=<provider_error>``.

Security notes
--------------
- ``state`` is opaque ``secrets.token_urlsafe(32)``; only its SHA256
  hash is persisted. The raw token lives briefly in the URL bar and in
  the provider's request logs.
- One-shot: ``consumed_at`` is set on first successful match. Replays
  miss the ``WHERE consumed_at IS NULL`` guard.
- 10-minute default TTL. Don't raise it — Google's auth codes also
  expire in ~10 minutes so a longer state window has no upside.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from .db import get_pg_conn

_logger = logging.getLogger("nousviz_sdk.oauth")

DEFAULT_TTL_SECONDS = 600  # 10 minutes — matches typical provider auth-code TTL.


@dataclass(frozen=True)
class OAuthCallbackResult:
    """Return value from a plugin's OAuth callback handler.

    :param credentials: Field-name → plaintext value mapping. core stores
        these in the encrypted-credentials table for this plugin via
        ``plugin_credentials.store_plugin_credential``. Keys are the
        same field names the plugin reads via
        :func:`nousviz_sdk.credentials.get_credential`. Pass an empty
        dict if the handler stores its own state and just wants the
        302 redirect.
    :param return_to: Optional override for the final redirect target.
        When ``None`` (the default), core redirects to the ``return_to``
        the plugin passed to :func:`start_flow`. Use this only when the
        plugin needs to land the user on a different page based on
        callback outcome (e.g. "pick which Google Analytics property to
        use" follow-up step).
    :param credential_type: Passed through to ``store_plugin_credential``.
        Defaults to ``"oauth2"`` for the connections-table audit trail.
    """

    credentials: dict[str, str] = field(default_factory=dict)
    return_to: Optional[str] = None
    credential_type: str = "oauth2"


def start_flow(
    *,
    plugin_slug: str,
    user_id: str,
    return_to: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    request_ip: Optional[str] = None,
    request_ua: Optional[str] = None,
) -> str:
    """Mint a one-shot ``state`` token and persist its binding.

    Call this from the plugin route that kicks off the OAuth dance,
    immediately before redirecting the user's browser to the provider's
    authorization URL. Pass the returned token as the ``state`` query
    param on that URL. When the provider redirects back to
    ``/api/oauth/callback/<plugin_slug>``, core matches on the SHA256
    hash to recover the originating user and ``return_to``.

    :param plugin_slug: The plugin's slug. Used by core to look up the
        ``oauth.callback_handler`` declared in the plugin's manifest.
    :param user_id: The originating user's id (UUID string). The plugin
        route is gated by the operator's session, so this is the user
        already authenticated when the flow started.
    :param return_to: The URL the user's browser should land on after
        core finishes the dance. Typically the plugin's settings page,
        e.g. ``"/plugin/google-analytics/settings"``. Relative paths
        are passed through to the 302 response unchanged.
    :param ttl_seconds: How long the state row stays valid. Default 600
        (10 minutes) — matches typical provider auth-code TTL.
    :param request_ip: Optional IP for the audit row.
    :param request_ua: Optional User-Agent for the audit row.

    :returns: The raw state token. Hand it to the provider as ``state``;
        do not store it client-side.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    # v0.10.3.1: explicit try/except so a permission / FK / autocommit
    # failure leaves a server-side breadcrumb even when the plugin route
    # catches the exception and falls back to redirecting anyway.
    # The prior silent-failure mode (v0.10.3) was indistinguishable from
    # "callback received stale state" downstream, costing ~30 min of
    # debug time on the B312 launch.
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO oauth_flows
                     (state_token_hash, plugin_id, user_id, return_to,
                      expires_at, ip_address, user_agent)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    token_hash,
                    plugin_slug,
                    user_id,
                    return_to,
                    expires_at,
                    request_ip,
                    request_ua,
                ),
            )
    except Exception as exc:
        _logger.error(
            "start_oauth_flow: insert into oauth_flows failed (plugin=%s, "
            "user_id=%r): %s. The provider redirect will fail with "
            "invalid_state because no row was persisted.",
            plugin_slug, user_id, exc,
        )
        raise

    return raw_token
