#!/usr/bin/env python3
"""Audit every user's role, RBAC overrides, plugin allowlist, and the
resulting plugin-route visibility.

Run on the droplet from the app root (loads .env the same way the API does):

    python3 scripts/audit_users.py

What it answers, per user:
  - Resolved role + active flag + last seen
  - Per-user plugin allowlist (B305): "unrestricted" or [slugs]
  - Which installed plugins they should see in /api/plugins
  - Which `plugin.<slug>.<level>` permissions their role holds AFTER
    `rbac_role_overrides` is layered on top (the resolved set the
    middleware actually checks at request time)
  - Any plugin whose `plugin.<slug>.read` permission is MISSING from
    their resolved set — those are the routes that will 403 for them

It also dumps:
  - All rows in `rbac_role_overrides` (so you can see if an admin
    revoked plugin perms via the matrix UI)
  - The set of `plugin.<slug>.<level>` permissions registered into
    `ROLE_PERMISSIONS` by the plugin loader at startup — if a plugin
    is installed on disk but missing here, the loader didn't register
    it and every non-admin will 403 on that plugin's routes

Output: prints a human-readable report + writes the full data to
`./audit_users_report.json` for further analysis.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Load .env the same way scripts/dev.sh does — the API reads these too.
_ENV_PATH = REPO / ".env"
if _ENV_PATH.exists():
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        # Don't clobber already-set vars (systemd / pm2 env wins).
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# Import after .env is loaded — db module reads POSTGRES_* at import time.
from apps.api.src.db import get_pg_conn  # noqa: E402
from apps.api.src.rbac.permissions import (  # noqa: E402
    ROLE_PERMISSIONS,
    all_permissions_for_role,
)
from apps.api.src.rbac.plugin_visibility import (  # noqa: E402
    allowed_plugin_slugs_for_user,
    is_per_user_filter_enabled,
)
from apps.api.src.plugin_manifest import LEVELS, permission_string  # noqa: E402


# ── Helpers ─────────────────────────────────────────────────────────────


def _installed_plugins_from_disk() -> list[str]:
    """Walk the plugin dirs the API walks at boot; return slug list.

    Matches `list_plugins`'s ACTIVE_PLUGIN_DIRS scan so we report on
    exactly the set the running API will register.
    """
    try:
        from apps.api.src.routes.plugins import ACTIVE_PLUGIN_DIRS
        import yaml
    except Exception as e:
        print(f"  ! could not import ACTIVE_PLUGIN_DIRS: {e}")
        return []

    slugs: list[str] = []
    for base_dir in ACTIVE_PLUGIN_DIRS:
        if not base_dir.exists():
            continue
        for d in sorted(base_dir.iterdir()):
            if not d.is_dir():
                continue
            manifest = d / "plugin.yaml"
            if not manifest.exists():
                continue
            try:
                data = yaml.safe_load(manifest.read_text())
                slugs.append(data.get("name", d.name))
            except Exception as e:
                print(f"  ! failed to parse {manifest}: {e}")
    return slugs


def _fmt_dt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


# ── Audit ───────────────────────────────────────────────────────────────


def audit() -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filter_flag_on": is_per_user_filter_enabled(),
        "installed_plugins_on_disk": [],
        "rbac_role_overrides": [],
        "role_resolved_permissions": {},
        "plugin_permission_registration_gap": [],
        "users": [],
    }

    installed = _installed_plugins_from_disk()
    report["installed_plugins_on_disk"] = installed

    # Pull rbac_role_overrides — this is the most common cause of
    # role-level plugin 403s if an admin clicked through the matrix UI.
    # Use its own connection so a missing-table error doesn't poison the
    # transaction state for the queries below.
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT role, permission, granted,
                       updated_at::text, updated_by::text, note
                FROM rbac_role_overrides
                ORDER BY role, permission
                """
            )
            for row in cur.fetchall():
                report["rbac_role_overrides"].append({
                    "role": row[0],
                    "permission": row[1],
                    "granted": row[2],
                    "updated_at": row[3],
                    "updated_by": row[4],
                    "note": row[5],
                })
    except Exception as e:
        report["rbac_role_overrides_error"] = str(e)

    # Resolved permission set per built-in role.
    for role in ROLE_PERMISSIONS.keys():
        try:
            report["role_resolved_permissions"][role] = sorted(
                all_permissions_for_role(role)
            )
        except Exception as e:
            report["role_resolved_permissions"][role] = f"error: {e}"

    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Gap check: for each installed plugin, is `plugin.<slug>.read`
        # in `viewer`'s resolved permissions? If not, every viewer 403s
        # on that plugin's routes.
        viewer_perms = set(report["role_resolved_permissions"].get("viewer", []))
        analyst_perms = set(report["role_resolved_permissions"].get("analyst", []))
        for slug in installed:
            for level in LEVELS:
                perm = permission_string(slug, level)
                if level == "read":
                    if perm not in viewer_perms:
                        report["plugin_permission_registration_gap"].append({
                            "permission": perm,
                            "missing_from_roles": [
                                r for r, expected_to_hold in (
                                    ("viewer", True),
                                    ("analyst", True),
                                ) if expected_to_hold and perm not in (
                                    viewer_perms if r == "viewer" else analyst_perms
                                )
                            ],
                        })

        # Per-user audit.
        cur.execute(
            """
            SELECT id::text, email, name, role, is_active,
                   last_login::text, last_seen_at::text, created_at::text
            FROM users
            ORDER BY email
            """
        )
        users = cur.fetchall()

    for row in users:
        user_id, email, name, role, is_active, last_login, last_seen, created = row
        try:
            allowlist = allowed_plugin_slugs_for_user(user_id, role or "")
        except Exception as e:
            allowlist = f"error: {e}"

        resolved_perms = report["role_resolved_permissions"].get(role, [])
        # What plugin sub-routes will the role 403 on?
        missing_plugin_read = []
        for slug in installed:
            perm = permission_string(slug, "read")
            if perm not in resolved_perms:
                missing_plugin_read.append(perm)

        if allowlist is None:
            visible_plugins = "unrestricted (all)"
        elif isinstance(allowlist, set):
            visible_plugins = sorted(allowlist)
        else:
            visible_plugins = allowlist  # error string

        report["users"].append({
            "id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "is_active": is_active,
            "last_login": last_login,
            "last_seen_at": last_seen,
            "created_at": created,
            "plugin_allowlist": (
                "unrestricted" if allowlist is None else
                (sorted(allowlist) if isinstance(allowlist, set) else allowlist)
            ),
            "visible_plugins_via_b305": visible_plugins,
            "missing_plugin_read_perms": missing_plugin_read,
        })

    return report


