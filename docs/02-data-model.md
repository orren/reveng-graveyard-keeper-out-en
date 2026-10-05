# 2. The game's data model

This document describes **GK1** in detail. The [GK2 section](#gk2-the-same-design-rewritten)
covers what changes in GK2. The idea is the same in both games; almost all the names
changed.

## In one sentence

**All of Graveyard Keeper's balance is a single ScriptableObject.**
`GameBalance.LoadGameBalance()` calls `Resources.Load<GameBalance>("game_data")`. That
4.3 MB object carries 34 definition lists: items, recipes, objects, technologies, fish,
souls, achievements and more. There's no database, no external JSON, no AssetBundle.
Whoever reads `game_data` reads the entire game.

The names the player sees are **not** in it. They live in the 11 `lng_*` assets (class
`GJL`), linked by id. Joining the two is what `scripts/catalog.py` does.

## The 34 lists (`out/gk1/data/balance/`)

| List | Count | Class | What it is |
| ---- | ----: | ----- | ---------- |
| `craft_data` | 2101 | `CraftDefinition` | item recipes (including alchemy, sermons, autopsy) |
| `objs_data` | 1318 | `ObjectDefinition` | world objects: workstations, trees, furniture, NPCs |
| `items_data` | 1157 | `ItemDefinition` | items (770 in use; the rest are `not_used`) |
| `craft_obj_data` | 533 | `ObjectCraftDefinition` | **construction** recipes (build/remove an object) |
| `techs_data` | 187 | `TechDefinition` | technology tree nodes |
| `spawners_data` | 169 | `SpawnerDefinition` | what spawns where |
| `achievements_data` | 125 | `AchievementDefinition` | Steam achievements |
| `logics_data` | 81 | `LogicDefinition` | object logics (furnace, garden bed, beehive…) |
| `souls_data` | 63 | `SoulDefinition` | souls |
| `bodies_data` | 54 | `BodyDefinition` | bodies and their parts |
| `world_zones_data` | 45 | `WorldZoneDefinition` | map zones |
| `perks_data` | 44 | `PerkDefinition` | perks (they feed into craft quality) |
| `buffs_data` | 34 | `BuffDefinition` | buffs |
| `quests_data` | 32 | `QuestDefinition` | quests |
| `vendors_data` | 31 | `VendorDefinition` | vendors and what they buy/sell |
| `fishes_data` | 26 | `FishDefinition` | fish |
| `object_groups` | 22 | `ObjectGroupDefinition` | object grouping |
| `product_types_data` | 22 | `ProductTypeDefinition` | product types (tavern) |
| `cutscenes_data` | 17 | `CutscenesDLCDefinition` | DLC cutscenes |
| `projectiles_data` | 10 | `ProjectileDefinition` | projectiles |
| `pray_events_data` · `tech_branches_data` · `tools_data` | 8 | — | prayer events · tree branches · tool types |
| `reservoirs_data` · `transport_paths` | 5 | — | fishing spots · transport routes |
| `tavern_events` | 4 | `TavernEventDefinition` | tavern events |
| `works_data` | 3 | `WorkDefinition` | jobs |
| `auras_data` · `workers_data` | 2 | — | auras · zombie workers |
| `chars_data`, `grade_levels`, `grave_requirement_data`, `jobs_atom_data`, `jobs_data` | 0 | — | **empty in this build** |

Total: **6,116 definitions**. Each list becomes a file in `out/gk1/data/balance/<list>.json`.
It's faithful to the binary (nothing filtered, nothing renamed) and serves as the baseline
for diffing between versions.

## Types that show up everywhere

### `BalanceBaseObject`
Just a string `id`. Every definition inherits from it, and the `id` is the universal key.
It links recipe to item, item to localization, and technology to recipe.

### `SmartExpression`: numbers that aren't numbers
Almost every numeric field in the balance is an expression, not a constant:

```json
{"_expression": "10-Ppar(\"p_woodworker\")*5", "_simplified": false, "_simpified_float": 0.0}
```

`_simplified = true` means the expression is a plain number and `_simpified_float` holds
it. Otherwise it's a formula, where `Ppar("p_woodworker")` is the player's perk level. The
`expr()` helper in `catalog_gk1.py` returns the number when it can and the raw string when it
can't. The formula is information, not noise.

### `GameRes`: a bag of resources
Two parallel lists, `_res_type` × `_res_v`. This is how a technology's cost is read:

```json
{"_res_type": ["r","g","b","v","gratitude_points"], "_res_v": [40,5,0,0,0]}
```

That's 40 red points and 5 green. The five types are in `TechDefinition.TECH_POINTS`:
`r` red, `g` green, `b` blue, `v` purple, `gratitude_points` gratitude.

### `Item`: ⚠️ `value` is a dead field
A recipe input or output is an `Item`, and it has **three** quantity fields: `value`
(int), plus `min_value` and `max_value` (SmartExpression).

**`min_value`/`max_value` are what count.** They're what
`WorldGameObject.GetCraftAmountCounter` evaluates. `value` was left behind, and it lies:

| recipe | `value` | `min_value` | truth |
| ------ | ------: | ----------- | ----- |
| `flitch_2` (saw) | 1 | `7+Ppar("p_woodworker")*2` | **7** flitches, +2 per perk level |
| `wood_balk_1` (saw) | 1 | `3+Ppar("p_woodworker")` | **3** beams |
| `flitch` (sawhorse) | 6 | `6` | 6 flitches |

This detail is what made the catalog's first run disagree with the fandom wiki. The fix is
in `qty()` in `scripts/gk/catalog_gk1.py`.

## Recipes

`CraftDefinition` is large. These are the fields that matter for the wiki:

| Field | Meaning |
| ----- | ------- |
| `craft_in` | ids of the objects where the recipe appears (the "station") |
| `needs` / `output` | inputs and outputs (`Item`, see above) |
| `needs_from_wgo` | what the station consumes from itself: in practice, `fire` (firewood) |
| `craft_time`, `energy`, `sanity` | cost, as `SmartExpression` |
| `difficulty`, `linked_perks`, `linked_buffs` | feed into the quality (stars) calculation |
| `hidden`, `needs_unlock` | hidden recipe / needs unlocking |
| `craft_type` | `ResourcesBasedCraft`, `Survey`, `MixedCraft`, `Fixing`, `AlchemyDecompose`, `PrayCraft`, `RatBuff`, `RefugeeCampCraft` |

Outputs whose id is `r`/`g`/`b`/`v`/`gratitude_points` **aren't items**. They're the tech
points the craft awards. The catalog splits them into `tech_points`.

`ObjectCraftDefinition` (construction) extends the previous class and changes one important
thing. `craft_in` stays empty, and the "station" is `builder_ids` (the construction site).
`build_type` is one of two values:

- `Put` builds the object and consumes `needs`;
- `Remove` demolishes it and returns materials in `output`. Its id has the `:r:` prefix.

### Quality (stars)
`GetMultiqualityResult` spells it out:

```
value = average ingredient quality + sum of perk stars + buffs − recipe difficulty
```

That value becomes the three probabilities of 1, 2 and 3 stars via `Clamp`. It's in
`out/gk1/src-csharp/Assembly-CSharp/CraftDefinition.cs`.

## Localization (`GJL`)

Two parallel lists, `txt_ids` × `txts`, with 10,961 pairs per language and 11 languages
(`en de fr pt-br es ru it pl ja zh_cn ko`). Conventions:

| Key | Content |
| --- | ------- |
| `<id>` | item/object/technology name |
| `<id>_d` | description |
| `tbranch_<n>` | technology tree branch name |

An item with stars (`id:2`) falls back to its base id. That's what
`ItemDefinition.GetItemName` does, and the catalog's `Names.name()` does the same.

The locale also carries an `aliases` table, and the game's `GJL.L()` checks it **before**
the dictionary, as a chain: `1h_ore_metal` → `t_iron_ore_2` → "Minério de ferro" (Iron
ore). `load_locale()` resolves aliases the same way. Without it, 51 items,
20 workstations and 7 technologies had no name. The modified organs (`blood:blood_1_0`)
also fell back to the base name, "Sangue" (Blood), instead of "Sangue modificado"
(Modified blood). An alias whose target isn't in the dictionary makes the game show the
raw target ("Advanced gravestones"). That isn't a translation, so it's ignored.

**24 items in use have no name, even with aliases.** They're all sermon bonuses
(`b_circle:1`, `b_techpoint_red:3`…). For these, the catalog leaves `name` null instead of
inventing a name, and lists them in `out/gk1/data/wiki/_missing_names.txt`.


---

# GK2: the same design, rewritten

`Resources.Load<GameBalance>("GameBalance")` still returns the whole game. What changed:

| | GK1 | GK2 |
| --- | --- | --- |
| Asset | `game_data` | `GameBalance` |
| Classes | `ItemDefinition`, `CraftDefinition`… | `ItemDef`, `CraftDef`… (`Def` suffix) |
| Fields | `snake_case` (`base_price`) | `camelCase` (`basePrice`) |
| Expressions | `SmartExpression` | `LazyExpression` (in `LazyBearTechnology.dll`) |
| Localization | `GJL` | `LazyBearTechnology.LL` |
| Recipe quantity | `min_value`/`max_value` (and a dead `value`) | `count`, with `minValue`/`maxValue` for ranges |
| Recipe output | `output` list | `outputItems` object with `chanceOutputItems` |
| Tech points | output items with id `r`/`g`/`b` | their own fields `techRed`/`techGreen`/`techBlue` |
| Technology cost | `GameRes price` | `redSpheresPrice`/`greenSpheresPrice`/`blueSpheresPrice` (int) |
| Technology branch | `branch_type` → locale `tbranch_<n>` | `tab` (`TechTreeTab`) → locale `tech_tab_<Name>` |

Some conventions **didn't** change:

- `id` is the universal key;
- the name comes from the locale under `<id>`, and the description under `<id>_d`;
- an id with a suffix (`item:2`) falls back to the base id.

## GK2's 33 lists (`out/gk2/data/balance/`)

| List | Count |
| ---- | ----: |
| `alchemyMixSourceDefs` | 6960 |
| `wgoDefs` | 1443 |
| `craftDefs` | 825 |
| `itemDefs` | 814 |
| `buildingDefs` | 614 |
| `questDefs` | 538 |
| `surveyDefs` | 396 |
| `inspirationDefs` | 382 |
| `perkDefs` | 310 |
| `wsoDefs` | 303 |
| `techDefs` | 236 |
| `talentLevelUpDefs` | 179 |
| `worldZoneDefs` | 105 |
| `vendorOrderDefs` | 74 |
| `bodyDefs` | 71 |
| `townBuildingDefs` | 63 |
| `gameLogicsDefs` | 61 |
| `sermonDefs` | 58 |
| `constDefs` | 53 |
| `achievementDefs` | 38 |
| `fighterDefs` | 34 |
| `fishingDefs` | 33 |
| `talentExpLevelDefs` | 30 |
| `alchemyFormulaDefs` | 29 |
| `fightDefinitions` | 26 |
| `vendorDefs` | 21 |
| `toolTypes` · `wgoGroupDefs` | 12 |
| `gameResSystemDefs` | 10 |
| `porterStationDefs` | 9 |
| `mercenariesDefs` | 7 |
| `talentDefs` | 5 |
| `sermonConfigDefs` | 3 |

That's **13,754 definitions**, more than twice GK1, in a demo. `wgoDefs` (World Game
Objects) is what GK1 called `objs_data`, and `wsoDefs` are static scenery objects.
`alchemyMixSourceDefs`, at almost 7,000 rows, is the alchemy combination table.

