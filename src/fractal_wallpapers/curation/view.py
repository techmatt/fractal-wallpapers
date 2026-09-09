"""What one pass may reach: a stratified, band-blind view over the pool.

The pool is ninety-eight thousand rows and eleven thousand of them clear their
mode's bar. A leg that walks all of them pays a pixel-cloud signature — a tenth
of a second — for every candidate the cheap rules do not refuse, and a 1-swap
loop asks about each of them more than once. So a pass chooses what it may reach
before it starts, writes down what it chose, and never touches the pool again.

**This is a view and never an edit.** Nothing here mutates the list it is handed;
the strata, their sizes and the draw seed all land on the record, so a pass is
reproducible from its own record and two passes over one pool differ in what the
record says they differ in.

## Two layers, and only one of them is ever cut

**One wallpaper per location is hard**, so a place can spend at most one seat and
the view keeps that place's strongest row by the pass's own rank key. **Every one
of them, always, whatever the strata say.** That set is exactly what the
sequential seating this leg replaced walked, so a view holding all of it cannot
choose worse than that walk did — and a view that cuts into it can, which is not a
theory: sizing the first draft's quotas over both layers together left the view
reaching 1,768 of 4,496 places, and the seed came back at a worst seated score of
0.299 where the retired greedy had reached 0.418 on the same pool. The floor under
this leg is the walk it replaced, and this layer is that floor.

One layer is not enough, though: a place's best row overall can be a crowded blue
while its second-best is the only azure that place can field, and the ceiling
refuses the first while the second would have been seated. So the view also keeps
each place's best row **per stratum** — the **alternates** — which is what lets a
stratum that needs candidates find them without letting a place field two seats.
The alternates are what a stratum's quota is spent on and what a slice cuts into.

**The strata are `(kind, mode, cell)`**: what made the picture, how it was
rendered, and what colour it came out. Those are the three axes every counted
rule in [`curation.rules`] acts on and the three a mine can be aimed down, so a
shortfall against a stratum is an instruction rather than an observation.

## A slice is band-blind, and that is the whole point

A stratum's **alternates**, small enough, are taken whole. A larger set is
**sampled across its own rank order at a seeded stride**, so the slice holds rows
from the top, the middle and the bottom of that stratum in the proportions the
stratum has them. A place's own best row is never in the draw — it is already in.

It is emphatically not a top-by-score cut, and the reason is the objective rather
than fairness. The worst seated score is the second thing the leg maximizes, and
the floors are the third: a leg that can only reach a stratum's strongest rows
cannot trade a crowded seat for a weaker one that covers a starved mode, and
cannot find the row that lifts the worst seat because the row that lifts the
worst seat is by construction not near the top of anything. Cutting at the top
would leave the swap loop with a neighbourhood that agrees with the seed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: A stratum this small is taken whole rather than sliced. Below it a stride is
#: meaningless — a stratum of six sampled at stride two is a top-by-score cut
#: with extra arithmetic — and the rows are cheap enough that keeping them all
#: costs nothing a pass notices.
SMALL_STRATUM = 8

#: How many **alternates** a stratum keeps for each seat it could contribute.
#: **Two.**
#:
#: One would be a view with no slack in it: a stratum that could field seven seats
#: and holds exactly seven rows has no second option anywhere, so every rule that
#: refuses one of them costs a seat outright.
#:
#: It sizes the alternates alone. Every place's strongest row is in the view
#: whatever this is set to, so lowering it cannot take the view below the walk
#: this leg replaced — it only takes away the second and third option inside a
#: stratum.
ROWS_PER_SEAT = 2

#: The seed the stride offsets are drawn under. Fixed here rather than left to a
#: caller, and on the record either way: two passes at one seed reach the same
#: rows, and a pass that wants a different sample says which seed it took.
DRAW_SEED = 0

#: What a candidate dominant in no colour cell is stratified under. 308 rows of
#: this pool are, and they are the fillers a target leans on — dropping them from
#: the view would quietly make every target harder than it is.
NO_CELL = "none"


def strata_of(candidate) -> tuple:
    """Every `(kind, mode, cell)` one candidate belongs to.

    More than one where a picture is dominant in more than one cell, which is the
    ordinary case: a candidate is in each of its cells' strata and is drawn into
    the view if **any** of them draws it.
    """
    cells = tuple(candidate.cells) or (NO_CELL,)
    return tuple((candidate.kind, candidate.mode, str(cell)) for cell in cells)


@dataclass
class View:
    """One pass's reachable rows, in rank order, and how they were chosen."""

    #: The rows a pass may reach, strongest first by the pass's own rank key.
    rows: list = field(default_factory=list)
    #: `{stratum name: what it held and what was drawn}`.
    strata: dict = field(default_factory=dict)
    #: Everything the record needs to say what this view was.
    config: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.rows)

    def record(self) -> dict:
        """The view, for the pass record. Every number a reader would need to redraw it.

        The per-stratum table is sorted by how much of the stratum was left
        behind, because that is the column a reader is looking for: a stratum the
        view could only reach a twentieth of is where a shortfall against it is
        the view's answer rather than the pool's.
        """
        rows = sorted(
            self.strata.values(), key=lambda held: (held["kept"] / max(1, held["rows"]), held["of"])
        )
        return {
            **self.config,
            "rows": len(self.rows),
            "strata": len(self.strata),
            "locations": len({row.location for row in self.rows}),
            "sliced": sum(1 for held in rows if held["stride"] > 1),
            "taken_whole": sum(1 for held in rows if held["stride"] == 1),
            "per_stratum": rows,
        }


