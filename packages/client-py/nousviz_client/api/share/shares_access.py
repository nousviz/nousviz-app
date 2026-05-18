from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.share_access import ShareAccess
from ...models.share_access_response import ShareAccessResponse
from ...types import Response


def _get_kwargs(
    share_id: str,
    *,
    body: ShareAccess,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/shares/{share_id}/access".format(
            share_id=quote(str(share_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | ShareAccessResponse | None:
    if response.status_code == 200:
        response_200 = ShareAccessResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 410:
        response_410 = ErrorDetail.from_dict(response.json())

        return response_410

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = ErrorDetail.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | ShareAccessResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    share_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: ShareAccess,
) -> Response[ErrorDetail | HTTPValidationError | ShareAccessResponse]:
    """Access a share link (public; password-gated when applicable)

    Args:
        share_id (str):
        body (ShareAccess):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | ShareAccessResponse]
    """

    kwargs = _get_kwargs(
        share_id=share_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    share_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: ShareAccess,
) -> ErrorDetail | HTTPValidationError | ShareAccessResponse | None:
    """Access a share link (public; password-gated when applicable)

    Args:
        share_id (str):
        body (ShareAccess):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | ShareAccessResponse
    """

    return sync_detailed(
        share_id=share_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    share_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: ShareAccess,
) -> Response[ErrorDetail | HTTPValidationError | ShareAccessResponse]:
    """Access a share link (public; password-gated when applicable)

    Args:
        share_id (str):
        body (ShareAccess):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | ShareAccessResponse]
    """

    kwargs = _get_kwargs(
        share_id=share_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    share_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: ShareAccess,
) -> ErrorDetail | HTTPValidationError | ShareAccessResponse | None:
    """Access a share link (public; password-gated when applicable)

    Args:
        share_id (str):
        body (ShareAccess):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | ShareAccessResponse
    """

    return (
        await asyncio_detailed(
            share_id=share_id,
            client=client,
            body=body,
        )
    ).parsed