## `LazyExpression`

```json
{"expressionString": "1", "pureValueType": 1, "pureValueFloat": 1.0, "pureValueBool": false}
```

`pureValueType` is the `PureValueType` enum: `0 None`, `1 Float`, `2 Bool`, `3 String`.
When it's `Float`, `pureValueFloat` holds the value. When it's `None` and there is an
`expressionString`, it's a formula. The `expr()` helper in `catalog_gk2.py` applies
exactly this.

## Recipes in GK2

```json
{
  "id": "wooden_plank",
  "craftsIn": ["woodworking_workbench_1", "woodworking_workbench_2"],
  "needItems": [{"id": "flitch", "count": {...}, "groupType": 0}],
  "outputItems": {
    "chanceOutputItems": [{"id": "wooden_plank", "count": {...}, "minValue": {...},
                           "maxValue": {...}, "chance": {...}, "isStarGroup": false}],
    "groupChanceOutputItems": []
  },
  "duration": {...}, "energyPerTick": {...}, "techRed": {...}
}
```

Two gotchas:

- **`outputItems` is an object, not a list.** The outputs are in `chanceOutputItems`.
  Alternatives with a chance go in `groupChanceOutputItems[].chanceItems`. Only one recipe
  uses this in the demo: `energy_potion_3`, with chance `perk_alchemist`.
- **Tech points moved out of the outputs.** In GK1 they were items with id `r`/`g`/`b`
  mixed into `output`. Here they're `techRed`/`techGreen`/`techBlue`, each an expression.

## Demo scope

`TechDef.isAvailableInDemo` marks what the demo unlocks: **185 of the 236 technologies are
excluded**. The file carries the balance of the entire game in development. That's useful
for previewing content but risky to publish as fact, because it may change before
release.
