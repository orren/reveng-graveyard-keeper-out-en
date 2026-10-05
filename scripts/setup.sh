#!/usr/bin/env bash
# Creates the extraction's Python environment (.venv at the project root).
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  uv venv .venv
  uv pip install --python .venv/bin/python -r requirements.txt
else
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

echo
echo "Done. Use:  source .venv/bin/activate"
./.venv/bin/python -c "import UnityPy; print('UnityPy', UnityPy.__version__)"
