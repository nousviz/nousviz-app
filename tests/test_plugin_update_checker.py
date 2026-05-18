"""Unit tests for plugin_update_checker (B144 / v0.9.2.4).

Pure-logic tests: version parsing, semver comparison, source-class
detection (filesystem-based, no network). The git ls-remote and DB cache
paths are not exercised here — those are tested live during deploy.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Version parsing ──────────────────────────────────────────────────


def test_parse_version_handles_basic_semver():
    from apps.api.src.plugin_update_checker import parse_version
    assert parse_version("1.2.3") is not None
    assert parse_version("v1.2.3") is not None
    assert parse_version("0.0.0") is not None
    assert parse_version("99.99.99") is not None


def test_parse_version_handles_prerelease():
    from apps.api.src.plugin_update_checker import parse_version
    assert parse_version("1.2.3-rc.1") is not None
    assert parse_version("1.2.3-alpha") is not None
    assert parse_version("v2.0.0-beta.5") is not None


def test_parse_version_handles_four_component():
    from apps.api.src.plugin_update_checker import parse_version
    assert parse_version("1.2.3.4") is not None


def test_parse_version_rejects_garbage():
    from apps.api.src.plugin_update_checker import parse_version
    assert parse_version("") is None
    assert parse_version("not-a-version") is None
    assert parse_version("1.2") is None  # need at least 3 components
    assert parse_version("v") is None
    assert parse_version("1.2.3.4.5") is None  # too many


# ── Semver comparison (the actual is_newer fn) ────────────────────────


def test_is_newer_basic_progression():
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("1.2.4", "1.2.3") is True
    assert is_newer("1.3.0", "1.2.99") is True
    assert is_newer("2.0.0", "1.99.99") is True
    assert is_newer("0.10.0", "0.9.99") is True


def test_is_newer_same_version():
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("1.2.3", "1.2.3") is False
    assert is_newer("v1.2.3", "1.2.3") is False  # leading-v ignored


def test_is_newer_older_latest():
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("1.2.3", "1.2.4") is False
    assert is_newer("1.0.0", "2.0.0") is False


def test_is_newer_prerelease_orders_before_release():
    """1.2.3-rc.1 is less than 1.2.3 — pre-release sorts before release."""
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("1.2.3", "1.2.3-rc.1") is True
    assert is_newer("1.2.3-rc.1", "1.2.3") is False


def test_is_newer_handles_unparseable_safely():
    """Garbage in either side returns False — never crash."""
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("garbage", "1.2.3") is False
    assert is_newer("1.2.3", "garbage") is False
    assert is_newer(None, "1.2.3") is False
    assert is_newer("1.2.3", None) is False
    assert is_newer("", "") is False


def test_is_newer_handles_four_component():
    from apps.api.src.plugin_update_checker import is_newer
    assert is_newer("1.2.3.5", "1.2.3.4") is True
    assert is_newer("1.2.3.4", "1.2.3.5") is False
    assert is_newer("1.2.4.0", "1.2.3.99") is True


# ── Source-class detection (filesystem-based) ───────────────────────


def test_detect_source_class_first_party_via_utilities():
    """A plugin whose manifest exists in plugins/utilities/<slug>/ is first-party."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "test-plug").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "test-plug" / "plugin.yaml").write_text(
            "name: test-plug\nversion: 1.0.0\n"
        )
        (td_path / "plugins" / "utilities" / "test-plug").mkdir(parents=True)
        (td_path / "plugins" / "utilities" / "test-plug" / "plugin.yaml").write_text(
            "name: test-plug\nversion: 1.0.1\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("test-plug")

    assert sc == "first_party"
    assert url is None


def test_detect_source_class_git_via_repository_url():
    """A plugin with no catalog source but repository_url in installed manifest is git."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "third-party").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "third-party" / "plugin.yaml").write_text(
            "name: third-party\nversion: 0.1.0\n"
            "repository_url: https://github.com/foo/bar\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("third-party")

    assert sc == "git"
    assert url == "https://github.com/foo/bar"


def test_detect_source_class_git_via_top_level_repository():
    """Plugin authors commonly use `repository:` (no _url suffix) at top level —
    accept that shape too."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "third-party").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "third-party" / "plugin.yaml").write_text(
            "name: third-party\nversion: 0.1.0\n"
            "repository: git@github.com:JoeHatch/foo.git\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("third-party")

    assert sc == "git"
    assert url == "git@github.com:JoeHatch/foo.git"


def test_detect_source_class_git_via_nested_publisher_repository():
    """Some manifests put repository under publisher.repository."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "third-party").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "third-party" / "plugin.yaml").write_text(
            "name: third-party\nversion: 0.1.0\n"
            "publisher:\n"
            "  name: Test Co\n"
            "  repository: https://github.com/test/repo\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("third-party")

    assert sc == "git"
    assert url == "https://github.com/test/repo"


def test_detect_source_class_unknown_when_manifest_missing():
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed").mkdir(parents=True)
        # No plugin dir at all

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("ghost")

    assert sc == "unknown"
    assert url is None


def test_detect_source_class_unknown_when_no_repo_and_not_first_party():
    """A plugin that's installed but has no catalog source AND no
    repository_url is unknown."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "orphan").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "orphan" / "plugin.yaml").write_text(
            "name: orphan\nversion: 0.1.0\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"), \
             patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            sc, url = puc.detect_source_class("orphan")

    assert sc == "unknown"
    assert url is None


