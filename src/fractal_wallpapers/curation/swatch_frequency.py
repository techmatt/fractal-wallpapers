"""The frequency sheet: every swatch, what it looks like, and how often the pool is it.

The census answers *which colours are missing* in four tables that each read
correctly and none of which fit on a page. This module is the one page: fifty-two
rows, one per swatch, ordered by how often that swatch is the **dominant** colour
of a judged candidate render, most common first, so the falloff reads top to
bottom and a cliff is visible as a cliff.

It is written for somebody who is about to author a colormap. That is why the
sheet carries what it carries:

* the colour in four notations, all of them read off [`palettes.codebook`] rather
  than recomputed here — a sheet that disagreed with the instrument that made the
  counts would be worse than no sheet;
* `gamut_limited`, which separates *nobody made a map for this* from *sRGB barely
  holds this at all*. A colour the gamut will not hold is not a gap a new map can
  close, and it would otherwise read as the deepest hole in the table;
* **library carriage** — how many maps carry the swatch at 10% of their ramp — so
  the answer to "is there an existing map to adjust" is on the same row as the
  gap. Counted twice, over the whole library and over the pool a colorize may
  actually draw from, because a map outside the pool cannot be picked however
  well it carries the colour.

## Two files, because a csv cannot hold a colour

The table is a **csv**: the thing to sort, filter and paste. But a name and three
coordinates do not tell an eye what colour is missing, so the same rows are also
written as one html strip with each swatch's own colour filled in behind its
name. Same numbers, same order, no second computation — the strip is the csv with
the chips the csv has nowhere to put.

## No new arithmetic, and that is the point

Every number here is lifted from the census artifact: the counts are stage 3's
score-free `dominant` tally, the carriage is stage 1's `at_10pct` cell, and the
colours are the codebook document the census wrote beside them. This module
joins, orders and formats. It cannot report a frequency the census does not,
which is what makes the sheet checkable against the readout.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path

from fractal_wallpapers.palettes import codebook

#: The share of a map's ramp a swatch must hold to count as *carried* by it. The
#: census's own lower pre-registered threshold — see [`codebook.SHARE_THRESHOLDS`]
#: — rather than a number this module chose, so the column means what stage 1's
#: table means.
CARRIAGE_THRESHOLD = 0.10

#: The columns, in order. The header row of the csv and the order of every row
#: built here; the html strip reads the same fields under the same names.
COLUMNS: tuple[str, ...] = (
    "rank",
    "swatch",
    "hex",
    "srgb_r",
    "srgb_g",
    "srgb_b",
    "oklab_l",
    "oklab_a",
    "oklab_b",
    "oklch_l",
    "oklch_c",
    "oklch_h",
    "gamut_limited",
    "dominant_renders",
    "share_of_pool",
    "maps_at_10pct",
    "pool_maps_at_10pct",
)


class SheetError(RuntimeError):
    """The sheet cannot be built from the census as it stands."""


def _hex(srgb) -> str:
    """The swatch's sRGB8 as `#rrggbb`, off the codebook's own channel values."""
    red, green, blue = (int(channel) for channel in srgb)
    return f"#{red:02x}{green:02x}{blue:02x}"


def rows(readout: dict) -> list[dict]:
    """One row per swatch, joined and ordered, from a census readout.

    Ordered by dominant count descending, ties broken by the **codebook's own
    order** rather than alphabetically: the tail is mostly zeroes, and codebook
    order keeps a hue's four cells together where an alphabet would scatter them.
    """
    stages = readout.get("stages") or {}
    for needed in ("library", "survival"):
        if needed not in stages:
            raise SheetError(
                f"the census readout carries no {needed} stage, and the sheet joins both. "
                f"Run `fractal-wallpapers curate colors` for all four stages first."
            )
    pool = stages["survival"].get("pool") or {}
    tally = pool.get("dominant") or {}
    total = int(pool.get("renders") or 0)
    carriage = (stages["library"].get("metrics") or {}).get("swatches") or {}
    pool_carriage = (stages["library"].get("pool_metrics") or {}).get("swatches") or {}
    at = f"at_{int(CARRIAGE_THRESHOLD * 100)}pct"

    # The codebook the CENSUS wrote, not whatever this module imports today: the
    # counts were taken under that one, and a sheet that mixed the two would put
    # today's coordinates beside yesterday's frequencies.
    described = (readout.get("codebook") or {}).get("swatches") or [
        dict(entry) for entry in codebook.swatches()
    ]

    built = []
    for order, entry in enumerate(described):
        name = entry["swatch"]
        count = int(tally.get(name, 0))
        lightness, chroma, hue = entry["oklch"]
        built.append(
            {
                "swatch": name,
                "hex": _hex(entry["srgb"]),
                "srgb_r": int(entry["srgb"][0]),
                "srgb_g": int(entry["srgb"][1]),
                "srgb_b": int(entry["srgb"][2]),
                "oklab_l": round(float(entry["lab"][0]), 4),
                "oklab_a": round(float(entry["lab"][1]), 4),
                "oklab_b": round(float(entry["lab"][2]), 4),
                "oklch_l": round(float(lightness), 4),
                "oklch_c": round(float(chroma), 4),
                "oklch_h": None if hue is None else round(float(hue), 1),
                "gamut_limited": "yes" if entry.get("gamut_limited") else "",
                "dominant_renders": count,
                "share_of_pool": round(count / total, 6) if total else 0.0,
                "maps_at_10pct": int((carriage.get(name) or {}).get(at, 0)),
                "pool_maps_at_10pct": int((pool_carriage.get(name) or {}).get(at, 0)),
                "order": order,
            }
        )
    ordered = sorted(built, key=lambda row: (-row["dominant_renders"], row["order"]))
    for rank, row in enumerate(ordered, start=1):
        row["rank"] = rank
    return ordered


def write_csv(table: list[dict], path: Path) -> Path:
    """The table as a csv. `newline=""` for the writer, `\\n` for the file itself."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(COLUMNS), extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(table)
    return path


