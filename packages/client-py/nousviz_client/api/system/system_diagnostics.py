from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.diagnostics_response import DiagnosticsResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    fresh: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["fresh"] = fresh

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/system/diagnostics",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DiagnosticsResponse.from_dict(response.json())

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
) -> Response[DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> Response[DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Diagnostic findings derived from /system/resources data (B272)

     Return findings produced by the diagnostic rules engine.

    12 pure-function rules (apps/api/src/services/system_diagnostics.py)
    each produce zero or more named findings with severity, evidence,
    and a recommendation. Cached in-process for 30 seconds; pass
    `?fresh=true` to bypass and re-evaluate.

    Args:
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        fresh=fresh,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Diagnostic findings derived from /system/resources data (B272)

     Return findings produced by the diagnostic rules engine.

    12 pure-function rules (apps/api/src/services/system_diagnostics.py)
    each produce zero or more named findings with severity, evidence,
    and a recommendation. Cached in-process for 30 seconds; pass
    `?fresh=true` to bypass and re-evaluate.

    Args:
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        fresh=fresh,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> Response[DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Diagnostic findings derived from /system/resources data (B272)

     Return findings produced by the diagnostic rules engine.

    12 pure-function rules (apps/api/src/services/system_diagnostics.py)
    each produce zero or more named findings with severity, evidence,
    and a recommendation. Cached in-process for 30 seconds; pass
    `?fresh=true` to bypass and re-evaluate.

    Args:
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        fresh=fresh,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Diagnostic findings derived from /system/resources data (B272)

     Return findings produced by the diagnostic rules engine.

    12 pure-function rules (apps/api/src/services/system_diagnostics.py)
    each produce zero or more named findings with severity, evidence,
    and a recommendation. Cached in-process for 30 seconds; pass
    `?fresh=true` to bypass and re-evaluate.

    Args:
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiagnosticsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            fresh=fresh,
        )
    ).parsed
