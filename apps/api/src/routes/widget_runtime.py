"""
/api/widget-runtime/* — host-served React shim for plugin widgets (B156).

# Why this exists

v0.9.4 plugin widgets are bundled as ESM modules and dynamically imported
by the host via native `import(url)`. Native ESM dynamic import does NOT
honour bundler aliases for bare specifiers like `"react"` — the spec
requires absolute/relative paths or an importmap.

v0.9.4.5 tried to solve this by recommending plugin authors bundle React
into their widget bundle. That's broken for any widget using hooks:
React 18's `useState`/`useEffect` rely on a singleton `ReactCurrentDispatcher`
inside the React copy that's actively rendering. If the host has its own
React copy and the widget bundles a separate copy, the widget's hooks
look up dispatcher state in their own React, which is null, and you get:

    TypeError: Cannot read properties of null (reading 'useState')

This is a well-known React-18 dual-instance problem.

# The fix (B156)

Host serves a tiny shim at a stable URL that re-exports the methods of
`window.NousViz.React` — which the host populates with its own React
copy at boot, before any plugin widget mounts. Plugin authors build with
`--alias:react=<this URL>` so their bundle's `import { useState } from
"react"` resolves to the host React's `useState` at runtime. One React
copy in play, hooks work, dual-instance bug gone.

# Stable contract

Both endpoints are content-stable in a release: they always export the
same names (the React 18 public API). Operators can cache the URL in
plugin builds without worrying about it changing. We bump the version
string in the response body's leading comment so we can grep server-side
to see which release served a given client.

# Cache headers

`Cache-Control: public, max-age=3600` — the shim itself doesn't change
between releases (only `window.NousViz.React`'s underlying methods do,
and those load with the host's main bundle). Conservative 1h cache; if
we ship a breaking change, operators hard-refresh.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/api/widget-runtime", tags=["widget-runtime"])

# B156 (v0.9.4.7): the React shim. Everything plugin widgets import from
# `react` resolves here. Each named export reads the host's React via
# the `window.NousViz.React` global, which the host's plugin-component-loader
# populates before any plugin widget executes.
#
# Maintenance: when adding a new React API plugins should be able to use,
# add it here. React's public surface area is stable across minor versions
# (18.0 → 18.3) so this list rarely needs updating. The default export
# is the full React object for cases where a plugin imports `import React
# from "react"` (CJS-interop style).

_REACT_SHIM = """// nousviz widget-runtime React shim — v0.9.4.7 (B156)
// Stable URL: /api/widget-runtime/react.js
// Plugin authors: build your widget with --alias:react=/api/widget-runtime/react.js
// so your bundled `import { useState } from "react"` resolves to the host's
// React at runtime, avoiding the dual-instance hooks bug.

const R = (typeof window !== "undefined" && window.NousViz && window.NousViz.React) || null;
if (!R) {
  throw new Error(
    "[widget-runtime] window.NousViz.React not published. " +
    "This shim must be loaded after the host's main bundle has booted. " +
    "Hard-refresh the host page; if the error persists, file a bug."
  );
}

// Hooks
export const useState = R.useState;
export const useEffect = R.useEffect;
export const useLayoutEffect = R.useLayoutEffect;
export const useRef = R.useRef;
export const useMemo = R.useMemo;
export const useCallback = R.useCallback;
export const useContext = R.useContext;
export const useReducer = R.useReducer;
export const useId = R.useId;
export const useDeferredValue = R.useDeferredValue;
export const useTransition = R.useTransition;
export const useSyncExternalStore = R.useSyncExternalStore;
export const useImperativeHandle = R.useImperativeHandle;
export const useInsertionEffect = R.useInsertionEffect;
export const useDebugValue = R.useDebugValue;

// Element creation
export const createElement = R.createElement;
export const cloneElement = R.cloneElement;
export const isValidElement = R.isValidElement;
export const Fragment = R.Fragment;
export const StrictMode = R.StrictMode;
export const Suspense = R.Suspense;

// Component primitives
export const Component = R.Component;
export const PureComponent = R.PureComponent;
export const memo = R.memo;
export const forwardRef = R.forwardRef;
export const lazy = R.lazy;
export const createRef = R.createRef;
export const createContext = R.createContext;

// Children utility
export const Children = R.Children;

// Misc
export const startTransition = R.startTransition;
export const version = R.version;

// Default export — the whole React object — for `import React from "react"` style
export default R;
"""

_JSX_RUNTIME_SHIM = """// nousviz widget-runtime react/jsx-runtime shim — v0.9.4.7 (B156)
// Stable URL: /api/widget-runtime/react-jsx-runtime.js
// Plugin authors: --alias:react/jsx-runtime=/api/widget-runtime/react-jsx-runtime.js
// (esbuild --jsx=automatic emits imports of jsx/jsxs/Fragment from this path.)

const RT = (typeof window !== "undefined"
  && window.NousViz
  && window.NousViz.ReactJSXRuntime) || null;
if (!RT) {
  throw new Error(
    "[widget-runtime] window.NousViz.ReactJSXRuntime not published. " +
    "Hard-refresh the host page; if the error persists, file a bug."
  );
}

export const jsx = RT.jsx;
export const jsxs = RT.jsxs;
export const jsxDEV = RT.jsxDEV;
export const Fragment = RT.Fragment;
"""


@router.get(
    "/react.js",
    operation_id="widget_runtime.react",
    response_class=Response,
    summary="React shim — JavaScript module (not JSON)",
    responses={
        200: {
            "content": {"application/javascript": {}},
            "description": "React shim ESM module.",
        },
    },
)
async def serve_react_shim():
    """Serve the React shim. Plugin widgets built with
    --alias:react=/api/widget-runtime/react.js import from this URL.

    Returns a JavaScript module (`application/javascript`), not JSON —
    `response_class=Response` is set so /openapi.json doesn't claim a
    JSON schema for it.
    """
    return Response(
        content=_REACT_SHIM,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get(
    "/react-jsx-runtime.js",
    operation_id="widget_runtime.jsx_runtime",
    response_class=Response,
    summary="react/jsx-runtime shim — JavaScript module (not JSON)",
    responses={
        200: {
            "content": {"application/javascript": {}},
            "description": "react/jsx-runtime shim ESM module.",
        },
    },
)
async def serve_jsx_runtime_shim():
    """Serve the react/jsx-runtime shim. esbuild --jsx=automatic emits
    imports of jsx/jsxs/Fragment from `react/jsx-runtime`; this shim
    rebinds them to the host's runtime.
    """
    return Response(
        content=_JSX_RUNTIME_SHIM,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )
