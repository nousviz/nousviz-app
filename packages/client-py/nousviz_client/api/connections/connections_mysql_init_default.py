from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.mysql_init_default_response import MysqlInitDefaultResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/connections/mysql/init-default",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = MysqlInitDefaultResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 500:
        response_500 = ErrorDetail.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail]:
    """Create the default MySQL 'nousviz' database

     Create a default MySQL 'nousviz' database using existing default MySQL connection.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail | None:
    """Create the default MySQL 'nousviz' database

     Create a default MySQL 'nousviz' database using existing default MySQL connection.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail]:
    """Create the default MySQL 'nousviz' database

     Create a default MySQL 'nousviz' database using existing default MySQL connection.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail | None:
    """Create the default MySQL 'nousviz' database

     Create a default MySQL 'nousviz' database using existing default MySQL connection.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | MysqlInitDefaultResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
