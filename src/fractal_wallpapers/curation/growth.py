"""What more mining buys, at every gallery size — measured by subsampling the pool.

The question this answers is the one a mining leg is bought to move: **does N
candidates' worth of mining buy a better gallery, and at which sizes?** It cannot
be answered from the history, because the history was never snapshotted — the
candidate ledger is a live store that grows and is pruned, and no copy of "the
pool as it stood in August" exists to solve against.

So it is answered the other way round, from the pool as it stands: draw a
**fraction** of the mining that made this pool, solve the gallery over what that
fraction produced, and read the curve. A pool at 1/8 is not the pool of the day it
held that many rows — the modes, the frames and the judge have all moved since —
but it is an honest answer to "what would this much of this kind of mining have
bought", which is the decision a mining leg is actually taken against.

Re-run after each mining leg, this accumulates a chronological series on its own:
each stamped run is a new folder, the earlier ones are never rewritten, and the
top rung of run k+1 is the pool run k could only reach by extrapolating.

## The unit of subsampling is a VISIT, never a row

A **visit** is `(location, leg)` — one mining leg opening one place. Drawing rows
would be drawing a fraction of each visit's palettes, which is not a smaller
history: it is the same history with the depth arm silently disabled, and it would
price a place at a twelfth of what a place costs. Drawing visits keeps the shape
of what mining actually does — it opens places, and each place it opens comes with
the whole palette set that opening bought.

Every candidate row from a drawn visit comes with it, whole. Rows whose leg is
unknown — the pre-ledger imports, which carry no `provenance.run` — form **one
pseudo-leg per location**, so each such location is a visit of its own rather than
one enormous visit nothing can subsample.

## Restricting the pool is the only change

`solve` is called exactly as `curate solve run` calls it: same eligibility bar,
one wallpaper per location, the twin rule, the colour allowances, the mode floors,
the four objective tiers, the production draw seed and rows-per-seat. Not one knob
differs. The rank order is computed **once** over the whole pool and restricted,
which is identical to computing it per subsample: [`rank_key.order_for`] scores
each candidate against a fitted key loaded from disk and never against its
neighbours, so the value a candidate gets does not depend on who else is in the
pool.

A subsample that cannot fill `n` is a **finding**, not an error. That is the curve.

## The output schema — `growth.jsonl`, one row per (rung, seed, n)

The website's `pipeline-growth` figure bakes from this file, so it is the contract
and not an implementation detail. Every field, its unit, and whether it is
approximate:

**Which cell this is** — `schema` (int, [`SCHEMA`]); `stamp` (text, the run folder's
name, on every row of the run); `rung` (text, `1/8`, the fraction spelled);
`fraction` (ratio, the same number); `seed` (int, the subsample draw's, and `null`
at the full pool, which is not drawn); `n` (seats asked for).

**The effort label** — `visits` and `visits_available` (counts, drawn and
reachable); `candidates` (count, pool rows the drawn visits carry); `attempts`
(count, **approximate**: ledger rows in the drawn visits, and retention keeps
three rows per `(location, mode)`, so this is a floor on what was attempted);
`mining_seconds` (seconds, **approximate** for the same reason and blind to rows
written before the leg stamped `hunt.seconds`); `mining_seconds_rows` (count, what
the seconds were summed over).

**What the leg had to choose from** — `eligible` (count, candidates clearing their
mode's bar) and `eligible_locations` (count, distinct places among them);
`after_the_preselection` (count, survivors of the neutral pre-selection);
`in_the_view` (count, rows the stratified view offered the seed).

**What it filled** — `filled` (seats) and `fill` (ratio, `filled / n`);
`floors_in_the_roster` (count, modes whose seat floor at this `n` is above zero)
and `floors_met` (count, of those, the ones filled); `modes_represented` and
`modes_in_the_roster` (counts, any seat at all over the accepted roster).

**How good it is** — `seated_rank` and `eligible_rank` (rank value, `min`, `max`
and `p10/25/50/75/90` on the **fitted** rank key); `seated_p_ge4` and
`eligible_p_ge4` (probability, the same percentiles on the judge's raw `P(>=4)`);
`selection_lift` (rank value, `seated_rank.p50 - eligible_rank.p50`).

**How varied it is** — `partitions_seated` (count) and
`largest_partition_share` (ratio, over `filled`); `cells_seated` (count, colour
cells the seated set is dominant in); `cell_spread` (`{top, bottom, ratio}`, seats
in the most- and least-held cell **over the cells the seated set holds** — a cell
with no seat is not in it); `twin_refusals` (count, candidates the diversity rule
refused) and `twin_collapse_share` (ratio, over `after_the_preselection`);
`centered_seats` and `centered_share` (count and ratio, seats at a location a walk
ledger calls `centered`, [`depth.centered_locations`]).

**What it cost** — `solve_seconds` (seconds, the solve's own wall clock).

Percentiles are **nearest-rank**: the value at index `ceil(q/100 * count) - 1` of
the sorted values. No interpolation, so every number printed is a value some
candidate actually holds.

`manifest.json` beside it carries the pool stamp, the ledger row count, the seeds,
the sizes and the commit — everything needed to say whether two runs are
comparable.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import candidate_ledger, solve
from fractal_wallpapers.paths import repo_root, tracked_name, under

#: The schema every row and every manifest this module writes carries.
SCHEMA = 1

#: The subtree a sweep's stamped folders land in.
UNIT = "growth"

#: What a stamped run's two files are called.
ROWS_NAME = "growth.jsonl"
MANIFEST_NAME = "manifest.json"

#: The rungs, as the **denominator** of the fraction of visits drawn. 1 is the
#: whole pool, which is not drawn at all.
DENOMINATORS = (64, 32, 16, 8, 4, 2, 1)

#: The gallery sizes each rung is solved at. A list and not a constant in the
#: caller: 2000 comes back the moment the pool can seat it, and the instrument
#: takes the sizes as an argument so that costs an argument rather than an edit.
SIZES = (50, 100, 200, 400, 700, 1000)

#: The seeds every rung below the full pool is drawn under. Three, so the bands on
#: the plots are a spread rather than a point, and fixed so a re-run of one cell
#: reproduces it exactly.
SEEDS = (11, 22, 33)

#: The leg a row with no `provenance.run` is filed under. Every such row at one
#: location is one pseudo-leg — see the module docstring.
UNKNOWN_LEG = "unknown"

#: The percentiles reported for the seated set and for the eligible pool alike.
QUANTILES = (10, 25, 50, 75, 90)


class GrowthRefused(RuntimeError):
    """The sweep cannot be run, or the run cannot be read back."""


# --------------------------------------------------------------------------- #
# Visits: what a subsample is a subsample OF.
# --------------------------------------------------------------------------- #
def visits(rows) -> tuple[dict, dict]:
    """`({candidate key: its visit}, {visit: what that visit cost})`.

    A visit is `(location, leg)` and the leg is the row's `provenance.run`. Takes
    an iterable so a caller can stream the ledger rather than hold it: the whole
    store is a few hundred megabytes and this needs four fields of each row.

    The cost block is the **effort label** the plots put on their legends, and it
    is approximate in two ways that are recorded rather than smoothed over.
    `rows` counts the ledger rows that survive — retention keeps three per
    `(location, mode)`, so a visit that drew twelve palettes may show three — and
    `seconds` is blind to any row written before the leg stamped `hunt.seconds`,
    which is why `timed` is beside it.
    """
    keyed: dict = {}
    per: dict = {}
    for row in rows:
        place = str((row.get("location") or {}).get("key"))
        named = (row.get("provenance") or {}).get("run")
        leg = UNKNOWN_LEG if named in (None, "") else str(named)
        visit = (place, leg)
        keyed[str(row["key"])] = visit
        held = per.get(visit)
        if held is None:
            held = per[visit] = {"rows": 0, "seconds": 0.0, "timed": 0}
        held["rows"] += 1
        seconds = (row.get("hunt") or {}).get("seconds")
        if seconds is not None:
            held["seconds"] += float(seconds)
            held["timed"] += 1
    return keyed, per


def draw(population, fraction: float, seed: int) -> list:
    """The visits one rung and one seed draws, uniformly at random, sorted.

    A shuffle-and-take rather than `random.sample`, because `sample` picks between
    two algorithms on the ratio of the draw to the population and a rung that
    crossed that boundary between two CPython releases would change what it drew
    while claiming the same seed. `Random.shuffle` is a plain Fisher-Yates over
    `_randbelow` and does not move.

    The count is `round(len * fraction)` and never less than one: a rung so small
    it draws nothing would report an empty pool as a finding about mining.
    """
    ordered = sorted(population)
    if float(fraction) >= 1.0:
        return ordered
    count = max(1, round(len(ordered) * float(fraction)))
    shuffled = list(ordered)
    random.Random(int(seed)).shuffle(shuffled)
    return sorted(shuffled[:count])


def restrict(candidates, visit_of: dict, drawn) -> list:
    """`candidates` cut to the drawn visits, order preserved. **Read-only.**

    The whole restriction, and it is in memory: nothing here writes to the ledger,
    and the list this returns is a new list over the same frozen
    [`solve.Candidate`] objects.
    """
    keep = set(drawn)
    return [held for held in candidates if visit_of.get(held.key) in keep]


def effort(per_visit: dict, drawn) -> dict:
    """What the drawn visits cost, summed over the visits actually drawn.

    Not the whole ledger's total scaled by the nominal fraction: the draw is
    random, so a rung's realized effort is not its expected effort, and summing
    the visits in hand is the same estimator without that noise in it. Both
    numbers stay approximate for [`visits`]'s two reasons.
    """
    attempts = 0
    seconds = 0.0
    timed = 0
    for visit in drawn:
        held = per_visit.get(visit)
        if held is None:
            continue
        attempts += held["rows"]
        seconds += held["seconds"]
        timed += held["timed"]
    return {
        "attempts": attempts,
        "mining_seconds": round(seconds, 1),
        "mining_seconds_rows": timed,
    }


# --------------------------------------------------------------------------- #
# Reading a spread.
# --------------------------------------------------------------------------- #
def quantiles(values) -> dict | None:
    """`{count, min, max, p10, p25, p50, p75, p90}`, nearest-rank. `None` when empty.

    Nearest-rank and not interpolated, so every number on the record is a value
    some candidate actually holds. `None` rather than zeros for an empty set: a
    rung that seated nothing has no quality, and a row of zeros would plot as a
    terrible gallery instead of as no gallery.
    """
    held = sorted(float(value) for value in values)
    if not held:
        return None
    out = {"count": len(held), "min": round(held[0], 6), "max": round(held[-1], 6)}
    for percent in QUANTILES:
        index = min(len(held) - 1, max(0, math.ceil(percent / 100 * len(held)) - 1))
        out[f"p{percent}"] = round(held[index], 6)
    return out


def _share(part: int, whole: int) -> float | None:
    return None if not whole else round(part / whole, 4)


# --------------------------------------------------------------------------- #
# One cell of the sweep.
# --------------------------------------------------------------------------- #
def row_of(
    record: dict,
    *,
    stamp: str,
    denominator: int,
    seed: int | None,
    drawn: int,
    available: int,
    spent: dict,
    eligible: dict,
    centered: frozenset,
) -> dict:
    """One `growth.jsonl` row, read off one finished solve record.

    Everything here is a projection of the record [`solve.solve`] returned —
    nothing is re-derived from the pool, so a number on this row and the same
    number on the pass record cannot drift apart.
    """
    seated = record["seated"]
    filled = int(record["filled"])
    asked = int(record["config"]["n"])
    modes = record["shortfalls"]["modes"]
    floors = {name: int(value) for name, value in modes["floors"].items()}
    wanted = [name for name, value in floors.items() if value > 0]
    short = set(modes["starved"])
    partitions: dict = {}
    for held in seated:
        name = str(held["partition"])
        partitions[name] = partitions.get(name, 0) + 1
    cells = record["shortfalls"]["cells"]["counts"]
    twin = int(record["rejection"]["reasons"].get("twin", 0))
    after = int(record["population"]["after_the_preselection"])
    on_centre = sum(1 for held in seated if str(held["location"]) in centered)
    seated_rank = quantiles(held["rank"] for held in seated if held.get("rank") is not None)
    return {
        "schema": SCHEMA,
        "stamp": str(stamp),
        "rung": f"1/{int(denominator)}",
        "fraction": round(1.0 / int(denominator), 8),
        "seed": None if seed is None else int(seed),
        "n": asked,
        # The spiral share cap this rung solved under, `None` for no cap. A growth
        # curve is a series and this leg takes `solve.solve`'s default, which
        # became a cap on 2026-09-04 — so a row taken after that date is not
        # comparable with one taken before it, and every row now says which it is
        # rather than leaving a reader to date it.
        "spiral_cap": record["config"]["spiral_cap"],
        # The per-mode ceilings the rung solved under, `{}` for none. On the row
        # for the spiral cap's reason one line up: a ladder is a series taken over
        # weeks and this rule arrived on 2026-09-05, so a rung says which side of
        # it was drawn on rather than leaving a reader to date it. Absent on a row
        # written before the field existed, which is a rung with no ceiling.
        "mode_ceilings": dict(record["config"].get("mode_ceilings") or {}),
        "visits": int(drawn),
        "visits_available": int(available),
        "candidates": int(record["population"]["candidates"]),
        "attempts": int(spent["attempts"]),
        "attempts_are": "surviving ledger rows in the drawn visits. Retention keeps three "
        "rows per (location, mode), so this is a FLOOR on what was attempted",
        "mining_seconds": spent["mining_seconds"],
        "mining_seconds_rows": int(spent["mining_seconds_rows"]),
        "eligible": int(record["population"]["clearing"]),
        "eligible_locations": int(record["population"]["clearing_locations"]),
        "after_the_preselection": after,
        "in_the_view": int(record["population"]["in_the_view"]),
        "filled": filled,
        "fill": _share(filled, asked),
        "floors_in_the_roster": len(wanted),
        "floors_met": sum(1 for name in wanted if name not in short),
        "modes_represented": int(modes["represented"]),
        "modes_in_the_roster": int(modes["of"]),
        "seated_rank": seated_rank,
        "seated_p_ge4": quantiles(held["p_ge4"] for held in seated),
        "eligible_rank": eligible["rank"],
        "eligible_p_ge4": eligible["p_ge4"],
        "selection_lift": None
        if seated_rank is None or eligible["rank"] is None
        else round(seated_rank["p50"] - eligible["rank"]["p50"], 6),
        "partitions_seated": len(partitions),
        "largest_partition_share": _share(max(partitions.values(), default=0), filled),
        "cells_seated": len(cells),
        "cell_spread": {
            "top": max(cells.values(), default=0),
            "bottom": min(cells.values(), default=0),
            "ratio": None
            if not cells or min(cells.values()) == 0
            else round(max(cells.values()) / min(cells.values()), 3),
        },
        "twin_refusals": twin,
        "twin_collapse_share": _share(twin, after),
        "centered_seats": on_centre,
        "centered_share": _share(on_centre, filled),
        "solve_seconds": float(record["seconds"]),
    }


def cell(
    candidates,
    *,
    stamp: str,
    denominator: int,
    seed: int | None,
    drawn: int,
    available: int,
    spent: dict,
    centered: frozenset,
    sizes=SIZES,
    order: dict | None = None,
    coverage: dict | None = None,
    swap_seconds: float | None = None,
    log=print,
) -> list[dict]:
    """Every size, solved over one subsample. One row per size.

    The eligible pool is derived **once** here rather than per size, because the
    bars and the clearing rule do not read `n` — and the derivation is checked
    against the count [`solve.solve`] puts on its own record, so the two readings
    of "what cleared" cannot silently part company.

    The **neutral pre-selection** is derived once here for the same reason and on
    the same terms. It does not read `n` either, and it is the more expensive of
    the two by a long way: 13.7 s over 5,818 places against 0.33 s for the bars,
    so a cell walking six sizes was spending over a minute recomputing one answer.
    [`solve.solve`] checks it against the pool it is handed before using it.
    """
    from fractal_wallpapers.curation import headroom

    table = headroom.bars(candidates)
    cleared = headroom.clearing(candidates, table)
    preselected = solve.preselection_for(cleared, log=log)
    eligible = {
        "rank": quantiles(solve.value_of(held, order) for held in cleared),
        "p_ge4": quantiles(held.score for held in cleared),
    }
    out = []
    for size in sizes:
        started = time.monotonic()
        record = solve.solve(
            candidates,
            n=int(size),
            order=order,
            coverage=coverage,
            seconds=swap_seconds,
            preselected=preselected,
            log=log,
        )
        if record["population"]["clearing"] != len(cleared):
            raise GrowthRefused(
                f"the eligible pool read here holds {len(cleared):,} candidate(s) and the "
                f"solve's own record says {record['population']['clearing']:,}. Two readings "
                "of the same rule have parted company, and the selection lift on this row "
                "would be taken against a pool the solve did not choose from"
            )
        held = row_of(
            record,
            stamp=stamp,
            denominator=denominator,
            seed=seed,
            drawn=drawn,
            available=available,
            spent=spent,
            eligible=eligible,
            centered=centered,
        )
        out.append(held)
        log(
            f"[growth] 1/{denominator} seed={seed} n={size}: {held['filled']} seat(s) "
            f"({'-' if held['fill'] is None else format(held['fill'], '.1%')}), "
            f"{held['floors_met']}/{held['floors_in_the_roster']} floor(s), "
            f"{record['seconds']}s solve, {round(time.monotonic() - started, 1)}s the cell"
        )
    return out


# --------------------------------------------------------------------------- #
# The sweep.
# --------------------------------------------------------------------------- #
def pool_stamp(candidates) -> str:
    """A digest of exactly which candidates the sweep could reach.

    What "the same pool" means, and what makes two runs of this instrument
    comparable. Over the keys alone and in sorted order, so it does not move with
    the order [`solve.pool`] happened to hand them back in.
    """
    digest = hashlib.sha256()
    for key in sorted(str(held.key) for held in candidates):
        digest.update(key.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def source_commit() -> str | None:
    """The commit this checkout is on, or `None` where git could not say.

    Soft, unlike [`models.ship.source_commit`]. That one stages an artifact other
    machines fetch and must refuse to describe a state it cannot name; this is an
    instrument reading a live store, and a sweep of hours should not fail to start
    because git is not on the path.
    """
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    held = done.stdout.strip()
    return held if len(held) == 40 else None


def stamp_now() -> str:
    """The name a run's folder takes: UTC, to the second, sortable."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def plan_of(denominators, seeds) -> list:
    """`[(denominator, seed)]` — every cell the sweep will solve, in order.

    The full pool carries seed `None` because it is not drawn: three seeds over a
    fraction of 1 would be three identical solves, and a record claiming a spread
    it did not measure is worse than one point.
    """
    out = []
    for denominator in denominators:
        held = int(denominator)
        for seed in (None,) if held == 1 else seeds:
            out.append((held, None if seed is None else int(seed)))
    return out


