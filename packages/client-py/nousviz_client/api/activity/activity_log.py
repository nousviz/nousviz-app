from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.activity_event import ActivityEvent
from ...models.activity_log_response import ActivityLogResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    *,
    body: ActivityEvent,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/activity",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ActivityLogResponse | ErrorDetail | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ActivityLogResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ActivityLogResponse | ErrorDetail | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ActivityEvent,
) -> Response[ActivityLogResponse | ErrorDetail | HTTPValidationError]:
    """Record a user activity event

     Record a user activity event with device and IP metadata.

    Open to any authenticated user (POST-only — they can log their own
    activity but can't read the firehose).

    Args:
        body (ActivityEvent):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityLogResponse | ErrorDetail | HTTPValidationError]
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
    body: ActivityEvent,
) -> ActivityLogResponse | ErrorDetail | HTTPValidationError | None:
    """Record a user activity event

     Record a user activity event with device and IP metadata.

    Open to any authenticated user (POST-only — they can log their own
    activity but can't read the firehose).

    Args:
        body (ActivityEvent):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityLogResponse | ErrorDetail | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ActivityEvent,
) -> Response[ActivityLogResponse | ErrorDetail | HTTPValidationError]:
    """Record a user activity event

     Record a user activity event with device and IP metadata.

    Open to any authenticated user (POST-only — they can log their own
    activity but can't read the firehose).

    Args:
        body (ActivityEvent):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityLogResponse | ErrorDetail | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: ActivityEvent,
) -> ActivityLogResponse | ErrorDetail | HTTPValidationError | None:
    """Record a user activity event

     Record a user activity event with device and IP metadata.

    Open to any authenticated user (POST-only — they can log their own
    activity but can't read the firehose).

    Args:
        body (ActivityEvent):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityLogResponse | ErrorDetail | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
