"""Every candidate this project has rendered, one row per recipe, kept.

A gallery pass makes candidates and then throws away everything about them
except a decision. The pictures stay on disk under `artifacts/`, and the rows in
the two decision stores say what was decided — but nothing anywhere answers the
question a solver has to ask first: **have we already made this picture?** 126
of the 15,488 candidate renders on record are the same recipe drawn twice by two
different passes, byte for byte, because nothing could tell either pass that the
other had already spent the seconds.

This is the store that answers it. One row per [`recipes.Recipe`], carrying the
location it stands on, the colour it turned out to be, where its picture is if
the picture is still there, and which pass paid for it.

## Record everything; filter nothing

No quality bar admits a row here. A floor is a reading of a score, a score is a
reading of a judge, and both move; the recipe and the pixels do not. So a
candidate a floor rejected, a candidate a person **rejected**, and a candidate
that took a seat are all one row each, and the rejection travels on the row for a
solver to honour. Record-and-rank, in [`curation.colors`]' sense.

## Scores are not part of a recipe's identity

They are in a **sidecar**, keyed `(recipe key, judge artifact, regime)`. A judge
adoption invalidates every score in this project and nothing else — not a
picture, not a recipe, not a colour — and a store that carried the score on the
recipe row would have to rewrite every row to say so. The sidecar is also what
makes an honest comparison possible at all: gallery1's rows and gallery4's rows
carry numbers read on different artifacts, and the same recipe drawn by both
appears here twice, once per artifact.

The backfill measured the other half of that. The 126 duplicate renders make 128
pairs of byte-identical pictures; 59 of the pairs disagree on `P(>=3)`, and the
largest disagreement is 2.8e-7. So the judge is reproducible to about the seventh
decimal on identical bytes and no further, which is why the sidecar records what
a run **read** rather than promising that a recipe has a score.

## A superseded framing is a re-key, not a rebuild

Framing refinement is moving into harvest, and a harvest refinement **moves the
location key** ([`supply.ledgers.refined_of`]) — deliberately, because a walk's
refined frame simply is the location it found. That will re-key a large fraction
of the pool.

So the row's identity is the **recipe** and never the location key. A recipe
already carries the frame it was drawn at, so one row per recipe is one row per
(location, recipe) with the location's identity as a field rather than as part of
the name. When harvest re-frames a place, the rows standing on the old key keep
their pictures and their colours, and what changes is a field: `location.key`
gains a `superseded_by` beside it. Nothing is rebuilt and nothing is deleted.

Both keys are on every row and **neither is reconciled here**. 2,903 of the
15,488 renders on record carry a `location.key` that disagrees with the viewport
they were drawn at, and every one is a refined-frame row: the gallery pass
pins a location's identity to the frame on record while rendering somewhere else
inside it, which is what stops one place taking two seats. `location.key` is that
recorded identity; `location.frame_key` is the identity of the frame the pixels
are of. A reader that wants "the same place" takes the first; a reader that wants
"the same picture" takes the recipe key.

## The `hunt` block says what the draw intended

A row made by a hunt, a mine or a depth run carries the intention beside the
outcome: which leg drew it, which mode and colormap, which band or cell it was
drawn *for*, and **`k` — which candidate at its location it was**. That last one
is here rather than only in the run's own `sequence.jsonl` because those live
under the regenerable tree and the ledger does not, and the corrections a reader
has to make are `k`-dependent: a prime rate read off the maximum of `k` noisy
judgements is a winner's-curse estimate, and the multiplier that turns it into a
calibrated one is a function of `k`.

The field is **additive**, and every row written before the stamp existed has no
`k` at all. [`k_of`] returns `None` for those rather than 1, because a reader
that took a missing `k` for a first draw would report that whole history as
unselected and under-correct every estimate over it.

## Where it lives

The rows are megabytes and the history guard acts at 1 MiB a file, so this gets
what [`curation.gallery_store`] and the supply sidecar get: the file under
`artifacts/`, a copy on the archive tier, and a **manifest** in the history
saying how many rows, how many bytes and which sha256 that copy is.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.curation import durability, gallery_store, recipes, records
from fractal_wallpapers.paths import archive_root, hot_root, tracked_name, under

#: The schema every ledger and sidecar row carries.
SCHEMA = 1

#: The subtree both files live in, under the regenerable tree.
UNIT = "candidate_ledger"

#: What the files are called, in whichever of the two ledgers they belong to.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"

#: The **wide** ledger: the store as it was written up to 2026-08-29, one row
#: per recipe at about three kilobytes. It lives at the root of the unit and it
#: is left exactly where it is. Nothing writes to it any more.
WIDE = ""

#: The **retained** ledger: the same store at top-[`retention.KEEP_PER_PAIR`]
#: per (location, mode) under the four protections, and each row cut to what the
#: readers actually consume. A subdirectory rather than a second name in the
#: same one, so the three files that belong together are together and a backup,
#: a manifest and a tier move all address them as a unit.
RETAINED = "retained"

#: **Which ledger the readers read, and the one line that reverts this.** Set it
#: back to [`WIDE`] and every reader is on the old file again — the old file is
#: still there, byte for byte. Reverting after a leg has run is the one thing it
#: does not buy: a merge writes to whichever ledger is live, so rows added since
#: the flip live in the retained one alone.
LIVE = RETAINED

#: What a candidate's engine build is recorded as. Every candidate render in
#: every pass and every run predates [`engine_fingerprint`], which stamps a view
#: directory rather than a candidate directory, so there is nothing to read: the
#: whole backfilled pool is pre-stamp material accepted as unknown-engine, by
#: rule. Spelled through the fingerprint's own constant and not as a second word
#: for one fact — "nobody wrote it down" is never equal to a real build, which is
#: the property that makes it safe to compare against.
UNKNOWN_ENGINE = engine_fingerprint.UNKNOWN

#: Which store a backfilled row came out of. A run records every scored candidate
#: in the tracked release store; a gallery pass records its attempts in
#: [`curation.gallery_store`] instead.
FROM_RELEASE = "release"
FROM_GALLERY = "gallery"


class LedgerError(RuntimeError):
    """The ledger cannot be built, or cannot be read."""


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def store_root() -> Path:
    """The subtree the whole store sits in, on whichever tier it is on."""
    return under("curation", UNIT)


def ledger_root(which: str | None = None) -> Path:
    """The subtree one of the two ledgers sits in. [`LIVE`] by default."""
    which = LIVE if which is None else which
    return store_root() / which if which else store_root()


def rows_path(which: str | None = None) -> Path:
    """The ledger: one row per recipe. The live one unless told otherwise."""
    return ledger_root(which) / ROWS_NAME


def scores_path(which: str | None = None) -> Path:
    """The sidecar: one row per (recipe, judge artifact, regime)."""
    return ledger_root(which) / SCORES_NAME


def manifest_dir(which: str | None = None) -> Path:
    """The tracked directory one ledger's manifests live in."""
    which = LIVE if which is None else which
    root = records.default_root() / UNIT
    return root / which if which else root


def backup_path(name: str, which: str | None = None) -> Path:
    """The durable copy, beside the gate store's and the sidecar's.

    Off a root rather than through `under()`, for [`durability`]'s reason: a copy
    that resolved through the tiers would land on the tier the original is
    already on, which is the one place a second copy is no use.

    Public because the sidecars beside this store are not all owned by it:
    [`curation.flatness`] keeps its own file in the same subtree and must put its
    copy in the same place, and a second spelling of this path is how one of them
    ends up backed up somewhere nothing looks.
    """
    which = LIVE if which is None else which
    archive = archive_root()
    root = hot_root() if archive is None else archive
    where = Path(root) / durability.BACKUP_UNIT / UNIT
    return (where / which if which else where) / name


