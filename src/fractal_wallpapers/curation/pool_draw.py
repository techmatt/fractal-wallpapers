"""A uniform draw over the pool's locations, one seat-ranked picture each.

Every other sheet this project cuts is aimed: a band around a bar, a mode nobody
has scored, the top of a ranked queue. Those measure a *correction*. This one
measures a **base rate** — what fraction of the places a gallery could seat carry
some property — and a base rate can only be read off a draw that was not aimed at
anything.

So the population is stated once and taken whole: every location holding at least
one candidate row that clears its own mode's bar in
[`curation.headroom.bars`], read fresh. That is the same set the census counts
as supply and the same set a gallery leg chooses from, which is what makes a rate
measured here a rate about the pool rather than about a slice of it.

## One picture per location, and it is the one the solve would seat

A location carries dozens of candidates that differ only in how they were
colored, and showing a person a random one would measure the palette draw as much
as the place. So each drawn location is represented by its **best-ranked clearing
row** under [`curation.solve.ranking`] — the row a seating pass walking this pool
would reach first. The picture on the card is therefore the picture the project
would actually ship from that place, which is the only render of it a question
about a gallery cap can honestly be asked about.

The draw is over **locations**, uniformly and seeded, after the per-location
choice has been made. Drawing over rows instead would weight a place by how many
recipes happen to sit on it, which is a fact about where mining legs have been.

## What a unit carries out of here

The plan is a finished-render sheet plan — [`labeling.sheets.units_from_plan`]
reads it unchanged — because the picture is a finished render even though the
verdict will key on the place. Three things beyond the recipe travel on every
unit:

* `leveled`, the `<stem>.leveled/` directory beside the candidate's own picture
  where the autolevel operator acted. Without it a rebuild of this sheet renders
  a different picture under the same identity, silently — the build does not
  notice, because it skips a unit whose picture is already on disk.
* `selected_on`, the reading the row was **drawn** on, at candidate geometry. The
  sheet renders at label geometry and a number read there is a different number;
  carrying both is what lets a later reader attribute a disagreement to the
  regime rather than to the labeler.
* `suggestion`, where a prefill was asked for. See [`prefill`].

Nothing here writes into a label store. The plan is the caller's decision and the
registration is where it is recorded; a pin over these units is
[`labeling.attributes.write_pin`]'s and is taken in its own step.

## This is a pool-holding leg

It reads the candidate ledger and the whole score sidecar, resolves the rank key
over both, and holds the pool. Nothing else that loads the pool may run beside
it — see the repository's own rule about one pool-holding process per box.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, headroom, solve
from fractal_wallpapers.paths import Tiers, rehome

#: The schema the plan's record carries.
SCHEMA = 1

#: How a plan and its record are named under whatever directory a caller gives.
PLAN_NAME = "plan.jsonl"
RECORD_NAME = "draw.json"


class DrawRefused(RuntimeError):
    """A draw that cannot be taken, or a population that cannot answer for itself."""


# --------------------------------------------------------------------------- #
# The population.
# --------------------------------------------------------------------------- #
def clearing_population(log=print) -> tuple[list, dict, dict]:
    """`(the clearing candidates, the bar table, what the pool refused)`.

    [`headroom`]'s population and [`headroom`]'s bars, not a second opinion about
    either: a draw over a set the census does not agree is supply is a draw
    nobody can quote a rate off.
    """
    candidates, _costs, refused = headroom.population(log=log)
    table = headroom.bars(candidates)
    clearing = headroom.clearing(candidates, table)
    log(
        f"[pool-draw] {len(clearing):,} clearing candidates over "
        f"{len({c.location for c in clearing}):,} locations, from {len(candidates):,} in the pool"
    )
    return clearing, table, refused


def seat_ranked(clearing: list, log=print) -> tuple[dict, dict | None, dict | None]:
    """`({location: the candidate a seating pass would reach first}, the order, its record)`.

    The order is [`solve.ranking`]'s under the leg's own default key, so "the
    picture the solve would seat" is that function's answer and never a second
    spelling of it. The mapping itself comes back because resolving it reads two
    more stores and no caller should pay for that twice.
    """
    order, coverage = solve.ranking_for(clearing, log=log)
    rank = solve.ranking(order)
    best: dict = {}
    for candidate in clearing:
        held = best.get(candidate.location)
        if held is None or rank(candidate) < rank(held):
            best[candidate.location] = candidate
    return best, order, coverage


def draw_locations(locations, n: int, seed: int) -> list[str]:
    """`n` locations, uniformly at random, seeded. Refuses a population too small.

    Sorted before the draw: a seeded sample over a set whose iteration order is a
    hash is a sample nobody can take twice.
    """
    ordered = sorted(locations)
    if n > len(ordered):
        raise DrawRefused(
            f"asked for {n:,} locations and the clearing population holds {len(ordered):,}. "
            f"A draw that takes the whole population is not a sample of it."
        )
    return random.Random(seed).sample(ordered, n)


# --------------------------------------------------------------------------- #
# The units.
# --------------------------------------------------------------------------- #
def leveled_dir(picture: str | None, tiers: Tiers | None = None) -> str | None:
    """The `<stem>.leveled/` beside a candidate's picture, where the operator acted.

    `None` where it did not, which is the common case and is not a gap: the
    operator is offered every eligible render and declines most of them, and a
    unit with no directory renders through the plain map exactly as its candidate
    did.

    **The derivation is [`candidate_ledger.sweep._delete_colormap`]'s, spelled
    the same way**, and that is what makes a prune unable to take a live
    directory: the two read the same expression off two rows' own pictures, so a
    prune could only reach a surviving row's colormap if a dropped row and a
    surviving row named one picture. `tests/test_leveled_identity.py` is the pin.

    `tiers` for a draw resolving a whole plan — see
    [`fractal_wallpapers.paths.rehome`] for what the per-call resolution costs.
    """
    if not picture:
        return None
    where = rehome(picture, tiers)
    if where is None:
        return None
    where = Path(where)
    directory = where.parent / f"{where.stem}.leveled"
    return str(directory) if directory.is_dir() else None


def unit_of(candidate, row: dict, rank_value: float | None, tiers: Tiers | None = None) -> dict:
    """One plan unit: the recipe the candidate was made from, and its provenance."""
    recipe = row.get("recipe") or {}
    missing = [
        key
        for key in ("family", "viewport", "maxiter", "mode", "curve", "colormap", "palette")
        if recipe.get(key) is None
    ]
    if missing:
        raise DrawRefused(
            f"ledger row {row.get('key')!r} names no {', '.join(missing)}; its picture cannot "
            f"be rebuilt and a verdict cast on it would be about nothing"
        )
    return {
        "family": recipe["family"],
        "viewport": recipe["viewport"],
        "maxiter": int(recipe["maxiter"]),
        "mode": recipe["mode"],
        "mode_params": dict(recipe.get("mode_params") or {}),
        "curve": recipe["curve"],
        "colormap": recipe["colormap"],
        "recipe": recipe["palette"],
        "leveled": leveled_dir(row.get("picture"), tiers),
        # The reading the row was DRAWN on, at the regime it was drawn at. The
        # sheet reads its own numbers off the picture it renders; these two are
        # not the same number and both are wanted.
        "selected_on": {
            "candidate": candidate.key,
            "regime": recipe.get("regime"),
            "p_ge4": round(float(candidate.score), 6),
            "p_ge3": round(float(candidate.p_ge3), 6),
            "rank": None if rank_value is None else round(float(rank_value), 6),
            "judge": candidate.kind,
        },
        "facts": [f"pool candidate {candidate.key} · {candidate.partition}"],
    }


def units_for(drawn: list[str], best: dict, order: dict | None) -> list[dict]:
    """A plan unit per drawn location, its ledger row fetched in one streamed pass."""
    keys = [best[location].key for location in drawn]
    rows = candidate_ledger.by_key(keys)
    missing = [key for key in keys if key not in rows]
    if missing:
        raise DrawRefused(
            f"{len(missing)} drawn candidate(s) are in the pool and not in the ledger, e.g. "
            f"{missing[:3]}. The pool is built from the ledger, so this is a store that moved "
            f"under the draw."
        )
    # Once for the plan, not once a unit: [`fractal_wallpapers.paths.rehome`].
    tiers = Tiers.current()
    out = []
    for location in drawn:
        candidate = best[location]
        value = None if order is None else order.get(candidate.key)
        out.append(unit_of(candidate, rows[candidate.key], value, tiers))
    return out


# --------------------------------------------------------------------------- #
# The prefill.
# --------------------------------------------------------------------------- #
def seed_vectors(aliases, gallery: Path, log=print) -> tuple[list, list[str], list[str]]:
    """`(vectors, the aliases that resolved, the ones that did not)`.

    An alias names a seat in a tentative gallery, the seat carries its location
    key, and the key is what the neutral-embedding store holds a vector for. Both
    joins can miss and they miss for different reasons — an alias nobody seated,
    and a place nothing has embedded — so the caller is told which.
    """
    import numpy

    from fractal_wallpapers.curation import embeddings

    wanted = list(dict.fromkeys(str(alias) for alias in aliases))
    seats: dict[str, str] = {}
    path = Path(gallery)
    path = path / "gallery.jsonl" if path.is_dir() else path
    if not path.is_file():
        raise DrawRefused(f"{path} does not exist; a seed alias is resolved against a gallery")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        seat = json.loads(line)
        alias = str(seat.get("alias") or "")
        if alias in wanted:
            seats[alias] = str(seat.get("location"))

    rows, matrix = embeddings.load()
    at = {str(row.get("key")): index for index, row in enumerate(rows)}
    vectors, resolved, lost = [], [], []
    for alias in wanted:
        location = seats.get(alias)
        index = at.get(location) if location is not None else None
        if index is None:
            lost.append(alias)
            continue
        vectors.append(matrix[index])
        resolved.append(alias)
    log(f"[pool-draw] {len(resolved)} of {len(wanted)} seed aliases carry a neutral embedding")
    return ([] if not vectors else list(numpy.stack(vectors))), resolved, lost


def prefill(units: list[dict], drawn: list[str], vectors, log=print) -> dict:
    """Prefill each unit by cosine to the seeds' centroid, cut at the median.

    A **hint**, and the page says so: the threshold is the median over the sheet's
    own units, so exactly half the page is prefilled either way and the prefill
    carries no claim about the base rate it is being used to measure. A sitting
    that took a prefill from a fitted threshold would be a sitting whose answer
    was partly the threshold's.

    The cosine travels onto the row as its `columns` reading, because it is the
    only number on the card and a reader a month later has to be able to see what
    the suggestion was made of.
    """
    import numpy

    from fractal_wallpapers.curation import embeddings

    rows, matrix = embeddings.load()
    at = {str(row.get("key")): index for index, row in enumerate(rows)}
    centroid = numpy.stack(vectors).mean(axis=0)
    norm = float(numpy.linalg.norm(centroid))
    if norm == 0.0:
        raise DrawRefused("the seed vectors cancel to zero; there is no centroid to measure from")
    centroid = centroid / norm

    cosines: list[float | None] = []
    for location in drawn:
        index = at.get(location)
        cosines.append(None if index is None else float(matrix[index] @ centroid))
    read = [value for value in cosines if value is not None]
    if len(read) != len(drawn):
        raise DrawRefused(
            f"{len(drawn) - len(read)} drawn location(s) have no neutral embedding, so a "
            f"prefill would mean one thing on some cards and nothing on others. A sheet "
            f"prefills all of its units or none of them."
        )
    threshold = float(numpy.median(numpy.array(read)))
    above = 0
    for unit, value in zip(units, cosines, strict=True):
        # 1 is the first class — `spiral` — and the ordinal is what a page casts.
        unit["suggestion"] = 1 if value >= threshold else 2
        unit["columns"] = {"cos_to_seeds": round(float(value), 6)}
        above += int(value >= threshold)
    log(f"[pool-draw] prefilled {above} of {len(units)} above cosine {threshold:.6f}")
    return {
        "rule": (
            "cosine to the centroid of the seeds' neutral embeddings, cut at the median over "
            "this sheet's own units — a hint the labeler flips, carrying no claim about the "
            "rate it is being used to measure"
        ),
        "threshold": round(threshold, 6),
        "suggested_first_class": above,
        "range": [round(min(read), 6), round(max(read), 6)],
    }


# --------------------------------------------------------------------------- #
# The leg.
# --------------------------------------------------------------------------- #
def write(directory: Path, units: list[dict], record: dict) -> tuple[Path, Path]:
    """Write the plan and its record. Returns both paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    plan = directory / PLAN_NAME
    with plan.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
    document = directory / RECORD_NAME
    document.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return plan, document


