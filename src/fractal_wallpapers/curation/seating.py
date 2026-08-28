"""Seat a gallery off the ledger with a trivial greedy, and keep every refusal.

The other half of [`curation.headroom`]. A census is an upper bound — it says what
could not possibly be seated. This is a **lower bound**: the simplest rule that
fills seats, run so that the gap between the two is visible. Close together and
the answer is known; far apart and that gap is the size of the prize an exact
solve is competing for, which is usually the signal to go and make more candidates
instead.

It only chooses. It proposes nothing and renders nothing: every reading about a
candidate — the colour, the palette group, the mode, the score — is already on the
ledger row, so a [`ceiling.Lens`] here is a **lookup** and never a second
derivation. Nothing here re-decodes a JPEG to be told what the row already says.

It does open pictures, for one rule and only for it. The twin test is a statement
about two *finished pictures* and there is no reading on the row that answers it,
so a candidate that has cleared every arithmetic test pays one pixel-cloud
signature. That is why the twin test runs **last** of the five: the four rules
above it are counts, they refuse most of what they see, and each one they refuse
is a signature not made.

## Fill by scarcity, not by score

Ordering by score alone converts satisfiable problems into apparent infeasibility.
Where the mode floors ask for most of the gallery — as the flat one-per-mode did
at `n = 20`, eighteen of twenty seats over eleven modes that can field a handful
of places between them — a walk down the ranked list spends its first seats on
`smooth` and `exp_smoothing`, which have thousands of candidates each, and then
reports that fifteen modes could not be seated. Every one of them could have been.

So the mandated constraints are seated **from their own subpools first, scarcest
first**, and only what is left over is drawn from the general pool by score. The
order is a fact about supply and not a preference: a mode with three eligible
places is seated before a mode with eight hundred because the three can only be
spent one way.

[`solve.mode_floor`] is now `floor(n / 100)`, so below a hundred seats there is no
mandate at all and this leg does nothing — which is the honest shape of a
twenty-seat debug gallery. `--mode-floor` puts an artificial floor back so the leg
is still exercised, and a record taken under one says so.

## One rule is hard and every other is soft

**One wallpaper per location** is absolute — it is the identity of the thing being
chosen, not a preference about it. Everything else records a shortfall and carries
on: the cell and family allowances, the mode floors, the palette-group cap. There
is no fallback leg, no least-violating rescue and no padding. An unfilled seat is
the honest output, and it is the number the census is a bound on.

## Two rules under one word, in the two places they belong

[`curation.distinct`] measured what "diversity" was hiding: *are these two the
same place* and *do these two read as one wallpaper* are near-orthogonal
questions — Pearson 0.034 — and one rule cannot answer both. So there are two, and
neither is in the solve.

**Are these two the same place** is [`distinct.preselect`], at pool construction,
before this module is called: a greedy suppression at [`distinct.PRESELECT_RADIUS`]
over the neutral descriptors. It refuses a *place*, so everything that place
carries goes with it, and it is recorded here as [`SAME_PLACE`] rather than as a
seating rule, because that is what it is.

**Do these two read as one wallpaper** is the twin test, at [`ceiling.TAU`], and
it is sequential state in this walk. It is the last of [`RULES`] and the only one
that opens a picture. It does not enter the solve and the solve's complexity does
not change: a rule that reads the seats already taken is a rule a greedy can apply
for the cost of one signature per surviving candidate, where a solver would have
to carry it as a quadratic family of rows.

## A greedy shortfall is not infeasibility

Every unseated candidate is recorded with the rule that refused it, aggregated by
cell, family, mode and partition, and that aggregate is the product — it is the
"what do we make next" answer. But a shortfall here means *this greedy did not find
it* and never *the pool does not hold it*. The only infeasibility claims this
project makes are [`curation.headroom`]'s necessary conditions, and the record
carries both so the two are read together.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fractal_wallpapers.curation import (
    candidate_ledger,
    ceiling,
    distinct,
    headroom,
    solve,
)

#: The schema every record this module writes carries.
#:
#: **2**: the twin rule joined [`RULES`], the mode floor became a function of `n`
#: rather than a constant, and the mode block counts representation separately
#: from the floor. A schema 1 record was taken under a flat floor of one and no
#: pairwise rule at all, and the two are not comparable seatings.
SCHEMA = 2

#: The subtree a seating's record and its sheet land in.
UNIT = "seat"

#: How many of the refused the contact sheet shows beside the seated, per rule.
#: Enough that a rule's refusals are a sample rather than an anecdote, few enough
#: that the page is one page.
SHOWN = 6

#: The rules, in the order the greedy applies them. The first to fail names the
#: refusal, which is what makes the rejection ledger a partition of the pool
#: rather than a tally that double-counts.
#:
#: `location` is hard and so is `twin` — both are statements about the identity
#: of the thing being chosen rather than preferences about it. The three between
#: them are soft: a candidate that fails one is passed over while a seat is still
#: being chosen, and the shortfall is recorded — but nothing is ever seated by
#: relaxing a rule it failed, so a soft rule that nothing can satisfy leaves the
#: seat empty.
#:
#: `twin` is **last** because it is the only one that costs anything. The four
#: above it are dictionary lookups over counts already held; this one decodes a
#: JPEG, builds half a mebibyte of pixel cloud and compares it to every seat
#: already taken. Every candidate the cheap rules refuse is a signature not made.
#:
#: `picture_unreadable` sits immediately before it and is the same rule's other
#: outcome: a candidate whose JPEG cannot be opened is refused rather than
#: admitted. It should be unreachable from a pool `solve.pool` built, which now
#: excludes an absent picture itself — it is here for the file that disappears
#: mid-pass, and because a rule that reads pixels must fail closed.
RULES = (
    "location",
    "group_cap",
    "cell_allowance",
    "family_allowance",
    "picture_unreadable",
    "twin",
)

#: What a candidate that broke no rule and simply lost is recorded as. It is a far
#: weaker statement than any of [`RULES`] and is kept apart for that reason: a
#: mine aimed at this population would be aimed at nothing.
UNSEATED = "the_greedy_had_no_seat_left"

#: What a candidate below its own mode's bar is recorded as. Not a refusal by any
#: selection rule — it never entered the population the seating chooses from.
BELOW_BAR = "below_its_mode_bar"

#: What a candidate whose **place** the neutral pre-selection refused is recorded
#: as. Kept apart from [`RULES`] for the same reason [`BELOW_BAR`] is: it is pool
#: construction and not a seat this walk declined to give. The place lost to
#: another place inside [`distinct.PRESELECT_RADIUS`], and no colouring of it
#: could have changed that.
SAME_PLACE = "another_place_is_the_same_place"

#: How many seated pictures inside [`ceiling.TAU`] it takes to refuse. **One.**
#:
#: Deliberately stricter than [`ceiling.TWINS`], which is 2 and is the shipped
#: gallery pass's setting — there the argument is that one near neighbour is a
#: collection with a pair in it and three of a kind is what a person notices. A
#: seating is choosing from fifteen thousand candidates for twenty seats and can
#: afford the strict form, and the lazy pairwise rule in [`curation.solve`] is
#: already the strict form, so this matches the solve rather than the pass. The
#: two are on the record wherever they meet.
TWIN_NEIGHBOURS = 1

#: How many signatures the seating's pixel-cloud cache holds before it forgets the
#: oldest. 256 is 128 MiB. The seated are **held** and never counted against it,
#: so the only thing this buys is the second offer of a candidate the scarcity leg
#: already tested — a few dozen, not a few thousand.
SIGNATURE_CACHE = 256


class SeatingRefused(RuntimeError):
    """The seating cannot be run."""


# --------------------------------------------------------------------------- #
# The lens, off the rows.
# --------------------------------------------------------------------------- #
def lens_for(rows=None) -> ceiling.Lens:
    """A [`ceiling.Lens`] that reads the ledger and never a picture.

    [`ceiling.Lens.reading`] decodes a JPEG unless it is handed a `stored_of`, and
    every ledger row already carries the reading in its `colour` block — so a
    seating driven off the ledger would otherwise spend a decode per candidate to
    be told what the row says. [`candidate_ledger.reading_source`] is that lookup,
    built over the whole store once however many candidates are tested.

    The pixel-cloud half stays unwired here even though the twin rule is now
    applied: [`Twins`] holds that state itself, keyed by candidate key and with
    the seated pictures **held** rather than cached, which is a different lifetime
    from anything a lens knows about.
    """
    return ceiling.Lens(
        render_of=lambda candidate: None,
        group_of=lambda candidate: str(candidate.get("palette_group")),
        stored_of=candidate_ledger.reading_source(rows),
    )


def clouds_for(candidates, cache: int = SIGNATURE_CACHE):
    """A [`pixel_clouds.Clouds`] over the pool, addressed by **candidate key**.

    By key and not by path because the twin test is per candidate: one place may
    carry fifty rows, they are fifty different pictures, and the rule is about the
    pictures. A row whose picture is not on disk reads as `None` and is admitted —
    [`Twins`] counts those rather than refusing on them, because a missing file is
    a fact about this checkout and not about the wallpaper.
    """
    from pathlib import Path

    from fractal_wallpapers.palettes import pixel_clouds
    from fractal_wallpapers.paths import rehome

    pictures = {candidate.key: candidate.picture for candidate in candidates}

    def path_of(name):
        held = pictures.get(str(name))
        if not held:
            return None
        where = Path(rehome(held))
        return where if where.is_file() else None

    return pixel_clouds.Clouds(path_of, cache=int(cache))


class Twins:
    """The twin rule's sequential state: is this picture one of the seated ones?

    Two stores, and the split is [`solve.BOUND`]'s. Every seated picture is kept
    twice — once as its full signature, held in the [`pixel_clouds.Clouds`], and
    once as [`solve.reduce_signature`]'s four blocks of quantiles, sixteen
    kibibytes against half a mebibyte. A candidate is screened against the reduced
    stack first, which is a sound *lower* bound on the metric, so a seat the bound
    puts at or beyond [`ceiling.TAU`] provably cannot be a twin and is never
    measured. Only the survivors cost a full comparison.

    The bound settles almost everything — 99.2% of the pairs in the sweep that
    measured this pool — but the saving is arithmetic and not I/O: the candidate's
    own signature has to be made either way, and that is the tenth of a second.
    What the bound buys is that the cost of the rule does not grow with the number
    of seats already taken.
    """

    def __init__(self, clouds, tau: float | None = None, neighbours: int = TWIN_NEIGHBOURS):
        self.clouds = clouds
        self.tau = ceiling.TAU if tau is None else float(tau)
        self.neighbours = int(neighbours)
        #: The seated, in seating order. Parallel to the reduced stack.
        self.keys: list = []
        self._reduced: list = []
        self._stack = None
        self.tested = 0
        self.settled_by_the_bound = 0
        self.measured = 0
        self.without_a_picture = 0

    def refuses(self, key: str) -> dict | None:
        """The seated picture this candidate is a twin of, or `None`.

        **A candidate whose picture cannot be read is REFUSED, not admitted.**
        It used to be admitted, on the reasoning that a missing file is a fact
        about the checkout rather than about the wallpaper — which is true, and
        is still the wrong direction to fail in. Admitting means the diversity
        rule silently stops applying to exactly the candidates nothing can check,
        and that put untested rows in a gallery: three seats of `p2b_n150` were
        taken by candidates whose files had been swept. Refusing costs a seat to
        a candidate that might have been fine; admitting costs the rule itself.
        The refusal is reported under its own name and never as a twin, because
        "I could not read this" is not "this is a duplicate".
        """
        import numpy

        from fractal_wallpapers.palettes import groups, pixel_clouds

        made = self.clouds.of(str(key))
        if made is None:
            self.without_a_picture += 1
            return {"unreadable": True, "why": "the candidate's picture is not on disk"}
        if not self._reduced:
            return None
        self.tested += 1
        if self._stack is None:
            self._stack = numpy.stack(self._reduced)
        mine = solve.reduce_signature(made).reshape(-1)
        width = groups.DIRECTIONS * solve.BOUND_BLOCKS
        lower = numpy.abs(self._stack - mine).sum(axis=1, dtype=numpy.float64) / width
        close = [int(at) for at in numpy.nonzero(lower < self.tau)[0]]
        self.settled_by_the_bound += len(self._reduced) - len(close)
        near = []
        for at in close:
            self.measured += 1
            gap = pixel_clouds.distance(made, self.clouds.of(self.keys[at]))
            if gap < self.tau:
                near.append((gap, self.keys[at]))
        if len(near) < self.neighbours:
            return None
        near.sort()
        return {
            "twin_of": near[0][1],
            "pixel_cloud": round(near[0][0], 6),
            "seated_within_tau": len(near),
        }

    def hold(self, key: str) -> bool:
        """Keep one seated picture's signature, in both forms. `False` if it has none."""
        import numpy

        made = self.clouds.of(str(key))
        if made is None:
            return False
        self.clouds.hold(str(key))
        self.keys.append(str(key))
        self._reduced.append(numpy.asarray(solve.reduce_signature(made).reshape(-1)))
        self._stack = None
        return True

    def record(self) -> dict:
        """What the rule cost and what it settled, for the pass record."""
        return {
            "tau": self.tau,
            "tau_from": "ceiling.TAU",
            "neighbours": self.neighbours,
            "metric": "pixel-cloud sliced Wasserstein-1 between two finished pictures",
            "bound": solve.BOUND,
            "candidates_tested": self.tested,
            "seat_comparisons_settled_by_the_bound": self.settled_by_the_bound,
            "seat_comparisons_measured": self.measured,
            "signatures_made": self.clouds.made,
            "signature_cache_hits": self.clouds.hits,
            "refused_without_a_picture_on_disk": self.without_a_picture,
            "seated_pictures_held": len(self.keys),
        }


