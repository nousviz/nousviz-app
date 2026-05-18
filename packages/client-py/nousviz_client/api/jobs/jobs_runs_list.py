from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.job_runs_list_response import JobRunsListResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    job_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_job_id: None | str | Unset
    if isinstance(job_id, Unset):
        json_job_id = UNSET
    else:
        json_job_id = job_id
    params["job_id"] = json_job_id

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/jobs/runs",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = JobRunsListResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    job_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail]:
    """List recent job runs

     List recent job runs, optionally filtered by job_id.

    Returns up to `limit` runs ordered by `started_at` DESC. Used by
    the System → Jobs page and the per-plugin Sync history block.

    Args:
        job_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    job_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail | None:
    """List recent job runs

     List recent job runs, optionally filtered by job_id.

    Returns up to `limit` runs ordered by `started_at` DESC. Used by
    the System → Jobs page and the per-plugin Sync history block.

    Args:
        job_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        job_id=job_id,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    job_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail]:
    """List recent job runs

     List recent job runs, optionally filtered by job_id.

    Returns up to `limit` runs ordered by `started_at` DESC. Used by
    the System → Jobs page and the per-plugin Sync history block.

    Args:
        job_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    job_id: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail | None:
    """List recent job runs

     List recent job runs, optionally filtered by job_id.

    Returns up to `limit` runs ordered by `started_at` DESC. Used by
    the System → Jobs page and the per-plugin Sync history block.

    Args:
        job_id (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobRunsListResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            job_id=job_id,
            limit=limit,
        )
    ).parsed
