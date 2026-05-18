#!/bin/bash
# Webhooks health check — always healthy if installed
# Unlike MySQL/ClickHouse, webhooks don't depend on an external service
echo '{"ok": true, "version": "1.0.0"}'
exit 0