# --------------------------------------------------------------------------- #
# The seating.
# --------------------------------------------------------------------------- #
class Seats:
    """What has been seated, and the three soft tests read off it.

    Holds counts and never pictures. Each test answers "would seating this break
    the rule", so the caller can ask before it commits and record the answer when
    it does not.
    """

    def __init__(self, rule: ceiling.Rule, n: int, floor: int = 0, twins: Twins | None = None):
        self.rule = rule
        self.n = int(n)
        #: How many seats each production mode's floor asks for, at this `n`.
        self.floor = int(floor)
        #: The twin rule's state, or `None` where the rule is not applied.
        self.twins = twins
        self.chosen: list = []
        self.places: set = set()
        self.cells: dict = {}
        self.families: dict = {}
        self.groups: dict = {}
        self.modes: dict = {}
        #: `{rule: how many times it was the reason}`, over every candidate tested.
        self.refusals: dict = {name: 0 for name in RULES}
        #: `{key: which seated picture it was a twin of}`, for the record.
        self.twin_of: dict = {}

    def refuses(self, candidate) -> str | None:
        """The first rule this candidate fails, or `None`. [`RULES`] order.

        The four arithmetic rules first and the twin test last, because that one
        costs a pixel-cloud signature and the four above it refuse most of what
        they see.
        """
        if candidate.location in self.places:
            return "location"
        if self.groups.get(candidate.group, 0) >= self.rule.group_cap:
            return "group_cap"
        for cell in candidate.cells:
            if self.cells.get(cell, 0) + 1 > self.rule.allowed(cell, self.n):
                return "cell_allowance"
        for family in candidate.families:
            if self.families.get(family, 0) + 1 > self.rule.allowed(family, self.n):
                return "family_allowance"
        if self.twins is not None:
            found = self.twins.refuses(candidate.key)
            if found is not None:
                if found.get("unreadable"):
                    return "picture_unreadable"
                self.twin_of[candidate.key] = found
                return "twin"
        return None

    def seat(self, candidate, why: str) -> dict:
        """Seat one candidate. The caller has already asked [`refuses`]."""
        self.chosen.append((candidate, why))
        self.places.add(candidate.location)
        self.groups[candidate.group] = self.groups.get(candidate.group, 0) + 1
        self.modes[candidate.mode] = self.modes.get(candidate.mode, 0) + 1
        for cell in candidate.cells:
            self.cells[cell] = self.cells.get(cell, 0) + 1
        for family in candidate.families:
            self.families[family] = self.families.get(family, 0) + 1
        if self.twins is not None:
            self.twins.hold(candidate.key)
        return {"key": candidate.key, "seated_for": why}

    @property
    def full(self) -> bool:
        return len(self.chosen) >= self.n


