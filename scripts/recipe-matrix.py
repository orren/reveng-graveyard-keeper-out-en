#!/usr/bin/env python3
"""Builds the GK1 recipe matrix spreadsheet from the English catalog.

One row per (workstation, recipe) pair, one column per inventory item, and in
each cell the number of that item the recipe consumes at that workstation:

  out/gk1/recipe-matrix.xlsx
    "Matrix"  -- the grid; rows grouped by workstation, frozen headers, filters
    "Inputs"  -- the same data as a long list (station, recipe, item, qty),
                 for pivot tables
    "Notes"   -- what is in and out, and how to read it

Reads only `out/gk1/data/wiki/recipes.json` (run `catalog.py gk1` first).
Needs `openpyxl`.

    python3 scripts/recipe-matrix.py
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

WIKI = os.path.join("out", "gk1", "data", "wiki")
OUT = os.path.join("out", "gk1", "recipe-matrix.xlsx")

NO_STATION = "(no station)"
FONT = "Arial"
LEFT = ["Station", "Station ID", "Recipe ID", "Produces", "Source", "Hidden"]

BOLD = Font(name=FONT, bold=True)
PLAIN = Font(name=FONT)
GREY_TEXT = Font(name=FONT, color="808080", italic=True)
HEAD_FILL = PatternFill("solid", fgColor="D9E1F2")
STATION_FILL = PatternFill("solid", fgColor="FCE4D6")   # columns supplied by the station
BAND_FILL = PatternFill("solid", fgColor="F2F2F2")      # every other workstation block
THIN = Side(style="thin", color="BFBFBF")


def qty_txt(ref: dict) -> str:
    q = ref["qty_expr"] if ref.get("qty_expr") else f"{ref['qty']:g}"
    if ref.get("qty_max") is not None:
        q += f"–{ref['qty_max']:g}" if isinstance(ref["qty_max"], (int, float)) else f"–{ref['qty_max']}"
    return f"{q}x {ref['name'] or ref['id']}"


def produces(r: dict) -> str:
    parts = [qty_txt(o) for o in r["outputs"]]
    obj = r.get("built_object")
    if obj and r.get("build_type") != "Remove":
        parts.insert(0, f"builds {obj['name'] or obj['id']}")
    parts += [f"{v:g} {k} point" if isinstance(v, (int, float)) else f"{v} {k} point"
              for k, v in r["tech_points"].items()]
    return "; ".join(parts)


def pin_zip_times(path: str) -> None:
    """Rewrites the .xlsx (a zip) with fixed entry timestamps, so that
    regenerating unchanged data gives a byte-identical file and no git diff."""
    with zipfile.ZipFile(path) as zin:
        entries = [(i.filename, zin.read(i.filename)) for i in zin.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries:
            if name == "docProps/core.xml":
                # openpyxl stamps the save time here regardless of wb.properties.
                data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*", rb"\g<1>2026-01-01T00:00:00Z", data)
            zout.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data,
                          compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    with open(os.path.join(WIKI, "recipes.json"), encoding="utf8") as fh:
        recipes = json.load(fh)

    # Item columns: every item any recipe consumes, plus what stations supply.
    item_name: dict[str, str | None] = {}
    station_items: dict[str, str | None] = {}
    for r in recipes:
        for i in r["inputs"]:
            item_name.setdefault(i["id"], i["name"])
        for i in r["station_inputs"]:
            station_items.setdefault(i["id"], i["name"])

    def label(obj_id: str, name: str | None) -> str:
        return name or obj_id

    station_cols = sorted(station_items, key=lambda i: label(i, station_items[i]).casefold())
    item_cols = sorted(item_name, key=lambda i: (label(i, item_name[i]).casefold(), i))
    columns = [("station", i) for i in station_cols] + [("item", i) for i in item_cols]
    first_item_col = len(LEFT) + 1

    # Rows: one per (station, recipe); recipes that consume nothing are skipped.
    rows, skipped = [], 0
    for r in recipes:
        if not r["inputs"] and not r["station_inputs"]:
            skipped += 1
            continue
        for st in r["stations"] or [{"id": NO_STATION, "name": None}]:
            rows.append((label(st["id"], st["name"]), st["id"], r))
    rows.sort(key=lambda x: (x[0].casefold(), x[1], x[2]["id"]))

    wb = Workbook()
    # Fixed timestamps keep the file byte-stable between runs.
    wb.properties.created = wb.properties.modified = datetime.datetime(2026, 1, 1)
    # The "Used in N recipes" row is formulas saved without cached values; make
    # every spreadsheet app compute them on open.
    wb.calculation.fullCalcOnLoad = True
    ws = wb.active
    ws.title = "Matrix"

    last_row = 3 + len(rows)
    # Row 1: how many recipes use each item; row 2: item name; row 3: item id.
    ws.cell(1, len(LEFT), "Used in N recipes →").font = BOLD
    ws.cell(2, len(LEFT), "Item →").font = BOLD
    for c, h in enumerate(LEFT, 1):
        cell = ws.cell(3, c, h)
        cell.font, cell.fill = BOLD, HEAD_FILL
    for k, (kind, item_id) in enumerate(columns):
        c = first_item_col + k
        col = get_column_letter(c)
        name = (station_items if kind == "station" else item_name)[item_id]
        title = label(item_id, name) + (" (from station)" if kind == "station" else "")
        fill = STATION_FILL if kind == "station" else HEAD_FILL
        n = ws.cell(1, c, f"=COUNT({col}4:{col}{last_row})")
        n.font, n.alignment = PLAIN, Alignment(horizontal="center")
        t = ws.cell(2, c, title)
        t.font = BOLD if name else GREY_TEXT
        t.fill = fill
        t.alignment = Alignment(text_rotation=90, vertical="bottom", horizontal="center")
        i = ws.cell(3, c, item_id)
        i.font, i.fill = Font(name=FONT, size=8, color="595959"), fill
        i.alignment = Alignment(text_rotation=90, vertical="bottom", horizontal="center")
        ws.column_dimensions[col].width = 4.5

    col_of = {key: first_item_col + k for k, key in enumerate(columns)}
    band, prev_station = False, None
    for n, (station, station_id, r) in enumerate(rows, 4):
        if station_id != prev_station:
            band, prev_station = not band, station_id
        values = [station, station_id, r["id"], produces(r), r["source"],
                  "yes" if r["hidden"] else ""]
        for c, v in enumerate(values, 1):
            cell = ws.cell(n, c, v)
            cell.font = BOLD if c == 1 else PLAIN
            if band:
                cell.fill = BAND_FILL
        need: dict[tuple[str, str], float] = defaultdict(float)
        for i in r["inputs"]:
            need[("item", i["id"])] += i["qty"]
        for i in r["station_inputs"]:
            need[("station", i["id"])] += i["qty"]
        for key, q in need.items():
            cell = ws.cell(n, col_of[key], int(q) if float(q).is_integer() else q)
            cell.font, cell.alignment = PLAIN, Alignment(horizontal="center")
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    for col, width in zip("ABCDEF", (28, 24, 30, 40, 12, 7)):
        ws.column_dimensions[col].width = width
    ws.row_dimensions[2].height = 170
    ws.row_dimensions[3].height = 110
    ws.freeze_panes = ws.cell(4, first_item_col)
    ws.auto_filter.ref = f"A3:{get_column_letter(first_item_col + len(columns) - 1)}{last_row}"

    # Long format, one row per (station, recipe, item).
    lst = wb.create_sheet("Inputs")
    head = ["Station", "Station ID", "Recipe ID", "Item", "Item ID", "Qty", "Supplied by"]
    for c, h in enumerate(head, 1):
        cell = lst.cell(1, c, h)
        cell.font, cell.fill = BOLD, HEAD_FILL
    n = 2
    for station, station_id, r in rows:
        for src, refs in (("player", r["inputs"]), ("station", r["station_inputs"])):
            for i in refs:
                for c, v in enumerate([station, station_id, r["id"], label(i["id"], i["name"]),
                                       i["id"], i["qty"], src], 1):
                    lst.cell(n, c, v).font = PLAIN
                n += 1
    for col, width in zip("ABCDEFG", (28, 24, 30, 30, 26, 7, 12)):
        lst.column_dimensions[col].width = width
    lst.freeze_panes = "A2"
    lst.auto_filter.ref = f"A1:G{n - 1}"

    notes = wb.create_sheet("Notes")
    text = [
        ("Graveyard Keeper — recipe matrix", BOLD),
        ("", PLAIN),
        ("Source: out/gk1/data/wiki/recipes.json (Steam build 22583570), built by "
         "scripts/recipe-matrix.py. Names are the game's official English strings.", PLAIN),
        ("", PLAIN),
        ("How to read the Matrix sheet", BOLD),
        ("Each row is one recipe at one workstation. A recipe offered at several "
         "workstations appears once per workstation.", PLAIN),
        ("Each item column is an inventory item; the cell is how many of it the recipe "
         "consumes. Blank means none.", PLAIN),
        ("Row 1 counts the rows that use each item; row 3 holds the game id, which the "
         "filter dropdowns use.", PLAIN),
        ("Orange columns (Fire, Science) are taken from the workstation's own stock, "
         "not from the player's inventory.", PLAIN),
        ("Grey italic column titles are items with no English name in the game; the "
         "game id is shown instead.", PLAIN),
        ("", PLAIN),
        ("What is included", BOLD),
        (f"{len(rows)} rows from {len({s for _, s, _ in rows})} workstations, "
         f"{len(item_cols)} items plus {len(station_cols)} station-supplied inputs.", PLAIN),
        (f"{skipped} recipes that consume nothing were left out (mostly demolitions, "
         "which give materials back instead).", PLAIN),
        (f"'{NO_STATION}' holds recipes the game defines with no workstation: grave "
         "repairs and organ enhancements.", PLAIN),
        ("Hidden = yes marks recipes the game flags as hidden; filter them out with "
         "the Hidden column.", PLAIN),
        ("Some item ids are quality groups (e.g. pumpkin_crop accepts any quality "
         "level); see docs/04-bridge-to-the-wiki.md.", PLAIN),
        ("Quantities are the base amounts. Perks can change outputs and energy, not the "
         "inputs shown here.", PLAIN),
    ]
    for n, (t, f) in enumerate(text, 1):
        notes.cell(n, 1, t).font = f
    notes.column_dimensions["A"].width = 120

    wb.save(OUT)
    pin_zip_times(OUT)
    print(f"-> {OUT}: {len(rows)} rows × {len(columns)} item columns "
          f"({skipped} recipes with no inputs skipped)")


if __name__ == "__main__":
    if not os.path.isfile(os.path.join(WIKI, "recipes.json")):
        sys.exit("Run first: python3 scripts/catalog.py gk1")
    main()
