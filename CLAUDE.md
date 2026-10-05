# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Read `README.md` before touching anything.** It's the master document: what the game
is, the pipeline, the structure, the GK1 field reference and the findings.

## What this project is

Data extraction from the two **Graveyard Keeper** games (Unity + **Mono** backend). It's an
English fork of upstream `leticiatavares1/reveng-graveyard-keeper`, which is written in
Brazilian Portuguese and feeds the fan wiki `keeper-wiki-fnd`.

Two games, one pipeline:

- **`gk1`**: Graveyard Keeper, Unity 2020.3.17f1.
- **`gk2`**: demo of Graveyard Keeper 2, Unity 6000.3.9f1.

Every script takes the game as its first argument and writes to `out/<game>/`.

**Everything is in English**: docs, code, comments, identifiers, file names, commit
messages and the GK1 catalog. The exceptions are game data and GK2:

- `out/*/data/locales/` holds the game's 11 languages, as extracted.
- `out/gk2/` stays in upstream's Portuguese format. Don't translate it unless asked.

## Commands

```sh
./scripts/setup.sh                                      # creates .venv and installs UnityPy
./scripts/inventory.sh         gk1|gk2                  # build version and files
./scripts/decompile.sh         gk1|gk2                  # C# -> out/<game>/src-csharp/
./.venv/bin/python scripts/extract-balance.py gk1|gk2   # -> out/<game>/data/balance/
./.venv/bin/python scripts/extract-locales.py gk1|gk2   # -> out/<game>/data/locales/
python3 scripts/catalog.py                    gk1|gk2   # -> out/<game>/{data/wiki,catalog*}
./.venv/bin/python scripts/extract-sprites.py gk1       # -> out/gk1/icons/*.png
```

`GK1_DATA` / `GK2_DATA` point at the `*_Data` folder when the install isn't the default
Steam one. `catalog.py` needs neither the game nor the `.venv`: it only reads `out/`.

## Rules

- **The game folder is read-only.** No script writes to it, nor to `~/.steam`.
- **`out/*/data/balance/` is faithful to the binary.** Don't filter, rename or "clean" any
  field there: it's the baseline for `git diff` between game builds. Normalization and
  editorial choices happen later, in `catalog.py`, and land in `out/*/data/wiki/`.
- **Never look up an object by `path_id`.** It changes with every build. Use the name
  (`gk/assets.py:monobehaviours`).
- **Differences between the games live in `scripts/gk/games.py`.** Class, assembly, asset
  name, localization field names, catalog folder: everything that changes between `gk1` and
  `gk2` goes in the registry. If you're about to write `if game.id == "gk1"` outside
  `catalog_gk1.py`, the `Game` is probably missing a field.
- **A class in a namespace needs its full name** in the TypeTree generator
  (`LazyBearTechnology.LL`, not `LL`). Otherwise it fails with "Object reference not set".
- **GK1 names come only from the official English locale.** Never machine-translate game
  text, and never fill a name from another language. An item with no English string keeps
  `name: null` and is listed in `out/gk1/data/wiki/_missing_names.txt`.
- **Item names aren't shared between the games.** The same id can be a different item, or
  have a different official name, in GK1 and GK2. Never reuse one game's glossary in the
  other.
- **`on_use` only means "what the item gives back" when `can_be_used` is true.** On tools,
  the same `params_on_use` holds the energy cost per swing (`axe_1`: `energy: -1`).
  Publishing that as a gain would get both the sign and the meaning wrong.
- **Distrust fields that look obvious.** `Item.value` exists, is an int, and is wrong: a
  recipe's real quantity is `min_value`/`max_value` (SmartExpression). Before publishing a
  number, check it against the game's behavior or the fandom wiki. When they disagree,
  find the reason in the decompiled C# before deciding who's right.
- **Don't invent sprites either.** The icon name is what `ItemDefinition.GetIcon()` builds
  (`icon`, or `i_<id>` when empty). Four items in use have no sprite under that name, and
  they have none in the game either. Show the blank; don't substitute a look-alike. PNGs
  don't go into git.
- **A workstation icon isn't just `custom_icon`.** The real icon is the one from
  `WorldGameObject.GetUniversalObjectInfo()`:
  - for a craft object, it's the icon of the "Put" recipe that builds it, else
    `custom_icon`, else `"i_b_" + id`;
  - for a builder or building site, it's `custom_icon`, else `"i_z_" + id`.

  Outside Craft, the build menu icon (from the recipe that builds the object, any
  `build_type` except Remove) comes before the naming convention. Without it, Game of
  Crone's refugee camp had no art. Using only `custom_icon`, as the extraction once did,
  left the carpentry workbench, the most basic one in the game, with no icon at all. See
  `docs/04`.
- When touching `scripts/gk/typetree.py`, re-read `docs/03`. The two fixes there aren't
  cosmetic: without them the read blows up or, worse, returns plausible garbage.
- **Upstream merges:** take upstream's version of `out/*/data/balance/`,
  `out/*/data/locales/`, `out/*/src-csharp/` and `out/gk2/`. Port code and doc changes into
  the English files by hand. Regenerate the GK1 catalog with `python3 scripts/catalog.py
  gk1` instead of taking upstream's Portuguese output. See `README.md` §9.

## Commits

Use the project skill `.claude/skills/commit` for every commit: Conventional Commits
(Angular), in English. **Never list Claude as co-author or mention AI in the message** (no
`Co-Authored-By: Claude`, no "Generated with Claude Code").