_STYLE = """
body { background:#12141a; color:#e8e8ea; font:13px/1.5 system-ui, sans-serif; margin:24px; }
h1 { font-size:20px; margin:0 0 4px; }
p.note { color:#9aa0aa; max-width:64em; }
table { border-collapse:collapse; margin-top:16px; }
th, td { padding:4px 10px; text-align:right; border-bottom:1px solid #23262e; white-space:nowrap; }
th { text-align:right; color:#9aa0aa; font-weight:600; position:sticky; top:0; background:#12141a; }
th.name, td.name { text-align:left; }
td.chip { padding:0; }
td.chip div { width:56px; height:20px; border:1px solid #444; border-radius:3px; }
tr.zero td { color:#c98b8b; }
td.dim { color:#6f7681; }
"""


def _page(table: list[dict], renders: int, taken_at: str | None) -> str:
    head = "".join(
        f"<th class='name'>{html.escape(name)}</th>"
        if name == "swatch"
        else f"<th>{html.escape(name)}</th>"
        for name in (
            "swatch",
            "colour",
            "hex",
            "oklch L",
            "oklch C",
            "oklch h",
            "gamut limited",
            "dominant",
            "share",
            "maps 10%",
            "pool maps 10%",
        )
    )
    lines = []
    for row in table:
        hue = "" if row["oklch_h"] is None else f"{row['oklch_h']:.1f}"
        share = f"{row['share_of_pool']:.2%}"
        lines.append(
            f'<tr class="{"zero" if row["dominant_renders"] == 0 else ""}">'
            f"<td class='name'>{row['rank']}. {html.escape(row['swatch'])}</td>"
            f"<td class='chip'><div style='background:{row['hex']}'></div></td>"
            f"<td class='dim'>{row['hex']}</td>"
            f"<td class='dim'>{row['oklch_l']:.2f}</td>"
            f"<td class='dim'>{row['oklch_c']:.3f}</td>"
            f"<td class='dim'>{hue}</td>"
            f"<td>{html.escape(row['gamut_limited'])}</td>"
            f"<td>{row['dominant_renders']}</td>"
            f"<td>{share}</td>"
            f"<td>{row['maps_at_10pct']}</td>"
            f"<td>{row['pool_maps_at_10pct']}</td>"
            "</tr>"
        )
    return (
        "<!doctype html><meta charset='utf-8'><title>Swatch frequency</title>"
        f"<style>{_STYLE}</style>"
        "<h1>Swatch frequency over the judged pool</h1>"
        f"<p class='note'>All 52 swatches, ordered by how often each is the <strong>dominant"
        f"</strong> colour of one of the {renders:,} judged candidate renders. Carriage is how "
        f"many colormaps hold the swatch over {CARRIAGE_THRESHOLD:.0%} of their ramp — the "
        f"census's own lower threshold — over the whole library and over the pool a colorize "
        f"draws from. <code>gamut limited</code> means sRGB would not hold the swatch's target "
        f"chroma at its lightness, so its absence is the gamut rather than the library. Census "
        f"taken {html.escape(str(taken_at))}.</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(lines)}</tbody></table>"
    )


def write_page(table: list[dict], path: Path, renders: int, taken_at: str | None) -> Path:
    """The same rows with each swatch's colour filled in, which a csv has nowhere to put."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_page(table, renders, taken_at), encoding="utf-8", newline="\n")
    return path


def write(readout: dict, directory: Path) -> dict:
    """Both files into `directory`. Returns what they hold, for the caller to print."""
    directory = Path(directory)
    table = rows(readout)
    renders = int((readout["stages"]["survival"].get("pool") or {}).get("renders") or 0)
    sheet = write_csv(table, directory / "swatch_frequency.csv")
    page = write_page(table, directory / "swatch_frequency.html", renders, readout.get("taken_at"))
    return {
        "csv": str(sheet),
        "page": str(page),
        "swatches": len(table),
        "renders": renders,
        "zero_dominance": [row["swatch"] for row in table if row["dominant_renders"] == 0],
        "uncarried": [row["swatch"] for row in table if row["maps_at_10pct"] == 0],
        "top": [(row["swatch"], row["dominant_renders"]) for row in table[:5]],
    }


__all__ = [
    "CARRIAGE_THRESHOLD",
    "COLUMNS",
    "SheetError",
    "rows",
    "write",
    "write_csv",
    "write_page",
]
