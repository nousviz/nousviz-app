"""
api/routes.py — Starter Plugin API Routes

This file is automatically discovered and loaded by the NousViz plugin loader.
It must export a `router` (FastAPI APIRouter instance).

Rules:
  - All routes must be under /plugins/{slug}/ — never in the core /api/* namespace
  - Only query tables declared in plugin.yaml databases — never other plugins' tables
  - All Postgres connections must use `with get_pg_conn() as conn:` — the context
    manager handles pool return, commit on success, and rollback on exception
  - All SQL must use parameterised queries — never f-strings or .format()
  - Never import from other plugin modules
"""

from fastapi import APIRouter, HTTPException, Query
from nousviz_sdk import get_pg_conn

router = APIRouter()

PLUGIN_SLUG = "starter-plugin"
BASE = f"/plugins/{PLUGIN_SLUG}"


# ── Health check ──────────────────────────────────────────────────────────────
# Every plugin should implement a health-check endpoint.
# The marketplace "Configure" page calls this to verify the plugin is working.

@router.get(f"{BASE}/health-check")
async def health_check():
    """Verify the plugin's database tables exist and are reachable."""
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM starter_items")
            count = cur.fetchone()[0]
        return {"status": "ok", "items": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


# ── List items ────────────────────────────────────────────────────────────────

@router.get(f"{BASE}/items")
async def list_items(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    List items from this plugin's starter_items table.

    Returns:
        {"items": [...], "total": int}
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Always use parameterised queries — never f-strings or .format() with user input
        cur.execute(
            "SELECT id, name, status, created_at "
            "FROM starter_items "
            "ORDER BY created_at DESC "
            "LIMIT %s OFFSET %s",
            (limit, offset),
        )
        cols = [d[0] for d in cur.description]
        items = [dict(zip(cols, row)) for row in cur.fetchall()]

        cur.execute("SELECT count(*) FROM starter_items")
        total = cur.fetchone()[0]

    return {"items": items, "total": total}


# ── Get single item ───────────────────────────────────────────────────────────

@router.get(f"{BASE}/items/{{item_id}}")
async def get_item(item_id: str):
    """Get a single item by ID."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, status, metadata, created_at "
            "FROM starter_items WHERE id = %s",
            (item_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Item {item_id!r} not found")
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


# ── Badge endpoint ─────────────────────────────────────────────────────────────
# If plugin.yaml navigation declares badge: items_count, the sidebar calls this
# endpoint and renders the returned count as a badge on the nav item.

@router.get(f"{BASE}/badge/items_count")
async def items_count_badge():
    """Return the count of active items for the sidebar badge."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM starter_items WHERE status = 'active'")
        return {"count": cur.fetchone()[0]}


# ── P206 (v0.9.0): smoke-test endpoints ──────────────────────────────────────
# The deploy smoke hits these to prove the SDK contract works end-to-end.
# If any of these fail after a deploy, the deploy fails — the gate that
# catches the next SDK regression before it ships.

@router.get(f"{BASE}/sdk-version")
async def sdk_version():
    """Return the loaded SDK version. Proves nousviz_sdk is importable
    from plugin code at runtime."""
    import nousviz_sdk
    return {"sdk_version": nousviz_sdk.__version__}


@router.get(f"{BASE}/db-check")
async def db_check():
    """Prove the SDK's DB contract works: open a connection via the
    broker-delivered nousviz_plugin role, run a SELECT on an own table,
    return the count. P203 guarantees this connection cannot touch
    credentials / users / api_keys.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM starter_items")
        count = cur.fetchone()[0]
    return {"ok": True, "count": count}


@router.get(f"{BASE}/env-check")
async def env_check():
    """P208 smoke: prove secrets are NOT in subprocess env.

    Looks for any env var matching conventional secret-field prefixes
    that the plugin itself declares. Before v0.9.0 these would be
    populated (decrypted into os.environ); after P208 they must be
    absent. Returns a dict the smoke script can assert on.
    """
    import os
    # Starter plugin doesn't declare secret connection fields by default;
    # this endpoint verifies the *absence* regardless.
    # Smoke assertion: any value prefixed STARTER_*_PASSWORD / SECRET
    # must be absent.
    leaked = []
    for key, value in os.environ.items():
        if not key.startswith("STARTER_"):
            continue
        # Tokenish variable names that should never be in env
        if any(x in key.lower() for x in ("password", "secret", "token", "key")):
            leaked.append(key)
    return {
        "ok": len(leaked) == 0,
        "leaked_env_keys": leaked,
        "hint": "If non-empty, P208 broker is not routing secrets correctly.",
    }


# ── Extra routers (optional) ──────────────────────────────────────────────────
# Use extra_routers only if you need routes outside /plugins/{slug}/.
# Examples: tracking redirect handlers (/go/{code}), public CMS pages (/site/*).
# Most plugins do not need this — delete if unused.

# from fastapi import APIRouter as _APIRouter
# _redirect_router = _APIRouter()
#
# @_redirect_router.get("/go/{code}")
# async def handle_redirect(code: str):
#     ...
#
# extra_routers = [
#     ("redirect_router", _redirect_router, {}),   # mounted at root
# ]
