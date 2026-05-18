from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.deploy_key_check_response import DeployKeyCheckResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response


def _get_kwargs(
    *,
    repo_url: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["repo_url"] = repo_url

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/settings/deploy-keys/check",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DeployKeyCheckResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    repo_url: str,
) -> Response[DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Check whether a deploy key exists for a given repo URL

     Check if a deploy key exists for the given repo URL.

    B204: only exact repo_url matches return has_key=True. The previous
    host fallback returned a green indicator even when the actual key
    couldn't authenticate against this URL — the operator was misled
    into thinking install would succeed.

    Args:
        repo_url (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        repo_url=repo_url,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    repo_url: str,
) -> DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Check whether a deploy key exists for a given repo URL

     Check if a deploy key exists for the given repo URL.

    B204: only exact repo_url matches return has_key=True. The previous
    host fallback returned a green indicator even when the actual key
    couldn't authenticate against this URL — the operator was misled
    into thinking install would succeed.

    Args:
        repo_url (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        repo_url=repo_url,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    repo_url: str,
) -> Response[DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Check whether a deploy key exists for a given repo URL

     Check if a deploy key exists for the given repo URL.

    B204: only exact repo_url matches return has_key=True. The previous
    host fallback returned a green indicator even when the actual key
    couldn't authenticate against this URL — the operator was misled
    into thinking install would succeed.

    Args:
        repo_url (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        repo_url=repo_url,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    repo_url: str,
) -> DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Check whether a deploy key exists for a given repo URL

     Check if a deploy key exists for the given repo URL.

    B204: only exact repo_url matches return has_key=True. The previous
    host fallback returned a green indicator even when the actual key
    couldn't authenticate against this URL — the operator was misled
    into thinking install would succeed.

    Args:
        repo_url (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DeployKeyCheckResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            repo_url=repo_url,
        )
    ).parsed
