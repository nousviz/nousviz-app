from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.connection_health_response import ConnectionHealthResponse
from ...models.error_detail import ErrorDetail
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/health/connections",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ConnectionHealthResponse | ErrorDetail | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = ConnectionHealthResponse.from_dict(response.json())

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
) -> Response[ConnectionHealthResponse | ErrorDetail | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ConnectionHealthResponse | ErrorDetail | RBACErrorDetail]:
    """Plugin connection health issues

     Banner-shaped list of plugin connection-health issues.

    Each entry carries a plugin id, severity, message, and optional
    structured detail — the UI renders each as a banner on the home
    dashboard. An empty list means all installed plugins report healthy
    connections.

    Plugins will register their own health checks via `plugin_registry`
    in a future release; the current implementation always returns no
    issues.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionHealthResponse | ErrorDetail | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ConnectionHealthResponse | ErrorDetail | RBACErrorDetail | None:
    """Plugin connection health issues

     Banner-shaped list of plugin connection-health issues.

    Each entry carries a plugin id, severity, message, and optional
    structured detail — the UI renders each as a banner on the home
    dashboard. An empty list means all installed plugins report healthy
    connections.

    Plugins will register their own health checks via `plugin_registry`
    in a future release; the current implementation always returns no
    issues.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionHealthResponse | ErrorDetail | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ConnectionHealthResponse | ErrorDetail | RBACErrorDetail]:
    """Plugin connection health issues

     Banner-shaped list of plugin connection-health issues.

    Each entry carries a plugin id, severity, message, and optional
    structured detail — the UI renders each as a banner on the home
    dashboard. An empty list means all installed plugins report healthy
    connections.

    Plugins will register their own health checks via `plugin_registry`
    in a future release; the current implementation always returns no
    issues.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionHealthResponse | ErrorDetail | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ConnectionHealthResponse | ErrorDetail | RBACErrorDetail | None:
    """Plugin connection health issues

     Banner-shaped list of plugin connection-health issues.

    Each entry carries a plugin id, severity, message, and optional
    structured detail — the UI renders each as a banner on the home
    dashboard. An empty list means all installed plugins report healthy
    connections.

    Plugins will register their own health checks via `plugin_registry`
    in a future release; the current implementation always returns no
    issues.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionHealthResponse | ErrorDetail | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
