from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.acl_default_policy_response import AclDefaultPolicyResponse
from ...models.default_policy_update import DefaultPolicyUpdate
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    resource_type: str,
    *,
    body: DefaultPolicyUpdate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/resource-acls/defaults/{resource_type}".format(
            resource_type=quote(str(resource_type), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AclDefaultPolicyResponse.from_dict(response.json())

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
) -> Response[AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    resource_type: str,
    *,
    client: AuthenticatedClient | Client,
    body: DefaultPolicyUpdate,
) -> Response[AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Set the default policy for a resource type ('allow' or 'deny')

    Args:
        resource_type (str):
        body (DefaultPolicyUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        resource_type=resource_type,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    resource_type: str,
    *,
    client: AuthenticatedClient | Client,
    body: DefaultPolicyUpdate,
) -> AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Set the default policy for a resource type ('allow' or 'deny')

    Args:
        resource_type (str):
        body (DefaultPolicyUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        resource_type=resource_type,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    resource_type: str,
    *,
    client: AuthenticatedClient | Client,
    body: DefaultPolicyUpdate,
) -> Response[AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Set the default policy for a resource type ('allow' or 'deny')

    Args:
        resource_type (str):
        body (DefaultPolicyUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        resource_type=resource_type,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    resource_type: str,
    *,
    client: AuthenticatedClient | Client,
    body: DefaultPolicyUpdate,
) -> AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Set the default policy for a resource type ('allow' or 'deny')

    Args:
        resource_type (str):
        body (DefaultPolicyUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AclDefaultPolicyResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            resource_type=resource_type,
            client=client,
            body=body,
        )
    ).parsed
