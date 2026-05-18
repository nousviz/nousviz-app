from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.activity_list_response import ActivityListResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    action: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    page_path: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_action: None | str | Unset
    if isinstance(action, Unset):
        json_action = UNSET
    else:
        json_action = action
    params["action"] = json_action

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    json_page_path: None | str | Unset
    if isinstance(page_path, Unset):
        json_page_path = UNSET
    else:
        json_page_path = page_path
    params["page_path"] = json_page_path

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/activity",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = ActivityListResponse.from_dict(response.json())

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
) -> Response[ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    action: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    page_path: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List recent activity events (admin-only firehose)

     List recent activity. Newest-first, optional filters on action /
    plugin_id / page_path.

    Args:
        action (None | str | Unset):
        plugin_id (None | str | Unset):
        page_path (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        action=action,
        plugin_id=plugin_id,
        page_path=page_path,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    action: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    page_path: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List recent activity events (admin-only firehose)

     List recent activity. Newest-first, optional filters on action /
    plugin_id / page_path.

    Args:
        action (None | str | Unset):
        plugin_id (None | str | Unset):
        page_path (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        action=action,
        plugin_id=plugin_id,
        page_path=page_path,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    action: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    page_path: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List recent activity events (admin-only firehose)

     List recent activity. Newest-first, optional filters on action /
    plugin_id / page_path.

    Args:
        action (None | str | Unset):
        plugin_id (None | str | Unset):
        page_path (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        action=action,
        plugin_id=plugin_id,
        page_path=page_path,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    action: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    page_path: None | str | Unset = UNSET,
    limit: int | Unset = 50,
) -> ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List recent activity events (admin-only firehose)

     List recent activity. Newest-first, optional filters on action /
    plugin_id / page_path.

    Args:
        action (None | str | Unset):
        plugin_id (None | str | Unset):
        page_path (None | str | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActivityListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            action=action,
            plugin_id=plugin_id,
            page_path=page_path,
            limit=limit,
        )
    ).parsed
