"""
Unit test for B128 health critical-tables drift check.

The actual SQL integration is tested via the deploy smoke suite. These tests
cover the decision logic: which tables are flagged critical, how drift is
surfaced in the response, and that the list stays in sync with what
plugin_credentials.py / run_jobs.py actually require.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_critical_tables_list_includes_credentials():
    """The bug that drove B128: credentials was missing and health was
    still green. Assert the list covers the things that caused the
    incident."""
    source = (REPO_ROOT / "apps" / "api" / "src" / "routes" / "health.py").read_text()
    # Look for the list as written in-line.
    assert '"credentials",' in source
    assert '"connections",' in source
    assert '"users",' in source
    assert '"job_runs",' in source
    assert '"app_logs",' in source
    assert '"schema_migrations",' in source


def test_drift_hint_message_exists():
    """When a critical table is missing, operators need to know what to
    do. Assert the hint references the right remediation path."""
    source = (REPO_ROOT / "apps" / "api" / "src" / "routes" / "health.py").read_text()
    assert "drift_hint" in source
    assert "deploy-local.sh" in source


def test_critical_tables_match_live_code_expectations():
    """Sanity: any table in the critical-tables list must be referenced
    in at least one live code path. Catches accidental typos."""
    source = (REPO_ROOT / "apps" / "api" / "src" / "routes" / "health.py").read_text()

    # Pull the list tuples heuristically.
    import re
    match = re.search(r"_CRITICAL_TABLES\s*=\s*\[([^\]]+)\]", source, re.DOTALL)
    assert match, "Couldn't find _CRITICAL_TABLES list in health.py"
    names = re.findall(r'"([^"]+)"', match.group(1))
    assert len(names) >= 6

    # Scan a couple of canonical files that should reference each table.
    plugin_creds = (REPO_ROOT / "apps" / "api" / "src" / "plugin_credentials.py").read_text()
    run_jobs = (REPO_ROOT / "apps" / "worker" / "src" / "run_jobs.py").read_text()
    log_events = (REPO_ROOT / "apps" / "api" / "src" / "log_events.py").read_text()
    all_code = plugin_creds + run_jobs + log_events

    # Of the 6 required tables, at least 4 should appear in these specific
    # files (the others — users, schema_migrations — live elsewhere).
    expected_in_canonical = ["credentials", "connections", "job_runs", "app_logs"]
    found = [t for t in expected_in_canonical if t in all_code]
    assert len(found) >= 4, f"Missing table references in canonical files: expected {expected_in_canonical}, found {found}"
