#!/usr/bin/env python3
"""
Migrate existing fusion records into user_dashboards (v0.10.0.x).

Fusions and user dashboards have near-identical shapes:

    fusions(id, name, slug, description, widgets jsonb, layout jsonb, is_default)
    user_dashboards(id, name, slug, description, widgets jsonb, layout jsonb,
                    sources jsonb, created_by)

For each fusion, this script inserts a user_dashboards row with the same
widgets + layout. The dashboard slug defaults to the fusion slug; on
conflict it falls back to `<slug>-from-fusion` so existing dashboards
aren't overwritten.

Idempotent: if a dashboard with the target slug already exists AND its
widgets blob equals the fusion's widgets blob, the script skips it
(treats it as already-migrated). Otherwise it inserts the conflict-
suffixed version.

Usage:
    python scripts/migrate_fusions_to_dashboards.py [--dry-run] [--db-url URL]

Output:
    Prints one line per fusion (migrated / skipped / conflict-renamed)
    and a final summary.

Safe to run multiple times. Does NOT delete the fusion rows — that
happens in a later phase after the migration is verified.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional


def _db_url_from_env() -> Optional[str]:
    """Resolve the standard NousViz DB URL. Mirrors apps/api/src/db.py
    behaviour without importing it (this script may run outside the
    app's venv/path)."""
    return os.environ.get("DATABASE_URL") or os.environ.get("NOUSVIZ_DATABASE_URL")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without modifying the database.",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Postgres URL. Defaults to $DATABASE_URL / $NOUSVIZ_DATABASE_URL.",
    )
    args = parser.parse_args()

    db_url = args.db_url or _db_url_from_env()
    if not db_url:
        print(
            "error: no DB URL. Set $DATABASE_URL or pass --db-url.",
            file=sys.stderr,
        )
        return 2

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        print("error: psycopg2 not installed in this venv.", file=sys.stderr)
        return 2

    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT name, slug, description, widgets, layout FROM fusions ORDER BY slug")
            fusions = cur.fetchall()

        print(f"Found {len(fusions)} fusion record(s) to consider.")
        if not fusions:
            print("Nothing to migrate.")
            return 0

        migrated = 0
        skipped = 0
        renamed = 0

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for f in fusions:
                target_slug = f["slug"]
                cur.execute(
                    "SELECT widgets FROM user_dashboards WHERE slug = %s",
                    (target_slug,),
                )
                existing = cur.fetchone()

                # Already migrated? — same slug + same widgets blob.
                if existing:
                    existing_widgets = (
                        existing["widgets"]
                        if isinstance(existing["widgets"], list)
                        else json.loads(existing["widgets"] or "[]")
                    )
                    fusion_widgets = (
                        f["widgets"]
                        if isinstance(f["widgets"], list)
                        else json.loads(f["widgets"] or "[]")
                    )
                    if existing_widgets == fusion_widgets:
                        print(f"  skip   {f['slug']}: dashboard with same widgets already exists")
                        skipped += 1
                        continue
                    target_slug = f"{f['slug']}-from-fusion"
                    renamed += 1
                    # Make sure the renamed slug is also free.
                    cur.execute(
                        "SELECT 1 FROM user_dashboards WHERE slug = %s",
                        (target_slug,),
                    )
                    if cur.fetchone():
                        print(
                            f"  skip   {f['slug']}: target slug {target_slug!r} also taken; "
                            f"resolve manually."
                        )
                        skipped += 1
                        renamed -= 1
                        continue

                action = f"would insert" if args.dry_run else "insert"
                print(f"  {action:<6} {target_slug}: {f['name']!r}")

                if not args.dry_run:
                    cur.execute(
                        """
                        INSERT INTO user_dashboards (name, slug, description, widgets, layout, sources, created_by)
                        VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, '[]'::jsonb, NULL)
                        """,
                        (
                            f["name"],
                            target_slug,
                            f["description"] or "",
                            json.dumps(f["widgets"]) if not isinstance(f["widgets"], str) else f["widgets"],
                            json.dumps(f["layout"]) if not isinstance(f["layout"], str) else f["layout"],
                        ),
                    )
                migrated += 1

        if args.dry_run:
            conn.rollback()
            print(
                f"\nDRY RUN — no changes committed.\n"
                f"Would migrate: {migrated}, skip: {skipped}, rename: {renamed}"
            )
        else:
            conn.commit()
            print(
                f"\nDone. Migrated: {migrated}, skipped (already migrated): {skipped}, "
                f"renamed on conflict: {renamed}"
            )
        return 0

    except Exception as exc:
        conn.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
