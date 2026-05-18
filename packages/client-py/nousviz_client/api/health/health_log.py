from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.health_log_response import HealthLogResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    days: int | Unset = 7,
    limit: int | Unset = 200,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["days"] = days

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/health/log",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = HealthLogResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 7,
    limit: int | Unset = 200,
) -> Response[ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail]:
    """Recent health-check snapshots from health_log

     Return health check history from the health_log table.

    Args:
        days (int | Unset):  Default: 7.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        days=days,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 7,
    limit: int | Unset = 200,
) -> ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail | None:
    """Recent health-check snapshots from health_log

     Return health check history from the health_log table.

    Args:
        days (int | Unset):  Default: 7.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        days=days,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 7,
    limit: int | Unset = 200,
) -> Response[ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail]:
    """Recent health-check snapshots from health_log

     Return health check history from the health_log table.

    Args:
        days (int | Unset):  Default: 7.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        days=days,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    days: int | Unset = 7,
    limit: int | Unset = 200,
) -> ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail | None:
    """Recent health-check snapshots from health_log

     Return health check history from the health_log table.

    Args:
        days (int | Unset):  Default: 7.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | HealthLogResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            days=days,
            limit=limit,
        )
    ).parsed
