from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.fire_now_response import FireNowResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    job_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/jobs/{job_id}/fire-now".format(
            job_id=quote(str(job_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = FireNowResponse.from_dict(response.json())

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

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    job_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail]:
    """Immediately trigger a schedulable job

     Immediately trigger a schedulable job.

    For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
    the manual-trigger endpoint which honors execution_mode (async vs
    sync). For core jobs (alerts-runner, health-monitor), this is a
    no-op for now — their schedulers are external (PM2 cron_restart).

    job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    job_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail | None:
    """Immediately trigger a schedulable job

     Immediately trigger a schedulable job.

    For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
    the manual-trigger endpoint which honors execution_mode (async vs
    sync). For core jobs (alerts-runner, health-monitor), this is a
    no-op for now — their schedulers are external (PM2 cron_restart).

    job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        job_id=job_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    job_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail]:
    """Immediately trigger a schedulable job

     Immediately trigger a schedulable job.

    For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
    the manual-trigger endpoint which honors execution_mode (async vs
    sync). For core jobs (alerts-runner, health-monitor), this is a
    no-op for now — their schedulers are external (PM2 cron_restart).

    job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    job_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail | None:
    """Immediately trigger a schedulable job

     Immediately trigger a schedulable job.

    For plugin syncs (job_id looks like '<plugin_id>-sync'), delegates to
    the manual-trigger endpoint which honors execution_mode (async vs
    sync). For core jobs (alerts-runner, health-monitor), this is a
    no-op for now — their schedulers are external (PM2 cron_restart).

    job_id comes from the `jobs` list `id` field (e.g. 'starter-plugin-sync').

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | FireNowResponse | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            job_id=job_id,
            client=client,
        )
    ).parsed
