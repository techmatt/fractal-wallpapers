"""Where a deep run stands: the two channels a seat can come from.

A **seat** is one nucleus the run will spend a share of its budget on. Seats are
the deep mode's budget lever — a leg is priced in seats, not in batches — and
this module is the only thing that produces one.

```text
newton         an anchor atom, then ∂M tracked down the ladder to a deep one
continuation   a place an earlier ledger already admitted below the shallow floor
```

## The Newton channel tracks ∂M; it does not lift a floor

The maker's deep spec settled this and the measurement behind it is in
`audit_deep_descent`: deep beauty is *depth-band-local*. An atom is worth seeing
over a band around its own size and is black below it, so a search that reaches
depth by lowering a walk's floor spends its whole budget descending through the
space between atoms. What works is to move *along* ∂M — from an atom to a
smaller atom near it — and frame each one in its own band.

So the channel is a ladder. It starts at a tracked plane-seed atom, which is a
real atom at a real place that somebody's grid already solved for, and steps to
the smallest nucleus it can find in a disc a few atom-widths across. Each step
is a Newton solve in arbitrary precision at the precision the atom asks for, and
each step multiplies the period rather than adding to it — which is why three or
four steps cross the eight decades between a plane seed and this mode's floor.

The ladder stops when an atom's band lands in the window
[`fractal_wallpapers.deep.depth.SEAT_SIZES`] — money shot below the shallow
floor, band floor above this mode's own. Overshooting is a miss and is recorded
as one: an atom below the window is real and this mode cannot frame it.

**The channel is parameter-plane only, structurally.** A Julia viewport is a
point of the *z*-plane and has no nucleus in the parameter-plane sense at all,
so there is nothing here for Newton to solve. That is the same rule
[`fractal_wallpapers.discovery.operators.degree_of`] states for the reframing
probe, read from there rather than restated.

## The continuation channel spends what is already known

Every ledger this project has written is full of places, and a few hundred of
them sit at the shallow floor with a good score against them — the walk stopped
because its floor said to, not because the material ran out. Those are roots
with provenance: a head has already looked at them, and the deep floor is two
decades of room the same lineage never got to use.

They are taken at their own recorded frame and deduplicated by
[`fractal_wallpapers.discovery.nucleus.key_from_strings`] where the family has a
nucleus at all, so a place four walks found is one seat.

## Sourcing happens more than once, so what a round took has to outlive it

A budgeted run seats to a projection and seats **again** when its frontier
empties with budget left ([`fractal_wallpapers.deep.run`]). Both channels
deduplicate, and both used to do it in sets that lived for one call — so a
second round would descend from anchors the first had spent, arrive back at
nuclei the run is already standing on, and offer the ledger rows it already
took. [`Standing`] is that memory, carried by the run and handed to every round:
the anchor queues, the two channels' seen-sets, and the family x band cells the
Newton channel is filling. A caller with one round to run passes nothing and
gets the one-shot behaviour exactly.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import mpmath as mp

from fractal_wallpapers.deep import centers, depth
from fractal_wallpapers.discovery import ledger as ledger_rows
from fractal_wallpapers.discovery import operators, plane_seeds
from fractal_wallpapers.paths import tracked_name
from fractal_wallpapers.supply import ledgers as ledger_module

#: The two channels a seat can arrive through.
NEWTON = "newton"
CONTINUATION = "continuation"

#: Probe radii for one ladder step, in units of the parent atom's own size.
#:
#: The same three [`fractal_wallpapers.discovery.operators.PROBE_RADII`] uses,
#: and for the same reason: measured in the parent's scale, "nearby" means the
#: same thing around a shallow atom and a deep one, and a flat radius finds
#: nothing at all around a deep parent.
PROBE_RADII = operators.PROBE_RADII

#: Probe seeds one ladder step may draw before it gives up.
#:
#: The bound that actually binds. Most probes land back inside the parent's own
#: atom domain and hand the parent back, so a budget phrased as "find one" is an
#: unbounded budget.
STEP_PROBES = 32

#: The period ceiling one step above the parent's, as a multiple of it.
#:
#: A child atom's period is a multiple of its parent's, and the multiple is
#: small — a decade of size is roughly a fifth again of period. Three is room
#: for a long step; it is not a search over periods.
PERIOD_HEADROOM = 3.0

#: The highest period a ladder step will solve at.
#:
#: Above [`fractal_wallpapers.discovery.operators.PERIOD_CAP`], because that one
#: bounds a *shallow* probe and this mode's whole subject is the atoms below it.
#: A period-400 solve is a 400-step orbit per Newton iteration in arbitrary
#: precision, which is the real price of the ceiling.
PERIOD_CAP = 400

#: Ladder steps one anchor may take before the descent is abandoned.
MAX_STEPS = 6

#: Seats one anchor may contribute. One: an anchor that produced a seat has had
#: its neighbourhood read, and a second seat off the same lineage is the same
#: place at a different period.
SEATS_PER_ANCHOR = 1


@dataclass
class Seat:
    """One nucleus a deep run will stand on, and how it came to be one."""

    channel: str
    family: dict
    #: The deep center, for a Newton seat. `None` on a continuation seat, whose
    #: place was found by a walk rather than produced by a solve.
    center: centers.DeepCenter | None
    #: The frames this seat contributes as roots, widest first.
    framings: list[dict]
    provenance: dict

    @property
    def band(self) -> str | None:
        """The depth band this seat's own deepest framing lands in.

        The framings are widest first, so this is the money shot on a Newton
        seat and the admitted frame itself on a continuation one — the frame the
        seat is *for*, rather than the neighbourhood view above it.
        """
        return depth.band_of(float(self.framings[-1]["width"]))

    def record(self) -> dict:
        return {
            "channel": self.channel,
            "band": self.band,
            "family": self.family,
            "center": None if self.center is None else self.center.record(),
            "framings": self.framings,
            "provenance": self.provenance,
        }


@dataclass
class Sourcing:
    """What one call to a channel did, whether or not it produced seats."""

    seats: list[Seat] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    ladders: list[dict] = field(default_factory=list)
    #: How a channel that spreads itself divided the seats, in its own cells:
    #: `"family|band"` for the Newton channel, which aims at a band, and
    #: `"family|offered"` / `"family|seated"` for the continuation channel, which
    #: spreads over the planes and takes whatever band a ledger row already sits
    #: in. One field rather than two because the question a reader asks of both
    #: is the same one — did this channel cover the planes, or fill from one.
    cells: dict[str, int] = field(default_factory=dict)

    def count(self, name: str, amount: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + amount

    def absorb(self, other: Sourcing) -> Sourcing:
        """Fold a second call to the same channel into this record.

        [`sourced`] asks the Newton channel twice when the continuation channel
        runs out of ledger to spend — its supply is finite in a way the other's
        is not — and two records of one channel in one round is two answers to
        what that channel did.
        """
        self.seats.extend(other.seats)
        self.ladders.extend(other.ladders)
        for name, amount in other.counts.items():
            self.count(name, amount)
        for name, amount in other.cells.items():
            self.cells[name] = self.cells.get(name, 0) + amount
        return self

    def record(self) -> dict:
        return {
            "seats": len(self.seats),
            "counts": dict(sorted(self.counts.items())),
            "cells": dict(sorted(self.cells.items())),
            "ladders": self.ladders,
        }


@dataclass
class Standing:
    """What a run has already seated, carried between its sourcing rounds.

    One object rather than five arguments, because the five are one fact: they
    are only ever read and written together, and a round handed four of them is
    a round that quietly re-seats along whichever axis was left out.

    A run that sources once may ignore this entirely — every entry point builds
    an empty one when it is not given one, and an empty one reproduces the
    single-round behaviour exactly.
    """

    #: Anchors not yet spent, per family, deepest first. Built on first use so
    #: the plane-seed file is read once a run rather than once a round, and
    #: **consumed**: an anchor a stalled ladder spent is gone, which is what
    #: stops a second round paying to prove the same descent does not arrive.
    anchor_queues: dict[str, list[dict]] | None = None
    #: Reflection keys of the nuclei the Newton channel is already standing on.
    seated: set[str] = field(default_factory=set)
    #: Place keys the continuation channel has already taken.
    places: set[str] = field(default_factory=set)
    #: `ledger|root_id` lineages the continuation channel has already taken.
    lineages: set[str] = field(default_factory=set)
    #: `family|band` cells and how many seats each holds, across every round —
    #: so a second round fills the cells the first one *left* least full rather
    #: than starting its own round-robin from zero.
    filled: dict[str, int] = field(default_factory=dict)
    #: Sourcing rounds this run has run.
    rounds: int = 0

    def anchors(self, limit_per_family: int) -> dict[str, list[dict]]:
        """The per-family anchor queues, read once and consumed thereafter."""
        if self.anchor_queues is None:
            queues: dict[str, list[dict]] = {}
            for anchor in anchors(limit_per_family):
                queues.setdefault(json.dumps(anchor["family"], sort_keys=True), []).append(anchor)
            self.anchor_queues = queues
        return self.anchor_queues

    def anchors_left(self) -> int:
        """Anchors no ladder has spent yet — the Newton channel's own supply."""
        return sum(len(queue) for queue in (self.anchor_queues or {}).values())

    def record(self) -> dict:
        return {
            "rounds": self.rounds,
            "anchors_left": self.anchors_left(),
            "newton_seated": len(self.seated),
            "continuation_places": len(self.places),
            "continuation_lineages": len(self.lineages),
            "cells": dict(sorted(self.filled.items())),
        }


