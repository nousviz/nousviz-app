"""
nousviz_sdk.testing — Dev harness for plugin authors.

The credential broker (P208 / v0.9.0) makes it impossible to run plugin
code that calls `get_credential()` outside a NousViz-spawned subprocess —
broker socket and one-shot token aren't there. This module gives plugin
authors a way to write `pytest` tests against their own code without
needing a running NousViz worker.

# Usage

```python
from nousviz_sdk.testing import use_test_credentials

def test_my_plugin_sync():
    with use_test_credentials({
        "host": "localhost",
        "port": 5432,
        "database": "test",
        "username": "test",
        "password": "test",
        "ssl_ca": "",
    }):
        from my_plugin.src import sync
        result = sync.run()
        assert result.ok
```

`use_test_credentials()` registers a stub resolver for the SDK's broker
client. Inside the `with` block:
  - `get_credential(plugin_id, key)` returns the matching value from the
    supplied dict
  - `get_pg_conn()` works if you supplied a `__db__` block (or use
    `fake_db_credentials()` for sensible defaults)

On exit, the resolver is unregistered and the SDK's per-process credential
cache is cleared, so the next test starts fresh.

# What this does NOT do

This is the credential / SDK-state harness. Things still on you:
  - **DB**: `get_pg_conn()` connects to whatever `POSTGRES_HOST` /
    `POSTGRES_DB` resolve to. Point at a test DB or use a fixture that
    spins one up.
  - **HTTP / FastAPI routes**: pair this harness with FastAPI's
    `TestClient` directly.
  - **Subprocess testing**: this runs in-process. To exercise the actual
    subprocess path, you'd need a real broker — that's a separate
    integration testing concern.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from . import _broker_client


def fake_db_credentials() -> dict[str, str]:
    """Default `__db__` block for tests — connects to local postgres
    using the `nousviz_plugin` role with password "test".

    Override individual fields by passing a custom `db_creds` dict to
    `use_test_credentials()` or by setting `POSTGRES_HOST` etc. in env.
    """
    return {
        "user": "nousviz_plugin",
        "password": "test",
    }


def reset_sdk_state() -> None:
    """Clear any registered test resolver and the per-process credential
    cache. Public, supported. Call between tests if you need a fresh state
    without using the `use_test_credentials` context manager.
    """
    _broker_client.reset_resolver_for_tests()
    _broker_client.reset_cache_for_tests()


@contextmanager
def use_test_credentials(
    creds: dict[str, Any],
    db_creds: Optional[dict[str, str]] = None,
    plugin_id: str = "test-plugin",
) -> Iterator[None]:
    """Context manager: register a stub credential resolver for the duration
    of the block.

    Args:
        creds: Dict of credential field-name → value. Whatever your plugin
               calls `get_credential(plugin_id, key)` for must be a key here.
        db_creds: Optional dict for the special `__db__` block used by
                  `get_pg_conn()`. Defaults to `fake_db_credentials()`.
                  Set to {} to deliberately disable DB access in tests.
        plugin_id: Plugin id the resolver responds for. Defaults to
                   "test-plugin"; override if your plugin calls
                   `get_credential(plugin_id, ...)` with a specific id.

    Behavior:
      - Sets `NOUSVIZ_PLUGIN_ID` env var so `get_pg_conn()` and the SDK's
        in-process resolver path can find the plugin id.
      - Registers an in-process resolver that returns `creds` (plus the
        `__db__` block) for the supplied plugin_id.
      - On exit, unregisters the resolver, clears the cache, and restores
        `NOUSVIZ_PLUGIN_ID` to whatever it was before (typically unset).
    """
    if db_creds is None:
        db_creds = fake_db_credentials()

    response: dict[str, Any] = dict(creds)
    if db_creds:
        response["__db__"] = db_creds

    def _resolver(requested_plugin_id: str) -> dict[str, Any]:
        # Always return the same dict — single-tenant test resolver.
        # `__core__` sentinel is used by get_pg_conn when no plugin_id is
        # known; serve the same response.
        return response

    prev_plugin_id = os.environ.get("NOUSVIZ_PLUGIN_ID")
    os.environ["NOUSVIZ_PLUGIN_ID"] = plugin_id

    # Clear any stale state from a previous test before registering
    _broker_client.reset_resolver_for_tests()
    _broker_client.reset_cache_for_tests()
    _broker_client.register_resolver(_resolver)

    try:
        yield
    finally:
        _broker_client.reset_resolver_for_tests()
        _broker_client.reset_cache_for_tests()
        if prev_plugin_id is None:
            os.environ.pop("NOUSVIZ_PLUGIN_ID", None)
        else:
            os.environ["NOUSVIZ_PLUGIN_ID"] = prev_plugin_id


__all__ = [
    "use_test_credentials",
    "reset_sdk_state",
    "fake_db_credentials",
]
