"""MC-201: the edition switch defaults safe and reads tolerantly."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from src import edition  # noqa: E402


def _with(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("NOUSVIZ_EDITION", raising=False)
    else:
        monkeypatch.setenv("NOUSVIZ_EDITION", value)
    importlib.reload(edition)
    return edition


def test_default_is_community(monkeypatch):
    e = _with(monkeypatch, None)
    assert e.get_edition() == "community"
    assert e.is_managed() is False


def test_managed_when_set(monkeypatch):
    e = _with(monkeypatch, "managed")
    assert e.get_edition() == "managed"
    assert e.is_managed() is True


def test_case_and_whitespace_tolerant(monkeypatch):
    e = _with(monkeypatch, "  Managed ")
    assert e.is_managed() is True


def test_unknown_value_falls_back_to_community(monkeypatch):
    e = _with(monkeypatch, "enterprise-deluxe")
    assert e.get_edition() == "community"
    assert e.is_managed() is False
