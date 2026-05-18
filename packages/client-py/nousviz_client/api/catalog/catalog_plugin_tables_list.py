from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.catalog_plugin_tables_response import CatalogPluginTablesResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    plugin_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/plugins/{plugin_id}/tables".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = CatalogPluginTablesResponse.from_dict(response.json())

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
) -> Response[CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
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
) -> Response[CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    r"""Discovered tables for one plugin (with manifest drift)

     All discovered tables for a single plugin.

    Returns empty `tables` list (not 404) if the plugin has no
    discovered tables, so the frontend can render an empty state
    cleanly without distinguishing \"plugin not installed\" from
    \"plugin owns nothing.\"

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
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
) -> CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    r"""Discovered tables for one plugin (with manifest drift)

     All discovered tables for a single plugin.

    Returns empty `tables` list (not 404) if the plugin has no
    discovered tables, so the frontend can render an empty state
    cleanly without distinguishing \"plugin not installed\" from
    \"plugin owns nothing.\"

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    r"""Discovered tables for one plugin (with manifest drift)

     All discovered tables for a single plugin.

    Returns empty `tables` list (not 404) if the plugin has no
    discovered tables, so the frontend can render an empty state
    cleanly without distinguishing \"plugin not installed\" from
    \"plugin owns nothing.\"

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
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
) -> CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    r"""Discovered tables for one plugin (with manifest drift)

     All discovered tables for a single plugin.

    Returns empty `tables` list (not 404) if the plugin has no
    discovered tables, so the frontend can render an empty state
    cleanly without distinguishing \"plugin not installed\" from
    \"plugin owns nothing.\"

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogPluginTablesResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
        )
    ).parsed
