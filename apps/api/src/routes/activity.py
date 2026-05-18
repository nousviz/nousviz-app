"""
/api/activity — Activity log and dashboard analytics

Tracks page views, queries, exports, and all user actions.
Provides dashboard usage analytics so admins know which dashboards
are actually being used.

Storage: Postgres `activity_events` table (migration 024).
"""

import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..db import get_pg_conn, rows_as_dicts
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.activity import (
    ActivityListResponse,
    ActivityLogResponse,
    DashboardUsageResponse,
    UserAnalyticsResponse,
)

logger = logging.getLogger("nousviz.api.activity")

router = APIRouter(tags=["activity"])

# B228: register activity routes (silent-leak fix).
# POST is for the SPA logging user actions — any authenticated user.
# GETs are audit-style — admin-tier.
register_route("POST", "/api/activity", "users.read_self")
register_route("GET", "/api/activity", "system.audit")
register_route("GET", "/api/activity/dashboard-usage", "system.audit")
register_route("GET", "/api/activity/analytics", "system.audit")


class ActivityEvent(BaseModel):
    action: str  # page_view | query | export | alert_triggered | annotation_created | note_created | etc.
    category: str = "general"
    page_path: str | None = None
    plugin_id: str | None = None
    detail: dict = {}
    duration_ms: int | None = None


def record_activity(
    action: str,
    plugin_id: str | None = None,
    detail: dict | None = None,
    category: str = "system",
    ip: str | None = None,
    user_id: str | None = None,
) -> None:
    """Internal helper — log an activity event from backend code (not via HTTP).

    Used by plugin install/uninstall, settings changes, etc. to populate the
    launchpad's Recent Activity section without requiring the frontend to POST.
    """
    import json as _json
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO activity_events (action, category, plugin_id, detail, ip_address, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (action, category, plugin_id, _json.dumps(detail or {}), ip, user_id))
    except Exception:
        pass


@router.post(
    "/activity",
    operation_id="activity.log",
    response_model=ActivityLogResponse,
    summary="Record a user activity event",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
async def log_activity(
    event: ActivityEvent,
    request: Request,
    _: None = Depends(requires("users.read_self")),
):
    """Record a user activity event with device and IP metadata.

    Open to any authenticated user (POST-only — they can log their own
    activity but can't read the firehose).
    """
    import json

    user_agent = request.headers.get("user-agent", "")
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    if "," in ip:
        ip = ip.split(",")[0].strip()

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO activity_events (action, category, page_path, plugin_id, detail, duration_ms, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            event.action, event.category, event.page_path, event.plugin_id,
            json.dumps(event.detail), event.duration_ms, ip, user_agent,
        ))

    return {"status": "logged"}


