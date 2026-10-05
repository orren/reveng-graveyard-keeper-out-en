# 4. Bridge to keeper-wiki-fnd

Upstream built this project for `keeper-wiki-fnd`, a Portuguese-language fan wiki. Its goal
is to replace "checked on the fandom wiki" with **"extracted from the game"**.

`keeper-wiki-fnd` has a hard rule in its `CLAUDE.md`: *don't write a game fact without a
source*. Today the source is the Graveyard Keeper Wiki (fandom) plus guides. With this
project, the source becomes the game binary. It's the only source that neither gets
things wrong on purpose nor goes stale on its own.

Names in quotes below are the game's official pt-BR strings, with the English in
parentheses where it helps: that comparison is the point of some sections.

## What comes out ready to use

| File | Count | Content |
| ---- | ----: | ------- |
| `out/gk1/data/wiki/items.json` | 1,157 | id, official English name and description, type, base price, quality, stack, `icon`, `stars`, `group`, `can_be_used`, `on_use`, `on_use_expr` |
| `out/gk1/data/wiki/recipes.json` | 2,634 | stations (with `icon`), inputs, outputs, time, energy, tech points, what unlocks it, and (construction) `built_object.icon` |
| `out/gk1/data/wiki/technologies.json` | 187 | branch (with name and `icon`), cost, prerequisites, what it unlocks, DLC |
| `out/gk1/data/wiki/_missing_names.txt` | — | ids that have no English name anywhere in the locale |
| `out/gk1/icons/*.png` | 952 | icons for items, workstations, construction objects and tech branches, plus the three quality stars and the 6 HUD "days of the week" glyphs |
| `out/gk2/data/wiki/{itens,receitas,tecnologias}.json` | 814 / 825 / 236 | GK2 demo, still in upstream's Portuguese-keyed format (see below) |

GK1 comes out in English: keys, names and Markdown. GK2 is left exactly as upstream
produces it, with Portuguese keys and both pt-BR and English names; its adapter
(`scripts/gk/catalog_gk2.py`) adds `energia_por_tick` (energy per tick), `e_automatica`
(is automatic), `combustivel` (fuel) and, on technologies, `disponivel_na_demo` (available
in the demo). Each game has its own adapter in `scripts/gk/catalog_<game>.py` because the
raw balance is quite different.

A GK1 recipe looks like this:

```json
{
  "id": "flitch_2",
  "source": "craft",
  "craft_type": "None",
  "stations": [{"id": "mf_saw_1", "name": "Circular Saw", "icon": "i_b_mf_saw_1"}],
  "inputs": [{"id": "wood", "name": "Log", "qty": 1.0}],
  "station_inputs": [],
  "outputs": [{"id": "flitch", "name": "Flitch",
               "qty": null, "qty_expr": "7+Ppar(\"p_woodworker\")*2"}],
  "tech_points": {"red": 1},
  "craft_time": 2.0, "energy": "10-Ppar(\"p_woodworker\")*5",
  "sanity": 0.0, "difficulty": 0.0,
  "hidden": false, "needs_unlock": false,
  "linked_perks": [], "unlocked_by": []
}
```

