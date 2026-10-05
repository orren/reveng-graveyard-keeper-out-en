"""Graveyard Keeper 1 catalog, in English.

Names and descriptions come only from the game's official English locale
(`out/gk1/data/locales/en.json`); nothing is machine-translated, and an id
without an English string gets `name: null` instead of an invented one.
"""
from __future__ import annotations

import os
from collections import defaultdict

from .catalog_common import Names, load, load_locale, load_locale_raw, write
from .games import Game

#: ItemDefinition.ItemType
ITEM_TYPES = {
    -1: "PseudoitemFirst", 0: "None", 1: "Axe", 2: "Pickaxe", 3: "Shovel", 4: "Sword",
    5: "Hammer", 6: "FishingRod", 9: "Torch", 10: "Hand", 11: "Item", 12: "HeadArmor",
    13: "BodyArmor", 20: "Preach", 31: "Bait", 50: "Crate", 60: "Rat", 61: "RatBuff",
    101: "GraveStone", 102: "GraveFence", 103: "GraveCover", 200: "Body",
    201: "BodyHead", 202: "BodyBody", 203: "BodyArmR", 204: "BodyArmL",
    205: "BodyLegR", 206: "BodyLegL", 210: "BodyHeadPart", 220: "BodyBodyPart",
    230: "BodyArmPart", 250: "BodyLegPart", 270: "BodyUniversalPart",
    271: "SoulBodyPart", 280: "Soul", 300: "ZombieWorker", 400: "Bag",
    10101: "GraveStoneReq", 10102: "GraveFenceReq", 10103: "GraveCoverReq",
}

#: CraftDefinition.CraftType
CRAFT_TYPES = {
    0: "None", 1: "ResourcesBasedCraft", 2: "Survey", 3: "MixedCraft", 4: "Fixing",
    5: "AlchemyDecompose", 6: "PrayCraft", 7: "RatBuff", 8: "RefugeeCampCraft",
}

#: ObjectCraftDefinition.BuildType
BUILD_TYPES = {0: "Put", 1: "Remove", 2: "None"}

#: DLCEngine.DLCVersion (Stories = Stranger Sins, Refugees = Game of Crone,
#: Souls = Better Save Soul).
DLC = {0: "none", 1: "breaking_dead", 2: "stranger_sins", 3: "game_of_crone",
       4: "better_save_soul"}

#: ObjectDefinition.InteractionType -- only the ones that matter for the
#: workstation icon (`station_icon`); Chest and Grave only fall back to the
#: build menu icon.
INTERACTION_CRAFT = 1
INTERACTION_RUNSCRIPT = 2
INTERACTION_BUILDER = 4

#: Three ids whose icon is hard-coded in the C# (`WorldGameObject.
#: GetUniversalObjectInfo()`), outside any rule: the plain grave uses the
#: icon of the bought grave, not of the hole, and the two embalming tables are
#: special cases in the switch on id.
FIXED_ICON = {
    "grave_ground": "i_b_grave_place",
    "mf_balsamation_1": "i_b_mf_balsamation_1",
    "mf_balsamation_2": "i_b_mf_balsamation_2",
}

#: ItemDefinition.QualityType.Stars -- the item shows a quality star.
QUALITY_STARS = 1

#: TechDefinition.TECH_POINTS -- outputs that are tech points, not items.
TECH_POINTS = ["r", "g", "b", "v", "gratitude_points"]

#: Tech point id -> readable name, used wherever points appear: technology
#: `cost`, recipe `tech_points`, item `on_use`.
POINTS = {"r": "red", "g": "green", "b": "blue", "v": "purple",
          "gratitude_points": "gratitude"}


