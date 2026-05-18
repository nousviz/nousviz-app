from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.restricted_users_list_response import RestrictedUsersListResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    exclude_slug: str | Unset = "",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["exclude_slug"] = exclude_slug

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/users/with-restricted-plugin-access",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse | None:
    if response.status_code == 200:
        response_200 = RestrictedUsersListResponse.from_dict(response.json())

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

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    exclude_slug: str | Unset = "",
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse]:
    r"""Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)

     Used by the install-success grant banner on the frontend. Returns
    users with `mode='specific'` whose allowlist does NOT include
    `exclude_slug` — i.e. the operator-visible \"people who can't see
    this new plugin yet\" set.

    Args:
        exclude_slug (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse]
    """

    kwargs = _get_kwargs(
        exclude_slug=exclude_slug,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    exclude_slug: str | Unset = "",
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse | None:
    r"""Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)

     Used by the install-success grant banner on the frontend. Returns
    users with `mode='specific'` whose allowlist does NOT include
    `exclude_slug` — i.e. the operator-visible \"people who can't see
    this new plugin yet\" set.

    Args:
        exclude_slug (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse
    """

    return sync_detailed(
        client=client,
        exclude_slug=exclude_slug,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    exclude_slug: str | Unset = "",
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse]:
    r"""Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)

     Used by the install-success grant banner on the frontend. Returns
    users with `mode='specific'` whose allowlist does NOT include
    `exclude_slug` — i.e. the operator-visible \"people who can't see
    this new plugin yet\" set.

    Args:
        exclude_slug (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse]
    """

    kwargs = _get_kwargs(
        exclude_slug=exclude_slug,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    exclude_slug: str | Unset = "",
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse | None:
    r"""Users with a specific-plugins allowlist that doesn't yet include a given slug (admin)

     Used by the install-success grant banner on the frontend. Returns
    users with `mode='specific'` whose allowlist does NOT include
    `exclude_slug` — i.e. the operator-visible \"people who can't see
    this new plugin yet\" set.

    Args:
        exclude_slug (str | Unset):  Default: ''.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RestrictedUsersListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            exclude_slug=exclude_slug,
        )
    ).parsed
