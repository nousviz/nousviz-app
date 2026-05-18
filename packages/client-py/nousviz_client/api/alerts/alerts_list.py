from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.alerts_list_response import AlertsListResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    plugin_id: None | str | Unset = UNSET,
    enabled_only: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    params["enabled_only"] = enabled_only

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/alerts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AlertsListResponse.from_dict(response.json())

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
) -> Response[AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
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
    enabled_only: bool | Unset = False,
) -> Response[AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List alert configs (newest-first, optional plugin/enabled filter)

     List all alerts, with human-readable frequency and period labels.

    Args:
        plugin_id (None | str | Unset):
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        enabled_only=enabled_only,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    enabled_only: bool | Unset = False,
) -> AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List alert configs (newest-first, optional plugin/enabled filter)

     List all alerts, with human-readable frequency and period labels.

    Args:
        plugin_id (None | str | Unset):
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        plugin_id=plugin_id,
        enabled_only=enabled_only,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    enabled_only: bool | Unset = False,
) -> Response[AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List alert configs (newest-first, optional plugin/enabled filter)

     List all alerts, with human-readable frequency and period labels.

    Args:
        plugin_id (None | str | Unset):
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        enabled_only=enabled_only,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    enabled_only: bool | Unset = False,
) -> AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List alert configs (newest-first, optional plugin/enabled filter)

     List all alerts, with human-readable frequency and period labels.

    Args:
        plugin_id (None | str | Unset):
        enabled_only (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AlertsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            plugin_id=plugin_id,
            enabled_only=enabled_only,
        )
    ).parsed
