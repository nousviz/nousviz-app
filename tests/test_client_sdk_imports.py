"""B246 (v0.9.10.5): smoke test that the generated Python client imports.

Confirms the package is well-formed:
- Top-level Client + AuthenticatedClient classes exist.
- At least a handful of api.<tag> modules + functions exist.
- At least a handful of model classes exist.

This test imports from the on-disk source tree (`packages/client-py/`)
without requiring an install — sets sys.path manually.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY_PKG_ROOT = REPO / "packages" / "client-py"


def test_client_classes_importable():
    if str(PY_PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PY_PKG_ROOT))

    from nousviz_client import Client, AuthenticatedClient

    # Smoke-construct each. AuthenticatedClient requires a token kwarg.
    c1 = Client(base_url="https://nousviz.online")
    c2 = AuthenticatedClient(base_url="https://nousviz.online", token="t")
    assert c1 is not None
    assert c2 is not None


def test_api_modules_importable():
    """Spot-check API endpoint modules — one per tag."""
    if str(PY_PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PY_PKG_ROOT))

    from nousviz_client.api.auth import auth_me, auth_login
    from nousviz_client.api.plugins import plugins_list, plugins_install
    from nousviz_client.api.health import health_check
    from nousviz_client.api.system import system_permissions

    # Each module exposes a `sync` function (may also expose asyncio).
    for mod in (auth_me, auth_login, plugins_list, plugins_install, health_check, system_permissions):
        assert callable(getattr(mod, "sync", None)), f"{mod.__name__} missing sync()"


def test_models_importable():
    """Spot-check model classes."""
    if str(PY_PKG_ROOT) not in sys.path:
        sys.path.insert(0, str(PY_PKG_ROOT))

    from nousviz_client.models import (
        MeResponse,
        PluginEntry,
        HealthResponse,
        LoginRequest,
        LoginResponse,
    )

    assert all(cls is not None for cls in (
        MeResponse, PluginEntry, HealthResponse, LoginRequest, LoginResponse,
    ))
