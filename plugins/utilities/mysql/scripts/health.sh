#!/bin/bash
# MySQL health check — returns JSON
HOST="${MYSQL_HOST:-localhost}"
PORT="${MYSQL_PORT:-3306}"
USER="${MYSQL_USER:-}"
PASS="${MYSQL_PASSWORD:-}"

if [ -z "$USER" ]; then
    echo '{"ok": false, "error": "MySQL not configured (no MYSQL_USER)"}'
    exit 1
fi

if command -v mysql &>/dev/null; then
    VERSION=$(mysql -h "$HOST" -P "$PORT" -u "$USER" -p"$PASS" -N -e "SELECT VERSION()" --connect-timeout=5 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "{\"ok\": true, \"version\": \"${VERSION}\"}"
        exit 0
    fi
fi

echo "{\"ok\": false, \"error\": \"MySQL connection failed: ${HOST}:${PORT}\"}"
exit 1
