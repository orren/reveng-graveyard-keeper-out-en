"""Graveyard Keeper 2 (demo) catalog.

GK2 is GK1's model redesigned: `GameBalance` is still a single
ScriptableObject, but the classes became `*Def`, the fields moved to camelCase
and `SmartExpression` became `LazyExpression`. Recipe outputs now live inside an
object (`outputItems.chanceOutputItems`) instead of a plain list.

NOTE: this fork left GK2 as upstream had it, so its OUTPUT is still upstream's
Portuguese format -- Portuguese keys (`pt`, `en`, `qtd`, `entradas`...), both
pt-BR and English names, and Portuguese Markdown headings. The string literals
below that end up in `out/gk2/` are that output and are kept verbatim; only the
code around them is in English.
"""
from __future__ import annotations

from collections import defaultdict

from .catalog_common import Names, load, load_locale, write
from .games import Game

#: ItemType (Assembly-CSharp.dll)
ITEM_TYPES = {
    0: "None", 1: "Axe", 2: "Shovel", 3: "Pickaxe", 4: "Hammer", 5: "FishingRod",
    10: "Hand", 11: "Sword", 12: "BodyArmor", 13: "Brain", 14: "Heart", 15: "Flesh",
    16: "Bones", 18: "Bait", 20: "Preach", 22: "Bow", 23: "SurgicalKit",
    24: "Reagents", 25: "SmallTools", 26: "Book", 27: "Talisman", 28: "Spit",
    30: "Embalm", 35: "Skull", 36: "Guts", 37: "Skin", 45: "Collar", 50: "Pike",
    400: "Bag", 666: "Demon",
}

#: TechTreeTab -- the name's key in the locale is `tech_tab_<Name>`.
TECH_TABS = {0: "Building", 1: "Metallurgy", 2: "Farming", 3: "Theology",
             4: "Anatomy", 5: "Cooking"}

#: The three tech points, as fields of their own on CraftDef.
CRAFT_POINTS = {"techRed": "tech_red", "techGreen": "tech_green", "techBlue": "tech_blue"}

#: Portuguese label of each tech point id, as written in the GK2 catalog
#: (red, green, blue, purple, gratitude, happiness).
POINT_LABELS = {
    "r": "vermelho", "g": "verde", "b": "azul", "v": "roxo",
    "gratitude_points": "gratidao",
    "tech_red": "vermelho", "tech_green": "verde", "tech_blue": "azul",
    "happiness": "felicidade",
}

#: PureValueType
PURE_NONE, PURE_FLOAT, PURE_BOOL, PURE_STRING = 0, 1, 2, 3


def expr(value):
    """LazyExpression -> a number when it is a pure value, else the raw expression."""
    if not isinstance(value, dict):
        return value
    kind = value.get("pureValueType", PURE_NONE)
    if kind == PURE_FLOAT:
        return round(value["pureValueFloat"], 4)
    if kind == PURE_BOOL:
        return bool(value["pureValueBool"])
    return value.get("expressionString") or None


def ref(names: Names, obj_id: str) -> dict:
    return {"id": obj_id, "pt": names.name(obj_id, "pt"), "en": names.name(obj_id, "en")}


def label(names: Names, obj_id: str) -> str:
    return names.name(obj_id, "pt") or names.name(obj_id, "en") or obj_id


def item_ref(names: Names, item: dict) -> dict:
    """Recipe input/output, with the quantity and the range when there is one."""
    out = ref(names, item["id"])
    count = expr(item.get("count"))
    lo, hi = expr(item.get("minValue")), expr(item.get("maxValue"))
    if isinstance(count, str):
        out["qtd"] = None
        out["qtd_expr"] = count
    else:
        out["qtd"] = count
    if lo is not None and hi is not None:
        out["qtd"], out["qtd_max"] = lo, hi
    chance = expr(item.get("chance"))
    if chance is not None:
        out["chance"] = chance
    if item.get("outputGroupId"):
        out["grupo"] = item["outputGroupId"]
    return out


def outputs_of(names: Names, craft: dict) -> list[dict]:
    """`outputItems` is an object with two lists, not a list."""
    output = craft.get("outputItems") or {}
    refs = [item_ref(names, i) for i in output.get("chanceOutputItems", [])]
    # Group output: a list of alternatives, each with its own chance.
    for group in output.get("groupChanceOutputItems", []):
        for i in group.get("chanceItems", []):
            r = item_ref(names, i)
            r["alternativa"] = True
            refs.append(r)
    return refs


