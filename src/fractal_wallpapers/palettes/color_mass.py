"""What colour a (palette group, mode) pair actually puts on a picture.

A ramp screen answers *can this map make green*, and the answer is nearly always
yes: at `dominance.FAMILY_LEAD` the bound removes **zero** of the 822 pool groups,
because the median group can lead 5.5 of the 12 hue families. What a colour rule
needs is the other question — *how much green does this pair actually deliver* —
and that is a measurement, not a bound. A ramp that can lead a family delivers it
23–33% of the time.

This module is the tracked answer, keyed on **(palette group, mode)** and nothing
finer. That key was chosen off a variance decomposition rather than by taste: over
784 pairs with n>=5 on >=3 partitions, the pair term carries **75.0%** of the
variation in the 48-cell vector, the partition within a pair 8.0%, and the
location-and-render residual 17.1%. Adding the fractal family to the key buys back
at most eight points; most of what is left is location-to-location inside a
partition, which no key coarser than the location can reach.

## Where the numbers come from

Two measurements, unioned, and neither alone is the map:

```text
census   15,681 judged pool rows, read where the palette head actually went.
         Production locations, production framing, but the coverage is the
         HEAD'S TASTE: 9,721 of 14,796 pairs at zero, and the thin colours
         stand on five to ten pairs each.
sweep    27,053 renders over a seeded two-location panel, made to cover the
         grid the head never visited. Every pair, but two locations.
```

The union is what makes the map complete — all 14,796 pairs — and the two counts
stay apart on every row, because a reader weighting a pair by how much production
evidence stands behind it needs to know which half it came from.

## What one row says, and what it deliberately does not

The mean chromatic share per codebook cell, over `dominance.of_shares`: neutrals
out of the numerator and the denominator, so the numbers are shares of the
picture's **colour** rather than of its pixels. Stored **sparse** at
[`STORED_FLOOR`] — a cell below one percent of the colour cannot lead a cell and
cannot carry a family on its own, and storing all 48 for every pair is four
megabytes of numbers nothing reads. The residual is recoverable: a row's stored
cells sum to at most 1, and `1 - sum` is what the floor dropped.

The **recipe is not stored** and neither is the render cost. Both are
reconstructible — the recipe from the key, the cost from the sweep's own log — and
a map that carried them would be an experiment log wearing a map's name. The
per-location rows are not here either, for the same reason and because the key is
the pair.

## Two warnings the rows carry rather than leave to a reader

**Autolevel.** `band_autolevel` rewrites the map's stops before the field is
coloured, so a levelled picture is not a lookup into the map that was screened.
It is not a small effect: `within-25 x smooth` reads teal 0.002 unlevelled and
**0.266** levelled. Every row says how many of its observations were levelled, so
a pair whose mass depends on the operator can be told from one that does not.

**Noisy modes.** [`NOISY_MODES`] — `gaussian_int` and three of the direct traps —
produce fields high-frequency enough that supersampling and JPEG average colour
*after* the colormap lookup, and the stored picture is meaningfully not a lookup
into its own colormap at all. `meloni x gaussian_int` reads red 0.458 against a
ramp bound of 0.010, and 0.000 at one sample per pixel written as PNG. They are
flagged and **kept**: the reading is what the pipeline really produces, which is
what a ceiling acts on. It is the *bound* that does not apply to them.

## Why it is eighteen files

One per mode over the roster it was measured on — see [`UNMEASURED`] for the
production mode that has no file — under `data/palettes/color_mass/`. `tests/test_history_purity.py`
caps a tracked file at 1 MiB and the whole map is several megabytes, so it splits
the way the tracked release store splits on partition — for the guard, and on the
axis a reader already has in hand. A `.json` under `data/palettes/` is a colormap
by convention (every reader of the library globs `*.json` there and takes the stem
as a map name), so these are `.jsonl` in a subdirectory, where that glob cannot
reach them.
"""

from __future__ import annotations

import json
from pathlib import Path

from fractal_wallpapers.paths import colormap_dir, tracked_name

#: The schema every row carries, from its first line.
SCHEMA = 1

#: The subdirectory of the tracked palette library the map lives in. One file per
#: mode inside it, named for the mode.
RECORD_DIR = "color_mass"

#: The two kinds of row a file holds: one header, then one per palette group.
METHOD_ROW = "method"
PAIR_ROW = "pair"

