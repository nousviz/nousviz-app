#!/usr/bin/env bash
# ClickHouse health check — returns JSON

PORT="${CLICKHOUSE_PORT:-8123}"
USER="${CLICKHOUSE_USER:-default}"
PW="${CLICKHOUSE_PASSWORD:-}"

if curl -sf "http://127.0.0.1:${PORT}/ping" | grep -q "Ok"; then
  VERSION=$(curl -sf -u "${USER}:${PW}" "http://127.0.0.1:${PORT}/?query=SELECT+version()" 2>/dev/null | head -1 || echo "unknown")
  [ -z "$VERSION" ] && VERSION="unknown"
  echo "{\"ok\": true, \"version\": \"${VERSION}\"}"
else
  echo "{\"ok\": false, \"error\": \"ClickHouse is not responding on port ${PORT}\"}"
fi
