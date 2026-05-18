from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.annotation_delete_response import AnnotationDeleteResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    annotation_id: str,
    *,
    permanent: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["permanent"] = permanent

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/annotations/{annotation_id}".format(
            annotation_id=quote(str(annotation_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AnnotationDeleteResponse.from_dict(response.json())

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
) -> Response[AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    permanent: bool | Unset = False,
) -> Response[AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Delete an annotation (soft by default; permanent=true to hard-delete)

    Args:
        annotation_id (str):
        permanent (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        annotation_id=annotation_id,
        permanent=permanent,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    permanent: bool | Unset = False,
) -> AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Delete an annotation (soft by default; permanent=true to hard-delete)

    Args:
        annotation_id (str):
        permanent (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        annotation_id=annotation_id,
        client=client,
        permanent=permanent,
    ).parsed


async def asyncio_detailed(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    permanent: bool | Unset = False,
) -> Response[AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Delete an annotation (soft by default; permanent=true to hard-delete)

    Args:
        annotation_id (str):
        permanent (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        annotation_id=annotation_id,
        permanent=permanent,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    permanent: bool | Unset = False,
) -> AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Delete an annotation (soft by default; permanent=true to hard-delete)

    Args:
        annotation_id (str):
        permanent (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationDeleteResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            annotation_id=annotation_id,
            client=client,
            permanent=permanent,
        )
    ).parsed
