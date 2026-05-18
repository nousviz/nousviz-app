from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.log_filters_response import LogFiltersResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/admin/logs/filters",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | LogFiltersResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = LogFiltersResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | LogFiltersResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | LogFiltersResponse | RBACErrorDetail]:
    """Distinct values for the /system/logs filter dropdowns

     B208 (v0.9.6.1): distinct values for the dropdown filters on
    /system/logs. Limited to events written in the last 30 days so the
    dropdowns don't accumulate stale plugin slugs or deleted users.

    Returns:
        plugins: list of distinct plugin_id values.
        users: list of {id, email} tuples for distinct actors.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | LogFiltersResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | LogFiltersResponse | RBACErrorDetail | None:
    """Distinct values for the /system/logs filter dropdowns

     B208 (v0.9.6.1): distinct values for the dropdown filters on
    /system/logs. Limited to events written in the last 30 days so the
    dropdowns don't accumulate stale plugin slugs or deleted users.

    Returns:
        plugins: list of distinct plugin_id values.
        users: list of {id, email} tuples for distinct actors.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | LogFiltersResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | LogFiltersResponse | RBACErrorDetail]:
    """Distinct values for the /system/logs filter dropdowns

     B208 (v0.9.6.1): distinct values for the dropdown filters on
    /system/logs. Limited to events written in the last 30 days so the
    dropdowns don't accumulate stale plugin slugs or deleted users.

    Returns:
        plugins: list of distinct plugin_id values.
        users: list of {id, email} tuples for distinct actors.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | LogFiltersResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | LogFiltersResponse | RBACErrorDetail | None:
    """Distinct values for the /system/logs filter dropdowns

     B208 (v0.9.6.1): distinct values for the dropdown filters on
    /system/logs. Limited to events written in the last 30 days so the
    dropdowns don't accumulate stale plugin slugs or deleted users.

    Returns:
        plugins: list of distinct plugin_id values.
        users: list of {id, email} tuples for distinct actors.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | LogFiltersResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