def _facts(path: Path) -> dict:
    """What the rows add to their own manifest: the population, and the colour rule.

    The rule and the codebook live here rather than on each row. They are
    identical on every one of them, and a share vector read next year under a
    moved codebook is a different number wearing the same name — which is a fact
    about the *store* and belongs where the store is described.
    """
    from fractal_wallpapers.palettes import codebook, dominance

    runs: dict = {}
    partitions: dict = {}
    locations: set = set()
    for row in _stream_of(Path(path)):
        run = str(row["provenance"]["run"])
        runs[run] = runs.get(run, 0) + 1
        partition = str(row.get("partition"))
        partitions[partition] = partitions.get(partition, 0) + 1
        locations.add(str((row.get("location") or {}).get("key")))
    return {
        "runs": dict(sorted(runs.items())),
        "partitions": dict(sorted(partitions.items())),
        "locations": len(locations),
        "colour": {
            "rule": dominance.RULE,
            "codebook": {
                "sigma": codebook.SIGMA,
                "swatches": len(codebook.names()),
                "census_size": list(codebook.CENSUS_SIZE),
            },
        },
        "engine": UNKNOWN_ENGINE,
    }


def durable_rows() -> durability.Durable:
    """The ledger as a [`durability.Durable`] — how it is saved, checked, restored."""
    return durability.Durable(
        name="the candidate ledger",
        live=rows_path(),
        copy=backup_path(ROWS_NAME),
        manifest=manifest_dir() / "rows.manifest.json",
        why_not_tracked=(
            "one row per recipe at about a kilobyte and a half a row, which is tens of "
            "megabytes against a 1 MiB per-file history guard, and rewritten whole on every "
            "backfill because the store upserts by key. The manifest is what the history "
            "keeps; the bytes live on both tiers."
        ),
        save_command="fractal-wallpapers curate candidate-ledger save",
        restore_command="fractal-wallpapers curate candidate-ledger restore",
        rebuild_command="fractal-wallpapers curate candidate-ledger backfill",
        facts=_facts,
    )


def durable_scores() -> durability.Durable:
    """The score sidecar as a [`durability.Durable`]."""
    return durability.Durable(
        name="the candidate ledger's scores",
        live=scores_path(),
        copy=backup_path(SCORES_NAME),
        manifest=manifest_dir() / "scores.manifest.json",
        why_not_tracked=(
            "one row per recipe per judge artifact, so it grows with the ledger and again "
            "with every judge this project ships. Same guard, same answer as the rows."
        ),
        save_command="fractal-wallpapers curate candidate-ledger save",
        restore_command="fractal-wallpapers curate candidate-ledger restore",
        rebuild_command="fractal-wallpapers curate candidate-ledger backfill",
        facts=lambda path: {},
    )


# --------------------------------------------------------------------------- #
# The rows.
# --------------------------------------------------------------------------- #
def row(
    *,
    recipe: recipes.Recipe,
    key: str,
    source: dict,
    also_rendered: list = (),
    also_recorded: list = (),
    colour: dict | None = None,
    picture: str | None = None,
    rejected: dict | None = None,
) -> dict:
    """One ledger row: a recipe, where it stands, what colour it is, who made it.

    `source` is the decision row this was read from — its own `location` block,
    its `key`, its run and candidate.

    The two lists beside it are different facts and are counted apart, because
    conflating them costs the ledger the number it exists to report.
    `also_rendered` is every *other render* that digests to this recipe: seconds
    a pass spent on a picture another pass already had, and the thing a cache
    prevents. `also_recorded` is every other decision **row** about the render
    this one names — a pass writes a gate row for the attempt and a release row
    for the seat, one picture, two decisions — and is what a protection joining a
    recipe back to its seat reads.

    ## The row carries what a reader consumes, and two invariants

    It was three kilobytes and is now about half of that. What came off was
    derived from the reader sites and not from a field list: `colour.cell_shares`
    and `colour.family_shares`, which every consumer skips in favour of the
    already-thresholded `cells`/`families`; the fields stored twice
    (`recipe_key`, `regime`, `palette_group`, and `location`'s copy of the
    recipe's `family`, `viewport` and `maxiter`); and the fields nothing reads at
    all (`location.frame_key`, `location.ledger`, `location.framing`,
    `location.superseded_by`, `provenance.store`, `provenance.source_key`,
    `provenance.engine`, and the `hunt` block's copies of the mode, the colormap
    and the draw's own bookkeeping).

    Two things it must always be able to do, and both are what the `recipe` block
    is here whole for:

    * **The recipe key stays recomputable.** [`recipes.of_row`] rebuilds the
      dataclass off `recipe` alone and [`recipes.key_of`] digests it back to
      `key`. `tests/test_candidate_ledger.py` holds that over the live store.
    * **The picture stays re-renderable from the row alone.** The same rebuilt
      recipe is [`recipes.Recipe.row`], which is the engine spec.

    Everything derived is derived rather than stored — `at_candidate_regime` is
    the one exception, because it is a bare boolean, five readers take it, and a
    pool that silently came back **empty** is how the last attempt at this row
    was noticed.
    """
    location = source.get("location") or {}
    place = location.get("key")
    return {
        "schema": SCHEMA,
        "key": str(key),
        "partition": location.get("partition"),
        "location": {
            # The recorded identity: what the one-wallpaper-per-location cap
            # counts on, and what a refinement deliberately does NOT move.
            "key": place,
            # Whether the pixels are of the frame that identity names. The frame's
            # own key was here beside it and is not any more: it is
            # `_frame_key(recipe)` and nothing read it, while this is a bare
            # boolean the census reports and re-deriving it would put a
            # `location_key` call on every row of a sweep.
            "agrees": place == _frame_key(recipe),
        },
        "recipe": recipe.record(),
        "at_candidate_regime": recipes.is_candidate_regime(recipe),
        "colour": colour_kept(colour),
        "provenance": {
            "run": source.get("run"),
            "candidate": source.get("candidate"),
            "also_rendered": list(also_rendered),
            "also_recorded": list(also_recorded),
        },
        "picture": picture,
        "rejected": rejected,
    }


def colour_kept(colour: dict | None) -> dict | None:
    """One colour block as the row stores it: the two thresholded lists, no shares.

    Takes a block rather than a [`palettes.dominance.Reading`] so that a colour
    *carried* from a row written under the old shape is cut the same way a fresh
    read is. `None` in, `None` out — a recipe with no picture has no colour, and
    an empty block would say something different.
    """
    if not colour:
        return None
    return {
        "cells": list(colour.get("cells") or []),
        "families": list(colour.get("families") or []),
    }


def live_artifact() -> str:
    """The sha256 of the judge shipped right now. What a score has to be read on."""
    from fractal_wallpapers.curation import floors

    return floors.live_stamp(floors.SCORING_HEAD)


def scores_by_recipe(scores=None, artifact: str | None = None, regime: str | None = None) -> dict:
    """`{recipe key: score row}` for **one** judge artifact, refusing a mixed read.

    The sidecar is keyed `(recipe key, artifact, regime)` precisely because a
    number is comparable only inside that triple. A join that flattened it to the
    recipe key alone would be last-row-wins across artifacts: two judges' scales
    in one ordering, with nothing anywhere saying so. Today the store holds one
    artifact and one regime, so such a join is right by luck; the first adoption
    is what turns luck into a silent wrong answer, and an adoption is a thing
    this project plans to do.

    So the artifact is named — `None` means the live head — and a row read on any
    other is **left out**, counted, and reported by [`stale_scores`]. Omitted and
    not silently rescaled: a recipe with no reading on the live judge has no
    score, which is a different and honest thing from having an old one.
    """
    read = read_scores() if scores is None else list(scores)
    want = live_artifact() if artifact is None else str(artifact)
    return {
        str(row["recipe_key"]): row
        for row in read
        if str(row.get("judge_artifact")) == want
        and (regime is None or str(row.get("regime")) == str(regime))
    }


