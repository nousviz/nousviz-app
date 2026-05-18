from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.rbac_error_detail import RBACErrorDetail
from ...models.sync_schedule_body import SyncScheduleBody
from ...models.sync_schedule_set_response import SyncScheduleSetResponse
from ...types import Response


def _get_kwargs(
    plugin_id: str,
    *,
    body: SyncScheduleBody,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/plugins/{plugin_id}/sync-schedule".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse | None:
    if response.status_code == 200:
        response_200 = SyncScheduleSetResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncScheduleBody,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse]:
    r"""Write or clear the per-plugin schedule override

     Write a per-plugin schedule override.

    Body forms (mutually exclusive):
      {\"cron\": \"0 */12 * * *\"}                 raw cron
      {\"interval_value\": 15, \"interval_unit\": \"minutes\"}  friendly form
      {\"cron\": null} or {\"cron\": \"\"}           clear override

    The scheduler observes the change on its next poll (within ~30s).
    To make the change visible immediately, we delete the registry row;
    the scheduler re-creates it on next poll with the new effective cron.

    Args:
        plugin_id (str):
        body (SyncScheduleBody): Per-plugin schedule override.

            B148: cron=None or "" clears the override (falls back to manifest).
            B205 (v0.9.6): friendly form — supply interval_value + interval_unit
            instead of a raw cron expression. The two forms are mutually exclusive
            in a single request.

            Examples:
                {"cron": "*/15 * * * *"}                      raw cron
                {"interval_value": 15, "interval_unit": "minutes"}  friendly form
                {"cron": null}                                 clear override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncScheduleBody,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse | None:
    r"""Write or clear the per-plugin schedule override

     Write a per-plugin schedule override.

    Body forms (mutually exclusive):
      {\"cron\": \"0 */12 * * *\"}                 raw cron
      {\"interval_value\": 15, \"interval_unit\": \"minutes\"}  friendly form
      {\"cron\": null} or {\"cron\": \"\"}           clear override

    The scheduler observes the change on its next poll (within ~30s).
    To make the change visible immediately, we delete the registry row;
    the scheduler re-creates it on next poll with the new effective cron.

    Args:
        plugin_id (str):
        body (SyncScheduleBody): Per-plugin schedule override.

            B148: cron=None or "" clears the override (falls back to manifest).
            B205 (v0.9.6): friendly form — supply interval_value + interval_unit
            instead of a raw cron expression. The two forms are mutually exclusive
            in a single request.

            Examples:
                {"cron": "*/15 * * * *"}                      raw cron
                {"interval_value": 15, "interval_unit": "minutes"}  friendly form
                {"cron": null}                                 clear override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncScheduleBody,
) -> Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse]:
    r"""Write or clear the per-plugin schedule override

     Write a per-plugin schedule override.

    Body forms (mutually exclusive):
      {\"cron\": \"0 */12 * * *\"}                 raw cron
      {\"interval_value\": 15, \"interval_unit\": \"minutes\"}  friendly form
      {\"cron\": null} or {\"cron\": \"\"}           clear override

    The scheduler observes the change on its next poll (within ~30s).
    To make the change visible immediately, we delete the registry row;
    the scheduler re-creates it on next poll with the new effective cron.

    Args:
        plugin_id (str):
        body (SyncScheduleBody): Per-plugin schedule override.

            B148: cron=None or "" clears the override (falls back to manifest).
            B205 (v0.9.6): friendly form — supply interval_value + interval_unit
            instead of a raw cron expression. The two forms are mutually exclusive
            in a single request.

            Examples:
                {"cron": "*/15 * * * *"}                      raw cron
                {"interval_value": 15, "interval_unit": "minutes"}  friendly form
                {"cron": null}                                 clear override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: SyncScheduleBody,
) -> ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse | None:
    r"""Write or clear the per-plugin schedule override

     Write a per-plugin schedule override.

    Body forms (mutually exclusive):
      {\"cron\": \"0 */12 * * *\"}                 raw cron
      {\"interval_value\": 15, \"interval_unit\": \"minutes\"}  friendly form
      {\"cron\": null} or {\"cron\": \"\"}           clear override

    The scheduler observes the change on its next poll (within ~30s).
    To make the change visible immediately, we delete the registry row;
    the scheduler re-creates it on next poll with the new effective cron.

    Args:
        plugin_id (str):
        body (SyncScheduleBody): Per-plugin schedule override.

            B148: cron=None or "" clears the override (falls back to manifest).
            B205 (v0.9.6): friendly form — supply interval_value + interval_unit
            instead of a raw cron expression. The two forms are mutually exclusive
            in a single request.

            Examples:
                {"cron": "*/15 * * * *"}                      raw cron
                {"interval_value": 15, "interval_unit": "minutes"}  friendly form
                {"cron": null}                                 clear override

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | RBACErrorDetail | SyncScheduleSetResponse
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
            body=body,
        )
    ).parsed