def sweep(
    *,
    stamp: str | None = None,
    denominators=DENOMINATORS,
    sizes=SIZES,
    seeds=SEEDS,
    swap_seconds: float | None = None,
    sink=None,
    rows=None,
    candidates=None,
    order: dict | None = None,
    coverage: dict | None = None,
    centered: frozenset | None = None,
    log=print,
) -> tuple[list[dict], dict]:
    """`(the rows, the manifest)`. Reads the live stores and writes nothing.

    Everything the sweep needs is read **once**: the ledger rows for the visit
    map, the pool and its scores, the fitted rank order, and the `centered` join.
    The rungs then differ only in which visits they hold.

    `sink` is handed each cell's rows the moment that cell finishes, and it is how
    a sweep that dies at cell fifteen keeps the fourteen it measured. It was added
    because one did: a 114-cell run sharing this machine with two other
    pool-holding processes hit a numpy `MemoryError` inside the twin rule and
    threw away everything, because the rows were written only at the end. A leg of
    hours that writes once is a leg whose whole cost is staked on its last minute.

    Every argument from `rows` down is an injection point for the suite — a
    fixture pool with no store behind it — and `None` on each of them means read
    the live one.
    """
    from fractal_wallpapers.curation import depth, headroom

    stamp = stamp_now() if stamp is None else str(stamp)
    started = time.monotonic()
    visit_of, per_visit = visits(candidate_ledger.stream() if rows is None else rows)
    refused: dict = {}
    if candidates is None:
        candidates, _costs, refused = headroom.population(log=log)
    if order is None:
        order, coverage = solve.ranking_for(candidates, solve.DEFAULT_KEY, log=log)
    if centered is None:
        centered = depth.centered_locations()
    reachable = sorted({visit_of[held.key] for held in candidates if held.key in visit_of})
    log(
        f"[growth] {len(candidates):,} candidate(s) over {len(reachable):,} visit(s) "
        f"of the {len(per_visit):,} in the ledger; {len(centered):,} centered location(s)"
    )
    if not reachable:
        raise GrowthRefused(
            "no candidate in the pool joins to a ledger row, so there are no visits to "
            "subsample. The visit map is built off the candidate ledger's own rows"
        )
    plan = plan_of(denominators, seeds)
    out: list[dict] = []
    for denominator, seed in plan:
        drawn = draw(reachable, 1.0 / denominator, 0 if seed is None else seed)
        held = restrict(candidates, visit_of, drawn)
        spent = effort(per_visit, drawn)
        log(
            f"[growth] 1/{denominator} seed={seed}: {len(drawn):,} visit(s), "
            f"{len(held):,} candidate(s), {spent['attempts']:,} attempt(s), "
            f"{spent['mining_seconds']:,.0f} mining second(s)"
        )
        measured = cell(
            held,
            stamp=stamp,
            denominator=denominator,
            seed=seed,
            drawn=len(drawn),
            available=len(reachable),
            spent=spent,
            centered=centered,
            sizes=sizes,
            order=order,
            coverage=coverage,
            swap_seconds=swap_seconds,
            log=log,
        )
        out.extend(measured)
        if sink is not None:
            sink(measured)
    manifest = {
        "schema": SCHEMA,
        "stamp": stamp,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": source_commit(),
        "of": "what N candidates' worth of mining buys, at gallery size n, by drawing a "
        "fraction of the VISITS that made this pool and solving over what they produced",
        "pool": {
            "stamp": pool_stamp(candidates),
            "stamp_is": "sha256 over the sorted candidate keys. Two runs carrying the same "
            "stamp were taken over the same pool and their rows compare directly",
            "candidates": len(candidates),
            "locations": len({held.location for held in candidates}),
            "refused": refused,
            "ledger_rows": len(visit_of),
            "visits_in_the_ledger": len(per_visit),
            "visits_reachable": len(reachable),
            "legs": len({leg for _place, leg in per_visit}),
            "rows_with_no_leg": sum(
                held["rows"] for visit, held in per_visit.items() if visit[1] == UNKNOWN_LEG
            ),
        },
        "plan": {
            "denominators": [int(each) for each in denominators],
            "sizes": [int(each) for each in sizes],
            "seeds": [int(each) for each in seeds],
            "seeds_are": "one draw seed per rung below the full pool. The full pool is not "
            "drawn and carries seed null",
            "cells": len(plan),
            "rows": len(out),
        },
        "solve": {
            "of": "production, unchanged. Restricting the pool is the only difference",
            "key": solve.DEFAULT_KEY,
            "group_cap": solve.DEFAULT_GROUP_CAP,
            "swap_seconds": swap_seconds,
            "floors": "the per-mode rule, mode_policy.seat_floors",
        },
        "seconds": round(time.monotonic() - started, 1),
    }
    return out, manifest


