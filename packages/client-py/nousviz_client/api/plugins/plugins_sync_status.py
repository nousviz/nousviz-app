from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.sync_status_response import SyncStatusResponse
from ...types import Response


def _get_kwargs(
    plugin_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/plugins/{plugin_id}/sync/status".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse | None:
    if response.status_code == 200:
        response_200 = SyncStatusResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse]:
    """Sync status snapshot for the unified Sync card (B205)

     Sync status snapshot for the unified Sync card (B205, v0.9.6).

    Returns:
        current: most recent run with status IN ('queued','running','cancelling'),
            including live progress JSONB and elapsed seconds. None when idle.
        last_success: most recent successful run.
        last_failure: most recent failed run (error/timeout/cancelled).
        last_sync: ISO timestamp of last_success.completed_at — kept for
            backward compatibility with pre-v0.9.6 frontend code.

    The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
    job_runs is the single source of truth.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse | None:
    """Sync status snapshot for the unified Sync card (B205)

     Sync status snapshot for the unified Sync card (B205, v0.9.6).

    Returns:
        current: most recent run with status IN ('queued','running','cancelling'),
            including live progress JSONB and elapsed seconds. None when idle.
        last_success: most recent successful run.
        last_failure: most recent failed run (error/timeout/cancelled).
        last_sync: ISO timestamp of last_success.completed_at — kept for
            backward compatibility with pre-v0.9.6 frontend code.

    The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
    job_runs is the single source of truth.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse]:
    """Sync status snapshot for the unified Sync card (B205)

     Sync status snapshot for the unified Sync card (B205, v0.9.6).

    Returns:
        current: most recent run with status IN ('queued','running','cancelling'),
            including live progress JSONB and elapsed seconds. None when idle.
        last_success: most recent successful run.
        last_failure: most recent failed run (error/timeout/cancelled).
        last_sync: ISO timestamp of last_success.completed_at — kept for
            backward compatibility with pre-v0.9.6 frontend code.

    The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
    job_runs is the single source of truth.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse | None:
    """Sync status snapshot for the unified Sync card (B205)

     Sync status snapshot for the unified Sync card (B205, v0.9.6).

    Returns:
        current: most recent run with status IN ('queued','running','cancelling'),
            including live progress JSONB and elapsed seconds. None when idle.
        last_success: most recent successful run.
        last_failure: most recent failed run (error/timeout/cancelled).
        last_sync: ISO timestamp of last_success.completed_at — kept for
            backward compatibility with pre-v0.9.6 frontend code.

    The legacy plugin_settings._last_sync fallback is removed in v0.9.6 —
    job_runs is the single source of truth.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncStatusResponse
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
        )
    ).parsed