def stale_scores(scores=None, artifact: str | None = None) -> dict:
    """What a join on the live judge leaves behind: `{artifact: rows}`.

    A census and not a warning. A store holding two artifacts is the ordinary
    state after an adoption — the old readings are kept, because a picture read
    by two judges is two facts — and this is how a caller says how much of its
    population it is about to have no score for.
    """
    read = read_scores() if scores is None else list(scores)
    want = live_artifact() if artifact is None else str(artifact)
    out: dict = {}
    for row in read:
        held = str(row.get("judge_artifact"))
        if held != want:
            out[held] = out.get(held, 0) + 1
    return dict(sorted(out.items(), key=lambda item: -item[1]))


def present_pictures(rows=None) -> set:
    """`{key}` for every row whose picture is **on disk**, as one batched pass.

    THE answer to "does this row still have a picture", and the only one: naming
    a picture and having one are different questions, and `curate retention` made
    the difference 30,040 rows wide by design — rows are never dropped, pictures
    are. A reader that asks the row is asking the wrong half.

    Two things make this affordable enough to sit in `solve.pool`, which every
    seating and every headroom census runs. `rehome` is called with one shared
    [`Tiers`] snapshot rather than resolving the settings per row — 1.0 s over
    the store against 215 s. And existence is answered by listing each pictures
    directory once instead of stat-ing each file: the 128,368 rows live in 21
    directories, which is 2.6 s of `scandir` against 12.8 s of `is_file`. Both
    numbers are this store on this machine, 2026-08-28.

    A row that names nothing, or whose name has no artifacts component for
    `rehome` to read, is absent — there is no picture either way.
    """
    import os
    from collections import defaultdict

    from fractal_wallpapers.paths import Tiers, rehome

    stored = read() if rows is None else rows
    tiers = Tiers.current()
    homed: dict = {}
    wanted: dict = defaultdict(set)
    for row in stored:
        named = row.get("picture")
        if not named:
            continue
        where = rehome(named, tiers)
        if where is None:
            continue
        homed[str(row["key"])] = where
        wanted[where.parent].add(where.name)

    listing: dict = {}
    for directory in wanted:
        try:
            listing[directory] = {entry.name for entry in os.scandir(directory)}
        except OSError:
            listing[directory] = set()
    return {key for key, where in homed.items() if where.name in listing.get(where.parent, ())}


def picture_census(rows=None) -> dict:
    """How many rows name a picture that is not there, by mode and by run.

    Permanent, expected state rather than damage: [`curation.retention`] keeps
    every row and drops the picture of everything outside the top five per
    (location, mode), the labeled, and a one-in-200 reservoir. This is the reader
    that state was missing — without it the only way to notice was a seating
    behaving oddly, which is how it was in fact noticed.
    """
    stored = read() if rows is None else rows
    present = present_pictures(stored)
    by_mode: dict = {}
    by_run: dict = {}
    absent = 0
    for row in stored:
        gone = str(row["key"]) not in present
        absent += gone
        mode = str((row.get("recipe") or {}).get("mode") or "?")
        run = str((row.get("provenance") or {}).get("run") or "?")
        for table, name in ((by_mode, mode), (by_run, run)):
            seen = table.setdefault(name, {"rows": 0, "absent": 0})
            seen["rows"] += 1
            seen["absent"] += gone
    for table in (by_mode, by_run):
        for seen in table.values():
            seen["share"] = round(seen["absent"] / seen["rows"], 4) if seen["rows"] else 0.0
    return {
        "schema": SCHEMA,
        "rows": len(stored),
        "with_a_picture_on_disk": len(present),
        "naming_a_picture_that_is_absent": absent,
        "share_absent": round(absent / len(stored), 4) if stored else 0.0,
        "policy": (
            "expected: `curate retention` drops pictures and never rows. An absent "
            "picture is not damage, and `curate candidate-ledger backfill` will not "
            "bring it back — only a re-render will."
        ),
        "by_mode": dict(sorted(by_mode.items(), key=lambda item: -item[1]["absent"])),
        "by_run": dict(sorted(by_run.items(), key=lambda item: -item[1]["absent"])),
    }


def k_of(row: dict) -> int | None:
    """Which candidate at its location this row was, or `None` where it cannot say.

    The `k` a planner stamps in the row's `hunt` block. It is **additive**: the
    85,129 rows written before the stamp existed carry no `k` at all, and a
    reader that treated a missing one as 1 would report the whole of that history
    as unselected first draws and under-correct every winner's-curse estimate
    over it. `None` is the honest answer and a caller has to decide what to do
    with it.
    """
    held = (row.get("hunt") or {}).get("k")
    try:
        return None if held is None else int(held)
    except (TypeError, ValueError):
        return None


def _frame_key(recipe: recipes.Recipe) -> str | None:
    """The location identity of the frame a recipe was drawn at, spelled as stored.

    Through [`supply.location.location_key`], which is this project's one answer
    to "the same location", and serialized the way the decision rows already
    serialize it so the two are comparable as strings.
    """
    from fractal_wallpapers.supply import location as location_module

    try:
        return json.dumps(list(location_module.location_key(recipe.family, recipe.viewport)))
    except (KeyError, TypeError, ValueError):
        return None


def _framing(block: dict | None) -> dict | None:
    """The refine leg's verdict, thinned to what a re-key later needs.

    Both frames and which one was used. The scores that decided it stay on the
    decision row: this store is about pictures, and a framing's `P(>=4)` is about
    a location.
    """
    if not block:
        return None
    return {
        "adopted": bool(block.get("adopted")),
        "used": block.get("used"),
        "original_viewport": (block.get("original") or {}).get("viewport"),
        "refined_viewport": (block.get("refined") or {}).get("viewport"),
    }


def score_row(*, key: str, artifact: str, regime: str, head: str, read: dict, source: dict) -> dict:
    """One reading of one recipe by one judge artifact at one regime.

    Keyed on the three of them together, because that triple is what a number is
    only comparable within. `block` says whether this is what the run read on the
    night it ran or a later re-score's reading of the same picture — the same
    distinction [`records.live_reading`] draws, kept rather than collapsed.
    """
    return {
        "schema": SCHEMA,
        "key": f"{key}|{artifact}|{regime}",
        "recipe_key": str(key),
        "judge_artifact": str(artifact),
        "regime": str(regime),
        "head": str(head),
        "p_ge2": read.get("p_ge2"),
        "p_ge3": read.get("p_ge3"),
        "p_ge4": read.get("p_ge4"),
        "rank_score": read.get("rank_score"),
        "block": "scores_current" if source.get("scores_current") else "scores",
        "read_by": {"run": source.get("run"), "candidate": source.get("candidate")},
    }


# --------------------------------------------------------------------------- #
# Reading and writing.
# --------------------------------------------------------------------------- #
def stream(path: Path | None = None):
    """Every ledger row, one at a time, in key order. **The reader.**

    Streaming rather than reading whole, which is what this was until
    2026-08-29. `read` built the whole file into one string, split it, and kept
    366,236 dictionaries: 46.5 s and several gigabytes of peak, paid fourteen
    times in a session by readers that each wanted a handful of fields per row.
    A generator costs one line at a time, and a caller that genuinely needs the
    list still says so by calling [`read`].

    An absent file yields nothing rather than raising: a checkout that has never
    backfilled is a state and not a failure, and every caller here already treats
    an empty ledger as one.
    """
    where = rows_path() if path is None else Path(path)
    yield from _stream_of(where)


def stream_scores(path: Path | None = None):
    """Every sidecar row, one at a time, in key order."""
    yield from _stream_of(scores_path() if path is None else Path(path))


def read(path: Path | None = None) -> list[dict]:
    """Every ledger row on record, in key order, as a list.

    Off [`stream`], so the 1.1 GB intermediate string is gone even here. A
    caller that only sweeps the rows once should take the stream: this holds
    every row at once because that is what its name promises.
    """
    return list(stream(path))