def stratify(
    candidates,
    n: int,
    rule,
    rank,
    floors: dict | None = None,
    cell_floors: dict | None = None,
    rows_per_seat: int = ROWS_PER_SEAT,
    small: int = SMALL_STRATUM,
    seed: int = DRAW_SEED,
    log=print,
) -> View:
    """The view one pass may reach. `candidates` is the pool and is not touched.

    `rank` is the sort key the pass walks — the pass's own, so the view and the
    walk agree about which row of a place is that place's best. `floors` is the
    mode floors at this `n`, read for the sizing alone: a mode that owes five
    seats must be able to reach at least five, whatever its cells' allowances say.
    `cell_floors` is the **colour** floor at this `n` and is read for exactly the
    same thing on exactly the same argument — a cell that owes twenty seats must
    be able to reach twenty rows that could fill them, and a stratum sized on the
    ceiling alone would size the thinnest cells on what the pool happens to hold.
    `None` is a pass carrying no colour floor.

    Every place's strongest row is kept unconditionally. The size of a stratum's
    **alternate** draw is what `n` seats could spend on that stratum: the fewer of
    its distinct places, `n` itself, and its cell's allowance at this `n`, raised
    to its mode's floor and its cell's floor and then multiplied by
    `rows_per_seat`. A stratum with at or below `small` alternates keeps all of
    them.
    """
    import random

    floors = dict(floors or {})
    cell_floors = dict(cell_floors or {})
    ordered = sorted(candidates, key=rank)
    best, alternates = _population(ordered)
    log(
        f"[view] {len(best):,} place(s) of {len(ordered):,} row(s), plus {len(alternates):,} "
        "stratum alternate(s)"
    )
    #: Every place's strongest row, in before anything is sized. The floor under
    #: this leg is the walk it replaced, and this is that floor.
    drawn: dict = {candidate.key: candidate for candidate in best}

    buckets: dict = {}
    forced: dict = {}
    for candidate in best:
        for stratum in strata_of(candidate):
            forced[stratum] = forced.get(stratum, 0) + 1
    for candidate in alternates:
        for stratum in strata_of(candidate):
            buckets.setdefault(stratum, []).append(candidate)

    rng = random.Random(int(seed))
    table: dict = {}
    for stratum in sorted(set(buckets) | set(forced)):
        rows = buckets.get(stratum, [])
        _kind, mode, cell = stratum
        held = forced.get(stratum, 0)
        seats = min(held + len(rows), int(n), _allowance(rule, cell, n))
        seats = max(seats, int(floors.get(mode, 0)), int(cell_floors.get(cell, 0)), 1)
        quota = (
            len(rows)
            if len(rows) <= int(small)
            else min(len(rows), max(int(small), int(rows_per_seat) * seats))
        )
        stride = max(1, len(rows) // quota) if quota else 1
        offset = 0 if stride == 1 else rng.randrange(stride)
        kept = _slice(rows, quota, stride, offset)
        for candidate in kept:
            drawn[candidate.key] = candidate
        table["|".join(stratum)] = {
            "of": "|".join(stratum),
            "kind": stratum[0],
            "mode": mode,
            "cell": cell,
            "rows": held + len(rows),
            "place_best": held,
            "alternates": len(rows),
            "locations": held + len({row.location for row in rows}),
            "seats_it_could_spend": seats,
            "quota": quota,
            "kept": held + len(kept),
            "stride": stride,
            "offset": offset,
        }

    view = View(
        rows=sorted(drawn.values(), key=rank),
        strata=table,
        config={
            "of": "a per-pass VIEW over the pool. The pool is never mutated and this is "
            "rebuilt from it, so a pass is reproducible from its own record",
            "population": len(ordered),
            "places": len(best),
            "alternates_available": len(alternates),
            "layers": [
                "every place's strongest row by the pass's own rank key — ALWAYS, and "
                "never cut: it is what the sequential seating this leg replaced walked, "
                "so a view holding all of it cannot choose worse than that walk did",
                "plus that place's strongest row in each further stratum it can field — "
                "the alternates, which are what a stratum's quota is spent on",
            ],
            "stratum": "(kind, mode, cell)",
            "no_cell": NO_CELL,
            "small_stratum": int(small),
            "rows_per_seat": int(rows_per_seat),
            "sizing": "min(rows, n, the cell's allowance at n), raised to the mode's floor "
            "and to the cell's floor, times rows_per_seat. A stratum at or below "
            "small_stratum is taken whole",
            "cell_floors": dict(sorted(cell_floors.items())),
            "cell_floors_are": "the colour floor at this n, read for the SIZING alone and "
            "never applied here: a cell that owes seats must be able to reach rows that "
            "could fill them. `{}` is a pass carrying no colour floor",
            "slice": "a seeded stride across the stratum's OWN rank order — band-blind, and "
            "never a top-by-score cut: the worst seated score and the floors are what the "
            "leg maximizes after the seat count, and neither is found at the top of a stratum",
            "draw_seed": int(seed),
        },
    )
    log(
        f"[view] {len(view):,} row(s) over {len(table):,} stratum(s), "
        f"{view.record()['sliced']:,} sliced"
    )
    return view


def _population(ordered) -> tuple[list, list]:
    """`(every place's best row, the stratum alternates)`, apart because they are
    treated apart: the first list is always in the view and the second is what a
    quota is spent on.

    `ordered` is already in rank order, so the first row a place or a
    `(place, stratum)` is seen at **is** its best one and no comparison is needed.
    """
    seen: set = set()
    best: list = []
    alternates: list = []
    for candidate in ordered:
        place = ("place", candidate.location)
        marks = [place] + [("stratum", candidate.location, one) for one in strata_of(candidate)]
        wanted = [mark for mark in marks if mark not in seen]
        if not wanted:
            continue
        seen.update(marks)
        (best if place in wanted else alternates).append(candidate)
    return best, alternates


def _allowance(rule, cell: str, n: int) -> int:
    """How many of `n` seats one stratum's cell may take. `NO_CELL` is uncapped.

    A candidate dominant in nothing is refused by no cell allowance, so its
    stratum's size is bounded by the seats and by its own rows and by nothing
    else. Reading the ceiling for it would invent an allowance the rules do not
    apply.
    """
    return int(n) if cell == NO_CELL else rule.allowed(cell, int(n))


def _slice(rows: list, quota: int, stride: int, offset: int) -> list:
    """`quota` of `rows` spread across them at `stride`, starting at `offset`.

    The strongest alternate is always in, whatever the offset — not as a
    top-by-score cut but as an anchor: one row is not a band, and a stratum whose
    single best alternate the draw stepped over is one the pass cannot reach its
    best of.
    """
    if not rows or stride <= 1 or quota >= len(rows):
        return list(rows)
    taken = {0: rows[0]}
    at = int(offset)
    while at < len(rows) and len(taken) < quota:
        taken[at] = rows[at]
        at += stride
    return [rows[index] for index in sorted(taken)]


__all__ = [
    "DRAW_SEED",
    "NO_CELL",
    "ROWS_PER_SEAT",
    "SMALL_STRATUM",
    "View",
    "stratify",
    "strata_of",
]
