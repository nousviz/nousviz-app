#!/usr/bin/env python3
"""
B251 (v0.9.10.0.3) — Operator-recovery CLI for password reset.

Use when:
- SMTP isn't configured (so the email-flow forgot-password path doesn't work)
- The only superadmin lost their password and there's no other way in

Usage:
    /opt/nousviz/.venv/bin/python apps/api/scripts/reset_password.py <email>

Or via the wrapper:
    /opt/nousviz/scripts/reset-password.sh <email>

The script prompts for the new password (no echo) and updates the
users.password_hash row directly via psycopg2 with parameterized SQL —
bypassing the API entirely. Bcrypt's `$2b$12$...` hash format is safe
in the parameterized binding (no shell interpolation hazard).

Exit codes:
    0  — password updated successfully
    1  — user not found, inactive, or other operational error
    2  — invalid usage
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

# Allow running from anywhere — locate the repo's venv-installed packages.
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset a NousViz user's password via direct DB write. "
                    "Bypasses the email-link flow; useful when SMTP is "
                    "unavailable or the only superadmin is locked out.",
    )
    parser.add_argument("email", help="Email of the user whose password to reset.")
    parser.add_argument(
        "--from-stdin",
        action="store_true",
        help="Read the new password from stdin (one line) instead of prompting. "
             "Useful for non-interactive invocation. NOT recommended for "
             "manual use (the password may end up in shell history).",
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email or "@" not in email:
        print(f"Error: invalid email: {args.email!r}", file=sys.stderr)
        return 2

    # Load env (POSTGRES_PASSWORD etc.) so we can connect.
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(REPO_ROOT / ".env", override=True)
    except ImportError:
        pass  # .env is optional if env vars are already set

    # Lazy imports (after sys.path + env load).
    try:
        import bcrypt
        from apps.api.src.db import get_pg_conn, dict_cursor
    except Exception as exc:
        print(f"Error: failed to import dependencies: {exc}", file=sys.stderr)
        print(f"  Try running with the project venv:\n  "
              f"{REPO_ROOT}/.venv/bin/python {Path(__file__).relative_to(REPO_ROOT)} {email}",
              file=sys.stderr)
        return 1

    # Look up the user first — we want to fail fast on "user not found"
    # before asking for a password.
    try:
        with get_pg_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute(
                "SELECT id, email, role, is_active FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()
    except Exception as exc:
        print(f"Error: database query failed: {exc}", file=sys.stderr)
        return 1

    if not user:
        print(f"Error: user not found: {email}", file=sys.stderr)
        return 1
    if not user["is_active"]:
        print(f"Error: user is inactive: {email}", file=sys.stderr)
        print("  Reactivate via the API (POST /api/auth/users/{id}/reactivate) before resetting password.",
              file=sys.stderr)
        return 1

    # Get new password.
    if args.from_stdin:
        new_password = sys.stdin.readline().rstrip("\n")
    else:
        try:
            new_password = getpass.getpass("New password (will not echo): ")
            confirm = getpass.getpass("Confirm new password: ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            return 1
        if new_password != confirm:
            print("Error: passwords don't match.", file=sys.stderr)
            return 1

    if not new_password or len(new_password) < 8:
        print("Error: password must be at least 8 characters.", file=sys.stderr)
        return 1

    # Hash and update. Parameterized SQL handles bcrypt's `$` correctly.
    try:
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    except Exception as exc:
        print(f"Error: bcrypt hash failed: {exc}", file=sys.stderr)
        return 1

    # Sanity check: hash should be 60 chars and start with $2b$12$.
    if not (len(password_hash) == 60 and password_hash.startswith("$2b$12$")):
        print(f"Error: bcrypt produced unexpected hash shape (len={len(password_hash)}).",
              file=sys.stderr)
        return 1

    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET password_hash = %s, updated_at = now() "
                "WHERE id = %s",
                (password_hash, user["id"]),
            )
            # Kill all active sessions for the user — same security
            # property as the email-link reset path (a hijacker with a
            # stolen session can't keep using it after recovery).
            cur.execute(
                "UPDATE user_sessions SET expires_at = now() "
                "WHERE user_id = %s AND expires_at > now()",
                (user["id"],),
            )

            # Audit row to rbac_config_audit (action='password_reset_cli').
            try:
                from apps.api.src.rbac.config_audit import log_config_change
                log_config_change(
                    cur,
                    action="password_reset_cli",
                    target_role=user["role"] or "unknown",
                    target_permission=None,
                    actor_user_id=str(user["id"]),
                    actor_role=user["role"],
                    before_state=None,
                    after_state={
                        "method": "scripts/reset-password.sh",
                        "sessions_killed": True,
                    },
                    note=f"Operator-recovery password reset for {email}",
                )
            except Exception as exc:
                # Audit best-effort — the password change itself succeeded.
                print(f"Warning: audit-log write failed: {exc} (password change succeeded anyway)",
                      file=sys.stderr)
    except Exception as exc:
        print(f"Error: database update failed: {exc}", file=sys.stderr)
        return 1

    print(f"Password updated for {email} (role: {user['role']}).")
    print(f"  Hash: {password_hash[:16]}... ({len(password_hash)} chars)")
    print("  All active sessions killed; user must log in with the new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
