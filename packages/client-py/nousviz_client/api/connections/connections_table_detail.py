from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    conn_id: str,
    schema: str,
    table: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/connections/{conn_id}/tables/{schema}/{table}".format(
            conn_id=quote(str(conn_id), safe=""),
            schema=quote(str(schema), safe=""),
            table=quote(str(table), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = response.json()
        return response_200

    if response.status_code == 400:
        response_400 = ErrorDetail.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 501:
        response_501 = ErrorDetail.from_dict(response.json())

        return response_501

    if response.status_code == 502:
        response_502 = ErrorDetail.from_dict(response.json())

        return response_502

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    conn_id: str,
    schema: str,
    table: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Schema + metadata for one (connection, schema, table)

    Args:
        conn_id (str):
        schema (str):
        table (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        conn_id=conn_id,
        schema=schema,
        table=table,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    conn_id: str,
    schema: str,
    table: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Schema + metadata for one (connection, schema, table)

    Args:
        conn_id (str):
        schema (str):
        table (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        conn_id=conn_id,
        schema=schema,
        table=table,
        client=client,
    ).parsed


async def asyncio_detailed(
    conn_id: str,
    schema: str,
    table: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Schema + metadata for one (connection, schema, table)

    Args:
        conn_id (str):
        schema (str):
        table (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        conn_id=conn_id,
        schema=schema,
        table=table,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    conn_id: str,
    schema: str,
    table: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Schema + metadata for one (connection, schema, table)

    Args:
        conn_id (str):
        schema (str):
        table (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            conn_id=conn_id,
            schema=schema,
            table=table,
            client=client,
        )
    ).parsed
