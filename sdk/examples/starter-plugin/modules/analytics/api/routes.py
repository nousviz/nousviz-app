"""
modules/analytics/api/routes.py — Analytics Module Routes

Module routes are loaded by the plugin loader when the module is enabled.
They follow the same rules as parent plugin routes:
  - Routes under /plugins/{parent-slug}/ namespace
  - Only query tables declared in module.yaml databases
  - Use get_pg_conn() context manager
  - Parameterised SQL only
"""

from fastapi import APIRouter
from nousviz_sdk import get_pg_conn

router = APIRouter()

PLUGIN_SLUG = "starter-plugin"
BASE = f"/plugins/{PLUGIN_SLUG}"


@router.get(f"{BASE}/analytics/summary")
async def analytics_summary():
    """Aggregated analytics for the starter plugin's items."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                date_trunc('day', created_at) AS day,
                count(*) AS items_created
            FROM starter_items
            WHERE created_at >= now() - interval '30 days'
            GROUP BY day
            ORDER BY day
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    return {"series": rows}
