"""
Router factory for NousViz plugin routes.

Usage:
    from nousviz_sdk import router_for_plugin

    router = router_for_plugin("my-plugin")

    @router.get("/data")
    def get_data():
        ...
"""

from fastapi import APIRouter


def router_for_plugin(slug: str) -> APIRouter:
    """
    Return a FastAPI APIRouter pre-configured for a plugin.

    Sets:
    - prefix: /api/plugins/{slug}
    - tags: ["{slug}"]

    The plugin loader in apps/api/src/plugin_loader.py includes this router
    automatically when it scans plugins/installed/{slug}/api/routes.py.
    """
    return APIRouter(
        prefix=f"/api/plugins/{slug}",
        tags=[slug],
    )
