"""The order a gallery page presents its seats in, derived at build time from the seating.

A recorded gallery is chosen on quality and on coverage, and then it is *read* on a
screen. Those are different problems. The seating is right to be ordered by the
leg's own rank key — that is what it maximized — but a page in rank order puts the
strongest rows first, and the strongest rows of this pool look alike: a screenful of
azure spirals, then a screenful of orange threads. The clumping is not a fault in the
seating. It is what a one-dimensional order does to a set chosen on several axes.

So the page takes a **presentation order**: a permutation of the seating, computed
here, at page build, from the rows alone. It moves nothing. No seat changes, no
record is rewritten, no ID moves, no digest moves, and nothing is re-solved — an
existing record gets this order for free the next time [`tentative.page`] runs over
it, which is what makes it safe to change again later.

## Local, not global

Seats are placed one at a time. At each step every unplaced seat is scored against a
**window of the last [`WINDOW`] placed**, and the best is taken.

It is deliberately **not** a farthest-point traversal over the whole set. A global
spread spends its variety at the front and leaves the leftovers — which are alike, or
they would have been spent — adjacent at the end. That is the clump moved rather than
removed. What a reader actually experiences is a screenful at a time, so the
constraint that matters is local and the window is the whole model of it.

## The attribute terms carry the guarantee

[`ATTRIBUTE_WEIGHTS`] is the main term and the embedding is the secondary one, in
that order and not the reverse. A repeat of a colour cell, a mode, a hue family or a
spiral verdict inside the window **costs**, and a repeat nearer the end of the window
costs more than one at its far edge — the seat two tiles back is on the same screen
as the one being placed, and the seat thirty back is on the way off it. Those four
columns are on the row, so the spacing they buy is a property of the ordering rather
than a hope about what the embedding happens to encode.

The embedding is a **tie-breaker with a ceiling**: two candidates that repeat nothing
are ordered by how far each is from the window, and [`DISTANCE_WEIGHT`] is set below
the smallest attribute weight so that no distance can buy back an attribute repeat.

**`p_ge4` descending seeds the page and breaks every remaining tie**, so the strongest
row opens the gallery and quality still orders it wherever spread is indifferent. The
row's `p_ge4` is the fine head's `p_fine(>=4)` — [`solve._seated`] writes the reading
under that name — and `rank`, the fitted cascade key, is a different number.

**No RNG anywhere.** One seating produces one order, on every build and every machine
that holds the same inputs.

## What a themed page does to the second term

A themed gallery is one colour cell by construction, so every picture in it shares a
hue and the embedding — read off a **neutral** render, one frozen colormap for every
location — has nothing to say about colour there in the first place. What is left is
texture and gross structure, and the within-window distances collapse towards each
other. That is the same degeneracy that made the pixel-cloud twin test unusable over a
themed pool (see [`rules.GEOMETRY_RADIUS`]). It is measured rather than assumed:
[`spacing`] reports the within-window distance distribution and the two products do
not read alike.

## The store the second term comes from is not tracked, and the page says so

[`curation.embeddings`] is keyed by **location**, and a gallery row carries its
`location`, so the join is direct and exact. But the store lives under `artifacts/`
and a clone does not have it — while `index.html` is a derivation of two tracked
files and has to stay one. So the distance term is **optional**: with no store the
order is the attribute terms alone, still deterministic, still a permutation, and the
page's header says which basis it used rather than going quiet about it.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = [
    "ATTRIBUTE_WEIGHTS",
    "DISTANCE_CAP",
    "DISTANCE_WEIGHT",
    "WINDOW",
    "basis",
    "order",
    "spacing",
    "vectors_for",
]


#: How many already-placed seats the window holds. **Thirty-two, which is about a
#: screenful**, read off the grid [`tentative._PAGE`] actually renders rather than
#: chosen: `grid-template-columns: repeat(auto-fill, minmax(224px, 1fr))` at a 10px
#: gap inside `main`'s 14px side padding gives **8 columns** on a 1920px viewport —
#: `floor((1920 - 28 + 10) / (224 + 10))` — and a card is a 16:9 thumbnail at the
#: resulting 227px plus three lines of meta, about 187px, against the ~842px the
#: sticky header leaves of a 1080px viewport: **4 rows**. 8 x 4.
#:
#: It is the one number here that is a reading of a layout rather than a judgement,
#: so a grid change is what moves it. Wider or shorter windows are not better or
#: worse in the abstract — they are answers to a different screen.
WINDOW = 32

#: What a repeat inside the window costs, per column, before the recency taper.
#:
#: Four columns, and every one of them is on the gallery row: they are what a reader
#: sees clumping. **`cell` leads** because colour is what the eye groups first and
#: the cell is the finest colour identity a row carries. `mode` is next — two
#: `threads` renders side by side read as one picture twice however differently they
#: are coloured. `hue_family` is the coarse colour axis and is deliberately *below*
#: `cell`: two cells of one family are a milder repeat than the same cell twice, and
#: pricing them equally would make the order fight itself. `spiral` is last and is a
#: single bit, so it can only ever say *another one of those*.
#:
#: **`palette_group` is not among them, and it is the one the prompt for this asked
#: for.** It is on the *solve* seat ([`solve._seated`]) and [`tentative.rows_of`]
#: does not copy it, so no `gallery.jsonl` in this tree holds it — reaching it would
#: mean either a column on the record or a candidate-ledger join at page build, and
#: the second is forty seconds and the end of *the page is written from the two
#: tracked files alone*. `cell` stands in for it and it is the closer axis anyway: a
#: palette group is a fact about the colormap, a cell is a measurement of the
#: picture that came out.
ATTRIBUTE_WEIGHTS: dict[str, float] = {
    "cell": 1.0,
    "mode": 0.8,
    "hue_family": 0.6,
    "spiral": 0.4,
}

#: The columns where only the POSITIVE value is a repeat, and the rest is the page.
#:
#: `spiral` alone, and it is not a special case so much as a different kind of
#: column: `cell` and `mode` are categories, where every value is as much a thing as
#: every other, but `spiral` is a **verdict on a place** and `False` is the absence
#: of the thing. 899 of the 1,000 seats of `20260911T022330Z` are not spirals, so
#: pricing a `False` beside a `False` would spend the term on the 90% that cannot be
#: spread — a run of non-spirals is not a clump, it is the gallery — and would leave
#: the 101 that can be. `None`, a place nobody has scored, is an absence too and is
#: priced the same way: silent.
#:
#: Measured, not argued, on `20260911T022330Z`, whose fullest window of spirals is
#: **13** in the order the page shipped with: pricing every value moved it the
#: **wrong way**, to 16. The True-only rule alone took it to 14, and only with
#: [`_unavoidable`]'s allowance beneath it does it reach **5** — the two are one
#: correction and neither is worth much without the other.
MARK_COLUMNS: frozenset[str] = frozenset({"spiral"})

#: The distance at which two locations are simply *far* and further buys nothing.
#:
#: **0.16**, in [`distinct.METRIC`], and it is read off the distribution this term
#: actually consumes rather than off a radius that reads well.
#:
#: `gallery.RADIUS` — 0.07, the radius the pre-solver draw refused inside — was the
#: obvious constant and it is the **wrong statistic**. It was calibrated against
#: *nearest-neighbour* distances over the whole admitted population, median 0.024,
#: and what this term consumes is a *within-window minimum over 32 seats of a
#: gallery already chosen for diversity*. Those are different distributions and they
#: do not overlap much: at a cap of 0.07, **96%** of the general page's minimums and
#: **100%** of the themed page's were already at or past it, so the reward was
#: saturated almost everywhere and the term discriminated between nothing. Measured
#: on `20260911T022330Z` and `20260913T001955Z`, whose within-window minimums run
#: p10 0.0724 / 0.0790 and p90 0.1587 / 0.1635.
#:
#: So the cap sits at the p90 of that, which leaves the term live across the body of
#: the range and saturated only in its tail. It is **not** the whole distance
#: allowed to matter: past the cap the term still saturates on purpose, because this
#: is a tie-breaker between candidates that repeat nothing and letting it grow
#: without bound would make it the global spread this module is not.
#:
#: The check that it has not over-reached is the *attribute* spacings, which is why
#: it is set where it is and not higher: at 0.16 the general page's minimum gap
#: between seats sharing a cell holds at 3 and the median rises 29 -> 32, while at
#: 0.20 the minimum falls back to 1 — the distance term buying itself a seat at the
#: colour term's expense, which is exactly the failure [`DISTANCE_WEIGHT`] bounds
#: and this cap is the second bound on.
DISTANCE_CAP = 0.16

#: What the whole distance term is worth. **0.25**, below the smallest weight in
#: [`ATTRIBUTE_WEIGHTS`], so being maximally far from the window can never pay for
#: repeating a spiral verdict — let alone a cell. That inequality is the "normalised
#: so it cannot dominate" rule, and it is an inequality between constants rather
#: than a hope about the distribution.
DISTANCE_WEIGHT = 0.25

#: What an unknown distance is worth: the **midpoint** of the term's range.
#:
#: 32 of the 1,000 seats of `20260911T022330Z` have no vector — locations admitted
#: since the store was last built — and they must not collect at either end of the
#: page, which is the artifact this whole module exists to remove. The midpoint is
#: the only value that cannot systematically advance or retard such a row, and it
#: needs no statistic of the page to compute, so [`order`] stays a pure function of
#: its inputs.
UNKNOWN_DISTANCE = DISTANCE_WEIGHT / 2

#: What the page says it ordered on, and what [`basis`] answers.
WITH_EMBEDDING = "attributes + embedding"
ATTRIBUTES_ONLY = "attributes only"


def basis(vectors: dict | None) -> str:
    """Which of [`WITH_EMBEDDING`] / [`ATTRIBUTES_ONLY`] an order was taken under.

    On the page rather than in a comment: the same rows order two ways depending on
    whether this machine holds the embedding store, and a reader comparing two
    builds of one record needs to be told which they are looking at.
    """
    return WITH_EMBEDDING if vectors else ATTRIBUTES_ONLY


#: What a column says about a row that is not a repeat of anything. Counted nowhere,
#: priced nowhere, and distinct from `None` — which is a real category value in every
#: column that is not in [`MARK_COLUMNS`].
SILENT = object()


def _value(row: dict, column: str):
    """One row's value in one attribute column, as a hashable a repeat is counted on.

    `None` is its own value and not a wildcard in a category column: a run of seats
    with no dominant cell is exactly as much of a clump as a run that shares one, and
    the page shows both the same way. In a [`MARK_COLUMNS`] column it is an absence
    and comes back [`SILENT`], along with every other non-positive value.
    """
    held = row.get(column)
    if column in MARK_COLUMNS:
        return True if held is True else SILENT
    return held


def _quality(row: dict) -> float:
    """The row's `p_ge4`, with an unread row below every read one.

    `-1.0` for a missing or unreadable reading, which is the page's own convention
    for the same column (`(b[key] ?? -1)` in the sort) — so the tie-break here and
    the reader's *P(>=4), best first* agree about where an unscored seat goes.
    """
    held = row.get("p_ge4")
    try:
        return -1.0 if held is None else float(held)
    except (TypeError, ValueError):
        return -1.0


def vectors_for(rows, path: Path | None = None) -> dict:
    """`{location key: unit vector}` for the locations these rows seat.

    One streamed pass of [`curation.embeddings`]'s store, keeping only the keys asked
    for and decoding only their vectors — 0.60 s to parse the 41,415 rows of the
    store of 2026-09-04 and a few milliseconds to unpack a thousand of them.

    `{}` where there is no store, which is what a clone has and is not an error:
    [`order`] runs on the attribute terms alone and [`basis`] says so. A row with no
    `location` — the shape a minimal record carries — simply asks for nothing.
    """
    from fractal_wallpapers.curation import embeddings

    wanted = {str(row["location"]) for row in rows if row.get("location")}
    store = embeddings.store_path() if path is None else Path(path)
    if not wanted or not store.is_file():
        return {}
    out: dict = {}
    with store.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            held = json.loads(line)
            key = str(held.get("key"))
            if key in wanted and key not in out:
                out[key] = embeddings.unpack(held["vector"])
    return out


def _matrix(rows, vectors: dict):
    """`(matrix, has_vector)` — one row of unit vector per seat, and which are real.

    A seat whose location is unembedded gets a zero row and a `False`, so the
    arithmetic below stays one array rather than a branch per seat.
    """
    import numpy

    found = [vectors.get(str(row.get("location"))) for row in rows]
    width = next((held.shape[0] for held in found if held is not None), 0)
    if not width:
        return None, [False] * len(rows)
    matrix = numpy.zeros((len(rows), width), dtype=numpy.float32)
    has = []
    for at, held in enumerate(found):
        has.append(held is not None)
        if held is not None:
            matrix[at] = held
    return matrix, has


def _taper(held: int, window: int) -> float:
    """The recency weights of a window holding `held` seats, summed.

    The allowance below is subtracted from a penalty measured in these units, so it
    has to be stated in them — and **the window in force is not always the full
    one**. A page opens with an empty window that fills one seat at a time, and a
    record shorter than [`WINDOW`] never fills it at all. Sizing the allowance off
    the full window regardless made it far larger than anything a short window could
    accrue, which left the order inert exactly where a reader starts: the first
    screenful. It is the bug the alternation guard in `tests/test_page_order.py`
    catches, and on eight rows of two cells it produced the arrival order.
    """
    return sum((window - back + 1) / window for back in range(1, min(held, window) + 1))


def _unavoidable(rows) -> dict:
    """`{(column, value): the share of the seating that value holds}`.

    **The term that stops the greedy hoarding, and it is the difference between a
    page and a page whose last eighth is the leftovers.**

    A value holding a share `s` of the seating appears about `s x window` times in
    any window, in *every* order there is — 263 of the 1,000 seats of
    `20260911T022330Z` are `tia`, so a screenful holds eight of them whatever this
    function does. Charging that the same as a rare value's second appearance is what
    made a plain greedy spend its scarce rows early and leave the common ones to run
    out together: every adjacent-mode pair of the first draft landed at position 864
    or later, 47 of them, all in the last seventh of the page.

    So a repeat is priced on its **excess over what is unavoidable**. An abundant
    value pays nothing for being as present as it has to be and pays from the moment
    it is more present than that; a rare value pays from its second appearance,
    because its share buys it almost nothing. Nothing is tuned: the share is counted
    off the seating being ordered, so the term sizes itself per page and per column.

    A **share** rather than a count, because the window it is charged against grows
    as the page opens: [`_taper`] turns it into the allowance in force at each step.
    """
    if not rows:
        return {}
    counts: dict = {}
    for row in rows:
        for column in ATTRIBUTE_WEIGHTS:
            value = _value(row, column)
            if value is SILENT:
                continue
            key = (column, value)
            counts[key] = counts.get(key, 0) + 1
    return {key: held / len(rows) for key, held in counts.items()}


def order(rows, vectors: dict | None = None, window: int = WINDOW) -> list[int]:
    """The seating's positions, in the order the page presents them.

    Returns **indices into `rows`** — `order(rows)[0]` is the seat that opens the
    page — and it is always a permutation: every seat exactly once, none dropped and
    none doubled. That is the guard worth having and `tests/test_page_order.py`
    holds it.

    `vectors` is [`vectors_for`]'s map, or `None`/`{}` for the attribute terms alone.
    `window` is [`WINDOW`] unless a caller is measuring what the window buys.
    """
    rows = list(rows)
    if len(rows) < 2:
        return list(range(len(rows)))
    window = max(1, int(window))
    matrix, has_vector = (None, [False] * len(rows))
    if vectors:
        matrix, has_vector = _matrix(rows, vectors)

    ring = None
    if matrix is not None:
        import numpy

        # The last `window` rows of dot products, one row per placed seat, so the
        # distance to the window is `1 - ring.max(axis=0)` and costs one matvec a
        # step instead of a rescan of the window. A seat with no vector writes -1.0,
        # which is the lowest a cosine can be and so never wins that maximum.
        ring = numpy.full((window, len(rows)), -1.0, dtype=numpy.float32)

    shares = _unavoidable(rows)
    unplaced = set(range(len(rows)))
    placed: list[int] = []
    while unplaced:
        held = placed[-window:]
        # The window's repeats, tapered by recency: the seat one back weighs 1, the
        # seat `window` back weighs 1/window. Rebuilt per step rather than carried,
        # because the window slides at both ends and 4 x 32 lookups is nothing.
        penalty: dict = {}
        for back, at in enumerate(reversed(held), start=1):
            weight = (window - back + 1) / window
            for column in ATTRIBUTE_WEIGHTS:
                value = _value(rows[at], column)
                if value is SILENT:
                    continue
                key = (column, value)
                penalty[key] = penalty.get(key, 0.0) + weight
        # The allowance in force NOW, which is the share scaled to the window that
        # actually exists at this step rather than to a full one — see [`_taper`].
        taper = _taper(len(held), window)
        far = None
        if ring is not None and placed:
            far = 1.0 - ring[: min(len(placed), window)].max(axis=0)

        best = None
        for at in unplaced:
            row = rows[at]
            cost = 0.0
            for column, weight in ATTRIBUTE_WEIGHTS.items():
                key = (column, _value(row, column))
                seen = penalty.get(key)
                if seen:
                    over = seen - taper * shares.get(key, 0.0)
                    if over > 0.0:
                        cost += weight * over
            if not placed:
                reward = 0.0
            elif far is None or not has_vector[at]:
                reward = UNKNOWN_DISTANCE
            else:
                reward = DISTANCE_WEIGHT * min(1.0, float(far[at]) / DISTANCE_CAP)
            # `key` last so two rows alike in everything measured still order the
            # same way on every machine: there is no RNG here and no dict order
            # either.
            mark = (cost - reward, -_quality(row), str(row.get("key") or ""))
            if best is None or mark < best[0]:
                best = (mark, at)

        taken = best[1]
        unplaced.discard(taken)
        if ring is not None:
            slot = len(placed) % window
            if has_vector[taken]:
                ring[slot] = matrix @ matrix[taken]
            else:
                ring[slot] = -1.0
        placed.append(taken)
    return placed


# --------------------------------------------------------------------------- #
# What the ordering did, which is the only way to know it did anything.
# --------------------------------------------------------------------------- #
def _gaps(rows, placement: list[int], column: str) -> dict:
    """How far apart consecutive seats sharing one column's value land.

    Pooled across the column's values rather than reported per value: the question
    is whether *any* repeat lands close, so the minimum over the whole column is the
    number that answers it and the median says whether the ordering moved the body
    of the distribution or only its tail.
    """
    seen: dict = {}
    for position, at in enumerate(placement):
        value = _value(rows[at], column)
        if value is SILENT:
            continue
        seen.setdefault(value, []).append(position)
    found = [
        later - earlier
        for positions in seen.values()
        for earlier, later in zip(positions, positions[1:], strict=False)
    ]
    if not found:
        return {"values": len(seen), "pairs": 0, "min": None, "median": None}
    found.sort()
    middle = len(found) // 2
    median = float(found[middle]) if len(found) % 2 else (found[middle - 1] + found[middle]) / 2.0
    return {"values": len(seen), "pairs": len(found), "min": found[0], "median": median}


def _spirals(rows, placement: list[int], window: int) -> dict:
    """The spiral clumping, said two ways because *run* is ambiguous on its own.

    `longest_run` is consecutive tiles; `most_in_a_window` is the fullest window of
    [`WINDOW`] there is. The first is what a reader notices, the second is what the
    ordering is actually steering, and a page can move one without the other.
    """
    flags = [bool(rows[at].get("spiral")) for at in placement]
    longest = held = 0
    for flag in flags:
        held = held + 1 if flag else 0
        longest = max(longest, held)
    fullest = 0
    running = 0
    for position, flag in enumerate(flags):
        running += flag
        if position >= window:
            running -= flags[position - window]
        fullest = max(fullest, running)
    return {
        "seats": sum(flags),
        "longest_run": longest,
        "most_in_a_window": fullest,
        "window": window,
    }


def _distances(rows, placement: list[int], vectors: dict, window: int) -> dict:
    """The within-window minimum distance: mean, median, and how much of it is real.

    Only positions whose own seat is embedded **and** whose window holds at least one
    embedded seat contribute, and `measured` says how many did. A mean taken over a
    page where a thirtieth of the seats have no vector is a mean over the rest, and
    it says so rather than quietly imputing.
    """
    if not vectors:
        return {"embedded": 0, "of": len(placement), "measured": 0, "mean": None, "median": None}
    import numpy

    matrix, has_vector = _matrix([rows[at] for at in placement], vectors)
    if matrix is None:
        return {"embedded": 0, "of": len(placement), "measured": 0, "mean": None, "median": None}
    found = []
    for position in range(1, len(placement)):
        if not has_vector[position]:
            continue
        start = max(0, position - window)
        neighbours = [at for at in range(start, position) if has_vector[at]]
        if not neighbours:
            continue
        found.append(1.0 - float(numpy.max(matrix[neighbours] @ matrix[position])))
    if not found:
        return {
            "embedded": sum(has_vector),
            "of": len(placement),
            "measured": 0,
            "mean": None,
            "median": None,
        }
    found_sorted = sorted(found)
    middle = len(found_sorted) // 2
    median = (
        found_sorted[middle]
        if len(found_sorted) % 2
        else (found_sorted[middle - 1] + found_sorted[middle]) / 2.0
    )
    return {
        "embedded": sum(has_vector),
        "of": len(placement),
        "measured": len(found),
        "mean": round(sum(found) / len(found), 6),
        "median": round(median, 6),
    }


def spacing(rows, placement: list[int], vectors: dict | None = None, window: int = WINDOW) -> dict:
    """What one order realized, as the numbers a before/after is read on.

    Takes the placement rather than computing one, so the *same* function measures
    the order this module derives and the order the page shipped with — which is the
    only way the comparison is a comparison rather than two instruments.
    """
    rows = list(rows)
    window = max(1, int(window))
    return {
        "seats": len(rows),
        "window": window,
        "gaps": {column: _gaps(rows, placement, column) for column in ATTRIBUTE_WEIGHTS},
        "spiral": _spirals(rows, placement, window),
        "distance": _distances(rows, placement, vectors or {}, window),
    }
