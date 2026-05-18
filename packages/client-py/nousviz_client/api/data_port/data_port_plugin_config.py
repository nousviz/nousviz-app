from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.dataport_plugin_config_response import DataportPluginConfigResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    plugin_slug: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/data-port/plugins/{plugin_slug}".format(
            plugin_slug=quote(str(plugin_slug), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DataportPluginConfigResponse.from_dict(response.json())

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
) -> Response[DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_slug: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Full dataport.yaml config for a plugin (verbatim)

     Return the full dataport.yaml config for a plugin.

    Schema is plugin-author-defined; we return it verbatim and let
    the frontend render whatever the plugin declared.

    Args:
        plugin_slug (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_slug=plugin_slug,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_slug: str,
    *,
    client: AuthenticatedClient | Client,
) -> DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Full dataport.yaml config for a plugin (verbatim)

     Return the full dataport.yaml config for a plugin.

    Schema is plugin-author-defined; we return it verbatim and let
    the frontend render whatever the plugin declared.

    Args:
        plugin_slug (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        plugin_slug=plugin_slug,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_slug: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Full dataport.yaml config for a plugin (verbatim)

     Return the full dataport.yaml config for a plugin.

    Schema is plugin-author-defined; we return it verbatim and let
    the frontend render whatever the plugin declared.

    Args:
        plugin_slug (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_slug=plugin_slug,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_slug: str,
    *,
    client: AuthenticatedClient | Client,
) -> DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Full dataport.yaml config for a plugin (verbatim)

     Return the full dataport.yaml config for a plugin.

    Schema is plugin-author-defined; we return it verbatim and let
    the frontend render whatever the plugin declared.

    Args:
        plugin_slug (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DataportPluginConfigResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_slug=plugin_slug,
            client=client,
        )
    ).parsed
