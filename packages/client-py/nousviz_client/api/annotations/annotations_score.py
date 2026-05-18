from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.annotation_score_response import AnnotationScoreResponse
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    annotation_id: str,
    *,
    score: str,
    note: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["score"] = score

    json_note: None | str | Unset
    if isinstance(note, Unset):
        json_note = UNSET
    else:
        json_note = note
    params["note"] = json_note

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/annotations/{annotation_id}/score".format(
            annotation_id=quote(str(annotation_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = AnnotationScoreResponse.from_dict(response.json())

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
) -> Response[AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
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
    score: str,
    note: None | str | Unset = UNSET,
) -> Response[AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Quick semantic score (useful | neutral | useless)

     Quick-score an annotation as useful / neutral / useless.

    Args:
        annotation_id (str):
        score (str):
        note (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        annotation_id=annotation_id,
        score=score,
        note=note,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    score: str,
    note: None | str | Unset = UNSET,
) -> AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Quick semantic score (useful | neutral | useless)

     Quick-score an annotation as useful / neutral / useless.

    Args:
        annotation_id (str):
        score (str):
        note (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return sync_detailed(
        annotation_id=annotation_id,
        client=client,
        score=score,
        note=note,
    ).parsed


async def asyncio_detailed(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    score: str,
    note: None | str | Unset = UNSET,
) -> Response[AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]:
    """Quick semantic score (useful | neutral | useless)

     Quick-score an annotation as useful / neutral / useless.

    Args:
        annotation_id (str):
        score (str):
        note (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        annotation_id=annotation_id,
        score=score,
        note=note,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    annotation_id: str,
    *,
    client: AuthenticatedClient | Client,
    score: str,
    note: None | str | Unset = UNSET,
) -> AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail | None:
    """Quick semantic score (useful | neutral | useless)

     Quick-score an annotation as useful / neutral / useless.

    Args:
        annotation_id (str):
        score (str):
        note (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        AnnotationScoreResponse | ErrorDetail | HTTPValidationError | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            annotation_id=annotation_id,
            client=client,
            score=score,
            note=note,
        )
    ).parsed