# --------------------------------------------------------------------------- #
# The Newton channel.
# --------------------------------------------------------------------------- #
def anchors(limit_per_family: int = 8, path: Path | None = None) -> list[dict]:
    """The tracked plane-seed atoms a ladder may start from, deepest first.

    Deepest first because the ladder's cost is its length: an anchor whose atom
    is already a decade above the seat window is one step from a seat, and one
    at the home view is six that will probably not finish. Only the rows the
    grid *solved* are anchors — a home view and a hand-picked frame are places,
    not atoms, and the ladder needs a size to probe in units of.
    """
    rows = [
        row
        for row in plane_seeds.read(path)
        if row["provenance"].get("channel") == plane_seeds.SOLVED and row.get("viewport")
    ]
    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(json.dumps(row["family"], sort_keys=True), []).append(row)
    out: list[dict] = []
    for group in by_family.values():
        group.sort(key=lambda row: float(row["viewport"]["width"]))
        out.extend(group[: int(limit_per_family)])
    return out


def _degree_of_key(family_key: str) -> int | None:
    """The multibrot degree of a family written as its own JSON key."""
    family = json.loads(family_key)
    return operators.degree_of(family.get("kind"), int(family.get("degree", 2)))


def _child_periods(parent_period: int) -> int:
    """The period ceiling one ladder step above a parent of this period."""
    return min(PERIOD_CAP, max(24, int(math.ceil(PERIOD_HEADROOM * int(parent_period)))))


