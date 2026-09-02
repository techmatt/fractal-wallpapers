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
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers import engine_fingerprint
from fractal_wallpapers.curation import durability, gallery_store, recipes, records
from fractal_wallpapers.paths import archive_root, hot_root, rehome, tracked_name, under

#: The schema every ledger and sidecar row carries.
SCHEMA = 1

#: The subtree both files live in, under the regenerable tree.
UNIT = "candidate_ledger"

#: What the three files that make up the store are called. The flatness sidecar
#: is [`curation.flatness.SIDECAR_NAME`], beside these and pruned with them.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"

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


def rows_path() -> Path:
    """The ledger: one row per recipe."""
    return store_root() / ROWS_NAME


def scores_path() -> Path:
    """The score sidecar: one row per (recipe, judge artifact, regime)."""
    return store_root() / SCORES_NAME


def manifest_dir() -> Path:
    """The tracked directory the store's manifests live in."""
    return records.default_root() / UNIT


def backup_path(name: str) -> Path:
    """The durable copy, beside the gate store's and the sidecar's.

    Off a root rather than through `under()`, for [`durability`]'s reason: a copy
    that resolved through the tiers would land on the tier the original is
    already on, which is the one place a second copy is no use.

    Public because the sidecars beside this store are not all owned by it:
    [`curation.flatness`] keeps its own file in the same subtree and must put its
    copy in the same place, and a second spelling of this path is how one of them
    ends up backed up somewhere nothing looks.
    """
    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / UNIT / name


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
    texture_flat: bool = False,
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

    Everything derived is derived rather than stored — `at_candidate_regime` and
    `texture_flat` are the two exceptions, and for one reason each is a bare
    boolean nothing can re-derive from the row. The first: five readers take it,
    and a pool that silently came back **empty** is how the last attempt at this
    row was noticed. The second: it is the engine's own
    `RenderReport.texture_flat`, and re-deriving it costs a *render* — the picture
    is the only place the fact survives, and even then only as the absence of
    something. See [`fractal_wallpapers.curation.mode_policy.routed_mode`] for
    what a `True` means, and [`fractal_wallpapers.coloring.texture_flat`] for how
    the rows written before the engine reported it were filled in.

    It is deliberately **not** the flatness sidecar's shape
    ([`curation.flatness`]). That column is a reading of a picture by a rule that
    could be re-chosen, so it is keyed on the recipe and kept out of the row.
    This one has no constant to re-choose — the engine either had a span to
    normalize against or it did not — and it is measured blind to a dead texture
    layer by the sidecar, whose `flat16_1.0` reads 0.182 on the degenerate rows
    against 0.170 on the varying ones: a rank-swept smooth field has no dead
    space, so the column that measures dead space cannot see this.
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
        # Whether the coloring's texture layer said nothing, so this row routes as
        # smooth-with-rank. False on every mode that has no texture, which is
        # sixteen of the seventeen.
        "texture_flat": bool(texture_flat),
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
    a picture and having one are different questions, and the two-K era made the
    difference 30,040 rows wide by design. [`prune`] closed it — a picture goes
    with its row — but the question stays worth asking, because a row that names
    an absent picture is exactly what a half-finished prune leaves behind.

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


# --------------------------------------------------------------------------- #
# Putting back a picture the row still names.
# --------------------------------------------------------------------------- #
#: Where a re-render leg dumps the fields it shares inside one (location, mode),
#: and writes its record. Its own subtree under the regenerable tree rather than
#: a directory inside the store, because the store holds three files and a fourth
#: thing living beside them is how a sweep comes to read one.
RE_RENDER_UNIT = "re_render"

#: How many engines a re-render drives at once. **Three**, this machine's render
#: pool — the same number every leg here takes, and a rule about the desktop
#: rather than a tuning knob. The priority half is [`engine.run`]'s and needs
#: nothing here.
RE_RENDER_WORKERS = 3


def re_render_dir() -> Path:
    """The subtree one re-render leg owns: its dumped fields and its record."""
    return under("curation", RE_RENDER_UNIT)


def missing_pictures(rows=None) -> list[dict]:
    """Every row whose picture the store names and the disk does not have.

    **The rule and nothing but the rule.** A row is here because it survived
    [`prune`] and its JPEG is gone, and for no other reason — no bar, no mode
    roster, no clearing test. A picture is kept if and only if its row is, so a
    retained row with no picture is a store that disagrees with itself, whatever
    the row's score happens to be.
    """
    stored = read() if rows is None else list(rows)
    present = present_pictures(stored)
    return [row for row in stored if str(row["key"]) not in present and row.get("picture")]


#: One worker process's copy of the cyclic-colormap set, built on first use.
#: A module global because that is what a spawned worker keeps between tasks.
_CYCLIC: set | None = None


def render_pair(payload: dict) -> dict:
    """One (location, mode) pair's missing pictures, in a worker. **Module level.**

    A Windows pool *spawns*, so a closure over the work list would not pickle;
    this takes a plain dict and re-imports what it needs once per worker.

    The pair is the unit rather than the row because a shareable mode's field is
    dumped once per (location, mode) and every map at it after that is a recolour
    — so two rows of one pair rendered in two workers would each pay the dump,
    and would race to write it. One pair, one worker, one dump.
    """
    from fractal_wallpapers.curation import colorize, recipes

    # Read once per WORKER and not once per pair. A pool task is one (location,
    # mode) and there are thirty-two thousand of them; the cyclic set is a read
    # of the colormap library, and paying it per task put the pool's concurrency
    # at 1.42 of three workers — half the machine idle behind a file read.
    global _CYCLIC
    if _CYCLIC is None:
        _CYCLIC = colorize.cyclic()
    cyclic = _CYCLIC
    fields = Path(payload["fields"]) if payload.get("fields") else None
    out = {"made": 0, "failed": 0, "seconds": 0.0, "why": []}
    started = time.time()
    for job in payload["rows"]:
        stored = job["recipe"]
        row = {
            "family": stored["family"],
            "viewport": stored["viewport"],
            "maxiter": int(stored["maxiter"]),
        }
        try:
            colorize.render(
                row,
                str(stored["mode"]),
                str(stored["colormap"]),
                cyclic,
                Path(job["picture"]),
                level=True,
                fields=fields,
            )
        except Exception as failure:  # noqa: BLE001 — a failed render is a recorded fact
            out["failed"] += 1
            out["why"].append(f"{job['key']}: {failure!r}"[:200])
            continue
        out["made"] += 1
    out["seconds"] = round(time.time() - started, 3)
    out["recipes"] = recipes.SCHEMA
    return out


