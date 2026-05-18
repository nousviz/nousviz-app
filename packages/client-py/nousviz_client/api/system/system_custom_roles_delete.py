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
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/system/custom-roles/{role}".format(
            role=quote(str(role), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 400:
        response_400 = ErrorDetail.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = StepUpRequiredDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorDetail.from_dict(response.json())

        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

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
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Delete a custom role (refuses if any user is assigned)

     Delete a custom role. Refuses if any user is assigned this role
    (operator must reassign first). Built-in roles cannot be deleted.
    Override rows for this role are also deleted.

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        role=role,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Delete a custom role (refuses if any user is assigned)

     Delete a custom role. Refuses if any user is assigned this role
    (operator must reassign first). Built-in roles cannot be deleted.
    Override rows for this role are also deleted.

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return sync_detailed(
        role=role,
        client=client,
    ).parsed


async def asyncio_detailed(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]:
    """Delete a custom role (refuses if any user is assigned)

     Delete a custom role. Refuses if any user is assigned this role
    (operator must reassign first). Built-in roles cannot be deleted.
    Override rows for this role are also deleted.

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail]
    """

    kwargs = _get_kwargs(
        role=role,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    role: str,
    *,
    client: AuthenticatedClient | Client,
) -> Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail | None:
    """Delete a custom role (refuses if any user is assigned)

     Delete a custom role. Refuses if any user is assigned this role
    (operator must reassign first). Built-in roles cannot be deleted.
    Override rows for this role are also deleted.

    Args:
        role (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDetail | HTTPValidationError | RBACErrorDetail | StepUpRequiredDetail
    """

    return (
        await asyncio_detailed(
            role=role,
            client=client,
        )
    ).parsed
