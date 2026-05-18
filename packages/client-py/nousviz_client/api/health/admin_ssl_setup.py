from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.ssl_setup_request import SslSetupRequest
from ...models.ssl_setup_response import SslSetupResponse
from ...types import Response


def _get_kwargs(
    *,
    body: SslSetupRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/admin/ssl/setup",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse | None:
    if response.status_code == 200:
        response_200 = SslSetupResponse.from_dict(response.json())

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

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 500:
        response_500 = ErrorDetail.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SslSetupRequest,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse]:
    """Provision Let's Encrypt SSL via the ssl-setup.sh script

     Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
    Only Let's Encrypt is supported (requires a domain).

    Args:
        body (SslSetupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: SslSetupRequest,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse | None:
    """Provision Let's Encrypt SSL via the ssl-setup.sh script

     Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
    Only Let's Encrypt is supported (requires a domain).

    Args:
        body (SslSetupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SslSetupRequest,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse]:
    """Provision Let's Encrypt SSL via the ssl-setup.sh script

     Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
    Only Let's Encrypt is supported (requires a domain).

    Args:
        body (SslSetupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: SslSetupRequest,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse | None:
    """Provision Let's Encrypt SSL via the ssl-setup.sh script

     Run SSL setup from the UI. Calls ssl-setup.sh as subprocess.
    Only Let's Encrypt is supported (requires a domain).

    Args:
        body (SslSetupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SslSetupResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