def _probe_seed(rng: random.Random, parent: centers.DeepCenter):
    """One probe seed around a parent atom, and the radius it was drawn at."""
    radius = PROBE_RADII[rng.randrange(len(PROBE_RADII))] * parent.size
    angle = rng.random() * 2.0 * math.pi
    seed = mp.mpc(
        mp.mpf(parent.center_re) + mp.mpf(radius * math.cos(angle)),
        mp.mpf(parent.center_im) + mp.mpf(radius * math.sin(angle)),
    )
    return seed, radius


def step(
    parent: centers.DeepCenter,
    rng: random.Random,
    *,
    probes: int = STEP_PROBES,
    width: float = depth.MIN_WIDTH,
    size_ceiling: float | None = None,
) -> tuple[centers.DeepCenter | None, str, dict]:
    """One rung down the atom ladder: `(child, why-not, tally)`.

    Probes a disc a few parent-sizes across, solves each seed for the atom it
    sits on, and keeps the best of what it found. **Best is not smallest.** An
    atom inside the seat window is the answer and the deepest one there is
    preferred; failing that, the smallest atom still *above* the window is the
    next rung, because a step past the window cannot be walked back — the atom
    below it is real and this mode has no frame for it.

    `size_ceiling` is what the ladder is *aiming* at — the top of one depth band
    rather than the top of the whole window — and it moves only the line between
    "arrived" and "one more rung". The floor stays [`depth.seat_sizes`]'s own,
    at the parent's own degree: an atom below the band being aimed at is a seat
    in a deeper one, and throwing it away would spend a descent to arrive at
    nothing.
    """
    low, window_top = depth.seat_sizes(parent.degree)
    high = window_top if size_ceiling is None else min(float(size_ceiling), window_top)
    ceiling = _child_periods(parent.period)
    found: dict[str, centers.DeepCenter] = {}
    tally: dict[str, int] = {}

    def note(reason: str) -> None:
        tally[reason] = tally.get(reason, 0) + 1

    with mp.workdps(centers.working_dps(width)):
        for _ in range(max(1, int(probes))):
            seed, radius = _probe_seed(rng, parent)
            child, why, _solves = centers.nearest(
                seed,
                degree=parent.degree,
                period_max=ceiling,
                # A child's period is strictly above its parent's, and asking
                # for that is what stops every probe handing the parent back.
                period_min=parent.period + 1,
                # Four probe radii: wide enough that a seed just outside an
                # atom still lands on it, tight enough that no ancestor can.
                near=radius * 4.0,
                width=width,
            )
            if child is None:
                note(why)
                continue
            if child.key == parent.key:
                note("hit_parent")
                continue
            if child.size >= parent.size:
                note("not_smaller")
                continue
            if child.size < low:
                note("below_the_window")
                continue
            found[child.key] = child

    tally["found"] = len(found)
    if not found:
        return None, max(tally, key=tally.get) if tally else "no_probe_landed", tally
    inside = [row for row in found.values() if row.size <= high]
    if inside:
        return min(inside, key=lambda row: row.size), "", tally
    return min(found.values(), key=lambda row: row.size), "", tally


