from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.profile_update import ProfileUpdate
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.step_up_required_detail import StepUpRequiredDetail
from ...models.user_serialized import UserSerialized
from ...types import Response


def _get_kwargs(
    *,
    body: ProfileUpdate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/auth/me",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized | None:
    if response.status_code == 200:
        response_200 = UserSerialized.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorDetail.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = StepUpRequiredDetail.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ProfileUpdate,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized]:
    """Update own profile (password change requires step-up — B251)

     Update the current user's profile.

    B251 (v0.9.10.0.3): when the request includes the password field,
    requires recent step-up auth (same gate as RBAC writes from B236).
    Without this, a stolen session token could change the password and
    lock the real owner out. Other fields (name, etc.) remain step-up-
    free — they're not security-sensitive.

    Args:
        body (ProfileUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: ProfileUpdate,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized | None:
    """Update own profile (password change requires step-up — B251)

     Update the current user's profile.

    B251 (v0.9.10.0.3): when the request includes the password field,
    requires recent step-up auth (same gate as RBAC writes from B236).
    Without this, a stolen session token could change the password and
    lock the real owner out. Other fields (name, etc.) remain step-up-
    free — they're not security-sensitive.

    Args:
        body (ProfileUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ProfileUpdate,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized]:
    """Update own profile (password change requires step-up — B251)

     Update the current user's profile.

    B251 (v0.9.10.0.3): when the request includes the password field,
    requires recent step-up auth (same gate as RBAC writes from B236).
    Without this, a stolen session token could change the password and
    lock the real owner out. Other fields (name, etc.) remain step-up-
    free — they're not security-sensitive.

    Args:
        body (ProfileUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: ProfileUpdate,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized | None:
    """Update own profile (password change requires step-up — B251)

     Update the current user's profile.

    B251 (v0.9.10.0.3): when the request includes the password field,
    requires recent step-up auth (same gate as RBAC writes from B236).
    Without this, a stolen session token could change the password and
    lock the real owner out. Other fields (name, etc.) remain step-up-
    free — they're not security-sensitive.

    Args:
        body (ProfileUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | UserSerialized
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