# --------------------------------------------------------------------------- #
# Where a run lands.
# --------------------------------------------------------------------------- #
def growth_dir(stamp: str) -> Path:
    """The stamped folder one run owns. Never shared with another run."""
    return under("curation", UNIT, str(stamp))


def start_run(stamp: str) -> Path:
    """Claim a **new** stamped folder and hand it back, empty.

    Refuses an existing one. A run that overwrote its predecessor would break the
    one property the whole arrangement is for — that the series accumulates — and
    the fix for a collision is a second of the clock, not a flag.
    """
    directory = growth_dir(stamp)
    if (directory / ROWS_NAME).exists():
        raise GrowthRefused(
            f"{tracked_name(directory / ROWS_NAME)} already exists. Each run is a new "
            "stamped folder and nothing here overwrites one: the series is the product"
        )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def append_rows(directory: Path, rows) -> None:
    """Append finished rows to `growth.jsonl`. **The crash-safe half.**

    Opened `newline="\\n"` like everything else here that writes a record a
    machine other than this one reads back.
    """
    where = Path(directory) / ROWS_NAME
    with where.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_manifest(directory: Path, manifest: dict) -> Path:
    """Write `manifest.json` — which is what makes a run **complete**.

    A folder holding rows and no manifest is a run that died partway. The rows it
    did measure are good and the plan it claimed was not finished, and a reader
    has to be able to tell those two apart.
    """
    where = Path(directory) / MANIFEST_NAME
    where.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return Path(directory)


