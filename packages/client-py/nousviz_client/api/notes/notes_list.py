from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.notes_list_response import NotesListResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    page_path: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    include_archived: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_page_path: None | str | Unset
    if isinstance(page_path, Unset):
        json_page_path = UNSET
    else:
        json_page_path = page_path
    params["page_path"] = json_page_path

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    params["include_archived"] = include_archived

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/notes",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = NotesListResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    page_path: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    include_archived: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail]:
    """List notes (pinned-first, optional page-path/plugin filter)

    Args:
        page_path (None | str | Unset):
        plugin_id (None | str | Unset):
        include_archived (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        page_path=page_path,
        plugin_id=plugin_id,
        include_archived=include_archived,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    page_path: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    include_archived: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail | None:
    """List notes (pinned-first, optional page-path/plugin filter)

    Args:
        page_path (None | str | Unset):
        plugin_id (None | str | Unset):
        include_archived (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        page_path=page_path,
        plugin_id=plugin_id,
        include_archived=include_archived,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    page_path: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    include_archived: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail]:
    """List notes (pinned-first, optional page-path/plugin filter)

    Args:
        page_path (None | str | Unset):
        plugin_id (None | str | Unset):
        include_archived (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        page_path=page_path,
        plugin_id=plugin_id,
        include_archived=include_archived,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    page_path: None | str | Unset = UNSET,
    plugin_id: None | str | Unset = UNSET,
    include_archived: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail | None:
    """List notes (pinned-first, optional page-path/plugin filter)

    Args:
        page_path (None | str | Unset):
        plugin_id (None | str | Unset):
        include_archived (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | NotesListResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            page_path=page_path,
            plugin_id=plugin_id,
            include_archived=include_archived,
        )
    ).parsed
