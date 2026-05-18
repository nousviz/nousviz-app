"""
Insights Engine — aggregates actionable insights from all installed plugins.

Two tiers:
  Tier 1: plugins/installed/*/insights.yaml — static SQL queries run by core.
  Tier 2: GET /plugins/{slug}/insights — rich programmatic insights from the plugin's
          own API route. Core calls each installed plugin's endpoint and merges results.
          Complex multi-query logic (e.g. week-over-week comparisons) belongs in the
          plugin repo, not here.
"""
import json
import logging
import os
import urllib.request
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Query

from ..db import get_pg_conn
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.insights import InsightsListResponse

logger = logging.getLogger("nousviz.insights")
router = APIRouter(prefix="/api/insights", tags=["insights"])

# B228: register insights routes (silent-leak fix). dashboards.read tier
# since insights are derived from plugin data the user already has access to.
register_route("GET", "/api/insights/", "dashboards.read")

PLUGINS_INSTALLED = Path(__file__).resolve().parents[4] / "plugins" / "installed"


def _run_yaml_insights() -> list[dict]:
    """Tier 1: run static SQL queries from installed plugins' insights.yaml files."""
    results = []
    for path in sorted(PLUGINS_INSTALLED.glob("*/insights.yaml")):
        plugin_slug = path.parent.name
        try:
            cfg = yaml.safe_load(path.read_text())
        except Exception as e:
            logger.warning(f"insights.yaml parse error for {plugin_slug}: {e}")
            continue

        with get_pg_conn() as conn:
            cur = conn.cursor()
            # S105: sandbox insights SQL. Same defense-in-depth pattern
            # as fusion widgets (S102) — plugin YAML is trusted at install
            # time but can be edited in place post-install. Read-only
            # transaction + nousviz_query role ensures edits can only
            # query, not mutate.
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SET LOCAL ROLE nousviz_query")
            cur.execute("SET LOCAL statement_timeout = '10s'")
            for query_spec in cfg.get("queries", []):
                try:
                    cur.execute(query_spec["sql"])
                    cols = [d[0] for d in cur.description]
                    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
                    results.append({
                        "plugin": plugin_slug,
                        "id": query_spec["id"],
                        "label": query_spec["label"],
                        "description": query_spec.get("description", ""),
                        "severity": query_spec.get("severity", "info"),
                        "rows": rows,
                    })
                except Exception as e:
                    conn.rollback()
                    # After rollback the transaction settings are reset;
                    # re-apply for the next query in the same loop iteration.
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SET LOCAL ROLE nousviz_query")
                    cur.execute("SET LOCAL statement_timeout = '10s'")
                    if query_spec.get("fallback_empty"):
                        continue
                    logger.warning(f"Insight query '{query_spec.get('id')}' in {plugin_slug} failed: {e}")

    return results


def _run_plugin_insights() -> list[dict]:
    """Tier 2: call GET /plugins/{slug}/insights on each installed plugin that has the route.
    Silently skips plugins that don't expose this endpoint.
    """
    results = []
    api_port = os.environ.get("API_PORT", "8000")

    if not PLUGINS_INSTALLED.exists():
        return results

    for plugin_dir in sorted(PLUGINS_INSTALLED.iterdir()):
        if not plugin_dir.is_dir():
            continue
        slug = plugin_dir.name
        url = f"http://localhost:{api_port}/plugins/{slug}/insights"
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read())
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict) and "insights" in data:
                results.extend(data["insights"])
        except Exception:
            # Plugin doesn't expose /insights — skip silently
            pass

    return results


@router.get(
    "/",
    operation_id="insights.list",
    response_model=InsightsListResponse,
    response_model_exclude_none=True,
    summary="Aggregate insights across all installed plugins",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the dashboards.read permission."},
    },
)
def get_insights(
    limit: int = Query(20, ge=1, le=100),
    _: None = Depends(requires("dashboards.read")),
):
    """Aggregate insights from all installed plugins (Tier 1 YAML + Tier 2 plugin endpoints).

    Sorted by severity (critical → warning → info → good → tip) before
    truncation. `total` is the un-truncated count so the UI can show
    "20 of 47" pagination hints.
    """
    yaml_insights = _run_yaml_insights()
    plugin_insights = _run_plugin_insights()

    all_insights = yaml_insights + plugin_insights

    severity_order = {"critical": 0, "warning": 1, "info": 2, "good": 3, "tip": 4}
    all_insights.sort(key=lambda x: severity_order.get(x.get("severity", "tip"), 5))

    return {
        "insights": all_insights[:limit],
        "total": len(all_insights),
    }
