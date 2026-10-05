"""Access to the games' Unity serialized files."""
from __future__ import annotations

import os
import struct
from typing import Iterator

import UnityPy

from . import typetree
from .games import Game

#: Where everything that matters lives: the balance and the `lng_*`.
RESOURCES = "resources.assets"

# MonoBehaviour header: m_GameObject(PPtr 12) + m_Enabled(1, aligned to 4)
# + m_Script(PPtr 12); `m_Name` is the first string right after it.
_NAME_OFFSET = 12 + 4 + 12


def load(game: Game, filename: str = RESOURCES):
    path = os.path.join(game.env_data_dir(), filename)
    if not os.path.isfile(path):
        raise SystemExit(f"File not found: {path}")
    return UnityPy.load(path)


def raw_name(raw: bytes) -> str | None:
    """Reads `m_Name` straight from the bytes, without needing a TypeTree."""
    if len(raw) < _NAME_OFFSET + 4:
        return None
    size = struct.unpack_from("<i", raw, _NAME_OFFSET)[0]
    if not 0 < size < 256 or _NAME_OFFSET + 4 + size > len(raw):
        return None
    try:
        return raw[_NAME_OFFSET + 4 : _NAME_OFFSET + 4 + size].decode("utf8")
    except UnicodeDecodeError:
        return None


def monobehaviours(env, predicate=None) -> Iterator[tuple[str, object]]:
    """(name, object) of each MonoBehaviour whose name passes `predicate`.

    Always by NAME: `path_id` is not stable across builds.
    """
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        name = raw_name(obj.get_raw_data())
        if name is None:
            continue
        if predicate is None or predicate(name):
            yield name, obj


def read_sprites(game: Game, names: set[str], filename: str = RESOURCES) -> Iterator[tuple[str, object]]:
    """(name, PIL image) of each requested Sprite, one per name.

    Sprite is a native Unity type: its TypeTree ships in the file itself and
    `typetree.py`'s generator does not come in here. The filter by name happens
    BEFORE `.image`, which is the expensive part -- there are 21,030 sprites in
    resources.assets and the wiki uses a little over a thousand.

    A repeated name keeps its first occurrence; the caller compares what it
    asked for with what came out to know what is missing.
    """
    env = load(game, filename)
    seen = set()
    for obj in env.objects:
        if obj.type.name != "Sprite":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", "")
        if name not in names or name in seen:
            continue
        seen.add(name)
        yield name, data.image


def read_balance(game: Game) -> dict:
    """The whole balance ScriptableObject, as a dict."""
    env = load(game)
    for _, obj in monobehaviours(env, lambda n: n == game.balance_asset):
        return obj.read_typetree(typetree.tree(game, *game.balance_type))
    raise SystemExit(
        f"MonoBehaviour {game.balance_asset!r} not found in {RESOURCES} of {game.name}"
    )


def read_locales(game: Game) -> Iterator[dict]:
    """Each localization, normalized to {id, strings, aliases}."""
    env = load(game)
    f = game.locale_fields
    for _, obj in monobehaviours(env, lambda n: n.startswith("lng_")):
        d = obj.read_typetree(typetree.tree(game, *game.locale_type))
        yield {
            "id": d["id"],
            "strings": dict(zip(d[f["ids"]], d[f["txts"]])),
            "aliases": dict(zip(d[f["aliases1"]], d[f["aliases2"]])),
        }
