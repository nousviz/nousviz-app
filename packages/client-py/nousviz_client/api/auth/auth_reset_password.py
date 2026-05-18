from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.generic_message_response import GenericMessageResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.reset_password_request import ResetPasswordRequest
from ...types import Response


def _get_kwargs(
    *,
    body: ResetPasswordRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/auth/reset-password",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | GenericMessageResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GenericMessageResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = cast(Any, None)
        return response_400

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | GenericMessageResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ResetPasswordRequest,
) -> Response[Any | GenericMessageResponse | HTTPValidationError]:
    """Consume a reset token + set new password

     Public endpoint — consume a password reset token.

    Validates the token, hashes the new password, updates the user row,
    marks the token used, kills all sessions for the user.

    Returns:
      200 {ok: true} on success
      400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
      400 if password too short

    Args:
        body (ResetPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GenericMessageResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: ResetPasswordRequest,
) -> Any | GenericMessageResponse | HTTPValidationError | None:
    """Consume a reset token + set new password

     Public endpoint — consume a password reset token.

    Validates the token, hashes the new password, updates the user row,
    marks the token used, kills all sessions for the user.

    Returns:
      200 {ok: true} on success
      400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
      400 if password too short

    Args:
        body (ResetPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GenericMessageResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ResetPasswordRequest,
) -> Response[Any | GenericMessageResponse | HTTPValidationError]:
    """Consume a reset token + set new password

     Public endpoint — consume a password reset token.

    Validates the token, hashes the new password, updates the user row,
    marks the token used, kills all sessions for the user.

    Returns:
      200 {ok: true} on success
      400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
      400 if password too short

    Args:
        body (ResetPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | GenericMessageResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: ResetPasswordRequest,
) -> Any | GenericMessageResponse | HTTPValidationError | None:
    """Consume a reset token + set new password

     Public endpoint — consume a password reset token.

    Validates the token, hashes the new password, updates the user row,
    marks the token used, kills all sessions for the user.

    Returns:
      200 {ok: true} on success
      400 {detail: {error: 'token_invalid' | 'token_expired' | 'token_used'}}
      400 if password too short

    Args:
        body (ResetPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | GenericMessageResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
