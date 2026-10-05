"""Pieces shared by the catalogs of both games."""
from __future__ import annotations

import json
import os

from .games import Game


def load(game: Game, name: str) -> list:
    path = os.path.join(game.out, "data", "balance", f"{name}.json")
    with open(path, encoding="utf8") as fh:
        return json.load(fh)


def load_locale_raw(game: Game, lng: str) -> tuple[dict[str, str], dict[str, str]]:
    """(strings, aliases) of a language, exactly as extracted."""
    path = os.path.join(game.out, "data", "locales", f"{lng}.json")
    with open(path, encoding="utf8") as fh:
        loc = json.load(fh)
    return loc["strings"], loc["aliases"]


def load_locale(game: Game, lng: str) -> dict[str, str]:
    """The language's strings, with the aliases already resolved.

    The game's `GJL.L()` checks the aliases before the dictionary, as a chain:
    `1h_ore_metal` -> `t_iron_ore_2` -> "Iron ore". Without this, 51 items,
    20 workstations and 7 technologies had no name. An alias whose target is
    not in the dictionary makes the game show the raw target ("Advanced
    gravestones"): that is not a translation, and it is ignored here.
    """
    raw, aliases = load_locale_raw(game, lng)
    strings = dict(raw)
    for key in aliases:
        target, seen = key, set()
        while target in aliases and target not in seen:
            seen.add(target)
            target = aliases[target]
        if target in raw:
            strings[key] = raw[target]
    return strings


class Names:
    """Name and description of an id, in the game's official languages.

    Both games use the same convention: the locale key is the `id` itself, the
    description is `<id>_d`, and an id with a suffix (`item:2`) falls back to
    the base id when it has no entry of its own.
    """

    def __init__(self, game: Game, tables: dict[str, dict[str, str]]):
        self.game, self.tables = game, tables

    def name(self, item_id: str, lng: str) -> str | None:
        table = self.tables[lng]
        for key in (item_id, item_id.rsplit(":", 1)[0]):
            if key in table:
                return table[key]
        return None

    def desc(self, item_id: str, lng: str) -> str | None:
        table = self.tables[lng]
        suffix = self.game.desc_suffix
        for key in (item_id + suffix, item_id.rsplit(":", 1)[0] + suffix):
            if key in table:
                return table[key]
        return None


def write(game: Game, jsons: dict[str, list], mds: dict[str, str]) -> None:
    out_json = os.path.join(game.out, "data", "wiki")
    out_md = os.path.join(game.out, game.catalog_dir)
    os.makedirs(out_json, exist_ok=True)
    os.makedirs(out_md, exist_ok=True)

    for name, payload in jsons.items():
        path = os.path.join(out_json, f"{name}.json")
        with open(path, "w", encoding="utf8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"  {path:38} {len(payload)} records")

    for name, text in mds.items():
        path = os.path.join(out_md, f"{name}.md")
        if game.notice:
            text = text.replace("\n\n", f"\n\n> **{game.notice}**\n\n", 1)
        with open(path, "w", encoding="utf8") as fh:
            fh.write(text)
        print(f"  {path:38} {len(text.splitlines())} lines")
