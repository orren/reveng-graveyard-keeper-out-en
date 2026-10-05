# 3. The read pipeline: TypeTree

This is the technical finding the project exists because of. Without it, `game_data` is
a shapeless 4.3 MB blob of bytes.

## The problem

A Unity serialized file normally carries the **TypeTree** of each type. That's the list
of fields, in order, with type and alignment rule, and it's what lets an external tool
read a `MonoBehaviour` without knowing the game's code.

Neither build **ships a TypeTree** (GK1 on Unity 2020.3, GK2 on Unity 6000.3):

```python
>>> obj.serialized_type
SerializedType(class_id=114, ..., node=None, m_ClassName=None)
```

`node=None`. UnityPy can list the objects, read their names and return the raw bytes, and
nothing more. `obj.read()` doesn't know what it's looking at.

## The solution

`TypeTreeGeneratorAPI` rebuilds the tree **from `Assembly-CSharp.dll`**. It reads the
class's fields and applies Unity's serialization rules. Because the game is Mono, the DLL
has the real types, and the tree comes out complete (3,805 nodes for `GameBalance` alone).

```python
gen = TypeTreeGenerator("2020.3.17f1")
gen.load_local_dll_folder(".../Managed")
nodes = gen.get_nodes("Assembly-CSharp.dll", "GameBalance")
```

## The two fixes (without them, nothing reads)

The generator and UnityPy's reader disagree on two points. Both fixes are in
`scripts/gk/typetree.py`, and both were found through an `EOFError`.

### 1. Alignment after `m_Enabled`

The generator synthesizes the `MonoBehaviour` header (`m_GameObject`, `m_Enabled`,
`m_Script`, `m_Name`) but emits `m_Enabled` with `m_MetaFlag = 0`. Unity writes that
`UInt8` and then **aligns to 4 bytes**. Without the flag, everything after it is shifted
by 3 bytes.

```python
if node["m_Level"] == 1 and node["m_Name"] == "m_Enabled":
    node["m_MetaFlag"] |= 0x4000        # align
```

### 2. `List<T>` is named after the **element** type

Unity emits a `List<string>` as a node of type `vector`. The generator emits it as
`string`, with the vector subtree hanging below. UnityPy's reader checks `m_Type`
**before** looking at the children:

```
string txt_ids          <- the generator says "string"
  Array Array
    int size            <- 10961
    string data         <- the strings
```

As a result, the reader took the 4 bytes of `size` as the length of **one** string and
tried to consume 10,961 bytes of text at once. That's the
`EOFError: read_str out of bounds`.

The rule that tells the two cases apart: a real string has the subtree
`Array > (int size, char data)`. Any other node with an `Array` child is a vector.

```python
is_real_string = node["m_Type"] == "string" and nodes[i + 3]["m_Type"] == "char"
if not is_real_string:
    node["m_Type"] = "vector"
```

## Validation

Not crashing isn't enough, because a misalignment can produce plausible garbage. The read
was checked in two ways. First, by **manually parsing the bytes** (`gk/assets.py:raw_name`
uses the same arithmetic). Second, against data that only lines up if everything is right:

- `lng_pt-br`: 10,961 ids and 10,961 strings, paired, ending exactly at the end of the
  blob;
- `bloody_nails_wash`: 1 bloody nail + 1 river sand + 1 water → 1 nail, 2 energy, at the
  cooking table, which is what the game does;
- `flitch` at the sawhorse: 1 log → 6 flitches, +1 red point.

GK2 passed the same check. `lng_pt-br` closes at 9,370 pairs. `wooden_plank` comes out as
1 `flitch` → 1 wooden plank at the Carpentry Workbench, in 4 s, for 2 energy per tick and
+2 red. The `work_with_wood_1` technology unlocks it.

## The third gotcha: namespaces

The generator wants the class's **full name**. GK2's localization lives in
`namespace LazyBearTechnology`. Asking for the class by its short name fails with a
message that says nothing about the cause:

```
>>> gen.get_nodes("LazyBearTechnology.dll", "LL")
Error generating tree nodes:
Object reference not set to an instance of an object.
AssertionError: failed to dump nodes raw
>>> gen.get_nodes("LazyBearTechnology.dll", "LazyBearTechnology.LL")   # works
```

A class in the global namespace (like `GameBalance`, in both games) works by its short
name. That's why `games.py` stores the `(assembly, class)` pair with the full name already
in place.

## It holds for Unity 2020 and Unity 6

Both fixes were found on GK1 (Unity 2020.3.17f1). They apply unchanged to GK2 (Unity
6000.3.9f1), because neither the serialized format nor the generator's output changed on
these points. The version passed to the generator still matters, since it changes
alignment rules. Use the one `globalgamemanagers` reports: that's what `games.py` stores
and what `inventory.sh` prints.

## Gotchas for next time

- **`path_id` isn't stable across builds.** Look objects up by name (`game_data`,
  `lng_*`).
- **`ilspycmd` 8.x targets .NET 6**, and the machine only has 8 and 10. You need
  `DOTNET_ROLL_FORWARD=LatestMajor`. `scripts/decompile.sh` already exports it.
- **The Unity version passed to the generator matters.** It changes alignment rules. Use
  the one `globalgamemanagers` reports (`scripts/inventory.sh` prints it).
- **A class in a namespace needs its full name** (see above).
- **Addressables don't get in the way.** GK2 ships 876 MB of bundles, but the balance is
  still in `resources.assets`. Not a single bundle had to be opened.