def descend(
    anchor: dict,
    rng: random.Random,
    *,
    max_steps: int = MAX_STEPS,
    probes: int = STEP_PROBES,
    width: float = depth.MIN_WIDTH,
    size_ceiling: float | None = None,
) -> tuple[centers.DeepCenter | None, str, list[dict]]:
    """Track ∂M from a plane-seed atom to one this mode can frame.

    Returns `(center, why-not, ladder)` — and the ladder is returned whether or
    not the descent arrived, because "it stopped at period 214 with nothing
    smaller in the disc" and "the anchor never solved at all" are different
    facts about this channel and only one of them is a reason to stop using it.

    `size_ceiling` aims the descent at one depth band: the ladder takes another
    rung while the atom it is standing on is *above* it. It is a ceiling and not
    a window, so a rung that lands below the band aimed at still arrives — that
    is a seat in a deeper band, which is a seat.
    """
    degree = operators.degree_of(anchor["family"]["kind"], int(anchor["family"].get("degree", 2)))
    if degree is None:
        return None, "no_nucleus_on_this_plane", []
    ceiling = depth.seat_sizes(degree)[1] if size_ceiling is None else float(size_ceiling)
    view = anchor["viewport"]
    seed = mp.mpc(mp.mpf(view["center_re"]), mp.mpf(view["center_im"]))
    period = anchor["provenance"].get("period")
    ladder: list[dict] = []

    try:
        current = centers.solve(seed, int(period), degree=degree, width=width)
    except (centers.NotANucleus, TypeError, ValueError) as why:
        return None, f"anchor_unsolved:{centers.refusal_of(str(why))}", ladder
    ladder.append({"step": 0, "period": current.period, "size": current.size})

    for index in range(1, int(max_steps) + 1):
        if depth.seats_this_size(current.size, degree) and current.size <= ceiling:
            return current, "", ladder
        child, why, tally = step(current, rng, probes=probes, width=width, size_ceiling=ceiling)
        if child is None:
            return None, f"ladder_stalled:{why}", ladder
        ladder.append(
            {
                "step": index,
                "period": child.period,
                "size": child.size,
                "probes": tally,
            }
        )
        current = child
    if depth.seats_this_size(current.size, degree) and current.size <= ceiling:
        return current, "", ladder
    return None, "ladder_did_not_reach_the_window", ladder


