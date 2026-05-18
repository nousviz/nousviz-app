"""B138: SDK dev harness verification.

Exercises `nousviz_sdk.testing.use_test_credentials` and `reset_sdk_state`
to confirm plugin authors can write `pytest` tests against the SDK without
a running NousViz worker.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_harness_provides_get_credential_inside_block():
    from sdk.nousviz_sdk import get_credential
    from sdk.nousviz_sdk.testing import use_test_credentials

    with use_test_credentials({"password": "test-pw", "api_token": "abc123"}):
        assert get_credential("test-plugin", "password") == "test-pw"
        assert get_credential("test-plugin", "api_token") == "abc123"
        # Missing key returns None (same as production behavior)
        assert get_credential("test-plugin", "nonexistent") is None


def test_harness_unregisters_resolver_on_exit():
    from sdk.nousviz_sdk import get_credential, CredentialBrokerUnavailable
    from sdk.nousviz_sdk.testing import use_test_credentials

    with use_test_credentials({"password": "secret"}):
        assert get_credential("test-plugin", "password") == "secret"

    # Outside the block, no resolver and no broker token → unavailable
    with pytest.raises(CredentialBrokerUnavailable):
        get_credential("test-plugin", "password")


def test_harness_resets_cache_between_blocks():
    from sdk.nousviz_sdk import get_credential
    from sdk.nousviz_sdk.testing import use_test_credentials

    with use_test_credentials({"password": "first"}):
        assert get_credential("test-plugin", "password") == "first"

    with use_test_credentials({"password": "second"}):
        assert get_credential("test-plugin", "password") == "second"


def test_harness_supports_db_creds():
    from sdk.nousviz_sdk._broker_client import get_cached
    from sdk.nousviz_sdk.testing import use_test_credentials, fake_db_credentials

    with use_test_credentials({"password": "x"}, db_creds={"user": "u", "password": "p"}):
        cached = get_cached(plugin_id="test-plugin")
        assert cached["__db__"] == {"user": "u", "password": "p"}

    # Default db_creds path
    with use_test_credentials({"password": "x"}):
        cached = get_cached(plugin_id="test-plugin")
        assert cached["__db__"] == fake_db_credentials()


def test_harness_disables_db_when_db_creds_empty():
    from sdk.nousviz_sdk._broker_client import get_cached
    from sdk.nousviz_sdk.testing import use_test_credentials

    with use_test_credentials({"password": "x"}, db_creds={}):
        cached = get_cached(plugin_id="test-plugin")
        assert "__db__" not in cached


def test_reset_sdk_state_is_public_and_works():
    from sdk.nousviz_sdk import get_credential, CredentialBrokerUnavailable
    from sdk.nousviz_sdk.testing import use_test_credentials, reset_sdk_state

    with use_test_credentials({"password": "leak-check"}):
        assert get_credential("test-plugin", "password") == "leak-check"
        # Manually reset inside the block — should clear state immediately
        reset_sdk_state()

    # Even after the with-block, a CredentialBrokerUnavailable is the
    # right error because reset_sdk_state cleared the resolver.
    with pytest.raises(CredentialBrokerUnavailable):
        get_credential("test-plugin", "password")


def test_harness_preserves_existing_plugin_id_env(monkeypatch):
    import os
    from sdk.nousviz_sdk.testing import use_test_credentials

    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "outer-plugin")
    with use_test_credentials({"password": "x"}, plugin_id="inner-plugin"):
        assert os.environ["NOUSVIZ_PLUGIN_ID"] == "inner-plugin"
    assert os.environ["NOUSVIZ_PLUGIN_ID"] == "outer-plugin"


def test_harness_unsets_plugin_id_env_if_was_unset(monkeypatch):
    import os
    from sdk.nousviz_sdk.testing import use_test_credentials

    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)
    with use_test_credentials({"password": "x"}):
        assert os.environ["NOUSVIZ_PLUGIN_ID"] == "test-plugin"
    assert "NOUSVIZ_PLUGIN_ID" not in os.environ