def read_scores(path: Path | None = None) -> list[dict]:
    """Every sidecar row on record, in key order."""
    return list(stream_scores(path))


def by_key(keys, path: Path | None = None) -> dict:
    """`{key: row}` for the keys asked for, in one streamed pass. **The lookup.**

    For a caller that wants a handful of rows out of a store of hundreds of
    thousands — the release render behind a solve's seats is a hundred and fifty
    of them. It stops as soon as it has them all, so a seat set that happens to
    sit early in key order costs a fraction of the file and never costs more than
    one pass of it.
    """
    wanted = {str(key) for key in keys}
    out: dict = {}
    for row in stream(path):
        key = str(row["key"])
        if key in wanted:
            out[key] = row
            if len(out) == len(wanted):
                break
    return out


def _stream_of(path: Path):
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write(rows) -> tuple[Path, int, int]:
    """Merge `rows` into the ledger by key. `(path, total, new)`. **Internal.**

    [`records.upsert_file`], which is what every other flat store here is written
    with: same key, same ordering, and a re-backfill over an unchanged pool
    writes byte-identical output.

    Every caller outside this module goes through [`merge`] instead, and
    `tests/test_ledger_tracking.py` is what holds that: this writes the bytes and
    says nothing about them, and a store written without being recorded is the
    era this module just spent.
    """
    path = rows_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


def write_scores(rows) -> tuple[Path, int, int]:
    """Merge score readings into the sidecar by key. `(path, total, new)`. **Internal.**"""
    path = scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    total, new = records.upsert_file(path, rows)
    return path, total, new


def merge(rows, scores, log=print) -> dict:
    """Upsert rows and score readings into the two files, and **record both**.

    THE door. Every leg that adds to the ledger — a hunt, a mine, a depth run,
    the backfill — comes through here, and there is one body rather than four
    copies of an upsert followed by a save each of them has to remember.

    **The tracking is the point.** The manifests are the only thing about this
    store the history keeps, and they went stale for an era: three merge legs and
    the backfill all wrote the rows and none of them recorded what they wrote, so
    the manifest said 16,006 rows against 128,368 live and `curate
    candidate-ledger check` could only ever answer `grown`. A writer that has to
    remember to record is a writer that will stop, so the record is not something
    a caller does afterwards — it is the second half of the write.

    **And the flatness sidecar is filled here, for the same reason.** It is keyed
    on the recipe and nothing else fills it, so a leg that merged and stopped left
    every row it wrote **unranked** to [`curation.rank_key`] — which is what
    `curate seat` orders on by default. Unranked rows sort last and are never
    refused, so they sat in the pool, cleared their bars, counted in every
    denominator, and could not win a seat while a ranked row was left:
    `mine1h` merged 8,192 rows and seated none of them, silently. The sweep is
    incremental and reads only pictures the sidecar has never seen — 33 s for
    those 8,192 — so a merge with nothing new to read pays one file read.

    The **copy** goes with the manifest, because that is what the manifest is a
    claim about: [`durability.save`] writes both or neither, and a manifest naming
    a count no copy holds would make [`durability.restore`] believe a stale file.
    That is the whole cost of this — one copy of each file per leg, at the end of
    a leg measured in minutes or hours.
    """
    from fractal_wallpapers.curation import flatness

    rows_file, total, new = write(rows)
    scores_file, score_total, score_new = write_scores(scores)
    swept = flatness.sweep(flatness.of_rows(rows), log=log)
    saved = {
        "rows": durability.save(durable_rows(), log=log),
        "scores": durability.save(durable_scores(), log=log),
    }
    return {
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
        "ledger": {"rows": total, "new": new},
        "scores": {"rows": score_total, "new": score_new},
        "flatness": {
            "column": swept["column"],
            "swept": swept["swept"],
            "read": swept["read"],
            "unreadable": swept["unreadable"],
            "seconds": swept["seconds"],
        },
        "recorded": {
            "rows": saved["rows"]["rows"],
            "scores": saved["scores"]["rows"],
            "manifests": [
                tracked_name(durable_rows().manifest),
                tracked_name(durable_scores().manifest),
            ],
        },
    }


#: How many rows one (location, `recipe.mode`) pair keeps in the retained
#: ledger, ranked by the shipped [`curation.rank_key`].
#:
#: **Three**, settled on the replay in `PRUNE1_replay_bestk_report.md`: at K=3
#: the solve at n=150 reproduced the full pool's seats exactly, and at K=2 it did
#: not. It is not [`retention.KEEP_PER_PAIR`] and must not be confused with it —
#: that one is five and it is how many **pictures** a pair keeps. A row is much
#: cheaper than a picture and a row is what recipe dedup reads, so the two
#: numbers are about different things and are allowed to differ.
RETAIN_PER_PAIR = 3

#: Why a row is in the retained ledger. The first is [`retention.RANKED`]; the
#: four after it are the protections, and each one keeps a row the rank let go.
RETAINED_RANKED = "ranked"
RETAINED_SEATED = "seated_in_a_live_release_row"
RETAINED_REJECTED = "carries_a_human_rejected_verdict"
RETAINED_LABELED = "a_label_row_joins_to_it"
RETAINED_FITTED = "named_by_the_rank_key_population"
RETAINED_REASONS = (
    RETAINED_RANKED,
    RETAINED_SEATED,
    RETAINED_REJECTED,
    RETAINED_LABELED,
    RETAINED_FITTED,
)


def compacted(wide: dict) -> dict:
    """One row of the wide ledger in the shape [`row`] writes now.

    A projection and not a rebuild: every field it keeps is copied across unread,
    so a row that comes out of here is the row that went in with the unread half
    removed. `location.agrees` and `at_candidate_regime` are carried rather than
    recomputed for that reason — recomputing them would let this quietly
    *re-decide* something the wide row had already recorded, over a store nothing
    can go back and check.
    """
    location = wide.get("location") or {}
    provenance = wide.get("provenance") or {}
    out = {
        "schema": SCHEMA,
        "key": str(wide["key"]),
        "partition": wide.get("partition"),
        "location": {"key": location.get("key"), "agrees": bool(location.get("agrees"))},
        "recipe": wide.get("recipe"),
        "at_candidate_regime": bool(wide.get("at_candidate_regime")),
        "colour": colour_kept(wide.get("colour")),
        "provenance": {
            "run": provenance.get("run"),
            "candidate": provenance.get("candidate"),
            "also_rendered": list(provenance.get("also_rendered") or []),
            "also_recorded": list(provenance.get("also_recorded") or []),
        },
        "picture": wide.get("picture"),
        "rejected": wide.get("rejected"),
    }
    if wide.get("hunt"):
        out["hunt"] = hunt_block(wide["hunt"])
    return out


def hunt_block(named: dict | None) -> dict:
    """The `hunt` block as the row keeps it: the seconds, and which draw this was.

    Two fields of nine. `seconds` is what [`headroom.render_cost`] prices a leg
    off; `k` is what [`k_of`] hands the winner's-curse correction, and it is the
    one field of the block that cannot be recovered from anywhere else. The other
    seven were the leg's name (which is `provenance.run`), its mode and its
    colormap (which are the recipe's), and four numbers about the draw that only
    the leg's own record ever read.
    """
    return {"seconds": (named or {}).get("seconds"), "k": (named or {}).get("k")}