# ── First-party version reading ──────────────────────────────────────


def test_read_first_party_latest_returns_catalog_version():
    """When a plugin exists in the catalog, read_first_party_latest returns its version."""
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "utilities" / "test").mkdir(parents=True)
        (td_path / "plugins" / "utilities" / "test" / "plugin.yaml").write_text(
            "name: test\nversion: 2.5.7\n"
        )

        with patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            assert puc.read_first_party_latest("test") == "2.5.7"


def test_read_first_party_latest_returns_none_when_absent():
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with patch.object(puc, "UTILITIES_DIR", td_path / "plugins" / "utilities"), \
             patch.object(puc, "OFFICIAL_DIR", td_path / "plugins" / "official"):
            assert puc.read_first_party_latest("nonexistent") is None


# ── Installed version reading ─────────────────────────────────────────


def test_read_installed_version_from_manifest():
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        (td_path / "plugins" / "installed" / "p").mkdir(parents=True)
        (td_path / "plugins" / "installed" / "p" / "plugin.yaml").write_text(
            "name: p\nversion: 0.3.3\n"
        )

        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"):
            assert puc.read_installed_version("p") == "0.3.3"


def test_read_installed_version_returns_none_for_missing_plugin():
    from apps.api.src import plugin_update_checker as puc

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with patch.object(puc, "INSTALLED_DIR", td_path / "plugins" / "installed"):
            assert puc.read_installed_version("ghost") is None


# ── fetch_latest_git_tag normalization ───────────────────────────────


def test_fetch_latest_git_tag_strips_leading_v(monkeypatch):
    """Tags often look like 'v1.2.3' but manifest version: fields are plain
    '1.2.3'. fetch_latest_git_tag must return the plain form so version
    comparisons and UI rendering don't double-prefix as 'vv1.2.3'."""
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = (
        "abc123\trefs/tags/v0.2.1\n"
        "def456\trefs/tags/v0.2.2\n"
    )
    fake_proc.stderr = ""

    monkeypatch.setattr(puc, "_get_deploy_key_path", lambda *a, **kw: None, raising=False)
    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")

    # Lazy-import _get_deploy_key_path may not exist as a module attribute;
    # the actual code does `from .routes.plugins import _get_deploy_key_path`
    # inside fetch_latest_git_tag, so patch that import path instead.
    import sys
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    result = puc.fetch_latest_git_tag("git@github.com:test/repo.git")
    assert result == "0.2.2"  # not "v0.2.2"


def test_fetch_latest_git_tag_returns_plain_when_no_v_prefix(monkeypatch):
    """If the upstream tag has no v prefix, return as-is."""
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "abc123\trefs/tags/1.5.0\n"
    fake_proc.stderr = ""

    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")
    import sys
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    result = puc.fetch_latest_git_tag("https://example.com/repo.git")
    assert result == "1.5.0"


# ── B152 (v0.9.4.4): with-ref variant for clone path ─────────────────


def test_fetch_with_ref_returns_v_prefixed_original_for_v_tagged_repo(monkeypatch):
    """B152: clone path needs the ORIGINAL tag ref (preserves leading v).
    `git clone --branch 0.3.0` against a `v0.3.0` upstream fails.
    fetch_latest_git_tag_with_ref must return both the original ref and
    the normalized version so callers pick the right one for each use."""
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock
    import sys

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = (
        "abc123\trefs/tags/v0.2.1\n"
        "def456\trefs/tags/v0.2.2\n"
        "ghi789\trefs/tags/v0.3.0\n"
    )
    fake_proc.stderr = ""
    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    result = puc.fetch_latest_git_tag_with_ref("git@github.com:test/repo.git")
    assert result == ("v0.3.0", "0.3.0")


def test_fetch_with_ref_returns_plain_when_upstream_has_no_v_prefix(monkeypatch):
    """When upstream tags don't have v-prefix, both values are equal."""
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock
    import sys

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "abc123\trefs/tags/1.5.0\n"
    fake_proc.stderr = ""
    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    result = puc.fetch_latest_git_tag_with_ref("https://example.com/repo.git")
    assert result == ("1.5.0", "1.5.0")


def test_fetch_with_ref_picks_highest_when_mixed_prefix(monkeypatch):
    """If upstream has both `0.2.0` and `v0.3.0`, the v-prefixed one wins
    on semver and we preserve its prefix in the original ref."""
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock
    import sys

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = (
        "abc123\trefs/tags/0.2.0\n"
        "def456\trefs/tags/v0.3.0\n"
    )
    fake_proc.stderr = ""
    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    result = puc.fetch_latest_git_tag_with_ref("git@example.com:repo.git")
    assert result == ("v0.3.0", "0.3.0")


def test_fetch_with_ref_returns_none_when_no_semver_tags(monkeypatch):
    from apps.api.src import plugin_update_checker as puc
    from unittest.mock import MagicMock
    import sys

    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "abc123\trefs/tags/random-tag\n"
    fake_proc.stderr = ""
    monkeypatch.setattr(puc.subprocess, "run", lambda *a, **kw: fake_proc)
    monkeypatch.setattr(puc.shutil, "which", lambda binname: "/usr/bin/git")
    fake_routes = MagicMock()
    fake_routes._get_deploy_key_path = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "apps.api.src.routes.plugins", fake_routes)

    assert puc.fetch_latest_git_tag_with_ref("git@example.com:repo.git") is None
