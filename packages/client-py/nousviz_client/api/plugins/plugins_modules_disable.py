from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.plugin_module_toggle_response import PluginModuleToggleResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    plugin_id: str,
    module_name: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/plugins/{plugin_id}/modules/{module_name}/disable".format(
            plugin_id=quote(str(plugin_id), safe=""),
            module_name=quote(str(module_name), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginModuleToggleResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    module_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail]:
    """Disable a plugin module (data preserved)

     Disable a plugin module. Data is preserved.

    Args:
        plugin_id (str):
        module_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        module_name=module_name,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    module_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail | None:
    """Disable a plugin module (data preserved)

     Disable a plugin module. Data is preserved.

    Args:
        plugin_id (str):
        module_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        module_name=module_name,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    module_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail]:
    """Disable a plugin module (data preserved)

     Disable a plugin module. Data is preserved.

    Args:
        plugin_id (str):
        module_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        module_name=module_name,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    module_name: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail | None:
    """Disable a plugin module (data preserved)

     Disable a plugin module. Data is preserved.

    Args:
        plugin_id (str):
        module_name (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginModuleToggleResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            module_name=module_name,
            client=client,
        )
    ).parsed
