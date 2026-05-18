# core/

Shared domain models and utilities for NousViz.

## Contract

`core/` contains code that is **imported by more than one app** and has **no app-specific dependencies** — no FastAPI, no Vite, no CLI.

```
apps/api/src/routes/auth.py       imports → core/connections/manager.py
apps/api/src/routes/sync.py       imports → core/connections/manager.py
apps/worker/src/run_alerts.py     imports → core/connections/manager.py
apps/mcp/src/main.py              imports → core/connections/manager.py
plugins/*/src/sync.py             imports → core/connections/manager.py (via nousviz_sdk)
```

## What belongs here

| Component | Module | Consumers |
|-----------|--------|-----------|
| Annotation domain models | `core/annotations/models.py` | API, worker, MCP |
| Credential encryption | `core/connections/encryption.py` | API, worker, sync scripts |
| Credential manager | `core/connections/manager.py` | API, worker, sync scripts |

## What does NOT belong here

- FastAPI route handlers → `apps/api/src/routes/`
- React components → `apps/web/src/`
- Plugin-specific logic → `plugins/<slug>/`
- Features only used by the API (fusions, alerts, insights) → `apps/api/src/routes/`
- Features only used by the worker → `apps/worker/src/`

## Contents

```
core/
├── annotations/
│   ├── __init__.py
│   └── models.py          — Annotation, AnnotationSource, AnnotationCategory, AnnotationSeverity
└── connections/
    ├── __init__.py
    ├── encryption.py      — AES-256-GCM encrypt/decrypt (NOUSVIZ_ENCRYPTION_KEY)
    ├── manager.py         — CredentialManager: store/retrieve/audit/rotate credentials
    └── models.py          — Connection, Credential, ConnectionStatus, CredentialType
```

## Adding to core/

Only add a module to `core/` if **all three** conditions are true:

1. It is used by two or more of: `apps/api`, `apps/worker`, `apps/mcp`, plugin sync scripts
2. It has no dependency on FastAPI, uvicorn, React, or any other app-layer framework
3. It models a domain concept that is genuinely shared (not just convenient to import)

If only one app uses it, put it in that app's directory. If it's plugin-specific, put it in the plugin.
