from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.step_up_required_detail import StepUpRequiredDetail
from ...types import Response


def _get_kwargs(
    role: str,
    permission: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/system/role-overrides/{role}/{permission}".format(
            role=quote(str(role), safe=""),
            permission=quote(str(permission), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 401:
        response_401 = StepUpRequiredDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if response.status_code == 500:
        response_500 = ErrorDetail.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    role: str,
    permission: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Clear an override (idempotent; 204 even on no-op)

     Clear any override for (role, permission). Idempotent — returns
    204 even when no override existed (no audit row in the no-op case).

    Args:
        role (str):
        permission (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        role=role,
        permission=permission,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    role: str,
    permission: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Clear an override (idempotent; 204 even on no-op)

     Clear any override for (role, permission). Idempotent — returns
    204 even when no override existed (no audit row in the no-op case).

    Args:
        role (str):
        permission (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return sync_detailed(
        role=role,
        permission=permission,
        client=client,
    ).parsed


async def asyncio_detailed(
    role: str,
    permission: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Clear an override (idempotent; 204 even on no-op)

     Clear any override for (role, permission). Idempotent — returns
    204 even when no override existed (no audit row in the no-op case).

    Args:
        role (str):
        permission (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        role=role,
        permission=permission,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    role: str,
    permission: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Clear an override (idempotent; 204 even on no-op)

     Clear any override for (role, permission). Idempotent — returns
    204 even when no override existed (no audit row in the no-op case).

    Args:
        role (str):
        permission (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return (
        await asyncio_detailed(
            role=role,
            permission=permission,
            client=client,
        )
    ).parsed
