"""Tests that updating a plugin installs its requirements.txt.

install_plugin pip-installs a plugin's requirements.txt (B306), but
update_plugin did not. An update that added or re-pinned a library shipped
code that could not import it, and the failure surfaced later as an
ImportError in the plugin's routes or sync job. These tests run the whole
update flow with its external effects (git, Postgres, PM2) stubbed, and pin
the contract: the new code's requirements are installed after the swap,
before the reload, and the result is reported as `deps_installed`.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def update_env(tmp_path, monkeypatch):
    """A fake installed plugin at v1.0.0 whose update stages v1.1.0 with a
    requirements.txt. Returns a dict the test inspects afterwards."""
    from apps.api.src.routes import plugins as plugins_mod

    installed = tmp_path / "installed"
    live = installed / "fake-plug"
    live.mkdir(parents=True)
    (live / "plugin.yaml").write_text("name: fake-plug\nversion: 1.0.0\n")
    monkeypatch.setattr(plugins_mod, "INSTALLED_DIR", installed)

    def fake_stage(plugin_id, source_class, source_url, staging_dir):
        staging_dir.mkdir(parents=True)
        (staging_dir / "plugin.yaml").write_text("name: fake-plug\nversion: 1.1.0\n")
        (staging_dir / "requirements.txt").write_text("somelib==2.0\n")
        return "v1.1.0"

    monkeypatch.setattr(plugins_mod, "_stage_plugin_clone", fake_stage)
    monkeypatch.setattr(plugins_mod, "_run_plugin_migrations", lambda *a, **kw: [])
    monkeypatch.setattr(plugins_mod, "_log_plugin_action", lambda *a, **kw: None)

    @contextmanager
    def fake_conn():
        yield MagicMock()

    monkeypatch.setattr(plugins_mod, "get_pg_conn", fake_conn)
    monkeypatch.setattr("apps.api.src.plugin_update_checker.detect_source_class",
                        lambda pid: ("first_party", None))
    monkeypatch.setattr("apps.api.src.plugin_update_checker.check_plugin",
                        lambda pid: None)
    monkeypatch.setattr("apps.api.src.plugin_grants.grant_plugin_tables",
                        lambda *a, **kw: None)

    # Record the PM2 reload without running it. subprocess.run (used for
    # `git rev-parse`) goes through Popen too, so everything else passes
    # through to the real one.
    import subprocess
    real_popen = subprocess.Popen
    order: list[str] = []

    def fake_popen(args, *a, **kw):
        if args and args[0] == "pm2":
            order.append("pm2_reload")
            return MagicMock()
        return real_popen(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    state = {"calls": [], "order": order, "live": live, "result": True}

    def fake_install(plugin_id, plugin_dir, actor_user_id=None):
        state["calls"].append((plugin_id, Path(plugin_dir)))
        # Must see the NEW code: the swap has already happened.
        state["saw_requirements"] = (Path(plugin_dir) / "requirements.txt").read_text()
        order.append("deps")
        return state["result"]

    monkeypatch.setattr(plugins_mod, "_install_plugin_requirements", fake_install)
    return state


def _run_update():
    from apps.api.src.routes import plugins as plugins_mod
    return asyncio.run(plugins_mod.update_plugin("fake-plug", request=MagicMock(), _=None))


def test_update_installs_new_requirements_before_reload(update_env):
    res = _run_update()

    assert res["status"] == "updated"
    assert res["to_version"] == "1.1.0"
    assert update_env["calls"] == [("fake-plug", update_env["live"])]
    assert update_env["saw_requirements"] == "somelib==2.0\n"
    assert update_env["order"] == ["deps", "pm2_reload"]
    assert res["deps_installed"] is True


def test_update_reports_failed_deps_without_rolling_back(update_env):
    """Matches install: a pip failure is reported and logged (by the
    helper), not fatal. The new code stays live so the operator can fix
    the dependency and retry, rather than losing the update."""
    update_env["result"] = False

    res = _run_update()

    assert res["status"] == "updated"
    assert res["deps_installed"] is False
    assert "1.1.0" in (update_env["live"] / "plugin.yaml").read_text()
