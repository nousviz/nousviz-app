from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.available_webhooks_response import AvailableWebhooksResponse
from ...models.error_detail import ErrorDetail
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/maintenance/job-alerts/webhooks",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AvailableWebhooksResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail]:
    """List outbound webhooks available for job-alert subscriptions (B284)

     Picker source for the create-subscription form: every outbound
    webhook in webhook_endpoints with its UUID. Empty list when the
    webhooks plugin isn't installed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail | None:
    """List outbound webhooks available for job-alert subscriptions (B284)

     Picker source for the create-subscription form: every outbound
    webhook in webhook_endpoints with its UUID. Empty list when the
    webhooks plugin isn't installed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail]:
    """List outbound webhooks available for job-alert subscriptions (B284)

     Picker source for the create-subscription form: every outbound
    webhook in webhook_endpoints with its UUID. Empty list when the
    webhooks plugin isn't installed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail | None:
    """List outbound webhooks available for job-alert subscriptions (B284)

     Picker source for the create-subscription form: every outbound
    webhook in webhook_endpoints with its UUID. Empty list when the
    webhooks plugin isn't installed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AvailableWebhooksResponse | ErrorDetail | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