@router.get(
    "/activity",
    operation_id="activity.list",
    response_model=ActivityListResponse,
    response_model_exclude_none=True,
    summary="List recent activity events (admin-only firehose)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def list_activity(
    action: str | None = None,
    plugin_id: str | None = None,
    page_path: str | None = None,
    limit: int = 50,
    _: None = Depends(requires("system.audit")),
):
    """List recent activity. Newest-first, optional filters on action /
    plugin_id / page_path."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM activity_events WHERE 1=1"
        params: list = []

        if action:
            sql += " AND action = %s"
            params.append(action)
        if plugin_id:
            sql += " AND plugin_id = %s"
            params.append(plugin_id)
        if page_path:
            sql += " AND page_path = %s"
            params.append(page_path)

        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        cur.execute(sql, params)
        rows = rows_as_dicts(cur)

    for r in rows:
        if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
            r["created_at"] = r["created_at"].isoformat()

    return {"events": rows, "count": len(rows)}


CORE_PAGE_LABELS: dict[str, str] = {
    "/": "Home",
    "/alerts": "Alerts",
    "/analytics": "Analytics",
    "/annotations": "Annotations",
    "/connections": "Connections",
    "/data-port": "Data Port",
    "/datasets": "Datasets",
    "/docs": "Documentation",
    "/fusions": "Fusions",
    "/marketplace": "Marketplace",
    "/plugins": "Plugins",
    "/settings": "Settings",
    "/shares": "Shares",
}


def _resolve_page_label(path: str, plugin_labels: dict[str, str]) -> str | None:
    """Resolve a URL path to a human-readable label. Returns None for unknown paths."""
    if path in CORE_PAGE_LABELS:
        return CORE_PAGE_LABELS[path]
    for core_path, label in CORE_PAGE_LABELS.items():
        if core_path != "/" and path.startswith(core_path + "/"):
            suffix = path[len(core_path) + 1:]
            return f"{label} — {suffix.replace('/', ' › ')}"
    import re
    m = re.match(r"^/plugin/([^/]+)(?:/([^/]+))?", path)
    if m:
        slug = m.group(1)
        tab = m.group(2)
        display = plugin_labels.get(slug, slug)
        return f"{display} — {tab.replace('-', ' ').title()}" if tab else display
    return None


def _load_events_since(days: int) -> list[dict]:
    """Load activity events from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM activity_events WHERE created_at >= %s ORDER BY created_at ASC",
            (cutoff,),
        )
        rows = rows_as_dicts(cur)
    for r in rows:
        if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def _get_plugin_labels() -> tuple[dict[str, str], list[str]]:
    """Scan installed plugin manifests for display names + dashboard paths."""
    import yaml as _yaml
    _installed_dir = Path(__file__).resolve().parents[4] / "plugins" / "installed"
    plugin_labels: dict[str, str] = {}
    all_dashboard_paths: list[str] = []
    if _installed_dir.exists():
        for _plugin_dir in _installed_dir.iterdir():
            if not _plugin_dir.is_dir():
                continue
            _manifest_path = _plugin_dir / "plugin.yaml"
            if not _manifest_path.exists():
                continue
            try:
                with open(_manifest_path) as _f:
                    _manifest = _yaml.safe_load(_f)
                _slug = _manifest.get("name") or _plugin_dir.name
                plugin_labels[_slug] = _manifest.get("display_name") or _slug
                for _dash in _manifest.get("dashboards", []):
                    all_dashboard_paths.append(f"/plugin/{_slug}/{_dash['name']}")
            except Exception:
                continue
    return plugin_labels, all_dashboard_paths