The full field list is in [`README.md`](../README.md#gk1-field-reference).

## Icon, star and quality group

Three fields in GK1's `items.json` exist so the wiki can show an item the way the game
does.

**`icon`** is the sprite name, following `ItemDefinition.GetIcon()`. It's the balance's
`icon` field, or `"i_" + id` when that field is empty (483 items). `extract-sprites.py`
writes the matching PNG to `out/gk1/icons/<icon>.png`.

**`stars`** is 1, 2 or 3, meaning the bronze, silver or gold star the game draws over
the icon. Otherwise it's `null`. The condition is the one in `GetQualityIconName()`:
`quality_type == Stars` and `quality >= 1`. The sprite is `item_star_<stars>.png`.
**A `:N` suffix on the id isn't enough.** `hamp_crop:1/2/3` has the suffix, but its
`quality_type` is Default and its `quality` is 0, so in the game hemp shows no star at
all.

**`group`** is the item id without the quality suffix (`pumpkin_crop:2` →
`pumpkin_crop`). It's set for the 242 items that are levels of the same item. It
implements the part of `Item.InitMultiqualityItems()` that matters here: an id **with no
definition of its own** becomes the group of the ids that start with `<id>:`. That's how
1,157 items become **998 entries**: 915 items without a group plus 83 groups.

This closes a gap in the data. **164 recipes ask for the group, not a level.** That's
80 different groups (`pumpkin_crop`, `fish_pike`, `meal:baked_pumpkin`), and those ids
don't exist in `items_data`. A consumer of `recipes.json` that doesn't know about groups
treats such an input as "not an item" and loses the link.

Two things stay **out** of `group` on purpose:

- `test_paper` and `test_scroll` have a definition of their own *and* suffixed variants.
  For the game the group never comes into being, and it doesn't here either.
- **Prefix groups** (`meal`, `snack`, `dessert`, `chisel`, `cover`, `fillet_fish`,
  `brain`, `heart`, `lungs`, `intestine`, `organs`) gather **different** items ("any
  meal", "any chisel"), not levels of the same item. 38 recipes ask for one of these
  eleven. It's a different concept and deserves different handling.

## What an item does when the player uses it

Three fields answer "what is this for?", a question the recipe list can't answer. Food
isn't an ingredient of anything, so its page used to end with "no recipe uses this item".

**`can_be_used`** is the game's `can_be_used`: the item can be used from the inventory.
240 items can.

**`on_use`** is the **fixed** part of the effect, `{resource: number}`, taken from
`params_on_use`. Examples: `{"energy": 24.0}` on the silver baked pumpkin, and
`{"energy": 80.0, "hp": -20.0}` on the infusion. Health comes from a field separate from
the `_res_type`/`_res_v` pair, and it **can be negative**: the poisonous mushroom only
takes. 189 items have a fixed effect:

- 161 give energy only;
- 19 give energy and health;
- 2 give health only (`pot_heal` and `shr_agaric`);
- 7 give tech points.

**`on_use_expr`** is the part that's a formula, kept raw by the same rule as `qty_expr`.
`AddPpar("energy", 20*Ppar("food_multiplier"))` is the perk-dependent gain, and
`AddBuff("buff_longtimer")` is the buff the food gives. 153 items have one. None of GK1's
229 expressions comes simplified to a constant, so none becomes a number without
evaluating it.

> **Read `on_use` together with `can_be_used`.** On tools (`can_be_used` false), the game
> stores the energy **cost** per swing in the same field. `axe_1` has
> `{"energy": -1.0}`, and that isn't what the axe gives back. 26 items are like this.

### Missing art

Of the 834 icon names, **703 have a sprite** in `resources.assets`. Of the 131 missing,
127 belong to `not_used` items: art that left the game and left the
definition behind. The other four are missing **in the game too**. `hop_honey:1/2/3`
(Hidromel, mead) and `lungs:lungs_1` (Pulmões, lungs) fall back to `"i_" + id`, and
`i_hop_honey:1` doesn't exist in any collection. No look-alike substitute is invented:
consumers show the blank.

## Workstation, construction object and tech branch icons

Items aren't the only things with sprites in the game. Three other fields, all GK1 only,
follow the same rule: a sprite name, `null` when none exists, never invented.

**`recipes[].stations[].icon`** follows the SAME rule as `WorldGameObject.
GetUniversalObjectInfo()`, the function that picks the icon in the game's interaction
panel. It isn't just the `custom_icon` of the `ObjectDefinition` (`objs_data`). There's no
dedicated "workstation" class: it's the same object as anything placeable on the map.
`custom_icon` alone covers little (87 of 228). Most objects never needed one, because the
game has a naming-convention fallback that changes with `interaction_type`:

| `interaction_type` | Rule |
| --- | --- |
| Craft (1) | icon of the "Put" recipe that builds this object, else `custom_icon`, else `"i_b_" + id` |
| RunScript (2) / Builder (4) | `custom_icon`, else the build menu icon, else `"i_z_" + id` |
| autopsy table | `custom_icon`, else `"i_b_" + id` (without the recipe override) |
| Chest, Grave, None | `custom_icon`, else the build menu icon. The game has no fallback for these; `UniversalObjectInfo.icon` stays `null` |

The **build menu icon** is the only step that doesn't come from the interaction panel. It's
the `icon` of any `craft_obj_data` recipe that builds the object (except demolition,
`Remove`): the sprite the player sees while building it. Without it, the refugee camp
(Game of Crone) lost its kitchen, beehive and well:

- the camp builds with `build_type` "None", not "Put";
- the kitchen and the beehive are None in the panel;
- the well's `i_z_refugee_camp_well` doesn't exist in the game.

The beehive is built as `refugee_camp_hive_place`, which becomes `refugee_camp_hive` when
it finishes (`after_hp_0`), and the icon carries over to the final object. This step
doesn't change the art of any workstation that already had a sprite. Only the 8 that had
none gain an icon: the 5 in the camp, plus `beehouse_1`, `bush_berry_garden` and
`tree_apple_garden`.

Three more ids (`grave_ground`, `mf_balsamation_1/2`) have an icon written straight into
the C#, outside any rule. With the fallback and the build menu, coverage rises to
**175 of 228** (77%). That includes the Carpentry workbench (`mf_workbench_1`), whose
`custom_icon` is empty but which falls back to `i_b_mf_workbench_1`. An example of a
recipe override: `mf_alchemy_mill` (Alchemy mill) → `i_b_alchemy_millstone`. As with item
icons, some of the guessed fallbacks have no real sprite: names of test/debug objects,
such as `i_z_slava_test_builder`. `extract-sprites.py` reports what's missing, and
consumers show the blank.

**`recipes[].built_object.icon`** is the `icon` of the construction recipe itself
(`craft_obj_data`): the sprite the build menu shows for that result. Coverage is high:
**185 distinct objects**, or 96% of the 533 construction recipes. It's preferred over the
built object's `custom_icon` for two reasons. Demolition (`build_type: "Remove"`) uses the same
icon as the original construction, and not every built object has its own `custom_icon`.

**`technologies[].branch.icon`** is fixed: `"i_tbranch_" + branch.n`. There's no per-technology
icon, only one per branch (`i_tbranch_1` to `i_tbranch_8`, one per specialty/color).
Technologies in the same branch repeat the same icon, the same way a workstation repeats
its icon in every recipe that uses it.

All three go through the same `extract-sprites.py`, into the same `out/gk1/icons/` folder,
without changing the sprite reader. They're sprites like any other in `resources.assets`.

## Mapping to the `Recipe` type

The wiki's `src/lib/content/types.ts` expects:

```ts
interface Recipe { id; station; time?; ingredients; result; category; en?; note? }
```

The conversion, field by field:

| `Recipe` | Comes from | Note |
| -------- | ---------- | ---- |
| `id` | recipe `id` | the game id is stable across builds, so it works as a key |
| `station` | `stations[].name` | **a recipe with N stations becomes N `Recipe`s**, as the wiki already does with `ripa-cavalete`/`ripa-serra` |
| `ingredients` | `inputs` | `{name, qty}` |
| `result` | `outputs[0]` | a recipe with more than one output doesn't fit the current type |
| `en` | `outputs[0].name` | the official English name, which the wiki's search already uses |
| `time` | `craft_time` | format it (`"2s"`); it's the automatic-craft time only |
| `note` | `tech_points` | becomes "+1 red", which is what the wiki writes today |
| `category` | **editorial decision** | the game has no category; this stays human curation |

Recommended filters before generating content:

- drop `hidden: true` (62 recipes);
- drop items with `not_used: true` (387 items);
- treat `source: "construction"` as a separate section, because construction isn't a
  workstation recipe.

### What doesn't convert automatically

- **`qty_expr`.** When the quantity depends on a perk (`7+Ppar("p_woodworker")*2`), the
  base number is what the player sees without the perk. The rest deserves a text note.
  The same goes for `energy`.
- **Quality/stars.** The formula exists (see `02`), but the probability depends on the
  player's perks. That's article content, not table content.
- **Station name.** 66 of the 228 workstation objects have no English name even with
  aliases (`sawhorse`, for example). The display name for those remains a human choice.

## ⚠️ The finding that changes already-published content

**The game has an official Portuguese translation, and it isn't the one the wiki uses.**
`GJL.AVAILABLE_LOCALE_NAMES` lists "Português do Brasil", and `lng_pt-br` carries the
10,961 strings. Compared with the 25 hand-written recipes on the wiki, **12 use a name
different from the official one**:

| en | wiki today | official in game |
| -- | ---------- | ---------------- |
| Flitch | Ripa | **Tábua** |
| Wood billet | Tarugo de madeira | **Pedaço de madeira** |
| Wooden plank | Tábua de madeira | **Placa de madeira** |
| A polished brick of stone | Tijolo de pedra polido | Tijolo polido de pedra |
| Wooden marker | Marco de madeira | Marcador de madeira |
| Clean paper | Papel limpo | Papel vazio |
| Ink | Tinta de escrever | Tinta |
| Pigskin paper | Papel de pele de porco | Papel de couro de porco |
| Wooden/Stone grave fence | Cerca de túmulo de madeira/pedra | Cerca de madeira/pedra de túmulo |

The first three are the dangerous ones. In Portuguese, what the wiki calls **"Tábua de
madeira"** the game calls "Placa de madeira" (Wooden plank), while **"Tábua"** in the game
is another item, the Flitch. A reader with the game open in Portuguese reads the wrong
recipe.

**Recommendation:** adopt the official name as the canonical name and keep the fandom name
as a search alias. `Recipe.en` already exists for this. The type could use an
`alias?: string[]` so the old name stays findable. It's Letícia's decision; this project
only brings the data.

## ⚠️ GK2 can't inherit GK1's glossary

The wiki already plans for two games (`content/gk1/`, `content/gk2/`), and the obvious
temptation is to reuse one game's translation in the other. **That doesn't work.** Of the
90 item ids that exist in both games, **37 have a different pt-BR name**:

| id | GK1 | GK2 |
| -- | --- | --- |
| `flitch` | Tábua | **Placa** |
| `ceramic_1` | Potes de cerâmica | **Placa de Argila** |
| `ceramic_2` | Jarro de cerâmica | **Urna de Argila** |
| `axe_1` / `axe_2` | Machado I / II | **Machado de Bronze / de Ferro** |
| `ash` | Ash *(untranslated)* | **Cinzas** |
| `detail_1` | Peças simples de ferro | Peça de Ferro simples |
| `bag_alchemy` | Bolsa do alquimista | Bolsa de Alquimista |

The convention changed too. GK2 uses **Title Case on Every Word** ("Bancada de Carpintaria
I"), and GK1 doesn't ("Bancada de cozinhar"). The same id can also be a different item:
`ceramic_1` stopped being "pots" and became "clay plate".

In locale numbers: of the 183 keys that exist in both `lng_pt-br` files, **103 have
different text**. The conclusion for the wiki is that item names are **per-game** data,
never shared. Fortunately, that's how `GameContent` is already modeled.

## GK2 demo scope

The demo's `GameBalance` carries the balance of the **full game in development**: 13,754
definitions, with **185 of the 236 technologies** marked `disponivel_na_demo: false`. It's
useful for previewing content but isn't publishable fact, because it may change before
release. If it becomes content, mark it as provisional and filter on `disponivel_na_demo`.

## Running it

```sh
python3 scripts/catalog.py gk1                     # from the committed out/ data, no game needed
./scripts/setup.sh                                  # once, before anything that reads the game
./.venv/bin/python scripts/extract-sprites.py gk1  # icons; after the catalog
```

To read with human eyes before it becomes content: `out/gk1/catalog/recipes.md` (recipes
grouped by station), `items.md` and `technologies.md`.
