"""
Webhooks plugin — inbound data ingestion + outbound alert delivery.

Management (authenticated):
  GET    /plugins/webhooks/endpoints           — list all endpoints
  POST   /plugins/webhooks/endpoints           — create endpoint
  PATCH  /plugins/webhooks/endpoints/{id}      — update name, url, active
  DELETE /plugins/webhooks/endpoints/{id}      — delete endpoint
  POST   /plugins/webhooks/endpoints/{id}/test — test outbound endpoint
  GET    /plugins/webhooks/events/{id}         — list recent inbound events

Ingestion (public):
  POST   /api/webhooks/in/{slug}               — receive external data
"""

import hashlib
import hmac as _hmac
import json
import logging
import secrets
import urllib.request

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("nousviz.plugin.webhooks")

router = APIRouter()
ingestion_router = APIRouter()


def _get_conn():
    # v0.9.0: migrated from `from apps.api.src.db import get_pg_conn`
    # to the SDK contract (P202). SDK connects as the nousviz_plugin
    # role with privileges scoped to webhook_* tables.
    from nousviz_sdk import get_pg_conn
    return get_pg_conn()


def _dict_cursor(conn):
    # v0.9.0: dict_cursor is now exposed by the SDK (previously a core
    # helper). Import from nousviz_sdk instead of apps.api.src.db.
    from nousviz_sdk import dict_cursor
    return dict_cursor(conn)


def _serialize_row(row):
    d = dict(row)
    for k in ("last_event_at", "created_at", "updated_at", "received_at"):
        if d.get(k) and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


# ── List endpoints ───────────────────────────────────────────────────

@router.get("/plugins/webhooks/endpoints")
async def list_endpoints(request: Request):
    direction = request.query_params.get("direction")
    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        if direction:
            cur.execute("""
                SELECT id, name, slug, direction, url, secret IS NOT NULL as has_secret,
                       is_active, event_count, last_event_at, created_at,
                       COALESCE(channel_type, 'generic') AS channel_type,
                       COALESCE(channel_config, '{}'::jsonb) AS channel_config
                FROM webhook_endpoints WHERE direction = %s
                ORDER BY created_at DESC
            """, (direction,))
        else:
            cur.execute("""
                SELECT id, name, slug, direction, url, secret IS NOT NULL as has_secret,
                       is_active, event_count, last_event_at, created_at,
                       COALESCE(channel_type, 'generic') AS channel_type,
                       COALESCE(channel_config, '{}'::jsonb) AS channel_config
                FROM webhook_endpoints ORDER BY created_at DESC
            """)
        return {"endpoints": [_serialize_row(r) for r in cur.fetchall()]}


# ── Create endpoint ──────────────────────────────────────────────────

class CreateEndpoint(BaseModel):
    name: str
    direction: str = "inbound"
    url: Optional[str] = None
    generate_secret: bool = False


@router.post("/plugins/webhooks/endpoints")
async def create_endpoint(body: CreateEndpoint, request: Request):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")
    if body.direction not in ("inbound", "outbound"):
        raise HTTPException(400, "Direction must be 'inbound' or 'outbound'")
    if body.direction == "outbound" and not body.url:
        raise HTTPException(400, "URL is required for outbound webhooks")

    slug = secrets.token_urlsafe(16) if body.direction == "inbound" else None
    secret = secrets.token_urlsafe(32) if body.generate_secret else None
    url = body.url.strip() if body.url else None

    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        cur.execute("""
            INSERT INTO webhook_endpoints (name, slug, direction, url, secret)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, slug, direction, url, is_active, created_at
        """, (name, slug, body.direction, url, secret))
        row = _serialize_row(cur.fetchone())

    if body.direction == "inbound":
        host = request.headers.get("host", "localhost")
        proto = request.headers.get("x-forwarded-proto", "https")
        row["ingestion_url"] = f"{proto}://{host}/api/webhooks/in/{slug}"

    if secret:
        row["secret"] = secret

    return row


# ── Update endpoint ──────────────────────────────────────────────────

