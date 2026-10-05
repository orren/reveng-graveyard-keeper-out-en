#!/usr/bin/env bash
# Inventory of the installed build: version, the studio's assemblies, serialized files.
# The equivalent of metrics-reveng's "classify binaries" step.
#
#   ./scripts/inventory.sh gk1
#   ./scripts/inventory.sh gk2
set -uo pipefail
cd "$(dirname "$0")/.."

GAME="${1:-gk1}"
eval "$(./.venv/bin/python - "$GAME" <<'PY'
import sys, os
sys.path.insert(0, "scripts")
from gk import games
g = games.get(sys.argv[1])
print(f'DATA={g.env_data_dir()!r}')
print(f'NAME={g.name!r}')
print(f'APPID={g.steam_appid}')
print('ASMS=(' + ' '.join(f'"{a}"' for a in g.assemblies) + ')')
PY
)"
[ -d "$DATA" ] || { echo "Game folder not found: $DATA" >&2; exit 1; }

echo "# Inventory — $NAME"
echo
echo "Folder: $DATA"
echo -n "Unity: "; strings -n 5 "$DATA/globalgamemanagers" | grep -m1 -E '^[0-9]{4}\.[0-9]+\.[0-9]+[a-z][0-9]+$'
BUILDID=$(grep -m1 '"buildid"' "$HOME/.local/share/Steam/steamapps/appmanifest_$APPID.acf" 2>/dev/null | tr -d '\t"' | sed 's/buildid//')
[ -n "${BUILDID:-}" ] && echo "Steam buildid:$BUILDID (appid $APPID)"

echo
echo "## Studio assemblies (decompilable)"
for dll in "${ASMS[@]}"; do
  f="$DATA/Managed/$dll.dll"
  [ -f "$f" ] && printf '%-34s %8s KiB\n' "$dll.dll" "$(( $(stat -c%s "$f") / 1024 ))"
done

echo
echo "## Serialized files (largest)"
find "$DATA" -maxdepth 1 -type f \( -name 'resources.assets' -o -name 'globalgamemanagers*' \
  -o -name 'level*' -o -name 'sharedassets*' \) -printf '%10s  %p\n' | sort -rn | head -10 | sed "s|$DATA/||"

if [ -d "$DATA/StreamingAssets/aa" ]; then
  echo
  echo "## Addressables"
  echo "$(find "$DATA/StreamingAssets/aa" -name '*.bundle' | wc -l) bundles, $(du -sh "$DATA/StreamingAssets/aa" | cut -f1)"
  echo "(art and scenes; the balance is NOT there -- it comes from resources.assets)"
fi
