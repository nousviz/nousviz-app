#!/bin/bash
# NousViz — Database backup
#
# Creates a compressed pg_dump of the nousviz database.
# Stores in BACKUP_DIR (default: ./backups) with timestamped filenames.
# Keeps the last N backups (default: 7), deletes older ones.
#
# Usage:
#   ./scripts/backup.sh                    # backup with defaults
#   ./scripts/backup.sh --keep 30          # keep 30 backups
#   ./scripts/backup.sh --dir /mnt/backup  # custom backup directory
#
# Cron (daily at 2am):
#   0 2 * * * cd /opt/nousviz && ./scripts/backup.sh >> logs/backup.log 2>&1

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$APP_DIR/.env" ]; then
    set -a; source "$APP_DIR/.env"; set +a
fi

BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP="${BACKUP_KEEP:-7}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-nousviz}"
DB_USER="${POSTGRES_USER:-nousviz}"

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep) KEEP="$2"; shift 2 ;;
        --dir) BACKUP_DIR="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Run ────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="nousviz_${TIMESTAMP}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

echo "$(date '+%Y-%m-%d %H:%M:%S') Starting backup → $FILEPATH"

export PGPASSWORD="${POSTGRES_PASSWORD:-}"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
    --no-owner --no-privileges --clean --if-exists \
    | gzip > "$FILEPATH"

SIZE=$(du -sh "$FILEPATH" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') Backup complete: $FILENAME ($SIZE)"

# ── Retention ──────────────────────────────────────────────────────────
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/nousviz_*.sql.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - KEEP))
    ls -1t "$BACKUP_DIR"/nousviz_*.sql.gz | tail -n "$REMOVE_COUNT" | while read f; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') Removing old backup: $(basename "$f")"
        rm -f "$f"
    done
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') Backups: $KEEP kept, $(ls -1 "$BACKUP_DIR"/nousviz_*.sql.gz 2>/dev/null | wc -l) total"