def retain(keep: int = RETAIN_PER_PAIR, log=print) -> dict:
    """Build the retained ledger and both its sidecars beside the wide ones.

    **Deletes nothing.** The wide ledger, its two sidecars and every picture stay
    exactly where they are; this writes three new files under [`RETAINED`], and
    the readers reach them because [`LIVE`] says so.

    The rule is top-`keep` per (location, `recipe.mode`) ranked by the shipped
    [`curation.rank_key`], through [`retention.decide`] rather than through a
    second selector — the same body that decides which pictures a pair keeps,
    handed rank values instead of a raw `P(>=4)`. Four protections keep a row the
    rank let go: a seat in a live release row, a human rejection, a human label
    joining it, and a row named by the rank key's own tracked population file,
    whose fit stops being reproducible if one of them goes.

    `decide`'s one-in-200 reservoir is **not** a fifth protection here and its
    rows are folded back into the dropped, counted. The reservoir exists so that
    a reject autopsy has pictures in the middle of the distribution; a row is not
    a picture, and the rule as settled names four.

    ## One transaction

    The three files are written to `.writing` names and renamed only once all
    three are whole. A sidecar pruned against a ledger that was never written
    would be a store of rows nothing joins to, and the half-written state is the
    one state this must not be able to leave behind.
    """
    import time

    from fractal_wallpapers.curation import flatness, retention

    started = time.time()
    wide = ledger_root(WIDE)
    live = ledger_root(RETAINED)
    if not (wide / ROWS_NAME).is_file():
        raise LedgerError(f"{wide / ROWS_NAME} is not there, so there is nothing to retain.")

    # ---- one pass to decide ------------------------------------------------- #
    meta = _retain_meta(wide, log=log)
    values, coverage = _retain_ranks(meta, log=log)
    stubs = [
        {"key": held["key"], "location": {"key": held["place"]}, "recipe": {"mode": held["mode"]}}
        for held in meta
    ]
    verdicts = retention.decide(stubs, values, None, keep=int(keep))
    protections = _retain_protections(meta, log=log)
    kept_because = dict.fromkeys(RETAINED_REASONS, 0)
    keys: set = set()
    for held in meta:
        key = held["key"]
        ranked = verdicts.get(key) == retention.RANKED
        because = [name for name in RETAINED_REASONS[1:] if key in protections[name]]
        if not ranked and not because:
            continue
        keys.add(key)
        kept_because[RETAINED_RANKED if ranked else because[0]] += 1
    saved = {
        name: sum(1 for key in protections[name] if verdicts.get(key) != retention.RANKED)
        for name in RETAINED_REASONS[1:]
    }
    log(f"[retain] {len(keys):,} of {len(meta):,} rows kept at K={int(keep)}; saved {saved}")

    # ---- one transaction to write ------------------------------------------- #
    live.mkdir(parents=True, exist_ok=True)
    names = (ROWS_NAME, SCORES_NAME, flatness.SIDECAR_NAME)
    temps = [live / f"{name}.writing" for name in names]
    written: dict = {}
    try:
        written["rows"] = _retain_rows(wide / ROWS_NAME, temps[0], keys)
        written["scores"] = _retain_sidecar(wide / SCORES_NAME, temps[1], keys)
        written["flatness"] = _retain_sidecar(wide / flatness.SIDECAR_NAME, temps[2], keys)
        for temp, name in zip(temps, names, strict=True):
            temp.replace(live / name)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        raise
    for name, record in written.items():
        log(f"[retain] {name}: {record['rows']:,} rows, {record['bytes']:,} bytes")

    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "keep_per_location_mode": int(keep),
        "wide": tracked_name(wide),
        "retained": tracked_name(live),
        "rank": coverage,
        "rows_read": len(meta),
        "rows_kept": len(keys),
        "kept_because": kept_because,
        "saved_by_a_protection": saved,
        "reservoir_folded_into_dropped": sum(
            1 for held in meta if verdicts.get(held["key"]) == retention.RESERVOIR
        ),
        "files": written,
        "seconds": round(time.time() - started, 1),
    }


def _retain_meta(wide: Path, log=print) -> list[dict]:
    """One streamed pass of the wide ledger into what the decision needs per row."""
    from fractal_wallpapers.curation import retention

    out: list[dict] = []
    for at, held in enumerate(_stream_of(wide / ROWS_NAME), start=1):
        colour = held.get("colour") or {}
        provenance = held.get("provenance") or {}
        out.append(
            {
                "key": str(held["key"]),
                "place": str((held.get("location") or {}).get("key")),
                "mode": str((held.get("recipe") or {}).get("mode")),
                "cells": tuple(colour.get("cells") or ()),
                "rejected": bool(held.get("rejected")),
                "render_key": retention.render_key_of(held),
                "seat": (str(provenance.get("run")), str(provenance.get("candidate"))),
                "also_recorded": tuple(
                    (str(named.get("run")), str(named.get("candidate")))
                    for named in (provenance.get("also_recorded") or ())
                ),
            }
        )
        if at % 100_000 == 0:
            log(f"[retain] {at:,} rows read")
    log(f"[retain] {len(out):,} rows read from {tracked_name(wide / ROWS_NAME)}")
    return out


class _Pooled:
    """What [`rank_key.features_for`] reads off a candidate, and nothing else."""

    __slots__ = ("cells", "key", "location", "mode", "p_ge3", "score")

    def __init__(self, held: dict, reading: dict):
        self.key = held["key"]
        self.location = held["place"]
        self.mode = held["mode"]
        self.cells = held["cells"]
        self.score = float(reading.get("p_ge4") or 0.0)
        self.p_ge3 = float(reading.get("p_ge3") or 0.0)


def _retain_ranks(meta: list, log=print) -> tuple[dict, dict]:
    """`({key: rank value}, coverage)` through the SHIPPED key, not a copy of it.

    A row the key cannot read — no reading on the live judge, no flatness — has
    no value here, and [`retention.decide`] ranks it last within its pair, which
    is [`curation.seating`]'s own convention for exactly that case.
    """
    from fractal_wallpapers.curation import flatness, intake, rank_key

    readings = scores_by_recipe(read_scores(scores_path(WIDE)))
    flat = flatness.by_recipe(flatness.read(ledger_root(WIDE) / flatness.SIDECAR_NAME))
    held = rank_key.load()
    pooled = [_Pooled(row, readings[row["key"]]) for row in meta if row["key"] in readings]
    features, gaps = rank_key.features_for(pooled, locations=intake.read_scores(), readings=flat)
    values = {name: held.score(row) for name, row in features.items()}
    log(f"[retain] {len(values):,} of {len(meta):,} rows carry a rank value; gaps {gaps}")
    return values, {
        "artifact": tracked_name(rank_key.artifact_path()),
        "fitted_at": held.document.get("fitted_at"),
        "columns": list(held.columns),
        "rows": len(meta),
        "with_a_live_score": len(pooled),
        "ranked": len(values),
        "unranked": len(meta) - len(values),
        **gaps,
    }


