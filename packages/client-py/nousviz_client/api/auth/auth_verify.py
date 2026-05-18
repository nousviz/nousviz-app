from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.verify_response import VerifyResponse
from ...types import UNSET, Response


def _get_kwargs(
    *,
    token: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["token"] = token

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/auth/verify",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | VerifyResponse | None:
    if response.status_code == 200:
        response_200 = VerifyResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | VerifyResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    token: str,
) -> Response[HTTPValidationError | VerifyResponse]:
    """Introspect a session token (public)

     Introspect a session token via the `?token=` query parameter.

    Public endpoint — does not require X-Session-Token. Returns
    `{valid: false}` for any invalid, expired, or missing token.
    Used by share-link landing pages and embed contexts to test
    whether a token is still good without consuming it.

    Args:
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | VerifyResponse]
    """

    kwargs = _get_kwargs(
        token=token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    token: str,
) -> HTTPValidationError | VerifyResponse | None:
    """Introspect a session token (public)

     Introspect a session token via the `?token=` query parameter.

    Public endpoint — does not require X-Session-Token. Returns
    `{valid: false}` for any invalid, expired, or missing token.
    Used by share-link landing pages and embed contexts to test
    whether a token is still good without consuming it.

    Args:
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | VerifyResponse
    """

    return sync_detailed(
        client=client,
        token=token,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    token: str,
) -> Response[HTTPValidationError | VerifyResponse]:
    """Introspect a session token (public)

     Introspect a session token via the `?token=` query parameter.

    Public endpoint — does not require X-Session-Token. Returns
    `{valid: false}` for any invalid, expired, or missing token.
    Used by share-link landing pages and embed contexts to test
    whether a token is still good without consuming it.

    Args:
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | VerifyResponse]
    """

    kwargs = _get_kwargs(
        token=token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    token: str,
) -> HTTPValidationError | VerifyResponse | None:
    """Introspect a session token (public)

     Introspect a session token via the `?token=` query parameter.

    Public endpoint — does not require X-Session-Token. Returns
    `{valid: false}` for any invalid, expired, or missing token.
    Used by share-link landing pages and embed contexts to test
    whether a token is still good without consuming it.

    Args:
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | VerifyResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            token=token,
        )
    ).parsed