#: Descents one seat may cost before the cell aiming them is closed.
#:
#: A ladder is the expensive half of sourcing and most anchors do not arrive, so
#: a cell nothing can fill — a family with no atom of that size within reach of
#: its anchors — would otherwise spend the whole leg proving it. Four is the
#: shakedown's own yield with room: seven of twelve mandelbrot anchors arrived
#: there, against a floor band nobody had aimed at yet.
DESCENTS_PER_SEAT = 4


def newton_seats(
    seats: int,
    rng: random.Random,
    *,
    anchors_per_family: int = 8,
    max_steps: int = MAX_STEPS,
    probes: int = STEP_PROBES,
    width: float = depth.MIN_WIDTH,
    descents_per_seat: int = DESCENTS_PER_SEAT,
    standing: Standing | None = None,
    clock=None,
    log=print,
) -> Sourcing:
    """Track ∂M down from tracked plane-seed atoms, spread over family × band.

    **Spread, not ranked.** Filling the seats in anchor order fills them off
    whichever family the plane-seed grid solved most of and off whatever band
    the first arriving ladder happened to land in — and the bands are not
    interchangeable: the head's scores rise with width, so a run seated from the
    top of the window reports on material the shallow walk could already reach.
    So the cells of family × [`depth.BAND_NAMES`] are filled round-robin, least
    full first, and each descent is *aimed* at its cell's band by the size
    ceiling it hands the ladder.

    Aim is not arrival. A ceiling only says where the ladder stops taking rungs,
    so a descent aimed at `upper` that lands in `middle` is credited to the cell
    it landed in — the alternative is to throw away a seat for being deeper than
    it was asked to be.

    **A plane gets only the bands its own floor reaches.**
    [`depth.open_bands`] answers that, and today it takes the `floor` band away
    from degree 5 alone. A cell that cannot be filled is not a cell that fills
    slowly: it is [`DESCENTS_PER_SEAT`] real ladders spent proving what the
    floor already said.

    `standing` carries the anchors, the seated nuclei and the cell fills across a
    run's sourcing rounds; `clock` is a wall-clock leg to spend descents against
    — anything with `may_start()` (falsy to go ahead) and `observe(seconds)`,
    which is what [`fractal_wallpapers.curation.pacing.Leg`] is. It **gates and
    measures and does not kill**: a descent is arbitrary-precision arithmetic in
    this process with no subprocess to take down, and [`MAX_STEPS`] and
    [`STEP_PROBES`] are what bound one from the inside.
    """
    out = Sourcing()
    standing = Standing() if standing is None else standing
    queues = standing.anchors(anchors_per_family)

    cells = [
        (family, band) for family in queues for band in depth.open_bands(_degree_of_key(family))
    ]
    order = {cell: index for index, cell in enumerate(cells)}
    spent = {cell: 0 for cell in cells}
    for cell in cells:
        standing.filled.setdefault(f"{cell[0]}|{cell[1]}", 0)
        out.cells[f"{cell[0]}|{cell[1]}"] = 0
    quota = max(1, math.ceil(int(seats) / max(1, len(cells))))
    budget = max(1, int(descents_per_seat) * quota)
    seated = standing.seated

    while len(out.seats) < int(seats):
        open_cells = [cell for cell in cells if queues[cell[0]] and spent[cell] < budget]
        if not open_cells:
            break
        if clock is not None and clock.may_start() is not None:
            out.count("newton:out_of_clock")
            break
        cell = min(
            open_cells, key=lambda cell: (standing.filled[f"{cell[0]}|{cell[1]}"], order[cell])
        )
        family_key, aimed = cell
        anchor = queues[family_key].pop(0)
        spent[cell] += 1
        started = time.monotonic()
        center, why, ladder = descend(
            anchor,
            rng,
            max_steps=max_steps,
            probes=probes,
            width=width,
            size_ceiling=depth.band_ceiling(aimed),
        )
        if clock is not None:
            clock.observe(time.monotonic() - started)
        out.ladders.append(
            {
                "anchor": anchor["id"],
                "family": anchor["family"],
                "aimed": aimed,
                "arrived": center is not None,
                "reason": why,
                "rungs": ladder,
            }
        )
        if center is None:
            out.count(f"newton:{why.split(':')[0]}")
            log(f"[deep] anchor {anchor['id']} aimed {aimed}: {why}")
            continue
        if not depth.releasable(center.center_re, center.center_im, center.money_shot):
            out.count("newton:not_releasable_in_f64")
            log(
                f"[deep] anchor {anchor['id']}: period {center.period} at size "
                f"{center.size:.3e}, but its money shot is "
                f"{center.release_ulps:.2f} units of last place per sample at release "
                f"geometry and the engine refuses below {depth.RESOLUTION_ULPS}"
            )
            continue
        if center.reflection_key in seated:
            # Two anchors a few plane-seed rows apart can be inside one atom
            # domain and walk down to the same nucleus — or to its reflection in
            # the real axis, which is the same atom and a flipped picture. Both
            # are one place, and a second seat on it is one of this run's eight
            # spent on nothing.
            out.count("newton:already_seated")
            continue
        seated.add(center.reflection_key)
        out.count("newton:seated")
        seat = _newton_seat(anchor, center, aimed)
        out.seats.append(seat)
        landed = f"{family_key}|{seat.band if seat.band in depth.BAND_NAMES else aimed}"
        standing.filled[landed] = standing.filled.get(landed, 0) + 1
        out.cells[landed] = out.cells.get(landed, 0) + 1
        out.count(f"newton:landed:{landed.rsplit('|', 1)[1]}")
        log(
            f"[deep] seat {center.key} period {center.period} size {center.size:.3e} "
            f"money shot {center.money_shot:.3e} band {seat.band} (aimed {aimed}, "
            f"{len(ladder) - 1} ladder step(s))"
        )
    return out


