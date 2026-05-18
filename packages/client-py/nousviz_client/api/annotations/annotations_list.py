from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.annotations_list_response import AnnotationsListResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    plugin_id: None | str | Unset = UNSET,
    dataset: None | str | Unset = UNSET,
    category: None | str | Unset = UNSET,
    date_from: None | str | Unset = UNSET,
    date_to: None | str | Unset = UNSET,
    semantic_score: None | str | Unset = UNSET,
    pinned: bool | None | Unset = UNSET,
    include_archived: bool | Unset = False,
    limit: int | Unset = 200,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_plugin_id: None | str | Unset
    if isinstance(plugin_id, Unset):
        json_plugin_id = UNSET
    else:
        json_plugin_id = plugin_id
    params["plugin_id"] = json_plugin_id

    json_dataset: None | str | Unset
    if isinstance(dataset, Unset):
        json_dataset = UNSET
    else:
        json_dataset = dataset
    params["dataset"] = json_dataset

    json_category: None | str | Unset
    if isinstance(category, Unset):
        json_category = UNSET
    else:
        json_category = category
    params["category"] = json_category

    json_date_from: None | str | Unset
    if isinstance(date_from, Unset):
        json_date_from = UNSET
    else:
        json_date_from = date_from
    params["date_from"] = json_date_from

    json_date_to: None | str | Unset
    if isinstance(date_to, Unset):
        json_date_to = UNSET
    else:
        json_date_to = date_to
    params["date_to"] = json_date_to

    json_semantic_score: None | str | Unset
    if isinstance(semantic_score, Unset):
        json_semantic_score = UNSET
    else:
        json_semantic_score = semantic_score
    params["semantic_score"] = json_semantic_score

    json_pinned: bool | None | Unset
    if isinstance(pinned, Unset):
        json_pinned = UNSET
    else:
        json_pinned = pinned
    params["pinned"] = json_pinned

    params["include_archived"] = include_archived

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/annotations",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AnnotationsListResponse.from_dict(response.json())

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
) -> Response[AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    dataset: None | str | Unset = UNSET,
    category: None | str | Unset = UNSET,
    date_from: None | str | Unset = UNSET,
    date_to: None | str | Unset = UNSET,
    semantic_score: None | str | Unset = UNSET,
    pinned: bool | None | Unset = UNSET,
    include_archived: bool | Unset = False,
    limit: int | Unset = 200,
) -> Response[AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List annotations (pinned-first; rich filter set)

    Args:
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        category (None | str | Unset):
        date_from (None | str | Unset):
        date_to (None | str | Unset):
        semantic_score (None | str | Unset):
        pinned (bool | None | Unset):
        include_archived (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        dataset=dataset,
        category=category,
        date_from=date_from,
        date_to=date_to,
        semantic_score=semantic_score,
        pinned=pinned,
        include_archived=include_archived,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    dataset: None | str | Unset = UNSET,
    category: None | str | Unset = UNSET,
    date_from: None | str | Unset = UNSET,
    date_to: None | str | Unset = UNSET,
    semantic_score: None | str | Unset = UNSET,
    pinned: bool | None | Unset = UNSET,
    include_archived: bool | Unset = False,
    limit: int | Unset = 200,
) -> AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List annotations (pinned-first; rich filter set)

    Args:
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        category (None | str | Unset):
        date_from (None | str | Unset):
        date_to (None | str | Unset):
        semantic_score (None | str | Unset):
        pinned (bool | None | Unset):
        include_archived (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
        plugin_id=plugin_id,
        dataset=dataset,
        category=category,
        date_from=date_from,
        date_to=date_to,
        semantic_score=semantic_score,
        pinned=pinned,
        include_archived=include_archived,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    dataset: None | str | Unset = UNSET,
    category: None | str | Unset = UNSET,
    date_from: None | str | Unset = UNSET,
    date_to: None | str | Unset = UNSET,
    semantic_score: None | str | Unset = UNSET,
    pinned: bool | None | Unset = UNSET,
    include_archived: bool | Unset = False,
    limit: int | Unset = 200,
) -> Response[AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """List annotations (pinned-first; rich filter set)

    Args:
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        category (None | str | Unset):
        date_from (None | str | Unset):
        date_to (None | str | Unset):
        semantic_score (None | str | Unset):
        pinned (bool | None | Unset):
        include_archived (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        dataset=dataset,
        category=category,
        date_from=date_from,
        date_to=date_to,
        semantic_score=semantic_score,
        pinned=pinned,
        include_archived=include_archived,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    plugin_id: None | str | Unset = UNSET,
    dataset: None | str | Unset = UNSET,
    category: None | str | Unset = UNSET,
    date_from: None | str | Unset = UNSET,
    date_to: None | str | Unset = UNSET,
    semantic_score: None | str | Unset = UNSET,
    pinned: bool | None | Unset = UNSET,
    include_archived: bool | Unset = False,
    limit: int | Unset = 200,
) -> AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """List annotations (pinned-first; rich filter set)

    Args:
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        category (None | str | Unset):
        date_from (None | str | Unset):
        date_to (None | str | Unset):
        semantic_score (None | str | Unset):
        pinned (bool | None | Unset):
        include_archived (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 200.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationsListResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
            plugin_id=plugin_id,
            dataset=dataset,
            category=category,
            date_from=date_from,
            date_to=date_to,
            semantic_score=semantic_score,
            pinned=pinned,
            include_archived=include_archived,
            limit=limit,
        )
    ).parsed
