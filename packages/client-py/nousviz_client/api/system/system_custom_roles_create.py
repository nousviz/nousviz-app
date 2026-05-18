from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.custom_role_create_request import CustomRoleCreateRequest
from ...models.custom_role_create_response import CustomRoleCreateResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.step_up_required_detail import StepUpRequiredDetail
from ...types import Response


def _get_kwargs(
    *,
    body: CustomRoleCreateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/system/custom-roles",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    if response.status_code == 201:
        response_201 = CustomRoleCreateResponse.from_dict(response.json())

        return response_201

    if response.status_code == 400:
        response_400 = ErrorDetail.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = StepUpRequiredDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 409:
        response_409 = ErrorDetail.from_dict(response.json())

        return response_409

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
) -> Response[CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CustomRoleCreateRequest,
) -> Response[CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Create a custom role (B233; step-up required)

     Create a new operator-defined role.

    If `permissions` is omitted and `based_on` is a built-in role, the
    new role's permission set starts as a copy of that role's defaults.
    If both are omitted, the role starts empty and overrides must be
    added separately via /role-overrides.

    B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
    rejected with 409 (was silently filtered before — operators were
    creating roles thinking they got the requested permissions).
    `based_on` seeds still filter sensitive perms from the source role's
    defaults, since the operator didn't ask for them explicitly.

    Args:
        body (CustomRoleCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
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
    body: CustomRoleCreateRequest,
) -> CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Create a custom role (B233; step-up required)

     Create a new operator-defined role.

    If `permissions` is omitted and `based_on` is a built-in role, the
    new role's permission set starts as a copy of that role's defaults.
    If both are omitted, the role starts empty and overrides must be
    added separately via /role-overrides.

    B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
    rejected with 409 (was silently filtered before — operators were
    creating roles thinking they got the requested permissions).
    `based_on` seeds still filter sensitive perms from the source role's
    defaults, since the operator didn't ask for them explicitly.

    Args:
        body (CustomRoleCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: CustomRoleCreateRequest,
) -> Response[CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Create a custom role (B233; step-up required)

     Create a new operator-defined role.

    If `permissions` is omitted and `based_on` is a built-in role, the
    new role's permission set starts as a copy of that role's defaults.
    If both are omitted, the role starts empty and overrides must be
    added separately via /role-overrides.

    B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
    rejected with 409 (was silently filtered before — operators were
    creating roles thinking they got the requested permissions).
    `based_on` seeds still filter sensitive perms from the source role's
    defaults, since the operator didn't ask for them explicitly.

    Args:
        body (CustomRoleCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: CustomRoleCreateRequest,
) -> CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Create a custom role (B233; step-up required)

     Create a new operator-defined role.

    If `permissions` is omitted and `based_on` is a built-in role, the
    new role's permission set starts as a copy of that role's defaults.
    If both are omitted, the role starts empty and overrides must be
    added separately via /role-overrides.

    B236 (v0.9.10.0): sensitive permissions in the explicit seed list are
    rejected with 409 (was silently filtered before — operators were
    creating roles thinking they got the requested permissions).
    `based_on` seeds still filter sensitive perms from the source role's
    defaults, since the operator didn't ask for them explicitly.

    Args:
        body (CustomRoleCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CustomRoleCreateResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
