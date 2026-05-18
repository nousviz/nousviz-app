from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.me_response import MeResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/me",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | MeResponse | None:
    if response.status_code == 200:
        response_200 = MeResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | MeResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MeResponse]:
    r"""Current actor (with optional acting_as target)

     Public `GET /api/auth/me` endpoint — Option B identity shape.

    B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
    to the session) as the primary identity. When the session is
    impersonating, the response also carries an `acting_as` field with
    the target's serialized identity.

    Frontend reads `me` for actor identity (audit, \"Exit impersonation\"
    banner, log-out button) and `me.acting_as` for effective identity
    (permission checks, role display). The `useEffectiveIdentity()` hook
    centralizes the choice for permission/UI display.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MeResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MeResponse | None:
    r"""Current actor (with optional acting_as target)

     Public `GET /api/auth/me` endpoint — Option B identity shape.

    B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
    to the session) as the primary identity. When the session is
    impersonating, the response also carries an `acting_as` field with
    the target's serialized identity.

    Frontend reads `me` for actor identity (audit, \"Exit impersonation\"
    banner, log-out button) and `me.acting_as` for effective identity
    (permission checks, role display). The `useEffectiveIdentity()` hook
    centralizes the choice for permission/UI display.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MeResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MeResponse]:
    r"""Current actor (with optional acting_as target)

     Public `GET /api/auth/me` endpoint — Option B identity shape.

    B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
    to the session) as the primary identity. When the session is
    impersonating, the response also carries an `acting_as` field with
    the target's serialized identity.

    Frontend reads `me` for actor identity (audit, \"Exit impersonation\"
    banner, log-out button) and `me.acting_as` for effective identity
    (permission checks, role display). The `useEffectiveIdentity()` hook
    centralizes the choice for permission/UI display.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MeResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MeResponse | None:
    r"""Current actor (with optional acting_as target)

     Public `GET /api/auth/me` endpoint — Option B identity shape.

    B236 (v0.9.10.0): always returns the ACTOR (the human authenticated
    to the session) as the primary identity. When the session is
    impersonating, the response also carries an `acting_as` field with
    the target's serialized identity.

    Frontend reads `me` for actor identity (audit, \"Exit impersonation\"
    banner, log-out button) and `me.acting_as` for effective identity
    (permission checks, role display). The `useEffectiveIdentity()` hook
    centralizes the choice for permission/UI display.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MeResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