def _ranking(order: dict | None):
    """The sort key one seating walks its pool in. Strongest first, ties by key.

    `None` is the incumbent: the render judge's `P(>=4)` off the candidate. A
    mapping is [`curation.rank_key`]'s, and a candidate it has no value for sorts
    **last** rather than at zero — zero is a real rank value under a fitted key,
    and a row nobody could read is not a row that scored badly.
    """
    if order is None:
        return lambda candidate: (0, -candidate.score, candidate.key)
    return lambda candidate: (
        (0, -float(order[candidate.key]), candidate.key)
        if candidate.key in order
        else (1, 0.0, candidate.key)
    )


def scarcity(kept, modes, rank=None) -> list:
    """The mandated constraints, scarcest first. `[(mode, its subpool)]`.

    The only mandate the **default** target vector produces is the mode floor:
    every production mode wants [`solve.mode_floor`] seats and no colour cell is
    demanded, because no `--target` is set. So the order is by how many distinct
    locations each mode can field, ascending — a mode with three is spent before a
    mode with eight hundred, because the three can only be spent one way.

    A mode with nothing at all is kept in the list rather than dropped, so the
    record says it was asked for and could not be met.

    Each subpool is ordered by the **same** `rank` the general leg walks, so a
    seating on a fitted key is on that key in both legs. A mode floor spent by the
    judge's order while everything else went by another key would be a gallery
    seated two ways.
    """
    rank = _ranking(None) if rank is None else rank
    by_mode: dict = {name: [] for name in modes}
    for candidate in kept:
        if candidate.mode in by_mode:
            by_mode[candidate.mode].append(candidate)
    ranked = sorted(
        by_mode.items(),
        key=lambda item: (len({c.location for c in item[1]}), item[0]),
    )
    return [(name, sorted(members, key=rank)) for name, members in ranked]


