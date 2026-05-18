from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.note_entry import NoteEntry
from ...models.note_update import NoteUpdate
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs(
    note_id: str,
    *,
    body: NoteUpdate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/notes/{note_id}".format(
            note_id=quote(str(note_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = NoteEntry.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    note_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: NoteUpdate,
) -> Response[ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail]:
    """Update a note (partial — null fields skipped)

    Args:
        note_id (str):
        body (NoteUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        note_id=note_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    note_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: NoteUpdate,
) -> ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail | None:
    """Update a note (partial — null fields skipped)

    Args:
        note_id (str):
        body (NoteUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail
    """

    return sync_detailed(
        note_id=note_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    note_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: NoteUpdate,
) -> Response[ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail]:
    """Update a note (partial — null fields skipped)

    Args:
        note_id (str):
        body (NoteUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        note_id=note_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    note_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: NoteUpdate,
) -> ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail | None:
    """Update a note (partial — null fields skipped)

    Args:
        note_id (str):
        body (NoteUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | NoteEntry | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            note_id=note_id,
            client=client,
            body=body,
        )
    ).parsed
