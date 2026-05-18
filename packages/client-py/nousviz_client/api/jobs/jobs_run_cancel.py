from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.job_run_control_response import JobRunControlResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    run_id: int,
    *,
    force: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["force"] = force

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/jobs/{run_id}/cancel".format(
            run_id=quote(str(run_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = JobRunControlResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 409:
        response_409 = ErrorDetail.from_dict(response.json())

        return response_409

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    run_id: int,
    *,
    client: AuthenticatedClient | Client,
    force: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail]:
    """Cancel a queued or running job run

     Cancel a queued or running run. Cooperative — the plugin sees the
    cancel via check_cancelled() on its next poll.

    - queued  → status='cancelled' (never ran)
    - running → status='cancelling' (plugin exits on next check_cancelled)
    - paused  → status='cancelled'
    - terminal (success/error/timeout/cancelled/skipped) → 200 no-op

    `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
    `cancelled` regardless of current status (skipping the cooperative
    `cancelling` state). Used for **orphaned runs** where the worker is
    confirmed gone — e.g. after a Postgres restart or scheduler crash
    that left rows in `'running'` without any process actively executing
    them. Without `?force=true`, those rows would hang in `cancelling`
    forever (no worker to observe the cancel).

    **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
    is passed against a `'running'` row whose `heartbeat_at` is fresh
    (worker heartbeated within the last 90 seconds), the request is
    refused with 409. The worker is alive — cooperative cancel will
    work, and force-cancel would create a status mismatch where the
    worker still thinks it's running. The dashboard frontend uses
    `JobsDashboardNowItem.worker_alive` to pick the right button
    automatically; this server-side check is the safety net.

    Args:
        run_id (int):
        force (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
        force=force,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    run_id: int,
    *,
    client: AuthenticatedClient | Client,
    force: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail | None:
    """Cancel a queued or running job run

     Cancel a queued or running run. Cooperative — the plugin sees the
    cancel via check_cancelled() on its next poll.

    - queued  → status='cancelled' (never ran)
    - running → status='cancelling' (plugin exits on next check_cancelled)
    - paused  → status='cancelled'
    - terminal (success/error/timeout/cancelled/skipped) → 200 no-op

    `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
    `cancelled` regardless of current status (skipping the cooperative
    `cancelling` state). Used for **orphaned runs** where the worker is
    confirmed gone — e.g. after a Postgres restart or scheduler crash
    that left rows in `'running'` without any process actively executing
    them. Without `?force=true`, those rows would hang in `cancelling`
    forever (no worker to observe the cancel).

    **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
    is passed against a `'running'` row whose `heartbeat_at` is fresh
    (worker heartbeated within the last 90 seconds), the request is
    refused with 409. The worker is alive — cooperative cancel will
    work, and force-cancel would create a status mismatch where the
    worker still thinks it's running. The dashboard frontend uses
    `JobsDashboardNowItem.worker_alive` to pick the right button
    automatically; this server-side check is the safety net.

    Args:
        run_id (int):
        force (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail
    """

    return sync_detailed(
        run_id=run_id,
        client=client,
        force=force,
    ).parsed


async def asyncio_detailed(
    run_id: int,
    *,
    client: AuthenticatedClient | Client,
    force: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail]:
    """Cancel a queued or running job run

     Cancel a queued or running run. Cooperative — the plugin sees the
    cancel via check_cancelled() on its next poll.

    - queued  → status='cancelled' (never ran)
    - running → status='cancelling' (plugin exits on next check_cancelled)
    - paused  → status='cancelled'
    - terminal (success/error/timeout/cancelled/skipped) → 200 no-op

    `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
    `cancelled` regardless of current status (skipping the cooperative
    `cancelling` state). Used for **orphaned runs** where the worker is
    confirmed gone — e.g. after a Postgres restart or scheduler crash
    that left rows in `'running'` without any process actively executing
    them. Without `?force=true`, those rows would hang in `cancelling`
    forever (no worker to observe the cancel).

    **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
    is passed against a `'running'` row whose `heartbeat_at` is fresh
    (worker heartbeated within the last 90 seconds), the request is
    refused with 409. The worker is alive — cooperative cancel will
    work, and force-cancel would create a status mismatch where the
    worker still thinks it's running. The dashboard frontend uses
    `JobsDashboardNowItem.worker_alive` to pick the right button
    automatically; this server-side check is the safety net.

    Args:
        run_id (int):
        force (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        run_id=run_id,
        force=force,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    run_id: int,
    *,
    client: AuthenticatedClient | Client,
    force: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail | None:
    """Cancel a queued or running job run

     Cancel a queued or running run. Cooperative — the plugin sees the
    cancel via check_cancelled() on its next poll.

    - queued  → status='cancelled' (never ran)
    - running → status='cancelling' (plugin exits on next check_cancelled)
    - paused  → status='cancelled'
    - terminal (success/error/timeout/cancelled/skipped) → 200 no-op

    `?force=true` (B277 v0.9.11.16.3+): force-marks the run terminal as
    `cancelled` regardless of current status (skipping the cooperative
    `cancelling` state). Used for **orphaned runs** where the worker is
    confirmed gone — e.g. after a Postgres restart or scheduler crash
    that left rows in `'running'` without any process actively executing
    them. Without `?force=true`, those rows would hang in `cancelling`
    forever (no worker to observe the cancel).

    **Server-gated liveness check (v0.9.11.16.4)**: when `?force=true`
    is passed against a `'running'` row whose `heartbeat_at` is fresh
    (worker heartbeated within the last 90 seconds), the request is
    refused with 409. The worker is alive — cooperative cancel will
    work, and force-cancel would create a status mismatch where the
    worker still thinks it's running. The dashboard frontend uses
    `JobsDashboardNowItem.worker_alive` to pick the right button
    automatically; this server-side check is the safety net.

    Args:
        run_id (int):
        force (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobRunControlResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            run_id=run_id,
            client=client,
            force=force,
        )
    ).parsed
