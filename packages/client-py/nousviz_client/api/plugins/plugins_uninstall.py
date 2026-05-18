from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.http_validation_error import HTTPValidationError
from ...models.plugin_uninstall_response import PluginUninstallResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import UNSET, Response, Unset


def _get_kwargs(
    plugin_id: str,
    *,
    remove_data: bool | Unset = False,
    remove_references: bool | Unset = False,
    cascade: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["remove_data"] = remove_data

    params["remove_references"] = remove_references

    params["cascade"] = cascade

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/plugins/{plugin_id}/install".format(
            plugin_id=quote(str(plugin_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PluginUninstallResponse.from_dict(response.json())

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
) -> Response[ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail]:
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
    remove_data: bool | Unset = False,
    remove_references: bool | Unset = False,
    cascade: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail]:
    """Uninstall a plugin (with optional dependent cascade)

     Uninstall a plugin.

    - remove_data=true: run down migrations to drop plugin tables before removal
    - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
      references — delete annotations pinned to the plugin, delete
      shares pointing at /plugin/<id>/*, strip the plugin slug from
      fusion `requires` arrays. Alert rules are left alone (Phase 2).
    - cascade=true: also uninstall all plugins that depend on this one

    Returns has_dependents status if dependents exist and cascade=false —
    the frontend should prompt the user to confirm cascade or cancel.

    Args:
        plugin_id (str):
        remove_data (bool | Unset):  Default: False.
        remove_references (bool | Unset):  Default: False.
        cascade (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        remove_data=remove_data,
        remove_references=remove_references,
        cascade=cascade,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    remove_data: bool | Unset = False,
    remove_references: bool | Unset = False,
    cascade: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail | None:
    """Uninstall a plugin (with optional dependent cascade)

     Uninstall a plugin.

    - remove_data=true: run down migrations to drop plugin tables before removal
    - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
      references — delete annotations pinned to the plugin, delete
      shares pointing at /plugin/<id>/*, strip the plugin slug from
      fusion `requires` arrays. Alert rules are left alone (Phase 2).
    - cascade=true: also uninstall all plugins that depend on this one

    Returns has_dependents status if dependents exist and cascade=false —
    the frontend should prompt the user to confirm cascade or cancel.

    Args:
        plugin_id (str):
        remove_data (bool | Unset):  Default: False.
        remove_references (bool | Unset):  Default: False.
        cascade (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail
    """

    return sync_detailed(
        plugin_id=plugin_id,
        client=client,
        remove_data=remove_data,
        remove_references=remove_references,
        cascade=cascade,
    ).parsed


async def asyncio_detailed(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    remove_data: bool | Unset = False,
    remove_references: bool | Unset = False,
    cascade: bool | Unset = False,
) -> Response[ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail]:
    """Uninstall a plugin (with optional dependent cascade)

     Uninstall a plugin.

    - remove_data=true: run down migrations to drop plugin tables before removal
    - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
      references — delete annotations pinned to the plugin, delete
      shares pointing at /plugin/<id>/*, strip the plugin slug from
      fusion `requires` arrays. Alert rules are left alone (Phase 2).
    - cascade=true: also uninstall all plugins that depend on this one

    Returns has_dependents status if dependents exist and cascade=false —
    the frontend should prompt the user to confirm cascade or cancel.

    Args:
        plugin_id (str):
        remove_data (bool | Unset):  Default: False.
        remove_references (bool | Unset):  Default: False.
        cascade (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs(
        plugin_id=plugin_id,
        remove_data=remove_data,
        remove_references=remove_references,
        cascade=cascade,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    plugin_id: str,
    *,
    client: AuthenticatedClient | Client,
    remove_data: bool | Unset = False,
    remove_references: bool | Unset = False,
    cascade: bool | Unset = False,
) -> ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail | None:
    """Uninstall a plugin (with optional dependent cascade)

     Uninstall a plugin.

    - remove_data=true: run down migrations to drop plugin tables before removal
    - remove_references=true (B281, v0.9.11.21): auto-clean orphaned
      references — delete annotations pinned to the plugin, delete
      shares pointing at /plugin/<id>/*, strip the plugin slug from
      fusion `requires` arrays. Alert rules are left alone (Phase 2).
    - cascade=true: also uninstall all plugins that depend on this one

    Returns has_dependents status if dependents exist and cascade=false —
    the frontend should prompt the user to confirm cascade or cancel.

    Args:
        plugin_id (str):
        remove_data (bool | Unset):  Default: False.
        remove_references (bool | Unset):  Default: False.
        cascade (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | HTTPValidationError | PluginUninstallResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            plugin_id=plugin_id,
            client=client,
            remove_data=remove_data,
            remove_references=remove_references,
            cascade=cascade,
        )
    ).parsed