def _retain_protections(meta: list, log=print) -> dict:
    """`{reason: {keys}}` for the four things kept whatever the rank says."""
    from fractal_wallpapers.curation import rank_key, retention, served_locations

    index = served_locations.build()
    live: set = set()
    for held in index.rows:
        live.add((str(held.get("run")), str(held.get("candidate"))))
        source = held.get("source") or {}
        if source.get("run") is not None:
            live.add((str(source.get("run")), str(source.get("candidate"))))
    marked = retention.labeled_renders()
    fitted = {
        str(json.loads(line)["recipe_key"])
        for line in rank_key.population_path().read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    out = {
        RETAINED_SEATED: {
            held["key"]
            for held in meta
            if held["seat"] in live or any(named in live for named in held["also_recorded"])
        },
        RETAINED_REJECTED: {held["key"] for held in meta if held["rejected"]},
        RETAINED_LABELED: {held["key"] for held in meta if held["render_key"] in marked},
        RETAINED_FITTED: {held["key"] for held in meta if held["key"] in fitted},
    }
    named = ", ".join(f"{name} {len(found):,}" for name, found in out.items())
    log(f"[retain] protections: {named}; the population file names {len(fitted):,} recipe(s)")
    return out


def _retain_rows(source: Path, into: Path, keys: set) -> dict:
    """Stream the wide ledger into the retained one, compacting as it goes."""
    rows = 0
    with into.open("w", encoding="utf-8", newline="\n") as handle:
        for held in _stream_of(source):
            if str(held["key"]) not in keys:
                continue
            handle.write(json.dumps(compacted(held), ensure_ascii=False) + "\n")
            rows += 1
    return {"rows": rows, "bytes": into.stat().st_size}


def _retain_sidecar(source: Path, into: Path, keys: set) -> dict:
    """Stream one recipe-keyed sidecar into the retained ledger, its rows only."""
    rows = 0
    dropped = 0
    with into.open("w", encoding="utf-8", newline="\n") as handle:
        for held in _stream_of(source):
            if str(held.get("recipe_key")) not in keys:
                dropped += 1
                continue
            handle.write(json.dumps(held, ensure_ascii=False) + "\n")
            rows += 1
    return {"rows": rows, "dropped": dropped, "bytes": into.stat().st_size}


def save(log=print) -> dict:
    """Copy both files to the archive tier and write both manifests."""
    return {
        "rows": durability.save(durable_rows(), log=log),
        "scores": durability.save(durable_scores(), log=log),
    }


def check(log=print) -> dict:
    """Are both files whole, against what the manifests say they were."""
    return {
        "rows": durability.check(durable_rows(), log=log),
        "scores": durability.check(durable_scores(), log=log),
    }


def restore(force: bool = False, log=print) -> dict:
    """Bring both files back from the archive tier."""
    return {
        "rows": durability.restore(durable_rows(), force=force, log=log),
        "scores": durability.restore(durable_scores(), force=force, log=log),
    }


# --------------------------------------------------------------------------- #
# The backfill.
# --------------------------------------------------------------------------- #
def sources() -> list[dict]:
    """Every candidate on record in either store, each stamped with which one.

    The same two stores [`gallery.pool_rows`] reads, and read here **without its
    three exclusions**. A row this pass wrote, a row a person rejected and a row
    with no score are all candidates that were rendered, and the ledger's whole
    claim is that it holds every picture that exists.
    """
    out = []
    for stamped, rows in (
        (FROM_RELEASE, records.read_decisions(records.RELEASE)),
        (FROM_GALLERY, gallery_store.read()),
    ):
        for candidate in rows:
            out.append({**candidate, "_store": stamped})
    return out


def _picture_of(source: dict) -> Path:
    """Where one row's own candidate render is, whether or not it is still there."""
    from fractal_wallpapers.curation import rescore
    from fractal_wallpapers.curation import run as run_module

    return run_module.run_dir(str(source["run"])) / rescore.PICTURES / f"{source['candidate']}.jpg"


#: Which stage of a decision row is preferred as a render's own record where the
#: same render carries two. The attempt is what made the picture; the seat is a
#: verdict on it taken later, and the two carry the same recipe either way.
MADE_IT = "gate"


def renders_of(everything: list) -> tuple[dict, dict]:
    """`({picture id: [its rows]}, counts)` — the two stores collapsed onto renders.

    **Two collapses and not one**, because a render arrives on more rows than it
    was made times, in two different ways, and only one of them is a fact about
    the pool.

    A **re-stamp** is a row about a picture some *other* row made: a pass seats a
    standing candidate under its own id and names the row it decided over in
    `source`, so [`rescore.origin_of`] walks down to the render. 90 of the two
    stores' 16,029 rows are those, and they are dropped here — the pass that
    seated a picture is not the pass that paid for it.

    A **restatement** is one run's own render carrying two decision rows: a
    gallery pass writes a gate row for the attempt and a release row for the
    seat, same run, same candidate, one JPEG. 451 rows are those, and they are
    kept beside their render rather than dropped, because a solver joining a
    recipe back to the seat it took needs them.

    Collapsing only the first would have reported those 451 as duplicate renders
    — 577 where the real number is 126, which is the one number this whole store
    exists to make smaller.
    """
    from fractal_wallpapers.curation import rescore

    index = {str(candidate["key"]): candidate for candidate in everything}
    by_render: dict = {}
    counts = {"restamps": 0, "restated": 0}
    for source in everything:
        run, candidate = rescore.origin_of(source, index)
        if (str(source["run"]), str(source["candidate"])) != (run, candidate):
            counts["restamps"] += 1
            continue
        identity = f"{run}_{candidate}"
        if identity in by_render:
            counts["restated"] += 1
        by_render.setdefault(identity, []).append(source)
    for rows in by_render.values():
        rows.sort(key=lambda source: (str(source.get("stage")) != MADE_IT, str(source["key"])))
    return by_render, counts


def canonical_artifacts(candidates: list) -> dict:
    """`{spelling: the longest spelling of that artifact}` over the whole pool.

    A run record abbreviates a head stamp to sixteen hex characters and a floor
    carries all sixty-four, so one shipped artifact reaches this store under two
    names — and a sidecar keyed on the name as written would hold two rows for one
    judge and let a reader believe they were two readings. The prefix rule is
    [`rescore._same_artifact`]'s, applied once here rather than at every read.
    """
    from fractal_wallpapers.curation import rescore

    seen = {str(rescore.artifact_of(candidate) or "") for candidate in candidates}
    seen.discard("")
    longest = sorted(seen, key=len, reverse=True)
    return {name: next(full for full in longest if full.startswith(name)) for name in seen}


def backfill(recolour: bool = False, log=print) -> dict:
    """Build the ledger and the sidecar from every candidate that already exists.

    No renders: everything here is read off the two decision stores and off the
    pictures those stores point at. The colour read is the expensive half — about
    20 ms a picture — so a recipe whose colour is already on record keeps it
    unless `recolour` is set. A second backfill over an unchanged pool is
    seconds, and writes byte-identical output.
    """
    from fractal_wallpapers.palettes import groups as groups_module

    everything = sources()
    table = groups_module.member_groups()
    artifacts = canonical_artifacts(everything)
    by_render, counts = renders_of(everything)
    counts.update(
        {
            "rows_read": len(everything),
            "unreadable": 0,
            "renders": 0,
            "recipes": 0,
            "duplicate_renders": 0,
            "off_regime": 0,
            "rejected": 0,
            "recoloured": 0,
            "colour_carried": 0,
            "colour_missing": 0,
        }
    )
    held: dict = {}
    for identity in sorted(by_render):
        drawn = by_render[identity]
        try:
            recipe = recipes.of_decision(drawn[0], table)
        except recipes.RecipeError as refusal:
            counts["unreadable"] += 1
            log(f"[ledger] {drawn[0]['key']}: {refusal}")
            continue
        counts["renders"] += 1
        key = recipes.key_of(recipe)
        held.setdefault(key, (recipe, []))[1].append(drawn)

    known = {str(stored["key"]): stored for stored in read()}
    rows, scores = [], []
    for at, (key, (recipe, made)) in enumerate(sorted(held.items()), start=1):
        made.sort(key=lambda rows_: (str(rows_[0]["run"]), str(rows_[0]["candidate"])))
        every_row = [source for rows_ in made for source in rows_]
        primary = made[0][0]
        counts["duplicate_renders"] += len(made) - 1
        if not recipes.is_candidate_regime(recipe):
            counts["off_regime"] += 1
        rejected = next(
            (source.get("rejected") for source in every_row if source.get("rejected")), None
        )
        counts["rejected"] += bool(rejected)

        picture = next((p for p in (_picture_of(rows_[0]) for rows_ in made) if p.is_file()), None)
        colour, how = _colour_for(key, picture, known, recolour)
        counts[how] += 1
        rows.append(
            row(
                recipe=recipe,
                key=key,
                source=primary,
                also_rendered=[_named(rows_[0]) for rows_ in made[1:]],
                also_recorded=[
                    _named(source) for source in every_row if source["key"] != primary["key"]
                ],
                colour=colour,
                picture=None if picture is None else tracked_name(picture),
                rejected=rejected,
            )
        )
        scores.extend(_scores_for(key, recipe, every_row, artifacts))
        if at % 500 == 0:
            log(f"[ledger] {at}/{len(held)} recipes")

    counts["recipes"] = len(rows)
    counts["score_readings"] = len(scores)
    counts["locations"] = len({str((stored["location"] or {})["key"]) for stored in rows})
    counts["with_picture"] = sum(1 for stored in rows if stored["picture"])
    counts["recipe_only"] = counts["recipes"] - counts["with_picture"]
    written = merge(rows, scores, log=log)
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows_path": written["rows_path"],
        "scores_path": written["scores_path"],
        "stored": {
            "rows": written["ledger"]["rows"],
            "new": written["ledger"]["new"],
            "scores": written["scores"]["rows"],
            "scores_new": written["scores"]["new"],
        },
        "recorded": written["recorded"],
        **counts,
    }