#: The smallest mean share a cell is stored at. Below this a cell can neither lead
#: (`dominance.CELL_LEAD` is 0.10) nor reach `CELL_ALONE`, and four of them
#: together fall short of `FAMILY_LEAD`; what it costs to drop them is on the
#: header as `mass_below_floor`, and a reader wanting the residual takes
#: `1 - sum(cells.values())`.
STORED_FLOOR = 0.01

#: The modes whose stored picture is meaningfully not a lookup into its own
#: colormap. Their fields are high-frequency enough that the supersample and the
#: JPEG average colour after the lookup, which puts realized mass **above** what
#: the ramp can supply — 190 of `direct_trap_multiply`'s 741 (pair, family) reads
#: sit above the bound, 111 of `direct_trap_screen`'s and 103 of
#: `direct_trap_ring`'s. Read their rows as noisier than the smooth ones; the ramp
#: screen should not be used on them at all.
NOISY_MODES = (
    "direct_trap_multiply",
    "direct_trap_ring",
    "direct_trap_screen",
    "gaussian_int",
)

#: **Production modes the map holds no rows for, named so the hole is not silent.**
#:
#: The map is a *measurement* — 15,681 judged pool rows and a 27,053-render sweep —
#: taken over the roster of the day. A mode added to the engine's catalog
#: afterwards has no file and no rows, and a lookup for it reads exactly like a
#: pair with no colour, which is the failure [`read`] and the completeness guard
#: exist to prevent. Writing it down here is what turns that into a stated
#: absence: the guard asserts this set is exactly the production modes with no
#: file, so a mode measured later has to leave this tuple and a mode retired from
#: the engine cannot linger in it.
#:
#: Filling one in is not a code change. It is a sweep leg — every palette group at
#: the new mode over the seeded two-location panel — and then
#: `fractal-wallpapers palettes color-mass build`.
#:
#: `tail_itinerary` is here because it arrived with the tail address window and
#: nothing has been rendered in it at scale. Its colour behaviour is not
#: `itinerary`'s: the address reads near zero wherever the orbit escaped fast, so
#: the modulate's shift is off over most of a frame and the realized mass is the
#: smooth base's rather than the address's.
UNMEASURED = ("tail_itinerary",)

#: The two measurements a pair's observations can come from, and what each is.
SOURCES = ("census", "sweep")


class ColorMassError(RuntimeError):
    """The colour-mass map cannot be read, or cannot be built from what is here."""


# --------------------------------------------------------------------------- #
# Where it lives.
# --------------------------------------------------------------------------- #
def record_dir(directory: Path | None = None) -> Path:
    """The subdirectory holding one file per mode."""
    return (colormap_dir() if directory is None else Path(directory)) / RECORD_DIR


def record_path(mode: str, directory: Path | None = None) -> Path:
    """One mode's file: every palette group's realized colour in that mode."""
    return record_dir(directory) / f"{mode}.jsonl"


def stored_modes(directory: Path | None = None) -> list[str]:
    """Every mode the committed map holds a file for, in name order."""
    root = record_dir(directory)
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob("*.jsonl"))


def measured_modes() -> list[str]:
    """Every production mode the map is meant to be complete over, in catalog order.

    The engine's roster less [`UNMEASURED`]. Read this rather than
    `engine.production_modes()` when asking whether the map has a hole: a mode
    that has never been swept is not a hole, it is a mode nobody has measured, and
    the two want different answers.
    """
    from fractal_wallpapers import engine

    absent = set(UNMEASURED)
    return [name for name in engine.production_modes() if name not in absent]


# --------------------------------------------------------------------------- #
# Reading.
# --------------------------------------------------------------------------- #
def read_mode(mode: str, directory: Path | None = None) -> tuple[dict, list[dict]]:
    """`(method, pairs)` for one mode, or a refusal naming the file that is absent.

    The header is returned beside the rows rather than filtered out of them: it
    carries the codebook the shares were read on and whether this mode is one of
    [`NOISY_MODES`], and a caller that dropped it would be reading numbers with no
    record of the instrument.
    """
    path = record_path(mode, directory)
    if not path.is_file():
        raise ColorMassError(
            f"{path} is not there, so nothing says what {mode!r} makes. Run "
            f"`fractal-wallpapers palettes color-mass` to build the map, or check the mode "
            f"name against `stored_modes()`."
        )
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows or rows[0].get("kind") != METHOD_ROW:
        raise ColorMassError(f"{path} does not open with a {METHOD_ROW!r} row.")
    return rows[0], [row for row in rows[1:] if row.get("kind") == PAIR_ROW]