def seat(
    candidates,
    n: int = candidate_ledger.FIRST_SOLVE,
    rule: ceiling.Rule | None = None,
    floor: int | None = None,
    radius: float | None = distinct.PRESELECT_RADIUS,
    twin: bool = True,
    group_cap: str = ceiling.IDENTITY,
    order: dict | None = None,
    log=print,
) -> dict:
    """Fill `n` seats by scarcity then by the rank key, and keep every refusal.

    Pool construction first: the bars, then the neutral pre-selection at `radius`
    — `None` for no pre-selection at all, which is what a caller comparing against
    a schema 1 record wants. Then two legs over one [`Seats`]. The first walks the
    mandated constraints in scarcity order and takes each one's best candidate
    that nothing refuses; the second walks whatever is left of the ranked pool. A
    candidate refused in the first leg is offered again in the second, because the
    state it was refused against has moved on.

    `floor` is the **artificial** mode floor a debug gallery uses to exercise the
    scarcity leg at a size where [`solve.mode_floor`] asks for nothing. Unset, the
    floor is the real one and the record says so.

    ## The two flags, and why the incumbent is still the default

    `group_cap` names the rule the palette-group cap runs under —
    [`ceiling.IDENTITY`], one seat a group, or [`ceiling.PROPORTIONAL`],
    `max(1, floor(0.025 n))`. `order` is `{candidate key: rank value}`, the sort
    key the pool is walked in; `None` is the render judge's `P(>=4)`, which is
    what every gallery this project has seated was ordered by.

    Both default to the incumbent so that a caller who does not ask gets the
    seating this project has always taken. **Neither touches the pool**: the bars,
    the clearing rule and the neutral pre-selection all read the judge's own
    columns, so two seatings differing in a flag differ in the sort order and in
    the cap and in nothing else, which is what makes a before/after exact.

    A candidate `order` has no value for is ranked **last** and counted. It is not
    refused — no rule acted on it — and it has not earned a place ahead of the
    rows the key could read.
    """
    from fractal_wallpapers import engine

    modes = list(engine.production_modes())
    cap = ceiling.group_cap(n, group_cap)
    if rule is None:
        rule = solve.rule_for()
        rule.group_cap = cap
    natural = solve.mode_floor(n)
    floor = natural if floor is None else int(floor)
    table = headroom.bars(candidates)
    cleared = headroom.clearing(candidates, table)
    log(f"[seat] {len(cleared):,} of {len(candidates):,} candidates clear their mode's bar")
    #: `{key: the rule that refused it, the last time it was offered}`.
    refused: dict = {}
    if radius is None:
        kept, preselection = list(cleared), {"skipped": "no neutral pre-selection was applied"}
    else:
        kept, preselection = distinct.preselect(cleared, radius=float(radius), log=log)
        survived = {candidate.key for candidate in kept}
        for candidate in cleared:
            if candidate.key not in survived:
                refused[candidate.key] = SAME_PLACE
    rank = _ranking(order)
    unranked = 0 if order is None else sum(1 for c in kept if c.key not in order)
    kept.sort(key=rank)
    twins = Twins(clouds_for(kept)) if twin else None
    seats = Seats(rule, n, floor=floor, twins=twins)

    mandated = scarcity(kept, modes, rank=rank)
    picked: set = set()
    for mode, members in mandated:
        if seats.full:
            break
        if seats.modes.get(mode, 0) >= floor:
            continue
        for candidate in members:
            why = seats.refuses(candidate)
            if why is None:
                seats.seat(candidate, f"mode_floor:{mode}")
                picked.add(candidate.key)
                refused.pop(candidate.key, None)
                break
            refused[candidate.key] = why
            seats.refusals[why] += 1

    for candidate in kept:
        if seats.full:
            break
        if candidate.key in picked:
            continue
        why = seats.refuses(candidate)
        if why is None:
            seats.seat(candidate, "general_pool")
            picked.add(candidate.key)
            refused.pop(candidate.key, None)
        else:
            refused[candidate.key] = why
            seats.refusals[why] += 1

    # Everything the walk never reached, because the seats ran out. Recorded as
    # its own thing and never as a refusal: no rule acted on it.
    for candidate in kept:
        if candidate.key not in picked and candidate.key not in refused:
            refused[candidate.key] = UNSEATED
    for candidate in candidates:
        if candidate.key not in picked and candidate.key not in refused:
            refused[candidate.key] = BELOW_BAR

    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": _config(n, rule, modes, table, floor, natural, twins, group_cap, order),
        "order": {
            "key": "p_ge4" if order is None else "rank_key",
            "of": "the render judge's P(>=4) on the candidate"
            if order is None
            else "a fitted rank key, applied to the ORDER only — every bar, the clearing "
            "rule and the neutral pre-selection still read the judge's own columns",
            "ranked": len(kept) - unranked,
            "unranked": unranked,
            "unranked_are": "sorted last and never refused: no rule acted on them",
        },
        "preselection": preselection,
        "population": {
            "candidates": len(candidates),
            "clearing": len(cleared),
            "after_the_preselection": len(kept),
            "locations": len({c.location for c in candidates}),
            "clearing_locations": len({c.location for c in cleared}),
            "locations_after_the_preselection": len({c.location for c in kept}),
        },
        "filled": len(seats.chosen),
        "unfilled": n - len(seats.chosen),
        "seated": [
            _seated(candidate, why, None if order is None else order.get(candidate.key))
            for candidate, why in seats.chosen
        ],
        "shortfalls": _shortfalls(seats, rule, modes, n, floor),
        "twins": None if twins is None else twins.record(),
        "twin_refusals": dict(sorted(seats.twin_of.items())),
        "rejection": rejection(candidates, refused, log=log),
        "samples": samples(
            candidates, refused, against=_lost_to(seats, preselection, cleared), rank=rank
        ),
    }
    log(
        f"[seat] {record['filled']} of {n} seat(s); "
        f"{record['shortfalls']['modes']['represented']} of "
        f"{record['shortfalls']['modes']['of']} mode(s) represented, "
        f"{record['shortfalls']['modes']['below_the_floor_count']} below a floor of {floor}"
    )
    return record


