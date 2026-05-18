from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.dataport_tab_rows_response import DataportTabRowsResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    plugin_slug: str,
    tab_id: str,
    *,
    page: int | Unset = 1,
    page_size: int | Unset = 50,
    sort: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page"] = page

    params["page_size"] = page_size

    json_sort: None | str | Unset
    if isinstance(sort, Unset):
        json_sort = UNSET
    else:
        json_sort = sort
    params["sort"] = json_sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/data-port/plugins/{plugin_slug}/tab/{tab_id}".format(
            plugin_slug=quote(str(plugin_slug), safe=""),
            tab_id=quote(str(tab_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = DataportTabRowsResponse.from_dict(response.json())

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
) -> Response[DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_slug: str,
    tab_id: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    page_size: int | Unset = 50,
    sort: None | str | Unset = UNSET,
) -> Response[DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Paginated rows from a dataport tab's declared table

     Query a plugin's dataport tab directly from its declared table.

    Sort/filter validation: column names and filter keys must appear in
    the plugin's `dataport.yaml`; any other keys are silently dropped.
    Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
    on every column reference (S106).

    Args:
        plugin_slug (str):
        tab_id (str):
        page (int | Unset):  Default: 1.
        page_size (int | Unset):  Default: 50.
        sort (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_slug=plugin_slug,
        tab_id=tab_id,
        page=page,
        page_size=page_size,
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_slug: str,
    tab_id: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    page_size: int | Unset = 50,
    sort: None | str | Unset = UNSET,
) -> DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Paginated rows from a dataport tab's declared table

     Query a plugin's dataport tab directly from its declared table.

    Sort/filter validation: column names and filter keys must appear in
    the plugin's `dataport.yaml`; any other keys are silently dropped.
    Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
    on every column reference (S106).

    Args:
        plugin_slug (str):
        tab_id (str):
        page (int | Unset):  Default: 1.
        page_size (int | Unset):  Default: 50.
        sort (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        plugin_slug=plugin_slug,
        tab_id=tab_id,
        client=client,
        page=page,
        page_size=page_size,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    plugin_slug: str,
    tab_id: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    page_size: int | Unset = 50,
    sort: None | str | Unset = UNSET,
) -> Response[DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Paginated rows from a dataport tab's declared table

     Query a plugin's dataport tab directly from its declared table.

    Sort/filter validation: column names and filter keys must appear in
    the plugin's `dataport.yaml`; any other keys are silently dropped.
    Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
    on every column reference (S106).

    Args:
        plugin_slug (str):
        tab_id (str):
        page (int | Unset):  Default: 1.
        page_size (int | Unset):  Default: 50.
        sort (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_slug=plugin_slug,
        tab_id=tab_id,
        page=page,
        page_size=page_size,
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_slug: str,
    tab_id: str,
    *,
    client: AuthenticatedClient | Client,
    page: int | Unset = 1,
    page_size: int | Unset = 50,
    sort: None | str | Unset = UNSET,
) -> DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Paginated rows from a dataport tab's declared table

     Query a plugin's dataport tab directly from its declared table.

    Sort/filter validation: column names and filter keys must appear in
    the plugin's `dataport.yaml`; any other keys are silently dropped.
    Sort direction must be ASC or DESC. Defense-in-depth via Identifier()
    on every column reference (S106).

    Args:
        plugin_slug (str):
        tab_id (str):
        page (int | Unset):  Default: 1.
        page_size (int | Unset):  Default: 50.
        sort (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DataportTabRowsResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_slug=plugin_slug,
            tab_id=tab_id,
            client=client,
            page=page,
            page_size=page_size,
            sort=sort,
        )
    ).parsed