class EnglishNames:
    """Official English names, with every fallback the locale allows.

    First the game's own rule (`Names`: the id, then the base id without the
    `:N` suffix, aliases already resolved). When that gives nothing or an empty
    string, try the base id's string, then the aliases (followed as a chain,
    like `GJL.L()`) of the id and of the base id. An alias whose target has no
    string is ignored: the game would show the raw target, which is not a
    name. Nothing found -> None, and the id goes to `missing`.
    """

    def __init__(self, game: Game):
        self.names = Names(game, {"en": load_locale(game, "en")})
        self.strings, self.aliases = load_locale_raw(game, "en")
        self.missing: dict[str, set[str]] = defaultdict(set)

    def _string(self, key: str) -> str | None:
        return self.strings.get(key) or None

    def _alias(self, key: str) -> str | None:
        seen = set()
        while key in self.aliases and key not in seen:
            seen.add(key)
            key = self.aliases[key]
        return self._string(key) if seen else None

    def lookup(self, key: str) -> str | None:
        base = key.rsplit(":", 1)[0]
        for k in dict.fromkeys((key, base)):
            if s := self._string(k):
                return s
        for k in dict.fromkeys((key, base)):
            if s := self._alias(k):
                return s
        return None

    def name(self, obj_id: str, where: str) -> str | None:
        found = self.names.name(obj_id, "en") or self.lookup(obj_id)
        if found is None:
            self.missing[where].add(obj_id)
        return found

    def desc(self, obj_id: str) -> str | None:
        return self.names.desc(obj_id, "en") or None

    def ref(self, obj_id: str, where: str) -> dict:
        return {"id": obj_id, "name": self.name(obj_id, where)}


def expr(value):
    """SmartExpression -> a number when it is constant, else the raw expression."""
    if not isinstance(value, dict):
        return value
    if value.get("_simplified"):
        return round(value["_simpified_float"], 4)
    return value.get("_expression") or None


def game_res(res: dict) -> dict:
    """GameRes -> {type: value}, only what is non-zero."""
    return {t: v for t, v in zip(res.get("_res_type", []), res.get("_res_v", [])) if v}


def points(res: dict) -> dict:
    """GameRes of tech points, with the point ids spelled out."""
    return {POINTS.get(k, k): v for k, v in res.items()}


def qty(item: dict) -> dict:
    """The REAL quantity of a recipe input/output.

    `Item.value` is a dead field in the balance: what counts is the
    `min_value`/`max_value` pair (SmartExpression), which is what
    `WorldGameObject.GetCraftAmountCounter` evaluates. E.g. `flitch_2` has
    value=1 but min_value='7+Ppar("p_woodworker")*2' -- it makes 7 flitches,
    not 1.
    """
    out = {}
    lo, hi = expr(item.get("min_value")), expr(item.get("max_value"))
    if lo is None:
        out["qty"] = item["value"]
    elif isinstance(lo, str):
        out["qty"] = None
        out["qty_expr"] = lo
    else:
        out["qty"] = lo
    if hi is not None and hi != lo:
        out["qty_max"] = hi
    return out


def item_ref(names: EnglishNames, item: dict, where: str) -> dict:
    return {**names.ref(item["id"], where), **qty(item)}


def icon(it: dict) -> str:
    """Sprite name of the item, by the rule of `ItemDefinition.GetIcon()`.

    The `icon` field is optional: 483 items have it empty and the game falls
    back to `"i_" + id`. `extract-sprites.py` exports the PNG from here.
    (`custom_ovr_icon` does NOT count: that is the icon the character holds up
    over their head, not the one in the inventory cell.)
    """
    return it["icon"] or f"i_{it['id']}"


def stars(it: dict) -> int | None:
    """Quality star level (1, 2 or 3), or None when there is none.

    Same condition as `ItemDefinition.GetQualityIconName()`, which builds the
    sprite as `"item_star_" + quality`. `hamp_crop:1..3` is the exception that
    shows why the condition matters: it has a quality suffix, but
    `quality_type` Default and `quality` 0 -- in the game it shows no star.
    """
    n = int(it["quality"])
    return n if it["quality_type"] == QUALITY_STARS and n > 0 else None


def on_use(it: dict) -> dict:
    """What the item gives back when the player uses it: energy, health, points.

    This is the FIXED part of the effect -- `params_on_use`, which the game
    always adds. Health comes in its own field, outside the
    `_res_type`/`_res_v` pair, and can be negative: `infusion` takes 20 health
    along with the 80 energy, and `shr_agaric` only takes 5.

    Read it together with `can_be_used`: on a tool (`can_be_used` false) the
    number here is the energy cost per swing, not what it gives back.
    """
    res = points(game_res(it["params_on_use"]))
    if it["params_on_use"]["_hp"]:
        res["hp"] = it["params_on_use"]["_hp"]
    return res


