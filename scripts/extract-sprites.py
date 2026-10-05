#!/usr/bin/env python3
"""Exports the item, workstation, construction object and tech branch icons
(and the quality stars) as PNG. GK1 only: GK2's catalog has no icon fields.

Reads `out/gk1/data/wiki/{items,recipes,technologies}.json` -- that is, it runs
AFTER `catalog.py`, which is what knows how to derive each sprite's name (item
by `ItemDefinition.GetIcon()`; workstation and construction object by the
balance's own `custom_icon`/`icon`; tech branch by `i_tbranch_<n>`, fixed).
This script only opens `resources.assets` and writes what the catalog asked for:

  out/gk1/icons/<name>.png

The quality star is a separate sprite (`item_star_1..3`), drawn over the icon
in the inventory cell: an item with `"stars": 2` shows up in the game with the
same `i_*` as the other levels plus the silver star.

The PNGs stay out of git (see `.gitignore`) -- they are game assets, not
extracted data. Regenerate them when the game build changes.

    ./scripts/extract-sprites.py gk1
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gk import assets, games  # noqa: E402

#: The glyph of each weekday in the game's HUD (HUDSinIcon.spr_back, one per
#: sin), used by keeper-wiki-fnd's hand-written "Days of the week" article.
#: It does not come from any catalog JSON -- it is UI (NGUI) data, not
#: item/recipe/technology -- so the names are fixed here, found once by reading
#: the HUD in the game scene directly (level2 + sharedassets2.assets, not
#: resources.assets). Only the "_off" variant (the base icon, always visible;
#: "_on" is the glow of a game state that does not matter here).
HUD_WEEK = {f"i_hud_sin0{n}_off" for n in range(1, 7)}
HUD_WEEK_FILE = "sharedassets2.assets"

#: The white (good deeds) and red (sins) skulls of the body panel, in the
#: morgue and on the embalming table (BodyPanelSkullBarGUI.skull_white /
#: skull_red), used by the effect tables of the "Bodies and autopsy" article.
#: Same situation as the weekdays: a UI sprite, not an item, so the name is
#: fixed here. They are in resources.assets, side by side (11x10 px).
HUD_SKULLS = {"icon_hud_skull", "icon_skull_red"}


def requested(wiki_dir: str) -> tuple[set[str], set[str], set[str]]:
    """(icons, stars, icons in use) that the catalog references.

    Workstation, construction object and tech branch have no `not_used` --
    unlike items, everything that shows up in a recipe or the research tree
    is, by definition, in use.
    """
    with open(os.path.join(wiki_dir, "items.json"), encoding="utf8") as fh:
        items = json.load(fh)
    with open(os.path.join(wiki_dir, "recipes.json"), encoding="utf8") as fh:
        recipes = json.load(fh)
    with open(os.path.join(wiki_dir, "technologies.json"), encoding="utf8") as fh:
        technologies = json.load(fh)

    icons = {i["icon"] for i in items if i.get("icon")}
    stars = {f"item_star_{i['stars']}" for i in items if i.get("stars")}
    in_use = {i["icon"] for i in items if i.get("icon") and not i["not_used"]}

    for r in recipes:
        for station in r.get("stations") or []:
            if station.get("icon"):
                icons.add(station["icon"])
                in_use.add(station["icon"])
        obj = r.get("built_object")
        if obj and obj.get("icon"):
            icons.add(obj["icon"])
            in_use.add(obj["icon"])
    for t in technologies:
        branch_icon = (t.get("branch") or {}).get("icon")
        if branch_icon:
            icons.add(branch_icon)
            in_use.add(branch_icon)

    return icons, stars, in_use


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(f"usage: {sys.argv[0]} <{'|'.join(games.GAMES)}> [destination]")
    game = games.get(sys.argv[1])
    if game.id != "gk1":
        raise SystemExit("Only gk1's catalog has icon fields.")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(game.out, "icons")

    wiki_dir = os.path.join(game.out, "data", "wiki")
    if not os.path.isfile(os.path.join(wiki_dir, "items.json")):
        raise SystemExit(f"Run first: python3 scripts/catalog.py {game.id}")

    icons, stars, in_use = requested(wiki_dir)
    if not icons:
        raise SystemExit(f"{wiki_dir} has no `icon` field -- run the catalog again")

    os.makedirs(out, exist_ok=True)
    saved = set()
    for name, image in assets.read_sprites(game, icons | stars):
        image.save(os.path.join(out, f"{name}.png"))
        saved.add(name)

    missing = sorted((icons | stars) - saved)
    print(f"  icons    {len(saved & icons):5}/{len(icons)}")
    print(f"  stars    {len(saved & stars):5}/{len(stars)}")
    if missing:
        # A missing sprite almost always belongs to an unused item, whose art
        # left the game while the balance kept it. The handful left over is
        # missing in the game too: `GetIcon` builds `i_<id>` and
        # `i_hop_honey:1` exists in no collection. No substitute is invented --
        # consumers show the blank.
        live = sorted(x for x in missing if x in in_use)
        print(f"\n{len(missing)} with no sprite in {assets.RESOURCES}, "
              f"{len(live)} of items in use" + (f": {', '.join(live)}" if live else ""))

    saved_hud = set()
    for name, image in assets.read_sprites(game, HUD_WEEK, filename=HUD_WEEK_FILE):
        image.save(os.path.join(out, f"{name}.png"))
        saved_hud.add(name)
    print(f"  hud      {len(saved_hud):5}/{len(HUD_WEEK)} (weekdays, {HUD_WEEK_FILE})")
    saved |= saved_hud

    saved_skulls = set()
    for name, image in assets.read_sprites(game, HUD_SKULLS):
        image.save(os.path.join(out, f"{name}.png"))
        saved_skulls.add(name)
    print(f"  skulls   {len(saved_skulls):5}/{len(HUD_SKULLS)} (body panel, {assets.RESOURCES})")
    saved |= saved_skulls

    print(f"-> {out} ({len(saved)} PNG)")


if __name__ == "__main__":
    main()