class UpdateEndpoint(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None
    # B283 (v0.9.11.24): typed channel + per-channel config.
    channel_type: Optional[str] = None
    channel_config: Optional[dict] = None


_ALLOWED_CHANNEL_TYPES = {"generic", "slack", "discord", "teams"}
# Discord/Teams accepted by the schema (so the column always validates),
# but B283 only formats Slack specially. The frontend disables those
# options until their tickets ship; this set is the backend safety net.
_TYPED_CHANNELS_WITH_CONFIG = {"slack"}


def _validate_channel_config(channel_type: str, cfg: dict) -> dict:
    """Reject unknown keys and validate format. Slack-only in B283;
    generic/discord/teams must be passed an empty dict."""
    if not isinstance(cfg, dict):
        raise HTTPException(400, "channel_config must be an object")
    if channel_type not in _TYPED_CHANNELS_WITH_CONFIG:
        # Generic / discord / teams: config must be empty until their
        # typed formatters ship.
        if cfg:
            raise HTTPException(
                400,
                f"channel_config not supported for channel_type={channel_type!r} yet",
            )
        return {}
    # Slack: validate known keys, reject unknown.
    allowed_keys = {"mention_user_ids", "mention_on_severities", "channel_override"}
    extra = set(cfg.keys()) - allowed_keys
    if extra:
        raise HTTPException(400, f"Unknown channel_config keys for slack: {sorted(extra)}")
    # Re-use the formatter's validators so badness is caught at write
    # time, not at the next alert dispatch.
    from apps.api.src.services.slack_formatter import (
        validate_mention_user_id,
        validate_channel_override,
    )
    out: dict = {}
    if "mention_user_ids" in cfg:
        ids = cfg["mention_user_ids"]
        if not isinstance(ids, list):
            raise HTTPException(400, "mention_user_ids must be a list")
        try:
            out["mention_user_ids"] = [validate_mention_user_id(x) for x in ids]
        except ValueError as e:
            raise HTTPException(400, f"Invalid mention_user_ids: {e}")
    if "mention_on_severities" in cfg:
        sev = cfg["mention_on_severities"]
        if not isinstance(sev, list) or not all(isinstance(s, str) for s in sev):
            raise HTTPException(400, "mention_on_severities must be a list of strings")
        valid = {"critical", "error", "warning", "timeout", "cancelled", "info"}
        bad = [s for s in sev if s not in valid]
        if bad:
            raise HTTPException(400, f"Invalid mention severities: {bad}. Allowed: {sorted(valid)}")
        out["mention_on_severities"] = sev
    if "channel_override" in cfg:
        try:
            v = validate_channel_override(cfg["channel_override"])
            if v is not None:
                out["channel_override"] = v
        except ValueError as e:
            raise HTTPException(400, f"Invalid channel_override: {e}")
    return out


@router.patch("/plugins/webhooks/endpoints/{endpoint_id}")
async def update_endpoint(endpoint_id: str, body: UpdateEndpoint):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")
    if "url" in updates:
        updates["url"] = updates["url"].strip()
    if "channel_type" in updates:
        if updates["channel_type"] not in _ALLOWED_CHANNEL_TYPES:
            raise HTTPException(
                400,
                f"channel_type must be one of {sorted(_ALLOWED_CHANNEL_TYPES)}",
            )
    if "channel_config" in updates:
        # Need to know channel_type to validate; pull current row when
        # the request didn't include one.
        ct = updates.get("channel_type")
        if ct is None:
            with _get_conn() as conn:
                cur = _dict_cursor(conn)
                cur.execute(
                    "SELECT COALESCE(channel_type, 'generic') AS channel_type "
                    "FROM webhook_endpoints WHERE id = %s",
                    (endpoint_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(404, "Endpoint not found")
                ct = row["channel_type"]
        updates["channel_config"] = json.dumps(
            _validate_channel_config(ct, updates["channel_config"])
        )
    set_parts = [f"{k} = %s" for k in updates] + ["updated_at = now()"]
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE webhook_endpoints SET {', '.join(set_parts)} WHERE id = %s RETURNING id",
            list(updates.values()) + [endpoint_id],
        )
        if not cur.fetchone():
            raise HTTPException(404, "Endpoint not found")
    return {"ok": True}


# ── Delete endpoint ──────────────────────────────────────────────────

@router.delete("/plugins/webhooks/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: str):
    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        cur.execute("SELECT name FROM webhook_endpoints WHERE id = %s", (endpoint_id,))
        endpoint = cur.fetchone()
        if not endpoint:
            raise HTTPException(404, "Endpoint not found")
        cur.execute("DELETE FROM webhook_endpoints WHERE id = %s", (endpoint_id,))
    return {"deleted": True}


# ── Test outbound ────────────────────────────────────────────────────

@router.post("/plugins/webhooks/endpoints/{endpoint_id}/test")
async def test_outbound(endpoint_id: str):
    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        cur.execute(
            """
            SELECT name, direction, url, secret,
                   COALESCE(channel_type, 'generic') AS channel_type,
                   COALESCE(channel_config, '{}'::jsonb) AS channel_config
            FROM webhook_endpoints WHERE id = %s
            """,
            (endpoint_id,),
        )
        endpoint = cur.fetchone()
    if not endpoint:
        raise HTTPException(404, "Endpoint not found")
    if endpoint["direction"] != "outbound":
        raise HTTPException(400, "Can only test outbound webhooks")
    if not endpoint["url"]:
        raise HTTPException(400, "No URL configured")

    # v0.9.11.22.8: top-level `text` field so Slack incoming webhooks
    # accept the payload (Slack returns 400 when `text` is missing).
    # v0.9.11.24 (B283): the body now flows through `format_for_channel`
    # so a Slack-typed endpoint receives Block Kit; generic-typed
    # endpoints continue to receive the same flat shape as before.
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    flat_payload = {
        "text": f"Test webhook from NousViz · endpoint: {endpoint['name']} · {timestamp_iso}",
        "alert_type": "webhook_test",
        "severity": "info",
        "title": f"Test webhook from NousViz · {endpoint['name']}",
        "event": "test",
        "source": "nousviz",
        "endpoint_name": endpoint["name"],
        "timestamp": timestamp_iso,
        "message": "This is a test webhook from NousViz.",
    }
    from apps.api.src.services.webhook_dispatch import format_for_channel
    payload = format_for_channel(
        flat_payload,
        endpoint["channel_type"],
        endpoint["channel_config"] or {},
    )

    headers = {"Content-Type": "application/json"}
    if endpoint["secret"]:
        sig = _hmac.new(endpoint["secret"].encode(), payload, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = sig

    try:
        req = urllib.request.Request(endpoint["url"], data=payload, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        return {"ok": True, "status": resp.status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── List inbound events ─────────────────────────────────────────────

@router.get("/plugins/webhooks/events/{endpoint_id}")
async def list_events(endpoint_id: str):
    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        cur.execute("""
            SELECT id, payload, source_ip, received_at
            FROM webhook_events
            WHERE endpoint_id = %s
            ORDER BY received_at DESC
            LIMIT 50
        """, (endpoint_id,))
        return {"events": [_serialize_row(r) for r in cur.fetchall()]}


# ── Public ingestion (inbound) ───────────────────────────────────────

@ingestion_router.post("/webhooks/in/{slug}")
async def receive_webhook(slug: str, request: Request):
    with _get_conn() as conn:
        cur = _dict_cursor(conn)
        cur.execute("""
            SELECT id, secret, is_active FROM webhook_endpoints
            WHERE slug = %s AND direction = 'inbound'
        """, (slug,))
        endpoint = cur.fetchone()

    if not endpoint:
        raise HTTPException(404, "Webhook not found")
    if not endpoint["is_active"]:
        raise HTTPException(410, "Webhook is disabled")

    body_bytes = await request.body()

    if endpoint["secret"]:
        sig = request.headers.get("x-webhook-signature", "")
        expected = _hmac.new(endpoint["secret"].encode(), body_bytes, hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            raise HTTPException(401, "Invalid signature")

    try:
        payload = json.loads(body_bytes)
    except (json.JSONDecodeError, ValueError):
        payload = {"raw": body_bytes.decode("utf-8", errors="replace")}

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    if "," in ip:
        ip = ip.split(",")[0].strip()

    relevant_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() in ("content-type", "user-agent", "x-github-event", "x-gitlab-event",
                          "x-stripe-signature", "x-shopify-topic")
    }

    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO webhook_events (endpoint_id, payload, headers, source_ip)
            VALUES (%s, %s, %s, %s)
        """, (endpoint["id"], json.dumps(payload), json.dumps(relevant_headers), ip))
        cur.execute("""
            UPDATE webhook_endpoints
            SET event_count = event_count + 1, last_event_at = now(), updated_at = now()
            WHERE id = %s
        """, (endpoint["id"],))

    return {"ok": True}


# ── Extra routers ────────────────────────────────────────────────────

extra_routers = [
    ("webhooks_ingestion", ingestion_router, {"prefix": "/api"}),
]