def on_use_expr(it: dict) -> list[str]:
    """The part of the effect that is a formula, not a number.

    `AddPpar("energy", 20*Ppar("food_multiplier"))` is the gain that depends on
    a player perk; `AddBuff("buff_longtimer")` is the buff the food gives. It
    stays raw, by the same rule as `qty_expr`: what is not a number is not
    rounded. None of GK1's 229 expressions comes simplified to a constant.
    """
    return [e["_expression"].strip() for e in it["on_use_expressions"]
            if e.get("_expression", "").strip()]


def quality_groups(items_data: list[dict]) -> dict[str, str]:
    """`item id -> group id`, for the items that only differ in quality.

    `pumpkin_crop:1/2/3` are three ItemDefinitions, one per level, and the game
    groups them as `pumpkin_crop`: this is the part of
    `Item.InitMultiqualityItems`'s rule that matters to the wiki -- an id with
    no definition of its own becomes the group of the ids starting with
    `<id>:`. That is why 80 recipes ask for `pumpkin_crop`, which does not
    exist in `items_data`.

    Two things are left out on purpose:
    - `test_paper` and `test_scroll`, which have their own definition AND
      suffixed variants: for the game the group never comes into being;
    - the prefix groups (`meal`, `chisel`, `fillet_fish`...), which gather
      DIFFERENT items ("any meal"), not levels of the same item.
    """
    ids = {it["id"] for it in items_data}
    group = {}
    for it in items_data:
        base, _, suffix = it["id"].rpartition(":")
        if base and suffix.isdigit() and base not in ids:
            group[it["id"]] = base
    return group


def items(game: Game, names: EnglishNames) -> list[dict]:
    items_data = load(game, "items_data")
    group = quality_groups(items_data)
    out = []
    for it in items_data:
        out.append({
            "id": it["id"],
            "name": names.name(it["id"], "items"),
            "description": names.desc(it["id"]),
            "type": ITEM_TYPES.get(it["type"], str(it["type"])),
            "base_price": it["base_price"],
            "quality": it["quality"],
            "stack_count": it["stack_count"],
            "efficiency": it["efficiency"],
            "has_durability": bool(it["has_durability"]),
            "not_used": bool(it["not_used"]),
            "product_types": it["product_types"],
            "icon": icon(it),
            "stars": stars(it),
            "group": group.get(it["id"]),
            "can_be_used": bool(it["can_be_used"]),
            # Only "what the item gives back" when can_be_used is true; on a
            # tool it is the energy cost per swing (axe_1: energy -1).
            "on_use": on_use(it),
            "on_use_expr": on_use_expr(it),
        })
    return sorted(out, key=lambda i: i["id"])


def station_icon(obj: dict | None, put_by_object: dict[str, str],
                 menu_by_object: dict[str, str], station_id: str) -> str | None:
    """Workstation icon, by the SAME rule as `WorldGameObject.
    GetUniversalObjectInfo()`, which picks the icon in the game's interaction
    panel -- not just `custom_icon`: it has a naming-convention fallback that
    changes with the interaction type, and a craft object swaps its icon for
    the one of the recipe that builds it.

    - Craft (1): the icon of the "Put" recipe that builds this object, if any;
      else `custom_icon`; else `"i_b_" + id`.
    - RunScript (2) / Builder (4): `custom_icon`, else `"i_z_" + id`.
    - Autopsy table: `custom_icon`, else `"i_b_" + id` (same fallback as Craft,
      but without the recipe swap).
    - Chest, Grave, None: only `custom_icon` -- the game has no fallback for
      them (`UniversalObjectInfo.icon` stays `null`), so most of them have no
      icon at all, and that is not a bug: the game has none there either.

    Outside Craft, the build menu icon (`menu_by_object`) comes between
    `custom_icon` and the naming convention: the sprite the player sees when
    building that object, in the same recipe that builds it. The interaction
    panel does not use that icon, but without it the refugee camp (Game of
    Crone) lost its kitchen, beehive and well: the kitchen and the beehive are
    None, with no fallback, and the well is RunScript, whose `"i_z_" + id` has
    no sprite in the game. This does not change any workstation that already
    had art: only the 8 that had none gain an icon.

    Without this rule the carpentry workbench -- the most basic one in the
    game -- had no icon (empty `custom_icon`), when the game actually shows
    `i_b_mf_workbench_1` through the fallback.
    """
    if station_id in FIXED_ICON:
        return FIXED_ICON[station_id]
    if obj is None:
        return None
    custom = obj["custom_icon"] or None
    if obj.get("is_autopsy_table"):
        return custom or f"i_b_{station_id}"
    interaction = obj.get("interaction_type")
    if interaction == INTERACTION_CRAFT:
        return put_by_object.get(station_id) or custom or f"i_b_{station_id}"
    menu = menu_by_object.get(station_id)
    if interaction in (INTERACTION_RUNSCRIPT, INTERACTION_BUILDER):
        return custom or menu or f"i_z_{station_id}"
    return custom or menu


