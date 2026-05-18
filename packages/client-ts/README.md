# @nousviz/client

Auto-generated TypeScript client for the [NousViz](https://nousviz.online) API.

Generated from `/openapi.json` via `openapi-typescript-codegen`. Do **not** edit
`src/generated/` by hand — re-run `scripts/regenerate-clients.sh` from the repo root.

## Install

```bash
npm install @nousviz/client
```

## Three-line example

```ts
import { createClient, AuthService, PluginsService } from "@nousviz/client";

createClient({ baseUrl: "https://nousviz.online", getToken: () => localStorage.getItem("token") ?? "" });

const me = await AuthService.authMe();
const plugins = await PluginsService.pluginsList();
```

## Auth

Pass a `getToken` callback. The client calls it per request and sets
`X-Session-Token: <returned-value>` if non-empty. Public endpoints
(`AuthService.authStatus()`, `HealthService.healthCheck()`) work
without a token.

## Operation naming

Every method is `<resource>.<verb>` from the platform's
`operationId` (B217). Examples:

| HTTP | Method |
|---|---|
| `GET /api/auth/me` | `AuthService.authMe()` |
| `GET /api/plugins` | `PluginsService.pluginsList()` |
| `POST /api/plugins/{id}/install` | `PluginsService.pluginsInstall({ pluginId, requestBody })` |
| `POST /api/auth/impersonate/{user_id}` | `AuthService.authImpersonateStart({ userId })` |

## Types

Every Pydantic response model is exported:

```ts
import type { MeResponse, PluginEntry, JobsListResponse } from "@nousviz/client";

const me: MeResponse = await AuthService.authMe();
```

See [`/docs/api`](https://nousviz.online/docs/api) for the live schema
panels and try-it-out form.

## Versioning

Each release of `@nousviz/client` matches the platform `VERSION`
file. Spec changes are PR-reviewable through the
`tests/test_openapi_stability.py` snapshot — when the snapshot
updates, regenerate the client in the same PR.
