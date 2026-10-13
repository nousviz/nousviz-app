"""B276: rollback backup dirs (`{slug}.backup.{ts}`) must never be
counted as installed plugins by any scanner."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from src import plugin_loader  # noqa: E402


def _fake_plugin(root: Path, name: str) -> None:
    d = root / name
    (d / "api").mkdir(parents=True)
    (d / "api" / "routes.py").write_text("router = None\n")
    (d / "plugin.yaml").write_text(f"name: {name}\nversion: 0.0.1\n")


def test_is_backup_dir_predicate():
    assert plugin_loader.is_backup_dir("x-leads.backup.2026-06-01T12-00-00")
    assert not plugin_loader.is_backup_dir("x-leads")
    assert not plugin_loader.is_backup_dir("backup-manager")  # name merely containing 'backup'


def test_discover_skips_backup_dirs(tmp_path, monkeypatch):
    _fake_plugin(tmp_path, "x-leads")
    _fake_plugin(tmp_path, "x-leads.backup.2026-06-01T12-00-00")
    monkeypatch.setattr(plugin_loader, "PLUGINS_DIR", tmp_path)
    found = plugin_loader.discover_plugins()
    assert [p["slug"] for p in found] == ["x-leads"]


def test_installed_slugs_skips_backup_dirs(tmp_path, monkeypatch):
    from src.routes import plugins as plugins_routes

    _fake_plugin(tmp_path, "webhooks")
    _fake_plugin(tmp_path, "webhooks.backup.2026-07-01T00-00-00")
    monkeypatch.setattr(plugins_routes, "ACTIVE_PLUGIN_DIRS", [tmp_path])
    assert plugins_routes._installed_slugs() == {"webhooks"}