def re_render(
    limit: int | None = None,
    workers: int = RE_RENDER_WORKERS,
    share_fields: bool = True,
    log=print,
) -> dict:
    """Render every picture the store names and cannot find. Writes no row.

    The ledger's second invariant, run as a repair: **the picture stays
    re-renderable from the row alone**. `recipes.of_record` rebuilds the recipe
    off the row and `Recipe.row` is the engine spec, so a row that survived
    [`prune`] can always have its pixels put back — which is the argument the
    prune was taken on, and this is the first thing to ever test it at scale.

    **The same pixels, not similar ones.** Each row is checked before it is
    rendered: the recipe the render path derives — the palette knobs from the
    cyclic set, the autolevel stamp from the shipped band — is digested, and the
    row is rendered only if that digest is the row's own key. A row whose stored
    recipe and the live checkout disagree would otherwise get *different* pixels
    under its own name, which is worse than having no picture. Those are counted
    and reported, never rendered.

    Nothing here writes to the ledger, its sidecars or their manifests. The
    pictures are the only thing that moves, which is what makes this safe to run
    beside anything except another leg driving the same three engines.
    """
    import shutil
    from concurrent.futures import ProcessPoolExecutor

    from fractal_wallpapers.curation import colorize, recipes
    from fractal_wallpapers.labeling import finished
    from fractal_wallpapers.palettes import groups as groups_module

    started = time.time()
    wanted = missing_pictures()
    log(f"[re-render] {len(wanted):,} row(s) name a picture that is not on disk")

    # ---- the guard, before any engine runs ---------------------------------- #
    cyclic = colorize.cyclic()
    band = colorize.band()
    table = groups_module.member_groups()
    jobs = []
    refused = []
    for row in wanted:
        stored = row["recipe"]
        mode, colormap = str(stored["mode"]), str(stored["colormap"])
        try:
            again = recipes.key_of(
                recipes.Recipe(
                    family=stored["family"],
                    viewport=stored["viewport"],
                    maxiter=int(stored["maxiter"]),
                    regime=recipes.CANDIDATE_REGIME,
                    mode=mode,
                    mode_params={},
                    curve=colorize.CURVE,
                    colormap=colormap,
                    palette=finished.recipe(mirror=colormap not in cyclic),
                    autolevel=recipes.live_stamp(mode, band),
                    palette_group=groups_module.group_of(colormap, table),
                )
            )
        except Exception as failure:  # noqa: BLE001
            refused.append({"key": str(row["key"]), "why": repr(failure)[:160]})
            continue
        if again != str(row["key"]):
            refused.append({"key": str(row["key"]), "the_render_path_would_make": again})
            continue
        where = rehome(str(row["picture"]))
        if where is None:
            refused.append({"key": str(row["key"]), "why": "the stored name is not under the tree"})
            continue
        jobs.append(
            {
                "key": str(row["key"]),
                "picture": str(where),
                "recipe": stored,
                "pair": (str((row.get("location") or {}).get("key")), mode),
            }
        )
    log(f"[re-render] {len(jobs):,} reproduce their own key; {len(refused):,} refused")
    # ---- one task per (location, mode) -------------------------------------- #
    fields = re_render_dir() / "fields"
    if share_fields:
        fields.mkdir(parents=True, exist_ok=True)
    grouped: dict = {}
    for job in jobs:
        grouped.setdefault(job["pair"], []).append(job)
    if limit is not None:
        # **Whole pairs.** A pilot that sliced the job list in row order would take
        # one picture from each of many pairs, and a dumped field pays for itself
        # only across the maps that follow it — so such a pilot pays every dump
        # and amortises none of them, and prices a leg that does not exist. The
        # first pilot did exactly that and read 2.23 s a picture at 1.03 pictures
        # a pair against the leg's real 1.78.
        held: dict = {}
        taken = 0
        for pair, rows_of in grouped.items():
            if taken >= int(limit):
                break
            held[pair] = rows_of
            taken += len(rows_of)
        grouped = held
        jobs = [job for rows_of in grouped.values() for job in rows_of]
        log(f"[re-render] limited to {len(jobs):,} over {len(grouped):,} whole pair(s)")
    payloads = [
        {"fields": str(fields) if share_fields else None, "rows": held} for held in grouped.values()
    ]
    log(
        f"[re-render] {len(payloads):,} (location, mode) pair(s) over {int(workers)} worker(s); "
        f"{len(jobs) / max(1, len(payloads)):.2f} picture(s) a pair"
    )

    made = 0
    failed = 0
    why: list = []
    engine_seconds = 0.0
    with ProcessPoolExecutor(max_workers=int(workers)) as pool:
        for done, out in enumerate(pool.map(render_pair, payloads), start=1):
            made += out["made"]
            failed += out["failed"]
            engine_seconds += out["seconds"]
            why += out["why"][: max(0, 20 - len(why))]
            if done % 250 == 0 or done == len(payloads):
                wall = time.time() - started
                rate = made / max(1e-9, wall)
                left = (len(jobs) - made) / max(1e-9, rate)
                log(
                    f"[re-render] {made:,} of {len(jobs):,} made in {wall / 60:.1f} min "
                    f"({rate:.1f}/s, ~{left / 60:.0f} min left), {failed:,} failed"
                )

    shutil.rmtree(fields, ignore_errors=True)
    wall = time.time() - started
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "share_fields": bool(share_fields),
        "named_but_absent": len(wanted),
        "reproduce_their_own_key": len(jobs) if limit is None else None,
        "refused": refused[:20],
        "refused_count": len(refused),
        "asked": len(jobs),
        "made": made,
        "failed": failed,
        "why": why,
        "pairs": len(payloads),
        "workers": int(workers),
        "wall_seconds": round(wall, 1),
        "engine_seconds": round(engine_seconds, 1),
        "seconds_per_picture": round(engine_seconds / max(1, made), 4),
        "seconds_per_picture_is": "per ENGINE. Wall a picture is this over the concurrency",
        "concurrency": round(engine_seconds / max(1e-9, wall), 2),
    }
    path = re_render_dir() / "re_render.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(f"[re-render] {made:,} made, {failed:,} failed in {wall / 60:.1f} min")
    return record


