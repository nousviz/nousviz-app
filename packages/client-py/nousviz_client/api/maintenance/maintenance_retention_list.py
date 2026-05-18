from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.retention_list_response import RetentionListResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/maintenance/retention",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | RBACErrorDetail | RetentionListResponse | None:
    if response.status_code == 200:
        response_200 = RetentionListResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | RBACErrorDetail | RetentionListResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | RBACErrorDetail | RetentionListResponse]:
    """List retention policies with live row counts and last-run state

     Return every retention policy registered in the POLICIES code
    constant, joined with the operator-tuned overrides + live counts.

    Each policy ships paused; first deploy is a no-op. Operator flips
    each on from `/settings/maintenance` after reviewing the
    `rows_would_prune` preview.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | RetentionListResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | RBACErrorDetail | RetentionListResponse | None:
    """List retention policies with live row counts and last-run state

     Return every retention policy registered in the POLICIES code
    constant, joined with the operator-tuned overrides + live counts.

    Each policy ships paused; first deploy is a no-op. Operator flips
    each on from `/settings/maintenance` after reviewing the
    `rows_would_prune` preview.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | RetentionListResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | RBACErrorDetail | RetentionListResponse]:
    """List retention policies with live row counts and last-run state

     Return every retention policy registered in the POLICIES code
    constant, joined with the operator-tuned overrides + live counts.

    Each policy ships paused; first deploy is a no-op. Operator flips
    each on from `/settings/maintenance` after reviewing the
    `rows_would_prune` preview.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | RetentionListResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | RBACErrorDetail | RetentionListResponse | None:
    """List retention policies with live row counts and last-run state

     Return every retention policy registered in the POLICIES code
    constant, joined with the operator-tuned overrides + live counts.

    Each policy ships paused; first deploy is a no-op. Operator flips
    each on from `/settings/maintenance` after reviewing the
    `rows_would_prune` preview.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | RetentionListResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
