#!/usr/bin/env bash
set -euo pipefail

# ClickHouse utility plugin — install script
# Downloads the ClickHouse binary, writes minimal config, adds PM2 entry.
# Called by the NousViz plugin install flow.

NOUSVIZ_DIR="${NOUSVIZ_DIR:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
CH_DIR="$NOUSVIZ_DIR/plugins/installed/clickhouse"
DATA_DIR="$NOUSVIZ_DIR/data/clickhouse"

echo "Installing ClickHouse..."

# Detect OS and architecture
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$ARCH" in
  x86_64|amd64)   ARCH_TAG="amd64" ;;
  aarch64|arm64)   ARCH_TAG="aarch64" ;;
  *)               echo "ERROR: Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Pre-flight: check minimum memory (ClickHouse needs at least 2GB)
if [ "$OS" = "linux" ]; then
  TOTAL_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
  if [ "$TOTAL_MB" -lt 1800 ]; then
    echo "ERROR: ClickHouse requires at least 2GB RAM. This server has ${TOTAL_MB}MB."
    echo "Consider upgrading the server or using an external ClickHouse instance."
    exit 1
  fi
fi

# Create directories
mkdir -p "$CH_DIR/bin" "$DATA_DIR"/{data,log,tmp,user_files}

# Download binary if not already present
if [ ! -f "$CH_DIR/bin/clickhouse" ]; then
  echo "Downloading ClickHouse binary (~500MB)..."
  if [ "$OS" = "linux" ]; then
    curl -fsSL "https://builds.clickhouse.com/master/${ARCH_TAG}/clickhouse" -o "$CH_DIR/bin/clickhouse"
  elif [ "$OS" = "darwin" ]; then
    if [ "$ARCH_TAG" = "aarch64" ]; then
      curl -fsSL "https://builds.clickhouse.com/master/macos-aarch64/clickhouse" -o "$CH_DIR/bin/clickhouse"
    else
      curl -fsSL "https://builds.clickhouse.com/master/macos/clickhouse" -o "$CH_DIR/bin/clickhouse"
    fi
  else
    echo "ERROR: Unsupported OS: $OS"; exit 1
  fi
  chmod +x "$CH_DIR/bin/clickhouse"
  echo "Binary downloaded."
else
  echo "Binary already exists, skipping download."
fi

# Generate password if not set
CH_PASSWORD="${CLICKHOUSE_PASSWORD:-$(openssl rand -hex 16)}"
CH_USER="${CLICKHOUSE_USER:-default}"
CH_DATABASE="${CLICKHOUSE_DATABASE:-nousviz}"
CH_PORT="${CLICKHOUSE_PORT:-8123}"

# Calculate memory limits based on available RAM (use 25% for CH, min 512MB)
if [ "$OS" = "linux" ]; then
  TOTAL_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
else
  TOTAL_MB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}' || echo 4096)
fi
CH_MEM_BYTES=$(( (TOTAL_MB / 4) * 1024 * 1024 ))
CH_QUERY_MEM_BYTES=$(( CH_MEM_BYTES / 2 ))
[ "$CH_MEM_BYTES" -lt 536870912 ] && CH_MEM_BYTES=536870912  # min 512MB
[ "$CH_QUERY_MEM_BYTES" -lt 134217728 ] && CH_QUERY_MEM_BYTES=134217728  # min 128MB

# Thread sizing — ClickHouse 26.x creates multiple BackgroundSchedulePools (default 512 + 3x16
# threads) during startup. If max_thread_pool_size is too small, init silently deadlocks on
# futex waits (process alive, never binds port). max_thread_pool_size is a ceiling, not a
# preallocation — 2000 is safe. Schedule pools are sized down explicitly for small hosts.
NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
CH_THREAD_POOL=2000
CH_SCHED_POOL=128           # was default 512 — too big for 2-vCPU / 4GB
CH_BUF_SCHED_POOL=8         # was default 16
CH_MB_SCHED_POOL=8          # was default 16
CH_DIST_SCHED_POOL=8        # was default 16
# background_pool_size must satisfy bg_pool * background_merges_mutations_concurrency_ratio (default 2)
# >= number_of_free_entries_in_pool_to_execute_mutation (default 20). So bg_pool >= 10.
# Use 16 as a safe minimum; scale up on larger hosts.
CH_BG_POOL=$(( NPROC * 4 ))
[ "$CH_BG_POOL" -lt 16 ] && CH_BG_POOL=16
CH_QUERY_THREADS=$NPROC
[ "$CH_QUERY_THREADS" -lt 4 ] && CH_QUERY_THREADS=4

echo "Memory limits: server=${CH_MEM_BYTES} bytes, query=${CH_QUERY_MEM_BYTES} bytes"
echo "Threads: global_pool=${CH_THREAD_POOL}, schedule_pool=${CH_SCHED_POOL}, bg=${CH_BG_POOL}, query=${CH_QUERY_THREADS} (nproc=${NPROC})"