def _config(
    n: int,
    rule: ceiling.Rule,
    modes: list,
    table: dict,
    floor: int,
    natural: int,
    twins: Twins | None,
    group_cap: str = ceiling.IDENTITY,
    order: dict | None = None,
) -> dict:
    return {
        "n": n,
        "hard": ["one wallpaper per location", "the twin test"],
        "soft": [
            "the palette group cap",
            "the per-cell allowance",
            "the per-family allowance",
            "the mode floors",
        ],
        "order": "the mandated constraints from their own subpools, scarcest first; then "
        "the general pool by score",
        "rules": list(RULES),
        "no_fallback": "nothing is seated by relaxing a rule it failed, and no seat is "
        "padded. Unfilled beats padded",
        "pairwise": (
            "APPLIED, sequentially, as the last of the rules: no candidate is seated "
            f"within {ceiling.TAU} of an already-seated picture in the pixel-cloud metric. "
            "It is not in the solve and the solve's complexity does not change. The other "
            "half of what `diversity` used to mean — are these two the same place — is the "
            "neutral pre-selection at pool construction, recorded under `preselection`"
        )
        if twins is not None
        else "NOT applied: this seating was asked for without the twin test, so it is a "
        "bound on a program without it",
        "bars": {name: block["rule"] for name, block in sorted(table["modes"].items())},
        "ceiling": {
            "k": rule.k,
            "cell_share": ceiling.CELL_SHARE,
            "family_share": ceiling.FAMILY_SHARE,
            "allowance": "floor(k * t * n) + 1",
            "group_cap": rule.group_cap,
            "group_cap_rule": str(group_cap),
            "group_cap_from": "ceiling.GROUP_CAP"
            if str(group_cap) == ceiling.IDENTITY
            else f"max(1, floor({ceiling.GROUP_CAP_RATE} * n))",
            "tau_group": rule.tau_group,
            "targets": dict(sorted(rule.targets.items())),
        },
        "sort_key": "p_ge4" if order is None else "rank_key",
        "mode_floor": floor,
        "mode_floor_rule": f"floor(n / {solve.SEATS_PER_MODE_FLOOR})",
        "mode_floor_natural": natural,
        "mode_floor_artificial": floor != natural,
        "modes": modes,
    }


