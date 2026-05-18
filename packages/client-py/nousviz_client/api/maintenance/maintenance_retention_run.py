from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.retention_run_response import RetentionRunResponse
from ...types import Response


def _get_kwargs(
    policy_key: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/maintenance/retention/{policy_key}/run".format(
            policy_key=quote(str(policy_key), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse | None:
    if response.status_code == 200:
        response_200 = RetentionRunResponse.from_dict(response.json())

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

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse]:
    r"""Run a retention policy now (force; bypasses paused state)

     Run one policy immediately. Bypasses the paused flag (the
    operator just clicked \"Run now\" — that's their consent). Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse]
    """

    kwargs = _get_kwargs(
        policy_key=policy_key,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse | None:
    r"""Run a retention policy now (force; bypasses paused state)

     Run one policy immediately. Bypasses the paused flag (the
    operator just clicked \"Run now\" — that's their consent). Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse
    """

    return sync_detailed(
        policy_key=policy_key,
        client=client,
    ).parsed


async def asyncio_detailed(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse]:
    r"""Run a retention policy now (force; bypasses paused state)

     Run one policy immediately. Bypasses the paused flag (the
    operator just clicked \"Run now\" — that's their consent). Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse]
    """

    kwargs = _get_kwargs(
        policy_key=policy_key,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse | None:
    r"""Run a retention policy now (force; bypasses paused state)

     Run one policy immediately. Bypasses the paused flag (the
    operator just clicked \"Run now\" — that's their consent). Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RetentionRunResponse
    """

    return (
        await asyncio_detailed(
            policy_key=policy_key,
            client=client,
        )
    ).parsed
