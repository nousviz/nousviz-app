# API Reference

NousViz exposes its operator-facing API as an OpenAPI 3.x spec, generated
directly from the live FastAPI route definitions. The spec always reflects
running code — never out of sync.

## Where to read the spec

| URL | What | Best for |
|---|---|---|
| `/docs/api` | Interactive native reference (NousViz UI) | Operators reading + browsing |
| `/openapi.json` | Raw spec, JSON | Tooling, generated SDK clients |
| `/openapi.yaml` | Same spec, YAML-encoded | LLM context (more token-efficient), PR diffs |

The canonical URL is **`/docs/api`** — that's what Settings → Documentation
links to and what new operators should bookmark. Built with NousViz primitives
(replaces the v0.9.7.0 Scalar widget — see CHANGELOG v0.9.7.1).

## What's documented

The spec covers the **platform's** core API — every handler in
`apps/api/src/routes/*.py`. As of v0.9.7.0:

- All 23 router groups have explicit tags with descriptions
- `X-Session-Token` and `X-API-Key` security schemes are declared
- Production and local-dev `servers` are listed for spec consumers

What's **not** in v0.9.7.1:

- Most schema panels show "no schema declared" — handlers still return
  `dict` instead of typed Pydantic models. Fixed incrementally in
  v0.9.7.2 (top 50 routes) and v0.9.7.3 (remaining 102).
- `Field(description=...)` polish on every model — v0.9.7.4.
- Stable `operationId` for client SDK generation — v0.9.7.4.
- Interactive try-it-out — v0.9.7.4 (the native page reserves a
  curl-example placeholder until then).

See the [v0.9.7 master plan](../todo/0.9.7/v0.9.7-master-plan.md) for the
full sequence.

## The three layers

NousViz has three API surfaces with different visibility rules:

| Layer | Source | Visibility | Documented at |
|---|---|---|---|
| **Core platform API** | `apps/api/src/routes/*.py` | Public | This spec / `/docs/api` |
| **Python SDK** | `sdk/nousviz_sdk/*.py` | Public — for plugin authors | `docs/sdk-reference.md` *(arrives in v0.9.7.4)* |
| **Plugin-defined HTTP routes** | `plugins/installed/<slug>/api/routes.py` | **Default private**; opt-in per plugin | Plugin's own docs |

### Plugin routes

Plugins can register their own HTTP routes that get mounted onto the same
FastAPI app. As of v0.9.7.0, these are **private by default** — they don't
appear in `/openapi.json` or in the API reference UI. Plugin authors who want
their routes documented in the platform's public spec opt in by adding to
their `plugin.yaml`:

```yaml
openapi_public: true
```

When set, all routers the plugin registers (main, extra, widget, module)
appear in the public spec. See
[contributing-a-plugin.md → Public API documentation](contributing-a-plugin.md#public-api-documentation-opt-in)
for details.

## Authentication

Most endpoints require an `X-Session-Token` header. Get one via:

```bash
curl -X POST https://nousviz.online/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "...", "password": "..."}'
```

Use the returned `token` in subsequent requests:

```bash
curl https://nousviz.online/api/plugins \
     -H "X-Session-Token: <token>"
```

Some endpoints accept `X-API-Key` instead — these are issued in
**Settings → API Keys** for programmatic / scripted access.

The native reference at `/docs/api` shows a curl example you can run
locally with your session token. Interactive in-browser try-it-out
arrives in v0.9.7.4.

## How tooling / LLMs should consume the spec

For LLMs that need API context: fetch `/openapi.yaml` (token-efficient).
The spec includes:

- All paths, methods, and parameters
- Authentication requirements per endpoint (via security schemes)
- Tag groupings to navigate the surface
- For v0.9.7.2+, response schemas (Pydantic-derived) for typed access

For client SDK generation: feed `/openapi.json` to
[openapi-generator](https://openapi-generator.tech/) or similar. Stable
`operationId` arrives in v0.9.7.4, so generated clients before then will
have function names that may shift on future refactors. Pin to the spec
version you generated against.

## Versioning

The platform is pre-1.0. Breaking changes are documented in the
[CHANGELOG](../CHANGELOG.md). There's no formal versioned-URL contract
yet (`/api/v1/...` etc.); the spec at any moment reflects current behavior.
