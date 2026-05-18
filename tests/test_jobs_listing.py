"""Tests for /system/jobs listing logic (B202).

The listing must surface plugins whose sync script lives at any path
declared in the manifest, not just the legacy src/sync.py default.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_plugin_sync_jobs_includes_default_and_custom_scripts(tmp_path, monkeypatch):
    """Default src/sync.py plugins AND custom sync.script plugins both appear.
    Plugins whose declared script is missing on disk are excluded."""
    from apps.api.src.routes import jobs as jobs_module

    installed = tmp_path / "installed"
    installed.mkdir()

    # Plugin A: default sync path (src/sync.py)
    pa = installed / "default-plugin"
    (pa / "src").mkdir(parents=True)
    (pa / "src" / "sync.py").write_text("# stub\n")
    (pa / "plugin.yaml").write_text(
        "name: default-plugin\nversion: 1.0.0\nsync:\n  schedule: '0 */6 * * *'\n"
    )

    # Plugin B: custom sync.script path
    pb = installed / "custom-plugin"
    (pb / "src").mkdir(parents=True)
    (pb / "src" / "custom_sync.py").write_text("# stub\n")
    (pb / "plugin.yaml").write_text(
        "name: custom-plugin\nversion: 1.0.0\nsync:\n  script: src/custom_sync.py\n  schedule: '0 */4 * * *'\n"
    )

    # Plugin C: declared sync.script but file missing — should NOT appear
    pc = installed / "ghost-plugin"
    pc.mkdir()
    (pc / "plugin.yaml").write_text(
        "name: ghost-plugin\nversion: 1.0.0\nsync:\n  script: src/missing.py\n"
    )

    # Plugin D: no sync block at all — should NOT appear
    pd = installed / "no-sync-plugin"
    pd.mkdir()
    (pd / "plugin.yaml").write_text("name: no-sync-plugin\nversion: 1.0.0\n")

    # Empty community dir to satisfy the glob.
    community = tmp_path / "community"
    community.mkdir()

    monkeypatch.setattr(jobs_module, "INSTALLED_DIR", installed)
    monkeypatch.setattr(jobs_module, "COMMUNITY_DIR", community)

    result = jobs_module._plugin_sync_jobs([])
    slugs = {entry["id"].removesuffix("-sync") for entry in result}

    assert "default-plugin" in slugs, "default src/sync.py plugin should appear"
    assert "custom-plugin" in slugs, "B202: custom sync.script plugin should appear"
    assert "ghost-plugin" not in slugs, "plugin with declared-but-missing script must be excluded"
    assert "no-sync-plugin" not in slugs, "plugin without any sync should be excluded"


def test_plugin_sync_jobs_cmd_reflects_resolved_path(tmp_path, monkeypatch):
    """B202: the `cmd` field on the listing matches the resolved script path,
    not a hardcoded src/sync.py."""
    from apps.api.src.routes import jobs as jobs_module

    installed = tmp_path / "installed"
    installed.mkdir()

    pb = installed / "myplugin"
    (pb / "src").mkdir(parents=True)
    (pb / "src" / "myplugin_sync.py").write_text("# stub\n")
    (pb / "plugin.yaml").write_text(
        "name: myplugin\nversion: 1.0.0\nsync:\n  script: src/myplugin_sync.py\n"
    )

    community = tmp_path / "community"
    community.mkdir()

    monkeypatch.setattr(jobs_module, "INSTALLED_DIR", installed)
    monkeypatch.setattr(jobs_module, "COMMUNITY_DIR", community)

    result = jobs_module._plugin_sync_jobs([])
    entry = next(e for e in result if e["id"] == "myplugin-sync")
    assert entry["command"] == "plugins/installed/myplugin/src/myplugin_sync.py"