def qty_txt(entry: dict) -> str:
    """'3x <name>' -- or the raw expression, when the quantity depends on a perk."""
    q = entry.get("qtd_expr")
    if q is None:
        q = f"{entry['qtd']:g}" if entry.get("qtd") is not None else "?"
    top = entry.get("qtd_max")
    if top is not None:
        q += f"–{top:g}" if isinstance(top, (int, float)) else f"–{top}"
    return f"{q}x {entry['pt'] or entry['en'] or entry['id']}"


def list_txt(entries: list[dict]) -> str:
    return "<br>".join(qty_txt(e) for e in entries) or "—"


def points_txt(pts: dict) -> str:
    return " ".join(f"{v} {POINT_LABELS.get(k, k)}" for k, v in pts.items()) or "—"


def items(game: Game, names: Names) -> list[dict]:
    out = []
    for it in load(game, "itemDefs"):
        out.append({
            "id": it["id"],
            "pt": names.name(it["id"], "pt"),
            "en": names.name(it["id"], "en"),
            "descricao_pt": names.desc(it["id"], "pt"),
            "descricao_en": names.desc(it["id"], "en"),
            "tipo": ITEM_TYPES.get(it["type"], str(it["type"])),
            "preco_base": it["basePrice"],
            "qualidade": it["quality"],
            "pilha": it["stackCount"],
            "tem_durabilidade": bool(it["hasDurability"]),
            "e_ferramenta": bool(it["isTool"]),
            "e_arma": bool(it["isWeapon"]),
            "e_semente": bool(it["isSeed"]),
            "e_combustivel": bool(it["isFuel"]),
            "e_produto": bool(it["isProduct"]),
            "e_ponto_de_tecnologia": bool(it["isTechPoint"]),
            "grupos": it["itemGroupIds"],
        })
    return sorted(out, key=lambda i: i["id"])


def recipes(game: Game, names: Names) -> list[dict]:
    unlocked_by: dict[str, list[str]] = defaultdict(list)
    for tech in load(game, "techDefs"):
        for craft_id in tech["craftsAfterUnlock"]:
            unlocked_by[craft_id].append(tech["id"])

    out = []
    for c in load(game, "craftDefs"):
        pts = {}
        for field, key in CRAFT_POINTS.items():
            v = expr(c.get(field))
            if v:
                pts[key] = v
        out.append({
            "id": c["id"],
            "origem": "craft",
            "estacoes": [ref(names, o) for o in c["craftsIn"]],
            "entradas": [item_ref(names, i) for i in c["needItems"]],
            "entradas_da_estacao": [item_ref(names, i) for i in c["needItemsFromWgo"]],
            "saidas": outputs_of(names, c),
            "pontos_tecnologia": pts,
            "tempo_s": expr(c["duration"]),
            "energia_por_tick": expr(c["energyPerTick"]),
            "insanidade_por_tick": expr(c["insanityPerTick"]),
            "oculta": bool(c["isHidden"]),
            "precisa_desbloquear": bool(c["isNeedsUnlock"]),
            "e_automatica": bool(c["isAuto"]),
            "e_de_estrela": bool(c["isStarCraft"]),
            "combustivel": c["fuelItemDefId"] or None,
            "perks": c["linkedPerks"],
            "aba": c["tabId"] or None,
            "liberada_por": unlocked_by.get(c["id"], []),
        })
    return sorted(out, key=lambda r: r["id"])


