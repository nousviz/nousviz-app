from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.share_update import ShareUpdate
from ...models.share_update_response import ShareUpdateResponse
from ...types import Response


def _get_kwargs(
    share_id: str,
    *,
    body: ShareUpdate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/shares/{share_id}".format(
            share_id=quote(str(share_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse | None:
    if response.status_code == 200:
        response_200 = ShareUpdateResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse]:
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
    body: ShareUpdate,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse]:
    """Update a share link's title and/or notes

     Update share title and/or notes.

    Args:
        share_id (str):
        body (ShareUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse]
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
    body: ShareUpdate,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse | None:
    """Update a share link's title and/or notes

     Update share title and/or notes.

    Args:
        share_id (str):
        body (ShareUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse
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
    body: ShareUpdate,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse]:
    """Update a share link's title and/or notes

     Update share title and/or notes.

    Args:
        share_id (str):
        body (ShareUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse]
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
    body: ShareUpdate,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse | None:
    """Update a share link's title and/or notes

     Update share title and/or notes.

    Args:
        share_id (str):
        body (ShareUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | ShareUpdateResponse
    """

    return (
        await asyncio_detailed(
            share_id=share_id,
            client=client,
            body=body,
        )
    ).parsed
