from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.plugin_audit_log_response import PluginAuditLogResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    plugin_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/plugins/audit-log",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginAuditLogResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail]:
    """Recent plugin lifecycle events (install/uninstall/update/etc.)

     View plugin audit log entries.

    Args:
        plugin_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail | None:
    """Recent plugin lifecycle events (install/uninstall/update/etc.)

     View plugin audit log entries.

    Args:
        plugin_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        plugin_id=plugin_id,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail]:
    """Recent plugin lifecycle events (install/uninstall/update/etc.)

     View plugin audit log entries.

    Args:
        plugin_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail | None:
    """Recent plugin lifecycle events (install/uninstall/update/etc.)

     View plugin audit log entries.

    Args:
        plugin_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginAuditLogResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            plugin_id=plugin_id,
            limit=limit,
        )
    ).parsed
