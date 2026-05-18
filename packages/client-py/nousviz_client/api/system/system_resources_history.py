from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.resources_history_response import ResourcesHistoryResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    metric: str,
    plugin: None | str | Unset = UNSET,
    days: int | Unset = 30,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["metric"] = metric

    json_plugin: None | str | Unset
    if isinstance(plugin, Unset):
        json_plugin = UNSET
    else:
        json_plugin = plugin
    params["plugin"] = json_plugin

    params["days"] = days

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/system/resources/history",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse | None:
    if response.status_code == 200:
        response_200 = ResourcesHistoryResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorDetail.from_dict(response.json())

        return response_400

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    metric: str,
    plugin: None | str | Unset = UNSET,
    days: int | Unset = 30,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse]:
    """Time-series for one resource metric over the snapshot window (B273)

     Return [{snapshot_at, value}] over the last N days for one
    metric. Snapshots come from the daily worker
    `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).

    Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
    `plugin_size` requires the `plugin` parameter.

    Args:
        metric (str):
        plugin (None | str | Unset):
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse]
    """

    kwargs = _get_kwargs(
        metric=metric,
        plugin=plugin,
        days=days,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    metric: str,
    plugin: None | str | Unset = UNSET,
    days: int | Unset = 30,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse | None:
    """Time-series for one resource metric over the snapshot window (B273)

     Return [{snapshot_at, value}] over the last N days for one
    metric. Snapshots come from the daily worker
    `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).

    Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
    `plugin_size` requires the `plugin` parameter.

    Args:
        metric (str):
        plugin (None | str | Unset):
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse
    """

    return sync_detailed(
        client=client,
        metric=metric,
        plugin=plugin,
        days=days,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    metric: str,
    plugin: None | str | Unset = UNSET,
    days: int | Unset = 30,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse]:
    """Time-series for one resource metric over the snapshot window (B273)

     Return [{snapshot_at, value}] over the last N days for one
    metric. Snapshots come from the daily worker
    `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).

    Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
    `plugin_size` requires the `plugin` parameter.

    Args:
        metric (str):
        plugin (None | str | Unset):
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse]
    """

    kwargs = _get_kwargs(
        metric=metric,
        plugin=plugin,
        days=days,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    metric: str,
    plugin: None | str | Unset = UNSET,
    days: int | Unset = 30,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse | None:
    """Time-series for one resource metric over the snapshot window (B273)

     Return [{snapshot_at, value}] over the last N days for one
    metric. Snapshots come from the daily worker
    `apps/worker/src/snapshot_resources.py` (PM2 cron 03:30 UTC).

    Initial supported metrics: `db_size`, `cache_hit_pct`, `plugin_size`.
    `plugin_size` requires the `plugin` parameter.

    Args:
        metric (str):
        plugin (None | str | Unset):
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | ResourcesHistoryResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            metric=metric,
            plugin=plugin,
            days=days,
        )
    ).parsed