def station_ref(names: EnglishNames, obj_by_id: dict, put_by_object: dict,
                menu_by_object: dict, station_id: str) -> dict:
    """Workstation reference, with the icon of the world object it is.

    There is no dedicated "workstation" class: in the game it is the same
    `ObjectDefinition` as any placeable object.
    """
    ref = names.ref(station_id, "recipes.stations[]")
    ref["icon"] = station_icon(obj_by_id.get(station_id), put_by_object,
                               menu_by_object, station_id)
    return ref


def recipes(game: Game, names: EnglishNames) -> list[dict]:
    unlocked_by: dict[str, list[str]] = defaultdict(list)
    for tech in load(game, "techs_data"):
        for craft_id in tech["crafts"]:
            unlocked_by[craft_id.lstrip("@")].append(tech["id"])

    obj_by_id = {o["id"]: o for o in load(game, "objs_data")}
    # "Put" is what builds the object; an out_obj can have more than one
    # recipe (a builder locked by a perk, for instance) -- the first one found
    # wins, as `BuildModeLogics.GetObjectPutCraftDefinition` would do too.
    put_by_object: dict[str, str] = {}
    for c in load(game, "craft_obj_data"):
        if c.get("out_obj") and c.get("build_type") == 0 and c.get("icon"):
            put_by_object.setdefault(c["out_obj"], c["icon"])
    # Build menu icon: any recipe that builds the object, except demolition
    # ("Remove"). The refugee camp builds with build_type "None", not "Put".
    # The beehive is built as `refugee_camp_hive_place`, which becomes
    # `refugee_camp_hive` when finished (`after_hp_0`): the icon carries over
    # to the final object.
    menu_by_object: dict[str, str] = {}
    for c in load(game, "craft_obj_data"):
        if c.get("out_obj") and c.get("build_type") != 1 and c.get("icon"):
            menu_by_object.setdefault(c["out_obj"], c["icon"])
            becomes = (obj_by_id.get(c["out_obj"]) or {}).get("after_hp_0", {}).get("_id")
            if c["out_obj"].endswith("_place") and becomes:
                menu_by_object.setdefault(becomes, c["icon"])

    out = []
    for source, crafts in (("craft", load(game, "craft_data")),
                           ("construction", load(game, "craft_obj_data"))):
        for c in crafts:
            outputs, tech_points = [], {}
            for item in c["output"]:
                if item["id"] in TECH_POINTS:
                    q = qty(item)
                    tech_points[POINTS[item["id"]]] = q.get("qty", q.get("qty_expr"))
                else:
                    outputs.append(item_ref(names, item, "recipes.outputs[]"))
            rec = {
                "id": c["id"],
                "source": source,
                "craft_type": CRAFT_TYPES.get(c["craft_type"], str(c["craft_type"])),
                # A construction recipe does not use `craft_in`: the "station"
                # is whoever builds it (`builder_ids`, e.g. the building site).
                "stations": [station_ref(names, obj_by_id, put_by_object, menu_by_object, o)
                             for o in (c["craft_in"] or c.get("builder_ids", []))],
                "inputs": [item_ref(names, i, "recipes.inputs[]") for i in c["needs"]],
                # needs_from_wgo: what the station consumes from its own
                # inventory (`fire` fuel, `science`), not from the player.
                "station_inputs": [item_ref(names, i, "recipes.station_inputs[]")
                                   for i in c["needs_from_wgo"]],
                "outputs": outputs,
                "tech_points": tech_points,
                "craft_time": expr(c["craft_time"]),
                "energy": expr(c["energy"]),
                # Player sanity cost (CraftComponent: SpendSanity); always 0 or
                # null in GK1.
                "sanity": expr(c["sanity"]),
                "difficulty": c["difficulty"],
                "hidden": bool(c["hidden"]),
                "needs_unlock": bool(c["needs_unlock"]),
                "linked_perks": c["linked_perks"],
                "unlocked_by": unlocked_by.get(c["id"], []),
            }
            if source == "construction":
                # `icon` is the sprite the game itself shows in the build menu
                # for this result -- more reliable than guessing from the built
                # object's `custom_icon`, which may not even exist (demolition
                # uses the same icon as the original construction).
                rec["built_object"] = (
                    {**names.ref(c["out_obj"], "recipes.built_object"),
                     "icon": c.get("icon") or None}
                    if c["out_obj"] else None
                )
                rec["build_type"] = BUILD_TYPES.get(c["build_type"], str(c["build_type"]))
            out.append(rec)
    return sorted(out, key=lambda r: r["id"])


