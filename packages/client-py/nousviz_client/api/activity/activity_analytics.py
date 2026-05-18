from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.user_analytics_response import UserAnalyticsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    days: int | Unset = 30,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["days"] = days

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/activity/analytics",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse | None:
    if response.status_code == 200:
        response_200 = UserAnalyticsResponse.from_dict(response.json())

        return response_200

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 30,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse]:
    """Admin analytics: time, devices, IPs, sessions

     Admin analytics: time spent, devices, IPs, sessions, and usage patterns.

    Time-spent is a heuristic — sums gaps between consecutive page_view
    events, capped at 30 minutes per gap so an idle tab doesn't inflate
    the total. Sessions are runs of page_views separated by gaps >= 30 min.

    Args:
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse]
    """

    kwargs = _get_kwargs(
        days=days,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 30,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse | None:
    """Admin analytics: time, devices, IPs, sessions

     Admin analytics: time spent, devices, IPs, sessions, and usage patterns.

    Time-spent is a heuristic — sums gaps between consecutive page_view
    events, capped at 30 minutes per gap so an idle tab doesn't inflate
    the total. Sessions are runs of page_views separated by gaps >= 30 min.

    Args:
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse
    """

    return sync_detailed(
        client=client,
        days=days,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 30,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse]:
    """Admin analytics: time, devices, IPs, sessions

     Admin analytics: time spent, devices, IPs, sessions, and usage patterns.

    Time-spent is a heuristic — sums gaps between consecutive page_view
    events, capped at 30 minutes per gap so an idle tab doesn't inflate
    the total. Sessions are runs of page_views separated by gaps >= 30 min.

    Args:
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse]
    """

    kwargs = _get_kwargs(
        days=days,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 30,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse | None:
    """Admin analytics: time, devices, IPs, sessions

     Admin analytics: time spent, devices, IPs, sessions, and usage patterns.

    Time-spent is a heuristic — sums gaps between consecutive page_view
    events, capped at 30 minutes per gap so an idle tab doesn't inflate
    the total. Sessions are runs of page_views separated by gaps >= 30 min.

    Args:
        days (int | Unset):  Default: 30.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | UserAnalyticsResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            days=days,
        )
    ).parsed
