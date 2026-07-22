"""
Unit tests for B306 — `signal_workers_to_reload`.

The helper sends SIGHUP to the gunicorn master so all API workers cycle
and pick up newly-installed plugin routes. It MUST refuse to signal any
parent that doesn't look like gunicorn, because `kill -HUP` against the
wrong PID (systemd, dev uvicorn, a pytest harness) ranges from "ignored"
to "fatal to the host". These tests pin that safety contract.

No live processes are involved — `os.kill`, `os.getppid`, and the
cmdline lookup are all mocked.
"""
from __future__ import annotations

import signal
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.src.plugin_loader import signal_workers_to_reload


def _proc_cmdline_bytes(s: str) -> bytes:
    return s.replace(" ", "\0").encode("utf-8")


# ── happy path: gunicorn parent ──────────────────────────────────────


def test_sends_sighup_when_parent_is_gunicorn():
    cmdline = _proc_cmdline_bytes(
        "/opt/nousviz/.venv/bin/python3 /opt/nousviz/.venv/bin/gunicorn "
        "apps.api.src.main:app --workers 2"
    )
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=12345), \
         patch("builtins.open", mock_open(read_data=cmdline)), \
         patch("apps.api.src.plugin_loader.os.kill") as mock_kill:
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is True
    mock_kill.assert_called_once_with(12345, signal.SIGHUP)


# ── refusals ─────────────────────────────────────────────────────────


def test_skips_when_parent_is_pid_1():
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=1), \
         patch("apps.api.src.plugin_loader.os.kill") as mock_kill:
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is False
    mock_kill.assert_not_called()


def test_skips_when_parent_is_not_gunicorn_via_proc():
    # /proc available, but cmdline doesn't mention gunicorn (dev uvicorn case)
    cmdline = _proc_cmdline_bytes(
        "/opt/nousviz/.venv/bin/python3 -m uvicorn apps.api.src.main:app --reload"
    )
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=4242), \
         patch("builtins.open", mock_open(read_data=cmdline)), \
         patch("apps.api.src.plugin_loader.os.kill") as mock_kill:
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is False
    mock_kill.assert_not_called()


def test_falls_back_to_ps_when_proc_missing_and_finds_gunicorn():
    # macOS dev path: /proc not available, ps reports gunicorn.
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=4242), \
         patch("builtins.open", side_effect=FileNotFoundError()), \
         patch("apps.api.src.plugin_loader.subprocess.run") as mock_run, \
         patch("apps.api.src.plugin_loader.os.kill") as mock_kill:
        mock_run.return_value.stdout = (
            "/opt/nousviz/.venv/bin/gunicorn apps.api.src.main:app --workers 2\n"
        )
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is True
    mock_kill.assert_called_once_with(4242, signal.SIGHUP)


def test_falls_back_to_ps_when_proc_missing_and_no_gunicorn():
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=4242), \
         patch("builtins.open", side_effect=FileNotFoundError()), \
         patch("apps.api.src.plugin_loader.subprocess.run") as mock_run, \
         patch("apps.api.src.plugin_loader.os.kill") as mock_kill:
        mock_run.return_value.stdout = "pytest tests/test_foo.py\n"
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is False
    mock_kill.assert_not_called()


# ── error handling ──────────────────────────────────────────────────


def test_returns_false_when_kill_raises_process_lookup():
    cmdline = _proc_cmdline_bytes("gunicorn apps.api.src.main:app")
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=99999), \
         patch("builtins.open", mock_open(read_data=cmdline)), \
         patch(
             "apps.api.src.plugin_loader.os.kill",
             side_effect=ProcessLookupError("no such process"),
         ):
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is False


def test_returns_false_when_kill_raises_permission_error():
    cmdline = _proc_cmdline_bytes("gunicorn apps.api.src.main:app")
    with patch("apps.api.src.plugin_loader.os.getppid", return_value=1234), \
         patch("builtins.open", mock_open(read_data=cmdline)), \
         patch(
             "apps.api.src.plugin_loader.os.kill",
             side_effect=PermissionError("operation not permitted"),
         ):
        result = signal_workers_to_reload(reason="install:test-plugin")

    assert result is False
