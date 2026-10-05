# reveng-graveyard-keeper (English fork)

Reverse engineering of the **Graveyard Keeper** games (Lazy Bear Games / tinyBuild, Unity).
The goal is to extract and catalog **every item, recipe and mechanic** straight from the
game binary.

This is an English fork of
[leticiatavares1/reveng-graveyard-keeper](https://github.com/leticiatavares1/reveng-graveyard-keeper),
which is written in Brazilian Portuguese and feeds `keeper-wiki-fnd`, a Portuguese-language
fan wiki. The fork differs from upstream in three ways:

- **Docs, scripts and history:** everything is translated to English. The docs were
  translated with an LLM; the Portuguese originals are upstream's.
- **GK1 catalog:** emitted in English: English keys, names from the game's official
  English localization only, English Markdown. Nothing is machine-translated, and an id
  with no English string gets `name: null` instead of an invented name.
- **GK2 (demo):** left exactly as upstream produces it. Its catalog under `out/gk2/`
  still uses upstream's Portuguese keys.

Two things stay as extracted, because they're game data and not prose:

- `out/<game>/data/balance/` uses the game's own C# field names, which are English.
- `out/<game>/data/locales/` holds all 11 of the game's languages, including `pt-br.json`.

| Game | Build | Engine | Definitions | Strings per language |
| ---- | ----- | ------ | ----------: | -------------------: |
| **GK1**: Graveyard Keeper | Steam `22583570` | Unity 2020.3.17f1 (Mono) | 6,116 | 10,961 × 11 |
| **GK2**: Graveyard Keeper 2 (**demo**) | Steam `25344626` | Unity 6000.3.9f1 (Mono) | 13,754 | 9,370 × 11 |

> ⚠️ Restricted use: this extracts data from **legally purchased and installed** games, for
> a non-profit fan wiki. Don't redistribute binaries, assets or the recovered source.

---

## 1. What can be extracted

Both games are **Unity with the Mono backend**, not IL2CPP. That changes everything. There
is a real `Assembly-CSharp.dll`, and it decompiles to readable C# with `ilspycmd`. Both
games also keep the whole game in a single ScriptableObject.

| Source | Where | What it gives |
| ------ | ----- | ------------- |
| **balance** (~4.3 MB in both) | `resources.assets` | **everything**: items, recipes, objects, technologies, quests |
| **`lng_*`** (11 languages each) | `resources.assets` | the official strings, English included |
| `Assembly-CSharp.dll` (+ `LazyBearTechnology.dll` in GK2) | `Managed/` | the rules: formulas, costs, logic |
| **sprites** (21,030 in GK1) | `resources.assets` | icons for items, workstations, construction objects and tech branches, plus the quality stars |
| scenes / Addressables | `level*` (GK1), `StreamingAssets/aa` (GK2, 876 MB) | map, NPCs, HUD (6 glyphs extracted by hand; the rest is **not extracted yet**) |
| `DialogData` (GK2) | `resources.assets` | dialogues (**not extracted yet**) |

Details of both builds are in [`docs/01-inventory.md`](docs/01-inventory.md).

---

## 2. Where the files come from

| Path | Content |
| ---- | ------- |
| `~/.local/share/Steam/steamapps/common/Graveyard Keeper/` | GK1 (Steam, native Linux) |
| `~/.local/share/Steam/steamapps/common/Graveyard Keeper 2 Demo/` | GK2 demo (Windows build, runs under Proton) |

The pipeline never writes to the game folder: extraction is **read-only**. To point at a
different install, export `GK1_DATA` or `GK2_DATA` with the path to the `*_Data` folder.

The extraction in `out/gk1/` was made from Steam build 22583570. If your install is on the
same build, you don't need to re-run steps 2–5 below: the committed data is what they would
produce.

---

## 3. Prerequisites

| Tool | Install | Used for |
| ---- | ------- | -------- |
| `python3` | already on the machine | the catalog (step 6) needs nothing else |
| `uv` | optional | faster `setup.sh` |
| `UnityPy` + `TypeTreeGeneratorAPI` | `./scripts/setup.sh` | reads the serialized files |
| `ilspycmd` | `dotnet tool install -g ilspycmd --version '8.*'` | decompiles the C# |
| `file`, `strings` | binutils/coreutils | inventory |

> **Gotcha:** `ilspycmd` 8.x targets .NET 6, and a machine with only the 8 and 10 runtimes
> needs `DOTNET_ROLL_FORWARD=LatestMajor`. `scripts/decompile.sh` already exports it.

---

## 4. The pipeline

Every script takes the game (`gk1` or `gk2`) as its first argument.

```sh
./scripts/setup.sh                                    # 1. once: creates .venv and installs the libs
./scripts/inventory.sh gk1                            # 2. version, assemblies, files
./scripts/decompile.sh gk1                            # 3. C# -> out/gk1/src-csharp/
./.venv/bin/python scripts/extract-balance.py gk1     # 4. balance -> out/gk1/data/balance/
./.venv/bin/python scripts/extract-locales.py gk1     # 5. lng_*   -> out/gk1/data/locales/
python3 scripts/catalog.py gk1                        # 6. joins everything -> out/gk1/{data/wiki,catalog}
./.venv/bin/python scripts/extract-sprites.py gk1     # 7. PNG icons -> out/gk1/icons/
```

Steps 4–7 take seconds and are idempotent. Step 3 takes about 15 s. Step 6 only reads
committed files, so it runs anywhere with plain `python3`.

Step 7 comes **after** step 6 on purpose. The catalog is what knows each sprite's name
(item, workstation, construction object, tech branch). The extractor only opens
`resources.assets` and saves what it was asked for. It also opens `sharedassets2.assets`
for the 6 HUD "days of the week" glyphs, which no balance field names. The PNGs stay out
of git because they are game assets, not extracted data.

### Steps 4 and 5: reading the serialized files

**The finding that makes the project work:** neither build embeds a TypeTree, so UnityPy
alone can't read any `MonoBehaviour`. The tree is rebuilt from `Assembly-CSharp.dll` by
`TypeTreeGeneratorAPI`. It still needs **two fixes** to match UnityPy's reader:

- alignment after `m_Enabled`;
- `List<T>` is emitted with the element type instead of `vector`.

Both fixes are in `scripts/gk/typetree.py` and are explained in
[`docs/03-typetree-pipeline.md`](docs/03-typetree-pipeline.md). They work the same on
Unity 2020 and Unity 6.

The output is **faithful to the binary**: nothing filtered, nothing renamed. It's the
baseline for diffing between versions. After each patch, re-run the extraction and
`git diff` shows exactly what changed in the balance, with no release notes needed.

### Step 6: catalog

Joins balance and localization, and produces two outputs:

- `out/<game>/data/wiki/*.json`, to become content;
- the Markdown tables, to read: `out/gk1/catalog/*.md` and `out/gk2/catalogo/*.md`.

The balance schema changed a lot between the two games, so each game has its own adapter
in `scripts/gk/catalog_<game>.py`.

---

## 5. GK1 catalog

| Path | Content |
| ---- | ------- |
| `out/gk1/data/wiki/items.json` | 1,157 items |
| `out/gk1/data/wiki/recipes.json` | 2,634 recipes (2,101 craft + 533 construction) |
| `out/gk1/data/wiki/technologies.json` | 187 technology tree nodes |
| `out/gk1/data/wiki/_missing_names.txt` | ids left with `name: null` |
| `out/gk1/catalog/{items,recipes,technologies}.md` | readable tables: items; recipes grouped by station; technologies in tree order |

**Names.** Every name and description comes from `out/gk1/data/locales/en.json`, looked
up the way the game does it. The lookup tries, in order:

1. the id;
2. the base id without the `:N` suffix;
3. the locale aliases, followed as a chain.

If none of those gives a string, the name is `null`. 24 items in use have no English name
anywhere. They're all sermon bonuses, such as `b_circle:1` and `b_techpoint_red:3`, and
the game has no name for them either. An empty description is `null`. Ids are the game's
own, unchanged, including technology ids like `Advanced alchemy`, whose display name is
"Advanced Alchemy".

### GK1 field reference

A field copied 1:1 from a game field keeps the game's C# name, even when its type is
coerced (int → bool, enum int → enum name). A field the catalog derives or reshapes gets a
descriptive name.

| File | Field | Meaning |
| ---- | ----- | ------- |
| items | `name`, `description` | official English strings |
| | `type` | `ItemDefinition.ItemType` |
| | `base_price`, `quality`, `stack_count`, `efficiency`, `has_durability`, `not_used`, `product_types`, `can_be_used` | game fields |
| | `icon`, `stars`, `group` | sprite name, quality star (1–3), quality group (see `docs/04`) |
| | `on_use`, `on_use_expr` | fixed effect on use, and its formula part (see the warning below) |
| recipes | `source` | `craft` (`craft_data`) or `construction` (`craft_obj_data`) |
| | `craft_type` | `CraftDefinition.CraftType` |
| | `stations` | `craft_in`, or `builder_ids` for construction |
| | `inputs`, `outputs` | `needs`, `output` (tech points moved out) |
| | `station_inputs` | `needs_from_wgo`: taken from the station's own inventory (`fire` fuel, `science`), not from the player |
| | `tech_points` | tech points the craft awards |
| | `craft_time`, `energy`, `sanity`, `difficulty` | seconds / player energy / player sanity (always 0 or null in GK1); a number or a formula |
| | `hidden`, `needs_unlock`, `linked_perks` | game fields |
| | `unlocked_by` | technology ids |
| | `built_object`, `build_type` | construction only; `Put` / `Remove` / `None` |
| refs | `id`, `name`, `qty`, `qty_expr`, `qty_max`, `icon` | inside `stations`, `inputs`, `outputs`, `built_object` |
| technologies | `name` | official English string |
| | `branch` `{n, name, icon}` | `name` from `en.json` `tbranch_<n>` |
| | `cost` | tech points |
| | `requires` | technology ids (`[""]` means none, as in the game) |
| | `crafts`, `perks`, `hidden` | what the node unlocks; `hidden` is `hidden` or `invisible` |
| | `requires_dlc`, `dlc` | `DLCEngine.DLCVersion`: `none`, `breaking_dead`, `stranger_sins`, `game_of_crone`, `better_save_soul` |

Point keys are spelled out wherever they appear (`cost`, `tech_points`, `on_use`): `red`,
`green`, `blue`, `purple`, `gratitude`.

> **Read `on_use` together with `can_be_used`.** `on_use` means "what the item gives
> back" only when `can_be_used` is true. On tools, the same game field holds the energy
> cost per swing: `axe_1` has `{"energy": -1.0}`.

> **Quantities.** Many numbers are formulas. When the amount depends on a perk, `qty` is
> `null` and `qty_expr` holds the raw expression, for example
> `3+Ppar("p_woodworker")`. The catalogs print that expression as-is.

---

## 6. The data model in one sentence

**The whole game is one ScriptableObject.** `Resources.Load<GameBalance>(...)` returns
33–34 definition lists linked by string `id`. The visible names live separately in the
`lng_*` assets and join on the same `id`. Tracing a mechanic means following
`id → definition → expression → the C# class that evaluates it`.

GK2 is the same design, rewritten:

- the classes became `*Def`;
- the fields moved to camelCase;
- `SmartExpression` became `LazyExpression`.

Classes, fields and pitfalls for both games are in
[`docs/02-data-model.md`](docs/02-data-model.md).

---

## 7. Project structure

```
reveng-graveyard-keeper/
├── README.md                     # this file
├── scripts/
│   ├── setup.sh                  # creates the .venv
│   ├── inventory.sh <game>       # build version, assemblies, serialized files
│   ├── decompile.sh <game>       # ilspycmd -> out/<game>/src-csharp/
│   ├── extract-balance.py <game> # balance -> one list per file
│   ├── extract-locales.py <game> # lng_* -> id → text
│   ├── catalog.py <game>         # joins everything; normalizes quantities and names
│   ├── extract-sprites.py gk1    # item/workstation/object/tech icons + HUD -> out/gk1/icons/
│   └── gk/
│       ├── games.py              # ← game registry: everything that differs lives here
│       ├── typetree.py           # ← TypeTree from the DLL + the 2 fixes
│       ├── assets.py             # find a MonoBehaviour by NAME (path_id isn't stable)
│       ├── catalog_common.py     # locale loading, Names, output writing
│       └── catalog_gk1.py · catalog_gk2.py   # one adapter per game
├── docs/
│   ├── 01-inventory.md           # what each build is and what's inside
│   ├── 02-data-model.md          # GameBalance, the lists, expressions, pitfalls
│   ├── 03-typetree-pipeline.md   # why it couldn't be read and how it became readable
│   └── 04-bridge-to-the-wiki.md  # how this becomes wiki content
└── out/
    ├── gk1/{src-csharp,data/{balance,locales,wiki},catalog}
    └── gk2/{src-csharp,data/{balance,locales,wiki},catalogo}
```

**The `.gitignore` rule:** version what was written by hand **and the extraction output**.
The output is the day-to-day knowledge base and the baseline for comparing builds. Only
binaries and heavy, regenerable files stay out.

---

## 8. Findings

| Finding | Where | In one line |
| ------- | ----- | ----------- |
| **No build has a TypeTree** | `docs/03` | Without a TypeTree, a `MonoBehaviour` is raw bytes. The tree comes from `Assembly-CSharp.dll`, with two fixes UnityPy requires. This unlocks everything, and it works the same on Unity 2020 and Unity 6. |
| **A class in a namespace needs its full name** | `docs/03` | `LL` fails with "Object reference not set to an instance of an object"; `LazyBearTechnology.LL` works. |
| **`Item.value` is a dead field (GK1)** | `docs/02` | The real quantity is in `min_value`/`max_value`. `flitch_2` has `value=1` but produces **7** flitches. The fandom wiki was right and the first catalog was wrong. |
| **The game has official pt-BR, and upstream's wiki didn't use it** | `docs/04` | **12 of the 25** hand-written recipes on `keeper-wiki-fnd` used a name different from the official one. |
| **GK1 and GK2 translate the same item differently** | `docs/04` | Of the 90 item ids that exist in both, **37 have a different pt-BR name**. A glossary shared between the games would be wrong. |
| **Almost every number is a formula** | `docs/02` | For example, `energy = 10-Ppar("p_woodworker")*5`. A fixed number is the exception, and perks feed straight into cost and yield. |
| **The GK2 demo ships the entire balance** | `docs/01` | It has 13,754 definitions, more than twice GK1. But **185 of the 236 technologies** are marked `isAvailableInDemo = false`. The data is from the full game in development and may change. |

---

## 9. Keeping up with upstream

Upstream is added as the `upstream` remote:

```sh
git remote add upstream https://github.com/leticiatavares1/reveng-graveyard-keeper
git fetch upstream
git merge upstream/main
```

The fork renamed and rewrote upstream's files, so expect conflicts. Resolve them as follows:

- **`out/*/data/balance/`, `out/*/data/locales/`, `out/*/src-csharp/`, `out/gk2/`:**
  take upstream's version. These are game data and GK2 output.
- **Docs and scripts:** port upstream's change into the English files. For example, a fix
  in upstream's `catalogo_gk1.py` goes into `catalog_gk1.py`.
- **GK1 catalog:** never take upstream's Portuguese `out/gk1/data/wiki/` or
  `out/gk1/catalogo/`. Regenerate it with `python3 scripts/catalog.py gk1`.

`git status` after regenerating shows exactly what upstream's change did to the English
catalog.
