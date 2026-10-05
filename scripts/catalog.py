#!/usr/bin/env python3
"""Joins balance + localization and builds the browsable catalogs.

Reads `out/<game>/data/balance` and `.../locales` (the output of the two
`extract-*.py` scripts) and writes:

  gk1:  out/gk1/data/wiki/{items,recipes,technologies}.json    wiki raw material, in English
        out/gk1/data/wiki/_missing_names.txt                   ids with no English name
        out/gk1/catalog/{items,recipes,technologies}.md        readable tables
  gk2:  out/gk2/data/wiki/{itens,receitas,tecnologias}.json    upstream's Portuguese format
        out/gk2/catalogo/{itens,receitas,tecnologias}.md

Each game has its own adapter in `gk/catalog_<game>.py`, because the balance
schema changed a lot between the two. See docs/04-bridge-to-the-wiki.md.

Only needs the committed `out/` files: no game install, no .venv.

    python3 scripts/catalog.py gk1
    python3 scripts/catalog.py gk2
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gk import catalog_gk1, catalog_gk2, games  # noqa: E402

ADAPTERS = {"gk1": catalog_gk1, "gk2": catalog_gk2}


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} <{'|'.join(games.GAMES)}>")
    game = games.get(sys.argv[1])

    if not os.path.isdir(os.path.join(game.out, "data", "balance")):
        raise SystemExit(f"Run first: ./scripts/extract-balance.py {game.id} "
                         f"and ./scripts/extract-locales.py {game.id}")

    ADAPTERS[game.id].run(game)


if __name__ == "__main__":
    main()
