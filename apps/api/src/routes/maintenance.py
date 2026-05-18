"""
B279 (v0.9.11.17) — operator-facing maintenance API.

Backs the `/settings/maintenance` page. Surfaces every retention policy
with current state (rows total, rows that would be pruned, last-run
outcome) and exposes endpoints for editing thresholds, flipping pause,
and triggering manual runs.

Permissions: every endpoint requires `system.audit`. The retention
worker reads the same overrides table directly via psycopg2 — it
doesn't go through this API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import ErrorDetail, RBACErrorDetail
from ..models.maintenance import (
    AvailableWebhooksResponse,
    CreateJobAlertSubscriptionBody,
    DiagnosticAlertSubscription,
    DiagnosticAlertSubscriptionListResponse,
    DiagnosticAlertTestResponse,
    JobAlertSubscription,
    JobAlertSubscriptionListResponse,
    JobAlertTestResponse,
    RetentionListResponse,
    RetentionPolicyState as RetentionPolicyStateModel,
    RetentionRunAllResponse,
    RetentionRunResponse,
    UpdateDiagnosticAlertSubscriptionBody,
    UpdateJobAlertSubscriptionBody,
    UpdateRetentionPolicyBody,
)
from ..rbac import register_route, requires
from ..services.retention import (
    POLICIES_BY_KEY,
    execute_policy,
    get_policies_state,
    run_all_unpaused,
    set_policy_state,
)
from ..services.diagnostic_alerts import (
    fire_test_alert,
    list_subscriptions,
    set_subscription,
)
from ..services import job_alerts as _job_alerts

logger = logging.getLogger("nousviz.routes.maintenance")

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# RBAC registry — every endpoint requires system.audit (operator-only).
register_route("GET", "/api/maintenance/retention", "system.audit")
register_route("PUT", "/api/maintenance/retention/{policy_key}", "system.audit")
register_route("POST", "/api/maintenance/retention/{policy_key}/run", "system.audit")
register_route("POST", "/api/maintenance/retention/run-all", "system.audit")
# B274 (v0.9.11.20): diagnostic-alert subscription management.
register_route("GET", "/api/maintenance/diagnostic-alerts/subscriptions", "system.audit")
register_route("PUT", "/api/maintenance/diagnostic-alerts/subscriptions/{webhook_id}", "system.audit")
register_route("POST", "/api/maintenance/diagnostic-alerts/test", "system.audit")
# B284 (v0.9.11.23): per-job-run failure alert subscriptions.
register_route("GET", "/api/maintenance/job-alerts", "system.audit")
register_route("GET", "/api/maintenance/job-alerts/webhooks", "system.audit")
register_route("POST", "/api/maintenance/job-alerts", "system.audit")
register_route("PUT", "/api/maintenance/job-alerts/{sub_id}", "system.audit")
register_route("DELETE", "/api/maintenance/job-alerts/{sub_id}", "system.audit")
register_route("POST", "/api/maintenance/job-alerts/{sub_id}/test", "system.audit")


def _state_to_model(s) -> RetentionPolicyStateModel:
    return RetentionPolicyStateModel(
        key=s.key,
        table=s.table,
        field=s.field,
        description=s.description,
        retention_days=s.retention_days,
        paused=s.paused,
        rows_total=s.rows_total,
        rows_would_prune=s.rows_would_prune,
        last_run_at=s.last_run_at,
        last_run_rows_deleted=s.last_run_rows_deleted,
        last_run_error=s.last_run_error,
        updated_at=s.updated_at,
    )


@router.get(
    "/retention",
    operation_id="maintenance.retention.list",
    response_model=RetentionListResponse,
    response_model_exclude_none=True,
    summary="List retention policies with live row counts and last-run state",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def list_retention_policies(
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return every retention policy registered in the POLICIES code
    constant, joined with the operator-tuned overrides + live counts.

    Each policy ships paused; first deploy is a no-op. Operator flips
    each on from `/settings/maintenance` after reviewing the
    `rows_would_prune` preview.
    """
    states = get_policies_state()
    return {
        "policies": [_state_to_model(s).model_dump() for s in states],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


@router.put(
    "/retention/{policy_key}",
    operation_id="maintenance.retention.update",
    response_model=RetentionPolicyStateModel,
    response_model_exclude_none=True,
    summary="Update a retention policy (threshold or paused flag)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Policy key not registered."},
        422: {"model": ErrorDetail, "description": "Invalid retention_days (must be 0-3650)."},
    },
)
def update_retention_policy(
    policy_key: str,
    body: UpdateRetentionPolicyBody,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Update one or both editable fields on a retention policy. Audit-
    logged with the operator's user_id."""
    if policy_key not in POLICIES_BY_KEY:
        raise HTTPException(404, f"Unknown retention policy: {policy_key!r}")
    if body.retention_days is None and body.paused is None:
        raise HTTPException(422, "Pass at least one of retention_days or paused")

    actor_user_id = getattr(request.state, "user_id", None)
    try:
        set_policy_state(
            policy_key,
            retention_days=body.retention_days,
            paused=body.paused,
            by_user=actor_user_id,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Structured audit entry.
    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"retention policy updated: {policy_key}",
            {
                "policy_key": policy_key,
                "retention_days": body.retention_days,
                "paused": body.paused,
            },
            source="retention",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass

    # Return the updated state so the UI can optimistic-update.
    states = get_policies_state()
    for s in states:
        if s.key == policy_key:
            return _state_to_model(s).model_dump()
    # Should be unreachable since we validated policy_key above.
    raise HTTPException(500, "Policy disappeared after update")


@router.post(
    "/retention/{policy_key}/run",
    operation_id="maintenance.retention.run",
    response_model=RetentionRunResponse,
    summary="Run a retention policy now (force; bypasses paused state)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Policy key not registered."},
    },
)
def run_retention_policy_now(
    policy_key: str,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Run one policy immediately. Bypasses the paused flag (the
    operator just clicked "Run now" — that's their consent). Audit-
    logged with the operator's user_id."""
    if policy_key not in POLICIES_BY_KEY:
        raise HTTPException(404, f"Unknown retention policy: {policy_key!r}")

    actor_user_id = getattr(request.state, "user_id", None)
    started = monotonic()
    rows_deleted = 0
    err: str | None = None
    try:
        rows_deleted = execute_policy(policy_key, force_run=True)
    except Exception as e:
        err = f"{e.__class__.__name__}: {str(e)[:300]}"
        # Surface the failure to the audit log + persisted policy row.
        try:
            from ..services.retention import _record_last_run as _rec
            _rec(policy_key, 0, error=err)
        except Exception:
            pass
        raise HTTPException(500, f"Retention run failed: {err}")
    finally:
        duration_ms = int((monotonic() - started) * 1000)
        try:
            from ..log_events import log_job_event
            log_job_event(
                "info" if err is None else "error",
                f"retention policy run: {policy_key}"
                + (f" — {rows_deleted} rows deleted" if err is None else f" — {err}"),
                {
                    "policy_key": policy_key,
                    "rows_deleted": rows_deleted,
                    "duration_ms": duration_ms,
                    "manual": True,
                    "error": err,
                },
                source="retention",
                actor_user_id=str(actor_user_id) if actor_user_id else None,
            )
        except Exception:
            pass

    # Record success path on the overrides row too (the worker does
    # this for cron runs; we mirror it here for manual runs).
    try:
        from ..services.retention import _record_last_run as _rec
        _rec(policy_key, rows_deleted, error=None)
    except Exception:
        pass

    return {
        "policy_key": policy_key,
        "rows_deleted": rows_deleted,
        "duration_ms": duration_ms,
    }


@router.post(
    "/retention/run-all",
    operation_id="maintenance.retention.run_all",
    response_model=RetentionRunAllResponse,
    summary="Run every UNPAUSED retention policy now",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def run_all_retention_policies(
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Run every currently-unpaused policy. Paused policies are
    skipped; failed policies are reported per-key. Audit-logged."""
    actor_user_id = getattr(request.state, "user_id", None)
    started = monotonic()
    summary = run_all_unpaused()
    duration_ms = int((monotonic() - started) * 1000)
    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"retention run-all: {sum(v for v in summary.values() if isinstance(v, int))} rows deleted",
            {"summary": summary, "duration_ms": duration_ms, "manual": True},
            source="retention",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass
    return {"summary": summary, "duration_ms": duration_ms}


# ── B274 (v0.9.11.20): diagnostic-alert subscriptions ───────────────


@router.get(
    "/diagnostic-alerts/subscriptions",
    operation_id="maintenance.diagnostic_alerts.list_subscriptions",
    response_model=DiagnosticAlertSubscriptionListResponse,
    response_model_exclude_none=True,
    summary="List outbound webhooks + their diagnostic-alert subscription state (B274)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def list_diagnostic_alert_subscriptions(
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Return every outbound webhook from `webhook_endpoints` (the
    webhooks plugin's table) along with whether it's subscribed to
    receive diagnostic alerts.

    Empty list when the webhooks plugin isn't installed — operator
    sees no rows and gets no toggle, no error.
    """
    return {"subscriptions": list_subscriptions()}


@router.put(
    "/diagnostic-alerts/subscriptions/{webhook_id}",
    operation_id="maintenance.diagnostic_alerts.update_subscription",
    response_model=DiagnosticAlertSubscription,
    response_model_exclude_none=True,
    summary="Subscribe or unsubscribe a webhook from diagnostic alerts (B274)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Webhook id not registered."},
    },
)
def update_diagnostic_alert_subscription(
    webhook_id: str,
    body: UpdateDiagnosticAlertSubscriptionBody,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Toggle subscription for one outbound webhook. Audit-logged with
    the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID."""
    actor_user_id = getattr(request.state, "user_id", None)
    try:
        set_subscription(
            webhook_id,
            body.enabled,
            by_user=str(actor_user_id) if actor_user_id else None,
        )
    except KeyError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"diagnostic alert subscription updated: {webhook_id} → enabled={body.enabled}",
            {"webhook_id": webhook_id, "enabled": body.enabled},
            source="diagnostic_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass

    # Return the updated state for optimistic UI.
    for sub in list_subscriptions():
        if sub["webhook_id"] == webhook_id:
            return sub
    raise HTTPException(500, "Subscription disappeared after update")


@router.post(
    "/diagnostic-alerts/test",
    operation_id="maintenance.diagnostic_alerts.test",
    response_model=DiagnosticAlertTestResponse,
    summary="Fire a synthetic test alert to every subscribed webhook (B274)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def test_diagnostic_alert(
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Send a fake critical finding to every webhook with an active
    subscription. Useful for one-click verification after configuring
    a new webhook."""
    actor_user_id = getattr(request.state, "user_id", None)
    result = fire_test_alert(
        by_user=str(actor_user_id) if actor_user_id else None,
    )
    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"diagnostic alert test fired ({result['delivered']}/{result['subscribed_webhooks']} delivered)",
            result,
            source="diagnostic_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass
    return result


# ── B284 (v0.9.11.23): per-job-run failure alert subscriptions ──────


@router.get(
    "/job-alerts",
    operation_id="maintenance.job_alerts.list",
    response_model=JobAlertSubscriptionListResponse,
    response_model_exclude_none=True,
    summary="List per-job-run failure alert subscriptions (B284)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def list_job_alert_subscriptions(
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Every subscription joined with the referenced webhook's display
    info (name, url, is_active). webhook_name/url null when the
    webhooks plugin is uninstalled (orphan subscriptions render with
    a "webhook missing" indicator in the UI)."""
    return {"subscriptions": _job_alerts.list_subscriptions()}


@router.get(
    "/job-alerts/webhooks",
    operation_id="maintenance.job_alerts.list_available_webhooks",
    response_model=AvailableWebhooksResponse,
    response_model_exclude_none=True,
    summary="List outbound webhooks available for job-alert subscriptions (B284)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
    },
)
def list_job_alert_available_webhooks(
    _: None = Depends(requires("system.audit")),
) -> dict:
    """Picker source for the create-subscription form: every outbound
    webhook in webhook_endpoints with its UUID. Empty list when the
    webhooks plugin isn't installed."""
    return {"webhooks": _job_alerts.list_available_webhooks()}


@router.post(
    "/job-alerts",
    operation_id="maintenance.job_alerts.create",
    response_model=JobAlertSubscription,
    response_model_exclude_none=True,
    summary="Create a per-job-run failure alert subscription (B284)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid plugin_id, on_status, or webhook_id."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Webhook id not registered."},
        409: {"model": ErrorDetail, "description": "Subscription already exists for (plugin_id, webhook_id)."},
    },
)
def create_job_alert_subscription(
    body: CreateJobAlertSubscriptionBody,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    actor_user_id = getattr(request.state, "user_id", None)
    try:
        new_id = _job_alerts.create_subscription(
            body.plugin_id,
            body.on_status,
            body.webhook_id,
            by_user=str(actor_user_id) if actor_user_id else None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"job alert subscription created: plugin={body.plugin_id} webhook={body.webhook_id}",
            {
                "subscription_id": new_id,
                "plugin_id": body.plugin_id,
                "on_status": body.on_status,
                "webhook_id": body.webhook_id,
            },
            source="job_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass

    for s in _job_alerts.list_subscriptions():
        if s["id"] == new_id:
            return s
    raise HTTPException(500, "Subscription disappeared after create")


@router.put(
    "/job-alerts/{sub_id}",
    operation_id="maintenance.job_alerts.update",
    response_model=JobAlertSubscription,
    response_model_exclude_none=True,
    summary="Update a job-alert subscription (toggle enabled / change on_status) (B284)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid on_status."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Subscription not found."},
    },
)
def update_job_alert_subscription(
    sub_id: str,
    body: UpdateJobAlertSubscriptionBody,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    actor_user_id = getattr(request.state, "user_id", None)
    try:
        updated = _job_alerts.update_subscription(
            sub_id,
            on_status=body.on_status,
            enabled=body.enabled,
            by_user=str(actor_user_id) if actor_user_id else None,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))

    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"job alert subscription updated: id={sub_id}",
            {
                "subscription_id": sub_id,
                "on_status": body.on_status,
                "enabled": body.enabled,
            },
            source="job_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass
    return updated


@router.delete(
    "/job-alerts/{sub_id}",
    operation_id="maintenance.job_alerts.delete",
    summary="Delete a job-alert subscription (B284)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Subscription not found."},
    },
)
def delete_job_alert_subscription(
    sub_id: str,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    actor_user_id = getattr(request.state, "user_id", None)
    try:
        _job_alerts.delete_subscription(
            sub_id,
            by_user=str(actor_user_id) if actor_user_id else None,
        )
    except KeyError as e:
        raise HTTPException(404, str(e))
    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"job alert subscription deleted: id={sub_id}",
            {"subscription_id": sub_id},
            source="job_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass
    return {"deleted": True, "id": sub_id}


@router.post(
    "/job-alerts/{sub_id}/test",
    operation_id="maintenance.job_alerts.test",
    response_model=JobAlertTestResponse,
    summary="Fire a synthetic test alert to a subscription's webhook (B284)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.audit permission."},
        404: {"model": ErrorDetail, "description": "Subscription not found."},
    },
)
def test_job_alert_subscription(
    sub_id: str,
    request: Request,
    _: None = Depends(requires("system.audit")),
) -> dict:
    actor_user_id = getattr(request.state, "user_id", None)
    try:
        result = _job_alerts.fire_test_alert_for_subscription(
            sub_id,
            by_user=str(actor_user_id) if actor_user_id else None,
        )
    except KeyError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    try:
        from ..log_events import log_job_event
        log_job_event(
            "info",
            f"job alert test fired: subscription={sub_id} delivered={result.get('delivered')}",
            {"subscription_id": sub_id, **result},
            source="job_alerts",
            actor_user_id=str(actor_user_id) if actor_user_id else None,
        )
    except Exception:
        pass
    return result
