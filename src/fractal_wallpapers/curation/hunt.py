"""Render candidates on purpose: breadth where the ledger is thin, colour where a solve was short.

Every candidate this project owns was made by a **gallery pass**, and a pass is a
selection instrument: it draws the strongest places, offers each one to the
palette head, and keeps what the head liked. That is the right shape for shipping
a collection and the wrong shape for stocking a ledger, and the two reads
[`curation.solve`] took say so precisely.

*Places are thin.* 1,223 locations carry recipes against 28,090 scanned, at a
median of eight recipes each. Depth per place is not what a gallery is short of —
the solve seats one wallpaper per location, so the 44th recipe at a place that
already has 43 cannot take a seat the first one could not.

*Green is thin.* 986 of those locations carry a red candidate and 248 carry a
lime one, and the reason is the palette head rather than the library: it is
offered the green carriers as often as anything else and picks them at 0.17x the
base rate. So a `dark_vivid_lime` target at n=60 is infeasible on the
`colour_target` row **alone** — 45 candidates over 44 locations against sixty
seats.

This module is the other half of that loop. It renders **into** those two
shortages and writes what it makes into [`curation.candidate_ledger`], so the
same solve can be taken again and the shortage measured against the candidates it
cost.

## Two legs, and why neither is the other

**Unconditional** buys breadth. Locations come from the admitted pool that carry
**no ledger recipe at all**, a shallow spread each, and the palettes are
*stratified across the codebook's cells* rather than picked by the head. The
stratification is the whole point: the head's argmax concentrates, and its
concentration is what left the ledger at a quarter as much green as red.

**Conditioned** buys one colour. The maps come from the tracked carrier table
([`palettes.carriers`]) for the cell a solve came up short in, and the draw
**bypasses the palette head entirely** — a conditioned attempt routed through
`palette_head.top_pick` would be offered its carrier and would decline it, which
is not a conditioned draw at all. The partitions come from the shortage's own
work order, which says where the pool's carriers of that colour already stand.

A conditioned candidate is a candidate and never a privilege: it is judged by the
same judge, its colour is read off **its own render** rather than off the carrier
table, and it takes a seat only by winning one.

## The frame is looked up where there is one, and is never an admission ticket

A recipe carries the frame it was drawn at, so a hunt has to choose one. Where the
pool-wide refinement scan holds a row for the location, it draws what that scan
chose at [`framing.MARGIN`] — the winner where it adopted, the recorded frame
where it refused. **No refinement machinery runs here**: this is a lookup, the
record says which margin it was taken at, and a record taken at another margin is
refused rather than reinterpreted.

Where the scan holds no row, it draws **the frame the location already carries**.
Every location row carries its own `viewport` and `maxiter`, so there is nothing
to wait for; [`frame_for`] is the whole of the seam and [`drawable`] no longer
knows the index exists. **Absence is not a rejection**, and the rule it replaced
was "minable if it was present the last time someone ran a batch job" — stale by
construction, and on 2026-09-01 it was holding 8,015 never-opened admitted
locations out of every mining leg, the whole reframing channel among them.

That the frame is part of the recipe is what makes both branches safe. A candidate
is recorded at the frame it was drawn at and stays valid if the margin later
moves; what a moved margin invalidates is the *choice of where to draw*, not the
picture that was drawn.

## Rows land as candidates land

One appended ledger row and one appended score row per picture, into the hunt's
own two files, before the next candidate starts. A killed hunt therefore leaves a
usable partial rather than nothing, and [`merge`] is what folds those files into
the ledger. The merge is a separate step because the ledger is rewritten whole on
every upsert: forty megabytes a candidate is not a write, it is a hunt that
renders nothing.

## The budget is spent at the candidate boundary

A hunt is given seconds, not a count, and it never *starts* a candidate it cannot
finish inside what is left. The price is read off what that partition has
actually cost **this run**, because maxiter does not price a partition — `phoenix`
ran 1.7x what its cap tier implied and `mandelbrot` 0.6x, fixed overhead is most
of a cheap location, and the residual is per-partition rather than random.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import random
import time
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, framing, recipes
from fractal_wallpapers.paths import rehome, tracked_name, under
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

#: The schema every record and every row this module writes carries.
SCHEMA = 1

#: The subtree a hunt's own output lands in, under the regenerable tree.
UNIT = "hunt"

#: What a hunt's two appended files and its record are called.
ROWS_NAME = "rows.jsonl"
SCORES_NAME = "scores.jsonl"
RECORD_NAME = "hunt.json"

#: Where a hunt's candidate renders live, under its own directory. Named by
#: **recipe key**, which is what lets a re-run find the picture it already made
#: rather than draw it a second time.
PICTURES = "pictures"

#: Where a unit of work's dumped fields live, under its own directory. One per
#: (location, mode), and every palette at that pair is a recolour of it — see
#: [`colorize.render`]. Swept down to [`colorize.FIELDS_KEPT`] as the run goes.
FIELDS = "fields"

#: The pool-wide refinement scan [`frames_path`] was derived from. **The artifact
#: is gone and nothing here ever built it** — this repository has only ever held a
#: reader for it, and the scan itself came from a job outside the tree. Deleted
#: 2026-09-02 (97.8 MiB) once [`build_frames`] was checked to have carried all
#: 28,090 of its rows across. The names stay because [`build_frames`] is still the
#: only thing that can make the index and would be unreconstructable without them;
#: what they point at will not come back on its own.
SCAN_UNIT = "frame_refit"
SCAN_NAME = "scan.jsonl"

#: The thin index derived from that scan: one row a location, the frame it chose
#: and nothing else. The scan was 98 MB of every rung and a hunt asks it one
#: question — parsing all of it per run was a minute of wall clock buying a lookup
#: table that does not change between runs. **It is now the durable half rather
#: than a cache**: the scan it came from is deleted, so this file cannot be rebuilt
#: and a leg that loses it draws every location at its recorded frame.
FRAMES_NAME = "frames.jsonl"

#: The two legs, in the spelling every row and every tally uses.
UNCONDITIONAL = "unconditional"
CONDITIONED = "conditioned"

#: Which store a hunt's ledger row came out of, beside
#: [`candidate_ledger.FROM_RELEASE`] and [`candidate_ledger.FROM_GALLERY`]. A
#: hunt is not a gallery pass and its rows do not pretend to be one: it renders
#: candidates and decides nothing, so it has no decision store to name.
FROM_HUNT = "hunt"

#: How many candidates one location is given. **Shallow, because the thin axis is
#: places**: the ledger's median location already carries eight recipes and a
#: gallery can seat one of them, so a fourth candidate at a fresh place is worth
#: more than a ninth at a stocked one.
PER_LOCATION = 3

#: The seed every draw here is taken under unless a caller names another. A
#: constant rather than a drawn one, because a hunt is a *supply* step: two hunts
#: at one seed over an unchanged pool ask for the same candidates, and the ledger
#: keys on the recipe, so the second one costs nothing and buys nothing. Moving
#: it is how a second hunt asks a different question.
DEFAULT_SEED = 20260826

#: How long a hunt may spend **rendering**, in seconds. Not the wall clock of the
#: invocation: the frame lookup, the plan and the merge sit outside it.
BUDGET_SECONDS = 1200.0

#: What one candidate is assumed to cost before this run has measured its
#: partition. The ledger's own figure for an attempt at this geometry, taken at
#: the dear end of it — over-pricing an unmeasured partition costs one candidate
#: at the tail of the budget, and under-pricing it overruns.
PRIOR_SECONDS = 3.1

#: How many candidates a partition has to have cost before this run prices it off
#: its own measurements instead of off [`PRIOR_SECONDS`].
PRICE_AFTER = 3

#: How much of [`Price.ema`] one freshly served candidate replaces. A tenth: the
#: within-leg spread on a dear partition is wide — `phoenix:classic` ran a median
#: 26.2 s against a max of 280 on one leg — so a fast EMA would swing the turn
#: weight on a single deep frame. At 0.1 the average has a memory of about ten
#: candidates, which is long enough to ignore one tail and short enough to catch
#: the machine moving, which is the thing that actually happened between `pc1` and
#: `pc20m`.
EMA_ALPHA = 0.1

#: Where a partition's price is read on its own measurements: **the dearest of
#: them**. The budget question is *can this one finish*, and a mean answers a
#: different question — half of a partition's candidates cost more than its mean.
PRICE_AT = "max"


class HuntRefused(RuntimeError):
    """A hunt cannot be planned, or the record it would look its frames up in cannot."""


def seed_of(*parts) -> int:
    """A non-negative seed derived from any number of parts, stable across processes.

    Through sha256 and **not** `hash()`. Python randomizes string hashing per
    process unless `PYTHONHASHSEED` is set, so a seed built out of `hash()` over a
    tuple holding a cell name is a different seed on every invocation — a draw
    that is recorded as seeded and is not reproducible from its record. It can
    also come back negative, which `numpy.random.default_rng` refuses outright;
    that refusal is the visible half of the same bug.
    """
    material = "|".join(str(part) for part in parts)
    return int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:8], 16)


# --------------------------------------------------------------------------- #
# Where it all is.
# --------------------------------------------------------------------------- #
def hunt_dir(name: str) -> Path:
    """One hunt's own subtree: its two appended files, its pictures, its record."""
    return under("curation", UNIT, str(name))


