"""B156 (v0.9.4.7): widget-runtime React shim tests.

Verifies the host-served React shim that plugin widgets alias to during
their esbuild step. The shim resolves the dual-instance hooks bug
(`Cannot read properties of null (reading 'useState')`) that v0.9.4.5's
"bundle React per widget" advice caused.

These tests exercise the route-level contract: the shim is served, has
the expected exports, has correct cache headers. They do NOT execute
the JavaScript — that requires a browser environment, covered by the
fixture-widget integration test in apps/web during deploy verification.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from apps.api.src.main import app
    return TestClient(app)


# ── React shim endpoint ──────────────────────────────────────────────


def test_react_shim_served_with_js_content_type(client):
    res = client.get("/api/widget-runtime/react.js")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/javascript")


def test_react_shim_exports_hooks(client):
    """Plugin widgets need useState, useEffect, etc. The shim must
    re-export every hook so any import { useState } from "react" resolves."""
    res = client.get("/api/widget-runtime/react.js")
    body = res.text
    # Hooks plugin authors are likely to use
    for hook in [
        "useState", "useEffect", "useLayoutEffect", "useRef",
        "useMemo", "useCallback", "useContext", "useReducer",
    ]:
        assert f"export const {hook}" in body, f"shim is missing export: {hook}"


def test_react_shim_exports_component_primitives(client):
    """forwardRef, memo, lazy, createContext are common in component libraries."""
    res = client.get("/api/widget-runtime/react.js")
    body = res.text
    for prim in ["forwardRef", "memo", "lazy", "createContext", "Fragment", "Suspense"]:
        assert f"export const {prim}" in body, f"shim is missing export: {prim}"


def test_react_shim_has_default_export(client):
    """Some bundlers emit `import React from "react"` — the shim provides
    a default export pointing at the full React object."""
    res = client.get("/api/widget-runtime/react.js")
    assert "export default" in res.text


def test_react_shim_reads_window_nousviz_react(client):
    """The shim's body must reference window.NousViz.React so it can re-export
    the host's copy. If this regresses (someone factors out the indirection),
    plugin widgets will fail at runtime."""
    res = client.get("/api/widget-runtime/react.js")
    assert "window.NousViz" in res.text
    assert "React" in res.text


def test_react_shim_throws_when_window_not_published(client):
    """If a plugin widget's bundle is loaded BEFORE the host publishes
    window.NousViz.React, the shim must throw with an actionable message
    rather than silently returning undefined.exports."""
    res = client.get("/api/widget-runtime/react.js")
    body = res.text
    assert "throw new Error" in body
    assert "window.NousViz.React not published" in body


def test_react_shim_has_cache_headers(client):
    """1h cache is reasonable — shim contents only change on host release.
    Without cache, every widget mount triggers a re-fetch."""
    res = client.get("/api/widget-runtime/react.js")
    cc = res.headers.get("cache-control", "")
    assert "max-age" in cc


# ── jsx-runtime shim endpoint ────────────────────────────────────────


def test_jsx_runtime_shim_served(client):
    res = client.get("/api/widget-runtime/react-jsx-runtime.js")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/javascript")


def test_jsx_runtime_shim_exports_jsx_apis(client):
    """esbuild --jsx=automatic emits imports of jsx, jsxs, jsxDEV, Fragment.
    The shim must export each."""
    res = client.get("/api/widget-runtime/react-jsx-runtime.js")
    body = res.text
    for sym in ["jsx", "jsxs", "Fragment"]:
        assert f"export const {sym}" in body, f"jsx-runtime shim missing: {sym}"


def test_jsx_runtime_shim_reads_window_nousviz_jsx_runtime(client):
    res = client.get("/api/widget-runtime/react-jsx-runtime.js")
    assert "window.NousViz" in res.text
    assert "ReactJSXRuntime" in res.text


# ── Public-GET behaviour (no auth required) ──────────────────────────


def test_react_shim_is_public_get(client, monkeypatch):
    """Native ESM `import(url)` doesn't carry session tokens. The shim
    MUST be reachable without auth or every plugin widget breaks."""
    # Force AUTH_REQUIRED=true for this test
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    res = client.get("/api/widget-runtime/react.js")
    # Even with auth required, the shim is in PUBLIC_GET_PATTERNS, so
    # GET succeeds without a session token.
    assert res.status_code == 200, (
        f"widget-runtime/react.js must be public-GET (got {res.status_code}); "
        f"check PUBLIC_GET_PATTERNS in middleware/auth.py"
    )


def test_jsx_runtime_shim_is_public_get(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    res = client.get("/api/widget-runtime/react-jsx-runtime.js")
    assert res.status_code == 200


# ── Version stability marker ─────────────────────────────────────────


def test_react_shim_includes_version_comment(client):
    """The shim's leading comment names the release that shipped this
    surface. Lets ops grep server-side to see which version a client is
    running. If we ever change the shim's exports, the version bumps
    and operators can correlate breaks to the upgrade."""
    res = client.get("/api/widget-runtime/react.js")
    # The shim file's leading comment names B156 and a version. We
    # don't pin to a specific version (it'll bump), just to the marker
    # so future maintainers don't accidentally drop the stamp.
    assert "B156" in res.text
    assert "widget-runtime" in res.text.lower()
