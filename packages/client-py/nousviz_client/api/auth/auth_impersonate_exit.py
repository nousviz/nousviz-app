from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.impersonate_exit_response import ImpersonateExitResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/auth/impersonate/exit",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ImpersonateExitResponse | None:
    if response.status_code == 200:
        response_200 = ImpersonateExitResponse.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ImpersonateExitResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ImpersonateExitResponse]:
    r"""End impersonation by clearing session flags (B254 — no re-login)

     End the current impersonation by clearing flags on the caller's session.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
    killed the impersonation session row. The session row is now the
    actor's existing session (with transient acting_as_* flags); exit
    just clears the flags. The session token, expires_at, and metadata
    all remain unchanged — actor stays logged in as themselves with no
    re-login needed.

    Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
    first-match-wins resolution picks this for `/impersonate/exit`
    rather than treating \"exit\" as a user_id parameter.

    Idempotent: returns 200 with `wasImpersonating: false` if the
    current session isn't impersonating.

    No step-up requirement — anyone holding the session may leave the
    impersonation. Step-up is required to ENTER impersonation, not exit.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ImpersonateExitResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ImpersonateExitResponse | None:
    r"""End impersonation by clearing session flags (B254 — no re-login)

     End the current impersonation by clearing flags on the caller's session.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
    killed the impersonation session row. The session row is now the
    actor's existing session (with transient acting_as_* flags); exit
    just clears the flags. The session token, expires_at, and metadata
    all remain unchanged — actor stays logged in as themselves with no
    re-login needed.

    Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
    first-match-wins resolution picks this for `/impersonate/exit`
    rather than treating \"exit\" as a user_id parameter.

    Idempotent: returns 200 with `wasImpersonating: false` if the
    current session isn't impersonating.

    No step-up requirement — anyone holding the session may leave the
    impersonation. Step-up is required to ENTER impersonation, not exit.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ImpersonateExitResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ImpersonateExitResponse]:
    r"""End impersonation by clearing session flags (B254 — no re-login)

     End the current impersonation by clearing flags on the caller's session.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
    killed the impersonation session row. The session row is now the
    actor's existing session (with transient acting_as_* flags); exit
    just clears the flags. The session token, expires_at, and metadata
    all remain unchanged — actor stays logged in as themselves with no
    re-login needed.

    Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
    first-match-wins resolution picks this for `/impersonate/exit`
    rather than treating \"exit\" as a user_id parameter.

    Idempotent: returns 200 with `wasImpersonating: false` if the
    current session isn't impersonating.

    No step-up requirement — anyone holding the session may leave the
    impersonation. Step-up is required to ENTER impersonation, not exit.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ImpersonateExitResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ImpersonateExitResponse | None:
    r"""End impersonation by clearing session flags (B254 — no re-login)

     End the current impersonation by clearing flags on the caller's session.

    B254 (v0.9.10.0.5): refactored from the v0.9.10.0 model where exit
    killed the impersonation session row. The session row is now the
    actor's existing session (with transient acting_as_* flags); exit
    just clears the flags. The session token, expires_at, and metadata
    all remain unchanged — actor stays logged in as themselves with no
    re-login needed.

    Declared BEFORE the `/impersonate/{user_id}` route so FastAPI's
    first-match-wins resolution picks this for `/impersonate/exit`
    rather than treating \"exit\" as a user_id parameter.

    Idempotent: returns 200 with `wasImpersonating: false` if the
    current session isn't impersonating.

    No step-up requirement — anyone holding the session may leave the
    impersonation. Step-up is required to ENTER impersonation, not exit.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ImpersonateExitResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