#: How many pictures go through the judge between one checkpoint and the next.
#: A chunk is the finest safe interruption point a re-score has: the readings so
#: far are on disk, and a kill costs the chunk in flight and nothing else.
SCORE_CHUNK = 4096

#: The judge reads this many pictures at once. 7.4 ms a picture at 128 against
#: 8.3 at 64, over 512 of this store's own pictures on this machine's GPU,
#: 2026-08-31 — the pass is JPEG decode and not the forward, so the batch buys
#: little past here.
SCORE_BATCH = 128


def partial_scores_path() -> Path:
    """Where a re-score in flight keeps the chunks it has already read.

    Beside the sidecar and not inside it: a half-finished re-score is not a
    reading of the store, and a reader that joined on the live artifact would
    otherwise see a pool that grows while it is being read. [`rescore`] folds it
    in at the end and deletes it.
    """
    return store_root() / "scores.partial.jsonl"


def rescore(
    artifact: str | None = None,
    limit: int | None = None,
    batch: int = SCORE_BATCH,
    device: str = "auto",
    log=print,
) -> dict:
    """Read every row whose picture is on disk through the judge shipped now.

    **The step a judge adoption makes necessary and nothing else does.** Scores
    are keyed on `(recipe, artifact, regime)` and
    [`scores_by_recipe`] joins on the live artifact alone, so the morning after a
    flip this store holds a full set of readings and the pool is *empty* — every
    row omitted as read on a head that no longer ships. Nothing is overwritten:
    the retired artifact's rows stay where they are, because a picture read by
    two judges is two facts.

    A row with no picture on disk is skipped rather than guessed at, the same
    rule [`curation.rescore`] holds over the release pool. There is one judge for
    both kinds since 2026-08-23, so the head is loaded once; `head` on the row
    still says which kind's floor and slot the row belongs to.

    **Resumable by chunk.** Each [`SCORE_CHUNK`] pictures are appended to
    [`partial_scores_path`] as they are read, and a re-run skips what that file
    already holds. The sidecar itself is written once, at the end, through the
    same upsert every other writer uses.
    """
    import time

    from fractal_wallpapers.curation import colorize, durability, hunt

    started = time.time()
    want = live_artifact() if artifact is None else str(artifact)
    stored = read()
    present = present_pictures(stored)
    held = {
        str(row["recipe_key"]) for row in read_scores() if str(row.get("judge_artifact")) == want
    }
    done_partial = _partial_keys(want)
    wanted = [
        row
        for row in stored
        if str(row["key"]) in present
        and str(row["key"]) not in held
        and str(row["key"]) not in done_partial
    ]
    if limit is not None:
        wanted = wanted[: int(limit)]
    log(
        f"[rescore] {len(stored):,} row(s), {len(present):,} with a picture; "
        f"{len(held):,} already read on {want[:8]}, {len(done_partial):,} in the partial; "
        f"{len(wanted):,} to read"
    )
    if wanted:
        from fractal_wallpapers.models import scoring, train

        model, config, where = colorize.load_judge(device)
        transform = scoring.transform_of(config)
        classes = int(config["classes"])
        log(f"[rescore] judge on {where}, {classes} classes, batch {int(batch)}")
        for at in range(0, len(wanted), SCORE_CHUNK):
            chunk = wanted[at : at + SCORE_CHUNK]
            paths = [rehome(str(row["picture"])) for row in chunk]
            probabilities = train.score(
                model, paths, transform, where, classes, {"batch_size": int(batch)}
            )
            _append_partial(
                [
                    score_row(
                        key=str(row["key"]),
                        artifact=want,
                        regime=str((row["recipe"] or {})["regime"]),
                        head=hunt.kind_of(str((row["recipe"] or {})["mode"])),
                        read=_reading_of(probabilities[index]),
                        source={
                            "scores_current": True,
                            "run": (row.get("provenance") or {}).get("run"),
                            "candidate": (row.get("provenance") or {}).get("candidate"),
                        },
                    )
                    for index, row in enumerate(chunk)
                ]
            )
            read_so_far = at + len(chunk)
            wall = time.time() - started
            rate = read_so_far / max(1e-9, wall)
            left = (len(wanted) - read_so_far) / max(1e-9, rate)
            log(
                f"[rescore] {read_so_far:,} of {len(wanted):,} in {wall / 60:.1f} min "
                f"({rate:.0f}/s, ~{left / 60:.0f} min left)"
            )
    fresh = list(_stream_of(partial_scores_path()))
    path, total, new = write_scores(fresh)
    saved = durability.save(durable_scores(), log=log)
    partial_scores_path().unlink(missing_ok=True)
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact": want,
        "rows": len(stored),
        "with_picture": len(present),
        "already_held": len(held),
        "read": len(fresh),
        "sidecar_rows": total,
        "sidecar_new": new,
        "wall_seconds": round(time.time() - started, 1),
        "saved": saved,
        "scores_path": tracked_name(path),
    }
    log(
        f"[rescore] {len(fresh):,} reading(s) on {want[:8]} merged; sidecar holds "
        f"{total:,} row(s) in {record['wall_seconds'] / 60:.1f} min"
    )
    return record


def _reading_of(probabilities) -> dict:
    """One judge output as [`score_row`] takes it: every cutpoint, and the sum.

    [`curation.colorize.score_picture`]'s body over an already-scored row rather
    than a second spelling of it — the rank score is the sum of the unconditional
    cutpoints and a second derivation of that is a second scale.
    """
    row = {f"p_ge{index + 2}": float(value) for index, value in enumerate(probabilities)}
    row["rank_score"] = float(sum(float(value) for value in probabilities))
    return row


def _partial_keys(artifact: str) -> set:
    """The recipes a partial re-score of THIS artifact has already read."""
    return {
        str(row["recipe_key"])
        for row in _stream_of(partial_scores_path())
        if str(row.get("judge_artifact")) == str(artifact)
    }


