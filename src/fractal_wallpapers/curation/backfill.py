"""Giving a curve back to the rows whose leg never wrote one down.

A third of a gallery's seats are `acted_unrecoverable`: the operator acted, the
row carries the boolean, and no record anywhere holds the curve it acted with.
Those seats cannot inherit a levelling decision ([`curation.stamps`]) because
there is no decision on file to inherit — so a release of one measures its own
tone at release geometry, which is the thing the replay change exists to stop.

## Why there are so many, and it is not only history

Two causes, and only the first is a backlog. Every candidate rendered before
2026-09-02 predates the whole stamp. But [`curation.mine`] **still** records no
stamp: `mine.make` returns it, the leg counts `autolevel_acted` off it and drops
it, and the ledger row keeps only the reduced stamp. A mine-sourced acted
candidate is therefore unrecoverable the day it is made. This module fills both
in the same way and does not pretend the second is closed by doing so.

## What a backfilled stamp is, and what it is not

**It is a re-derivation, not a recovery.** The original curve came off the
original base render, and that render is gone: what is on disk is the *levelled*
picture the judge scored. So this re-renders the base at candidate geometry with
the operator switched off, measures that, and derives. Where the row's own
`<stem>.leveled/` directory survives, the stops it holds are the ramp that
actually shipped, and the leg **compares** the two rather than choosing between
them — the agreement rate is the honest measure of what a backfill is worth, and
it is on the record this writes.

Every row says which it is, under `provenance.curve`, and no reader has to trust
a re-derivation as though it were the original.

## The sidecar, not the record

Nothing rewrites, deletes or re-keys any existing row, and no leg's
`sequence.jsonl` is touched. This is a second file, append-only, keyed by
**recipe key**, overlaid at read time — `score_amendments.jsonl`'s shape
([`curation.amend`]) for `score_amendments.jsonl`'s reason: the record is what
the leg wrote on the night it wrote it, and a pass that edited it would delete
the only evidence of what was actually recorded. Two backfills of one key are two
rows and the later wins.

**It lives in the ignored store**, so a clone does not have it and the website
cannot read it. That is the same standing as every other artifact here bar a
published record's two text files, and it means a backfilled seat is replayable
*on this machine* and still ships its stored picture everywhere else.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fractal_wallpapers.coloring import autolevel
from fractal_wallpapers.paths import colormap_dir, under

#: The schema every backfill row carries.
SCHEMA = 1

#: What the sidecar is called, in the curation store beside the ledger.
BACKFILL_NAME = "autolevel_backfill.jsonl"

#: What `provenance.curve` says on a stamp this module made. Not
#: [`autolevel.DERIVED`], which means *this render derived it from its own base*
#: — a backfilled curve was derived from a base render made months after the
#: picture, and a reader that could not tell the two apart would be reading a
#: reconstruction as a record.
REDERIVED = "rederived"

#: What a row says about how its curve was checked against the shipped ramp.
AGREES, DIFFERS, NO_RAMP = "agrees", "differs", "no_ramp"


class BackfillError(RuntimeError):
    """The sidecar cannot be read, or a seat cannot be backfilled."""


def path() -> Path:
    """Where the sidecar lives: the curation store, beside the ledger it amends."""
    return under("curation") / BACKFILL_NAME


def rows(where: Path | None = None) -> list[dict]:
    """Every backfill row ever appended, in the order they were written."""
    where = path() if where is None else Path(where)
    if not where.is_file():
        return []
    out = []
    for number, line in enumerate(where.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") != SCHEMA:
            raise BackfillError(
                f"{where}:{number}: schema {row.get('schema')!r}, expected {SCHEMA}"
            )
        out.append(row)
    return out


def read(where: Path | None = None) -> dict:
    """`{recipe key: row}` — the overlay [`curation.stamps.for_rows`] prefers.

    Last row for a key wins. Unlike the score amendment this is **not** filtered
    by engine build: a tone curve is a function of the picture's tone and the
    band, and the band is in the recipe key already; two builds that drew the same
    recipe drew the same picture or the recipe key would have moved.
    """
    return {row["key"]: row for row in rows(where)}


def append(minted: list[dict], where: Path | None = None) -> Path:
    """Append these rows. Never rewrites, so an interrupted leg keeps what it did."""
    where = path() if where is None else Path(where)
    if not minted:
        return where
    where.parent.mkdir(parents=True, exist_ok=True)
    with where.open("a", encoding="utf-8", newline="\n") as handle:
        for row in minted:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return where


def row(key: str, stamp: dict, checked: str, source: dict) -> dict:
    """One sidecar row: a recipe key, the whole re-derived stamp, and what it cost.

    `checked` is [`AGREES`], [`DIFFERS`] or [`NO_RAMP`] — whether the stops this
    curve rebuilds are the stops the row's own `.leveled/` directory holds, where
    that directory still exists. It is recorded per row rather than only counted,
    because a reader asking whether *this* seat's backfill is trustworthy is
    asking about one row and not about a rate.
    """
    marked = json.loads(json.dumps(stamp))
    marked["provenance"] = {"curve": REDERIVED, "from": dict(source)}
    return {
        "schema": SCHEMA,
        "key": str(key),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "autolevel": marked,
        "checked": str(checked),
        "source": dict(source),
    }


def shipped_stops(picture: Path | None, colormap: str) -> list | None:
    """The stop list this row actually shipped, off its own `.leveled/` directory.

    `None` where the picture is gone, the directory was swept, or the row never
    acted. The directory is named for the picture's stem at every site that writes
    one — see [`curation.colorize.render`]'s `rerender` — so it is found from the
    picture's own path and nothing has to remember where a leg put it.
    """
    if picture is None:
        return None
    picture = Path(picture)
    where = picture.parent / f"{picture.stem}.leveled" / f"{colormap}.json"
    if not where.is_file():
        return None
    try:
        return json.loads(where.read_text(encoding="utf-8")).get("stops")
    except (OSError, ValueError):
        return None


def agreement(stamp: dict, shipped: list | None, stops: list) -> str:
    """Whether a re-derived curve rebuilds the ramp that shipped. See [`row`]."""
    if not shipped:
        return NO_RAMP
    if not stamp.get("acted"):
        # An in-band re-derivation and a `.leveled/` directory on disk disagree
        # by construction: the row shipped a curved ramp and this says it should
        # not have. That is a difference and the sharpest kind.
        return DIFFERS
    try:
        rebuilt = autolevel.stops_from_stamp(stamp, stops)
    except autolevel.AutolevelError:
        return DIFFERS
    return AGREES if rebuilt == shipped else DIFFERS


#: Which record's seats a backfill sweeps unless a caller names another. The
#: n=1000 gallery of 2026-09-08 — the record the site's figures resolve and the
#: one every seat of which is expressible from the candidate path.
DEFAULT_RECORD = "20260908T144844Z"

#: How often the leg says where it is. A backfill is hundreds of renders and the
#: only thing that distinguishes a slow one from a hung one is a line.
PROGRESS = 25


def _wanted(rows: dict, held: dict) -> list[str]:
    """The keys of `rows` that have no curve anywhere and take the operator at all.

    Three exclusions, and each is a different fact. A recipe whose `autolevel` is
    null is a mode [`coloring.autolevel.applies_to`] answers no for — a direct
    trap — and there is no curve to want. A key already in `held` has one on a run
    record. Everything else is a seat whose leg wrote none down.
    """
    out = []
    for key, row in rows.items():
        if key in held:
            continue
        if not ((row.get("recipe") or {}).get("autolevel")):
            continue
        out.append(key)
    return sorted(out)


def survey(stamp: str = DEFAULT_RECORD) -> dict:
    """What a record's seats stand at, and what filling them would cost. No renders.

    Read-only and cheap enough to run before deciding: it opens the record, looks
    every seat up in the ledger, groups the lookups by leg and streams each leg's
    sequence once. The price of a store-wide backfill is quoted from the same
    arithmetic over [`curation.tentative.protected_keys`], which is why that
    number is here rather than estimated in a report.
    """
    from fractal_wallpapers.curation import candidate_ledger, tentative
    from fractal_wallpapers.curation import stamps as stamps_module

    keys = [str(row["key"]) for row in tentative.read_rows(stamp)]
    rows = candidate_ledger.by_key(keys)
    already = read()
    held = stamps_module.for_rows(rows, already)
    wanted = _wanted(rows, held)
    no_operator = [k for k, row in rows.items() if not ((row.get("recipe") or {}).get("autolevel"))]
    with_ramp = sum(
        1
        for key in wanted
        if shipped_stops(rows[key].get("picture"), str(rows[key]["recipe"]["colormap"]))
    )
    protected = tentative.protected_keys()
    return {
        "record": stamp,
        "seats": len(keys),
        "in_the_ledger": len(rows),
        "already_replayable": len(held),
        "no_operator": len(no_operator),
        "to_backfill": len(wanted),
        "of_those_with_a_shipped_ramp": with_ramp,
        "backfilled_already": len(already),
        # What the same sweep over every protected seat in the store would be.
        # Priced and not run: it is the whole gallery's worth of renders and it is
        # a decision, not a step.
        "protected_keys_in_store": len(protected),
        "store_wide_upper_bound_renders": len(protected),
    }


def _rerender(row: dict, band: dict | None, where: Path, cyclic: set):
    """Re-render one ledger row's candidate at its own geometry and level it.

    The **whole** operator, through the one door a candidate is ever made by, so
    what comes back is the pass the original leg made rather than an imitation of
    it. The recipe is handed over member by member — the curve and the palette
    included, through the overrides [`colorize.render_row`] grew — because a row
    whose knobs were not the candidate path's defaults would otherwise be
    re-derived as a picture it never was.
    """
    from fractal_wallpapers.curation import colorize, recipes

    recipe = recipes.of_record(row["recipe"])
    return colorize.render(
        {"family": recipe.family, "viewport": recipe.viewport, "maxiter": recipe.maxiter},
        recipe.mode,
        recipe.colormap,
        cyclic,
        where,
        render_geometry=recipe.render(),
        level=True,
        band=band,
        mode_params=recipe.mode_params,
        curve=recipe.curve,
        palette=recipe.palette,
    )


def sweep(
    stamp: str = DEFAULT_RECORD, limit: int | None = None, log=print, where: Path | None = None
) -> dict:
    """Re-derive a curve for every seat of one record that has none, and record it.

    **Serial, and that is the render-pool rule rather than a shortcut**: one
    engine at below-normal priority is inside the three this machine allows, and
    a backfill is a leg that runs beside nothing. Each seat costs a base render
    and, where the operator acts, a second colouring — the same two passes the
    original candidate cost.

    Nothing it writes is a record of what shipped. See the module docstring: the
    curve comes off a base render made now, the row says so under
    `provenance.curve`, and where the seat's own `.leveled/` directory survived
    the two are compared and the verdict stored per row.
    """
    import shutil
    import time as time_module

    from fractal_wallpapers.curation import candidate_ledger, colorize, tentative
    from fractal_wallpapers.curation import stamps as stamps_module

    keys = [str(row["key"]) for row in tentative.read_rows(stamp)]
    rows = candidate_ledger.by_key(keys)
    held = stamps_module.for_rows(rows, read())
    wanted = _wanted(rows, held)
    if limit is not None:
        wanted = wanted[: max(0, int(limit))]
    scratch = Path(where) if where is not None else under("curation", "backfill", str(stamp))
    scratch.mkdir(parents=True, exist_ok=True)
    band, cyclic, maps = colorize.band(), colorize.cyclic(), colormap_dir()
    log(f"[backfill] {len(wanted)} seat(s) of {stamp} with no curve on any record")
    minted: list[dict] = []
    written = 0
    counts = {AGREES: 0, DIFFERS: 0, NO_RAMP: 0, "acted": 0, "in_band": 0, "failed": 0}
    started = time_module.monotonic()

    def append_and_clear(held: list[dict]) -> list[dict]:
        """Append what is held, empty the list, and hand back what went."""
        gone = list(held)
        append(gone)
        held.clear()
        return gone

    for number, key in enumerate(wanted, start=1):
        row = rows[key]
        picture = scratch / f"{key}.jpg"
        try:
            made, fresh = _rerender(row, band, picture, cyclic)
        except Exception as failure:  # noqa: BLE001 — a failed seat is a counted seat
            counts["failed"] += 1
            log(f"[backfill] {key} failed: {failure!r}"[:200])
            continue
        colormap = str(row["recipe"]["colormap"])
        entry = json.loads((maps / f"{colormap}.json").read_text(encoding="utf-8"))
        shipped = shipped_stops(row.get("picture"), colormap)
        verdict = agreement(fresh or {}, shipped, entry["stops"])
        counts[verdict] += 1
        counts["acted" if (fresh or {}).get("acted") else "in_band"] += 1
        minted.append(row_for(key, fresh, verdict, row, stamp))
        # The picture and its levelled colormap were made to be measured and are
        # not a record of anything: the seat's own picture is still where it was.
        Path(made).unlink(missing_ok=True)
        shutil.rmtree(picture.parent / f"{picture.stem}.leveled", ignore_errors=True)
        if number % PROGRESS == 0:
            # Flushed as it goes rather than at the end, which is what makes the
            # claim of resumability true: a leg killed at seat 200 keeps 200
            # seats, and the next run skips them because they are in the overlay
            # the wanted list is computed against.
            written += len(append_and_clear(minted))
            rate = (time_module.monotonic() - started) / number
            log(f"[backfill] {number}/{len(wanted)} at {rate:.2f} s/seat, {written} written")
    written += len(append_and_clear(minted))
    seconds = time_module.monotonic() - started
    shutil.rmtree(scratch, ignore_errors=True)
    return {
        "record": stamp,
        "considered": len(wanted),
        "written": written,
        "seconds": round(seconds, 1),
        "seconds_per_seat": round(seconds / max(1, written), 3),
        "counts": counts,
        "sidecar": str(path()),
    }


def row_for(key: str, stamp: dict | None, verdict: str, ledger_row: dict, record: str) -> dict:
    """[`row`], with the source block a backfill of a record's seat carries."""
    return row(
        key,
        stamp or {},
        verdict,
        {
            "record": str(record),
            "run": ((ledger_row.get("provenance") or {}).get("run")),
            "regime": str(ledger_row["recipe"]["regime"]),
        },
    )


__all__ = [
    "AGREES",
    "BACKFILL_NAME",
    "DEFAULT_RECORD",
    "PROGRESS",
    "DIFFERS",
    "NO_RAMP",
    "REDERIVED",
    "SCHEMA",
    "BackfillError",
    "agreement",
    "append",
    "path",
    "read",
    "row",
    "row_for",
    "rows",
    "shipped_stops",
    "survey",
    "sweep",
]