def read(directory: Path | None = None) -> dict[tuple[str, str], dict]:
    """The whole map as `{(group, mode): row}`, the shape a lookup wants.

    `noisy` is attached to every row on the way out, from its file's header. The
    record says it once per file — it is a property of the mode and true of all
    822 rows or none of them — and a reader holding one row still has to be able
    to see it, which is what this join is for.
    """
    out: dict[tuple[str, str], dict] = {}
    for mode in stored_modes(directory):
        method, pairs = read_mode(mode, directory)
        for row in pairs:
            out[(str(row["group"]), str(row["mode"]))] = {**row, "noisy": bool(method["noisy"])}
    return out


def share_of(row: dict, name: str) -> float:
    """One cell's mean share on a pair's row; `0.0` for a cell the floor dropped.

    A cell absent from a row is not missing data — it is a cell measured below
    [`STORED_FLOOR`], which is a number, and returning it as one is what keeps a
    caller from having to know the storage rule.
    """
    return float((row.get("cells") or {}).get(name, 0.0))


def observations(row: dict) -> int:
    """How many renders stand behind one pair's means, over both measurements."""
    counts = row.get("observations") or {}
    return sum(int(counts.get(name, 0)) for name in SOURCES)


def delivers(cell: str, group: str, table: dict, prior: float = 0.0, modes=None) -> float:
    """How much of `cell` one palette group is expected to put on a picture.

    **Mode-conditional mass where it exists, the carrier prior where it does not.**
    The mass map is keyed on `(group, mode)` and the carrier table on the map, so
    the two answer the same question at different keys and only one of them is a
    measurement of the pipeline; `prior` — the group's carrier mean for the cell —
    is consulted for a group with no mass row at all (one of the 823 today) and
    never to overrule one that has.

    The **max** over `modes` and not the mean, because a run's map pool is shared
    by every arm and every mode in it: a map dropped for failing on modes the leg
    will not run is a map narrowed away for nothing. `modes` unsaid is
    [`curation.mode_policy.accepted`], which is the set a leg may actually render —
    the four measured modes outside it include the noisy ones this module's own
    docstring warns are not lookups into their colormap.

    **A caller in a loop resolves `modes` once and hands it in.** `accepted()` reads
    its record on every call at about 13 ms, which is nothing once and 54 seconds
    over the 4,110 (map, cell) pairs a five-cell cut of the pool asks — which is
    what this cost before [`delivering`] hoisted it.
    """
    from fractal_wallpapers.curation import mode_policy

    wanted = mode_policy.accepted() if modes is None else modes
    best = None
    for mode in wanted:
        row = table.get((str(group), str(mode)))
        if row is not None:
            share = share_of(row, str(cell))
            best = share if best is None else max(best, share)
    return float(prior) if best is None else best


