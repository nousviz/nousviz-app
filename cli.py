#!/usr/bin/env python3
"""
NousViz CLI

Usage:
    nousviz start              Start all services (API, frontend, worker)
    nousviz stop               Stop all services
    nousviz status             Show system health and connection status
    nousviz sync [plugin]      Trigger a data sync (default: all plugins)
    nousviz setup              First-time setup (schema, deps, .env)
    nousviz mcp-setup          Configure NousViz as an MCP server for Claude
    nousviz dev                Start in development mode with hot reload
    nousviz logs               Show recent logs
    nousviz version            Show version info
    nousviz plugin install <slug>   Install a plugin from official registry or GitHub
    nousviz plugin uninstall <slug> Remove an installed plugin
    nousviz plugin list             List all installed plugins
"""

import os
import sys
import json
import signal
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "bin" / "python3"
PID_DIR = ROOT / ".pids"
ENV_FILE = ROOT / ".env"
VERSION_FILE = ROOT / "VERSION"
VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0.0.0"


def _print(msg: str, style: str = ""):
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "blue": "\033[94m", "bold": "\033[1m", "dim": "\033[2m"}
    reset = "\033[0m"
    prefix = colors.get(style, "")
    print(f"{prefix}{msg}{reset}")


def _check_postgres():
    """Verify Postgres is reachable. Print a clear error and exit if not."""
    import socket
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
    except OSError:
        _print(f"Postgres is not reachable at {host}:{port}.", "red")
        _print("  Run ./scripts/setup.sh to install and start Postgres.", "dim")
        sys.exit(1)


def _check_venv():
    if not VENV_PYTHON.exists():
        _print("Python venv not found. Running setup...", "yellow")
        cmd_setup()


def _load_env():
    """Load .env file into environment."""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _save_pid(name: str, pid: int):
    PID_DIR.mkdir(exist_ok=True)
    (PID_DIR / f"{name}.pid").write_text(str(pid))


def _get_pid(name: str) -> int | None:
    pid_file = PID_DIR / f"{name}.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return pid
        except (ProcessLookupError, ValueError):
            pid_file.unlink(missing_ok=True)
    return None


def _kill_pid(name: str) -> bool:
    pid = _get_pid(name)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            (PID_DIR / f"{name}.pid").unlink(missing_ok=True)
            return True
        except ProcessLookupError:
            pass
    return False


# ── Commands ──────────────────────────────────────────────────────────


