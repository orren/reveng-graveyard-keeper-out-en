#!/usr/bin/env python3
"""Extracts the game's entire balance to JSON, one list per file.

Each Graveyard Keeper's balance is a single ScriptableObject
(`Resources.Load<GameBalance>(...)`) holding ALL the definition lists: items,
recipes, objects, technologies, perks, quests... The output is faithful to the
binary: nothing is filtered or renamed, so that a `git diff` between two
versions of the game shows exactly what Lazy Bear changed.

    ./scripts/extract-balance.py gk1
    ./scripts/extract-balance.py gk2
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
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(game.out, "data", "balance")

    os.makedirs(out, exist_ok=True)
    data = assets.read_balance(game)

    index = {}
    for key, value in data.items():
        if not isinstance(value, list):
            continue
        index[key] = len(value)
        with open(os.path.join(out, f"{key}.json"), "w", encoding="utf8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=1, sort_keys=True)
        if value:
            print(f"  {key:24} {len(value):5}")

    with open(os.path.join(out, "_index.json"), "w", encoding="utf8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"-> {out} ({sum(index.values())} definitions in {len(index)} lists)")


if __name__ == "__main__":
    main()