# Write server config (users in separate file for ClickHouse compatibility)
cat > "$CH_DIR/config.xml" <<XMLEOF
<clickhouse>
    <logger>
        <level>information</level>
        <log>${DATA_DIR}/log/clickhouse-server.log</log>
        <errorlog>${DATA_DIR}/log/clickhouse-server.err.log</errorlog>
        <size>10M</size>
        <count>3</count>
    </logger>
    <http_port>${CH_PORT}</http_port>
    <tcp_port>9000</tcp_port>
    <listen_host>127.0.0.1</listen_host>
    <path>${DATA_DIR}/data/</path>
    <tmp_path>${DATA_DIR}/tmp/</tmp_path>
    <user_files_path>${DATA_DIR}/user_files/</user_files_path>
    <max_server_memory_usage>${CH_MEM_BYTES}</max_server_memory_usage>
    <max_thread_pool_size>${CH_THREAD_POOL}</max_thread_pool_size>
    <background_schedule_pool_size>${CH_SCHED_POOL}</background_schedule_pool_size>
    <background_buffer_flush_schedule_pool_size>${CH_BUF_SCHED_POOL}</background_buffer_flush_schedule_pool_size>
    <background_message_broker_schedule_pool_size>${CH_MB_SCHED_POOL}</background_message_broker_schedule_pool_size>
    <background_distributed_schedule_pool_size>${CH_DIST_SCHED_POOL}</background_distributed_schedule_pool_size>
    <background_pool_size>${CH_BG_POOL}</background_pool_size>
    <mark_cache_size>67108864</mark_cache_size>
    <max_concurrent_queries>8</max_concurrent_queries>
    <max_connections>64</max_connections>
    <mlock_executable>false</mlock_executable>
    <users_config>users.xml</users_config>
</clickhouse>
XMLEOF

cat > "$CH_DIR/users.xml" <<XMLEOF
<clickhouse>
    <users>
        <default>
            <password>${CH_PASSWORD}</password>
            <networks><ip>127.0.0.1</ip></networks>
            <profile>default</profile>
            <quota>default</quota>
            <access_management>1</access_management>
        </default>
    </users>
    <profiles>
        <default>
            <max_memory_usage>${CH_QUERY_MEM_BYTES}</max_memory_usage>
            <max_threads>${CH_QUERY_THREADS}</max_threads>
        </default>
    </profiles>
    <quotas>
        <default>
            <interval>
                <duration>3600</duration>
                <queries>0</queries>
                <errors>0</errors>
                <result_rows>0</result_rows>
                <read_rows>0</read_rows>
                <execution_time>0</execution_time>
            </interval>
        </default>
    </quotas>
</clickhouse>
XMLEOF

# Write env vars to .env
ENV_FILE="$NOUSVIZ_DIR/.env"
# Remove any existing CLICKHOUSE_ lines
if [ -f "$ENV_FILE" ]; then
  sed -i.bak '/^CLICKHOUSE_/d' "$ENV_FILE" 2>/dev/null || true
  rm -f "${ENV_FILE}.bak"
fi
cat >> "$ENV_FILE" <<EOF
CLICKHOUSE_HOST=127.0.0.1
CLICKHOUSE_PORT=${CH_PORT}
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=${CH_PASSWORD}
CLICKHOUSE_DATABASE=${CH_DATABASE}
EOF

echo "ClickHouse env vars written to .env"

# Start via PM2 if available
if command -v pm2 &>/dev/null; then
  pm2 delete clickhouse 2>/dev/null || true
  pm2 start "$CH_DIR/bin/clickhouse" \
    --name clickhouse \
    --interpreter none \
    -- server --config-file="$CH_DIR/config.xml"
  pm2 save
  echo "ClickHouse started via PM2."
else
  echo "PM2 not found. Start manually: $CH_DIR/bin/clickhouse server --config-file=$CH_DIR/config.xml"
fi

# Wait for startup (may take 15-30s on low-memory servers)
echo "Waiting for ClickHouse to start (this may take up to 60 seconds)..."
for i in $(seq 1 20); do
  if curl -sf "http://127.0.0.1:${CH_PORT}/ping" | grep -q "Ok"; then
    echo "ClickHouse is running."

    # Create default database
    curl -sf "http://127.0.0.1:${CH_PORT}/?user=default&password=${CH_PASSWORD}" \
      -d "CREATE DATABASE IF NOT EXISTS ${CH_DATABASE}" || true

    echo "ClickHouse utility installed successfully."
    exit 0
  fi
  sleep 3
done

echo "WARNING: ClickHouse may not have started yet. Check logs at $DATA_DIR/log/"
echo "On low-memory servers, startup may take longer. Try: curl http://127.0.0.1:${CH_PORT}/ping"
exit 0
