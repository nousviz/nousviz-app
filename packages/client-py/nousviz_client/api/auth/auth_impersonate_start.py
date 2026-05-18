from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.impersonate_start_response import ImpersonateStartResponse
from ...models.step_up_required_detail import StepUpRequiredDetail
from ...types import Response


def _get_kwargs(
    user_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/auth/impersonate/{user_id}".format(
            user_id=quote(str(user_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail | None:
    if response.status_code == 200:
        response_200 = ImpersonateStartResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = StepUpRequiredDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 409:
        response_409 = cast(Any, None)
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
) -> Response[Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    user_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail]:
    """Start impersonating a user (B254 — sets session flag, no token swap)

     Start impersonating another user — by setting flags on the
    caller's existing session, NOT by issuing a new session token.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
    INSERTed a new short-lived session row and returned a new token.
    Now updates the caller's session with `acting_as_user_id` and
    `acting_as_until`. The caller's token is unchanged. On exit (or
    auto-expire), the flags clear and the caller is back as themselves
    without re-login.

    Requirements:
    - Caller has users.manage (gated by Depends-style routing — see register_route above)
    - Caller has stepped up within the last STEP_UP_TTL_MINUTES
    - Caller's role rank > target's role rank (strict)
    - Target user exists and is active
    - Caller cannot already be impersonating (must exit first)

    Returns:
    - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
      Note: NO `token` field in the response. Caller's existing token
      continues to work; the next /api/auth/me will show the new
      `acting_as` field.
    - 401 if not stepped up.
    - 403 with `{error: 'rank_violation'}` if rank check fails.
    - 404 if target not found.
    - 409 if already impersonating.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        user_id=user_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    user_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail | None:
    """Start impersonating a user (B254 — sets session flag, no token swap)

     Start impersonating another user — by setting flags on the
    caller's existing session, NOT by issuing a new session token.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
    INSERTed a new short-lived session row and returned a new token.
    Now updates the caller's session with `acting_as_user_id` and
    `acting_as_until`. The caller's token is unchanged. On exit (or
    auto-expire), the flags clear and the caller is back as themselves
    without re-login.

    Requirements:
    - Caller has users.manage (gated by Depends-style routing — see register_route above)
    - Caller has stepped up within the last STEP_UP_TTL_MINUTES
    - Caller's role rank > target's role rank (strict)
    - Target user exists and is active
    - Caller cannot already be impersonating (must exit first)

    Returns:
    - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
      Note: NO `token` field in the response. Caller's existing token
      continues to work; the next /api/auth/me will show the new
      `acting_as` field.
    - 401 if not stepped up.
    - 403 with `{error: 'rank_violation'}` if rank check fails.
    - 404 if target not found.
    - 409 if already impersonating.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail
    """

    return sync_detailed(
        user_id=user_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    user_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail]:
    """Start impersonating a user (B254 — sets session flag, no token swap)

     Start impersonating another user — by setting flags on the
    caller's existing session, NOT by issuing a new session token.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
    INSERTed a new short-lived session row and returned a new token.
    Now updates the caller's session with `acting_as_user_id` and
    `acting_as_until`. The caller's token is unchanged. On exit (or
    auto-expire), the flags clear and the caller is back as themselves
    without re-login.

    Requirements:
    - Caller has users.manage (gated by Depends-style routing — see register_route above)
    - Caller has stepped up within the last STEP_UP_TTL_MINUTES
    - Caller's role rank > target's role rank (strict)
    - Target user exists and is active
    - Caller cannot already be impersonating (must exit first)

    Returns:
    - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
      Note: NO `token` field in the response. Caller's existing token
      continues to work; the next /api/auth/me will show the new
      `acting_as` field.
    - 401 if not stepped up.
    - 403 with `{error: 'rank_violation'}` if rank check fails.
    - 404 if target not found.
    - 409 if already impersonating.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        user_id=user_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    user_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail | None:
    """Start impersonating a user (B254 — sets session flag, no token swap)

     Start impersonating another user — by setting flags on the
    caller's existing session, NOT by issuing a new session token.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where this
    INSERTed a new short-lived session row and returned a new token.
    Now updates the caller's session with `acting_as_user_id` and
    `acting_as_until`. The caller's token is unchanged. On exit (or
    auto-expire), the flags clear and the caller is back as themselves
    without re-login.

    Requirements:
    - Caller has users.manage (gated by Depends-style routing — see register_route above)
    - Caller has stepped up within the last STEP_UP_TTL_MINUTES
    - Caller's role rank > target's role rank (strict)
    - Target user exists and is active
    - Caller cannot already be impersonating (must exit first)

    Returns:
    - 200 with `{acting_as: {target serialized}, acting_as_until: <iso>}`.
      Note: NO `token` field in the response. Caller's existing token
      continues to work; the next /api/auth/me will show the new
      `acting_as` field.
    - 401 if not stepped up.
    - 403 with `{error: 'rank_violation'}` if rank check fails.
    - 404 if target not found.
    - 409 if already impersonating.

    Args:
        user_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | ImpersonateStartResponse | StepUpRequiredDetail
    """

    return (
        await asyncio_detailed(
            user_id=user_id,
            client=client,
        )
    ).parsed
