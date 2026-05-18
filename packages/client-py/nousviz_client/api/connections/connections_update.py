from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.connection_row import ConnectionRow
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.update_connection import UpdateConnection
from ...types import Response


def _get_kwargs(
    conn_id: str,
    *,
    body: UpdateConnection,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/connections/{conn_id}".format(
            conn_id=quote(str(conn_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = ConnectionRow.from_dict(response.json())

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

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    conn_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateConnection,
) -> Response[ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Patch a connection (password preserved when masked)

    Args:
        conn_id (str):
        body (UpdateConnection):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        conn_id=conn_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    conn_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateConnection,
) -> ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Patch a connection (password preserved when masked)

    Args:
        conn_id (str):
        body (UpdateConnection):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        conn_id=conn_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    conn_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateConnection,
) -> Response[ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Patch a connection (password preserved when masked)

    Args:
        conn_id (str):
        body (UpdateConnection):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        conn_id=conn_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    conn_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateConnection,
) -> ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Patch a connection (password preserved when masked)

    Args:
        conn_id (str):
        body (UpdateConnection):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ConnectionRow | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            conn_id=conn_id,
            client=client,
            body=body,
        )
    ).parsed
