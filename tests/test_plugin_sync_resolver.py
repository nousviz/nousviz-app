"""Pure-logic tests for resolve_sync_script (B201).

The resolver reads `sync.script` from a plugin's manifest and falls back
to `src/sync.py` when absent. Existence checks belong at the call site;
these tests cover the resolution logic only.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_resolve_uses_manifest_when_present(tmp_path):
    """Manifest declares sync.script — resolver returns that path."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "my-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        "name: my-plugin\nversion: 1.0.0\nsync:\n  script: src/foo_sync.py\n"
    )

    abs_path, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/foo_sync.py"
    assert abs_path == plugin_dir / "src" / "foo_sync.py"


def test_resolve_falls_back_to_default_when_manifest_silent(tmp_path):
    """Manifest exists but has no sync block — resolver returns src/sync.py."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "legacy-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text("name: legacy-plugin\nversion: 1.0.0\n")

    abs_path, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/sync.py"
    assert abs_path == plugin_dir / "src" / "sync.py"


def test_resolve_falls_back_when_manifest_missing(tmp_path):
    """No plugin.yaml on disk — resolver returns src/sync.py without raising."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "ghost-plugin"
    plugin_dir.mkdir()
    # No plugin.yaml at all.

    abs_path, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/sync.py"
    assert abs_path == plugin_dir / "src" / "sync.py"


def test_resolve_strips_whitespace(tmp_path):
    """Manifest declares the path with surrounding whitespace — resolver trims."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "ws-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        "name: ws-plugin\nsync:\n  script: '   src/ws_sync.py   '\n"
    )

    _abs, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/ws_sync.py"


def test_resolve_falls_back_on_malformed_yaml(tmp_path):
    """Unparseable YAML — resolver returns default rather than raising."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "broken-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(":\nthis: is: not: valid yaml\n  - [")

    _abs, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/sync.py"


def test_resolve_falls_back_on_non_string_script(tmp_path):
    """sync.script is not a string — resolver returns default."""
    from apps.api.src.plugin_sync import resolve_sync_script

    plugin_dir = tmp_path / "weird-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        "name: weird-plugin\nsync:\n  script: 42\n"
    )

    _abs, rel = resolve_sync_script(plugin_dir)
    assert rel == "src/sync.py"