def draw(
    n: int,
    seed: int,
    directory: Path,
    like=(),
    gallery: Path | None = None,
    log=print,
) -> dict:
    """Take the draw, write the plan, and return the record of what it was.

    `like` are gallery aliases whose neutral embeddings seed the prefill; without
    them, or with fewer than [`MINIMUM_SEEDS`] of them resolving, the sheet ships
    unprefilled and the record says so.
    """
    clearing, table, refused = clearing_population(log=log)
    best, order, coverage = seat_ranked(clearing, log=log)

    drawn = draw_locations(best, n, seed)
    units = units_for(drawn, best, order)

    prefilled: dict | None = None
    seeds_resolved: list[str] = []
    seeds_lost: list[str] = []
    if like:
        vectors, seeds_resolved, seeds_lost = seed_vectors(like, gallery, log=log)
        if len(seeds_resolved) < MINIMUM_SEEDS:
            log(
                f"[pool-draw] {len(seeds_resolved)} seed(s) resolved, under the "
                f"{MINIMUM_SEEDS} a prefill needs; shipping the sheet unprefilled"
            )
        else:
            prefilled = prefill(units, drawn, vectors, log=log)

    modes: dict[str, int] = {}
    partitions: dict[str, int] = {}
    for location in drawn:
        modes[best[location].mode] = modes.get(best[location].mode, 0) + 1
        partitions[best[location].partition] = partitions.get(best[location].partition, 0) + 1

    record = {
        "schema": SCHEMA,
        "rule": (
            "uniform random over the locations holding at least one candidate row that clears "
            "its own mode's bar in headroom.bars, one unit each, represented by the "
            "best-ranked clearing row a seating pass would reach first"
        ),
        "seed": seed,
        "drawn": len(drawn),
        "population": {
            "clearing_locations": len(best),
            "clearing_rows": len(clearing),
            "pool_refused": refused,
            "bars": {
                "on_default": table["on_default"],
                "on_fallback": table["on_fallback"],
                "default": table["default"],
                "fallback": table["fallback"],
            },
        },
        # **The key this draw's `best-ranked` actually meant**, off the coverage
        # record the resolver wrote rather than off a constant here, so a cascade
        # draw and a rank-key draw are told apart by their own records. The two
        # disagree about which row represents a place for most of the pool, so a
        # sheet whose record does not name the order is a sheet nobody can
        # attribute later. `rank_key` below is the coverage record whole and keeps
        # its 2026-08 name: every drawn record on disk carries it.
        "key": solve.ordered_by(order, solve.DEFAULT_KEY, coverage),
        "rank_key": coverage,
        "modes": dict(sorted(modes.items(), key=lambda item: (-item[1], item[0]))),
        "partitions": dict(sorted(partitions.items(), key=lambda item: (-item[1], item[0]))),
        "leveled_units": sum(1 for unit in units if unit.get("leveled")),
        "prefill": prefilled,
        "seeds": {
            "asked": [str(alias) for alias in like],
            "resolved": seeds_resolved,
            "unresolved": seeds_lost,
            "minimum": MINIMUM_SEEDS,
        },
        "drawn_at": _now(),
    }
    plan, document = write(directory, units, record)
    record["plan"] = str(plan)
    record["record"] = str(document)
    document.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


#: How many seed aliases have to resolve before a prefill means anything. Under
#: this the centroid is one or two pictures and the hint is noise wearing a
#: threshold, so the sheet ships blind and the record says which seeds were lost.
MINIMUM_SEEDS = 5


def _now() -> str:
    from fractal_wallpapers.labeling import store

    return store.now()


__all__ = [
    "MINIMUM_SEEDS",
    "PLAN_NAME",
    "RECORD_NAME",
    "SCHEMA",
    "DrawRefused",
    "clearing_population",
    "draw",
    "draw_locations",
    "leveled_dir",
    "prefill",
    "seat_ranked",
    "seed_vectors",
    "unit_of",
    "units_for",
    "write",
]
