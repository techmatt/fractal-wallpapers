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

**Unconditional** buys breadth. Locations come from the scanned pool that carry
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

## The frame is looked up, not recomputed

A recipe carries the frame it was drawn at, so a hunt has to choose one. It
chooses the frame the pool-wide refinement scan already chose at
[`framing.MARGIN`] — the winner where that scan adopted, the recorded frame where
it refused — read out of the scan's record. **No refinement machinery runs
here**: this is a lookup, the record says which margin it was taken at, and a
record taken at another margin is refused rather than reinterpreted.

That the frame is part of the recipe is what makes the lookup safe. A candidate
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

import hashlib
import itertools
import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, framing, recipes
from fractal_wallpapers.paths import rehome, tracked_name, under

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

#: The pool-wide refinement scan a hunt looks its frames up in.
SCAN_UNIT = "frame_refit"
SCAN_NAME = "scan.jsonl"

#: The thin index derived from that scan: one row a location, the frame it chose
#: and nothing else. The scan is 98 MB of every rung and a hunt asks it one
#: question — parsing all of it per run is a minute of wall clock buying a lookup
#: table that does not change between runs.
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
    """
    source = scan_path()
    if not source.is_file():
        raise HuntRefused(
            f"there is no refinement scan at {tracked_name(source)}, so a hunt has no frame "
            f"to draw at. The scan is resumable and regenerates in about three and a half "
            f"hours; the curation README says how."
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
    """`{location key: the frame the scan chose}`, off the index, built on first ask."""
    path = frames_path()
    if rebuild or not path.is_file():
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


def drawable(rows: list, index: dict, opened: set) -> dict:
    """`{partition: [rows]}` — scanned, admitted, and carrying no ledger recipe yet.

    A location the scan does not hold is dropped rather than drawn at its recorded
    frame. The frame is part of the recipe and *the frame the scan chose* is what
    this hunt is specified to draw at, so a location with no scan row is one it
    cannot honestly render.
    """
    out: dict = {}
    for row in rows:
        key = str(row["key"])
        if key in opened or key not in index:
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

    def named(self) -> dict:
        """This intention as the ledger row carries it."""
        return {
            "leg": self.leg,
            "mode": self.mode,
            "colormap": self.colormap,
            "drawn_for": self.cell,
            "k": self.k,
        }


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

    Interleaved and not blocked, which is the whole of it. A work order reading
    `julia:mandelbrot 19, mandelbrot 6, ...` as nineteen consecutive turns spends
    the first forty-four-turn round's opening nineteen on one partition, and a leg
    shorter than that round never reaches the second — a proportional order that
    is not proportional over any prefix is a work order that only acts if the leg
    is long. Each partition's k-th turn is placed at `(k + 0.5) / weight` and the
    turns are sorted on that, so every prefix is proportional too.
    """
    placed = []
    for name in order:
        weight = max(1, int((weights or {}).get(name, 1)))
        placed += [((at + 0.5) / weight, name) for at in range(weight)]
    return [name for _at, name in sorted(placed, key=lambda item: (item[0], item[1]))]


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
    from fractal_wallpapers.curation import colorize, mode_policy
    from fractal_wallpapers.palettes import dominance

    maps = list(colorize.pool(seed) if pool is None else pool)
    # The accepted roster, not the engine's production one: a hunt buys more of a
    # mode, and [`curation.mode_policy`] weight 0 is the ruling that this project
    # has stopped buying that one. Its existing material stands.
    roster = tuple(mode_policy.accepted())
    breadth = _leg(
        UNCONDITIONAL,
        spread(pools, -(-int(unconditional) // max(1, per_location)), seed),
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

    def __init__(self, prior: float = PRIOR_SECONDS, after: int = PRICE_AFTER):
        self.prior = float(prior)
        self.after = int(after)
        self.seen: dict = {}

    def add(self, partition: str, seconds: float) -> None:
        self.seen.setdefault(str(partition), []).append(float(seconds))

    def of(self, partition: str) -> float:
        """What to reserve for one more candidate of this partition."""
        measured = self.seen.get(str(partition)) or []
        if len(measured) < self.after:
            everything = [value for values in self.seen.values() for value in values]
            if len(everything) < self.after:
                return self.prior
            return max(everything)
        return max(measured)

    def table(self) -> dict:
        """The per-partition price table: the thing that sizes the next budget."""
        out: dict = {}
        for name, values in sorted(self.seen.items()):
            ordered = sorted(values)
            out[name] = {
                "candidates": len(ordered),
                "seconds": round(sum(ordered), 2),
                "mean": round(sum(ordered) / len(ordered), 3),
                "median": round(ordered[len(ordered) // 2], 3),
                "min": round(ordered[0], 3),
                "max": round(ordered[-1], 3),
            }
        return out


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
        """
        from fractal_wallpapers.curation import colorize
        from fractal_wallpapers.labeling import finished
        from fractal_wallpapers.palettes import groups as groups_module

        return recipes.Recipe(
            family=place["family"],
            viewport=frame["viewport"],
            maxiter=int(frame["maxiter"]),
            regime=recipes.CANDIDATE_REGIME,
            mode=plan.mode,
            mode_params={},
            curve=colorize.CURVE,
            colormap=plan.colormap,
            palette=finished.recipe(mirror=plan.colormap not in self.cyclic),
            autolevel=self.stamp_for(plan.mode),
            palette_group=groups_module.group_of(plan.colormap, self.groups),
        )

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
    pools = drawable(places, index, opened)
    log(
        f"[hunt] {sum(len(held) for held in pools.values()):,} scanned location(s) carry no "
        f"ledger recipe, over {len(pools)} partition(s); {len(opened):,} are already open"
    )
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
        frame = index[intent.location]
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
        price.add(intent.partition, result["seconds"])
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
            "margin": float(margin),
            "regime": recipes.CANDIDATE_REGIME.spelled,
            "judge_artifact": artifact,
        },
        "population": {
            "scanned_admitted": len(places),
            "already_open": len(opened),
            "unopened_drawable": sum(len(held) for held in pools.values()),
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
    "PRICE_AFTER",
    "PRIOR_SECONDS",
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
    "frames",
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
    "rows_path",
    "run",
    "scan_path",
    "scanned",
    "scores_path",
    "seed_of",
    "shape_of",
    "source_for",
    "spread",
]
