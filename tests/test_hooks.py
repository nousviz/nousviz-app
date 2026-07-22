"""MC-203: hook seams default to community no-ops; the enterprise
add-on loads only in managed mode and fails open."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from src import enterprise_loader, hooks  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_registry():
    hooks.reset()
    yield
    hooks.reset()


class TestDefaults:
    def test_invite_allowed(self):
        d = hooks.user_invite_allowed()
        assert d.allowed is True and d.reason is None

    def test_plugin_install_allowed(self):
        assert hooks.plugin_install_allowed("anything").allowed is True

    def test_smtp_passthrough(self):
        cfg = {"host": "smtp.example.com"}
        assert hooks.resolve_smtp_config(cfg) is cfg
        assert hooks.resolve_smtp_config(None) is None

    def test_features_enabled(self):
        assert hooks.feature_enabled("mcp") is True


class TestRegistry:
    def test_register_replaces(self):
        hooks.register("user_invite_allowed", lambda: hooks.Decision(False, "limit"))
        d = hooks.user_invite_allowed()
        assert d.allowed is False and d.reason == "limit"

    def test_unknown_name_raises(self):
        with pytest.raises(ValueError):
            hooks.register("not_a_hook", lambda: None)

    def test_reset_restores_defaults(self):
        hooks.register("feature_enabled", lambda name: False)
        hooks.reset()
        assert hooks.feature_enabled("anything") is True


class _FakeApp:
    pass


class TestLoader:
    def test_community_never_imports(self, monkeypatch):
        monkeypatch.delenv("NOUSVIZ_EDITION", raising=False)
        sys.modules.pop("nousviz_enterprise", None)
        assert enterprise_loader.load_enterprise(_FakeApp()) is False
        assert "nousviz_enterprise" not in sys.modules

    @pytest.mark.skipif(
        not (
            Path(__file__).resolve().parent.parent
            / "enterprise" / "nousviz_enterprise" / "__init__.py"
        ).exists(),
        reason="enterprise add-on not present — public builds have no submodule "
        "by design; the managed-build pipeline runs this test with it mounted",
    )
    def test_managed_loads_and_registers(self, monkeypatch):
        monkeypatch.setenv("NOUSVIZ_EDITION", "managed")
        sys.modules.pop("nousviz_enterprise", None)
        assert enterprise_loader.load_enterprise(_FakeApp()) is True
        assert "nousviz_enterprise" in sys.modules

    def test_managed_missing_addon_fails_open(self, monkeypatch):
        monkeypatch.setenv("NOUSVIZ_EDITION", "managed")
        monkeypatch.setattr(enterprise_loader, "_PACKAGE", "nousviz_enterprise_absent")
        assert enterprise_loader.load_enterprise(_FakeApp()) is False
