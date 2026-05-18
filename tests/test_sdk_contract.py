"""
SDK contract tests (B121 v0.8.2).

Enforces the rule from sdk/README.md: plugins must only import from
nousviz_sdk, never from apps.*. Violations cause core refactors to
break plugins unpredictably.

Plugin authors in external repos aren't bound by this test — it only
enforces the rule for in-tree plugin code (examples + official). But
it's the canonical statement of the rule for CI and code review.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories searched for violations. Each is either plugin source or an
# SDK example that external authors would copy.
PLUGIN_SEARCH_DIRS = [
    REPO_ROOT / "plugins" / "official",
    REPO_ROOT / "plugins" / "utilities",
    REPO_ROOT / "plugins" / "community",
    REPO_ROOT / "plugins" / "examples",
    REPO_ROOT / "sdk" / "examples",
]


def test_no_plugin_imports_from_apps():
    """Plugins in the main repo must not import from apps.* — the rule is
    sdk/README.md's "SDK as the only contract" section."""
    existing = [d for d in PLUGIN_SEARCH_DIRS if d.exists()]
    if not existing:
        return  # nothing to scan; trivially passing (no plugin code in tree yet)

    result = subprocess.run(
        [
            "grep", "-rn", "-E",
            r"^(from|import)\s+apps\.",
            *[str(d) for d in existing],
            "--include=*.py",
        ],
        capture_output=True,
        text=True,
    )
    # Filter out __pycache__ matches (shouldn't happen — grep ignores binary,
    # but .pyc parent dirs can contain matches if someone committed them).
    hits = [ln for ln in result.stdout.splitlines() if "__pycache__" not in ln]
    assert not hits, (
        f"Found {len(hits)} `apps.*` import(s) in plugin code. "
        f"Plugins must only import from nousviz_sdk (see sdk/README.md).\n\n"
        + "\n".join(hits)
    )


def test_sdk_surface_is_stable():
    """Every public SDK capability lives under nousviz_sdk.*. Smoke-check
    that the documented modules actually import."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "sdk"))

    import nousviz_sdk
    assert hasattr(nousviz_sdk, "get_pg_conn")
    assert hasattr(nousviz_sdk, "router_for_plugin")
    assert hasattr(nousviz_sdk, "get_credential")

    # v0.4.0 additions
    from nousviz_sdk import jobs, schedule, settings
    for mod, required in [
        (jobs, ["heartbeat", "check_cancelled", "get_run_id"]),
        (schedule, ["get_schedule"]),
        (settings, ["get_setting", "set_setting", "list_settings", "delete_setting"]),
    ]:
        for name in required:
            assert hasattr(mod, name), f"{mod.__name__} missing {name}"


def test_sdk_version_matches_pyproject():
    """__version__ in __init__.py must match version in pyproject.toml —
    catches the bump-one-forget-the-other failure mode."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "sdk"))

    import nousviz_sdk
    sdk_version = nousviz_sdk.__version__

    pyproject = (REPO_ROOT / "sdk" / "pyproject.toml").read_text()
    # Extract version line (simple parser — no tomllib dep needed for this check)
    for line in pyproject.splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            toml_version = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            assert toml_version == sdk_version, (
                f"Version mismatch: __version__={sdk_version}, pyproject={toml_version}"
            )
            return
    raise AssertionError("Could not find version in pyproject.toml")