def cmd_start():
    """Start all NousViz services."""
    _load_env()
    _check_postgres()
    _check_venv()

    api_port = os.environ.get("API_PORT", "8000")
    web_port = os.environ.get("WEB_PORT", "5173")

    _print("Starting NousViz...", "bold")

    # 1. API server
    if _get_pid("api"):
        _print("  API server already running", "dim")
    else:
        _print(f"  Starting API server on port {api_port}...", "dim")
        env = os.environ.copy()
        proc = subprocess.Popen(
            [str(VENV_PYTHON), "-m", "uvicorn", "apps.api.src.main:app", "--port", api_port],
            cwd=ROOT, env=env,
            stdout=open(ROOT / ".logs" / "api.log", "a") if (ROOT / ".logs").exists() else subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        _save_pid("api", proc.pid)

    # 3. Frontend
    if _get_pid("web"):
        _print("  Frontend already running", "dim")
    else:
        _print(f"  Starting frontend on port {web_port}...", "dim")
        web_dir = ROOT / "apps" / "web"
        if not (web_dir / "node_modules").exists():
            subprocess.run(["npm", "install"], cwd=web_dir, capture_output=True)
        proc = subprocess.Popen(
            ["npx", "vite", "--port", web_port],
            cwd=web_dir,
            stdout=open(ROOT / ".logs" / "web.log", "a") if (ROOT / ".logs").exists() else subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        _save_pid("web", proc.pid)

    import time
    time.sleep(2)

    _print("")
    _print("  NousViz is running!", "green")
    _print(f"  App:  http://localhost:{web_port}", "blue")
    _print(f"  API:  http://localhost:{api_port}", "blue")
    _print(f"  Health: http://localhost:{api_port}/api/health", "dim")
    _print("")


def cmd_stop():
    """Stop all NousViz services."""
    _load_env()
    web_port = os.environ.get("WEB_PORT", "5173")

    _print("Stopping NousViz...", "bold")

    killed_api = _kill_pid("api")
    killed_web = _kill_pid("web")

    if killed_api:
        _print("  Stopped API server", "dim")
    if killed_web:
        _print("  Stopped frontend", "dim")

    # Also kill by process name as fallback
    subprocess.run(["pkill", "-f", "uvicorn apps.api"], capture_output=True)
    subprocess.run(["pkill", "-f", f"vite.*{web_port}"], capture_output=True)

    _print("")
    _print("  Services stopped.", "dim")
    _print("  Postgres continues running as a native service.", "dim")
    _print("  To stop Postgres: brew services stop postgresql@16  (macOS)", "dim")


def cmd_status():
    """Show system health."""
    _load_env()
    api_port = os.environ.get("API_PORT", "8000")

    _print("NousViz Status", "bold")
    _print(f"  Version: {VERSION}", "dim")
    _print("")

    # Check processes
    api_pid = _get_pid("api")
    web_pid = _get_pid("web")
    _print(f"  API server:  {'running (pid ' + str(api_pid) + ')' if api_pid else 'stopped'}", "green" if api_pid else "red")
    _print(f"  Frontend:    {'running (pid ' + str(web_pid) + ')' if web_pid else 'stopped'}", "green" if web_pid else "red")

    # Check Postgres
    import socket
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    try:
        with socket.create_connection((pg_host, pg_port), timeout=2):
            _print(f"  Postgres: reachable at {pg_host}:{pg_port}", "green")
    except OSError:
        _print(f"  Postgres: not reachable at {pg_host}:{pg_port}", "red")
        _print("  Run ./scripts/setup.sh to install and start Postgres", "dim")

    # Check API health
    if api_pid:
        try:
            import urllib.request
            req = urllib.request.urlopen(f"http://localhost:{api_port}/api/health", timeout=3)
            health = json.loads(req.read())
            pg = health.get("services", {}).get("postgres", {})
            _print(f"\n  Postgres (API): {pg.get('status', 'unknown')}", "green" if pg.get("status") == "connected" else "red")
            ch = health.get("services", {}).get("clickhouse", {})
            if ch.get("status") not in (None, "unavailable"):
                _print(f"  ClickHouse: {ch.get('status', 'unknown')}", "green" if ch.get("status") == "connected" else "red")
            _print(f"  API version: {health.get('version', 'unknown')}", "dim")
        except Exception:
            _print("\n  Could not reach API health endpoint", "yellow")


def cmd_sync(plugin_id: str):
    """Trigger a data sync for an installed plugin."""
    _load_env()
    _check_venv()

    # B201: resolve the sync script via manifest (sync.script field) with
    # src/sync.py fallback. Matches the worker + API routes' behavior.
    sys.path.insert(0, str(ROOT))
    from apps.api.src.plugin_sync import resolve_sync_script
    plugin_dir = ROOT / "plugins" / "installed" / plugin_id
    sync_path, sync_path_rel = resolve_sync_script(plugin_dir)
    if not sync_path.exists():
        _print(f"Sync script not found for installed plugin '{plugin_id}'", "red")
        _print(f"  Expected: {sync_path}", "dim")
        _print(f"  Manifest sync.script: {sync_path_rel}", "dim")
        _print("  Is the plugin installed? Check: nousviz plugin list", "dim")
        sys.exit(1)

    _print(f"Syncing {plugin_id}...", "bold")
    result = subprocess.run(
        [str(VENV_PYTHON), str(sync_path), "--days", "7"],
        cwd=ROOT,
    )

    if result.returncode == 0:
        _print("Sync completed successfully", "green")
    else:
        _print("Sync failed", "red")
        sys.exit(1)


def cmd_setup():
    """First-time setup."""
    _print("Setting up NousViz...", "bold")

    # Create venv
    if not VENV.exists():
        _print("  Creating Python virtual environment...", "dim")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)

    # Install Python deps
    _print("  Installing Python dependencies...", "dim")
    req_file = ROOT / "apps" / "api" / "requirements.txt"
    if req_file.exists():
        subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(req_file)], capture_output=True)
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "clickhouse-connect", "pymysql", "pyyaml",
                    "fastapi", "uvicorn[standard]", "python-dotenv", "mcp"], capture_output=True)

    # Install frontend deps
    web_dir = ROOT / "apps" / "web"
    if (web_dir / "package.json").exists() and not (web_dir / "node_modules").exists():
        _print("  Installing frontend dependencies...", "dim")
        subprocess.run(["npm", "install"], cwd=web_dir, capture_output=True)

    # Create .env if missing
    if not ENV_FILE.exists():
        example = ROOT / ".env.example"
        if example.exists():
            shutil.copy(example, ENV_FILE)
            _print("  Created .env from .env.example — edit it with your settings", "yellow")

    # Create log directory
    (ROOT / ".logs").mkdir(exist_ok=True)
    PID_DIR.mkdir(exist_ok=True)

    # Run setup.sh for DB migrations
    _print("  Running setup script (Postgres + migrations)...", "dim")
    setup_sh = ROOT / "scripts" / "setup.sh"
    if setup_sh.exists():
        subprocess.run(["bash", str(setup_sh)], cwd=ROOT)

    _print("")
    _print("  Setup complete! Run 'nousviz start' to launch.", "green")


