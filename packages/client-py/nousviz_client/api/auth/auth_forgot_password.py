from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.forgot_password_request import ForgotPasswordRequest
from ...models.generic_message_response import GenericMessageResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    *,
    body: ForgotPasswordRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/auth/forgot-password",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | GenericMessageResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = GenericMessageResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = ErrorDetail.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | GenericMessageResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ForgotPasswordRequest,
) -> Response[ErrorDetail | GenericMessageResponse | HTTPValidationError]:
    """Initiate password reset (enumeration-resistant)

     Public endpoint — initiate a password reset.

    Always returns 200 with the same body regardless of whether the
    email exists, matches a real user, or the email send actually
    succeeded. This prevents user-enumeration via response timing or
    response shape.

    Args:
        body (ForgotPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | GenericMessageResponse | HTTPValidationError]
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
    body: ForgotPasswordRequest,
) -> ErrorDetail | GenericMessageResponse | HTTPValidationError | None:
    """Initiate password reset (enumeration-resistant)

     Public endpoint — initiate a password reset.

    Always returns 200 with the same body regardless of whether the
    email exists, matches a real user, or the email send actually
    succeeded. This prevents user-enumeration via response timing or
    response shape.

    Args:
        body (ForgotPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | GenericMessageResponse | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ForgotPasswordRequest,
) -> Response[ErrorDetail | GenericMessageResponse | HTTPValidationError]:
    """Initiate password reset (enumeration-resistant)

     Public endpoint — initiate a password reset.

    Always returns 200 with the same body regardless of whether the
    email exists, matches a real user, or the email send actually
    succeeded. This prevents user-enumeration via response timing or
    response shape.

    Args:
        body (ForgotPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | GenericMessageResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: ForgotPasswordRequest,
) -> ErrorDetail | GenericMessageResponse | HTTPValidationError | None:
    """Initiate password reset (enumeration-resistant)

     Public endpoint — initiate a password reset.

    Always returns 200 with the same body regardless of whether the
    email exists, matches a real user, or the email send actually
    succeeded. This prevents user-enumeration via response timing or
    response shape.

    Args:
        body (ForgotPasswordRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | GenericMessageResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
