from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.create_job_alert_subscription_body import CreateJobAlertSubscriptionBody
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.job_alert_subscription import JobAlertSubscription
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    *,
    body: CreateJobAlertSubscriptionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/maintenance/job-alerts",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = JobAlertSubscription.from_dict(response.json())

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

    if response.status_code == 409:
        response_409 = ErrorDetail.from_dict(response.json())

        return response_409

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateJobAlertSubscriptionBody,
) -> Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]:
    """Create a per-job-run failure alert subscription (B284)

    Args:
        body (CreateJobAlertSubscriptionBody): POST /api/maintenance/job-alerts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]
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
    body: CreateJobAlertSubscriptionBody,
) -> ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail | None:
    """Create a per-job-run failure alert subscription (B284)

    Args:
        body (CreateJobAlertSubscriptionBody): POST /api/maintenance/job-alerts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CreateJobAlertSubscriptionBody,
) -> Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]:
    """Create a per-job-run failure alert subscription (B284)

    Args:
        body (CreateJobAlertSubscriptionBody): POST /api/maintenance/job-alerts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CreateJobAlertSubscriptionBody,
) -> ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail | None:
    """Create a per-job-run failure alert subscription (B284)

    Args:
        body (CreateJobAlertSubscriptionBody): POST /api/maintenance/job-alerts.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
