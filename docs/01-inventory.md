# 1. Build inventory

Regenerate with `./scripts/inventory.sh gk1` / `gk2`.

## The two games side by side

| | **GK1** | **GK2 (demo)** |
| --- | --- | --- |
| Steam appid / buildid | 599140 / 22583570 | 5075680 / 25344626 |
| Engine | Unity **2020.3.17f1** | Unity **6000.3.9f1** |
| Scripting backend | **Mono** | **Mono** |
| Build analyzed | native Linux | Windows (runs under Proton) |
| Studio assembly | `Assembly-CSharp.dll` (2,587 KiB) | `Assembly-CSharp.dll` (3,813 KiB) + `LazyBearTechnology.dll` (505 KiB) |
| Recovered `.cs` files | 3,110 | 2,744 |
| Where the balance lives | `resources.assets` → `game_data` | `resources.assets` → `GameBalance` |
| Asset distribution | `level0`…`level27` | **Addressables**: 24,062 bundles, 876 MB |

Both are Mono, and that shapes the whole project. There is a real `Assembly-CSharp.dll`,
and `ilspycmd` turns it back into near-original C#. It's the same decompiler, with the
same runtime gotcha, as in `metrics-reveng`. With IL2CPP the path would have been Ghidra.

## GK1: serialized files

| File | Size | Contains |
| ---- | ---: | -------- |
| `resources.assets` | 93.8 MB | **everything that matters**: `game_data`, the 11 `lng_*`, sprites |
| `level0` … `level27` | 5 KB – 70 MB | scenes (map, placed objects, NPCs) |
| `globalgamemanagers` | 9.6 MB | player settings; this is where the Unity version comes from |

53,728 MonoBehaviours, 43,988 GameObjects, 21,030 Sprites.

## GK2: serialized files

| File | Size | Contains |
| ---- | ---: | -------- |
| `resources.assets` | 59.1 MB | `GameBalance`, the 11 `lng_*`, `DialogData`, fonts |
| `sharedassets0.resource` | 276 MB | audio |
| `StreamingAssets/aa/` | 876 MB | **Addressables**: art and scenes, 24,062 bundles |

There are only 841 MonoBehaviours in `resources.assets`, far fewer than GK1, because almost
everything moved to the bundles. **The balance didn't move.** It's still in
`resources.assets`, loaded by `Resources.Load<GameBalance>("GameBalance")`, so extracting
game data doesn't require opening any bundle.

### Present in GK2, absent in GK1

- **`StreamingAssets/ModdingTools/VoiceOvers/`**: Lazy Bear shipped official support for
  voice mods. It includes a `voiceover_lines.json` with every voiceable line in all 11
  languages, and a README that explains the format. That's game data handed over for free,
  in plain text.
- **`DialogData`** (0.31 MB in `resources.assets`) holds the dialogues, loaded via
  `Resources.Load<DialogDataContainer>("Locales/DialogData")`.
- **`lng_tr`**: Turkish joined the language list. GK1 has 11 languages without Turkish;
  GK2 has 11 with it.

## Not extracted yet

- **Sprites/icons**: UnityPy can export them; what's missing is deciding what the wiki
  may use.
- **Scenes** (GK1 `level*`) and **Addressables** (GK2): NPC positions, zones, spawns.
- **GK2 dialogues** (`DialogData` + `voiceover_lines.json`).
