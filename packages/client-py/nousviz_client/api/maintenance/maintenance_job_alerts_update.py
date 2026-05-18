from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.job_alert_subscription import JobAlertSubscription
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.update_job_alert_subscription_body import UpdateJobAlertSubscriptionBody
from ...types import Response


def _get_kwargs(
    sub_id: str,
    *,
    body: UpdateJobAlertSubscriptionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/maintenance/job-alerts/{sub_id}".format(
            sub_id=quote(str(sub_id), safe=""),
        ),
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
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateJobAlertSubscriptionBody,
) -> Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]:
    """Update a job-alert subscription (toggle enabled / change on_status) (B284)

    Args:
        sub_id (str):
        body (UpdateJobAlertSubscriptionBody): PUT /api/maintenance/job-alerts/{id}. Pass only the
            fields you're changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        sub_id=sub_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateJobAlertSubscriptionBody,
) -> ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail | None:
    """Update a job-alert subscription (toggle enabled / change on_status) (B284)

    Args:
        sub_id (str):
        body (UpdateJobAlertSubscriptionBody): PUT /api/maintenance/job-alerts/{id}. Pass only the
            fields you're changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail
    """

    return sync_detailed(
        sub_id=sub_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateJobAlertSubscriptionBody,
) -> Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]:
    """Update a job-alert subscription (toggle enabled / change on_status) (B284)

    Args:
        sub_id (str):
        body (UpdateJobAlertSubscriptionBody): PUT /api/maintenance/job-alerts/{id}. Pass only the
            fields you're changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        sub_id=sub_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    sub_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateJobAlertSubscriptionBody,
) -> ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail | None:
    """Update a job-alert subscription (toggle enabled / change on_status) (B284)

    Args:
        sub_id (str):
        body (UpdateJobAlertSubscriptionBody): PUT /api/maintenance/job-alerts/{id}. Pass only the
            fields you're changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | JobAlertSubscription | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            sub_id=sub_id,
            client=client,
            body=body,
        )
    ).parsed
