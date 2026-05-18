from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.plugin_list_response import PluginListResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/plugins",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | PluginListResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginListResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | PluginListResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PluginListResponse | RBACErrorDetail]:
    """List installed plugins

     List only active (installed) plugins — used by the Installed Plugins page and sidebar.

    B144 (v0.9.2.4): each entry carries an `update_status` block from the
    plugin_update_status cache. Stale entries (older than ~1h) trigger a
    fire-and-forget refresh in the background so the next call sees fresh
    data. The current call doesn't block on the network check.

    Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
    lookups that `_enrich_datasets` used to fire per-plugin are now
    pre-fetched in two batched calls before the loop. Drops `/api/plugins`
    DB round trips from ~6N to ~3 for the enrichment block alone.

    B305 (v0.10.0.6): the result list is filtered through
    `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
    allowlist (resource_acls rows for resource_type='plugin') sees only
    their permitted set + utilities. Admins/superadmins bypass.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PluginListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PluginListResponse | RBACErrorDetail | None:
    """List installed plugins

     List only active (installed) plugins — used by the Installed Plugins page and sidebar.

    B144 (v0.9.2.4): each entry carries an `update_status` block from the
    plugin_update_status cache. Stale entries (older than ~1h) trigger a
    fire-and-forget refresh in the background so the next call sees fresh
    data. The current call doesn't block on the network check.

    Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
    lookups that `_enrich_datasets` used to fire per-plugin are now
    pre-fetched in two batched calls before the loop. Drops `/api/plugins`
    DB round trips from ~6N to ~3 for the enrichment block alone.

    B305 (v0.10.0.6): the result list is filtered through
    `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
    allowlist (resource_acls rows for resource_type='plugin') sees only
    their permitted set + utilities. Admins/superadmins bypass.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PluginListResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PluginListResponse | RBACErrorDetail]:
    """List installed plugins

     List only active (installed) plugins — used by the Installed Plugins page and sidebar.

    B144 (v0.9.2.4): each entry carries an `update_status` block from the
    plugin_update_status cache. Stale entries (older than ~1h) trigger a
    fire-and-forget refresh in the background so the next call sees fresh
    data. The current call doesn't block on the network check.

    Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
    lookups that `_enrich_datasets` used to fire per-plugin are now
    pre-fetched in two batched calls before the loop. Drops `/api/plugins`
    DB round trips from ~6N to ~3 for the enrichment block alone.

    B305 (v0.10.0.6): the result list is filtered through
    `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
    allowlist (resource_acls rows for resource_type='plugin') sees only
    their permitted set + utilities. Admins/superadmins bypass.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PluginListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PluginListResponse | RBACErrorDetail | None:
    """List installed plugins

     List only active (installed) plugins — used by the Installed Plugins page and sidebar.

    B144 (v0.9.2.4): each entry carries an `update_status` block from the
    plugin_update_status cache. Stale entries (older than ~1h) trigger a
    fire-and-forget refresh in the background so the next call sees fresh
    data. The current call doesn't block on the network check.

    Keystone B (Phase 12 perf, v0.10.0.5.6): the catalog + last-sync
    lookups that `_enrich_datasets` used to fire per-plugin are now
    pre-fetched in two batched calls before the loop. Drops `/api/plugins`
    DB round trips from ~6N to ~3 for the enrichment block alone.

    B305 (v0.10.0.6): the result list is filtered through
    `rbac.filter_plugins_for_user` so a viewer/analyst with a per-user
    allowlist (resource_acls rows for resource_type='plugin') sees only
    their permitted set + utilities. Admins/superadmins bypass.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PluginListResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
