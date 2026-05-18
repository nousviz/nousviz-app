from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.launchpad_response import LaunchpadResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/launchpad",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | LaunchpadResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = LaunchpadResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | LaunchpadResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | LaunchpadResponse | RBACErrorDetail]:
    """Single-call aggregate data feed for the Overview page

     Single-call data feed for the Overview page.

    Each block is fetched in its own savepoint — failures roll back
    that block only and leave the rest of the response intact. The
    frontend receives partial data rather than a 500 when one of the
    underlying queries hits a missing table or stale schema.

    Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
    so the cache absorbs back-to-back requests without staleness anyone
    notices.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | LaunchpadResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | LaunchpadResponse | RBACErrorDetail | None:
    """Single-call aggregate data feed for the Overview page

     Single-call data feed for the Overview page.

    Each block is fetched in its own savepoint — failures roll back
    that block only and leave the rest of the response intact. The
    frontend receives partial data rather than a 500 when one of the
    underlying queries hits a missing table or stale schema.

    Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
    so the cache absorbs back-to-back requests without staleness anyone
    notices.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | LaunchpadResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | LaunchpadResponse | RBACErrorDetail]:
    """Single-call aggregate data feed for the Overview page

     Single-call data feed for the Overview page.

    Each block is fetched in its own savepoint — failures roll back
    that block only and leave the rest of the response intact. The
    frontend receives partial data rather than a 500 when one of the
    underlying queries hits a missing table or stale schema.

    Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
    so the cache absorbs back-to-back requests without staleness anyone
    notices.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | LaunchpadResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | LaunchpadResponse | RBACErrorDetail | None:
    """Single-call aggregate data feed for the Overview page

     Single-call data feed for the Overview page.

    Each block is fetched in its own savepoint — failures roll back
    that block only and leave the rest of the response intact. The
    frontend receives partial data rather than a 500 when one of the
    underlying queries hits a missing table or stale schema.

    Response cached 30s (v0.10.0.6.2). The Overview page polls every 60s,
    so the cache absorbs back-to-back requests without staleness anyone
    notices.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | LaunchpadResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