def _lost_to(seats: Seats, preselection: dict, cleared: list) -> dict:
    """`{candidate key: the picture it lost to}` for the two pairwise refusals.

    Both are keyed by **candidate**, because that is what the rejection ledger and
    the sheet are keyed by — but the two rules do not refuse the same kind of
    thing. The twin test names a seated candidate. The pre-selection names a
    *place*, and every row that place carries went with it, so each of them is
    given the picture the place lost to.
    """
    pictures = {candidate.key: candidate.picture for candidate in cleared}
    at_place: dict = {}
    for candidate in cleared:
        at_place.setdefault(candidate.location, []).append(candidate.key)
    out = {
        key: {
            "picture": pictures.get(found["twin_of"]),
            "pixel_cloud": found["pixel_cloud"],
            "rule": f"twin: under {ceiling.TAU} of a seated picture",
        }
        for key, found in seats.twin_of.items()
    }
    for row in preselection.get("refusals") or []:
        lost = {
            "picture": row["lost_to_picture"],
            "neutral": row["distance"],
            "rule": f"the same place: under {preselection['radius']} in the neutral descriptor",
        }
        for key in at_place.get(row["location"], ()):
            out[key] = lost
    return out


def _seated(candidate, why: str, rank: float | None = None) -> dict:
    """One seat's row. `rank` is the value the seating's own sort key gave it,
    written beside `p_ge4` and never over it: a sheet sorted good-to-bad has to
    sort by the key the seating actually walked, and a reader comparing two
    seatings has to be able to see both numbers."""
    return {
        "key": candidate.key,
        "seated_for": why,
        "rank": None if rank is None else round(float(rank), 6),
        "location": candidate.location,
        "partition": candidate.partition,
        "mode": candidate.mode,
        "kind": candidate.kind,
        "palette_group": candidate.group,
        "cells": list(candidate.cells),
        "families": list(candidate.families),
        "p_ge4": round(candidate.score, 6),
        "p_ge3": round(candidate.p_ge3, 6),
        "picture": candidate.picture,
    }


def _shortfalls(seats: Seats, rule: ceiling.Rule, modes: list, n: int, floor: int) -> dict:
    """Every soft rule's shortfall, recorded rather than repaired.

    The mode block counts two different things and says which is which. `floor`
    is what the policy asked for at this `n`, and below a hundred seats it asks
    for nothing — so `below_the_floor` is empty there and says nothing about the
    gallery. `represented` is how many modes actually took a seat, which is the
    number a reader of a small gallery wants and the one a vacuous floor would
    otherwise have hidden behind an eighteen-of-eighteen.
    """
    missing = [name for name in modes if seats.modes.get(name, 0) < floor]
    return {
        "seats": {"asked": n, "filled": len(seats.chosen), "unfilled": n - len(seats.chosen)},
        "modes": {
            "floor": floor,
            "asked": floor * len(modes),
            "represented": sum(1 for name in modes if seats.modes.get(name, 0)),
            "of": len(modes),
            "below_the_floor": missing,
            "below_the_floor_count": len(missing),
            "counts": dict(sorted(seats.modes.items(), key=lambda item: -item[1])),
        },
        "cells": {
            "held": len(seats.cells),
            "over_allowance": {
                cell: count
                for cell, count in sorted(seats.cells.items())
                if count > rule.allowed(cell, n)
            },
            "counts": dict(sorted(seats.cells.items(), key=lambda item: -item[1])),
        },
        "families": {
            "held": len(seats.families),
            "over_allowance": {
                family: count
                for family, count in sorted(seats.families.items())
                if count > rule.allowed(family, n)
            },
            "counts": dict(sorted(seats.families.items(), key=lambda item: -item[1])),
        },
        "groups": {
            "held": len(seats.groups),
            "cap": rule.group_cap,
            # What the cap ACTUALLY bound to, which is the number the ruling that
            # raised it asked to see rather than assume: a cap of three is only a
            # cap of three if something spent it, and a key that prefers good maps
            # will want to spend its whole allowance on the best of them.
            "realized_max": max(seats.groups.values(), default=0),
            "at_the_cap": sum(1 for count in seats.groups.values() if count >= rule.group_cap),
            "counts": dict(sorted(seats.groups.items(), key=lambda item: (-item[1], item[0]))[:20]),
            "over_cap": {
                group: count
                for group, count in sorted(seats.groups.items())
                if count > rule.group_cap
            },
        },
        "refusals_while_seating": dict(sorted(seats.refusals.items(), key=lambda i: -i[1])),
        "read": "a greedy shortfall is `this walk did not find it`, never `the pool does "
        "not hold it`. The only infeasibility claims are the census's necessary conditions",
    }


