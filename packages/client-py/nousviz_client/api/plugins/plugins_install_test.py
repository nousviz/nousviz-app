from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.install_test_response import InstallTestResponse
from ...models.plugin_install_request import PluginInstallRequest
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    plugin_id: str,
    *,
    body: None | PluginInstallRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/plugins/{plugin_id}/install/test".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    if isinstance(body, PluginInstallRequest):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = InstallTestResponse.from_dict(response.json())

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

    if response.status_code == 502:
        response_502 = ErrorDetail.from_dict(response.json())

        return response_502

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: None | PluginInstallRequest | Unset = UNSET,
) -> Response[ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail]:
    """Pre-install repo connectivity probe (clone + read manifest)

     Test connectivity to a private repo before installing. Probe-clones and reads manifest.

    Args:
        plugin_id (str):
        body (None | PluginInstallRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: None | PluginInstallRequest | Unset = UNSET,
) -> ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail | None:
    """Pre-install repo connectivity probe (clone + read manifest)

     Test connectivity to a private repo before installing. Probe-clones and reads manifest.

    Args:
        plugin_id (str):
        body (None | PluginInstallRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: None | PluginInstallRequest | Unset = UNSET,
) -> Response[ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail]:
    """Pre-install repo connectivity probe (clone + read manifest)

     Test connectivity to a private repo before installing. Probe-clones and reads manifest.

    Args:
        plugin_id (str):
        body (None | PluginInstallRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: None | PluginInstallRequest | Unset = UNSET,
) -> ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail | None:
    """Pre-install repo connectivity probe (clone + read manifest)

     Test connectivity to a private repo before installing. Probe-clones and reads manifest.

    Args:
        plugin_id (str):
        body (None | PluginInstallRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | InstallTestResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
            body=body,
        )
    ).parsed