def cmd_dev():
    """Start in development mode with hot reload."""
    _load_env()
    _check_postgres()
    _check_venv()

    api_port = os.environ.get("API_PORT", "8000")
    web_port = os.environ.get("WEB_PORT", "5173")

    _print("Starting NousViz in dev mode...", "bold")
    _print(f"  API:  http://localhost:{api_port} (reload enabled)", "blue")
    _print(f"  Web:  http://localhost:{web_port} (HMR enabled)", "blue")
    _print("  Press Ctrl+C to stop\n", "dim")

    # Start frontend in background
    web_dir = ROOT / "apps" / "web"
    web_proc = subprocess.Popen(["npx", "vite", "--port", web_port], cwd=web_dir)

    # Start API in foreground with reload
    try:
        env = os.environ.copy()
        subprocess.run(
            [str(VENV_PYTHON), "-m", "uvicorn", "apps.api.src.main:app", "--port", api_port, "--reload"],
            cwd=ROOT, env=env,
        )
    except KeyboardInterrupt:
        pass
    finally:
        web_proc.terminate()
        _print("\nStopped.", "dim")


def cmd_mcp_setup():
    """Configure NousViz as an MCP server for Claude Desktop."""
    _load_env()

    config_path = Path.home() / ".claude" / "claude_desktop_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}

    config.setdefault("mcpServers", {})
    config["mcpServers"]["nousviz"] = {
        "command": str(VENV_PYTHON),
        "args": ["-m", "apps.mcp.src.main"],
        "cwd": str(ROOT),
        "env": {
            "CH_HOST": os.environ.get("CH_HOST", "localhost"),
            "CH_PORT": os.environ.get("CH_PORT", "8123"),
            "CH_DATABASE": os.environ.get("CH_DATABASE", "nousviz"),
        },
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    _print("MCP server configured for Claude Desktop!", "green")
    _print(f"  Config: {config_path}", "dim")
    _print(f"  Server: NousViz ({ROOT})", "dim")
    _print(f"  ClickHouse: {os.environ.get('CH_HOST', 'localhost')}:{os.environ.get('CH_PORT', '8123')}", "dim")
    _print("")
    _print("  Restart Claude Desktop to connect.", "yellow")
    _print("")
    _print("  11 tools available:", "dim")
    _print("    query, list_datasets, get_dataset_schema, get_health,", "dim")
    _print("    list_alerts, list_annotations, get_notes,", "dim")
    _print("    get_dashboard_data, export_data,", "dim")
    _print("    create_annotation, trigger_sync", "dim")


def cmd_logs():
    """Show recent logs."""
    log_dir = ROOT / ".logs"
    if not log_dir.exists():
        _print("No logs found. Start the app first.", "yellow")
        return

    for log_file in sorted(log_dir.glob("*.log")):
        _print(f"\n── {log_file.stem} ──", "bold")
        lines = log_file.read_text().strip().split("\n")
        for line in lines[-20:]:
            print(f"  {line}")


def cmd_version():
    """Show version info."""
    _print(f"NousViz v{VERSION}", "bold")
    _print(f"  Path: {ROOT}", "dim")
    _print(f"  Python: {sys.version.split()[0]}", "dim")
    node = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if node.returncode == 0:
        print(f"  Node: {node.stdout.strip()}")


# ── Plugin management ─────────────────────────────────────────────────

PLUGIN_DIRS = {
    "official": ROOT / "plugins" / "official",
    "installed": ROOT / "plugins" / "installed",
}
GITHUB_ORG = "nousviz"


def _find_plugin(slug: str) -> Path | None:
    """Return directory of an installed plugin, or None."""
    installed = PLUGIN_DIRS["installed"] / slug
    if (installed / "plugin.yaml").exists():
        return installed
    return None


def cmd_plugin_list():
    """List all installed plugins."""
    installed_dir = PLUGIN_DIRS["installed"]
    found = []

    if installed_dir.exists():
        for d in sorted(installed_dir.iterdir()):
            if d.is_dir() and (d / "plugin.yaml").exists():
                import yaml
                with open(d / "plugin.yaml") as f:
                    meta = yaml.safe_load(f)
                found.append((meta.get("name", d.name), meta.get("version", "?"), meta.get("description", "")))

    if not found:
        _print("No plugins installed.", "yellow")
        _print("  Install one from the marketplace: http://localhost:5173/marketplace", "dim")
        _print("  Or via API: POST /api/plugins/install {\"plugin_id\": \"starter-plugin\"}", "dim")
        return

    _print(f"{'PLUGIN':<30} {'VERSION':<10} DESCRIPTION", "bold")
    for slug, ver, desc in found:
        print(f"  {slug:<28} {ver:<10} {desc[:60]}")


def cmd_plugin_install(slug: str):
    """Install a plugin by slug via the API (preferred) or direct git clone."""
    _load_env()
    api_port = os.environ.get("API_PORT", "8000")

    # Try API install first — this runs migrations, registers the plugin, and hot-reloads routes
    _print(f"Installing plugin '{slug}'...", "bold")
    try:
        import urllib.request
        import urllib.error
        body = json.dumps({"plugin_id": slug}).encode()
        req = urllib.request.Request(
            f"http://localhost:{api_port}/api/plugins/install",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        _print(f"  ✓ {result.get('message', 'Plugin installed')}", "green")
        if result.get("migrations_applied"):
            _print(f"  ✓ Migrations applied: {result['migrations_applied']}", "dim")
        _print(f"  Visit: http://localhost:5173/plugin/{slug}", "blue")
        return
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        _print(f"  ✗ API install failed: {body}", "red")
        return
    except Exception:
        _print("  API not reachable — install the plugin from the marketplace UI instead:", "yellow")
        _print(f"  http://localhost:{api_port.replace('8000', '5173')}/marketplace", "blue")


def cmd_plugin_uninstall(slug: str):
    """Remove an installed plugin."""
    dest = PLUGIN_DIRS["installed"] / slug
    if not dest.exists():
        _print(f"Plugin '{slug}' is not installed.", "red")
        return
    shutil.rmtree(dest)
    _print(f"✓ Plugin '{slug}' removed.", "green")
    _print("  Restart the API server to deactivate it.", "dim")


# ── Main ──────────────────────────────────────────────────────────────

COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
    "sync": cmd_sync,
    "setup": cmd_setup,
    "dev": cmd_dev,
    "mcp-setup": cmd_mcp_setup,
    "logs": cmd_logs,
    "version": cmd_version,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    # ── plugin subcommand ──────────────────────────────────────────────
    if cmd == "plugin":
        if len(sys.argv) < 3:
            _print("Usage: nousviz plugin <install|uninstall|list> [slug]", "red")
            sys.exit(1)
        subcmd = sys.argv[2]
        if subcmd == "list":
            cmd_plugin_list()
        elif subcmd == "install":
            if len(sys.argv) < 4:
                _print("Usage: nousviz plugin install <slug>", "red")
                sys.exit(1)
            cmd_plugin_install(sys.argv[3])
        elif subcmd == "uninstall":
            if len(sys.argv) < 4:
                _print("Usage: nousviz plugin uninstall <slug>", "red")
                sys.exit(1)
            cmd_plugin_uninstall(sys.argv[3])
        else:
            _print(f"Unknown plugin subcommand: {subcmd}", "red")
            _print("Usage: nousviz plugin <install|uninstall|list> [slug]", "dim")
            sys.exit(1)
        return

    if cmd not in COMMANDS:
        _print(f"Unknown command: {cmd}", "red")
        print(__doc__)
        sys.exit(1)

    # Pass extra args for commands that accept them
    if cmd == "sync":
        if len(sys.argv) < 3:
            _print("Usage: nousviz sync <plugin-slug>", "red")
            _print("  Example: nousviz sync starter-plugin", "dim")
            sys.exit(1)
        COMMANDS[cmd](sys.argv[2])
    elif cmd in ("plugin",) and len(sys.argv) > 3:
        # already handled above
        pass
    else:
        COMMANDS[cmd]()


if __name__ == "__main__":
    main()
