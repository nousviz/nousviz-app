from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.plugin_catalog_response import PluginCatalogResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/plugins/catalog",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | PluginCatalogResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginCatalogResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | PluginCatalogResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PluginCatalogResponse | RBACErrorDetail]:
    """Full plugin catalog for the Marketplace page

     Full plugin catalog — official + installed + community, with installed flag.
    Used by the Marketplace page.

    Priority: installed/ and community/ win over official/ stubs for the same
    plugin slug — the installed copy has richer metadata and is the live version.
    Official stubs only appear in the catalog when the plugin is not installed.

    P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
    Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PluginCatalogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PluginCatalogResponse | RBACErrorDetail | None:
    """Full plugin catalog for the Marketplace page

     Full plugin catalog — official + installed + community, with installed flag.
    Used by the Marketplace page.

    Priority: installed/ and community/ win over official/ stubs for the same
    plugin slug — the installed copy has richer metadata and is the live version.
    Official stubs only appear in the catalog when the plugin is not installed.

    P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
    Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PluginCatalogResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PluginCatalogResponse | RBACErrorDetail]:
    """Full plugin catalog for the Marketplace page

     Full plugin catalog — official + installed + community, with installed flag.
    Used by the Marketplace page.

    Priority: installed/ and community/ win over official/ stubs for the same
    plugin slug — the installed copy has richer metadata and is the live version.
    Official stubs only appear in the catalog when the plugin is not installed.

    P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
    Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PluginCatalogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PluginCatalogResponse | RBACErrorDetail | None:
    """Full plugin catalog for the Marketplace page

     Full plugin catalog — official + installed + community, with installed flag.
    Used by the Marketplace page.

    Priority: installed/ and community/ win over official/ stubs for the same
    plugin slug — the installed copy has richer metadata and is the live version.
    Official stubs only appear in the catalog when the plugin is not installed.

    P20b: merges install_count, featured, listed, pricing_model from plugin_registry.
    Plugins with listed=false are excluded. Sorted: featured first, then by install_count desc.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PluginCatalogResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
