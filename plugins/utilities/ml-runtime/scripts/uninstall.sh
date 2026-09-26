#!/usr/bin/env bash
set -euo pipefail

# ML runtime utility — uninstall hook.
#
# The libraries are deliberately LEFT in the venv. It is shared by core and
# every plugin, and pip cannot tell whether something else now imports
# numpy or scipy; removing them could break an unrelated plugin. The
# platform already refuses to uninstall this utility while a plugin still
# declares `requires: ml_runtime: true`.
#
# This utility keeps no data of its own (trained models live in each
# plugin's database), so NOUSVIZ_REMOVE_DATA has nothing to remove.

source "$(dirname "$0")/_python.sh"

echo "ML Runtime uninstalled. The libraries remain in the Python environment."
echo "To remove them as well, once nothing else uses them:"
echo "  $PY -m pip uninstall -y lightgbm scikit-learn"