@router.get(
    "/activity/dashboard-usage",
    operation_id="activity.dashboard_usage",
    response_model=DashboardUsageResponse,
    summary="Per-page and per-plugin usage analytics",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def dashboard_usage(
    days: int = 30,
    _: None = Depends(requires("system.audit")),
):
    """Analytics: which dashboards are being used?

    Aggregates page_view events into per-page + per-plugin counts plus
    a daily-activity histogram. `unused_dashboards` enumerates manifest-
    declared dashboard paths that received zero views in the period.
    """
    entries = _load_events_since(days)

    page_views: dict[str, int] = defaultdict(int)
    plugin_views: dict[str, int] = defaultdict(int)
    action_counts: dict[str, int] = defaultdict(int)
    daily_activity: dict[str, int] = defaultdict(int)

    for e in entries:
        action_counts[e.get("action", "unknown")] += 1
        if e.get("action") == "page_view" and e.get("page_path"):
            page_views[e["page_path"]] += 1
        if e.get("plugin_id"):
            plugin_views[e["plugin_id"]] += 1
        day = e.get("created_at", "")[:10]
        daily_activity[day] += 1

    sorted_pages = sorted(page_views.items(), key=lambda x: x[1], reverse=True)
    sorted_plugins = sorted(plugin_views.items(), key=lambda x: x[1], reverse=True)

    plugin_labels, all_dashboard_paths = _get_plugin_labels()
    unused = [p for p in all_dashboard_paths if page_views.get(p, 0) == 0]

    resolved_pages = []
    for path, views in sorted_pages:
        label = _resolve_page_label(path, plugin_labels)
        if label:
            resolved_pages.append({"path": path, "label": label, "views": views})

    return {
        "period_days": days,
        "total_events": sum(action_counts.values()),
        "page_views": resolved_pages,
        "plugin_activity": [{"plugin": plugin_labels.get(p, p), "events": v} for p, v in sorted_plugins],
        "action_breakdown": dict(action_counts),
        "daily_activity": [{"date": d, "events": c} for d, c in sorted(daily_activity.items())],
        "unused_dashboards": unused,
    }


@router.get(
    "/activity/analytics",
    operation_id="activity.analytics",
    response_model=UserAnalyticsResponse,
    summary="Admin analytics: time, devices, IPs, sessions",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
async def user_analytics(
    days: int = 30,
    _: None = Depends(requires("system.audit")),
):
    """Admin analytics: time spent, devices, IPs, sessions, and usage patterns.

    Time-spent is a heuristic — sums gaps between consecutive page_view
    events, capped at 30 minutes per gap so an idle tab doesn't inflate
    the total. Sessions are runs of page_views separated by gaps >= 30 min.
    """
    filtered = _load_events_since(days)

    page_views = [e for e in filtered if e.get("action") == "page_view"]

    # Time spent estimate from consecutive page views
    total_time_minutes = 0.0
    for i in range(1, len(page_views)):
        try:
            prev = datetime.fromisoformat(page_views[i - 1]["created_at"])
            curr = datetime.fromisoformat(page_views[i]["created_at"])
            gap = (curr - prev).total_seconds()
            if gap < 1800:
                total_time_minutes += gap / 60
        except Exception:
            pass

    # Devices and browsers
    devices: dict[str, int] = defaultdict(int)
    browsers: dict[str, int] = defaultdict(int)
    ips: dict[str, int] = defaultdict(int)

    for e in filtered:
        ua = e.get("user_agent") or ""
        ip = e.get("ip_address") or "unknown"
        ips[ip] += 1

        if "Mobile" in ua or "iPhone" in ua or "Android" in ua:
            devices["Mobile"] += 1
        elif "iPad" in ua or "Tablet" in ua:
            devices["Tablet"] += 1
        else:
            devices["Desktop"] += 1

        if "Chrome" in ua and "Edg" not in ua:
            browsers["Chrome"] += 1
        elif "Firefox" in ua:
            browsers["Firefox"] += 1
        elif "Safari" in ua and "Chrome" not in ua:
            browsers["Safari"] += 1
        elif "Edg" in ua:
            browsers["Edge"] += 1
        else:
            browsers["Other"] += 1

    # Sessions (gaps > 30 minutes)
    session_count = 1 if page_views else 0
    for i in range(1, len(page_views)):
        try:
            prev = datetime.fromisoformat(page_views[i - 1]["created_at"])
            curr = datetime.fromisoformat(page_views[i]["created_at"])
            if (curr - prev).total_seconds() > 1800:
                session_count += 1
        except Exception:
            pass

    # Hourly distribution
    hourly: dict[int, int] = defaultdict(int)
    for e in filtered:
        try:
            hour = datetime.fromisoformat(e["created_at"]).hour
            hourly[hour] += 1
        except Exception:
            pass
    peak_hour = max(hourly, key=hourly.get) if hourly else 0

    # Time per page
    page_time: dict[str, float] = defaultdict(float)
    for i in range(1, len(page_views)):
        try:
            prev = datetime.fromisoformat(page_views[i - 1]["created_at"])
            curr = datetime.fromisoformat(page_views[i]["created_at"])
            gap = (curr - prev).total_seconds() / 60
            if gap < 30:
                page_time[page_views[i - 1].get("page_path", "unknown")] += gap
        except Exception:
            pass

    sorted_page_time = sorted(page_time.items(), key=lambda x: x[1], reverse=True)

    return {
        "period_days": days,
        "total_events": len(filtered),
        "total_page_views": len(page_views),
        "estimated_time_minutes": round(total_time_minutes, 1),
        "estimated_time_display": f"{int(total_time_minutes // 60)}h {int(total_time_minutes % 60)}m",
        "sessions": session_count,
        "avg_session_minutes": round(total_time_minutes / max(session_count, 1), 1),
        "devices": dict(devices),
        "browsers": dict(browsers),
        "unique_ips": list(ips.keys()),
        "ip_activity": dict(sorted(ips.items(), key=lambda x: x[1], reverse=True)),
        "peak_hour": f"{peak_hour:02d}:00",
        "hourly_distribution": {f"{h:02d}:00": c for h, c in sorted(hourly.items())},
        "time_per_page": [
            {"path": p, "minutes": round(m, 1)}
            for p, m in sorted_page_time[:20]
        ],
    }
