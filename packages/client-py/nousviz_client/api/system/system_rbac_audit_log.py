from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_audit_log_response import RbacAuditLogResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    actor_user_id: None | str | Unset = UNSET,
    target_role: None | str | Unset = UNSET,
    action: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_actor_user_id: None | str | Unset
    if isinstance(actor_user_id, Unset):
        json_actor_user_id = UNSET
    else:
        json_actor_user_id = actor_user_id
    params["actor_user_id"] = json_actor_user_id

    json_target_role: None | str | Unset
    if isinstance(target_role, Unset):
        json_target_role = UNSET
    else:
        json_target_role = target_role
    params["target_role"] = json_target_role

    json_action: None | str | Unset
    if isinstance(action, Unset):
        json_action = UNSET
    else:
        json_action = action
    params["action"] = json_action

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
        "url": "/api/system/rbac-audit-log",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse | None:
    if response.status_code == 200:
        response_200 = RbacAuditLogResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    actor_user_id: None | str | Unset = UNSET,
    target_role: None | str | Unset = UNSET,
    action: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse]:
    """Paginated RBAC config-mutation audit log

     Recent RBAC config mutations. Filters: actor / target_role /
    action / time window. Cursor-based pagination (opaque numeric
    cursor = the smallest id from the previous page).

    Joins users.email so renamed users still show up correctly.

    Gated by system.audit (admin+). Read-only.

    Args:
        actor_user_id (None | str | Unset):
        target_role (None | str | Unset):
        action (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse]
    """

    kwargs = _get_kwargs(
        actor_user_id=actor_user_id,
        target_role=target_role,
        action=action,
        since=since,
        until=until,
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
    actor_user_id: None | str | Unset = UNSET,
    target_role: None | str | Unset = UNSET,
    action: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse | None:
    """Paginated RBAC config-mutation audit log

     Recent RBAC config mutations. Filters: actor / target_role /
    action / time window. Cursor-based pagination (opaque numeric
    cursor = the smallest id from the previous page).

    Joins users.email so renamed users still show up correctly.

    Gated by system.audit (admin+). Read-only.

    Args:
        actor_user_id (None | str | Unset):
        target_role (None | str | Unset):
        action (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse
    """

    return sync_detailed(
        client=client,
        actor_user_id=actor_user_id,
        target_role=target_role,
        action=action,
        since=since,
        until=until,
        cursor=cursor,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    actor_user_id: None | str | Unset = UNSET,
    target_role: None | str | Unset = UNSET,
    action: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 50,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse]:
    """Paginated RBAC config-mutation audit log

     Recent RBAC config mutations. Filters: actor / target_role /
    action / time window. Cursor-based pagination (opaque numeric
    cursor = the smallest id from the previous page).

    Joins users.email so renamed users still show up correctly.

    Gated by system.audit (admin+). Read-only.

    Args:
        actor_user_id (None | str | Unset):
        target_role (None | str | Unset):
        action (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse]
    """

    kwargs = _get_kwargs(
        actor_user_id=actor_user_id,
        target_role=target_role,
        action=action,
        since=since,
        until=until,
        cursor=cursor,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    actor_user_id: None | str | Unset = UNSET,
    target_role: None | str | Unset = UNSET,
    action: None | str | Unset = UNSET,
    since: None | str | Unset = UNSET,
    until: None | str | Unset = UNSET,
    cursor: int | None | Unset = UNSET,
    limit: int | Unset = 50,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse | None:
    """Paginated RBAC config-mutation audit log

     Recent RBAC config mutations. Filters: actor / target_role /
    action / time window. Cursor-based pagination (opaque numeric
    cursor = the smallest id from the previous page).

    Joins users.email so renamed users still show up correctly.

    Gated by system.audit (admin+). Read-only.

    Args:
        actor_user_id (None | str | Unset):
        target_role (None | str | Unset):
        action (None | str | Unset):
        since (None | str | Unset):
        until (None | str | Unset):
        cursor (int | None | Unset):
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | RbacAuditLogResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            actor_user_id=actor_user_id,
            target_role=target_role,
            action=action,
            since=since,
            until=until,
            cursor=cursor,
            limit=limit,
        )
    ).parsed