def delivering(cells, cutoff: float | None = None, within=None, modes=None) -> list[str]:
    """Every map expected to deliver **any** of `cells` at or above `cutoff`.

    The palette neighbourhood a cell-aimed draw offers. Any and not all: a leg
    listing five thin cells wants the maps that serve one of them, and a pool cut
    to the maps that serve all five is a pool cut to almost nothing.

    `cutoff` unsaid is [`palettes.dominance.CELL_LEAD`] rather than a constant of
    this module's own. A row here is the mean chromatic share a pair puts on a
    picture and `CELL_LEAD` is the share at which a cell *leads* one, so the
    default reads as **this pair's expected colour in the cell is at least what a
    cell needs to be dominant at**. It is also the loosest value that is still a
    bound at this library: at `0.10` the thinnest cell offers 40 maps of the
    collapsed pool and at `0.15` it offers 28, under the 32
    [`curation.colorize.CANDIDATES`] asks for.

    `within` is the maps the caller may actually draw — a run's collapsed
    `colorize.pool` — and the result keeps its order, so a caller narrowing a pool
    hands one back in the same order it was given. Unsaid, the whole shipped
    library through [`palettes.groups.library`].

    This is a **draw filter and nothing else**, on [`curation.depth.read_maps`]'
    standing: it re-marks no map, folds none, moves no bar and writes nothing back
    to the tracked colour records.
    """
    from fractal_wallpapers.curation import mode_policy
    from fractal_wallpapers.palettes import carriers, dominance, groups

    wanted = [str(one) for one in cells]
    if not wanted:
        raise ColorMassError("delivering() was asked for no cell, so it has nothing to cut on.")
    known = set(dominance.cells())
    unknown = [one for one in wanted if one not in known]
    if unknown:
        raise ColorMassError(
            f"{unknown[0]!r} is not a codebook cell, so no map can be measured against it. "
            f"A misspelt cell would narrow a pool nobody chose."
        )
    bar = dominance.CELL_LEAD if cutoff is None else float(cutoff)
    roster = tuple(mode_policy.accepted() if modes is None else modes)
    offered = list(groups.library()) if within is None else [str(one) for one in within]
    table = read()
    member = groups.member_groups()
    carrier_table = carriers.table()
    priors = {cell: carrier_table.get(cell, {}) for cell in wanted}
    out = []
    for name in offered:
        group = groups.group_of(name, member)
        for cell in wanted:
            if delivers(cell, group, table, priors[cell].get(name, 0.0), roster) >= bar:
                out.append(name)
                break
    return out


# --------------------------------------------------------------------------- #
# Writing.
# --------------------------------------------------------------------------- #
def text_of(rows: list[dict]) -> str:
    """One mode's file text: one row to a line, the header first."""
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def write_mode(mode: str, rows: list[dict], directory: Path | None = None) -> Path:
    """Write one mode's file as tracked text. LF, because this file is in the history."""
    path = record_path(mode, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text_of(rows), encoding="utf-8", newline="\n")
    return path


# --------------------------------------------------------------------------- #
# Building it, out of the two measurements.
# --------------------------------------------------------------------------- #
def _levelled_by_picture() -> dict[str, bool]:
    """Whether autolevel acted on each pool picture, keyed by the picture's path.

    The census's observation rows name a picture and nothing else about the
    operator; the pool row that picture was decided on carries `autolevel.acted`.
    So the flag is joined back here rather than re-derived, and a picture whose row
    predates the operator is simply absent from the table — three thousand of them
    are, and a `False` there would claim the operator ran and did nothing.
    """
    from fractal_wallpapers.curation import gallery_store, records, rescore

    pool = [*records.read_decisions(records.RELEASE), *gallery_store.read()]
    index = {str(row.get("key")): row for row in pool if row.get("key")}
    out: dict[str, bool] = {}
    for row in pool:
        operator = row.get("autolevel")
        if not isinstance(operator, dict):
            continue
        try:
            picture = str(rescore.picture_of(row, index))
        except (KeyError, TypeError):
            continue
        out.setdefault(picture, bool(operator.get("acted")))
    return out


def _cell(table: dict, key: tuple[str, str]) -> dict:
    return table.setdefault(
        key,
        {"sum": {}, "census": 0, "sweep": 0, "levelled": 0, "unrecorded": 0, "colourless": 0},
    )


def _add(cell: dict, shares: dict) -> None:
    for name, value in shares.items():
        cell["sum"][name] = cell["sum"].get(name, 0.0) + float(value)


