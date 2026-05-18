from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.catalog_table import CatalogTable
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    plugin_id: str,
    table_name: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/plugins/{plugin_id}/tables/{table_name}".format(
            plugin_id=quote(str(plugin_id), safe=""),
            table_name=quote(str(table_name), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = CatalogTable.from_dict(response.json())

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

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Schema + metadata for one (plugin, table) pair

     Schema and metadata for one specific (plugin, table).

    Args:
        plugin_id (str):
        table_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        table_name=table_name,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Schema + metadata for one (plugin, table) pair

     Schema and metadata for one specific (plugin, table).

    Args:
        plugin_id (str):
        table_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        table_name=table_name,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Schema + metadata for one (plugin, table) pair

     Schema and metadata for one specific (plugin, table).

    Args:
        plugin_id (str):
        table_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        table_name=table_name,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Schema + metadata for one (plugin, table) pair

     Schema and metadata for one specific (plugin, table).

    Args:
        plugin_id (str):
        table_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogTable | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            table_name=table_name,
            client=client,
        )
    ).parsed
