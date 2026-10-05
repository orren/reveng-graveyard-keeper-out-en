"""TypeTrees of the game's classes, generated from the Mono DLLs.

Neither game embeds a TypeTree in its serialized files
(`SerializedType.node is None`), so UnityPy alone does not know how to read a
MonoBehaviour. TypeTreeGeneratorAPI rebuilds the tree by reading
`Assembly-CSharp.dll` -- but it emits two details differently from what
UnityPy's reader expects. Both fixes are in `tree()` and are the key to the
whole pipeline; see docs/03-typetree-pipeline.md.
"""
from __future__ import annotations

import os

from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
from UnityPy.helpers.TypeTreeNode import TypeTreeNode

from .games import Game

ALIGN_FLAG = 0x4000

_gens: dict[str, TypeTreeGenerator] = {}
_cache: dict[tuple[str, str, str], TypeTreeNode] = {}


def managed_dir(game: Game) -> str:
    return os.path.join(game.env_data_dir(), "Managed")


def generator(game: Game) -> TypeTreeGenerator:
    gen = _gens.get(game.id)
    if gen is None:
        if not os.path.isdir(managed_dir(game)):
            raise SystemExit(
                f"Game folder not found: {game.env_data_dir()}\n"
                f"Point {game.id.upper()}_DATA at the `*_Data` folder of {game.name}."
            )
        gen = TypeTreeGenerator(os.environ.get("GK_UNITY_VERSION", game.unity))
        gen.load_local_dll_folder(managed_dir(game))
        _gens[game.id] = gen
    return gen


def tree(game: Game, assembly: str, cls: str) -> TypeTreeNode:
    """Type tree of `cls`, ready for `ObjectReader.read_typetree()`.

    `cls` needs the FULL name when the class is in a namespace (GK2's
    `LazyBearTechnology.LL`); with the short name the generator fails with
    "Object reference not set to an instance of an object".
    """
    key = (game.id, assembly, cls)
    if key in _cache:
        return _cache[key]

    nodes = [
        {
            "m_Level": n.m_Level,
            "m_Type": n.m_Type,
            "m_Name": n.m_Name,
            "m_MetaFlag": n.m_MetaFlag,
            "m_ByteSize": 0,
            "m_Version": 1,
        }
        for n in generator(game).get_nodes(assembly, cls)
    ]

    for i, node in enumerate(nodes):
        # (1) Unity aligns to 4 bytes after `m_Enabled`; the generator synthesizes
        #     the MonoBehaviour header without that flag and everything after it
        #     comes out shifted.
        if node["m_Level"] == 1 and node["m_Name"] == "m_Enabled":
            node["m_MetaFlag"] |= ALIGN_FLAG

        # (2) The generator names `List<T>`/`T[]` after the ELEMENT type, not
        #     "vector". UnityPy decides "is this a string?" by m_Type before
        #     looking at the children, so a `List<string>` was read as ONE giant
        #     string (EOFError). A real string has the subtree
        #     Array > (int size, char data); any other node with an Array child is
        #     a vector.
        has_array_child = (
            i + 3 < len(nodes)
            and nodes[i + 1]["m_Type"] == "Array"
            and nodes[i + 1]["m_Level"] == node["m_Level"] + 1
        )
        if has_array_child:
            is_real_string = node["m_Type"] == "string" and nodes[i + 3]["m_Type"] == "char"
            if not is_real_string:
                node["m_Type"] = "vector"

    root = TypeTreeNode.from_list(nodes)
    _cache[key] = root
    return root
