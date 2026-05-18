from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.role_permissions_response import RolePermissionsResponse
from ...types import Response


def _get_kwargs(
    role: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/role-permissions/{role}".format(
            role=quote(str(role), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse | None:
    if response.status_code == 200:
        response_200 = RolePermissionsResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse]:
    r"""Permissions held by an arbitrary role (admin preview UI)

     B231 (v0.9.8.4): return the permissions held by an arbitrary role.

    Powers the admin-only \"preview as <role>\" UI — admins toggle the
    sidebar to render as if they had a different role, and the frontend
    needs the permission set for that role to compute hasPermission().

    Frontend-only feature: the backend still authorizes the request
    based on the admin's REAL session. This endpoint is gated by
    system.audit so a non-admin can't fish for role permissions.

    Returns 404 if the role is unknown (typo, future custom role).

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse]
    """

    kwargs = _get_kwargs(
        role=role,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse | None:
    r"""Permissions held by an arbitrary role (admin preview UI)

     B231 (v0.9.8.4): return the permissions held by an arbitrary role.

    Powers the admin-only \"preview as <role>\" UI — admins toggle the
    sidebar to render as if they had a different role, and the frontend
    needs the permission set for that role to compute hasPermission().

    Frontend-only feature: the backend still authorizes the request
    based on the admin's REAL session. This endpoint is gated by
    system.audit so a non-admin can't fish for role permissions.

    Returns 404 if the role is unknown (typo, future custom role).

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse
    """

    return sync_detailed(
        role=role,
        client=client,
    ).parsed


async def asyncio_detailed(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse]:
    r"""Permissions held by an arbitrary role (admin preview UI)

     B231 (v0.9.8.4): return the permissions held by an arbitrary role.

    Powers the admin-only \"preview as <role>\" UI — admins toggle the
    sidebar to render as if they had a different role, and the frontend
    needs the permission set for that role to compute hasPermission().

    Frontend-only feature: the backend still authorizes the request
    based on the admin's REAL session. This endpoint is gated by
    system.audit so a non-admin can't fish for role permissions.

    Returns 404 if the role is unknown (typo, future custom role).

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse]
    """

    kwargs = _get_kwargs(
        role=role,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse | None:
    r"""Permissions held by an arbitrary role (admin preview UI)

     B231 (v0.9.8.4): return the permissions held by an arbitrary role.

    Powers the admin-only \"preview as <role>\" UI — admins toggle the
    sidebar to render as if they had a different role, and the frontend
    needs the permission set for that role to compute hasPermission().

    Frontend-only feature: the backend still authorizes the request
    based on the admin's REAL session. This endpoint is gated by
    system.audit so a non-admin can't fish for role permissions.

    Returns 404 if the role is unknown (typo, future custom role).

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RolePermissionsResponse
    """

    return (
        await asyncio_detailed(
            role=role,
            client=client,
        )
    ).parsed