def rows_path(name: str) -> Path:
    """The ledger rows this hunt has made so far, appended as each lands."""
    return hunt_dir(name) / ROWS_NAME


def scores_path(name: str) -> Path:
    """The sidecar rows this hunt has made so far, appended as each lands."""
    return hunt_dir(name) / SCORES_NAME


def record_path(name: str) -> Path:
    """What the hunt reports about itself: the plan, the price, the coverage."""
    return hunt_dir(name) / RECORD_NAME


def pictures_dir(name: str) -> Path:
    """Where this hunt's candidate renders are, one per recipe key."""
    return hunt_dir(name) / PICTURES


def fields_dir(name: str) -> Path:
    """Where this hunt's dumped fields are, one per (location, mode)."""
    return hunt_dir(name) / FIELDS


def scan_path() -> Path:
    """The pool-wide refinement scan's record."""
    return under("curation", SCAN_UNIT) / SCAN_NAME


def frames_path() -> Path:
    """The thin frame index derived from it."""
    return under("curation", UNIT) / FRAMES_NAME


def frames_backup_path() -> Path:
    """The durable copy of the index: the archive tier where there is one, hot where not.

    Off a root rather than through [`under`], for the reason
    [`curation.durables.backup_path`] states: `under()` resolves to whichever
    tier the subtree is already on, which for a copy that has never been written
    is the hot one, beside the original it is supposed to survive.
    """
    from fractal_wallpapers.curation import durability
    from fractal_wallpapers.paths import archive_root, hot_root

    archive = archive_root()
    root = hot_root() if archive is None else archive
    return Path(root) / durability.BACKUP_UNIT / FRAMES_NAME


def frames_manifest_path() -> Path:
    """The tracked manifest: what the frame index was, last time anybody recorded it."""
    from fractal_wallpapers.paths import repo_root

    return repo_root() / "data" / "curation" / "hunt_frames.manifest.json"


def frames_durable():
    """The frame index as a [`curation.durability.Durable`] — saved, checked, restored.

    **The one durable here that cannot be rebuilt at any price.** The sidecar is
    a scoring pass, the amendment is a redraw, the sweep log is 8.7 hours of
    renders; each of those is expensive and each of them is a command. This is
    the index [`build_frames`] cut from a 97.8 MiB scan that no job in this
    repository builds and that was deleted on 2026-09-02 — so `build_frames`
    refuses, and the only copy of the 28,090 frame choices is the file itself.

    Every mining leg reads it through [`frame_for`]. Losing it is not an error
    anywhere: a location the index has no row for draws at the frame it already
    carries, which is `frame_for`'s other half and the majority case. That is
    exactly why it is guarded — a leg that lost the index renders successfully at
    19,041 unrefined framings and says nothing about it.
    """
    from fractal_wallpapers.curation import durability

    return durability.Durable(
        name="the hunt frame index",
        live=frames_path(),
        copy=frames_backup_path(),
        manifest=frames_manifest_path(),
        why_not_tracked=(
            "tens of megabytes of frame rows against a 1 MiB per-file history guard. The "
            "manifest is what the history keeps: the row count, the byte count, the sha256, "
            "the margin every row was chosen at and how many of them adopted a new framing."
        ),
        save_command="fractal-wallpapers curate frames save",
        restore_command="fractal-wallpapers curate frames restore",
        # There is no rebuild, and the string has to say so rather than name a
        # command that refuses: `build_frames` reads a scan this repository has
        # never built and no longer holds.
        rebuild_command=(
            "there is no rebuild — the refinement scan this index was cut from was deleted "
            "on 2026-09-02 and nothing in this repository builds one, so `curate hunt "
            "frames` refuses. Restore the copy"
        ),
        facts=_frames_facts,
    )


def _frames_facts(where: Path) -> dict:
    """The columns the index adds to its manifest: the margin, and what it decided.

    `adopted` is the half of the file that carries a *chosen* frame; the rest
    carry the location's recorded one, stamped `used: original`. A manifest with
    only a row count could not tell a restored index from one whose adopted rows
    had gone, and the adopted rows are the whole value of the file.
    """
    margins: dict[str, int] = {}
    adopted = 0
    partitions: dict[str, int] = {}
    with Path(where).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            margins[str(row.get("margin"))] = margins.get(str(row.get("margin")), 0) + 1
            adopted += bool(row.get("adopted"))
            key = str(row.get("partition"))
            partitions[key] = partitions.get(key, 0) + 1
    return {
        "adopted": adopted,
        "rows_by_margin": dict(sorted(margins.items())),
        "rows_by_partition": dict(sorted(partitions.items())),
    }


# --------------------------------------------------------------------------- #
# The frame, looked up.
# --------------------------------------------------------------------------- #
def chosen_frame(row: dict) -> dict:
    """The frame one scan row chose, as a hunt renders it.

    The winner where the scan **adopted** at its own margin, the recorded frame
    where it refused. Both sides travel, because the ledger row wants the framing
    block a gallery pass would have written and that block names the two frames
    and which of them was used.
    """
    original = row.get("original") or {}
    if not row.get("adopted") or not row.get("winner"):
        return {
            "adopted": False,
            "used": "original",
            "viewport": original.get("viewport"),
            "maxiter": original.get("maxiter"),
            "original_viewport": original.get("viewport"),
            "refined_viewport": None,
            "slug": original.get("slug"),
            "gain": None,
        }
    winner = next(
        (rung for rung in (row.get("rungs") or []) if rung.get("slug") == row["winner"]), None
    )
    if winner is None:
        raise HuntRefused(
            f"{row.get('key')!r} says its winning frame is {row['winner']!r} and carries no "
            f"rung by that name, so the frame it chose cannot be looked up."
        )
    return {
        "adopted": True,
        "used": "refined",
        "viewport": winner.get("viewport"),
        "maxiter": winner.get("maxiter"),
        "original_viewport": original.get("viewport"),
        "refined_viewport": winner.get("viewport"),
        "slug": winner.get("slug"),
        "gain": row.get("gain"),
    }


