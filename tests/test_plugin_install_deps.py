"""Tests for _install_plugin_requirements.

Before this helper existed, the install pipeline called pip with
`capture_output=True` and discarded the result — a failed pip install
silently marked the plugin "installed" and the failure only surfaced
as a runtime ImportError (e.g. intercom plugin v0.5.2 vaderSentiment
incident).

These tests pin the contract: success → True, every failure mode →
False AND a log_plugin_event call with action='deps_install'.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _make_plugin_dir(tmp_path: Path, with_requirements: bool = True) -> Path:
    plugin_dir = tmp_path / "fake-plugin"
    plugin_dir.mkdir()
    if with_requirements:
        (plugin_dir / "requirements.txt").write_text("vaderSentiment==3.3.2\n")
    return plugin_dir


def test_no_requirements_file_returns_true_without_logging(tmp_path, monkeypatch):
    """No requirements.txt → noop, no event, return True."""
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path, with_requirements=False)

    events: list = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: events.append((a, kw)),
    )

    assert plugins_mod._install_plugin_requirements("p", plugin_dir) is True
    assert events == []


def test_pip_success_returns_true_and_logs_info_event(tmp_path, monkeypatch):
    """pip rc=0 → True, info event records stdout tail.

    Logging on success matters: it lets operators verify in /system/logs
    *which* packages pip touched. Helps catch "rc=0 but the import still
    fails at runtime" (silent no-op from a cached wheel / malformed
    requirements.txt).
    """
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="Successfully installed vaderSentiment-3.3.2\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    events: list = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: events.append((a, kw)),
    )

    assert plugins_mod._install_plugin_requirements("p", plugin_dir) is True
    assert len(events) == 1
    args, kwargs = events[0]
    assert args[0] == "info"
    assert args[2] == "deps_install"
    assert "Successfully installed vaderSentiment" in kwargs["detail"]["stdout"]


def test_pip_nonzero_rc_returns_false_and_logs_error(tmp_path, monkeypatch):
    """pip rc!=0 → False, error event with stderr/stdout in detail."""
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="Collecting vaderSentiment...\n",
            stderr="ERROR: Could not find a version that satisfies\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    events: list = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: events.append((a, kw)),
    )

    result = plugins_mod._install_plugin_requirements(
        "intercom", plugin_dir, actor_user_id="user-123",
    )
    assert result is False

    assert len(events) == 1
    args, kwargs = events[0]
    # positional: level, plugin_id, action, message
    assert args[0] == "error"
    assert args[1] == "intercom"
    assert args[2] == "deps_install"
    assert "rc=1" in args[3]
    assert kwargs["detail"]["stderr"].startswith("ERROR: Could not find")
    assert kwargs["source"] == "plugin_install"
    assert kwargs["actor_user_id"] == "user-123"


def test_pip_timeout_returns_false_and_logs_error(tmp_path, monkeypatch):
    """Timeout (300s) → False, error event surfaces the TimeoutExpired class."""
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pip install", timeout=300)

    monkeypatch.setattr(subprocess, "run", fake_run)

    events: list = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: events.append((a, kw)),
    )

    assert plugins_mod._install_plugin_requirements("intercom", plugin_dir) is False
    assert len(events) == 1
    args, _ = events[0]
    assert args[0] == "error"
    assert "TimeoutExpired" in args[3]


def test_pip_python_bin_missing_returns_false_and_logs_error(tmp_path, monkeypatch):
    """OSError from subprocess (e.g. python_bin not found) → False, error event."""
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'python3'")

    monkeypatch.setattr(subprocess, "run", fake_run)

    events: list = []
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: events.append((a, kw)),
    )

    assert plugins_mod._install_plugin_requirements("intercom", plugin_dir) is False
    assert len(events) == 1
    args, _ = events[0]
    assert args[0] == "error"
    assert "FileNotFoundError" in args[3]


def test_pip_runs_against_sys_executable(tmp_path, monkeypatch):
    """The pip subprocess must use sys.executable, not a guessed venv path.

    Earlier this helper used `REPO_ROOT/.venv/bin/python3` and silently
    fell back to `"python3"` from PATH when that didn't exist. On a
    production box where the venv isn't at `<repo>/.venv` (Docker,
    systemd with custom WorkingDirectory, etc.), pip would silently
    install into the wrong interpreter — the install would report
    success and the plugin's import would still fail.

    sys.executable is *the* interpreter running this code; pip via
    `sys.executable -m pip` always targets the same venv as the calling
    process.
    """
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    captured_argv: list = []

    def fake_run(*args, **kwargs):
        captured_argv.extend(args[0])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "apps.api.src.log_events.log_plugin_event",
        lambda *a, **kw: None,
    )

    plugins_mod._install_plugin_requirements("p", plugin_dir)

    assert captured_argv[0] == sys.executable
    assert captured_argv[1:5] == ["-m", "pip", "install", "-r"]


def test_nousviz_env_vars_stripped_from_subprocess_env(tmp_path, monkeypatch):
    """P22-G5: NOUSVIZ_* env vars must not leak to the pip subprocess."""
    from apps.api.src.routes import plugins as plugins_mod

    plugin_dir = _make_plugin_dir(tmp_path)

    monkeypatch.setenv("NOUSVIZ_DB_PASSWORD", "secret-creds")
    monkeypatch.setenv("NOUSVIZ_ENCRYPTION_KEY", "secret-key")
    monkeypatch.setenv("PATH", "/usr/bin")

    captured_env: dict = {}

    def fake_run(*args, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    plugins_mod._install_plugin_requirements("p", plugin_dir)

    assert "NOUSVIZ_DB_PASSWORD" not in captured_env
    assert "NOUSVIZ_ENCRYPTION_KEY" not in captured_env
    assert captured_env.get("PATH") == "/usr/bin"
