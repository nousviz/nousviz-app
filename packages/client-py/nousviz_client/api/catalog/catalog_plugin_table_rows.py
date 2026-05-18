from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.catalog_table_rows_response import CatalogTableRowsResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    plugin_id: str,
    table_name: str,
    *,
    page: int | Unset = 1,
    limit: int | Unset = 50,
    sort: None | str | Unset = UNSET,
    q: None | str | Unset = UNSET,
    filter_: list[str] | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page"] = page

    params["limit"] = limit

    json_sort: None | str | Unset
    if isinstance(sort, Unset):
        json_sort = UNSET
    else:
        json_sort = sort
    params["sort"] = json_sort

    json_q: None | str | Unset
    if isinstance(q, Unset):
        json_q = UNSET
    else:
        json_q = q
    params["q"] = json_q

    json_filter_: list[str] | Unset = UNSET
    if not isinstance(filter_, Unset):
        json_filter_ = filter_

    params["filter"] = json_filter_

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/plugins/{plugin_id}/tables/{table_name}/rows".format(
            plugin_id=quote(str(plugin_id), safe=""),
            table_name=quote(str(table_name), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = CatalogTableRowsResponse.from_dict(response.json())

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

    if response.status_code == 500:
        response_500 = ErrorDetail.from_dict(response.json())

        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    limit: int | Unset = 50,
    sort: None | str | Unset = UNSET,
    q: None | str | Unset = UNSET,
    filter_: list[str] | Unset = UNSET,
) -> Response[CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    r"""Paginated rows from a discovered plugin table (B262: server-side filters + search)

     Paginated rows from a discovered plugin table.

    The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
    Works for every plugin's every granted table — no `dataport.yaml`
    opt-in required.

    `sort` accepts \"column\" or \"column desc\" / \"column asc\". Invalid
    sort (column not in table) is silently dropped (no-sort fallback)
    rather than 400-erroring; pagination still works.

    `q` is a server-side substring search. Casts text-coercible columns
    to text and matches via ILIKE. Empty q is treated as no q.

    `filter` is repeatable. Each value is `col:op:value` (or
    `col:is_null` / `col:not_null` for null checks). Filters AND together;
    the response's `total` reflects the filtered count.

    Response:
        {
          \"rows\": [{...}, {...}, ...],
          \"total\": 7068,    # filtered count when q/filter present
          \"page\": 1,
          \"limit\": 50
        }

    Args:
        plugin_id (str):
        table_name (str):
        page (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.
        sort (None | str | Unset):
        q (None | str | Unset): Full-dataset substring search (B262). Matches via ILIKE %q% across
            text-coercible columns (text, varchar, json, jsonb, uuid). Capped at 100 characters.
        filter_ (list[str] | Unset): Per-column predicate filter (B262). Repeatable. Each filter
            is `col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, startswith, is_null,
            not_null. Up to 8 per request. Filters compose with AND.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        table_name=table_name,
        page=page,
        limit=limit,
        sort=sort,
        q=q,
        filter_=filter_,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    limit: int | Unset = 50,
    sort: None | str | Unset = UNSET,
    q: None | str | Unset = UNSET,
    filter_: list[str] | Unset = UNSET,
) -> CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    r"""Paginated rows from a discovered plugin table (B262: server-side filters + search)

     Paginated rows from a discovered plugin table.

    The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
    Works for every plugin's every granted table — no `dataport.yaml`
    opt-in required.

    `sort` accepts \"column\" or \"column desc\" / \"column asc\". Invalid
    sort (column not in table) is silently dropped (no-sort fallback)
    rather than 400-erroring; pagination still works.

    `q` is a server-side substring search. Casts text-coercible columns
    to text and matches via ILIKE. Empty q is treated as no q.

    `filter` is repeatable. Each value is `col:op:value` (or
    `col:is_null` / `col:not_null` for null checks). Filters AND together;
    the response's `total` reflects the filtered count.

    Response:
        {
          \"rows\": [{...}, {...}, ...],
          \"total\": 7068,    # filtered count when q/filter present
          \"page\": 1,
          \"limit\": 50
        }

    Args:
        plugin_id (str):
        table_name (str):
        page (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.
        sort (None | str | Unset):
        q (None | str | Unset): Full-dataset substring search (B262). Matches via ILIKE %q% across
            text-coercible columns (text, varchar, json, jsonb, uuid). Capped at 100 characters.
        filter_ (list[str] | Unset): Per-column predicate filter (B262). Repeatable. Each filter
            is `col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, startswith, is_null,
            not_null. Up to 8 per request. Filters compose with AND.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        table_name=table_name,
        client=client,
        page=page,
        limit=limit,
        sort=sort,
        q=q,
        filter_=filter_,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    limit: int | Unset = 50,
    sort: None | str | Unset = UNSET,
    q: None | str | Unset = UNSET,
    filter_: list[str] | Unset = UNSET,
) -> Response[CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    r"""Paginated rows from a discovered plugin table (B262: server-side filters + search)

     Paginated rows from a discovered plugin table.

    The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
    Works for every plugin's every granted table — no `dataport.yaml`
    opt-in required.

    `sort` accepts \"column\" or \"column desc\" / \"column asc\". Invalid
    sort (column not in table) is silently dropped (no-sort fallback)
    rather than 400-erroring; pagination still works.

    `q` is a server-side substring search. Casts text-coercible columns
    to text and matches via ILIKE. Empty q is treated as no q.

    `filter` is repeatable. Each value is `col:op:value` (or
    `col:is_null` / `col:not_null` for null checks). Filters AND together;
    the response's `total` reflects the filtered count.

    Response:
        {
          \"rows\": [{...}, {...}, ...],
          \"total\": 7068,    # filtered count when q/filter present
          \"page\": 1,
          \"limit\": 50
        }

    Args:
        plugin_id (str):
        table_name (str):
        page (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.
        sort (None | str | Unset):
        q (None | str | Unset): Full-dataset substring search (B262). Matches via ILIKE %q% across
            text-coercible columns (text, varchar, json, jsonb, uuid). Capped at 100 characters.
        filter_ (list[str] | Unset): Per-column predicate filter (B262). Repeatable. Each filter
            is `col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, startswith, is_null,
            not_null. Up to 8 per request. Filters compose with AND.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        table_name=table_name,
        page=page,
        limit=limit,
        sort=sort,
        q=q,
        filter_=filter_,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    table_name: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    limit: int | Unset = 50,
    sort: None | str | Unset = UNSET,
    q: None | str | Unset = UNSET,
    filter_: list[str] | Unset = UNSET,
) -> CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    r"""Paginated rows from a discovered plugin table (B262: server-side filters + search)

     Paginated rows from a discovered plugin table.

    The catalog-driven replacement for /api/data-port/plugins/:slug/tab/:tabId.
    Works for every plugin's every granted table — no `dataport.yaml`
    opt-in required.

    `sort` accepts \"column\" or \"column desc\" / \"column asc\". Invalid
    sort (column not in table) is silently dropped (no-sort fallback)
    rather than 400-erroring; pagination still works.

    `q` is a server-side substring search. Casts text-coercible columns
    to text and matches via ILIKE. Empty q is treated as no q.

    `filter` is repeatable. Each value is `col:op:value` (or
    `col:is_null` / `col:not_null` for null checks). Filters AND together;
    the response's `total` reflects the filtered count.

    Response:
        {
          \"rows\": [{...}, {...}, ...],
          \"total\": 7068,    # filtered count when q/filter present
          \"page\": 1,
          \"limit\": 50
        }

    Args:
        plugin_id (str):
        table_name (str):
        page (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.
        sort (None | str | Unset):
        q (None | str | Unset): Full-dataset substring search (B262). Matches via ILIKE %q% across
            text-coercible columns (text, varchar, json, jsonb, uuid). Capped at 100 characters.
        filter_ (list[str] | Unset): Per-column predicate filter (B262). Repeatable. Each filter
            is `col:op:value`. Operators: eq, neq, gt, lt, gte, lte, contains, startswith, is_null,
            not_null. Up to 8 per request. Filters compose with AND.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogTableRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            table_name=table_name,
            client=client,
            page=page,
            limit=limit,
            sort=sort,
            q=q,
            filter_=filter_,
        )
    ).parsed