def _newton_seat(anchor: dict, center: centers.DeepCenter, aimed: str | None = None) -> Seat:
    return Seat(
        channel=NEWTON,
        family=anchor["family"],
        center=center,
        framings=[center.viewport(framing) for framing in depth.ROOT_FRAMINGS],
        provenance={
            "anchor": anchor["id"],
            "anchor_period": anchor["provenance"].get("period"),
            "nucleus_key": center.key,
            "period": center.period,
            "framings": list(depth.ROOT_FRAMINGS),
            "aimed_band": aimed,
        },
    )


# --------------------------------------------------------------------------- #
# The continuation channel.
# --------------------------------------------------------------------------- #
#: The width at or below which a ledger row is a *deep admission* worth
#: continuing from. The shallow floor itself: a row resting on it is a lineage
#: the floor stopped, not one the material stopped.
CONTINUABLE_WIDTH = depth.SHALLOW_MIN_WIDTH * 1.5


def continuation_seats(
    seats: int,
    *,
    paths=None,
    exclude: Path | None = None,
    width_max: float = CONTINUABLE_WIDTH,
    standing: Standing | None = None,
    log=print,
) -> Sourcing:
    """Seats from places earlier ledgers already admitted at the shallow floor.

    Ranked by depth first and score second: the deepest rows are the ones with
    the least of their own band left to walk, and a row the head liked is a
    lineage worth two more decades of it. A row with no score at all — the null
    scorer's rows, which is most of one early harvest — ranks last rather than
    being dropped, because "nothing looked at this" is not "this is bad".

    **Spread over the planes, ranked inside one.** That rank is a rank over
    *ledgers*, and a ledger is whatever the last run harvested: taken straight it
    seats every deep row of one harvest before it looks at a plane that harvest
    happened not to visit. So the families take turns and each one offers its own
    best remaining row. The Newton channel spreads over family × band because it
    can aim a ladder at a band; this one takes what a walk already admitted, so
    the band it lands in is a fact about the row rather than a choice, and it is
    recorded rather than steered.

    **This channel's supply is finite and small.** Every ledger this project has
    written holds about fifteen hundred rows at or below the shallow floor and
    fifty-odd distinct lineages between them, so a run asking for more seats than
    that gets what there is — and [`sourced`] sends the shortfall back to the
    Newton channel, whose own supply is the plane-seed pool and is two orders of
    magnitude larger.
    """
    out = Sourcing()
    standing = Standing() if standing is None else standing
    rows: list[dict] = []
    available = (
        ledger_module.ledger_paths(exclude=exclude) if paths is None else [Path(p) for p in paths]
    )
    for path in available:
        for row in ledger_module.rows(path, "candidate"):
            if row.get("fate") not in (ledger_rows.SURVIVED, ledger_rows.EXPANDABLE):
                continue
            view = row.get("viewport") or {}
            try:
                width = float(view["width"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (0.0 < width <= float(width_max)):
                continue
            rows.append({**row, "_width": width, "_ledger": path})
    out.count("deep_ledger_rows", len(rows))

    seen = standing.places
    lineages = standing.lineages
    rows.sort(key=lambda row: (row["_width"], -(row.get("score") or -1.0)))
    queues: dict[str, list[dict]] = {}
    for row in rows:
        queues.setdefault(json.dumps(row["family"], sort_keys=True), []).append(row)
    families = sorted(queues)
    for family in families:
        out.cells.setdefault(f"{family}|offered", len(queues[family]))
    turn = 0
    while len(out.seats) < int(seats) and any(queues[family] for family in families):
        family = families[turn % len(families)]
        turn += 1
        if not queues[family]:
            continue
        row = queues[family].pop(0)
        key = _place_key(row)
        lineage = f"{tracked_name(row['_ledger'])}|{row.get('root_id')}"
        if key in seen or lineage in lineages:
            # Two reasons, one refusal. The place key catches the same view
            # written twice; the lineage catches a walk root's whole subtree,
            # whose rows sit a frame apart at one scale and are one place to
            # descend from however many of them a ledger holds.
            out.count(
                "continuation:already_seated"
                if key in seen
                else "continuation:lineage_already_seated"
            )
            continue
        seen.add(key)
        lineages.add(lineage)
        view = row["viewport"]
        floor = depth.min_width(
            operators.degree_of(row["family"].get("kind"), int(row["family"].get("degree", 2)))
        )
        if not depth.releasable(view["center_re"], view["center_im"], floor):
            out.count("continuation:floor_not_releasable_in_f64")
            continue
        out.count("continuation:seated")
        out.cells[f"{json.dumps(row['family'], sort_keys=True)}|seated"] = (
            out.cells.get(f"{json.dumps(row['family'], sort_keys=True)}|seated", 0) + 1
        )
        out.seats.append(
            Seat(
                channel=CONTINUATION,
                family=row["family"],
                center=None,
                framings=[
                    {
                        "center_re": str(view["center_re"]),
                        "center_im": str(view["center_im"]),
                        "width": str(view["width"]),
                    }
                ],
                provenance={
                    "ledger": tracked_name(row["_ledger"]),
                    "fate": row.get("fate"),
                    "score": row.get("score"),
                    "score_great": row.get("score_great"),
                    "admitted_width": row["_width"],
                    "place_key": key,
                },
            )
        )
        log(
            f"[deep] seat {key} from {Path(row['_ledger']).parent.name} at width "
            f"{row['_width']:.4e}, score {row.get('score')}"
        )
    return out


#: How far apart two admitted rows must be to be two places, in frame widths.
#:
#: One. Two centers closer than a frame width at the same scale are the same
#: view of the same thing, and seating both spends two of the run's seats on one
#: place. The shakedown found exactly that: four rows of one lineage sit at width
#: `1.0286e-9` with centers `1.5e-9` apart, and a key built from the coordinates
#: themselves called them four places because they differ in the ninth decimal.
PLACE_WIDTHS = 1.0


def _place_key(row: dict) -> str:
    """One name for a place, so four walks that found it seat it once.

    The family, the plane's own mirror symmetry folded where it has one, and the
    row's center quantized to a cell of its own frame width — the same scale-relative grid
    [`fractal_wallpapers.discovery.operators.ProbeGovernor`] quantizes a probed
    region to, and for the same reason: "nearby" has to mean the same thing at
    `1e-3` and at `1e-11`, which an absolute tolerance cannot.

    The cell has boundaries and two rows either side of one are two seats. That
    is the cheap failure of this shape and it is the right way round: the
    expensive one is calling two different places the same, and a grid cannot do
    that beyond its own cell.
    """
    view = row["viewport"]
    width = float(view["width"])
    side = width * PLACE_WIDTHS
    down = float(view["center_im"])
    if operators.degree_of(row["family"].get("kind"), int(row["family"].get("degree", 2))):
        # A parameter plane's recurrence has real coefficients, so a location and
        # its conjugate are one place seen in a mirror. A *dynamical* plane's
        # symmetry is `z -> -z` and not this one, so the fold is asked for by
        # plane rather than applied to every row.
        down = abs(down)
    return "|".join(
        [
            json.dumps(row["family"], sort_keys=True),
            str(math.floor(float(view["center_re"]) / side)),
            str(math.floor(down / side)),
            f"{math.log10(width):.1f}",
        ]
    )


def sourced(
    seats: int,
    rng: random.Random,
    *,
    newton_share: float = 0.5,
    anchors_per_family: int = 8,
    paths=None,
    exclude: Path | None = None,
    standing: Standing | None = None,
    clock=None,
    log=print,
) -> tuple[list[Seat], dict]:
    """Both channels, to a seat cap. Returns the seats and what each channel did.

    The share is a *target*, not a quota: whatever one channel cannot fill the
    other is allowed to, in the same call, because a seat cap is a budget and an
    unfilled half of it is budget thrown away. Which channel actually filled it
    is on every seat and in the record.

    **The fallback runs both ways, and it did not use to.** Newton was asked
    first and the continuation channel was handed the remainder, so a run whose
    continuation supply ran dry simply came up short — invisible at eight seats,
    and the binding constraint at a hundred and eighty, because that channel's
    supply is fifty-odd lineages of finished ledger and the Newton channel's is
    nineteen hundred tracked anchors. So a shortfall goes back to Newton, in the
    same call, against the same [`Standing`].

    `standing` is the run's memory across sourcing rounds and `clock` a wall-clock
    leg to spend descents against; both default to a fresh, unbudgeted round.
    """
    seats = int(seats)
    standing = Standing() if standing is None else standing
    standing.rounds += 1
    want = max(0, min(seats, int(round(seats * float(newton_share)))))
    newton = newton_seats(
        want,
        rng,
        anchors_per_family=anchors_per_family,
        standing=standing,
        clock=clock,
        log=log,
    )
    carried = continuation_seats(
        seats - len(newton.seats), paths=paths, exclude=exclude, standing=standing, log=log
    )
    short = seats - len(newton.seats) - len(carried.seats)
    if short > 0:
        newton.absorb(
            newton_seats(
                short,
                rng,
                anchors_per_family=anchors_per_family,
                standing=standing,
                clock=clock,
                log=log,
            )
        )
    taken = [*newton.seats, *carried.seats][:seats]
    return taken, {
        NEWTON: newton.record(),
        CONTINUATION: carried.record(),
        "standing": standing.record(),
        "seated": {
            NEWTON: sum(1 for seat in taken if seat.channel == NEWTON),
            CONTINUATION: sum(1 for seat in taken if seat.channel == CONTINUATION),
        },
    }


__all__ = [
    "CONTINUABLE_WIDTH",
    "CONTINUATION",
    "DESCENTS_PER_SEAT",
    "MAX_STEPS",
    "NEWTON",
    "PERIOD_CAP",
    "PERIOD_HEADROOM",
    "STEP_PROBES",
    "Seat",
    "Sourcing",
    "anchors",
    "continuation_seats",
    "descend",
    "newton_seats",
    "sourced",
    "step",
]
