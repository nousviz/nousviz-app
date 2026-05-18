from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.logs_list_response import LogsListResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    source: None | str | Unset = UNSET,
    level: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    actor_user_id: None | str | Unset = UNSET,
    run_id: int | None | Unset = UNSET,
    q: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 100,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_source: None | str | Unset
    if isinstance(source, Unset):
        json_source = UNSET
    else:
        json_source = source
    params["source"] = json_source

    json_level: None | str | Unset
    if isinstance(level, Unset):
        json_level = UNSET
    else:
        json_level = level
    params["level"] = json_level

    json_since: None | str | Unset
    if isinstance(since, Unset):
        json_since = UNSET
    else:
        json_since = since
    params["since"] = json_since

    json_until: None | str | Unset
    if isinstance(until, Unset):
        json_until = UNSET
    else:
        json_until = until
    params["until"] = json_until

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    json_actor_user_id: None | str | Unset
    if isinstance(actor_user_id, Unset):
        json_actor_user_id = UNSET
    else:
        json_actor_user_id = actor_user_id
    params["actor_user_id"] = json_actor_user_id

    json_run_id: int | None | Unset
    if isinstance(run_id, Unset):
        json_run_id = UNSET
    else:
        json_run_id = run_id
    params["run_id"] = json_run_id

    json_q: None | str | Unset
    if isinstance(q, Unset):
        json_q = UNSET
    else:
        json_q = q
    params["q"] = json_q

    json_cursor: int | None | Unset
    if isinstance(cursor, Unset):
        json_cursor = UNSET
    else:
        json_cursor = cursor
    params["cursor"] = json_cursor

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/admin/logs",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = LogsListResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    level: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    actor_user_id: None | str | Unset = UNSET,
    run_id: int | None | Unset = UNSET,
    q: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 100,
) -> Response[ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail]:
    """Paginated app_logs feed with filters

     Return application logs. Admin only.

    B208 (v0.9.6.1): supports filtering on the promoted columns
    (plugin_id, actor_user_id, run_id) plus free-text search and date
    range. Falls back to detail->>'key' for legacy rows where the
    promoted column is NULL, so events written before the migration
    are still discoverable.

    Pagination: keyset on `id` descending. Pass the response's
    `next_cursor` back as `cursor` for the next page.

    B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
    or full ISO timestamps. Date-only inputs are normalized to start /
    end of UTC day server-side.

    Args:
        source (None | str | Unset):
        level (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        plugin_id (None | str | Unset):
        actor_user_id (None | str | Unset):
        run_id (int | None | Unset):
        q (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        source=source,
        level=level,
        since=since,
        until=until,
        plugin_id=plugin_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
        q=q,
        cursor=cursor,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    level: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    actor_user_id: None | str | Unset = UNSET,
    run_id: int | None | Unset = UNSET,
    q: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 100,
) -> ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail | None:
    """Paginated app_logs feed with filters

     Return application logs. Admin only.

    B208 (v0.9.6.1): supports filtering on the promoted columns
    (plugin_id, actor_user_id, run_id) plus free-text search and date
    range. Falls back to detail->>'key' for legacy rows where the
    promoted column is NULL, so events written before the migration
    are still discoverable.

    Pagination: keyset on `id` descending. Pass the response's
    `next_cursor` back as `cursor` for the next page.

    B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
    or full ISO timestamps. Date-only inputs are normalized to start /
    end of UTC day server-side.

    Args:
        source (None | str | Unset):
        level (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        plugin_id (None | str | Unset):
        actor_user_id (None | str | Unset):
        run_id (int | None | Unset):
        q (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        source=source,
        level=level,
        since=since,
        until=until,
        plugin_id=plugin_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
        q=q,
        cursor=cursor,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    level: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    actor_user_id: None | str | Unset = UNSET,
    run_id: int | None | Unset = UNSET,
    q: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 100,
) -> Response[ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail]:
    """Paginated app_logs feed with filters

     Return application logs. Admin only.

    B208 (v0.9.6.1): supports filtering on the promoted columns
    (plugin_id, actor_user_id, run_id) plus free-text search and date
    range. Falls back to detail->>'key' for legacy rows where the
    promoted column is NULL, so events written before the migration
    are still discoverable.

    Pagination: keyset on `id` descending. Pass the response's
    `next_cursor` back as `cursor` for the next page.

    B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
    or full ISO timestamps. Date-only inputs are normalized to start /
    end of UTC day server-side.

    Args:
        source (None | str | Unset):
        level (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        plugin_id (None | str | Unset):
        actor_user_id (None | str | Unset):
        run_id (int | None | Unset):
        q (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        source=source,
        level=level,
        since=since,
        until=until,
        plugin_id=plugin_id,
        actor_user_id=actor_user_id,
        run_id=run_id,
        q=q,
        cursor=cursor,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    level: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    actor_user_id: None | str | Unset = UNSET,
    run_id: int | None | Unset = UNSET,
    q: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 100,
) -> ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail | None:
    """Paginated app_logs feed with filters

     Return application logs. Admin only.

    B208 (v0.9.6.1): supports filtering on the promoted columns
    (plugin_id, actor_user_id, run_id) plus free-text search and date
    range. Falls back to detail->>'key' for legacy rows where the
    promoted column is NULL, so events written before the migration
    are still discoverable.

    Pagination: keyset on `id` descending. Pass the response's
    `next_cursor` back as `cursor` for the next page.

    B212 (v0.9.6.3): `since` / `until` accept date-only ('YYYY-MM-DD')
    or full ISO timestamps. Date-only inputs are normalized to start /
    end of UTC day server-side.

    Args:
        source (None | str | Unset):
        level (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        plugin_id (None | str | Unset):
        actor_user_id (None | str | Unset):
        run_id (int | None | Unset):
        q (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 100.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | LogsListResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            source=source,
            level=level,
            since=since,
            until=until,
            plugin_id=plugin_id,
            actor_user_id=actor_user_id,
            run_id=run_id,
            q=q,
            cursor=cursor,
            limit=limit,
        )
    ).parsed
