#!/usr/bin/env python3
"""Extracts the official localizations (`lng_*`) to JSON.

Each `lng_<id>` is a ScriptableObject with two parallel lists (ids x strings).
`lng_en` is the game's OFFICIAL English text -- the only source of the names
in this project's English catalog.

    ./scripts/extract-locales.py gk1
    ./scripts/extract-locales.py gk2
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gk import assets, games  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} <{'|'.join(games.GAMES)}> [destination]")
    game = games.get(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(game.out, "data", "locales")

    os.makedirs(out, exist_ok=True)
    found = 0
    for loc in assets.read_locales(game):
        payload = {"id": loc["id"], "count": len(loc["strings"]),
                   "strings": loc["strings"], "aliases": loc["aliases"]}
        with open(os.path.join(out, f"{loc['id']}.json"), "w", encoding="utf8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"  {loc['id']:8} {len(loc['strings']):6} strings, {len(loc['aliases'])} aliases")
        found += 1

    if not found:
        raise SystemExit("No `lng_*` MonoBehaviour found")
    print(f"-> {out} ({found} languages)")


if __name__ == "__main__":
    main()