def technologies(game: Game, names: EnglishNames) -> list[dict]:
    out = []
    for t in load(game, "techs_data"):
        branch_key = f"tbranch_{t['branch_type']}"
        branch_name = names.lookup(branch_key)
        if branch_name is None:
            names.missing["technologies.branch"].add(branch_key)
        dlc = t["requires_dlc"]
        if dlc not in DLC:
            raise SystemExit(f"technology {t['id']!r}: unknown requires_dlc {dlc!r}")
        out.append({
            "id": t["id"],
            "name": names.name(t["id"], "technologies"),
            # TechBranchDefinition only stores the branch number; the name
            # comes from the locale, under `tbranch_<n>`. There is no
            # per-technology icon -- only per branch (`i_tbranch_<n>`, 8
            # sprites, one per color/specialty).
            "branch": {
                "n": t["branch_type"],
                "name": branch_name,
                "icon": f"i_tbranch_{t['branch_type']}",
            },
            "cost": points(game_res(t["price"])),
            "requires": t["_parents"],
            "crafts": t["crafts"],
            "perks": t["perks"],
            "hidden": bool(t["hidden"]) or bool(t["invisible"]),
            "requires_dlc": dlc,
            "dlc": DLC[dlc],
        })
    return sorted(out, key=lambda x: (x["branch"]["n"], x["id"]))


# --- Markdown ----------------------------------------------------------------

def num(v) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def cell(v) -> str:
    """Scalar for a table cell: numbers plain, formulas as code, null as —."""
    if v is None:
        return "—"
    if isinstance(v, str):
        return f"`{v}`"
    return num(v)


def qty_txt(ref: dict) -> str:
    """'3x Wooden plank', or the raw formula when the amount depends on perks."""
    if ref.get("qty_expr") is not None:
        q = f"`{ref['qty_expr']}`"
    else:
        q = num(ref["qty"]) if ref.get("qty") is not None else "?"
    top = ref.get("qty_max")
    if top is not None:
        q += f"–`{top}`" if isinstance(top, str) else f"–{num(top)}"
    return f"{q}x {ref['name'] or ref['id']}"


def list_txt(refs: list[dict]) -> str:
    return "<br>".join(qty_txt(r) for r in refs) or "—"


def points_txt(pts: dict, fmt=str) -> str:
    return " ".join(f"{fmt(v)} {k}" for k, v in pts.items()) or "—"


