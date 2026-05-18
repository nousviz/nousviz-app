#!/usr/bin/env bash
set -euo pipefail

# ClickHouse utility plugin — uninstall script
# Honours NOUSVIZ_REMOVE_DATA=1 (set by the platform) to delete the data dir.
# When not set, preserves data so reinstall can pick it up.

NOUSVIZ_DIR="${NOUSVIZ_DIR:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
CH_DIR="$NOUSVIZ_DIR/plugins/installed/clickhouse"
DATA_DIR="$NOUSVIZ_DIR/data/clickhouse"
REMOVE_DATA="${NOUSVIZ_REMOVE_DATA:-0}"

echo "Uninstalling ClickHouse utility..."

# Stop PM2 process
if command -v pm2 &>/dev/null; then
  pm2 delete clickhouse 2>/dev/null || true
  pm2 save 2>/dev/null || true
fi

# Remove binary and config
rm -rf "$CH_DIR/bin" "$CH_DIR/config.xml" "$CH_DIR/scripts"

# Remove CLICKHOUSE_ env vars from .env
ENV_FILE="$NOUSVIZ_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  sed -i.bak '/^CLICKHOUSE_/d' "$ENV_FILE" 2>/dev/null || true
  rm -f "${ENV_FILE}.bak"
fi

if [ "$REMOVE_DATA" = "1" ]; then
  rm -rf "$DATA_DIR"
  echo "ClickHouse utility uninstalled (data removed)."
else
  echo "ClickHouse utility uninstalled."
  echo "Data directory preserved at: $DATA_DIR"
fi
