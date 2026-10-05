#!/usr/bin/env bash
# Decompiles the studio's assemblies to C# in out/<game>/src-csharp/.
# Same technique as metrics-reveng: ilspycmd, one .csproj project per assembly.
#
#   ./scripts/decompile.sh gk1
#   ./scripts/decompile.sh gk2
set -euo pipefail
cd "$(dirname "$0")/.."

GAME="${1:-gk1}"
eval "$(./.venv/bin/python - "$GAME" <<'PY'
import sys
sys.path.insert(0, "scripts")
from gk import games
g = games.get(sys.argv[1])
print(f'DATA={g.env_data_dir()!r}')
print(f'DEST={g.out!r}/src-csharp')
print('ASMS=(' + ' '.join(f'"{a}"' for a in g.assemblies) + ')')
PY
)"
DEST="${2:-$DEST}"

# ilspycmd 8.x targets .NET 6 and the machine only has 8/10 -- same gotcha as metrics-reveng.
export DOTNET_ROLL_FORWARD=LatestMajor

command -v ilspycmd >/dev/null 2>&1 || {
  echo "ilspycmd not found. Install it with: dotnet tool install -g ilspycmd --version '8.*'" >&2
  exit 1
}

for dll in "${ASMS[@]}"; do
  echo "== $dll"
  rm -rf "${DEST:?}/$dll"
  mkdir -p "$DEST/$dll"
  ilspycmd -p -o "$DEST/$dll" "$DATA/Managed/$dll.dll"
done

echo
echo "-> $DEST ($(find "$DEST" -name '*.cs' | wc -l) .cs files)"
