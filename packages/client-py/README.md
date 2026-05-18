# nousviz-client

Auto-generated Python client for the [NousViz](https://nousviz.online) API.

Generated from `/openapi.json` via `openapi-python-client`. Do **not** edit
`nousviz_client/` by hand — re-run `scripts/regenerate-clients.sh` from the
repo root.

> **Distinct from** `nousviz_sdk` (the plugin SDK that runs *inside*
> NousViz). This package is for **external integrations** that talk to a
> NousViz instance over HTTP.

## Install

```bash
pip install nousviz-client
```

## Three-line example

```python
from nousviz_client import AuthenticatedClient
from nousviz_client.api.auth import auth_me
from nousviz_client.api.plugins import plugins_list

client = AuthenticatedClient(base_url="https://nousviz.online", token="<your-session-token>")
me = auth_me.sync(client=client)
plugins = plugins_list.sync(client=client)
```

For unauthenticated calls (public endpoints like `/api/health`), use
`Client` instead of `AuthenticatedClient`:

```python
from nousviz_client import Client
from nousviz_client.api.health import health_check

client = Client(base_url="https://nousviz.online")
status = health_check.sync(client=client)
```

## Auth

`AuthenticatedClient(token=...)` sets the `X-Session-Token` header on
every request. Issue a session token via `POST /api/auth/login`:

```python
from nousviz_client import Client
from nousviz_client.api.auth import auth_login
from nousviz_client.models import LoginRequest

client = Client(base_url="https://nousviz.online")
resp = auth_login.sync(client=client, body=LoginRequest(email="me@example.com", password="..."))
print(resp.token)  # → "abc123..."
```

## Operation naming

Every endpoint module is `nousviz_client.api.<tag>.<resource_verb>`:

| HTTP | Module |
|---|---|
| `GET /api/auth/me` | `nousviz_client.api.auth.auth_me` |
| `GET /api/plugins` | `nousviz_client.api.plugins.plugins_list` |
| `POST /api/plugins/{id}/install` | `nousviz_client.api.plugins.plugins_install` |
| `POST /api/auth/impersonate/{user_id}` | `nousviz_client.api.auth.auth_impersonate_start` |

Each module exposes:
- `sync(client, ...)` — synchronous request, returns the parsed response.
- `asyncio(client, ...)` — async via httpx.AsyncClient.
- `sync_detailed(client, ...)` / `asyncio_detailed(client, ...)` —
  return the full `Response[T]` wrapper with status code + headers.

## Types

Every Pydantic response model is exported from `nousviz_client.models`:

```python
from nousviz_client.models import MeResponse, PluginEntry, JobsListResponse
```

See [`/docs/api`](https://nousviz.online/docs/api) for the live schema
panels and try-it-out form.

## Versioning

Each release of `nousviz-client` matches the platform `VERSION` file.
Spec changes are PR-reviewable through the OpenAPI snapshot test
(`tests/test_openapi_stability.py`) — when the snapshot updates,
regenerate the client in the same PR.