# ── Render ──────────────────────────────────────────────────────────────


def render(report: dict[str, Any]) -> None:
    print()
    print("=" * 78)
    print("  NousViz user / permission audit")
    print(f"  Generated: {report['generated_at']}")
    print(f"  Per-user plugin filter (B305) enabled: {report['filter_flag_on']}")
    print("=" * 78)

    print()
    print(f"Installed plugins on disk ({len(report['installed_plugins_on_disk'])}):")
    for s in report["installed_plugins_on_disk"]:
        print(f"  - {s}")

    print()
    print(f"rbac_role_overrides rows ({len(report['rbac_role_overrides'])}):")
    if not report["rbac_role_overrides"]:
        print("  (none — no admin edits via the matrix UI)")
    for row in report["rbac_role_overrides"]:
        marker = "DENY" if not row["granted"] else "grant"
        print(
            f"  [{marker}] role={row['role']:<10} perm={row['permission']:<40} "
            f"at={row['updated_at']} by={row['updated_by']}"
        )

    print()
    print("Resolved permissions per role (post-override):")
    for role, perms in report["role_resolved_permissions"].items():
        if isinstance(perms, str):
            print(f"  {role}: {perms}")
            continue
        plugin_perms = [p for p in perms if p.startswith("plugin.")]
        core_perms = [p for p in perms if not p.startswith("plugin.")]
        print(f"  {role}: {len(core_perms)} core perms, {len(plugin_perms)} plugin perms")

    print()
    print("Gap check — installed plugins missing `plugin.<slug>.read` for viewer/analyst:")
    if not report["plugin_permission_registration_gap"]:
        print("  (none — every installed plugin has its read permission registered "
              "and granted to viewer+)")
    for gap in report["plugin_permission_registration_gap"]:
        print(f"  ! {gap['permission']} missing from: {', '.join(gap['missing_from_roles'])}")

    print()
    print(f"Users ({len(report['users'])}):")
    print(f"  {'email':<40} {'role':<12} {'active':<7} {'allowlist':<14} {'missing_reads':<6}")
    print(f"  {'-'*40} {'-'*12} {'-'*7} {'-'*14} {'-'*6}")
    for u in report["users"]:
        al = u["plugin_allowlist"]
        if al == "unrestricted":
            al_disp = "unrestricted"
        elif isinstance(al, list):
            al_disp = f"{len(al)} slugs" if al else "(empty)"
        else:
            al_disp = "error"
        miss = len(u["missing_plugin_read_perms"])
        print(
            f"  {u['email'][:40]:<40} {(u['role'] or '?'):<12} "
            f"{('yes' if u['is_active'] else 'NO'):<7} {al_disp:<14} {miss}"
        )

    # Per-user detail for any with restrictions or gaps.
    for u in report["users"]:
        al = u["plugin_allowlist"]
        miss = u["missing_plugin_read_perms"]
        if al == "unrestricted" and not miss:
            continue
        print()
        print(f"  {u['email']} ({u['role']}):")
        if isinstance(al, list):
            print(f"    allowlist: {al if al else '(empty — sees ZERO plugins)'}")
        if miss:
            print(f"    missing plugin.<slug>.read perms ({len(miss)}):")
            for p in miss:
                print(f"      - {p}")


def main() -> int:
    try:
        report = audit()
    except Exception as e:
        print(f"FATAL: audit failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

    render(report)

    out = REPO / "audit_users_report.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print()
    print(f"Full JSON report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
