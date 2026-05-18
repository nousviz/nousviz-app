from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.dataset_detail_response import DatasetDetailResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    slug: str,
    *,
    limit: int | Unset = 0,
    offset: int | Unset = 0,
    sort_by: None | str | Unset = UNSET,
    sort_order: str | Unset = "asc",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    json_sort_by: None | str | Unset
    if isinstance(sort_by, Unset):
        json_sort_by = UNSET
    else:
        json_sort_by = sort_by
    params["sort_by"] = json_sort_by

    params["sort_order"] = sort_order

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/datasets/{slug}".format(
            slug=quote(str(slug), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DatasetDetailResponse.from_dict(response.json())

        return response_200

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
) -> Response[DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    slug: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 0,
    offset: int | Unset = 0,
    sort_by: None | str | Unset = UNSET,
    sort_order: str | Unset = "asc",
) -> Response[DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Get a dataset including its data matrix (sortable, paginated)

    Args:
        slug (str):
        limit (int | Unset): Limit rows (0 = all) Default: 0.
        offset (int | Unset):  Default: 0.
        sort_by (None | str | Unset):
        sort_order (str | Unset):  Default: 'asc'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        slug=slug,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    slug: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 0,
    offset: int | Unset = 0,
    sort_by: None | str | Unset = UNSET,
    sort_order: str | Unset = "asc",
) -> DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Get a dataset including its data matrix (sortable, paginated)

    Args:
        slug (str):
        limit (int | Unset): Limit rows (0 = all) Default: 0.
        offset (int | Unset):  Default: 0.
        sort_by (None | str | Unset):
        sort_order (str | Unset):  Default: 'asc'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        slug=slug,
        client=client,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    ).parsed


async def asyncio_detailed(
    slug: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 0,
    offset: int | Unset = 0,
    sort_by: None | str | Unset = UNSET,
    sort_order: str | Unset = "asc",
) -> Response[DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Get a dataset including its data matrix (sortable, paginated)

    Args:
        slug (str):
        limit (int | Unset): Limit rows (0 = all) Default: 0.
        offset (int | Unset):  Default: 0.
        sort_by (None | str | Unset):
        sort_order (str | Unset):  Default: 'asc'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        slug=slug,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    slug: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 0,
    offset: int | Unset = 0,
    sort_by: None | str | Unset = UNSET,
    sort_order: str | Unset = "asc",
) -> DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Get a dataset including its data matrix (sortable, paginated)

    Args:
        slug (str):
        limit (int | Unset): Limit rows (0 = all) Default: 0.
        offset (int | Unset):  Default: 0.
        sort_by (None | str | Unset):
        sort_order (str | Unset):  Default: 'asc'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DatasetDetailResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            slug=slug,
            client=client,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    ).parsed