def md_items(items: list[dict]) -> str:
    lines = ["# Items", "",
             f"{len(items)} items in `items_data`. Names are the game's official "
             "English localization; items flagged `not_used` are omitted.",
             "", "| id | name | type | price | quality | stack |",
             "| -- | ---- | ---- | ----: | ------: | ----: |"]
    for i in items:
        if i["not_used"]:
            continue
        lines.append(f"| `{i['id']}` | {i['name'] or '—'} | {i['type']} | "
                     f"{num(i['base_price'])} | {num(i['quality'])} | {i['stack_count']} |")
    return "\n".join(lines) + "\n"


def md_recipes(recipes: list[dict]) -> str:
    no_station = "(no station)"
    by_station: dict[str, list[dict]] = defaultdict(list)
    label: dict[str, str] = {no_station: no_station}
    for r in recipes:
        for st in r["stations"] or [{"id": no_station, "name": None}]:
            by_station[st["id"]].append(r)
            if st["name"]:
                label.setdefault(st["id"], st["name"])

    lines = ["# Recipes by station", "",
             f"{len(recipes)} recipes (`craft_data` + `craft_obj_data`), "
             f"{len(by_station)} stations.", ""]
    for station in sorted(by_station):
        lines += [f"## {label.get(station, station)} — `{station}`", "",
                  "| recipe | needs | produces | time (s) | energy | points |",
                  "| ------ | ----- | -------- | -------: | -----: | ------ |"]
        for r in sorted(by_station[station], key=lambda x: x["id"]):
            lines.append(f"| `{r['id']}` | {list_txt(r['inputs'])} | {list_txt(r['outputs'])} "
                         f"| {cell(r['craft_time'])} | {cell(r['energy'])} "
                         f"| {points_txt(r['tech_points'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def md_technologies(game: Game, techs: list[dict]) -> str:
    # The table follows the order the tree is drawn in (branch, then y, then
    # x), which says more than the alphabetical order used in the JSON.
    by_id = {t["id"]: t for t in techs}
    order = sorted(load(game, "techs_data"),
                   key=lambda x: (x["branch_type"], x["y"], x["x"]))
    lines = ["# Technologies", "",
             "Tech point cost and what each node unlocks (`techs_data`).",
             "", "| technology | branch | cost | unlocks |",
             "| ---------- | ------ | ---- | ------- |"]
    for raw in order:
        t = by_id[raw["id"]]
        unlocks = ", ".join(f"`{c}`" for c in t["crafts"][:8]) or "—"
        if len(t["crafts"]) > 8:
            unlocks += f" (+{len(t['crafts']) - 8})"
        lines.append(f"| {t['name'] or t['id']} (`{t['id']}`) "
                     f"| {t['branch']['name'] or t['branch']['n']} "
                     f"| {points_txt(t['cost'], num)} | {unlocks} |")
    return "\n".join(lines) + "\n"


def missing_txt(names: EnglishNames, items: list[dict]) -> str:
    not_used = {i["id"] for i in items if i["not_used"]}
    lines = ["# Ids left with `name: null`: no English string for the id, its base",
             "# id without the `:N` suffix, or a locale alias. Grouped by key path.",
             "# Items flagged not_used (hidden from the catalog) are listed separately.",
             ""]
    for where in sorted(names.missing):
        ids = sorted(names.missing[where])
        if where == "items":
            used = [i for i in ids if i not in not_used]
            unused = [i for i in ids if i in not_used]
            lines += [f"## items (used): {len(used)}", *used, "",
                      f"## items (not_used): {len(unused)}", *unused, ""]
        else:
            lines += [f"## {where}: {len(ids)}", *ids, ""]
    return "\n".join(lines)


def run(game: Game) -> None:
    names = EnglishNames(game)
    i, r, t = items(game, names), recipes(game, names), technologies(game, names)
    write(game,
          {"items": i, "recipes": r, "technologies": t},
          {"items": md_items(i), "recipes": md_recipes(r),
           "technologies": md_technologies(game, t)})
    path = os.path.join(game.out, "data", "wiki", "_missing_names.txt")
    with open(path, "w", encoding="utf8") as fh:
        fh.write(missing_txt(names, i))
    print(f"  {path}")
    no_name = [x["id"] for x in i if not x["name"] and not x["not_used"]]
    print(f"\n{len(no_name)} items in use with no name in the localization (e.g. {no_name[:5]})")