def tally(census: Path, sweep: Path, log=print) -> tuple[dict, dict]:
    """`(table, counts)` — every (group, mode) pair's running totals, over both sources.

    The two files are read row by row rather than loaded: the sweep's is tens of
    megabytes of 48-cell vectors and the whole point of the map is that nothing
    downstream has to hold that.

    A **colourless** observation — a picture with no chromatic pixels at all, which
    `dominance.of_shares` reads as an empty vector — is counted in the pair's `n`
    and contributes nothing to its sums. That is the honest arithmetic: the render
    happened and it made no colour, so it belongs in the denominator. 1,576 of the
    sweep's renders and 217 of the census's are in that position.
    """
    from fractal_wallpapers.palettes import codebook

    kinds = {entry["swatch"]: entry["kind"] for entry in codebook.swatches()}
    levelled = _levelled_by_picture()
    log(f"[color-mass] autolevel read for {len(levelled):,} pool picture(s)")

    table: dict[tuple[str, str], dict] = {}
    counts = {"census": 0, "sweep": 0, "colourless": 0, "unrecorded": 0}
    with Path(census).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            cell = _cell(table, (str(row["group"]), str(row["mode"])))
            cell["census"] += 1
            counts["census"] += 1
            # The census's rows are already chromatic shares of the colour — the
            # observation writer took them through `dominance.of_shares` — so they
            # are summed as they stand rather than renormalised a second time.
            if row["cells"]:
                _add(cell, row["cells"])
            else:
                cell["colourless"] += 1
                counts["colourless"] += 1
            acted = levelled.get(str(row["picture"]))
            if acted is None:
                cell["unrecorded"] += 1
                counts["unrecorded"] += 1
            elif acted:
                cell["levelled"] += 1

    with Path(sweep).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") != "render":
                continue
            if row.get("error"):
                raise ColorMassError(
                    f"{sweep} holds a failed render for {row.get('group')} x "
                    f"{row.get('mode')}: {row['error']}. The sweep reported zero failures; "
                    f"a map cut over a file that has some is a map with a hole in it."
                )
            cell = _cell(table, (str(row["group"]), str(row["mode"])))
            cell["sweep"] += 1
            counts["sweep"] += 1
            # The sweep's rows are the raw 52-cell census, neutrals included, so
            # they go through the same reduction the census's did.
            chromatic = {
                name: float(value)
                for name, value in (row.get("shares") or {}).items()
                if kinds.get(name) == "hue"
            }
            total = sum(chromatic.values())
            if total > 0.0:
                _add(cell, {name: value / total for name, value in chromatic.items()})
            else:
                cell["colourless"] += 1
                counts["colourless"] += 1
            if row.get("leveled"):
                cell["levelled"] += 1
    log(
        f"[color-mass] {counts['census']:,} census + {counts['sweep']:,} sweep observation(s) "
        f"over {len(table):,} pair(s)"
    )
    return table, counts


def rows_for(mode: str, table: dict, floor: float = STORED_FLOOR) -> tuple[list[dict], dict]:
    """`(rows, price)` — one mode's file, and what the sparsity floor cost it."""
    out = []
    dropped_cells = 0
    dropped_mass = 0.0
    for (group, name), cell in sorted(table.items()):
        if name != mode:
            continue
        n = cell["census"] + cell["sweep"]
        mean = {key: value / n for key, value in cell["sum"].items()}
        kept = {key: round(value, 4) for key, value in mean.items() if value >= floor}
        kept = {key: value for key, value in kept.items() if value > 0.0}
        dropped_cells += len(mean) - len(kept)
        dropped_mass += sum(mean.values()) - sum(kept.values())
        out.append(
            {
                "schema": SCHEMA,
                "kind": PAIR_ROW,
                "group": group,
                "mode": mode,
                "observations": {"census": cell["census"], "sweep": cell["sweep"]},
                # How many of those observations the operator changed, and how many
                # cannot say. `levelled` counts the renders autolevel ACTED on, not
                # the ones it was offered: a switch that ran and moved nothing is a
                # picture that is a lookup into its own map, which is the thing this
                # column exists to distinguish.
                "autolevel": {"acted": cell["levelled"], "unrecorded": cell["unrecorded"]},
                # A render that came out with no chromatic pixel at all. In `n`,
                # out of the sums, and named so a pair standing mostly on black
                # pictures cannot read as a pair with thin colour.
                "colourless": cell["colourless"],
                "cells": dict(sorted(kept.items(), key=lambda item: (-item[1], item[0]))),
            }
        )
    price = {
        "pairs": len(out),
        "cells_stored": sum(len(row["cells"]) for row in out),
        "cells_below_floor": dropped_cells,
        "mass_below_floor": round(dropped_mass / max(1, len(out)), 6),
    }
    return out, price


