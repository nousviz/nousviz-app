from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.health_config_response import HealthConfigResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/health/config",
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HealthConfigResponse | None:
    if response.status_code == 200:
        response_200 = HealthConfigResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HealthConfigResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[HealthConfigResponse]:
    r"""Boolean status of security-sensitive config

     Return boolean status of security-sensitive config values.

    Public endpoint (no auth required) — this is what the dashboard
    config-banner reads to decide whether to nudge the operator about
    missing encryption keys, missing superadmin user, SMTP config, etc.

    **Never exposes actual values** — only whether they are set and
    non-default. The `update_*` fields surface a once-per-hour-cached
    GitHub release check so operators can see the \"update available\"
    banner without polling the GitHub API on every request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HealthConfigResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> HealthConfigResponse | None:
    r"""Boolean status of security-sensitive config

     Return boolean status of security-sensitive config values.

    Public endpoint (no auth required) — this is what the dashboard
    config-banner reads to decide whether to nudge the operator about
    missing encryption keys, missing superadmin user, SMTP config, etc.

    **Never exposes actual values** — only whether they are set and
    non-default. The `update_*` fields surface a once-per-hour-cached
    GitHub release check so operators can see the \"update available\"
    banner without polling the GitHub API on every request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HealthConfigResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[HealthConfigResponse]:
    r"""Boolean status of security-sensitive config

     Return boolean status of security-sensitive config values.

    Public endpoint (no auth required) — this is what the dashboard
    config-banner reads to decide whether to nudge the operator about
    missing encryption keys, missing superadmin user, SMTP config, etc.

    **Never exposes actual values** — only whether they are set and
    non-default. The `update_*` fields surface a once-per-hour-cached
    GitHub release check so operators can see the \"update available\"
    banner without polling the GitHub API on every request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HealthConfigResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> HealthConfigResponse | None:
    r"""Boolean status of security-sensitive config

     Return boolean status of security-sensitive config values.

    Public endpoint (no auth required) — this is what the dashboard
    config-banner reads to decide whether to nudge the operator about
    missing encryption keys, missing superadmin user, SMTP config, etc.

    **Never exposes actual values** — only whether they are set and
    non-default. The `update_*` fields surface a once-per-hour-cached
    GitHub release check so operators can see the \"update available\"
    banner without polling the GitHub API on every request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HealthConfigResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
