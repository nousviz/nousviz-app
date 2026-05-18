from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.users_with_permissions_response import UsersWithPermissionsResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/system/users-with-permissions",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse | None:
    if response.status_code == 200:
        response_200 = UsersWithPermissionsResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse]:
    """Per-user permission audit data (Users tab on the matrix page)

     B231 (v0.9.8.4) — per-user permission audit data.

    Backs the Users tab on the matrix page. For each user, returns:
      - identity (id, email, name, role, is_active)
      - their resolved permission set (from role -> permissions catalog)
      - their most-recent allow decision in auth_audit (last 30d)

    The resolved permission set comes from the static catalog because
    v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
    top — this endpoint will return the post-override resolved set so
    the frontend contract doesn't change.

    Sorted by email for stable rendering. An empty list is valid —
    e.g. a fresh install before the wizard creates the first superadmin.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse | None:
    """Per-user permission audit data (Users tab on the matrix page)

     B231 (v0.9.8.4) — per-user permission audit data.

    Backs the Users tab on the matrix page. For each user, returns:
      - identity (id, email, name, role, is_active)
      - their resolved permission set (from role -> permissions catalog)
      - their most-recent allow decision in auth_audit (last 30d)

    The resolved permission set comes from the static catalog because
    v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
    top — this endpoint will return the post-override resolved set so
    the frontend contract doesn't change.

    Sorted by email for stable rendering. An empty list is valid —
    e.g. a fresh install before the wizard creates the first superadmin.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse]:
    """Per-user permission audit data (Users tab on the matrix page)

     B231 (v0.9.8.4) — per-user permission audit data.

    Backs the Users tab on the matrix page. For each user, returns:
      - identity (id, email, name, role, is_active)
      - their resolved permission set (from role -> permissions catalog)
      - their most-recent allow decision in auth_audit (last 30d)

    The resolved permission set comes from the static catalog because
    v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
    top — this endpoint will return the post-override resolved set so
    the frontend contract doesn't change.

    Sorted by email for stable rendering. An empty list is valid —
    e.g. a fresh install before the wizard creates the first superadmin.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse | None:
    """Per-user permission audit data (Users tab on the matrix page)

     B231 (v0.9.8.4) — per-user permission audit data.

    Backs the Users tab on the matrix page. For each user, returns:
      - identity (id, email, name, role, is_active)
      - their resolved permission set (from role -> permissions catalog)
      - their most-recent allow decision in auth_audit (last 30d)

    The resolved permission set comes from the static catalog because
    v0.9.8.x has no DB overrides yet. v0.9.9.x will layer overrides on
    top — this endpoint will return the post-override resolved set so
    the frontend contract doesn't change.

    Sorted by email for stable rendering. An empty list is valid —
    e.g. a fresh install before the wizard creates the first superadmin.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | UsersWithPermissionsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