def method_row(mode: str, price: dict, sources: dict) -> dict:
    """The header every mode's file opens with: the instrument, and what it cost."""
    from fractal_wallpapers.palettes import codebook, dominance

    return {
        "schema": SCHEMA,
        "kind": METHOD_ROW,
        "mode": mode,
        "noisy": mode in NOISY_MODES,
        "cells": len(dominance.cells()),
        "stored_floor": STORED_FLOOR,
        "rule": dominance.RULE,
        "codebook": codebook.document()["assignment"],
        "sources": sources,
        **price,
        "note": (
            "mean chromatic share per codebook cell over a (palette group, mode) pair, "
            "stored sparse: a cell below `stored_floor` is not on the row and reads 0.0. "
            "The residual a row does not account for is 1 - sum(cells). `observations` "
            "splits the two measurements because they are two populations - the census is "
            "where the palette head went, the sweep is a seeded two-location panel over the "
            "whole grid. `noisy` marks a mode whose field is high-frequency enough that "
            "supersampling and JPEG average colour AFTER the colormap lookup, so its "
            "picture is meaningfully not a lookup into its own map; down-weight it rather "
            "than dropping it. The recipe is not stored and is reconstructible from the key."
        ),
    }


def build(census: Path, sweep: Path, floor: float = STORED_FLOOR, log=print) -> dict:
    """Cut the map out of the two measurements and write it. One file per mode."""
    table, counts = tally(Path(census), Path(sweep), log=log)
    modes = sorted({mode for _group, mode in table})
    # `tracked_name`, because these files are named inside the history: a header
    # carrying one machine's drive letter is a source nobody else can look at, and
    # the sweep's record is under the regenerable tree, which moves between tiers.
    sources = {
        "census": {"path": tracked_name(census), "observations": counts["census"]},
        "sweep": {"path": tracked_name(sweep), "observations": counts["sweep"]},
    }
    written = []
    for mode in modes:
        rows, price = rows_for(mode, table, floor=floor)
        path = write_mode(mode, [method_row(mode, price, sources), *rows], None)
        written.append(
            {
                "mode": mode,
                "path": tracked_name(path),
                "bytes": path.stat().st_size,
                "noisy": mode in NOISY_MODES,
                **price,
            }
        )
        log(f"[color-mass] {mode:24} {price['pairs']:4} pair(s)  {path.stat().st_size:>9,} bytes")
    return {
        "schema": SCHEMA,
        "pairs": len(table),
        "modes": len(modes),
        "groups": len({group for group, _mode in table}),
        "stored_floor": floor,
        "observations": counts,
        "sources": sources,
        "largest_file_bytes": max(entry["bytes"] for entry in written),
        "total_bytes": sum(entry["bytes"] for entry in written),
        "files": written,
    }


# --------------------------------------------------------------------------- #
# The sweep log the map was cut from, on the archive tier under a manifest.
# --------------------------------------------------------------------------- #
#: What the sweep's per-render record is called, wherever it is. One row per
#: (group, mode, location) triple with its 48-cell vector, its recipe, whether
#: autolevel acted and what it cost — 25.7 MB of it.
SWEEP_LOG = "rows.jsonl"

#: The subtree that record sits in, under the regenerable tree.
SWEEP_UNIT = "palette_mass_sweep"


def sweep_log_path() -> Path:
    """The sweep's record, on whichever tier curation's subtree is."""
    from fractal_wallpapers.paths import under

    return under("curation", SWEEP_UNIT) / SWEEP_LOG


def sweep_backup_path() -> Path:
    """The durable copy, beside the sidecar's and the gate stores' on the archive tier.

    Off a root rather than through `under()`, for [`curation.durability`]'s
    reason: a copy resolved through the tiers lands on whichever tier the original
    is already on, which is the one place a second copy is no use.
    """
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.paths import archive_root, hot_root

    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / SWEEP_UNIT / SWEEP_LOG


def sweep_manifest_path() -> Path:
    """The tracked manifest: what the sweep log was, last time it was recorded.

    Under `data/curation/` beside the other three durability manifests, and
    **not** beside the map it fed: a `.json` under `data/palettes/` is a colormap
    by convention, and a manifest filed there would read back as a map named
    `palette_mass_sweep.manifest`.
    """
    from fractal_wallpapers.curation import records

    return records.root() / f"{SWEEP_UNIT}.manifest.json"


def _sweep_facts(path: Path) -> dict:
    """The columns the sweep log adds to its manifest: what it measured, and over what."""
    modes: dict[str, int] = {}
    pairs: set[tuple[str, str]] = set()
    locations: set[str] = set()
    failed = 0
    header: dict = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") == "header":
                header = row
                continue
            mode = str(row.get("mode"))
            modes[mode] = modes.get(mode, 0) + 1
            pairs.add((str(row.get("group")), mode))
            locations.add(str(row.get("location")))
            if row.get("error"):
                failed += 1
    return {
        "pairs": len(pairs),
        "locations": len(locations),
        "rows_by_mode": dict(sorted(modes.items())),
        "failed": failed,
        "bands": header.get("bands"),
        "panel": header.get("panel"),
        "geometry": header.get("geometry"),
        "cut_into": tracked_name(record_dir()),
    }


