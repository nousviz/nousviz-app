from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.sync_request import SyncRequest
from ...models.sync_response import SyncResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    plugin_id: str,
    *,
    body: SyncRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/plugins/{plugin_id}/sync".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | SyncResponse | None:
    if response.status_code == 200:
        response_200 = SyncResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | SyncResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncRequest | Unset = UNSET,
) -> Response[HTTPValidationError | SyncResponse]:
    r"""Trigger Sync

     Trigger a plugin sync manually.

    B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
    scheduled runs (the scheduler dispatches them) but ignored here —
    manual triggers always enqueue and return immediately so the HTTP
    request never blocks on subprocess execution. The unified Sync card
    on the plugin Settings tab polls /sync/status for live progress.

    Returns 409 Conflict when an active run already exists (status in
    queued/running/cancelling). Body shape on 409:
        {\"detail\": {\"run_id\": <existing>, \"status\": <status>,
                    \"already_running\": true}}
    Frontend swaps to the live progress view in this case rather than
    enqueueing a duplicate.

    Args:
        plugin_id (str):
        body (SyncRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SyncResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncRequest | Unset = UNSET,
) -> HTTPValidationError | SyncResponse | None:
    r"""Trigger Sync

     Trigger a plugin sync manually.

    B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
    scheduled runs (the scheduler dispatches them) but ignored here —
    manual triggers always enqueue and return immediately so the HTTP
    request never blocks on subprocess execution. The unified Sync card
    on the plugin Settings tab polls /sync/status for live progress.

    Returns 409 Conflict when an active run already exists (status in
    queued/running/cancelling). Body shape on 409:
        {\"detail\": {\"run_id\": <existing>, \"status\": <status>,
                    \"already_running\": true}}
    Frontend swaps to the live progress view in this case rather than
    enqueueing a duplicate.

    Args:
        plugin_id (str):
        body (SyncRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SyncResponse
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncRequest | Unset = UNSET,
) -> Response[HTTPValidationError | SyncResponse]:
    r"""Trigger Sync

     Trigger a plugin sync manually.

    B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
    scheduled runs (the scheduler dispatches them) but ignored here —
    manual triggers always enqueue and return immediately so the HTTP
    request never blocks on subprocess execution. The unified Sync card
    on the plugin Settings tab polls /sync/status for live progress.

    Returns 409 Conflict when an active run already exists (status in
    queued/running/cancelling). Body shape on 409:
        {\"detail\": {\"run_id\": <existing>, \"status\": <status>,
                    \"already_running\": true}}
    Frontend swaps to the live progress view in this case rather than
    enqueueing a duplicate.

    Args:
        plugin_id (str):
        body (SyncRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SyncResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncRequest | Unset = UNSET,
) -> HTTPValidationError | SyncResponse | None:
    r"""Trigger Sync

     Trigger a plugin sync manually.

    B205 (v0.9.6): always async. Manifest `execution_mode` is honored for
    scheduled runs (the scheduler dispatches them) but ignored here —
    manual triggers always enqueue and return immediately so the HTTP
    request never blocks on subprocess execution. The unified Sync card
    on the plugin Settings tab polls /sync/status for live progress.

    Returns 409 Conflict when an active run already exists (status in
    queued/running/cancelling). Body shape on 409:
        {\"detail\": {\"run_id\": <existing>, \"status\": <status>,
                    \"already_running\": true}}
    Frontend swaps to the live progress view in this case rather than
    enqueueing a duplicate.

    Args:
        plugin_id (str):
        body (SyncRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SyncResponse
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
            body=body,
        )
    ).parsed