def write_run(stamp: str, rows, manifest: dict) -> Path:
    """One finished sweep, written whole: [`start_run`] and the two writers."""
    directory = start_run(stamp)
    append_rows(directory, rows)
    return write_manifest(directory, manifest)


def read_run(stamp: str) -> tuple[list[dict], dict]:
    """`(rows, manifest)` for one stamped run."""
    directory = growth_dir(stamp)
    where = directory / ROWS_NAME
    if not where.is_file():
        raise GrowthRefused(f"{tracked_name(where)} does not exist")
    rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines() if line]
    for number, row in enumerate(rows, start=1):
        if row.get("schema") != SCHEMA:
            raise GrowthRefused(f"{tracked_name(where)}:{number}: schema {row.get('schema')!r}")
    beside = directory / MANIFEST_NAME
    manifest = json.loads(beside.read_text(encoding="utf-8")) if beside.is_file() else {}
    return rows, manifest


def stamps() -> list[str]:
    """Every stamped run on this machine, oldest first."""
    root = under("curation", UNIT)
    if not root.is_dir():
        return []
    return sorted(held.name for held in root.iterdir() if (held / ROWS_NAME).is_file())


__all__ = [
    "DENOMINATORS",
    "MANIFEST_NAME",
    "QUANTILES",
    "ROWS_NAME",
    "SCHEMA",
    "SEEDS",
    "SIZES",
    "UNIT",
    "UNKNOWN_LEG",
    "GrowthRefused",
    "cell",
    "draw",
    "effort",
    "growth_dir",
    "plan_of",
    "pool_stamp",
    "quantiles",
    "append_rows",
    "read_run",
    "restrict",
    "row_of",
    "source_commit",
    "stamp_now",
    "stamps",
    "start_run",
    "sweep",
    "visits",
    "write_manifest",
    "write_run",
]
