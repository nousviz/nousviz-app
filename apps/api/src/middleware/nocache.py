"""
No-cache middleware — stamps `Cache-Control: no-store` on every /api/* response.

The API is fully dynamic. No endpoint should be cached by any intermediary
(Safari/Chrome disk cache, service workers, CDN edges). Stale reads produce
user-visible bugs — e.g. /api/jobs returning a pre-deploy shape hours after
the deploy because Safari decided to serve from cache.

The nginx config sets the same headers at the edge; this middleware is
defence in depth so localhost bypass (direct curl to 127.0.0.1:8000) also
gets the no-cache behaviour.

# Cacheable exceptions (B156, v0.9.4.7)

A few endpoints serve static-ish content where caching IS desirable —
specifically the widget-runtime React shim, fetched by every plugin
widget mount. Without caching, each dashboard re-render triggers a
fresh fetch for the same handful of bytes. The endpoints in
`CACHEABLE_PREFIXES` keep whatever Cache-Control the route sets.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Endpoints exempt from no-cache stamping (they set their own cache headers).
# Keep this list short and well-justified — every entry is a possible
# stale-cache vector.
CACHEABLE_PREFIXES = (
    "/api/widget-runtime/",  # B156: React shim, stable per-release; fetched on every widget mount
)

# Endpoints exempt only when they match a deeper path pattern.
# Plugin widget bundles are at /api/plugins/{id}/widget/{file}.js and
# benefit from caching (they have ETag headers from the route). Plugin
# manifest endpoints (/api/plugins, /api/plugins/{id}) must stay no-cache.
import re
_CACHEABLE_PATTERNS = (
    re.compile(r"^/api/plugins/[^/]+/widget/[^/]+\.js$"),
)


def _should_skip_nocache(path: str) -> bool:
    if any(path.startswith(p) for p in CACHEABLE_PREFIXES):
        return True
    return any(p.match(path) for p in _CACHEABLE_PATTERNS)


class NoCacheAPIMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Only stamp API responses — static assets are separate and benefit from caching
        if request.url.path.startswith("/api/") and not _should_skip_nocache(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
