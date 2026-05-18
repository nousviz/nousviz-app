from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.diagnostic_alert_subscription import DiagnosticAlertSubscription
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.update_diagnostic_alert_subscription_body import UpdateDiagnosticAlertSubscriptionBody
from ...types import Response


def _get_kwargs(
    webhook_id: str,
    *,
    body: UpdateDiagnosticAlertSubscriptionBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/maintenance/diagnostic-alerts/subscriptions/{webhook_id}".format(
            webhook_id=quote(str(webhook_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DiagnosticAlertSubscription.from_dict(response.json())

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
) -> Response[DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    webhook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDiagnosticAlertSubscriptionBody,
) -> Response[DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Subscribe or unsubscribe a webhook from diagnostic alerts (B274)

     Toggle subscription for one outbound webhook. Audit-logged with
    the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID.

    Args:
        webhook_id (str):
        body (UpdateDiagnosticAlertSubscriptionBody): PUT /api/maintenance/diagnostic-
            alerts/subscriptions/{webhook_id}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        webhook_id=webhook_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDiagnosticAlertSubscriptionBody,
) -> DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Subscribe or unsubscribe a webhook from diagnostic alerts (B274)

     Toggle subscription for one outbound webhook. Audit-logged with
    the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID.

    Args:
        webhook_id (str):
        body (UpdateDiagnosticAlertSubscriptionBody): PUT /api/maintenance/diagnostic-
            alerts/subscriptions/{webhook_id}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        webhook_id=webhook_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    webhook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDiagnosticAlertSubscriptionBody,
) -> Response[DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Subscribe or unsubscribe a webhook from diagnostic alerts (B274)

     Toggle subscription for one outbound webhook. Audit-logged with
    the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID.

    Args:
        webhook_id (str):
        body (UpdateDiagnosticAlertSubscriptionBody): PUT /api/maintenance/diagnostic-
            alerts/subscriptions/{webhook_id}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        webhook_id=webhook_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateDiagnosticAlertSubscriptionBody,
) -> DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Subscribe or unsubscribe a webhook from diagnostic alerts (B274)

     Toggle subscription for one outbound webhook. Audit-logged with
    the operator's user_id. v0.9.11.24 (B283): keyed on webhook_id UUID.

    Args:
        webhook_id (str):
        body (UpdateDiagnosticAlertSubscriptionBody): PUT /api/maintenance/diagnostic-
            alerts/subscriptions/{webhook_id}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiagnosticAlertSubscription | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            webhook_id=webhook_id,
            client=client,
            body=body,
        )
    ).parsed
