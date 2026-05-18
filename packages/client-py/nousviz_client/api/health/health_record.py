from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.health_record_response import HealthRecordResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/health/record",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HealthRecordResponse | None:
    if response.status_code == 200:
        response_200 = HealthRecordResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = ErrorDetail.from_dict(response.json())

        return response_429

    if response.status_code == 500:
        response_500 = ErrorDetail.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HealthRecordResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HealthRecordResponse]:
    """Run a health check + persist to health_log (PM2 cron + manual refresh)

     Run a health check and store the result in health_log.

    Accepted from:
    - localhost (PM2 cron on the same box) — unlimited rate
    - authenticated requests (session token, API key, or Cloudflare) — lets
      an operator force a fresh check from the browser via the Refresh button
      on /health-overview. Rate-limited per-IP.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HealthRecordResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HealthRecordResponse | None:
    """Run a health check + persist to health_log (PM2 cron + manual refresh)

     Run a health check and store the result in health_log.

    Accepted from:
    - localhost (PM2 cron on the same box) — unlimited rate
    - authenticated requests (session token, API key, or Cloudflare) — lets
      an operator force a fresh check from the browser via the Refresh button
      on /health-overview. Rate-limited per-IP.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HealthRecordResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HealthRecordResponse]:
    """Run a health check + persist to health_log (PM2 cron + manual refresh)

     Run a health check and store the result in health_log.

    Accepted from:
    - localhost (PM2 cron on the same box) — unlimited rate
    - authenticated requests (session token, API key, or Cloudflare) — lets
      an operator force a fresh check from the browser via the Refresh button
      on /health-overview. Rate-limited per-IP.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HealthRecordResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HealthRecordResponse | None:
    """Run a health check + persist to health_log (PM2 cron + manual refresh)

     Run a health check and store the result in health_log.

    Accepted from:
    - localhost (PM2 cron on the same box) — unlimited rate
    - authenticated requests (session token, API key, or Cloudflare) — lets
      an operator force a fresh check from the browser via the Refresh button
      on /health-overview. Rate-limited per-IP.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HealthRecordResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