def sweep_log():
    """The sweep log as a [`curation.durability.Durable`] — how it is saved and checked.

    It gets the archive treatment the supply sidecar and the gate stores get, and
    for a reason none of the three share: it is an **experiment log**, finished and
    not to be added to, and the only thing that would let this map be re-cut on
    other terms — excluding [`NOISY_MODES`], weighting the panel differently,
    rolling to families instead of cells. Re-deriving it is **52.1 hours of engine
    time** over 27,053 renders — its own rows' `seconds`, summed 2026-09-05, which
    is where the 8.7 hours this said before went — and the pictures it read were
    censused and deleted.

    Tracking it is out for the ordinary reason and by a wide margin: 25.7 MB
    against a 1 MiB per-file guard. What the history keeps is this manifest and
    [`record_dir`]'s map; what the archive keeps is the log.
    """
    from fractal_wallpapers.curation import durability

    return durability.Durable(
        name="the palette colour-mass sweep log",
        live=sweep_log_path(),
        copy=sweep_backup_path(),
        manifest=sweep_manifest_path(),
        why_not_tracked=(
            "25.7 MB of 48-cell vectors over 27,053 renders against a 1 MiB per-file "
            "history guard. It is a finished experiment log rather than a record anything "
            "reads: what production reads is the map cut from it, which is tracked. The "
            "manifest is what the history keeps — the row count, the bytes, the sha256, the "
            "pairs and locations measured, and the panel they were measured on."
        ),
        save_command="fractal-wallpapers curate mass-sweep save",
        restore_command="fractal-wallpapers curate mass-sweep restore",
        # The rebuild and the restore are the same command on purpose. Every other
        # durable file names a subcommand that makes it again; this one has none.
        # The sweep ran out of `scratch/palette_mass_sweep/`, which is defined as
        # disposable, and re-deriving it is 52.1 engine hours over pictures that
        # were censused and deleted. That there is nothing to rebuild it WITH is the
        # whole argument for archiving it, so the refusal says restore twice
        # rather than naming a command nobody can run.
        rebuild_command="fractal-wallpapers curate mass-sweep restore",
        facts=_sweep_facts,
    )


def save_sweep_log(log=print) -> dict:
    """Copy the sweep log to the archive tier and write its manifest. One claim, one call."""
    from fractal_wallpapers.curation import durability

    return durability.save(sweep_log(), log=log)


def check_sweep_log(log=print) -> dict:
    """Read the live sweep log against its manifest, and name the disagreement.

    `missing` is the **resting state** for this one, not an alarm: the log is
    archived on purpose and the hot copy is meant to be gone. Nothing guards on
    it — `durables.guard` refuses over the supply sidecar and nothing else — so
    a checkout with no local copy is a checkout that has not needed one.
    """
    from fractal_wallpapers.curation import durability

    return durability.check(sweep_log(), log=log)


def restore_sweep_log(force: bool = False, log=print) -> dict:
    """Bring the archived sweep log back, counted against the manifest before it is believed."""
    from fractal_wallpapers.curation import durability

    return durability.restore(sweep_log(), force=force, log=log)


__all__ = [
    "METHOD_ROW",
    "NOISY_MODES",
    "PAIR_ROW",
    "RECORD_DIR",
    "SCHEMA",
    "SOURCES",
    "STORED_FLOOR",
    "UNMEASURED",
    "ColorMassError",
    "SWEEP_LOG",
    "SWEEP_UNIT",
    "build",
    "check_sweep_log",
    "delivering",
    "delivers",
    "measured_modes",
    "method_row",
    "observations",
    "read",
    "read_mode",
    "record_dir",
    "record_path",
    "restore_sweep_log",
    "rows_for",
    "save_sweep_log",
    "share_of",
    "stored_modes",
    "sweep_backup_path",
    "sweep_log",
    "sweep_log_path",
    "sweep_manifest_path",
    "tally",
    "text_of",
    "write_mode",
]
