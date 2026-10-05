"""Registry of the supported games.

The two Graveyard Keeper games share an architecture -- Unity/Mono, the whole
balance in a single ScriptableObject, localization in sibling ScriptableObjects
-- but almost every name differs: the class, the assembly, the asset name and
the localization fields. Everything that differs lives here; the rest of the
pipeline is the same for both.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

STEAM = os.path.expanduser("~/.local/share/Steam/steamapps/common")


@dataclass(frozen=True)
class Game:
    id: str
    name: str
    steam_appid: int
    #: The install's `*_Data` folder.
    data_dir: str
    #: Unity version of the build (`inventory.sh` prints the one on disk).
    unity: str
    #: The studio's own assemblies, which `decompile.sh` processes.
    assemblies: tuple[str, ...]
    #: Name of the balance MonoBehaviour inside resources.assets.
    balance_asset: str
    #: (assembly, class) of the balance.
    balance_type: tuple[str, str]
    #: (assembly, class) of the localization.
    locale_type: tuple[str, str]
    #: Serialized field names of the localization, which changed between games.
    locale_fields: dict[str, str]
    #: Folder under `out/<game>/` for the readable Markdown catalogs.
    catalog_dir: str
    #: Suffix of the description key in the locale (`<id>_d` in both games).
    desc_suffix: str = "_d"
    #: Notice added to the output when the build is not the full game.
    notice: str = ""

    @property
    def out(self) -> str:
        return os.path.join("out", self.id)

    def env_data_dir(self) -> str:
        """Lets you point at another install with GK1_DATA / GK2_DATA / GK_DATA."""
        return (os.environ.get(f"{self.id.upper()}_DATA")
                or os.environ.get("GK_DATA")
                or self.data_dir)


GK1 = Game(
    id="gk1",
    name="Graveyard Keeper",
    steam_appid=599140,
    data_dir=f"{STEAM}/Graveyard Keeper/Graveyard Keeper_Data",
    unity="2020.3.17f1",
    assemblies=("Assembly-CSharp", "Assembly-CSharp-firstpass"),
    balance_asset="game_data",
    balance_type=("Assembly-CSharp.dll", "GameBalance"),
    locale_type=("Assembly-CSharp-firstpass.dll", "GJL"),
    locale_fields={"ids": "txt_ids", "txts": "txts",
                   "aliases1": "aliases_1", "aliases2": "aliases_2"},
    catalog_dir="catalog",
)

GK2 = Game(
    id="gk2",
    name="Graveyard Keeper 2 (demo)",
    steam_appid=5075680,
    data_dir=f"{STEAM}/Graveyard Keeper 2 Demo/GraveyardKeeper2Demo_Data",
    unity="6000.3.9f1",
    assemblies=("Assembly-CSharp", "Assembly-CSharp-firstpass", "LazyBearTechnology"),
    balance_asset="GameBalance",
    balance_type=("Assembly-CSharp.dll", "GameBalance"),
    # The localization class lives in a namespace: without the full name the
    # generator returns "Object reference not set to an instance of an object".
    locale_type=("LazyBearTechnology.dll", "LazyBearTechnology.LL"),
    locale_fields={"ids": "txtIds", "txts": "txts",
                   "aliases1": "aliases1", "aliases2": "aliases2"},
    # GK2's catalog is still upstream's Portuguese output, left as is.
    catalog_dir="catalogo",
    # Written verbatim into GK2's (Portuguese) Markdown catalogs. In English:
    # "DEMO build: the balance ships complete in the file, but part of the
    # content is marked unavailable in the demo (see isAvailableInDemo in
    # techDefs) and may change in the final game."
    notice=("Build de DEMO: o balanceamento vem completo no arquivo, mas parte do "
            "conteudo esta marcada como indisponivel na demo (ver isAvailableInDemo "
            "em techDefs) e pode mudar no jogo final."),
)

GAMES = {g.id: g for g in (GK1, GK2)}


def get(game_id: str) -> Game:
    try:
        return GAMES[game_id]
    except KeyError:
        raise SystemExit(f"Unknown game: {game_id!r}. Use one of: {', '.join(GAMES)}")