# --------------------------------------------------------------------------- #
# The rejection ledger — the product.
# --------------------------------------------------------------------------- #
def rejection(candidates, refused: dict, log=print) -> dict:
    """For every candidate not seated, which rule killed it, aggregated four ways.

    By cell, by family, by mode and by partition, because those are the four axes
    a leg can be aimed down. A cell whose whole refusal column is `cell_allowance`
    is a cell the gallery is already full of; one whose column is `location` is a
    cell that exists only at places something else already took, and the answer to
    those two is not the same answer.

    Aggregated over **distinct locations** as well as rows, for the reason every
    count in this pair of modules is: a rule that refused four hundred rows at
    twelve places refused twelve wallpapers.
    """
    axes = {
        "cells": lambda candidate: candidate.cells,
        "families": lambda candidate: candidate.families,
        "modes": lambda candidate: (candidate.mode,),
        "partitions": lambda candidate: (candidate.partition,),
    }
    rows: dict = {name: {} for name in axes}
    places: dict = {name: {} for name in axes}
    overall: dict = {}
    for candidate in candidates:
        why = refused.get(candidate.key)
        if why is None:
            continue
        overall[why] = overall.get(why, 0) + 1
        for axis, values_of in axes.items():
            for value in values_of(candidate):
                rows[axis].setdefault(value, {}).setdefault(why, 0)
                rows[axis][value][why] += 1
                places[axis].setdefault(value, {}).setdefault(why, set()).add(candidate.location)
    log(f"[seat] {sum(overall.values()):,} candidates refused; {dict(sorted(overall.items()))}")
    return {
        "reasons": dict(sorted(overall.items(), key=lambda item: -item[1])),
        "by": {
            axis: {
                str(value): {
                    "rows": dict(sorted(reasons.items(), key=lambda item: -item[1])),
                    "locations": {
                        why: len(keys)
                        for why, keys in sorted(
                            places[axis][value].items(), key=lambda item: -len(item[1])
                        )
                    },
                }
                for value, reasons in sorted(rows[axis].items())
            }
            for axis in axes
        },
        "read": "the rule that refused each candidate the LAST time it was offered, in "
        f"{list(RULES)} order. `{UNSEATED}` broke no rule and simply arrived after the "
        f"seats ran out; `{BELOW_BAR}` never entered the population at all, and "
        f"`{SAME_PLACE}` was refused at pool construction because another place inside "
        "the neutral pre-selection radius took it",
    }


def samples(
    candidates, refused: dict, count: int = SHOWN, against: dict | None = None, rank=None
) -> dict:
    """`{rule: the strongest few it refused}` — the visual half of the ledger.

    Strongest first inside each rule, because a refusal of a weak candidate says
    nothing: the question a sheet answers is whether the rule is throwing away
    pictures a person would have kept.

    `against` is `{key: what it lost to}` for the two rules where the refusal is
    about a *pair* — the twin test and the pre-selection. A twin refusal shown on
    its own is unreadable: the whole question is whether the picture it was
    refused against is the same wallpaper, and that is a two-picture question.
    """
    rank = _ranking(None) if rank is None else rank
    held: dict = {}
    for candidate in sorted(candidates, key=rank):
        why = refused.get(candidate.key)
        if why is None:
            continue
        mine = held.setdefault(why, [])
        if len(mine) < int(count):
            row = _seated(candidate, why)
            lost_to = (against or {}).get(candidate.key)
            if lost_to is not None:
                row["lost_to"] = lost_to
            mine.append(row)
    return held


# --------------------------------------------------------------------------- #
# Where it lands.
# --------------------------------------------------------------------------- #
def seat_dir(name: str):
    from fractal_wallpapers.paths import under

    return under("curation", UNIT, str(name))


def write_record(name: str, record: dict):
    import json

    path = seat_dir(name) / "seat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _rank_of(row: dict) -> float:
    """The value the seating's own sort key gave one seat.

    `rank` where the seating carried one and `p_ge4` where it did not, which is
    the same number under the incumbent key and the right one under any other.
    """
    held = row.get("rank")
    return float(row.get("p_ge4") or 0.0) if held is None else float(held)