def _append_partial(rows) -> None:
    """One chunk onto the partial file. Appended, so a kill costs one chunk."""
    path = partial_scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def picture_census(rows=None) -> dict:
    """How many rows name a picture that is not there, by mode and by run.

    **Nearly always zero now, and that is the change.** While the picture rule
    ran on its own ranking at its own K this was permanent expected state, 30,040
    rows wide; since 2026-08-29 a picture is kept if and only if its row is, so a
    row naming an absent picture is either one of the 41 the ledger inherited or
    a [`prune`] that was interrupted between its two halves. Either way this is
    the reader that says so — without it the only way to notice was a seating
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


# --------------------------------------------------------------------------- #
# The other direction: pictures on disk that no record names.
# --------------------------------------------------------------------------- #
#: The five subtrees under `curation` that hold pool pictures. Swept 2026-09-02
#: over 177,993 rows: `depth` 158,628 - `runs` 11,875 - `mine` 4,566 -
#: `reframe_draw` 2,283 - `hunt` 641, and **no row points anywhere else at all**.
#: The list is written down rather than discovered per call because it is what
#: bounds [`orphans`] — a sweep that found its own subtrees would follow the tree
#: wherever it grew.
POOL_SUBTREES = ("depth", "runs", "mine", "reframe_draw", "hunt")

#: What every leg calls the directory it keeps its candidates in. [`orphans`]
#: looks at `<subtree>/<leg>/pictures` and at **no other shape**, which is what
#: keeps it structurally unable to reach a leg's `fields/`, its `candidates/`,
#: its `release/` or a sheet, whatever any record says.
PICTURES_NAME = "pictures"


def picture_dirs() -> list[Path]:
    """Every `<pool subtree>/<leg>/pictures` there is, resolved through the tiers.

    A fixed shape at a fixed depth, not a walk: the directories are named rather
    than discovered, so the enumeration cannot follow the tree into somewhere
    that merely happens to hold JPEGs.
    """
    found = []
    for name in POOL_SUBTREES:
        base = under("curation", name)
        if not base.is_dir():
            continue
        for leg in sorted(base.iterdir()):
            where = leg / PICTURES_NAME
            if where.is_dir():
                found.append(where)
    return found


def _named_by_the_ledger(tiers) -> dict:
    """`{resolved pictures directory: {file name}}` for every picture a row names.

    Bucketed by directory and resolved through one shared [`paths.Tiers`]
    snapshot, for [`present_pictures`]'s reason: the alternative re-reads the
    settings once per row, which was 215 s against 1.0 s over this store.
    """
    from collections import defaultdict

    wanted: dict = defaultdict(set)
    for row in stream():
        named = row.get("picture")
        if not named:
            continue
        where = rehome(str(named), tiers)
        if where is not None:
            wanted[where.parent].add(where.name)
    return wanted


def _named_by_the_leg(leg: Path) -> set:
    """Every `.jpg` file name this leg's own records mention.

    A leg keeps records the ledger never sees — `sequence.jsonl`,
    `profile.jsonl`, `candidates.jsonl`, `screened.jsonl`, the plan files — and
    `curation/README.md` is explicit that those are measurement records rather
    than a feature store, recorded whole on purpose and read whole by things like
    `depth.contact_sheet`. A picture one of them names is therefore **not**
    unreferenced, whatever the ledger says about it.

    Deliberately a regex over the text rather than a schema-aware read. These
    records spell a picture several ways — the stored `artifacts/...` name, a
    name relative to the leg, a bare file name — and this question has a safe
    direction to be wrong in. Over-reading a name keeps a picture that could have
    gone; under-reading one deletes a picture something names.
    """
    import re

    pattern = re.compile(r"([A-Za-z0-9_.\-]+)\.jpg")
    found: set = set()
    for path in sorted(leg.rglob("*")):
        if PICTURES_NAME in path.parts[len(leg.parts) :]:
            continue
        if not path.is_file() or path.suffix not in (".json", ".jsonl"):
            continue
        try:
            with path.open(encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    found.update(f"{stem}.jpg" for stem in pattern.findall(line))
        except OSError:
            continue
    return found


def orphans(apply: bool = False, log=print) -> dict:
    """Pictures in the pool subtrees that **nothing** names. The backstop under [`prune`].

    [`prune`] is the retention rule and it runs from [`merge`], so every leg that
    finishes hands its candidates to the ledger and the rule bounds them from
    then on. A leg that is **killed** never reaches `merge`: its pictures are on
    disk, no row was ever written for them, and no later prune can free them,
    because a prune only ever decides about rows it can see. This is the only
    thing that can, and that is the whole reason it exists.

    ## What counts as named, and why the ledger is not the whole of it

    Two reference sets, unioned, and the second is what makes this safe to run:

    * every picture a **ledger row** names, resolved through the tiers;
    * every `.jpg` a **leg's own records** mention — see [`_named_by_the_leg`].

    The difference between them is neither small nor theoretical. Over this
    machine on 2026-09-02: 10,007 pictures carried no ledger row, and **9,983 of
    them were named by the leg that made them.** A sweep keyed on the ledger
    alone would have deleted all 10,007 and reported it as garbage collection.

    ## Where the safety actually lives

    Three places, none of them a promise made in a comment:

    * the enumeration is [`picture_dirs`], a fixed shape at a fixed depth, so a
      leg's `fields/` is not reachable however large it gets;
    * every directory is checked against the tier roots **here**, at the point of
      deciding, rather than trusted from whatever produced the list;
    * the deletion is [`delete_pictures`] and nothing else, which re-homes each
      name as it unlinks and leaves alone any name with no artifacts component.

    `apply=False` is the default and is the whole of the dry run. Costs a
    `scandir` per leg plus one streamed pass of the ledger and one of each leg's
    own records: about 35 s over this store.
    """
    import os
    from collections import Counter

    from fractal_wallpapers.paths import Tiers

    started = time.time()
    tiers = Tiers.current()
    roots = [Path(root).resolve() for root in (tiers.hot, tiers.archive) if root is not None]
    wanted = _named_by_the_ledger(tiers)

    by_subtree: dict = {}
    doomed: list = []
    ledger_only: Counter = Counter()
    for where in picture_dirs():
        # The check at the point of decision, and not carried over from the
        # enumeration. A directory that does not sit under a tier root is not
        # something this may reason about at all, whoever put it in the list.
        resolved = where.resolve()
        if not any(root == resolved or root in resolved.parents for root in roots):
            raise LedgerError(
                f"{where} is not under either tier root ({[str(root) for root in roots]}), "
                f"and this sweep deletes what it decides about. Nothing was read."
            )
        subtree = where.parent.parent.name
        cell = by_subtree.setdefault(
            subtree,
            {
                "legs": 0,
                "pictures": 0,
                "named_by_the_ledger": 0,
                "named_by_a_leg_record": 0,
                "named_by_nothing": 0,
                "bytes": 0,
            },
        )
        cell["legs"] += 1

        stems: dict = {}
        for entry in os.scandir(where):
            if entry.is_file(follow_symlinks=False) and entry.name.endswith(".jpg"):
                stems[entry.name] = entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False) and entry.name.endswith(".leveled"):
                # A levelled colormap whose JPEG is already gone is precisely the
                # pile, and it is addressed by the name its picture would have.
                stems.setdefault(f"{entry.name[: -len('.leveled')]}.jpg", 0)
        cell["pictures"] += len(stems)

        held = wanted.get(where, set())
        loose = {name for name in stems if name not in held}
        cell["named_by_the_ledger"] += len(stems) - len(loose)
        if not loose:
            continue
        ledger_only[subtree] += len(loose)
        mentioned = _named_by_the_leg(where.parent)
        unnamed = sorted(name for name in loose if name not in mentioned)
        cell["named_by_a_leg_record"] += len(loose) - len(unnamed)
        cell["named_by_nothing"] += len(unnamed)
        cell["bytes"] += sum(stems[name] for name in unnamed)
        doomed.extend(tracked_name(where / name) for name in unnamed)

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": bool(apply),
        "subtrees": list(POOL_SUBTREES),
        "by_subtree": dict(sorted(by_subtree.items())),
        "pictures_on_disk": sum(cell["pictures"] for cell in by_subtree.values()),
        "carrying_no_ledger_row": dict(sorted(ledger_only.items())),
        "named_by_nothing": len(doomed),
        "bytes_named_by_nothing": sum(cell["bytes"] for cell in by_subtree.values()),
    }
    log(
        f"[orphans] {record['pictures_on_disk']:,} pictures, "
        f"{sum(ledger_only.values()):,} with no ledger row, of which "
        f"{len(doomed):,} are named by nothing either"
    )
    if not apply:
        record["pictures"] = {"would_delete": len(doomed)}
        record["seconds"] = round(time.time() - started, 1)
        return record

    record["pictures"] = delete_pictures(doomed, log=log)
    record["seconds"] = round(time.time() - started, 1)
    return record


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
    """Upsert a leg's rows, record them, prune the store back to the rule.

    THE door. Every leg that adds to the ledger — a hunt, a mine, a depth run,
    the backfill — comes through here, and there is one body rather than four
    copies of an upsert followed by a save each of them has to remember. It is
    also the only door the retention rule needs to stand at.

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

    **And [`prune`] runs here, which is the half that makes the store bounded.**
    A merge is the only thing that grows this file, so it is the only place the
    rule has to act; anywhere else and a rule nothing runs is a rule the store
    stops obeying between the times somebody remembers it. Rows per (location,
    mode) cannot exceed [`RETAIN_PER_PAIR`] after this returns, and the pictures
    of the rows it drops are gone with them. Deciding is **18.4 s** over the
    122,516 rows standing on 2026-08-29, and rewriting the three files is about as
    much again — paid at the end of a leg measured in minutes or hours, which is
    the same trade the flatness sweep above it makes.

    The **copy** goes with the manifest, because that is what the manifest is a
    claim about: [`durability.save`] writes both or neither, and a manifest naming
    a count no copy holds would make [`durability.restore`] believe a stale file.
    It is written **after** the prune and not before: a manifest recording the
    pre-prune count would make [`durability.check`] read `short` on a store that
    is exactly what the rule says it should be.

    **All four files are recorded, not two.** The flatness sidecar is written by
    the sweep above and rewritten by the prune below, and for an era it was saved
    only when somebody ran `curate flatness save` by hand — so the one file whose
    absence silently unranks a merge's whole output was the one file the door did
    not record. The reduced-signature sidecar joined it for the weaker but real
    version of the same reason: nothing here fills it, but a restore without it
    re-derives 68.6 MB of readings the mirror could have copied. Note what this
    does *not* buy: `curate candidate-ledger check` still reads the rows and the
    scores alone, so a short or missing sidecar is not what makes that command
    exit 1. Extending it is a decision about what a build failure is, and it has
    not been taken here.
    """
    from fractal_wallpapers.curation import colorize, flatness, retention, signatures

    # Before the upsert, because it is a reading of what the store held BEFORE
    # this leg's own rows joined it — see [`retention.repeat_draws`].
    standing = retention.drawn_before(stream())
    repeated = retention.repeat_draws(rows, standing, pool=len(colorize.pool(0)))
    log(
        f"[ledger] {repeated['at_locations_with_deleted_rows']:,} of {len(rows):,} row(s) "
        f"land at a location holding deleted recipes; at most {repeated['bound']:,} and "
        f"about {repeated['expected']} of them are renders this project already paid for"
    )

    rows_file, total, new = write(rows)
    scores_file, score_total, score_new = write_scores(scores)
    swept = flatness.sweep(flatness.of_rows(rows), log=log)
    pruned = prune(log=log)
    saved = {
        "rows": durability.save(durable_rows(), log=log),
        "scores": durability.save(durable_scores(), log=log),
    }
    # The flatness sidecar is the third file of this store and the prune above
    # rewrites it, so it is recorded here with the other two rather than left to
    # `curate flatness save` by hand — which is the only reason its manifest was
    # ever current. Conditional where they are not, and the reason is not the
    # sweep: `flatness.sweep` writes no file when it read nothing, but `prune`
    # rewrites all three and runs between them, so the sidecar is here by now and
    # a merge that swept nothing records it empty. The test is what keeps
    # [`durability.save`]'s refusal — it raises on a file that is not there —
    # from turning a checkout that has never swept into a failed merge.
    if flatness.sidecar_path().is_file():
        saved["flatness"] = durability.save(flatness.durable(), log=log)
    # The reduced-signature sidecar is the fourth, and conditional for a stronger
    # version of the flatness sidecar's reason: nothing in a merge fills it, so on
    # a checkout that has never run `curate signatures sweep` there is no file at
    # all. Where there is one it is mirrored here rather than left to a restore to
    # re-derive over the three-worker pool, which is minutes for bytes a copy
    # already had.
    if signatures.sidecar_path().is_file():
        saved["signatures"] = durability.save(signatures.durable(), log=log)
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
        "repeat_draws": repeated,
        "pruned": pruned,
        "recorded": {
            "rows": saved["rows"]["rows"],
            "scores": saved["scores"]["rows"],
            "flatness": saved["flatness"]["rows"] if "flatness" in saved else None,
            "signatures": saved["signatures"]["rows"] if "signatures" in saved else None,
            "manifests": [
                tracked_name(durable_rows().manifest),
                tracked_name(durable_scores().manifest),
                *([tracked_name(flatness.durable().manifest)] if "flatness" in saved else []),
                *([tracked_name(signatures.durable().manifest)] if "signatures" in saved else []),
            ],
        },
    }


#: How many rows one (location, `recipe.mode`) pair keeps, ranked by the shipped
#: [`curation.rank_key`]. **The** constant: a picture is kept if and only if its
#: row is, so this bounds the pictures too and there is no second number.
#:
#: **Three**, settled on the replay in `PRUNE1_replay_bestk_report.md`: at K=3
#: the solve at n=150 reproduced the full pool's seats exactly, and at K=2 it did
#: not. It was one of two until 2026-08-29 — `retention.KEEP_PER_PAIR` kept five
#: **pictures** a pair by raw `P(>=4)`, on a different ranking, and the two were
#: not nested, so a row in the top three by rank could be sixth by `P(>=4)` and
#: have lost its picture. That second spelling is gone.
RETAIN_PER_PAIR = 3

#: Why a row survives [`prune`]. The first is [`retention.RANKED`]; the five
#: after it are the protections, and each one keeps a row the rank let go.
RETAINED_RANKED = "ranked"
RETAINED_SEATED = "seated_in_a_live_release_row"
RETAINED_REJECTED = "carries_a_human_rejected_verdict"
RETAINED_LABELED = "a_label_row_joins_to_it"
RETAINED_FITTED = "named_by_the_rank_key_population"
#: A seat in a **tentative gallery** — [`curation.tentative`] — which is a
#: recorded gallery somebody has started referring to pictures by. It protects
#: for the same reason a live release row does and needs its own class for a
#: sharper one: a seat is chosen on the gallery's objective, over a view, against
#: the colour rules, and none of that is being in the top three of its own
#: (location, mode) pair, so the rank drops these routinely. An ID that stopped
#: resolving would take its picture with it and there is no way to notice.
RETAINED_TENTATIVE = "seated_in_a_tentative_gallery"
RETAINED_REASONS = (
    RETAINED_RANKED,
    RETAINED_SEATED,
    RETAINED_REJECTED,
    RETAINED_LABELED,
    RETAINED_FITTED,
    RETAINED_TENTATIVE,
)


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


def prune(keep: int = RETAIN_PER_PAIR, apply: bool = True, log=print) -> dict:
    """Bring the store back to the settled rule. **Rows and their pictures, together.**

    Top-`keep` per (location, `recipe.mode`) ranked by the shipped
    [`curation.rank_key`], through [`retention.decide`] rather than a second
    selector — the same body the article teaches the rule with, handed rank values
    instead of a raw `P(>=4)`. Five protections keep a row the rank let go: a seat
    in a live release row, a human rejection, a human label joining it, a row named
    by the rank key's own tracked population file (whose fit stops being
    reproducible if one of them goes), and a seat in a **tentative gallery**,
    whose whole point is that its IDs stay resolvable.

    A dropped row loses **its picture in the same call**. That is the one rule
    now: until 2026-08-29 the pictures were swept on their own ranking at their
    own K and the two were not nested, so a row could be retained with its picture
    already gone. `pictures` says what this freed.

    ## The order is the safety property

    Pictures first, then the record transaction. A crash between them leaves rows
    naming pictures that are not there — which [`picture_census`] reports,
    `solve.pool` refuses, and a second `prune` repairs, because the ranking is a
    deterministic function of the rows. The other order leaves pictures nothing
    names, which is garbage no reader can find and no run can free.

    The three files are then written to `.writing` names and renamed only once all
    three are whole. A sidecar pruned against a ledger that was never written
    would be a store of rows nothing joins to, and the half-written state is the
    one state this must not be able to leave behind.

    `apply=False` reads and decides and touches nothing, which is what
    `fractal-wallpapers curate candidate-ledger prune --dry-run` is.
    """
    import time

    from fractal_wallpapers.curation import retention

    started = time.time()
    # Through the path accessors and never off `store_root()`, because those are
    # what a test redirects: `tests/test_candidate_ledger.isolated` moves the two
    # row files and the sidecar by name, and a prune that rebuilt the paths from
    # the root would read past the redirect into the real store and rewrite it.
    # It did exactly that once, on 2026-08-29, and cost 266 pictures.
    files = (rows_path(), scores_path(), _flatness_path())
    homes = {path.parent for path in files}
    if len(homes) != 1:
        # A REFUSAL and not a repair, because the shape it catches is a test that
        # redirected two of the three and left the third pointing at this
        # machine's real store — which would then be rewritten to hold only the
        # keys of a temporary one. That is not hypothetical: it happened on
        # 2026-08-29, and the sidecar is the one of the three that is reached
        # through another module and so the one a caller forgets.
        raise LedgerError(
            f"the store's three files are in {len(homes)} directories and a prune rewrites "
            f"all three against one set of keys: {[str(path) for path in files]}. Nothing "
            f"was read. If this is a test, redirect `flatness.sidecar_path` too."
        )
    if not files[0].is_file():
        raise LedgerError(f"{files[0]} is not there, so there is nothing to prune.")

    # ---- one pass to decide ------------------------------------------------- #
    meta = _prune_meta(files[0], log=log)
    values, coverage = _prune_ranks(meta, log=log)
    stubs = [
        {
            "key": held["key"],
            "location": {"key": held["place"]},
            "recipe": {"mode": held["mode"]},
            "picture": held["picture"],
        }
        for held in meta
    ]
    verdicts = retention.decide(stubs, values, keep=int(keep))
    protections = _prune_protections(meta, log=log)
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
    log(f"[prune] {len(keys):,} of {len(meta):,} rows kept at K={int(keep)}; saved {saved}")

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "applied": bool(apply),
        "keep_per_location_mode": int(keep),
        "store": tracked_name(files[0].parent),
        "rank": coverage,
        "rows_read": len(meta),
        "rows_kept": len(keys),
        "rows_dropped": len(meta) - len(keys),
        "kept_because": kept_because,
        "saved_by_a_protection": saved,
    }
    doomed = [held["picture"] for held in meta if held["key"] not in keys and held["picture"]]
    if not apply:
        record["pictures"] = {"would_delete": len(doomed)}
        record["seconds"] = round(time.time() - started, 1)
        return record

    # ---- the pictures, then the records ------------------------------------- #
    record["pictures"] = delete_pictures(doomed, log=log)
    columns = ("key", "recipe_key", "recipe_key")
    temps = [path.with_suffix(path.suffix + ".writing") for path in files]
    written: dict = {}
    try:
        for name, path, temp, column in zip(
            ("rows", "scores", "flatness"), files, temps, columns, strict=True
        ):
            written[name] = _prune_file(path, temp, keys, column)
        for temp, path in zip(temps, files, strict=True):
            temp.replace(path)
    except BaseException:
        for temp in temps:
            temp.unlink(missing_ok=True)
        raise
    for name, held in written.items():
        log(f"[prune] {name}: {held['rows']:,} rows, {held['bytes']:,} bytes")

    record["files"] = written
    record["seconds"] = round(time.time() - started, 1)
    return record


def _flatness_path() -> Path:
    """The flatness sidecar, through its own module's accessor.

    A third name for a path this module already knows how to build would be a
    third thing to redirect, and redirecting two of three is how a test comes to
    rewrite the real store.
    """
    from fractal_wallpapers.curation import flatness

    return flatness.sidecar_path()


def delete_pictures(named, log=print) -> dict:
    """Delete the candidate pictures a prune dropped, and their levelled colormaps.

    `named` is stored names, read through [`paths.rehome`], because a row names
    its picture as the run that made it saw it and the subtree may have been
    archived since. A name with no artifacts component is not a name this project
    wrote and is left alone entirely — which is what keeps a fixture's `a.jpg`,
    and anything beside it, out of reach of this.

    **The levelled colormap goes with the picture**, because it is part of what
    that render cost and the rule is that a picture goes with its row.
    `colorize.render` writes the autolevel operator's overriding map to
    `<stem>.leveled/` beside the JPEG on every acted render, ~76 KiB against the
    picture's ~157 KiB. Unlinking the one and leaving the other is how 206,147 of
    them reached 14.9 GiB — more than the whole candidate pool — and how they
    would do it again. Nothing reads a candidate's for content and the row
    re-derives it, so it is regenerable exactly as the picture is.

    The colormap is swept whether or not the JPEG was still there: a row is being
    dropped either way, and a colormap outliving an already-deleted picture is
    precisely the pile.

    Counted rather than raised on: a picture already gone is the ordinary state
    of a store somebody has swept before, and a leg that refused to finish over
    one would leave the records ahead of the disk.
    """
    from fractal_wallpapers.paths import rehome

    out = {
        "asked": 0,
        "deleted": 0,
        "bytes": 0,
        "absent": 0,
        "unreadable": 0,
        "colormaps": 0,
        "colormap_bytes": 0,
    }
    for stored in named:
        out["asked"] += 1
        where = rehome(str(stored))
        if where is None:
            out["absent"] += 1
            continue
        try:
            size = where.stat().st_size
        except OSError:
            size = None
        if size is None:
            out["absent"] += 1
        else:
            try:
                where.unlink()
            except OSError as failure:
                out["unreadable"] += 1
                log(f"[prune] {where}: {failure!r}")
            else:
                out["deleted"] += 1
                out["bytes"] += size
        # One call site, past every outcome the JPEG can have. A second one
        # inside a branch is how the sweep would come to be skipped for exactly
        # the rows whose picture was already the odd case.
        _delete_colormap(where, out, log)
        if out["deleted"] and out["deleted"] % 25_000 == 0:
            log(f"[prune] {out['deleted']:,} picture(s) deleted, {out['bytes'] / 2**30:.2f} GiB")
    out["gib"] = round(out["bytes"] / 2**30, 3)
    out["colormap_gib"] = round(out["colormap_bytes"] / 2**30, 3)
    log(
        f"[prune] {out['deleted']:,} of {out['asked']:,} picture(s) deleted, {out['gib']} GiB, "
        f"and {out['colormaps']:,} levelled colormap(s), {out['colormap_gib']} GiB"
    )
    return out


def _delete_colormap(picture: Path, out: dict, log) -> None:
    """Remove the `<stem>.leveled/` directory beside one picture, if it has one.

    Spelled the way [`curation.colorize.render`] spells it when it writes the
    thing, so the two cannot drift apart into a writer and a sweeper that
    disagree about the name.
    """
    import shutil

    where = picture.parent / f"{picture.stem}.leveled"
    if not where.is_dir():
        return
    try:
        size = sum(entry.stat().st_size for entry in where.iterdir() if entry.is_file())
        shutil.rmtree(where)
    except OSError as failure:
        out["unreadable"] += 1
        log(f"[prune] {where}: {failure!r}")
        return
    out["colormaps"] += 1
    out["colormap_bytes"] += size


def _prune_meta(path: Path, log=print) -> list[dict]:
    """One streamed pass of the ledger into what the decision needs per row.

    Takes the **file** and not the directory it is in. It took the directory for
    one afternoon and joined `ROWS_NAME` onto a name that was already the file,
    which `_stream_of` answers by yielding nothing — so the prune decided over an
    empty store and wrote three empty files. A silent empty read is what that
    shape of mistake always looks like here, which is why the caller now hands
    every path in and this builds none of its own.
    """
    from fractal_wallpapers.curation import retention

    out: list[dict] = []
    for at, held in enumerate(_stream_of(path), start=1):
        colour = held.get("colour") or {}
        provenance = held.get("provenance") or {}
        out.append(
            {
                "key": str(held["key"]),
                "place": str((held.get("location") or {}).get("key")),
                "mode": str((held.get("recipe") or {}).get("mode")),
                "cells": tuple(colour.get("cells") or ()),
                "rejected": bool(held.get("rejected")),
                "picture": held.get("picture"),
                "render_key": retention.render_key_of(held),
                "seat": (str(provenance.get("run")), str(provenance.get("candidate"))),
                "also_recorded": tuple(
                    (str(named.get("run")), str(named.get("candidate")))
                    for named in (provenance.get("also_recorded") or ())
                ),
            }
        )
        if at % 100_000 == 0:
            log(f"[prune] {at:,} rows read")
    log(f"[prune] {len(out):,} rows read from {tracked_name(path)}")
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


def _prune_ranks(meta: list, log=print) -> tuple[dict, dict]:
    """`({key: rank value}, coverage)` through the SHIPPED key, not a copy of it.

    A row the key cannot read — no reading on the live judge, no flatness — has
    no value here, and [`retention.decide`] ranks it last within its pair, which
    is [`curation.solve`]'s own convention for exactly that case.
    """
    from fractal_wallpapers.curation import flatness, intake, rank_key

    readings = scores_by_recipe(read_scores())
    flat = flatness.by_recipe(flatness.read())
    held = rank_key.load()
    pooled = [_Pooled(row, readings[row["key"]]) for row in meta if row["key"] in readings]
    features, gaps = rank_key.features_for(pooled, locations=intake.read_scores(), readings=flat)
    values = {name: held.score(row) for name, row in features.items()}
    log(f"[prune] {len(values):,} of {len(meta):,} rows carry a rank value; gaps {gaps}")
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


def _prune_protections(meta: list, log=print) -> dict:
    """`{reason: {keys}}` for the five things kept whatever the rank says."""
    from fractal_wallpapers.curation import rank_key, retention, served_locations, tentative

    index = served_locations.build()
    live: set = set()
    for held in index.rows:
        live.add((str(held.get("run")), str(held.get("candidate"))))
        source = held.get("source") or {}
        if source.get("run") is not None:
            live.add((str(source.get("run")), str(source.get("candidate"))))
    marked = retention.labeled_renders()
    recorded = tentative.protected_keys()
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
        RETAINED_TENTATIVE: {held["key"] for held in meta if held["key"] in recorded},
    }
    named = ", ".join(f"{name} {len(found):,}" for name, found in out.items())
    log(
        f"[prune] protections: {named}; the population file names {len(fitted):,} recipe(s) "
        f"and {len(tentative.stamps())} recorded gallery/ies name {len(recorded):,}"
    )
    return out


def _prune_file(source: Path, into: Path, keys: set, column: str) -> dict:
    """Stream one recipe-keyed file into a `.writing` name, its kept rows only.

    One body for the ledger and both sidecars: the only thing that differs is
    which column carries the recipe key, and two copies of a filter is how a
    sidecar comes to be pruned against a rule the rows were not.
    """
    rows = 0
    dropped = 0
    with into.open("w", encoding="utf-8", newline="\n") as handle:
        for held in _stream_of(source):
            if str(held.get(column)) not in keys:
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
            "texture_flat": 0,
            "texture_flat_from_register": 0,
            "texture_flat_carried": 0,
            "texture_flat_unmeasured": 0,
            "texture_flat_no_texture": 0,
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
        flat, from_where = _texture_flat_for(recipe, known.get(key) or {})
        counts[from_where] += 1
        counts["texture_flat"] += int(flat)
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
                texture_flat=flat,
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


def _texture_flat_for(recipe: recipes.Recipe, stored: dict) -> tuple[bool, str]:
    """`(the flag, which counter to bump)` for one recipe. Renders nothing.

    A backfill rebuilds the ledger out of the two decision stores and drives no
    engine, so the one thing it cannot do is *measure* this. Two places have the
    answer and they are asked in that order:

    * **The register** — [`fractal_wallpapers.coloring.texture_flat`] — which is
      the measurement, tracked, and keyed on the field side of the render so one
      probe answers for every map at a location.
    * **The row already on record**, for a candidate mined since the engine began
      reporting it. That row's flag came straight off the engine and no register
      entry exists for it.

    They cannot disagree: both are the engine's answer about one field identity.
    A recipe neither knows reads `False`, which is what every reader concluded
    before the flag existed. A mode with no texture layer is counted apart from
    that and not as a fallback: `False` is the only true answer there, and sixteen
    of the seventeen production modes are in it.
    """
    from fractal_wallpapers.coloring import texture_flat

    if not texture_flat.has_a_texture(recipe.mode):
        return False, "texture_flat_no_texture"
    measured = texture_flat.register().get(texture_flat.field_key(recipe.row()))
    if measured is not None:
        return bool(measured), "texture_flat_from_register"
    if "texture_flat" in stored:
        return bool(stored["texture_flat"]), "texture_flat_carried"
    return False, "texture_flat_unmeasured"


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
    from fractal_wallpapers.curation import mode_policy
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
        # The mode a row COUNTS as, not the mode it was drawn in: a modulate whose
        # texture said nothing is the smooth field spent by rank bit for bit, and a
        # census that counted it as `itinerary` would be reporting a fill the
        # gallery cannot spend. See [`mode_policy.routed_mode`].
        "modes": _fill(stored, _production_modes(), lambda row: [mode_policy.routed_mode_of(row)]),
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
        # Rows whose modulate texture said nothing, so they are counted as
        # `smooth` on the modes axis above and seated on the smooth side.
        "texture_flat": sum(1 for stamped in stored if stamped.get("texture_flat")),
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
    "delete_pictures",
    "hunt_block",
    "durable_rows",
    "durable_scores",
    "feasibility",
    "k_of",
    "live_artifact",
    "manifest_dir",
    "missing_pictures",
    "merge",
    "read",
    "read_scores",
    "stream",
    "stream_scores",
    "re_render",
    "render_pair",
    "renders_of",
    "prune",
    "restore",
    "row",
    "rows_path",
    "save",
    "score_row",
    "scores_by_recipe",
    "rescore",
    "scores_path",
    "sources",
    "stale_scores",
    "store_root",
    "write",
    "write_scores",
]
