#!/usr/bin/env bash
#
# NousViz installer
# Usage: curl -fsSL https://raw.githubusercontent.com/nousviz/nousviz-app/main/install.sh | bash
#
set -e

REPO="https://github.com/nousviz/nousviz-app.git"
INSTALL_DIR="$HOME/nousviz"

echo ""
echo "  ╔═══════════════════════════════════╗"
echo "  ║         NousViz Installer         ║"
echo "  ║    Data Intelligence Platform     ║"
echo "  ╚═══════════════════════════════════╝"
echo ""

# ── Check prerequisites ───────────────────────────────────────────────

check_cmd() {
    if ! command -v "$1" &> /dev/null; then
        echo "  ✗ $1 is required but not installed."
        echo "    $2"
        exit 1
    fi
    echo "  ✓ $1 found"
}

echo "Checking prerequisites..."
check_cmd "git"     "Install: https://git-scm.com/"
check_cmd "python3" "Install: https://www.python.org/downloads/"
check_cmd "node"    "Install: https://nodejs.org/"
check_cmd "npm"     "Comes with Node.js"
echo ""

# ── Clone ─────────────────────────────────────────────────────────────

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists."
    read -p "Update existing installation? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        git pull
    else
        echo "Aborted."
        exit 0
    fi
else
    echo "Cloning NousViz..."
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── Run setup.sh (installs Postgres, creates DB, runs migrations) ──────

echo ""
echo "Running setup..."
bash "$INSTALL_DIR/scripts/setup.sh"

# ── Make CLI available ────────────────────────────────────────────────

chmod +x "$INSTALL_DIR/cli.py"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  NousViz installed successfully!"
echo ""
echo "  To start (from $INSTALL_DIR):"
echo ""
echo "    # Terminal 1 — API server:"
echo "    source .venv/bin/activate"
echo "    python3 -m uvicorn apps.api.src.main:app --reload --port 8000"
echo ""
echo "    # Terminal 2 — Frontend:"
echo "    cd apps/web && npm run dev"
echo ""
echo "  Then visit: http://localhost:5173"
echo ""
echo "  Documentation: https://nousviz.com/docs"
echo "  GitHub: https://github.com/nousviz/nousviz-app"
echo ""
echo "═══════════════════════════════════════════════════════════"