def contact_sheet(name: str, record: dict, rejected=None, output=None):
    """The seated, and a sample of the refused with the rule that refused each.

    Both halves for [`solve.contact_sheet`]'s reason: a gallery on its own says
    only what the rule liked. A refusal captioned with the rule that made it is
    the thing a person can disagree with — and here the captions are the *product*,
    because a column of `cell_allowance` and a column of `location` are two
    different instructions to whatever makes candidates next.
    """
    import html
    from pathlib import Path

    from fractal_wallpapers.curation import sheet as sheet_module
    from fractal_wallpapers.paths import rehome

    output = seat_dir(name) / "contact_sheet.html" if output is None else Path(output)
    config = record["config"]
    shortfalls = record["shortfalls"]
    # Sorted by the seating's OWN key, best first, and never shuffled. A sheet in
    # seating order is in scarcity order for its first seats, which reads as a
    # quality claim it is not making; and a sheet sorted by `p_ge4` under a
    # seating that ranked on something else is a picture of a different walk.
    key_name = str(config.get("sort_key") or "p_ge4")
    ranked_seats = sorted(
        record.get("seated") or [], key=lambda row: (-_rank_of(row), str(row.get("key")))
    )

    def frame(picture) -> str:
        source = None if not picture else Path(rehome(picture))
        return (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )

    def card(row: dict, caption: str) -> str:
        lost_to = row.get("lost_to") or {}
        body = frame(row.get("picture"))
        if lost_to.get("picture"):
            body = (
                f"<div class='pair'><div class='frame'>{body}</div>"
                f"<div class='frame'>{frame(lost_to['picture'])}</div></div>"
            )
        facts = [
            f"mode <b>{html.escape(str(row.get('mode')))}</b>",
            f"P(&ge;4) {row.get('p_ge4')} &middot; P(&ge;3) {row.get('p_ge3')}",
            f"cells {html.escape(', '.join(row.get('cells') or []) or 'none')}",
            f"group {html.escape(str(row.get('palette_group')))}",
            f"partition {html.escape(str(row.get('partition')))}",
        ]
        if lost_to:
            gap = lost_to.get("pixel_cloud", lost_to.get("neutral"))
            facts.append(f"lost to the picture beside it at <b>{gap}</b>")
        return (
            "<figure>"
            + (body if lost_to.get("picture") else f"<div class='frame'>{body}</div>")
            + "<figcaption>"
            f"<b>{html.escape(caption)}</b><ul>"
            + "".join(f"<li>{fact}</li>" for fact in facts)
            + "</ul></figcaption></figure>"
        )

    lines = [
        "<!doctype html><meta charset='utf-8'>",
        f"<title>seat {html.escape(name)}</title>",
        f"<style>{sheet_module.STYLE}"
        ".pair { display: grid; gap: .4rem; grid-template-columns: 1fr 1fr; }"
        "</style>",
        f"<h1>seat {html.escape(name)}</h1>",
        f"<p class='lede'>{record['filled']} of {config['n']} seat(s) filled from "
        f"{record['population'].get('after_the_preselection', record['population']['clearing']):,}"
        f" candidates over "
        f"{record['population'].get('locations_after_the_preselection', 0):,} locations that "
        f"clear their mode's bar and survive the neutral pre-selection. "
        f"{shortfalls['modes']['represented']} of {shortfalls['modes']['of']} modes "
        f"represented, against a floor of {shortfalls['modes']['floor']}. "
        f"Sorted on <b>{html.escape(key_name)}</b>, palette-group cap "
        f"<b>{config['ceiling']['group_cap']}</b> "
        f"({html.escape(str(config['ceiling'].get('group_cap_rule', 'identity')))}). "
        "A greedy: fill by scarcity, then by the key. Nothing here is optimal and a "
        "shortfall is not infeasibility.</p>",
        f"<h2>Seated ({record['filled']}), best first by <code>{html.escape(key_name)}</code></h2>",
        "<div class='grid'>"
        + "".join(
            card(row, f"{at}. {key_name} {_rank_of(row):.4f} — {row['seated_for']}")
            for at, row in enumerate(ranked_seats, start=1)
        )
        + "</div>",
    ]
    for why, sample in sorted((rejected or {}).items()):
        if not sample:
            continue
        lines += [
            f"<h2>Refused by <code>{html.escape(why)}</code> ({len(sample)} shown)</h2>",
            "<div class='grid'>" + "".join(card(row, why) for row in sample) + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


__all__ = [
    "BELOW_BAR",
    "RULES",
    "SAME_PLACE",
    "SCHEMA",
    "SHOWN",
    "SIGNATURE_CACHE",
    "TWIN_NEIGHBOURS",
    "UNIT",
    "UNSEATED",
    "SeatingRefused",
    "Seats",
    "Twins",
    "clouds_for",
    "contact_sheet",
    "lens_for",
    "rejection",
    "samples",
    "scarcity",
    "seat",
    "seat_dir",
    "write_record",
]
