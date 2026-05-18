from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.my_permissions_response import MyPermissionsResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/me/permissions",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | MyPermissionsResponse | None:
    if response.status_code == 200:
        response_200 = MyPermissionsResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | MyPermissionsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MyPermissionsResponse]:
    """Resolved permissions for the current effective user

     B230 (v0.9.8.3): return the set of permissions the current user
    holds. The frontend uses this for role-aware UI (sidebar nav,
    conditional buttons) without needing to duplicate the role-permission
    catalog from rbac/permissions.py.

    Resolves the user, looks up their role's permission set, and returns
    a flat list. v0.9.9.x will layer DB overrides on top — this same
    endpoint will return the resolved post-override set, so the frontend
    contract doesn't change.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MyPermissionsResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MyPermissionsResponse | None:
    """Resolved permissions for the current effective user

     B230 (v0.9.8.3): return the set of permissions the current user
    holds. The frontend uses this for role-aware UI (sidebar nav,
    conditional buttons) without needing to duplicate the role-permission
    catalog from rbac/permissions.py.

    Resolves the user, looks up their role's permission set, and returns
    a flat list. v0.9.9.x will layer DB overrides on top — this same
    endpoint will return the resolved post-override set, so the frontend
    contract doesn't change.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MyPermissionsResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MyPermissionsResponse]:
    """Resolved permissions for the current effective user

     B230 (v0.9.8.3): return the set of permissions the current user
    holds. The frontend uses this for role-aware UI (sidebar nav,
    conditional buttons) without needing to duplicate the role-permission
    catalog from rbac/permissions.py.

    Resolves the user, looks up their role's permission set, and returns
    a flat list. v0.9.9.x will layer DB overrides on top — this same
    endpoint will return the resolved post-override set, so the frontend
    contract doesn't change.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MyPermissionsResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MyPermissionsResponse | None:
    """Resolved permissions for the current effective user

     B230 (v0.9.8.3): return the set of permissions the current user
    holds. The frontend uses this for role-aware UI (sidebar nav,
    conditional buttons) without needing to duplicate the role-permission
    catalog from rbac/permissions.py.

    Resolves the user, looks up their role's permission set, and returns
    a flat list. v0.9.9.x will layer DB overrides on top — this same
    endpoint will return the resolved post-override set, so the frontend
    contract doesn't change.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MyPermissionsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