def build_frames(margin: float = framing.MARGIN, log=print) -> tuple[Path, int]:
    """Derive [`frames_path`] from the scan record. `(path, rows)`.

    Refuses a scan row taken at another margin rather than reinterpreting it. The
    margin is a property of that *record*, and re-deciding it is a read of every
    rung — which is what the scan kept every rung for, and is not something a
    hunt does on its way past.

    **This can no longer run**, because [`SCAN_UNIT`]'s artifact is deleted and
    nothing in this repository builds one. Re-deriving at a different margin was
    the only thing the scan was still being kept for, and it is bought back only
    by re-running the outside job that made it. The index it already wrote is the
    durable product.
    """
    source = scan_path()
    if not source.is_file():
        raise HuntRefused(
            f"there is no refinement scan at {tracked_name(source)} and nothing in this "
            f"repository builds one — it was deleted on 2026-09-02, having no builder here "
            f"and no reader but this. {tracked_name(frames_path())} is the index it wrote "
            f"and is what a hunt actually reads; a location missing from it draws at the "
            f"frame it already carries, which is `frame_for`'s other half and not an error."
        )
    out = frames_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with (
        source.open(encoding="utf-8") as handle,
        out.open("w", encoding="utf-8", newline="\n") as sink,
    ):
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if float(row.get("margin", -1.0)) != float(margin):
                raise HuntRefused(
                    f"{tracked_name(source)} was taken at margin {row.get('margin')} and this "
                    f"hunt draws at {margin}. A hunt looks a frame up rather than deciding "
                    f"one, so re-decide the margin off the scan's own rungs first."
                )
            sink.write(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "key": str(row["key"]),
                        "partition": row.get("partition"),
                        "margin": float(margin),
                        **chosen_frame(row),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    log(f"[hunt] {written:,} frame(s) indexed at margin {margin}")
    return out, written


def frames(margin: float = framing.MARGIN, rebuild: bool = False, log=print) -> dict:
    """`{location key: the frame the scan chose}`, off the index, built on first ask.

    **Empty where there is no scan at all**, rather than refused. A framing is an
    attribute a location may carry and never an admission ticket: a leg reads
    this to draw a refined frame where one was chosen, and draws the recorded
    frame where one was not — see [`frame_for`]. Asking for a *rebuild* still
    refuses, because that is a caller naming the scan.
    """
    path = frames_path()
    if rebuild or not path.is_file():
        if not rebuild and not scan_path().is_file():
            log(
                f"[hunt] no refinement scan at {tracked_name(scan_path())}; every location "
                f"draws at the frame it already carries"
            )
            return {}
        build_frames(margin, log=log)
    out: dict = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if float(row.get("margin", -1.0)) != float(margin):
                raise HuntRefused(
                    f"{tracked_name(path)} was indexed at margin {row.get('margin')} and this "
                    f"hunt draws at {margin}. Rebuild it with `--rebuild-frames`."
                )
            out[str(row["key"])] = row
    return out


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def opened_locations(rows=None) -> set:
    """Every location the ledger already carries a recipe at.

    The **recorded** identity (`location.key`), which is what the solve's
    one-wallpaper-per-location row counts on and what the scan is keyed by — not
    `location.frame_key`. A refined-frame row stands on the place it was planned
    at, and a hunt looking for unopened places has to agree with the rule that
    would later refuse a second seat there.
    """
    stored = candidate_ledger.read() if rows is None else list(rows)
    return {str((row.get("location") or {}).get("key")) for row in stored}


def scanned(log=print) -> list[dict]:
    """The admitted, embedded locations — the population the scan was taken over.

    Through [`embeddings.admitted_only`], so a location the sidecar has since put
    under the junk floor is out of a hunt's reach for the same reason it is out of
    a solve's: it is not a place this collection may ship.
    """
    from fractal_wallpapers.curation import embeddings, intake

    rows, matrix = embeddings.load()
    if not rows:
        raise HuntRefused(
            "the embedding store holds no row, so a hunt has no population to draw from. "
            "Run `fractal-wallpapers curate embed`."
        )
    scores = intake.read_scores(amended=True)
    rows, _matrix, fallen = embeddings.admitted_only(rows, matrix, scores, log)
    for row in rows:
        row.pop("vector", None)
    log(f"[hunt] {len(rows):,} admitted location(s); {fallen:,} now under the junk floor")
    return rows


def recorded_frame(place: dict) -> dict:
    """The frame a location already carries, in the shape [`chosen_frame`] returns.

    Every location row — the ledger's, the sidecar's, the embedding store's —
    carries its own `viewport` and `maxiter`, because a store that could not
    re-render its own pictures would not be a store. So a location no refinement
    scan has ever looked at is still fully renderable, and this is the frame it
    renders at: [`framing.ORIGINAL`], which is *the recorded framing, always*.

    `from_scan` is the one member [`chosen_frame`] does not set, and it is spelled
    that way rather than `scanned` because [`scanned`] here is the admitted
    population. It separates a location the scan looked at and refused — which
    also comes back `adopted: False` at the original — from one the scan never
    held a row for. Both draw the same picture; only the second is a location
    whose framing is still an open question.
    """
    return {
        "adopted": False,
        "used": framing.ORIGINAL,
        "from_scan": False,
        "viewport": place.get("viewport"),
        "maxiter": place.get("maxiter"),
        "original_viewport": place.get("viewport"),
        "refined_viewport": None,
        "slug": None,
        "gain": None,
    }


def frame_for(place: dict, index: dict) -> dict:
    """The frame one location is rendered at: the scan's where there is one.

    **Absence is not a rejection.** This is the single seam between the pool-wide
    framing scan and every leg that draws: where the scan holds a row the leg
    draws what the scan chose, and where it does not the leg draws the frame the
    location already has. Nothing above this function has to know which happened,
    and no leg's population is bounded by which happened.
    """
    return index.get(str(place["key"])) or recorded_frame(place)


def wants_framing(place: dict, index: dict) -> bool:
    """Whether a refinement scan would have anything left to decide here.

    Two ways the answer is no. The scan already holds a row for this location —
    the ordinary case — or the location is [`framing.is_centered`], and then its
    centre **is** the location and its scale is the rung its head picked out of
    [`discovery.reframing.RUNGS`]. A centered location is not incomplete for
    having no scan row; it is a location whose framing was decided somewhere else.

    A store that does not carry the flag says nothing about it, exactly as
    [`framing.is_centered`] reads it: absent and `false` are one case. The
    embedding store and the supply sidecar both drop it today, so this separates
    the two populations only where the rows come from a walk ledger.
    """
    if str(place["key"]) in index:
        return False
    return not framing.is_centered(place)


def unframed(rows: list, index: dict) -> list:
    """The locations a framing scan would still be pointed at. A census, not a gate.

    Nothing in this repository builds the pool-wide scan, and no leg here waits on
    one: every row in this list is minable today at the frame it already carries,
    through [`frame_for`]. What the count is for is saying how much of a
    population has an open framing question — which is a different number from how
    much of it drew unrefined, and smaller by every centered location.
    """
    return [row for row in rows if wants_framing(row, index)]


def drawable(rows: list, opened: set, partitions=ALL_PARTITIONS) -> dict:
    """`{partition: [rows]}` — admitted, and carrying no ledger recipe yet.

    That is the whole of the rule. `rows` has already been through
    [`scanned`]'s admission — the location head's rating over the junk floor —
    and what is subtracted here is the places the ledger already stands on.

    **Every registered partition gets a key, empty or not.** A partition with no
    drawable rows used to be absent rather than zero, so it could not appear as a
    refusal anywhere in the hunt's own records — and `phoenix:classic` spent the
    project's whole history at zero without one report saying so. A table that
    omits a partition and a table that reports it empty are different statements.

    **A framing row is not part of it.** It used to be: a location the pool-wide
    scan did not hold was dropped rather than drawn at its recorded frame, which
    made "minable" mean "present the last time someone ran a batch job" and left
    every location admitted after a scan silently out of reach — 8,778 of the
    36,868 admitted on 2026-09-01, 8,015 of those never opened, the whole
    reframing channel among them. A location with no scan row draws at the frame
    it already has, through [`frame_for`].
    """
    out: dict = {p: [] for p in partitions}
    for row in rows:
        key = str(row["key"])
        if key in opened:
            continue
        out.setdefault(str(row["partition"]), []).append(row)
    return {name: sorted(held, key=lambda row: str(row["key"])) for name, held in out.items()}


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Try:
    """One candidate a hunt intends to make, before anything is rendered."""

    leg: str
    location: str
    partition: str
    mode: str
    colormap: str
    #: The codebook cell the map was drawn **for** — the stratifier's cell on the
    #: unconditional leg, the target on the conditioned one. A prior about the
    #: map and never a claim about the picture, whose colour is read off its own
    #: render like every other candidate's.
    cell: str
    #: Which candidate this is at its location, counting only this hunt's own,
    #: from 1. A hunt does not vary `k` deliberately the way a depth run does,
    #: but the ledger row is corrected on it downstream all the same — see
    #: [`mine.Unit.named`] — so it is stamped rather than inferred.
    k: int = 1
    #: The mode's own settings, where the leg named a `(mode, settings)` pair on
    #: its roster ([`colorize.roster_entry`]). Empty for every draw that names a
    #: bare mode, which is every draw a hunt takes today. Read by
    #: [`Maker.recipe_for`], which is why [`mine.Unit`] and [`depth.Shot`] carry
    #: the same member under the same name: those three are one duck type and the
    #: maker reads whichever it is handed.
    mode_params: dict = dataclass_field(default_factory=dict)
    #: Overrides onto the palette pass [`Maker.recipe_for`] would otherwise spend,
    #: `{}` for every draw that takes the candidate path's own — which is every
    #: draw a hunt takes. The third member of the duck type above, for the same
    #: reason and with the same warning: `palette` is in [`curation.recipes.KEYED`],
    #: so a varied candidate takes its own key and its own file and cannot
    #: overwrite the plain one. `mirror` is **not** an override a draw may set —
    #: it is the map's bake, read off the cyclic set by the maker — so a draw
    #: naming one would be describing another map's picture under this map's name.
    palette: dict = dataclass_field(default_factory=dict)

    def named(self) -> dict:
        """This intention as the ledger row carries it."""
        out = {
            "leg": self.leg,
            "mode": self.mode,
            "colormap": self.colormap,
            "drawn_for": self.cell,
            "k": self.k,
        }
        if self.mode_params:
            out["mode_params"] = dict(self.mode_params)
        if self.palette:
            out["palette_drawn"] = dict(self.palette)
        return out


def modes_for(key: str, count: int, seed: int, roster: tuple) -> list[str]:
    """`count` production modes for one location, without replacement and seeded.

    Without replacement for [`colorize.modes_drawn_for`]'s reason: a second draw
    that could repeat the first buys the same picture twice. Uniform over the
    **whole** production roster rather than split by judge kind, because a hunt is
    not allocating a judge's budget — it is stocking a ledger whose thinnest mode
    axis is exactly the rare modes a kind split reaches once in seventeen draws.
    """
    return random.Random(seed_of(seed, key)).sample(list(roster), min(int(count), len(roster)))


class Stratifier:
    """The unconditional leg's palette draw: the cells in turn, a carrier for each.

    The head's argmax concentrates — 986 of the ledger's locations carry red and
    248 carry lime — so a hunt that asked the head for a colour would buy the same
    skew again at a fresh set of places. This walks the codebook's cells in a
    seeded order instead and asks the carrier table for a map that makes each one.

    It stratifies the **ask** and not the answer, and the difference is measured:
    a map drawn for a cell delivers that cell's family something under a third of
    the time, because the field and the mode carry a real share of the outcome.
    """

    def __init__(self, cells: list, pool: list, seed: int):
        self.cells = list(cells)
        self.pool = list(pool)
        self.seed = int(seed)
        random.Random(self.seed).shuffle(self.cells)
        self.at = 0
        self.rounds: dict = {}

    def next(self) -> tuple | None:
        """`(cell, map)` for the next candidate, or `None` where nothing carries.

        A cell whose carriers this pool cannot reach is **skipped** rather than
        refused: an even ask across the cells that can be asked for is the whole
        of the job, and one unreachable cell is not a reason to stop.
        """
        from fractal_wallpapers.palettes import carriers as carrier_table

        for _attempt in range(len(self.cells)):
            cell = self.cells[self.at % len(self.cells)]
            self.at += 1
            turn = self.rounds.get(cell, 0)
            self.rounds[cell] = turn + 1
            drawn = carrier_table.draw(cell, 1, seed_of(self.seed, cell, turn), within=self.pool)
            if drawn:
                return cell, drawn[0]
        return None


def conditioned_maps(cell: str, count: int, pool: list, seed: int) -> list:
    """`count` maps for one target cell, drawn without replacement and re-drawn.

    The re-draw on a bumped seed is what stops a target being met by one map,
    which is a target met by one picture repeated: the palette-group cap would
    refuse all but the first of them. Seeded through [`seed_of`] and so through
    sha256 — the retired gallery pass's own version of this draw seeded on
    `hash()` over a tuple holding a cell name, which is not stable across
    processes, and it was deleted rather than repaired.
    """
    from fractal_wallpapers.palettes import carriers as carrier_table

    out: list = []
    turn = 0
    while len(out) < count:
        more = carrier_table.draw(cell, count - len(out), seed_of(seed, cell, turn), within=pool)
        if not more:
            break
        out += more
        turn += 1
    return out


def spread(pools: dict, count: int, seed: int, weights: dict | None = None) -> list:
    """`count` locations off `{partition: [rows]}`, round-robin, seeded per partition.

    Round-robin rather than proportional to what each partition holds, because the
    axis being bought is **places** and every partition's places are equally thin
    against the scan. A proportional draw would spend a third of a breadth leg on
    `julia:mandelbrot` alone and leave the per-partition price table — the thing
    that sizes the next budget — with two rows worth reading.

    `weights` turns it into a shortage's work order instead: a partition gets as
    many turns per round as the work order gives it, so a leg aimed at a colour
    looks where that colour's carriers already stand.
    """
    order = sorted(pools)
    if not order or count <= 0:
        return []
    shuffled = {
        name: random.Random(seed_of(seed, name)).sample(held, len(held))
        for name, held in pools.items()
    }
    turns = _turns(order, weights)
    at = {name: 0 for name in order}
    out: list = []
    while len(out) < count:
        took = False
        for name in turns:
            if len(out) >= count:
                break
            if at[name] < len(shuffled[name]):
                out.append(shuffled[name][at[name]])
                at[name] += 1
                took = True
        if not took:
            break
    return out


def _turns(order: list, weights: dict | None) -> list:
    """One round of the draw: each partition as often as its weight, **interleaved**.

    [`curation.draw_weights.order`], which is now the only copy of this
    arithmetic — the interleave, and the scaling that lets a *fractional* weight
    act at all. `floor=1`, which is the rule this site has always held: a work
    order is a shortage's, and a partition it does not mention still gets its
    turn. An integer table comes out of the shared helper as the turns it always
    was, so a work order this project has already passed draws what it drew.
    """
    from fractal_wallpapers.curation import draw_weights

    return draw_weights.order(order, weights, floor=1)


def plan(
    pools: dict,
    *,
    seed: int,
    per_location: int = PER_LOCATION,
    unconditional: int = 0,
    conditioned: int = 0,
    cell: str | None = None,
    work_order: dict | None = None,
    pool: list | None = None,
    log=print,
) -> list:
    """The whole plan, both legs, interleaved. Renders nothing.

    Interleaved rather than one leg after the other, because the budget is spent
    at the candidate boundary: a hunt that ran out on a concatenated plan would
    have bought all of one leg and none of the other, which answers neither of the
    two questions it was sent to ask.
    """
    from fractal_wallpapers.curation import colorize, draw_weights, mode_policy
    from fractal_wallpapers.palettes import dominance

    maps = list(colorize.pool(seed) if pool is None else pool)
    # The mined roster, not the engine's production one and not `accepted()`
    # either: a hunt buys more of a mode, and [`curation.mode_policy`] holds two
    # separate rulings about that — weight 0 for a mode this project has stopped
    # buying at all, and `UNMINED` for one the gallery still seats and no leg
    # buys more of. Existing material stands under both.
    roster = tuple(mode_policy.mined())
    # The breadth leg draws under the standing weight table and the aimed one does
    # not: what a partition costs to render is a fact about a *breadth* draw, and
    # a leg sent at a shortage is already saying which partitions it means. See
    # [`curation.draw_weights`] for the table and for the override.
    breadth = _leg(
        UNCONDITIONAL,
        spread(
            pools,
            -(-int(unconditional) // max(1, per_location)),
            seed,
            weights=draw_weights.table(),
        ),
        per_location,
        seed,
        roster,
        Stratifier(list(dominance.cells()), maps, seed).next,
        int(unconditional),
    )
    aimed: list = []
    if conditioned and cell:
        drawn = conditioned_maps(str(cell), int(conditioned), maps, seed + 1)
        if not drawn:
            raise HuntRefused(
                f"no map this hunt can draw carries {cell}. The carrier table is over the "
                f"whole library and the pool is one member per palette group, so either the "
                f"cell has no carrier at all or every one of its carriers stood down."
            )
        supply = itertools.cycle(drawn)
        aimed = _leg(
            CONDITIONED,
            spread(
                pools,
                -(-int(conditioned) // max(1, per_location)),
                seed + 1,
                weights=work_order,
            ),
            per_location,
            seed + 1,
            roster,
            lambda: (str(cell), next(supply)),
            int(conditioned),
        )
    log(
        f"[hunt] planned {len(breadth):,} unconditional and {len(aimed):,} conditioned candidate(s)"
    )
    return _interleave(breadth, aimed)


def _leg(leg, places, per_location, seed, roster, draw, want) -> list:
    """One leg's candidates: each place tried in `per_location` modes and colours."""
    out: list = []
    for row in places:
        for k, mode in enumerate(modes_for(str(row["key"]), per_location, seed, roster), start=1):
            if len(out) >= want:
                return out
            picked = draw()
            if picked is None:
                return out
            cell, colormap = picked
            out.append(
                Try(
                    leg=leg,
                    location=str(row["key"]),
                    partition=str(row["partition"]),
                    mode=str(mode),
                    colormap=str(colormap),
                    cell=str(cell),
                    k=k,
                )
            )
    return out


def _interleave(one: list, other: list) -> list:
    """Two legs woven together, so a budget that runs out truncates both alike."""
    if not one or not other:
        return list(one) + list(other)
    out: list = []
    step = len(other) / len(one)
    owed = 0.0
    at = 0
    for item in one:
        out.append(item)
        owed += step
        while owed >= 1.0 and at < len(other):
            out.append(other[at])
            at += 1
            owed -= 1.0
    return out + other[at:]


# --------------------------------------------------------------------------- #
# What one candidate costs, per partition.
# --------------------------------------------------------------------------- #
class Price:
    """What a partition has cost **this run**, and what the next one is priced at.

    Priced off measurement rather than off the iteration cap, because the cap does
    not price a partition: over the pool-wide scan `phoenix` cost 1.7x what its
    median maxiter implied and `mandelbrot` 0.6x, and `mandelbrot` — dearest
    partition in the pool by cap — ran cheaper per location than `julia:mandelbrot`
    at 2.5x the iterations. Fixed overhead is about 70% of a cheap location, so no
    power of maxiter fits both ends.
    """

    def __init__(
        self,
        prior: float = PRIOR_SECONDS,
        after: int = PRICE_AFTER,
        seeded: dict | None = None,
        band: str | None = None,
    ):
        self.prior = float(prior)
        self.after = int(after)
        self.seen: dict = {}
        #: The band every `add` is filed under when the caller names none. A leg
        #: whose draws are all one kind sets it once here instead of at every site.
        self.band = None if band is None else str(band)
        #: `{(partition, band): [seconds]}`. The band split is the whole reason
        #: this class is not one number a partition — see [`banded`].
        self.by_band: dict = {}
        #: `{(partition, band): seconds a candidate}`, an exponential moving
        #: average over this leg's own served candidates, seeded from the last
        #: recorded leg **of the same band**. This is what a seconds share is
        #: converted through, and it is deliberately not [`of`]: that one is a
        #: reserve and takes the worst case, and a reserve is the wrong number to
        #: size a share with.
        self.ema: dict = dict(seeded or {})
        #: What the EMA started at, kept so the record can say whether a leg
        #: inherited a price or discovered its own.
        self.seeded: dict = dict(seeded or {})

    def _cell(self, partition: str, band: str | None) -> tuple:
        return (str(partition), self.band if band is None else str(band))

    def add(self, partition: str, seconds: float, band: str | None = None) -> None:
        """One served candidate, at its price. Files it pooled **and** by band."""
        seconds = float(seconds)
        self.seen.setdefault(str(partition), []).append(seconds)
        cell = self._cell(partition, band)
        self.by_band.setdefault(cell, []).append(seconds)
        # The EMA is the whole point of updating during the leg rather than after
        # it: a price carried in from another leg is a guess about this machine on
        # this day, and `pc20m` measured that guess wrong by 52% six hours later.
        held = self.ema.get(cell)
        self.ema[cell] = seconds if held is None else (1.0 - EMA_ALPHA) * held + EMA_ALPHA * seconds

    def of(self, partition: str) -> float:
        """What to reserve for one more candidate of this partition."""
        measured = self.seen.get(str(partition)) or []
        if len(measured) < self.after:
            everything = [value for values in self.seen.values() for value in values]
            if len(everything) < self.after:
                return self.prior
            return max(everything)
        return max(measured)

    @staticmethod
    def _spread(values: list) -> dict:
        ordered = sorted(values)
        return {
            "candidates": len(ordered),
            "seconds": round(sum(ordered), 2),
            "mean": round(sum(ordered) / len(ordered), 3),
            "median": round(ordered[len(ordered) // 2], 3),
            "min": round(ordered[0], 3),
            "max": round(ordered[-1], 3),
        }

    def table(self) -> dict:
        """The per-partition price table: the thing that sizes the next budget.

        `share` is the realized share of this leg's **engine seconds**, which is
        the quantity `curation.draw_weights.SECONDS_SHARE` is denominated in — so
        a leg says in its own record whether the ruling it ran under came true,
        rather than somebody deriving it from a `price` block afterwards.

        `bands` is the split the next leg seeds from, and the pooled numbers above
        it are kept for continuity with every record already written. **Read the
        band and not the pooled figure when sizing a leg**: `phoenix:classic` reads
        1.2-1.5 s in the near band and 17-31 s on a deep breadth arm, and the
        pooled 12.41 s describes neither.
        """
        total = sum(sum(values) for values in self.seen.values())
        out: dict = {}
        for name, values in sorted(self.seen.items()):
            block = self._spread(values)
            block["share"] = round(sum(values) / total, 4) if total else None
            block["bands"] = {
                band: {
                    **self._spread(held),
                    "share": round(sum(held) / total, 4) if total else None,
                    "ema": round(self.ema[(partition, band)], 3),
                    "seeded_from": (
                        None
                        if (partition, band) not in self.seeded
                        else round(self.seeded[(partition, band)], 3)
                    ),
                }
                for (partition, band), held in sorted(
                    self.by_band.items(), key=lambda item: (str(item[0][1]), item[0][0])
                )
                if partition == name
            }
            out[name] = block
        return out

    def banded(self, band: str | None = None) -> dict:
        """`{partition: seconds a candidate}` for one band — the next leg's seed.

        The EMA and not the mean, so the figure handed forward is the one this leg
        ended on rather than the one it averaged over a machine that was busy for
        the first half of it.
        """
        band = self.band if band is None else str(band)
        return {partition: value for (partition, held), value in self.ema.items() if held == band}


def forget_recorded_prices() -> None:
    """Drop [`recorded_prices`]'s memo. For a guard that redirects the tree."""
    recorded_prices.cache_clear()


def _priced_from_sequence(path, band: str) -> dict:
    """`{partition: mean seconds}` for one arm, off a leg's per-candidate rows.

    The retroactive read. Mean and not median: a share of the clock is a sum, and
    the mean is the only average that reconstructs one.
    """
    import json

    path = Path(path)
    if not path.is_file():
        return {}
    held: dict = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("arm")) != str(band):
                continue
            seconds = row.get("seconds")
            if seconds is None:
                continue
            held.setdefault(str(row.get("partition")), []).append(float(seconds))
    return {name: sum(values) / len(values) for name, values in held.items() if values}


@functools.cache
def recorded_prices(band: str, unit: str = "depth", newest: int = 40) -> tuple[dict, dict]:
    """`(prices, provenance)` — the newest recorded leg that priced this BAND.

    A leg seeds its price from the last leg of the **same band** and never from
    the last leg full stop. `TIDY_render_cv_and_two_reads` measured why on nine
    legs: `phoenix:classic` runs 17-31 s a candidate on the deep breadth arms and
    1.2-1.5 s in the near band, an order of magnitude on one plane under one
    weight, because a near-band re-render is shallow. A breadth leg that inherited
    a near-band price would ask for roughly twenty times the turns the ruling
    wants, and it would do it silently, since every number involved is a plausible
    number of seconds.

    Empty where nothing has priced the band. That is not an error and the caller
    is expected to pilot instead — see [`curation.draw_weights.converted`], which
    refuses rather than converting a share against a price it does not have.

    Records written before the band split carry no `bands` block; they are read
    for their pooled figure only when the caller asks for the band they were taken
    under, and skipped otherwise. An old record cannot say which band it was, so
    guessing would reintroduce exactly the mixing this function exists to stop.

    **Cached, and it has to be.** This walks the leg records and parses a
    `sequence.jsonl` of a few thousand rows for each band it cannot answer from a
    `bands` block — 0.65 s a band, 3.35 s for the five [`curation.depth.DRAWS`],
    and `depth.plan` asks for all five. Uncached that is 3.35 s per plan call
    charged to every guard that plans a leg, which is `tests/README.md`'s rule
    about production code reaching a store. The answer cannot change inside one
    leg: a leg reads it before it renders and the records it reads are finished
    ones. A test that redirects the tree calls [`forget_recorded_prices`] first.
    """
    root = under("curation", unit)
    if not root.is_dir():
        return {}, {"leg": None, "why": f"no {unit} records on this machine"}
    records = sorted(
        (path for path in root.glob(f"*/{unit}.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[: int(newest)]
    for path in records:
        try:
            held = json.loads(path.read_text(encoding="utf-8")).get("price") or {}
        except (OSError, json.JSONDecodeError):
            continue
        prices = {
            name: float(block["bands"][band]["ema"])
            for name, block in held.items()
            if isinstance(block, dict) and str(band) in (block.get("bands") or {})
        }
        source = "the record's own banded price"
        if not prices:
            # A record written before the band split has one pooled number a
            # partition, which is exactly the figure that must not be inherited.
            # Its `sequence.jsonl` carries `arm`, `partition` and `seconds` per
            # row, though, so the band price is *derivable* rather than lost —
            # and deriving it is what stops this feature having a cold start in
            # which no band is ever priced because no leg has run under the code
            # that prices bands.
            prices = _priced_from_sequence(path.parent / "sequence.jsonl", band)
            source = "derived from the leg's sequence.jsonl"
        if prices:
            return prices, {
                "leg": path.parent.name,
                "record": str(path),
                "band": str(band),
                "partitions": len(prices),
                "source": source,
            }
    return {}, {
        "leg": None,
        "band": str(band),
        "why": f"none of the newest {len(records)} {unit} record(s) priced the {band!r} "
        f"band. This leg's own pilot has to set the price",
    }


# --------------------------------------------------------------------------- #
# Making one candidate.
# --------------------------------------------------------------------------- #
class Maker:
    """The band, the map table, the judge and the group table, loaded once.

    A class for [`colorize.Colorizer`]'s reason — the judge is the expensive part
    and loading it per candidate would dominate a short hunt — and **not** that
    class, because that one loads the palette head as well and this leg is
    defined by not asking it anything.
    """

    def __init__(self, name: str, device: str = "auto", log=print, fields: Path | None = None):
        from fractal_wallpapers.curation import colorize
        from fractal_wallpapers.palettes import groups as groups_module

        self.name = str(name)
        self.log = log
        self.device = device
        self.cyclic = colorize.cyclic()
        self.band = colorize.band()
        self.groups = groups_module.member_groups()
        #: Where this maker's dumped fields go, so one (location, mode) iterates
        #: once however many palettes are asked of it. Named by the caller
        #: because a mine keeps its own subtree and a hunt keeps this one; what
        #: is *in* it, and whether a given candidate can be served out of it, is
        #: [`colorize.render`]'s decision and not a caller's.
        self.fields = Path(fields) if fields is not None else fields_dir(self.name)
        self._judge = None

    def judge(self):
        """THE shipped finished-render judge, loaded on first use and kept."""
        from fractal_wallpapers.curation import colorize

        if self._judge is None:
            self._judge = colorize.load_judge(self.device)
        return self._judge

    def recipe_for(self, plan: Try, place: dict, frame: dict) -> recipes.Recipe:
        """The recipe one intention becomes, **before** anything is rendered.

        Every member is known up front — the frame is a lookup, the palette knobs
        are [`finished.recipe`]'s defaults, and the autolevel stamp is the band's
        identity rather than anything the operator measures — so the recipe key is
        too. That is what makes *have we already made this picture* a question a
        hunt can ask before it spends the render, which is the whole reason
        [`curation.candidate_ledger`] exists.

        `mode_params` comes off the intention rather than being pinned empty here,
        which is the whole of what lets a leg name a `(mode, settings)` pair on its
        roster. `recipes.KEYED` holds it, so a varied candidate takes its own key
        and its own file and cannot overwrite the shipped mode's picture.

        `palette` is the same arrangement one member over, and the same sentence
        is true of it: the intention's overrides land on [`finished.recipe`]'s
        defaults, `palette` is keyed, and a drawn `phase` or `cycles` is a new
        picture beside the plain one rather than an overwrite of it. **`mirror`
        stays this function's** — it is the map's bake and not a knob a draw gets
        to turn — so the override is applied over it and an intention naming one is
        refused rather than silently repainting a different map's picture.
        """
        from fractal_wallpapers.curation import colorize
        from fractal_wallpapers.palettes import groups as groups_module

        return recipes.Recipe(
            family=place["family"],
            viewport=frame["viewport"],
            maxiter=int(frame["maxiter"]),
            regime=recipes.CANDIDATE_REGIME,
            mode=plan.mode,
            mode_params=dict(plan.mode_params or {}),
            curve=colorize.CURVE,
            colormap=plan.colormap,
            palette=self.palette_for(plan),
            autolevel=self.stamp_for(plan.mode),
            palette_group=groups_module.group_of(plan.colormap, self.groups),
        )

    def palette_for(self, plan) -> dict:
        """The **whole** palette pass one intention is rendered through.

        One derivation, and that is the whole point of it being a method rather
        than an expression inside [`recipe_for`]: the recipe's `palette` member and
        the pass [`colorize.render`] is handed have to be the same object's value
        or the row is keyed for a picture nobody drew. That is `mine.make`'s
        `mode_params` defect exactly — a member named on the row and dropped on the
        way to the engine — and `tests/test_renderer_agreement.py` is the guard.

        The plain pass is [`finished.recipe`]'s defaults over the map's bake, which
        is what every leg but a varied draw spends. An intention's `palette` is
        **overrides onto** that and never a replacement of it, so a draw cannot
        forget a knob it did not mean to move.

        Two refusals rather than a silent drop. `mirror` is the map's bake — read
        off the cyclic set here — and a draw that turned it would be painting a
        different map's picture under this map's name. A knob the engine does not
        read would be recorded on the row, dropped between here and the spec, and
        would leave the row claiming a pass its picture never had.
        """
        from fractal_wallpapers.labeling import finished

        drawn = dict(getattr(plan, "palette", None) or {})
        if "mirror" in drawn:
            raise RuntimeError(
                "an intention drew `mirror`, which is the colormap's bake and not a palette "
                "knob a draw may turn: a folded map painted unfolded is a different map's "
                "picture under this one's name. Draw the knobs that describe the pass."
            )
        loose = set(drawn) - set(finished.RECIPE_KEYS)
        if loose:
            raise RuntimeError(
                f"{sorted(loose)} is not a palette knob the engine reads "
                f"({', '.join(finished.RECIPE_KEYS)}), so it would be recorded on the row, "
                f"dropped on the way to the engine spec, and leave the row claiming a pass "
                f"its picture never had."
            )
        return finished.recipe(mirror=plan.colormap not in self.cyclic, **drawn)

    def stamp_for(self, mode: str) -> dict | None:
        """The autolevel identity a render in this mode will carry.

        Derivable rather than observed, and that is the point: [`recipes.stamp_of`]
        keeps the operator, the switch and the band's sha256, and drops `acted` on
        purpose — whether the curve fires is a function of the picture, not an
        input to it. So the three members that decide the recipe's name are all
        known before the engine runs.

        Built through [`autolevel.make_stamp`] and not spelled out here. The band
        record calls its digest `_sha256` and the stamp calls it `sha256`, and a
        second spelling of that translation is how a hunt comes to name identical
        pixels differently from the pass that made them — which is exactly what
        happened, and is what this goes through the operator's own function to
        stop happening again.
        """
        from fractal_wallpapers.coloring import autolevel
        from fractal_wallpapers.curation import colorize

        if not autolevel.enabled() or not recipes.autolevel_applies(colorize.kind_of(mode)):
            return recipes.NO_AUTOLEVEL
        return recipes.stamp_of(autolevel.make_stamp(self.band or {}, {}, {}, 0, 0, acted=False))

    def make(self, plan: Try, place: dict, frame: dict, recipe: recipes.Recipe, key: str) -> dict:
        """Render one candidate, judge it, read its colour. The row it becomes.

        Through [`colorize.render`], which is THE one place a curation picture is
        made: the same geometry, the same autolevel switch and the same
        temporary-then-rename as every candidate already in the ledger. A hunt
        that made its pictures its own way would be stocking a ledger with rows
        nothing else could compare against.
        """
        from fractal_wallpapers.curation import colorize
        from fractal_wallpapers.palettes import dominance

        row = {
            "family": place["family"],
            "viewport": frame["viewport"],
            "maxiter": int(frame["maxiter"]),
        }
        started = colorize.tick()
        reported: dict = {}
        picture, stamp = colorize.render(
            row,
            plan.mode,
            plan.colormap,
            self.cyclic,
            pictures_dir(self.name) / f"{key}.jpg",
            level=True,
            band=self.band,
            fields=self.fields,
            reported=reported,
            mode_params=dict(plan.mode_params or {}),
            # The pass the recipe above was keyed under, through the one
            # derivation that built it. A palette named on the row and not handed
            # to the renderer is `mine.make`'s `mode_params` defect one member
            # over: the row says varied and the file is plain.
            palette=self.palette_for(plan),
        )
        verdict = colorize.score_picture(self.judge(), picture)
        reading = dominance.of_picture(picture)
        return {
            "picture": picture,
            "seconds": round(colorize.tick() - started, 3),
            "verdict": verdict,
            "acted": bool((stamp or {}).get("acted")),
            "colour": candidate_ledger.colour_block(reading),
            "cells": list(reading.cells),
            "recipe": recipe,
            # The engine's own word on whether this coloring's texture said
            # anything. Absent on every mode that has no texture. See
            # [`curation.mode_policy.routed_mode`].
            "texture_flat": bool(reported.get("texture_flat")),
        }


def kind_of(mode: str, texture_flat: bool = False) -> str:
    """Which label store's KIND a candidate in this mode belongs to.

    [`curation.budget`]'s two spellings, which are what every record already on
    disk uses and what the sidecar's `head` member is read as. One judge answers
    for both since 2026-08-23; the kind still selects a floor and a slot.

    `texture_flat` is the engine's report that a modulate's texture said nothing,
    which makes the picture the smooth field spent by rank bit for bit — so the
    row is the smooth judge's whatever the recipe's mode says. The routing itself
    is [`curation.mode_policy.routed_mode`]'s and is asked of it rather than
    restated: this is the KIND half, and a second spelling of the rule would agree
    with the first until one of them was edited.
    """
    from fractal_wallpapers.curation import budget as budget_module
    from fractal_wallpapers.curation import colorize, mode_policy

    routed = mode_policy.routed_mode(mode, texture_flat)
    return budget_module.SMOOTH if routed == colorize.SMOOTH_MODE else budget_module.STRANGE


def source_for(name: str, plan: Try, place: dict, frame: dict, at: int) -> dict:
    """One candidate as the *decision row* [`candidate_ledger.row`] reads.

    A hunt has no decision store, so this is the shape and not a row from one: the
    location block the ledger row is built out of, the framing verdict the frame
    lookup produced, and a provenance the ledger can join back on.
    """
    return {
        "key": f"{name}|{at:05d}",
        "run": name,
        "candidate": f"{at:05d}",
        "_store": FROM_HUNT,
        "location": {
            "key": plan.location,
            "partition": plan.partition,
            "ledger": place.get("ledger"),
        },
        "framing": {
            "adopted": bool(frame.get("adopted")),
            "used": frame.get("used"),
            "original": {"viewport": frame.get("original_viewport")},
            "refined": {"viewport": frame.get("refined_viewport")},
        },
    }


# --------------------------------------------------------------------------- #
# The hunt.
# --------------------------------------------------------------------------- #
def shape_of(pools: dict, intended: list) -> dict:
    """What a plan would spend, before anything is rendered. Decides nothing.

    The read `hunt plan` prints: how many candidates of each leg, over how many
    places and partitions, in how many modes and maps. It carries no estimate of
    seconds on purpose — the price is per partition and is measured on the run
    itself, and a number here would be the maxiter model the pool-wide scan
    already showed does not fit.
    """
    return {
        "schema": SCHEMA,
        "drawable": {
            "locations": sum(len(held) for held in pools.values()),
            "by_partition": {name: len(held) for name, held in sorted(pools.items())},
        },
        "planned": len(intended),
        "legs": {
            leg: {
                "candidates": sum(1 for item in intended if item.leg == leg),
                "locations": len({item.location for item in intended if item.leg == leg}),
                "partitions": _tally(item.partition for item in intended if item.leg == leg),
                "cells_asked": len({item.cell for item in intended if item.leg == leg}),
                "maps": len({item.colormap for item in intended if item.leg == leg}),
            }
            for leg in (UNCONDITIONAL, CONDITIONED)
            if any(item.leg == leg for item in intended)
        },
        "modes": _tally(item.mode for item in intended),
    }


def run(
    name: str,
    *,
    seed: int = DEFAULT_SEED,
    budget: float = BUDGET_SECONDS,
    per_location: int = PER_LOCATION,
    unconditional: int = 0,
    conditioned: int = 0,
    cell: str | None = None,
    work_order: dict | None = None,
    device: str = "auto",
    margin: float = framing.MARGIN,
    log=print,
) -> dict:
    """One hunt, end to end. Rows land as candidates land; the record is returned.

    The budget is enforced at the candidate boundary and nothing is started that
    cannot finish inside what is left, so the report can say what was actually
    spent against what was allowed rather than how far past it the last render
    ran.
    """
    started = time.monotonic()
    index = frames(margin, log=log)
    places = scanned(log=log)
    # One read of the ledger, not two. It is the largest store this project has
    # and it grows every leg, so a second pass costs whatever it happens to weigh
    # that week; both questions asked of it here — which places are open, and
    # which recipes already exist — are answered off the same rows.
    stored = candidate_ledger.read()
    opened = opened_locations(stored)
    known = {str(row["key"]) for row in stored}
    pools = drawable(places, opened)
    at_recorded = sum(1 for held in pools.values() for row in held if str(row["key"]) not in index)
    log(
        f"[hunt] {sum(len(held) for held in pools.values()):,} admitted location(s) carry no "
        f"ledger recipe, over {len(pools)} partition(s); {len(opened):,} are already open, "
        f"and {at_recorded:,} draw at the frame they already carry"
    )
    from fractal_wallpapers.curation import draw_weights

    intended = plan(
        pools,
        seed=seed,
        per_location=per_location,
        unconditional=unconditional,
        conditioned=conditioned,
        cell=cell,
        work_order=work_order,
        log=log,
    )
    by_key = {str(row["key"]): row for row in places}
    # Once, before anything renders: the build every row this leg writes will name.
    # See [`candidate_ledger.live_engine`] for why it is not asked per row.
    build = candidate_ledger.live_engine()
    maker = Maker(name, device=device, log=log)
    price = Price()
    rows_file = rows_path(name)
    rows_file.parent.mkdir(parents=True, exist_ok=True)
    scores_file = scores_path(name)
    artifact = _artifact()
    made: list = []
    counts = {
        "planned": len(intended),
        "made": 0,
        "already_in_ledger": 0,
        "failed": 0,
        "stopped_for_budget": 0,
        "autolevel_acted": 0,
        "fields_swept": 0,
    }
    spent = 0.0
    for at, intent in enumerate(intended, start=1):
        place = by_key[intent.location]
        frame = frame_for(place, index)
        recipe = maker.recipe_for(intent, place, frame)
        key = recipes.key_of(recipe)
        if key in known:
            counts["already_in_ledger"] += 1
            continue
        reserve = price.of(intent.partition)
        if spent + reserve > float(budget):
            counts["stopped_for_budget"] = len(intended) - at + 1
            log(
                f"[hunt] stopping at candidate {at}: {intent.partition} is priced at "
                f"{reserve:.2f}s and {float(budget) - spent:.2f}s remain of {budget:.0f}s"
            )
            break
        try:
            result = maker.make(intent, place, frame, recipe, key)
        except Exception as failure:  # noqa: BLE001 — a failed candidate is a recorded fact
            counts["failed"] += 1
            log(f"[hunt] {key} failed: {failure!r}")
            continue
        spent += result["seconds"]
        price.add(intent.partition, result["seconds"], band=intent.leg)
        known.add(key)
        counts["made"] += 1
        counts["autolevel_acted"] += int(result["acted"])
        source = source_for(name, intent, place, frame, at)
        stored = candidate_ledger.row(
            recipe=recipe,
            key=key,
            source=source,
            colour=result["colour"],
            picture=tracked_name(result["picture"]),
            texture_flat=result["texture_flat"],
            engine=build,
        )
        stored["hunt"] = candidate_ledger.hunt_block(
            {"seconds": result["seconds"], **intent.named()}
        )
        scored = candidate_ledger.score_row(
            key=key,
            artifact=artifact,
            regime=recipe.regime.spelled,
            head=kind_of(intent.mode, result["texture_flat"]),
            read=result["verdict"],
            source=source,
        )
        _append(rows_file, stored)
        _append(scores_file, scored)
        made.append(
            {
                "key": key,
                "leg": intent.leg,
                "location": intent.location,
                "partition": intent.partition,
                "mode": intent.mode,
                "colormap": intent.colormap,
                "palette_group": recipe.palette_group,
                "drawn_for": intent.cell,
                "cells": result["cells"],
                "hit": intent.cell in result["cells"],
                "p_ge4": round(float(result["verdict"].get("p_ge4") or 0.0), 6),
                "p_ge3": round(float(result["verdict"].get("p_ge3") or 0.0), 6),
                "seconds": result["seconds"],
                "picture": tracked_name(result["picture"]),
            }
        )
        if counts["made"] % 25 == 0:
            from fractal_wallpapers.curation import colorize

            # A hunt gives one location a handful of candidates and opens
            # hundreds of them, so its dumped fields are working and not record.
            counts["fields_swept"] += colorize.sweep_fields(maker.fields)
            log(
                f"[hunt] {counts['made']:,} made, {spent:.0f}s of {budget:.0f}s spent "
                f"({spent / max(1, counts['made']):.2f}s each)"
            )
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": name,
        "config": {
            "seed": seed,
            "budget_seconds": float(budget),
            "per_location": int(per_location),
            "unconditional": int(unconditional),
            "conditioned": int(conditioned),
            "cell": cell,
            "work_order": dict(work_order or {}),
            "partition_draw_weights": draw_weights.table(),
            "margin": float(margin),
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
        },
        "population": {
            "scanned_admitted": len(places),
            "already_open": len(opened),
            "unopened_drawable": sum(len(held) for held in pools.values()),
            "unopened_at_recorded_frame": at_recorded,
            "unopened_wanting_framing": len(
                unframed([row for held in pools.values() for row in held], index)
            ),
            "by_partition": {name_: len(held) for name_, held in sorted(pools.items())},
        },
        "counts": counts,
        "budget": {
            "allowed": float(budget),
            "spent": round(spent, 2),
            "share": round(spent / float(budget), 4) if budget else None,
            "wall_seconds": round(time.monotonic() - started, 2),
        },
        "price": price.table(),
        "legs": _legs(made),
        "coverage": coverage(made),
        "made": made,
        "rows_path": tracked_name(rows_file),
        "scores_path": tracked_name(scores_file),
    }
    path = record_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    log(
        f"[hunt] {counts['made']:,} candidate(s) in {spent:.0f}s of {budget:.0f}s — "
        f"{tracked_name(path)}"
    )
    return record


def _artifact() -> str:
    """The sha256 of the judge that is shipped right now, read at call time."""
    from fractal_wallpapers.curation import floors

    return floors.live_stamp(floors.SCORING_HEAD)


def _append(path: Path, row: dict) -> None:
    """One row, appended and flushed. What makes a killed hunt a usable partial."""
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _legs(made: list) -> dict:
    """What each leg bought: candidates, places, and how often its ask landed."""
    out: dict = {}
    for leg in (UNCONDITIONAL, CONDITIONED):
        held = [row for row in made if row["leg"] == leg]
        if not held:
            continue
        hits = [row for row in held if row["hit"]]
        out[leg] = {
            "candidates": len(held),
            "locations": len({row["location"] for row in held}),
            "seconds": round(sum(row["seconds"] for row in held), 2),
            "drawn_for_delivered": len(hits),
            "delivery_rate": round(len(hits) / len(held), 4),
            "cells_asked": len({row["drawn_for"] for row in held}),
            "cells_delivered": len({cell for row in held for cell in row["cells"]}),
        }
    return out


def coverage(made: list) -> dict:
    """What this hunt added over the census's own axes. Counts, not verdicts."""
    return {
        "candidates": len(made),
        "locations": len({row["location"] for row in made}),
        "partitions": _tally(row["partition"] for row in made),
        "modes": _tally(row["mode"] for row in made),
        "palette_groups": len({row["palette_group"] for row in made}),
        "cells": _tally(cell for row in made for cell in row["cells"]),
        "dominant_in_none": sum(1 for row in made if not row["cells"]),
    }


def _tally(values) -> dict:
    out: dict = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


# --------------------------------------------------------------------------- #
# Folding a hunt into the ledger.
# --------------------------------------------------------------------------- #
def merge(name: str, log=print) -> dict:
    """Upsert one hunt's two files into the ledger and its sidecar.

    Separate from the hunt for the reason in the module docstring — the ledger is
    rewritten whole on every upsert — and idempotent for the reason every other
    store here is: [`records.upsert_file`] keys on the recipe, so merging a hunt
    twice writes the same bytes and merging a killed hunt's partial is the same
    operation as merging a finished one's.

    Through [`candidate_ledger.merge`] and never the two writers under it, so the
    manifests move with the rows. `recorded` on the report is what they now say.
    """
    rows = _read(rows_path(name))
    scores = _read(scores_path(name))
    if not rows:
        raise HuntRefused(
            f"{tracked_name(rows_path(name))} holds no row, so there is nothing to merge. "
            f"A hunt writes its rows as it makes them; an empty file means none landed."
        )
    written = candidate_ledger.merge(rows, scores, log=log)
    total, new = written["ledger"]["rows"], written["ledger"]["new"]
    report = {
        "schema": SCHEMA,
        "name": name,
        "merged": len(rows),
        "ledger": written["ledger"],
        "scores": written["scores"],
        "recorded": written["recorded"],
        # What this leg re-rendered because the retention rule had already
        # deleted it: a floor, reported and never prevented. See
        # [`retention.repeat_draws`].
        "repeat_draws": written["repeat_draws"],
        "pruned": written["pruned"],
        "locations_added": len({str((row.get("location") or {})["key"]) for row in rows}),
    }
    log(
        f"[hunt] merged {len(rows):,} row(s): the ledger holds {total:,} recipes, "
        f"{new:,} of them new"
    )
    return report


def _read(path: Path) -> list:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


# --------------------------------------------------------------------------- #
# The sheet.
# --------------------------------------------------------------------------- #
#: How many candidates of each leg the contact sheet shows, strongest first. A
#: hunt makes hundreds and the page is for one judgement — whether forcing a
#: colour onto a place degrades the picture — which a few dozen answers.
SHEET_ROWS = 36


def contact_sheet(name: str, record: dict, output: Path | None = None, rows: int = SHEET_ROWS):
    """What the hunt admitted, with the conditioned candidates called out apart.

    Apart and not mixed in, because they are the question. Forcing a colour onto a
    place is exactly where quality could quietly degrade, and no score on this
    page can answer that — the judge already scored them and the judge is what is
    being checked. The two halves are laid out the same way so the comparison is
    the eye's.
    """
    import html

    from fractal_wallpapers.curation import sheet as sheet_module

    output = hunt_dir(name) / "contact_sheet.html" if output is None else Path(output)
    made = list(record.get("made") or [])
    counts = record.get("counts") or {}
    budget_block = record.get("budget") or {}
    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>hunt {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}</style>",
        f"<h1>hunt {html.escape(name)}</h1>",
        f"<p class='lede'>{counts.get('made', 0):,} candidate(s) made in "
        f"{budget_block.get('spent')}s of {budget_block.get('allowed')}s, over "
        f"{(record.get('coverage') or {}).get('locations', 0):,} location(s) that carried no "
        f"ledger recipe before. Every one is recorded; no quality bar admitted any of them. "
        f"Rendered at the frame the refinement scan chose at margin "
        f"{(record.get('config') or {}).get('margin')}.</p>",
        _legs_html(record.get("legs") or {}, record.get("config") or {}),
    ]
    for leg, heading, lede in (
        (
            CONDITIONED,
            f"Conditioned on {(record.get('config') or {}).get('cell')}",
            "The map was drawn from the carrier table for that cell and the palette head "
            "was never asked. Its colour is read off its own render, so a candidate whose "
            "cells do not include the target is a normal candidate that came out another "
            "colour. This is the half to look at: forcing a colour onto a place is where "
            "quality could quietly degrade, and that is an eye's question.",
        ),
        (
            UNCONDITIONAL,
            "Unconditional",
            "Fresh places, a shallow spread each, the palette stratified across the "
            "codebook's cells rather than picked by the head.",
        ),
    ):
        held = sorted((row for row in made if row["leg"] == leg), key=lambda row: -row["p_ge4"])[
            :rows
        ]
        if not held:
            continue
        lines += [
            f"<h2>{html.escape(heading)} ({len(held)} strongest of "
            f"{sum(1 for row in made if row['leg'] == leg)})</h2>",
            f"<p class='lede'>{html.escape(lede)}</p>",
            "<div class='grid'>" + "".join(_card(row, sheet_module) for row in held) + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _legs_html(legs: dict, config: dict) -> str:
    import html

    if not legs:
        return ""
    body = "".join(
        f"<tr><th>{html.escape(name)}</th><td>{block['candidates']:,} candidate(s) over "
        f"{block['locations']:,} place(s), {block['seconds']}s; the colour it asked for "
        f"landed {block['drawn_for_delivered']:,} times "
        f"({block['delivery_rate']:.1%}); {block['cells_asked']} cell(s) asked for, "
        f"{block['cells_delivered']} delivered</td></tr>"
        for name, block in legs.items()
    )
    return f"<h2>What each leg bought</h2><table>{body}</table>"


def _card(row: dict, sheet_module) -> str:
    import html

    source = Path(rehome(row["picture"])) if row.get("picture") else None
    body = (
        f'<img src="{sheet_module.thumbnail(source)}" alt="">'
        if source is not None and source.is_file()
        else '<div class="missing">no picture on disk</div>'
    )
    facts = [
        f"{row['partition']} - {row['mode']} - {row['palette_group']}",
        f"map {row['colormap']}, drawn for {row['drawn_for']}"
        + (" - DELIVERED" if row.get("hit") else ""),
        f"dominant in {', '.join(row.get('cells') or []) or 'nothing'}",
        f"P(>=4) {row['p_ge4']:.4f}, P(>=3) {row['p_ge3']:.4f}, {row['seconds']}s",
    ]
    caption = "".join(f"<li>{html.escape(line)}</li>" for line in facts)
    return (
        f'<figure><div class="frame">{body}</div>'
        f"<figcaption><b>{html.escape(row['key'])}</b><ul>{caption}</ul></figcaption></figure>"
    )


__all__ = [
    "BUDGET_SECONDS",
    "CONDITIONED",
    "DEFAULT_SEED",
    "FRAMES_NAME",
    "FROM_HUNT",
    "PER_LOCATION",
    "FIELDS",
    "PICTURES",
    "EMA_ALPHA",
    "PRICE_AFTER",
    "PRIOR_SECONDS",
    "forget_recorded_prices",
    "recorded_prices",
    "RECORD_NAME",
    "ROWS_NAME",
    "SCHEMA",
    "SCORES_NAME",
    "SHEET_ROWS",
    "UNCONDITIONAL",
    "UNIT",
    "HuntRefused",
    "Maker",
    "Price",
    "Stratifier",
    "Try",
    "build_frames",
    "chosen_frame",
    "conditioned_maps",
    "contact_sheet",
    "coverage",
    "drawable",
    "frame_for",
    "frames",
    "frames_backup_path",
    "frames_durable",
    "frames_manifest_path",
    "frames_path",
    "fields_dir",
    "hunt_dir",
    "kind_of",
    "merge",
    "modes_for",
    "opened_locations",
    "pictures_dir",
    "plan",
    "record_path",
    "recorded_frame",
    "rows_path",
    "run",
    "scan_path",
    "scanned",
    "scores_path",
    "seed_of",
    "shape_of",
    "source_for",
    "spread",
    "unframed",
    "wants_framing",
]
