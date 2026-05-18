from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.maintenance_job_alerts_delete_response_maintenance_job_alerts_delete import (
    MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete,
)
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    sub_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/maintenance/job-alerts/{sub_id}".format(
            sub_id=quote(str(sub_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> (
    ErrorDetail
    | HTTPValidationError
    | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete
    | RBACErrorDetail
    | None
):
    if response.status_code == 200:
        response_200 = MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete.from_dict(response.json())

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
) -> Response[
    ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail
]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail
]:
    """Delete a job-alert subscription (B284)

    Args:
        sub_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        sub_id=sub_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> (
    ErrorDetail
    | HTTPValidationError
    | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete
    | RBACErrorDetail
    | None
):
    """Delete a job-alert subscription (B284)

    Args:
        sub_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail
    """

    return sync_detailed(
        sub_id=sub_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[
    ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail
]:
    """Delete a job-alert subscription (B284)

    Args:
        sub_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        sub_id=sub_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> (
    ErrorDetail
    | HTTPValidationError
    | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete
    | RBACErrorDetail
    | None
):
    """Delete a job-alert subscription (B284)

    Args:
        sub_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | MaintenanceJobAlertsDeleteResponseMaintenanceJobAlertsDelete | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            sub_id=sub_id,
            client=client,
        )
    ).parsed