def _named(source: dict) -> dict:
    """One decision row as another row's record points at it. Enough to join back."""
    return {
        "run": source.get("run"),
        "candidate": source.get("candidate"),
        "stage": source.get("stage"),
        "store": source.get("_store"),
        "source_key": source.get("key"),
    }


def _colour_for(key: str, picture: Path | None, known: dict, recolour: bool) -> tuple:
    """`(colour block, which counter to bump)` for one recipe.

    The read is [`palettes.dominance`], which is the project's one answer to what
    colour a picture is. **The rule and the codebook it was read under are on the
    manifest and not on the row**, which is where [`curation.colors`] puts them
    for the same reason: they are one sentence and one triple, identical on every
    row, and fifteen thousand copies of them is five megabytes of one constant.

    A cell holding less than [`codebook.SMALL_SHARE`]-scale noise is dropped at
    the same threshold `codebook.census` stores at. Thirty-seven of the
    forty-eight cells are below it on the median picture, and a cell at 1e-5 of a
    picture's colour cannot satisfy or violate any constraint that acts on it.
    """
    from fractal_wallpapers.palettes import dominance

    stored = known.get(key) or {}
    if not recolour and stored.get("colour"):
        return stored["colour"], "colour_carried"
    if picture is None:
        return None, "colour_missing"
    return colour_block(dominance.of_picture(picture)), "recoloured"


def colour_block(reading) -> dict:
    """One [`palettes.dominance.Reading`] as a ledger row stores it.

    Its own function because two writers make ledger rows — this backfill, off
    pictures that already exist, and [`curation.hunt`], off a picture it has just
    rendered — and a colour block written two ways is two stores wearing one
    name.

    **The share vectors are not in it.** They were, at 678 bytes a row and 236 MB
    over the store, and no reader ever opened one: every consumer — the pool, the
    ceiling, the census, the retention aggregates, the rank key's stratum — takes
    the already-thresholded `cells` and `families`, which is the reading
    [`palettes.dominance.RULE`] has already made. A share vector kept beside the
    verdict it produced is the verdict stored twice, once in a form nothing can
    act on.
    """
    return {"cells": list(reading.cells), "families": list(reading.families)}


def _scores_for(key: str, recipe: recipes.Recipe, drawn: list, artifacts: dict) -> list[dict]:
    """Every reading of this recipe that any of its renders carries.

    One row per (artifact, regime) and not one per render: two renders of one
    recipe read by one artifact are one reading, and the first of them is kept.
    A row whose artifact nothing can name is skipped rather than filed under a
    guess — [`rescore.artifact_of`] returns `None` for exactly that, and it is
    not the same fact as *stale*.
    """
    from fractal_wallpapers.curation import rescore

    out: dict = {}
    for source in drawn:
        artifact = artifacts.get(str(rescore.artifact_of(source) or ""))
        read = records.live_reading(source)
        if not artifact or read.get("p_ge3") is None:
            continue
        stamped = score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=records.kind_of(source),
            read=read,
            source=source,
        )
        out.setdefault(stamped["key"], stamped)
    return list(out.values())


# --------------------------------------------------------------------------- #
# The census: what we already own, over the axes constraints act on.
# --------------------------------------------------------------------------- #
#: The trivial first solve the feasibility read is taken against: twenty
#: wallpapers, one per location, the hard diversity radius, the colour ceiling and
#: the group cap as budgets, the mode floors soft. Not a default anything solves
#: at — a number to answer "would any of this bind" against.
FIRST_SOLVE = 20


def census(rows=None, n: int = FIRST_SOLVE, log=print) -> dict:
    """What the ledger holds, over the axes a constraint acts on. Decides nothing.

    Location x colour cell x mode x palette group, with the partition riding on
    the location because that is where it is already recorded. Every axis reports
    its fill **and its empties**: a solver's question is never how much material
    there is, it is which of its constraints has nothing to satisfy it with.
    """
    from fractal_wallpapers.palettes import dominance

    stored = read() if rows is None else list(rows)
    if not stored:
        raise LedgerError(
            "the ledger is empty, so there is nothing to take a census over. Run "
            "`fractal-wallpapers curate candidate-ledger backfill` first."
        )
    log(f"[census] {len(stored):,} rows")
    return {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "population": _population(stored),
        "locations": _locations(stored),
        "cells": _fill(stored, dominance.cells(), _cells_of),
        "families": _fill(stored, dominance.families(), _families_of),
        "modes": _fill(stored, _production_modes(), lambda row: [(row["recipe"] or {})["mode"]]),
        "groups": _fill(
            stored, _drawable_groups(), lambda row: [(row["recipe"] or {})["palette_group"]]
        ),
        "feasibility": feasibility(stored, n=n, log=log),
    }


def _population(stored: list) -> dict:
    runs: dict = {}
    partitions: dict = {}
    for stamped in stored:
        run = str((stamped.get("provenance") or {}).get("run"))
        runs[run] = runs.get(run, 0) + 1
        partition = str(stamped.get("partition"))
        partitions[partition] = partitions.get(partition, 0) + 1
    return {
        "recipes": len(stored),
        "with_picture": sum(1 for stamped in stored if stamped.get("picture")),
        "recipe_only": sum(1 for stamped in stored if not stamped.get("picture")),
        "off_regime": sum(1 for stamped in stored if not stamped.get("at_candidate_regime")),
        "rejected": sum(1 for stamped in stored if stamped.get("rejected")),
        "no_colour": sum(1 for stamped in stored if not stamped.get("colour")),
        "duplicate_renders": sum(
            len((stamped.get("provenance") or {}).get("also_rendered") or []) for stamped in stored
        ),
        "by_run": dict(sorted(runs.items())),
        "by_partition": dict(sorted(partitions.items())),
    }


def _locations(stored: list) -> dict:
    """How many places the ledger stands on, and how deep it stands on each."""
    per: dict = {}
    per_partition: dict = {}
    for stamped in stored:
        key = str((stamped.get("location") or {}).get("key"))
        per[key] = per.get(key, 0) + 1
        per_partition.setdefault(str(stamped.get("partition")), set()).add(key)
    depths = sorted(per.values())
    moved = sum(1 for stamped in stored if not (stamped.get("location") or {}).get("agrees"))
    return {
        "locations": len(per),
        "recipes_per_location": _spread(depths),
        "at_one_recipe": sum(1 for depth in depths if depth == 1),
        "locations_by_partition": {name: len(keys) for name, keys in sorted(per_partition.items())},
        "rows_whose_key_is_not_their_frame": moved,
    }


def _spread(values: list) -> dict:
    """Min, the quartiles, p90 and max of an already-sorted list of counts."""
    if not values:
        return {}

    def at(share: float):
        return values[min(len(values) - 1, int(share * len(values)))]

    return {
        "min": values[0],
        "p25": at(0.25),
        "median": at(0.5),
        "p75": at(0.75),
        "p90": at(0.90),
        "max": values[-1],
        "mean": round(sum(values) / len(values), 2),
    }


def _cells_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("cells") or [])


def _families_of(stored: dict) -> list:
    return list((stored.get("colour") or {}).get("families") or [])


