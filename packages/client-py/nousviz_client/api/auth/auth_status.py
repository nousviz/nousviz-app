from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.auth_status_response import AuthStatusResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/status",
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> AuthStatusResponse | None:
    if response.status_code == 200:
        response_200 = AuthStatusResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[AuthStatusResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[AuthStatusResponse]:
    """Auth-mode and current-session status

     Return auth-mode flags and (if a session token is present and
    valid) the authenticated user.

    Public endpoint — no auth required. The frontend calls this on
    page load to decide whether to show the login screen, the setup
    wizard (no users exist), or the dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AuthStatusResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> AuthStatusResponse | None:
    """Auth-mode and current-session status

     Return auth-mode flags and (if a session token is present and
    valid) the authenticated user.

    Public endpoint — no auth required. The frontend calls this on
    page load to decide whether to show the login screen, the setup
    wizard (no users exist), or the dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AuthStatusResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[AuthStatusResponse]:
    """Auth-mode and current-session status

     Return auth-mode flags and (if a session token is present and
    valid) the authenticated user.

    Public endpoint — no auth required. The frontend calls this on
    page load to decide whether to show the login screen, the setup
    wizard (no users exist), or the dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AuthStatusResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> AuthStatusResponse | None:
    """Auth-mode and current-session status

     Return auth-mode flags and (if a session token is present and
    valid) the authenticated user.

    Public endpoint — no auth required. The frontend calls this on
    page load to decide whether to show the login screen, the setup
    wizard (no users exist), or the dashboard.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AuthStatusResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
