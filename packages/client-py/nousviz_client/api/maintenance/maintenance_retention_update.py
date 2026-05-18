from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.retention_policy_state import RetentionPolicyState
from ...models.update_retention_policy_body import UpdateRetentionPolicyBody
from ...types import Response


def _get_kwargs(
    policy_key: str,
    *,
    body: UpdateRetentionPolicyBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/maintenance/retention/{policy_key}".format(
            policy_key=quote(str(policy_key), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | RBACErrorDetail | RetentionPolicyState | None:
    if response.status_code == 200:
        response_200 = RetentionPolicyState.from_dict(response.json())

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
        response_422 = ErrorDetail.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | RBACErrorDetail | RetentionPolicyState]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateRetentionPolicyBody,
) -> Response[ErrorDetail | RBACErrorDetail | RetentionPolicyState]:
    """Update a retention policy (threshold or paused flag)

     Update one or both editable fields on a retention policy. Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):
        body (UpdateRetentionPolicyBody): PUT /api/maintenance/retention/{policy_key} body.

            Either field may be omitted; pass only what's changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | RetentionPolicyState]
    """

    kwargs = _get_kwargs(
        policy_key=policy_key,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateRetentionPolicyBody,
) -> ErrorDetail | RBACErrorDetail | RetentionPolicyState | None:
    """Update a retention policy (threshold or paused flag)

     Update one or both editable fields on a retention policy. Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):
        body (UpdateRetentionPolicyBody): PUT /api/maintenance/retention/{policy_key} body.

            Either field may be omitted; pass only what's changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | RetentionPolicyState
    """

    return sync_detailed(
        policy_key=policy_key,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateRetentionPolicyBody,
) -> Response[ErrorDetail | RBACErrorDetail | RetentionPolicyState]:
    """Update a retention policy (threshold or paused flag)

     Update one or both editable fields on a retention policy. Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):
        body (UpdateRetentionPolicyBody): PUT /api/maintenance/retention/{policy_key} body.

            Either field may be omitted; pass only what's changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | RBACErrorDetail | RetentionPolicyState]
    """

    kwargs = _get_kwargs(
        policy_key=policy_key,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    policy_key: str,
    *,
    client: AuthenticatedClient | Client,
    body: UpdateRetentionPolicyBody,
) -> ErrorDetail | RBACErrorDetail | RetentionPolicyState | None:
    """Update a retention policy (threshold or paused flag)

     Update one or both editable fields on a retention policy. Audit-
    logged with the operator's user_id.

    Args:
        policy_key (str):
        body (UpdateRetentionPolicyBody): PUT /api/maintenance/retention/{policy_key} body.

            Either field may be omitted; pass only what's changing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | RBACErrorDetail | RetentionPolicyState
    """

    return (
        await asyncio_detailed(
            policy_key=policy_key,
            client=client,
            body=body,
        )
    ).parsed