def _fill(stored: list, axis, values_of) -> dict:
    """One axis: how many recipes and how many locations reach each of its values.

    Both counts, because they answer different questions. A cell fifty recipes
    carry at one location is a cell the one-wallpaper-per-location rule can only
    seat once, however many recipes stand behind it.
    """
    recipes_at = {name: 0 for name in axis}
    locations_at: dict = {name: set() for name in axis}
    unlisted: dict = {}
    none = 0
    for stamped in stored:
        values = values_of(stamped)
        if not values:
            none += 1
        for value in values:
            if value in recipes_at:
                recipes_at[value] += 1
                locations_at[value].add(str((stamped.get("location") or {}).get("key")))
            else:
                unlisted[value] = unlisted.get(value, 0) + 1
    ranked = sorted(recipes_at.items(), key=lambda item: (-item[1], item[0]))
    return {
        "axis": len(axis),
        "held": sum(1 for name in axis if recipes_at[name]),
        "empty": [name for name in axis if not recipes_at[name]],
        "recipes_carrying_none": none,
        "recipes": dict(ranked),
        "locations": {name: len(locations_at[name]) for name, _count in ranked},
        "not_on_the_axis": dict(sorted(unlisted.items())),
    }


def _production_modes() -> tuple:
    """Every mode a candidate row can be *in*, off the engine's own tiers.

    The census axis, and deliberately wider than [`_accepted_modes`]: a mode ruled
    niche keeps every row it ever made, and a census that stopped counting them
    would report the ledger shrinking on the day of a policy decision.
    """
    from fractal_wallpapers import engine

    return tuple(engine.production_modes())


def _accepted_modes() -> tuple:
    """Every mode a gallery may seat: what a mode floor is asked of."""
    from fractal_wallpapers.curation import mode_policy

    return tuple(mode_policy.accepted())


def _drawable_groups() -> tuple:
    """Every palette group the colorizer's pool can reach, through the group table.

    The pool is already one map per group — a pass records that as
    `palette_pool.collapsed` — so this is the pool's own size. Derived rather than
    assumed, because a group table that stopped collapsing would make the two
    differ and the census would go on reporting the wrong denominator.
    """
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    table = groups_module.member_groups()
    return tuple(sorted({groups_module.group_of(name, table) for name in colorize.pool(0)}))


def feasibility(stored: list, n: int = FIRST_SOLVE, log=print) -> dict:
    """Which of a trivial first solve's constraints could bind, on what we hold.

    Each entry says what the constraint needs, what the ledger offers, and whether
    the second is short of the first. Nothing here is a solve, and every entry
    says which kind of read it is: a constraint that cannot bind on the marginals
    can still bind jointly.
    """
    from fractal_wallpapers.curation import ceiling as ceiling_module
    from fractal_wallpapers.palettes import dominance

    locations = {str((row.get("location") or {}).get("key")) for row in stored}
    groups = {str((row.get("recipe") or {}).get("palette_group")) for row in stored}
    cell_allowance = int(ceiling_module.K * ceiling_module.CELL_SHARE * n) + 1
    family_allowance = int(ceiling_module.K * ceiling_module.FAMILY_SHARE * n) + 1
    cells_held = {name for row in stored for name in _cells_of(row)}
    families_held = {name for row in stored for name in _families_of(row)}
    colourless = sum(1 for row in stored if not _cells_of(row))
    return {
        "n": n,
        "one_wallpaper_per_location": {
            "needs": n,
            "holds": len(locations),
            "binds": len(locations) < n,
            "read": "marginal",
        },
        "distinct_places": _distinct_read(locations, n, log=log),
        "group_cap": {
            "cap": ceiling_module.GROUP_CAP,
            "needs": n,
            "holds": len(groups),
            "of_drawable": len(_drawable_groups()),
            "binds": len(groups) < n,
            "read": "marginal, and the loosest form of the cap: a second seat in a group "
            "is allowed when its pixel cloud is more than tau_group from every picture "
            "that group already seated",
        },
        "colour_ceiling": {
            "k": ceiling_module.K,
            "cell_allowance": cell_allowance,
            "family_allowance": family_allowance,
            "cells_held": len(cells_held),
            "cells_needed": -(-n // max(1, cell_allowance)),
            "families_held": len(families_held),
            "families_needed": -(-n // max(1, family_allowance)),
            "recipes_with_no_dominant_cell": colourless,
            "binds_on_cells": len(cells_held) < -(-n // max(1, cell_allowance)),
            "binds_on_families": len(families_held) < -(-n // max(1, family_allowance)),
            "note": "only a candidate DOMINANT in an over-allowance colour is refused, so "
            f"the {colourless:,} recipes dominant in no cell cannot be refused by it at all",
            "rule": dominance.RULE,
            "read": "marginal — the allowance is per seat and the walk is path-dependent",
        },
        "mode_floors": {
            "acts": "soft",
            # The floor is asked of the modes a gallery may seat, which is
            # [`curation.mode_policy.accepted`] and not the whole production
            # roster. The `modes` axis above stays at the full roster on purpose:
            # a niche mode keeps its rows and a census of the ledger counts them.
            "modes": len(_accepted_modes()),
            "modes_held": sum(1 for name in _accepted_modes() if _mode_count(stored, name)),
            "binds": False,
        },
    }


def _mode_count(stored: list, mode: str) -> int:
    return sum(1 for row in stored if (row.get("recipe") or {}).get("mode") == mode)


def _distinct_read(locations: set, n: int, log=print) -> dict:
    """Whether the ledger holds `n` places the pre-selection would call different.

    The rule itself and not an estimate: [`distinct.suppress`] at
    [`distinct.PRESELECT_RADIUS`] over the neutral descriptors, which is the walk
    a solve's pool is actually built through. It used to be the retired gallery
    pass's quality-weighted draw at its own wider radius, which asked about a rule
    nothing runs any more — a necessary condition has to be a condition of the
    program that will be solved.

    **The order is by key**, and that is a statement rather than a default. The
    walk keeps whichever of a near-cluster it is offered first, so an order
    changes *which* place survives but not how many do, and a census has no score
    to offer them by — it is a read over the whole ledger and a rank would have to
    pick a judge. [`distinct.preselect`] does have one and orders by it.
    """
    from fractal_wallpapers.curation import distinct, embeddings

    stored = embeddings.read()
    if not stored:
        return {
            "radius": distinct.PRESELECT_RADIUS,
            "embedded": 0,
            "read": "no embedding store",
        }
    embedded = {str(row["key"]) for row in stored}
    log(f"[census] {len(locations & embedded):,}/{len(locations):,} ledger locations are embedded")
    walk = distinct.suppress(sorted(locations), rows=stored)
    return {
        "radius": distinct.PRESELECT_RADIUS,
        "metric": distinct.METRIC,
        "embedded": len(locations & embedded),
        "unembedded": len(walk["unembedded"]),
        "needs": n,
        "distinct": len(walk["kept"]),
        "binds": len(walk["kept"]) < n,
        "refused_as_the_same_place": len(walk["refused"]),
        "read": "the pre-selection itself, over the ledger's places in key order",
    }


__all__ = [
    "FIRST_SOLVE",
    "FROM_GALLERY",
    "FROM_RELEASE",
    "LedgerError",
    "MADE_IT",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "UNIT",
    "UNKNOWN_ENGINE",
    "backfill",
    "canonical_artifacts",
    "census",
    "check",
    "colour_block",
    "colour_kept",
    "compacted",
    "hunt_block",
    "durable_rows",
    "durable_scores",
    "feasibility",
    "k_of",
    "live_artifact",
    "manifest_dir",
    "merge",
    "read",
    "read_scores",
    "stream",
    "stream_scores",
    "renders_of",
    "retain",
    "restore",
    "row",
    "rows_path",
    "save",
    "score_row",
    "scores_by_recipe",
    "scores_path",
    "sources",
    "stale_scores",
    "store_root",
    "write",
    "write_scores",
]