def technologies(game: Game, names: Names) -> list[dict]:
    out = []
    for t in load(game, "techDefs"):
        tab = TECH_TABS.get(t["tab"], str(t["tab"]))
        cost = {k: v for k, v in (("tech_red", t["redSpheresPrice"]),
                                  ("tech_green", t["greenSpheresPrice"]),
                                  ("tech_blue", t["blueSpheresPrice"])) if v}
        out.append({
            "id": t["id"],
            "pt": names.name(t["id"], "pt"),
            "en": names.name(t["id"], "en"),
            "aba": {"id": tab, "pt": names.name(f"tech_tab_{tab}", "pt")},
            "custo": cost,
            "requer": t["parents"],
            "libera_receitas": t["craftsAfterUnlock"],
            "libera_construcoes": t["buildingsAfterUnlock"],
            "libera_perks": t["perksAfterUnlock"],
            "libera_formulas": t["alchemyFormulasAfterUnlock"],
            "disponivel_na_demo": bool(t["isAvailableInDemo"]),
            "oculta_no_inicio": bool(t["hiddenAtStart"]),
        })
    return sorted(out, key=lambda x: (x["aba"]["id"], x["id"]))


def md_items(items: list[dict]) -> str:
    lines = ["# Itens", "",
             f"{len(items)} itens em `itemDefs`. Nome pt-BR e o da traducao oficial do jogo.",
             "", "| id | pt-BR | en | tipo | preco | qualidade | pilha |",
             "| -- | ----- | -- | ---- | ----: | --------: | ----: |"]
    for i in items:
        lines.append("| `{id}` | {pt} | {en} | {tipo} | {preco_base:g} | {qualidade:g} | {pilha} |".format(
            **{**i, "pt": i["pt"] or "—", "en": i["en"] or "—"}))
    return "\n".join(lines) + "\n"


def md_recipes(recipes: list[dict], names: Names) -> str:
    by_station: dict[str, list[dict]] = defaultdict(list)
    for r in recipes:
        for st in r["estacoes"] or [{"id": "(sem estacao)"}]:
            by_station[st["id"]].append(r)

    lines = ["# Receitas por estacao", "",
             f"{len(recipes)} receitas (`craftDefs`), {len(by_station)} estacoes.", ""]
    for station in sorted(by_station):
        lines += [f"## {label(names, station)} — `{station}`", "",
                  "| receita | precisa | produz | tempo | energia/tick | pontos |",
                  "| ------- | ------- | ------ | ----: | -----------: | ------ |"]
        for r in sorted(by_station[station], key=lambda x: x["id"]):
            lines.append("| `{id}` | {n} | {o} | {t} | {e} | {p} |".format(
                id=r["id"], n=list_txt(r["entradas"]), o=list_txt(r["saidas"]),
                t=r["tempo_s"] if r["tempo_s"] is not None else "—",
                e=r["energia_por_tick"] if r["energia_por_tick"] is not None else "—",
                p=points_txt(r["pontos_tecnologia"])))
        lines.append("")
    return "\n".join(lines) + "\n"


def md_technologies(techs: list[dict]) -> str:
    lines = ["# Tecnologias", "",
             "Custo em esferas e o que cada no libera (`techDefs`). A coluna demo diz se "
             "o no esta disponivel nesta build.",
             "", "| tecnologia | aba | custo | demo | libera |",
             "| ---------- | --- | ----- | :--: | ------ |"]
    for t in techs:
        cost = " ".join(f"{v:g} {POINT_LABELS.get(k, k)}" for k, v in t["custo"].items())
        unlocks = t["libera_receitas"] + t["libera_construcoes"]
        txt = ", ".join(f"`{c}`" for c in unlocks[:6]) or "—"
        if len(unlocks) > 6:
            txt += f" (+{len(unlocks) - 6})"
        lines.append(f"| {t['pt'] or t['id']} (`{t['id']}`) | {t['aba']['pt'] or t['aba']['id']} "
                     f"| {cost or '—'} | {'sim' if t['disponivel_na_demo'] else 'nao'} | {txt} |")
    return "\n".join(lines) + "\n"


def run(game: Game) -> None:
    names = Names(game, {"pt": load_locale(game, "pt-br"), "en": load_locale(game, "en")})
    i, r, t = items(game, names), recipes(game, names), technologies(game, names)
    write(game,
          {"itens": i, "receitas": r, "tecnologias": t},
          {"itens": md_items(i), "receitas": md_recipes(r, names),
           "tecnologias": md_technologies(t)})
    no_name = [x["id"] for x in i if not x["pt"]]
    outside_demo = [x for x in t if not x["disponivel_na_demo"]]
    print(f"\n{len(no_name)} items with no name in the localization (e.g. {no_name[:5]})")
    print(f"{len(outside_demo)} of {len(t)} technologies marked as outside the demo")
