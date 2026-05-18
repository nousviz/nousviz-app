from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.plugin_update_response import PluginUpdateResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    plugin_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/plugins/{plugin_id}/update".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginUpdateResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail]:
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
) -> Response[ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail]:
    """Atomic-swap update to the latest version (B145)

     Update an installed plugin to the latest version from its source.

    Atomic-swap design (B145): the new code is cloned to a staging directory
    first, validated, then atomically swapped with the live install. If
    anything fails before the swap, the live install is untouched. If the
    post-swap idempotent steps (migrations, grants) fail, the previous live
    install is restored from a sibling backup.

    Credentials, settings, and synced data are preserved across the swap
    (DB tables are not dropped). The plugin briefly becomes unavailable
    while PM2 reloads to pick up the new routes.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail]
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
) -> ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail | None:
    """Atomic-swap update to the latest version (B145)

     Update an installed plugin to the latest version from its source.

    Atomic-swap design (B145): the new code is cloned to a staging directory
    first, validated, then atomically swapped with the live install. If
    anything fails before the swap, the live install is untouched. If the
    post-swap idempotent steps (migrations, grants) fail, the previous live
    install is restored from a sibling backup.

    Credentials, settings, and synced data are preserved across the swap
    (DB tables are not dropped). The plugin briefly becomes unavailable
    while PM2 reloads to pick up the new routes.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail]:
    """Atomic-swap update to the latest version (B145)

     Update an installed plugin to the latest version from its source.

    Atomic-swap design (B145): the new code is cloned to a staging directory
    first, validated, then atomically swapped with the live install. If
    anything fails before the swap, the live install is untouched. If the
    post-swap idempotent steps (migrations, grants) fail, the previous live
    install is restored from a sibling backup.

    Credentials, settings, and synced data are preserved across the swap
    (DB tables are not dropped). The plugin briefly becomes unavailable
    while PM2 reloads to pick up the new routes.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail]
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
) -> ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail | None:
    """Atomic-swap update to the latest version (B145)

     Update an installed plugin to the latest version from its source.

    Atomic-swap design (B145): the new code is cloned to a staging directory
    first, validated, then atomically swapped with the live install. If
    anything fails before the swap, the live install is untouched. If the
    post-swap idempotent steps (migrations, grants) fail, the previous live
    install is restored from a sibling backup.

    Credentials, settings, and synced data are preserved across the swap
    (DB tables are not dropped). The plugin briefly becomes unavailable
    while PM2 reloads to pick up the new routes.

    Args:
        plugin_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginUpdateResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
        )
    ).parsed
