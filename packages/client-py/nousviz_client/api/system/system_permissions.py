from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_detail import ErrorDetail
from ...models.permissions_matrix_response import PermissionsMatrixResponse
from ...models.rbac_error_detail import RBACErrorDetail
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/system/permissions",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail | None:
    if response.status_code == 200:
        response_200 = PermissionsMatrixResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDetail.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = RBACErrorDetail.from_dict(response.json())

        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail]:
    r"""Full RBAC matrix snapshot for /system/permissions

     Full RBAC registry snapshot for the audit matrix UI.

    Response shape:
    {
      \"permissions\": {
        \"<name>\": {\"description\": \"...\", \"sensitive\": bool}
      },
      \"roles\": {
        \"<role>\": [\"<permission>\", ...]
      },
      \"routes\": [
        {
          \"method\": \"GET\",
          \"path\": \"/api/...\",
          \"permission\": \"plugins.read\",
          \"is_plugin_route\": bool,
          \"is_plugin_default\": bool,
          \"last_accessed\": {
            \"viewer\": \"<iso ts>\" | null,
            \"analyst\": \"<iso ts>\" | null,
            ...
          }
        }
      ],
      \"public_routes\": [[\"GET\", \"/api/health\"], ...],
      \"audit_summary\": {
        \"window_hours\": 24,
        \"decisions\": {\"allow\": N, \"deny\": M, \"shadow_mismatch\": K},
        \"top_denials\": [{\"permission\": \"...\", \"count\": N}, ...]
      },
      \"shadow_mode\": bool,
      \"version\": \"0.9.8.3\"
    }

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail | None:
    r"""Full RBAC matrix snapshot for /system/permissions

     Full RBAC registry snapshot for the audit matrix UI.

    Response shape:
    {
      \"permissions\": {
        \"<name>\": {\"description\": \"...\", \"sensitive\": bool}
      },
      \"roles\": {
        \"<role>\": [\"<permission>\", ...]
      },
      \"routes\": [
        {
          \"method\": \"GET\",
          \"path\": \"/api/...\",
          \"permission\": \"plugins.read\",
          \"is_plugin_route\": bool,
          \"is_plugin_default\": bool,
          \"last_accessed\": {
            \"viewer\": \"<iso ts>\" | null,
            \"analyst\": \"<iso ts>\" | null,
            ...
          }
        }
      ],
      \"public_routes\": [[\"GET\", \"/api/health\"], ...],
      \"audit_summary\": {
        \"window_hours\": 24,
        \"decisions\": {\"allow\": N, \"deny\": M, \"shadow_mismatch\": K},
        \"top_denials\": [{\"permission\": \"...\", \"count\": N}, ...]
      },
      \"shadow_mode\": bool,
      \"version\": \"0.9.8.3\"
    }

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail]:
    r"""Full RBAC matrix snapshot for /system/permissions

     Full RBAC registry snapshot for the audit matrix UI.

    Response shape:
    {
      \"permissions\": {
        \"<name>\": {\"description\": \"...\", \"sensitive\": bool}
      },
      \"roles\": {
        \"<role>\": [\"<permission>\", ...]
      },
      \"routes\": [
        {
          \"method\": \"GET\",
          \"path\": \"/api/...\",
          \"permission\": \"plugins.read\",
          \"is_plugin_route\": bool,
          \"is_plugin_default\": bool,
          \"last_accessed\": {
            \"viewer\": \"<iso ts>\" | null,
            \"analyst\": \"<iso ts>\" | null,
            ...
          }
        }
      ],
      \"public_routes\": [[\"GET\", \"/api/health\"], ...],
      \"audit_summary\": {
        \"window_hours\": 24,
        \"decisions\": {\"allow\": N, \"deny\": M, \"shadow_mismatch\": K},
        \"top_denials\": [{\"permission\": \"...\", \"count\": N}, ...]
      },
      \"shadow_mode\": bool,
      \"version\": \"0.9.8.3\"
    }

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail | None:
    r"""Full RBAC matrix snapshot for /system/permissions

     Full RBAC registry snapshot for the audit matrix UI.

    Response shape:
    {
      \"permissions\": {
        \"<name>\": {\"description\": \"...\", \"sensitive\": bool}
      },
      \"roles\": {
        \"<role>\": [\"<permission>\", ...]
      },
      \"routes\": [
        {
          \"method\": \"GET\",
          \"path\": \"/api/...\",
          \"permission\": \"plugins.read\",
          \"is_plugin_route\": bool,
          \"is_plugin_default\": bool,
          \"last_accessed\": {
            \"viewer\": \"<iso ts>\" | null,
            \"analyst\": \"<iso ts>\" | null,
            ...
          }
        }
      ],
      \"public_routes\": [[\"GET\", \"/api/health\"], ...],
      \"audit_summary\": {
        \"window_hours\": 24,
        \"decisions\": {\"allow\": N, \"deny\": M, \"shadow_mismatch\": K},
        \"top_denials\": [{\"permission\": \"...\", \"count\": N}, ...]
      },
      \"shadow_mode\": bool,
      \"version\": \"0.9.8.3\"
    }

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDetail | PermissionsMatrixResponse | RBACErrorDetail
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
