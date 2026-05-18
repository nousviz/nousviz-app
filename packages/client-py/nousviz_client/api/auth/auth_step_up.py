from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.step_up_request import StepUpRequest
from ...models.step_up_response import StepUpResponse
from ...types import Response


def _get_kwargs(
    *,
    body: StepUpRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/auth/step-up",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | StepUpResponse | None:
    if response.status_code == 200:
        response_200 = StepUpResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

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
) -> Response[ErrorDetail | HTTPValidationError | StepUpResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: StepUpRequest,
) -> Response[ErrorDetail | HTTPValidationError | StepUpResponse]:
    """Re-authenticate for sensitive operations (B236)

     Re-authenticate the current session for sensitive operations.

    Returns 200 with `step_up_until` on correct password, sets
    user_sessions.step_up_until to now() + 5 minutes for the active session.

    Wrong password returns 401 with the same error shape as /login. Subject
    to the same per-IP rate limit as /login (5 attempts / 60s).

    Requires an active session — returns 401 if no valid token.

    Args:
        body (StepUpRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | StepUpResponse]
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
    body: StepUpRequest,
) -> ErrorDetail | HTTPValidationError | StepUpResponse | None:
    """Re-authenticate for sensitive operations (B236)

     Re-authenticate the current session for sensitive operations.

    Returns 200 with `step_up_until` on correct password, sets
    user_sessions.step_up_until to now() + 5 minutes for the active session.

    Wrong password returns 401 with the same error shape as /login. Subject
    to the same per-IP rate limit as /login (5 attempts / 60s).

    Requires an active session — returns 401 if no valid token.

    Args:
        body (StepUpRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | StepUpResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: StepUpRequest,
) -> Response[ErrorDetail | HTTPValidationError | StepUpResponse]:
    """Re-authenticate for sensitive operations (B236)

     Re-authenticate the current session for sensitive operations.

    Returns 200 with `step_up_until` on correct password, sets
    user_sessions.step_up_until to now() + 5 minutes for the active session.

    Wrong password returns 401 with the same error shape as /login. Subject
    to the same per-IP rate limit as /login (5 attempts / 60s).

    Requires an active session — returns 401 if no valid token.

    Args:
        body (StepUpRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | StepUpResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: StepUpRequest,
) -> ErrorDetail | HTTPValidationError | StepUpResponse | None:
    """Re-authenticate for sensitive operations (B236)

     Re-authenticate the current session for sensitive operations.

    Returns 200 with `step_up_until` on correct password, sets
    user_sessions.step_up_until to now() + 5 minutes for the active session.

    Wrong password returns 401 with the same error shape as /login. Subject
    to the same per-IP rate limit as /login (5 attempts / 60s).

    Requires an active session — returns 401 if no valid token.

    Args:
        body (StepUpRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | StepUpResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
