"""Seat a gallery off the ledger with a trivial greedy, and keep every refusal.

The other half of [`curation.headroom`]. A census is an upper bound — it says what
could not possibly be seated. This is a **lower bound**: the simplest rule that
fills seats, run so that the gap between the two is visible. Close together and
the answer is known; far apart and that gap is the size of the prize an exact
solve is competing for, which is usually the signal to go and make more candidates
instead.

It only chooses. It proposes nothing and renders nothing: every reading about a
candidate — the colour, the palette group, the mode, the score — is already on the
ledger row, so the colour a rule reads is a **lookup** and never a second
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

**The floors are per mode and they are the default.**
[`curation.mode_policy.seat_floors`] is what an unflagged seating asks for: half
each accepted strange mode's share of the strange seat budget, which at `n = 150`
is 45 of the 150 seats mandated across thirteen modes rather than the 14 the flat
floor asked for. Diversity is the design rather than a knob, so the rule is on
unless a seating turns it off, and `--flat-floor` is how — it puts back
[`solve.mode_floor`]'s `floor(n / 100)`, one number for every mode, which is what
every gallery seated before 2026-08-31 was seated under. `--mode-floor` still puts
an artificial flat floor back for a debug gallery, and the record names which of
the three it was.

This leg is therefore doing something at every `n` the flat floor was silent at:
at twenty seats the rule asks for twelve strange seats and floors six of them,
where `floor(n / 100)` asked for nothing at all.

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
    mode_policy,
    solve,
)

#: The schema every record this module writes carries.
#:
#: **2**: the twin rule joined [`RULES`], the mode floor became a function of `n`
#: rather than a constant, and the mode block counts representation separately
#: from the floor. A schema 1 record was taken under a flat floor of one and no
#: pairwise rule at all, and the two are not comparable seatings.
#:
#: **3**: [`attribution`] joined the record — every seat's rank percentile inside
#: the clearing pool and the leg that placed it — and the release leg's own block
#: lands under `render`. The seatings either side of the bump are comparable: what
#: moved is what is *written down*, not what the walk did. The two defaults flipped
#: at the same commit and that is **not** what the bump is for — `config` has named
#: the cap and the key since schema 2, so a reader compares those and never a date.
SCHEMA = 3

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

#: The render judge's fourth cutpoint alone, which is what every gallery this
#: project shipped before 2026-08-28 was ordered by. Still reachable by name.
JUDGE_KEY = "p_ge4"

#: [`curation.rank_key`]'s fitted five-column form — the location head, both judge
#: cutpoints, the calibration stratum and the flatness column.
RANK_KEY = "rank-key"

#: The keys a caller may name.
KEYS = (RANK_KEY, JUDGE_KEY)

#: **The sort key a seating walks unasked**, since 2026-08-28: the fitted one.
#:
#: Matt's, off the contact sheets — the four-arm before/after at `n = 150` put the
#: fitted order beside the judge alone on one pool and he accepted it by eye. It
#: is an acceptance and not a measurement, and the record says which key a seating
#: ran under either way, so a later reading can be taken against the incumbent
#: without re-deciding anything.
#:
#: It moves the **order** and nothing else. Every bar, the clearing rule and the
#: neutral pre-selection still read the judge's own columns.
DEFAULT_KEY = RANK_KEY

#: **The palette-group cap rule a seating runs under unasked**, since 2026-08-28:
#: the proportional one, `max(1, floor(GROUP_CAP_RATE * n))`.
#:
#: The ckpt-88 ruling. [`ceiling.IDENTITY`] — one seat a map — is still the
#: constant [`ceiling.GROUP_CAP`] and is still what a caller gets by naming it;
#: what moved is which of the two an unflagged seating applies. Below
#: `1 / ceiling.GROUP_CAP_RATE` seats the two rules produce the same cap, so a
#: debug gallery at n=20 is unaffected by the flip.
DEFAULT_GROUP_CAP = ceiling.PROPORTIONAL

#: How many of the seats the bottom-quartile attribution block is cut at. A
#: quarter, of the seats and never of the pool: the question it answers is "which
#: legs are placing the weakest wallpapers this gallery ships".
BOTTOM_QUARTILE = 0.25


class SeatingRefused(RuntimeError):
    """The seating cannot be run."""


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

    def __init__(self, rule: ceiling.Rule, n: int, floor=0, twins: Twins | None = None):
        self.rule = rule
        self.n = int(n)
        #: `{mode: how many seats its floor asks for}`, at this `n`. A number is
        #: the same floor for every mode, which is what every caller passes today.
        self.floors: dict = dict(floor) if isinstance(floor, dict) else {}
        #: The largest floor any mode asked for. The three soft tests do not read
        #: it; [`seat`]'s scarcity leg reads [`floors`] per mode.
        self.floor = max(self.floors.values(), default=0) if self.floors else int(floor)
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


def ranking_for(candidates, key: str = DEFAULT_KEY, log=print) -> tuple[dict | None, dict | None]:
    """`(the order a seating walks, what the key could read)` for one pool.

    `(None, None)` on [`JUDGE_KEY`], where the order is the candidate's own
    `P(>=4)` and there is nothing to resolve. On [`RANK_KEY`] it is
    [`rank_key.order_for`]'s mapping and its coverage record, and resolving it
    reads two stores — the flatness sidecar and the location readings — so this is
    the one place a seating pays for its key and it is paid once per pool.

    Named apart from [`seat`] because [`seat`] is arithmetic over candidates it is
    handed and this is I/O. A caller with an order already in hand passes it
    straight to `seat(order=...)` and never reaches here.
    """
    named = str(key)
    if named == JUDGE_KEY:
        return None, None
    if named != RANK_KEY:
        raise SeatingRefused(f"the sort key is one of {KEYS}, not {key!r}")
    from fractal_wallpapers.curation import rank_key

    return rank_key.order_for(candidates, log=log)


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


def floors_for(floor, modes) -> dict:
    """`{mode: its floor}` over `modes`, from either a number or a mapping.

    A number is the same floor for every accepted mode, which is the shape every
    caller passes today and the shape [`solve.mode_floor`] returns. A mapping is
    per mode — what [`curation.mode_policy.seat_floors`] builds — and a mode it
    does not name asks for nothing rather than inheriting a default, because a
    floor rule that silently floors a mode it never mentioned is not a rule
    anybody can read off its own table.
    """
    if isinstance(floor, dict):
        return {name: max(0, int(floor.get(name, 0))) for name in modes}
    return dict.fromkeys(modes, max(0, int(floor)))


def scarcity(kept, modes, rank=None) -> list:
    """The mandated constraints, scarcest first. `[(mode, its subpool)]`.

    The only mandate the **default** target vector produces is the mode floor:
    every accepted mode wants [`solve.mode_floor`] seats and no colour cell is
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
    floor: int | dict | None = None,
    radius: float | None = distinct.PRESELECT_RADIUS,
    twin: bool = True,
    group_cap: str = DEFAULT_GROUP_CAP,
    key: str = DEFAULT_KEY,
    order: dict | None = None,
    coverage: dict | None = None,
    allow_unranked: bool = False,
    log=print,
) -> dict:
    """Fill `n` seats by scarcity then by the rank key, and keep every refusal.

    Pool construction first: the bars, then the neutral pre-selection at `radius`
    — `None` for no pre-selection at all, which is what a caller comparing against
    a schema 1 record wants. Then two legs over one [`Seats`]. The first walks the
    mandated constraints in scarcity order and takes each one's best candidates
    that nothing refuses, **down its subpool until the floor is met or the subpool
    is spent**; the second walks whatever is left of the ranked pool. A candidate
    refused in the first leg is offered again in the second, because the state it
    was refused against has moved on.

    `floor` **replaces the default rule**, which is
    [`curation.mode_policy.seat_floors`] — half each accepted strange mode's share
    of the strange seat budget, per mode. Unset is that rule, and a gallery seated
    here is seated under it. A **mapping** is one floor per mode, some other
    caller's; a **number** is the same floor for every accepted mode, which is
    both the flat `solve.mode_floor(n)` the rule replaced (`--flat-floor`, the way
    off) and the artificial floor a debug gallery uses to exercise the scarcity
    leg at a size where the flat one asks for nothing. The record says which of
    the three it was.

    ## The two decisions, both flipped on 2026-08-28, both still reachable

    `group_cap` names the rule the palette-group cap runs under —
    [`ceiling.PROPORTIONAL`], `max(1, floor(0.025 n))`, which is
    [`DEFAULT_GROUP_CAP`], or [`ceiling.IDENTITY`], one seat a group, which is
    what every gallery before that date was seated under. `key` names the sort key
    the pool is walked in — [`RANK_KEY`], which is [`DEFAULT_KEY`], or
    [`JUDGE_KEY`], the render judge's `P(>=4)` alone.

    `order` is the resolved `{candidate key: rank value}` and **overrides `key`**:
    a caller that already holds the mapping — a sweep seating one pool four ways —
    passes it and never pays [`ranking_for`]'s two store reads again. `coverage`
    is what that resolution reported, carried onto the record beside it.

    **Neither decision touches the pool**: the bars, the clearing rule and the
    neutral pre-selection all read the judge's own columns, so two seatings
    differing in one of them differ in the sort order and in the cap and in
    nothing else, which is what makes a before/after exact.

    A candidate `order` has no value for is ranked **last** and counted. It is not
    refused — no rule acted on it — and it has not earned a place ahead of the
    rows the key could read.

    ## An unreadable clearing pool is a refusal, not a seating

    Sorting last is the right *order* and the wrong thing to be quiet about. A leg
    that merged without a flatness sweep left every row it wrote unreadable by
    [`RANK_KEY`], and rows that sort last behind a full pool cannot win a seat at
    all: `mine1h` merged 8,192 rows, cleared 1,326 of them into the pool, and
    seated **none**, with nothing in the output saying so. So a clearing candidate
    the active key cannot read raises [`SeatingRefused`] naming the count and the
    command that fills the gap.

    `allow_unranked` is the way past it and exists for one case: a picture that is
    on disk and will not decode has no reading and never will, so a pool holding
    one would otherwise be unseatable forever. It is not the flag for "the sweep
    has not been run" — that is the refusal doing its job.
    """
    if order is None and str(key) != JUDGE_KEY:
        order, coverage = ranking_for(candidates, key, log=log)
    # The accepted roster, not the engine's production one: a mode
    # [`curation.mode_policy`] weights 0 has no rows in [`solve.pool`] at all, so a
    # floor over it would be a mandate nothing could meet and an `unmet` row that
    # is a policy decision wearing the shape of a shortfall.
    modes = mode_policy.accepted()
    cap = ceiling.group_cap(n, group_cap)
    if rule is None:
        rule = solve.rule_for()
        rule.group_cap = cap
    # The DEFAULT is the per-mode rule. `floor` replaces it: a mapping is one
    # floor per mode, a number is the same floor for every accepted mode — which
    # is how `--flat-floor` asks for the flat `solve.mode_floor(n)` the rule
    # replaced.
    natural = mode_policy.seat_floors(n)
    asked = natural if floor is None else floor
    floors = floors_for(asked, modes)
    #: The uniform floor, where the caller passed one. `None` says it was per mode.
    floor = None if isinstance(asked, dict) else int(asked)
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
    if order is not None:
        blind = [c for c in cleared if c.key not in order]
        if blind and not allow_unranked:
            raise SeatingRefused(
                f"{len(blind):,} of {len(cleared):,} clearing candidate(s) carry no "
                f"{key!r} value, so they sort last and cannot win a seat while a readable "
                "row is left — which is a seating that silently ignores them rather than "
                "one that refuses them. The usual cause is a leg merged before its "
                "pictures were swept: run `fractal-wallpapers curate flatness sweep`, "
                "then seat again. Pass allow_unranked=True (`--allow-unranked`) only for "
                "a picture that is on disk and will not decode, which has no reading to "
                f"take. First few: {[c.key for c in blind[:3]]}"
            )
        if blind:
            log(
                f"[seat] {len(blind):,} clearing candidate(s) are unreadable by {key!r} and "
                "were allowed through: they sort last and no rule acts on them"
            )
    unranked = 0 if order is None else sum(1 for c in kept if c.key not in order)
    kept.sort(key=rank)
    twins = Twins(clouds_for(kept)) if twin else None
    seats = Seats(rule, n, floor=floors, twins=twins)

    mandated = scarcity(kept, modes, rank=rank)
    picked: set = set()
    for mode, members in mandated:
        if seats.full:
            break
        # Keep taking from this mode's subpool until its floor is met or the
        # subpool is spent. [`scarcity`] yields **one** entry per mode, so a leg
        # that stopped at its first success would cap every mode at one seat and
        # quietly turn a floor of two into a floor of one — a greedy that
        # disagreed with the exact solver on the same program, in the direction
        # of seating less of the roster than was asked for.
        for candidate in members:
            if seats.full or seats.modes.get(mode, 0) >= floors.get(mode, 0):
                break
            why = seats.refuses(candidate)
            if why is None:
                seats.seat(candidate, f"mode_floor:{mode}")
                picked.add(candidate.key)
                refused.pop(candidate.key, None)
            else:
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

    seated_rows = [
        _seated(candidate, why, None if order is None else order.get(candidate.key))
        for candidate, why in seats.chosen
    ]
    placement = attribution(seated_rows, cleared, order, seats, rule, modes, n, floors)
    record = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": _config(n, rule, modes, table, floor, floors, natural, twins, group_cap, order),
        "order": {
            "key": "p_ge4" if order is None else "rank_key",
            "of": "the render judge's P(>=4) on the candidate"
            if order is None
            else "a fitted rank key, applied to the ORDER only — every bar, the clearing "
            "rule and the neutral pre-selection still read the judge's own columns",
            "ranked": len(kept) - unranked,
            "unranked": unranked,
            "unranked_are": "sorted last and never refused: no rule acted on them",
            "unranked_allowed": bool(allow_unranked),
            "coverage": coverage,
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
        "seated": seated_rows,
        "attribution": placement,
        "shortfalls": _shortfalls(seats, rule, modes, n, floors, cleared, refused),
        "twins": None if twins is None else twins.record(),
        "twin_refusals": dict(sorted(seats.twin_of.items())),
        "rejection": rejection(candidates, refused, log=log),
        "samples": samples(
            candidates, refused, against=_lost_to(seats, preselection, cleared), rank=rank
        ),
    }
    block = record["shortfalls"]["modes"]
    log(
        f"[seat] {record['filled']} of {n} seat(s); "
        f"{block['represented']} of {block['of']} mode(s) represented, "
        f"{block['below_the_floor_count']} below a floor "
        f"{'of ' + str(floor) if floor is not None else 'set per mode'}"
    )
    return record


def _config(
    n: int,
    rule: ceiling.Rule,
    modes: list,
    table: dict,
    floor: int | None,
    floors: dict,
    natural: dict,
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
        # The uniform floor, or `None` where the floors are per mode — which is
        # what the default rule builds. Both shapes are always in `mode_floors`,
        # which is what a reader should take.
        "mode_floor": floor,
        "mode_floors": dict(floors),
        "mode_floor_rule": floor_rule(n, floor, floors, natural, modes),
        # What nobody naming a floor would have got: the default rule's answer.
        "mode_floor_natural": floors_for(natural, modes),
        "mode_floor_artificial": dict(floors) != floors_for(natural, modes),
        "modes": modes,
        "mode_policy": mode_policy.record(),
    }


def floor_rule(n: int, floor: int | None, floors: dict, natural: dict, modes: list) -> str:
    """One sentence naming the rule the floors in this record came from.

    Three answers and they are not interchangeable: the **default**, the **flat**
    floor the default replaced — which is the one `--flat-floor` asks for and the
    one every gallery before this flip was seated under — and a floor some caller
    made up. A record that said `floor(n / 100)` for all three, which this said
    while the flat floor was the default, is a record that cannot tell a
    measurement apart from its own baseline.

    Public because [`curation.headroom`] writes the same sentence into its census
    block, and the census naming the floors one way while the seating names them
    another is the confusion this sentence exists to end. It is called from there
    rather than copied: `headroom` cannot import this module at the top (this one
    imports it), so the call is deferred inside the census.
    """
    if dict(floors) == floors_for(natural, modes):
        return (
            "the per-mode floor rule, curation.mode_policy.seat_floors(n): half each "
            "accepted strange mode's share of the strange seat budget, summing to half "
            "of it. THE DEFAULT — a seating that named no floor was seated under this"
        )
    if floor is None:
        return "set per mode by the caller"
    if floor == solve.mode_floor(n):
        return (
            f"the FLAT floor, floor(n / {solve.SEATS_PER_MODE_FLOOR}) = {floor} for every "
            "accepted mode. It was the default until the per-mode rule replaced it, and "
            "it is what `--flat-floor` asks for"
        )
    return f"an artificial flat {floor} for every accepted mode"


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


def _per_mode(seats: Seats, modes: list, floors: dict, cleared: list, refused: dict) -> dict:
    """`{mode: what its floor asked for and what it got}` — the floor, seat by seat.

    Three facts per mode, because a mode short of its floor is short for one of
    two unrelated reasons and a single list conflates them. `clearing` is how many
    of that mode's candidates cleared their bar at all, and `refused_by` is which
    rules acted on the ones that were not seated — so a mode the **ceiling** beat
    reads apart from a mode the **pool** never held. The ceiling winning is the
    designed outcome, not a fault: a bar outranks a guarantee, and an unfilled
    floor beats a padded gallery.
    """
    supply: dict = {}
    for candidate in cleared:
        if candidate.mode in floors:
            supply[candidate.mode] = supply.get(candidate.mode, 0) + 1
    acted: dict = {}
    for candidate in cleared:
        why = refused.get(candidate.key)
        if why is not None and candidate.mode in floors:
            acted.setdefault(candidate.mode, {})
            acted[candidate.mode][why] = acted[candidate.mode].get(why, 0) + 1
    out: dict = {}
    for name in modes:
        asked = int(floors.get(name, 0))
        held = int(seats.modes.get(name, 0))
        out[name] = {
            "floor": asked,
            "seated": held,
            "short": max(0, asked - held),
            "clearing": supply.get(name, 0),
            "refused_by": dict(sorted(acted.get(name, {}).items(), key=lambda item: -item[1])),
        }
    return out


def _shortfalls(
    seats: Seats,
    rule: ceiling.Rule,
    modes: list,
    n: int,
    floors: dict,
    cleared: list,
    refused: dict,
) -> dict:
    """Every soft rule's shortfall, recorded rather than repaired.

    The mode block counts things that are not the same thing and says which is
    which. `floors` is what the policy asked of each mode at this `n`, and below a
    hundred seats it asks for nothing — so `starved` is empty there and says
    nothing about the gallery, while every mode is in `floor_never_needed`
    instead. `represented` is how many modes actually took a seat, which is the
    number a reader of a small gallery wants and the one a vacuous floor would
    otherwise have hidden behind a fourteen-of-fourteen.

    **A mode nobody asked for is not a mode that went short.** `starved` is a
    floor above zero that went unfilled; `floor_never_needed` is a floor of zero,
    which no gallery can fail. Conflating them is how a floor rule reads as
    working when it is switched off — and how a real starvation hides inside a
    list most of whose entries were never at risk.
    """
    per_mode = _per_mode(seats, modes, floors, cleared, refused)
    starved = [name for name in modes if per_mode[name]["short"] > 0]
    never = [name for name in modes if per_mode[name]["floor"] == 0]
    # One number where every mode asked for the same thing — which since the
    # per-mode rule became the default is only a seating that asked for the flat
    # floor — and `None` where they did not, so a reader of `floor` is never
    # handed one mode's figure as if it were the gallery's.
    asked = {per_mode[name]["floor"] for name in modes}
    uniform = next(iter(asked)) if len(asked) == 1 else None
    return {
        "seats": {"asked": n, "filled": len(seats.chosen), "unfilled": n - len(seats.chosen)},
        "modes": {
            "floor": uniform,
            "floors": {name: per_mode[name]["floor"] for name in modes},
            "floors_are": "one floor for every mode" if uniform is not None else "per mode",
            "asked": sum(per_mode[name]["floor"] for name in modes),
            "represented": sum(1 for name in modes if seats.modes.get(name, 0)),
            "of": len(modes),
            "per_mode": per_mode,
            "starved": starved,
            "starved_count": len(starved),
            "starved_are": "a floor above zero that went unfilled. Read `per_mode` for "
            "which: a mode with `clearing` above `seated` lost its seats to a rule named "
            "in `refused_by`, and one with `clearing` at `seated` had nothing left to seat",
            "floor_never_needed": never,
            "floor_never_needed_count": len(never),
            "floor_never_needed_are": "asked for nothing, so they cannot have gone short",
            "below_the_floor": starved,
            "below_the_floor_count": len(starved),
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
# The leg attribution — where each seat came from, and how strong it was.
# --------------------------------------------------------------------------- #
#: The two legs [`seat`] fills from, spelled as the walk itself spells them.
#:
#: There is no third. A "cell fill" leg does not exist: the cell allowance is a
#: ceiling applied *inside* the ranked walk and never a stage that places a seat,
#: and naming it here would put a leg on the record that no code implements.
LEGS = {
    "mode_floor": "the scarcity leg: each mandated mode from its own subpool, scarcest "
    "first, taking that mode's best candidate nothing refuses",
    "general_pool": "the ranked walk down whatever the scarcity leg left, in the "
    "seating's own sort key, with every soft ceiling applied as it goes",
}


def leg_of(seated_for: str) -> str:
    """Which of [`LEGS`] placed a seat, off the `seated_for` the walk stamped."""
    return "mode_floor" if str(seated_for).startswith("mode_floor:") else "general_pool"


def _value_of(candidate, order: dict | None):
    """One candidate's value under the seating's own key, or `None` if it has none."""
    if order is None:
        return float(candidate.score)
    held = order.get(candidate.key)
    return None if held is None else float(held)


def _percentiles(cleared, order: dict | None):
    """`(value -> percentile, readable, unreadable)` over the clearing pool.

    A candidate the key could not read sorts **last** in the walk, so it counts as
    below every readable row here too — anything else would quietly inflate every
    percentile by the size of the hole.
    """
    import bisect

    values = sorted(value for value in (_value_of(c, order) for c in cleared) if value is not None)
    unreadable = len(cleared) - len(values)
    total = max(1, len(cleared))

    def of(value) -> float:
        if value is None:
            return 0.0
        return round(100.0 * (unreadable + bisect.bisect_left(values, float(value))) / total, 2)

    return of, len(values), unreadable


def _spread(values) -> dict:
    held = sorted(values)
    if not held:
        return {"seats": 0, "min": None, "median": None, "max": None}
    return {"seats": len(held), "min": held[0], "median": held[len(held) // 2], "max": held[-1]}


def attribution(seated, cleared, order, seats, rule, modes, n: int, floors: dict) -> dict:
    """Where every seat came from and how strong it was. **Mutates `seated`.**

    Three questions, and together they are the mining list rather than a summary
    of one:

    * for each seat, its **rank percentile inside the clearing pool** and which of
      [`LEGS`] placed it — so a leg spending seats on the tail is visible as a leg
      rather than as a handful of weak pictures;
    * which legs hold the bottom [`BOTTOM_QUARTILE`] of the seats by that
      percentile;
    * per mode and per cell, **how strong the best candidate the pool could
      offer was** — because a cell whose best available row sits at the fortieth
      percentile is a cell to go and make candidates for, and a cell merely at its
      allowance is a cell the gallery is already full of. Those are two different
      instructions and they are reported apart, in `best_available` and
      `binding`.

    The percentile is against the **clearing pool** and not the pre-selected one:
    the pre-selection refuses places, so a percentile against what survived it
    would be measured against a population no mine can aim at.
    """
    percentile_of, readable, unreadable = _percentiles(cleared, order)
    for row in seated:
        row["leg"] = leg_of(row["seated_for"])
        row["rank_percentile"] = percentile_of(_rank_of(row))

    by_leg: dict = {}
    for row in seated:
        by_leg.setdefault(row["leg"], []).append(row["rank_percentile"])
    cut = max(1, int(round(BOTTOM_QUARTILE * len(seated)))) if seated else 0
    weakest = sorted(seated, key=lambda row: (row["rank_percentile"], row["key"]))[:cut]

    def tally(rows, values_of) -> dict:
        out: dict = {}
        for row in rows:
            for value in values_of(row):
                out[str(value)] = out.get(str(value), 0) + 1
        return dict(sorted(out.items(), key=lambda item: -item[1]))

    return {
        "percentile_of": "the seat's own rank value against every candidate that cleared "
        "its mode's bar, before the neutral pre-selection",
        "clearing_pool": {
            "candidates": len(cleared),
            "readable_by_the_key": readable,
            "unreadable_by_the_key": unreadable,
            "unreadable_sit_at": "the bottom, which is where the walk sorts them",
        },
        "legs": LEGS,
        "by_leg": {name: _spread(values) for name, values in sorted(by_leg.items())},
        "by_seated_for": tally(seated, lambda row: (row["seated_for"],)),
        "bottom_quartile": {
            "share": BOTTOM_QUARTILE,
            "seat_count": len(weakest),
            "percentile_at_or_below": weakest[-1]["rank_percentile"] if weakest else None,
            "by_leg": tally(weakest, lambda row: (row["leg"],)),
            "by_seated_for": tally(weakest, lambda row: (row["seated_for"],)),
            "by_mode": tally(weakest, lambda row: (row["mode"],)),
            "by_cell": tally(weakest, lambda row: row["cells"]),
            "seats": [
                {
                    "key": row["key"],
                    "rank_percentile": row["rank_percentile"],
                    "leg": row["leg"],
                    "seated_for": row["seated_for"],
                    "mode": row["mode"],
                    "cells": row["cells"],
                    "p_ge4": row["p_ge4"],
                }
                for row in weakest
            ],
        },
        "best_available": _best_available(cleared, order, percentile_of, seats),
        "unmet": _unmet(seats, modes, n, floors),
        "binding": _binding(seats, rule, n),
    }


def _best_available(cleared, order, percentile_of, seats: Seats) -> dict:
    """Per mode and per cell, how strong the pool's **best** candidate was. Weakest first.

    The whole of the "go and make more of this" list. A mode or a cell whose best
    available candidate sits low in the clearing pool is one where the gallery had
    nothing good to seat, whatever it seated; ranked by how weak, so the list has
    an order somebody can work down.
    """
    axes = {"modes": lambda held: (held.mode,), "cells": lambda held: held.cells}
    out: dict = {}
    for axis, values_of in axes.items():
        best: dict = {}
        for candidate in cleared:
            value = _value_of(candidate, order)
            for name in values_of(candidate):
                held = best.setdefault(
                    str(name), {"rows": 0, "locations": set(), "best": None, "key": None}
                )
                held["rows"] += 1
                held["locations"].add(candidate.location)
                if value is not None and (held["best"] is None or value > held["best"]):
                    held["best"], held["key"] = value, candidate.key
        rows = [
            {
                "name": name,
                "cleared_rows": held["rows"],
                "cleared_locations": len(held["locations"]),
                "best_rank": None if held["best"] is None else round(held["best"], 6),
                "best_percentile": percentile_of(held["best"]),
                "best_candidate": held["key"],
                "seated": (seats.modes if axis == "modes" else seats.cells).get(name, 0),
            }
            for name, held in best.items()
        ]
        out[axis] = sorted(rows, key=lambda row: (row["best_percentile"], row["name"]))
    return out


def _unmet(seats: Seats, modes, n: int, floors: dict) -> list:
    """Every constraint the seating asked for and did not get, and how far short.

    Only the two that **can** go unmet. The cell and family allowances and the
    palette-group cap are ceilings: a seating cannot fall short of one, it can only
    bind against it, and that is [`_binding`] and a different instruction.
    """
    short = [
        {
            "constraint": "seats",
            "asked": int(n),
            "held": len(seats.chosen),
            "short": int(n) - len(seats.chosen),
        }
    ]
    for name in modes:
        held = seats.modes.get(name, 0)
        asked = int(floors.get(name, 0))
        if held < asked:
            short.append(
                {
                    "constraint": f"mode_floor:{name}",
                    "asked": asked,
                    "held": held,
                    "short": asked - held,
                }
            )
    return [row for row in short if row["short"] > 0]


def _binding(seats: Seats, rule: ceiling.Rule, n: int) -> dict:
    """Every ceiling that was actually spent to its last seat. Not a shortfall.

    A cell at its allowance means the gallery is already as full of that colour as
    the ceiling permits, so more candidates there buy nothing; a cell whose best
    available row is weak is the opposite instruction. Both lists exist so that a
    mine is not aimed at the first one.
    """
    return {
        "cells_at_the_allowance": {
            cell: count
            for cell, count in sorted(seats.cells.items(), key=lambda item: -item[1])
            if count >= rule.allowed(cell, n)
        },
        "families_at_the_allowance": {
            family: count
            for family, count in sorted(seats.families.items(), key=lambda item: -item[1])
            if count >= rule.allowed(family, n)
        },
        "groups_at_the_cap": {
            group: count
            for group, count in sorted(seats.groups.items(), key=lambda item: (-item[1], item[0]))
            if count >= rule.group_cap
        },
        "read": "a ceiling spent to its last seat, which is the OPPOSITE instruction to a "
        "weak `best_available` row: more candidates here cannot be seated",
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


def release_seats(name: str, record: dict, workers=None, regime=None, timeout=None, log=print):
    """Render every seat of this seating at release geometry. Mutates `record`.

    [`solve.render_seats`] with this seating's own directory, and deliberately not
    a second copy of it: a seat row and a solve's seat row carry the same fields,
    and two legs would be two places for the geometry, the autolevel stamp and the
    resume rule to drift apart.

    **No bar acts here and none is invented here.** The leg renders every seat the
    walk chose, records what each one cost, and refuses nothing. The rule that a
    shortlist should be re-scored at shipping geometry and floored on *that*
    reading is not implemented anywhere in this project, and this is not the place
    to improvise one: a floor is a ruling.
    """
    from fractal_wallpapers.curation import solve

    return solve.render_seats(
        name,
        record,
        workers=workers,
        regime=regime,
        where=seat_dir(name) / "release",
        timeout=solve.ROW_BACKSTOP if timeout is None else timeout,
        log=log,
    )


def autolevel_rate(record: dict) -> dict:
    """The release leg's autolevel act rate **with its denominator**.

    Three numbers and not one, because the operator has three outcomes and a bare
    percentage hides two of them. A seat gets a stamp when the operator was asked;
    `acted` is the subset where the curve was not the identity. A seat with no
    stamp at all was **never asked** — its mode is a direct-trap kind, which
    [`autolevel.applies_to`] answers no for at the one place that decides — and it
    belongs in neither the numerator nor the denominator.
    """
    seated = record.get("seated") or []
    stamped = [row for row in seated if row.get("release_autolevel")]
    acted = [row for row in stamped if (row.get("release_autolevel") or {}).get("acted")]
    return {
        "seats": len(seated),
        "asked": len(stamped),
        "acted": len(acted),
        "rate": None if not stamped else round(len(acted) / len(stamped), 4),
        "not_asked": len(seated) - len(stamped),
        "denominator": "the seats the operator was ASKED about — a stamp on the release "
        "render. A seat whose mode is a direct-trap kind is never asked and is in "
        "neither half",
    }


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
        # `rehome` answers None for a name with no artifacts component, and a
        # release picture written outside the tree is exactly that. Keep the name
        # the record carried rather than crashing on it.
        source = None if not picture else (rehome(picture) or Path(picture))
        return (
            f'<img src="{sheet_module.thumbnail(source)}" alt="">'
            if source is not None and source.is_file()
            else '<div class="missing">no picture on disk</div>'
        )

    def shown(row: dict) -> str:
        """The release render where the leg made one, the candidate otherwise.

        A sheet of a *released* gallery has to show the pictures that were
        released: the candidate is 640x360 through the unmodified map and the
        release render is the shipping geometry with the autolevel operator inside
        it, so the two are different pictures of one recipe. Which one a card is
        showing is on the card, because a page that showed one and captioned the
        other would say something false with every field on it true.
        """
        return frame(row.get("release_picture") or row.get("picture"))

    def card(row: dict, caption: str, seat: bool = False) -> str:
        lost_to = row.get("lost_to") or {}
        body = shown(row)
        if lost_to.get("picture"):
            body = (
                f"<div class='pair'><div class='frame'>{body}</div>"
                f"<div class='frame'>{frame(lost_to['picture'])}</div></div>"
            )
        released = row.get("release_picture")
        geometry = row.get("release_geometry") or {}
        facts = [
            f"mode <b>{html.escape(str(row.get('mode')))}</b>",
            f"P(&ge;4) {row.get('p_ge4')} &middot; P(&ge;3) {row.get('p_ge3')}",
            f"cells {html.escape(', '.join(row.get('cells') or []) or 'none')}",
            f"group {html.escape(str(row.get('palette_group')))}",
            f"partition {html.escape(str(row.get('partition')))}",
        ]
        if row.get("rank_percentile") is not None:
            facts.append(
                f"pool percentile <b>{row['rank_percentile']}</b> &middot; leg "
                f"{html.escape(str(row.get('leg')))}"
            )
        if released:
            frame_at = "x".join(str(at) for at in (geometry.get("resolution") or []))
            facts.append(
                f"shown at <b>{html.escape(frame_at)}ss{geometry.get('supersample')}</b> "
                f"&middot; {sheet_module.autolevel_line(row.get('release_autolevel'))}"
            )
        elif seat:
            # Only a SEAT can be missing a release picture; a refused candidate was
            # never going to have one, and saying so on every refusal card would be
            # noise that reads as a fault.
            facts.append("shown as the <b>candidate</b> render: this seat has no release picture")
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
        f"represented, against a floor of {shortfalls['modes']['floor']}"
        f"{'' if shortfalls['modes']['floor'] is not None else ' set per mode'}. "
        f"Sorted on <b>{html.escape(key_name)}</b>, palette-group cap "
        f"<b>{config['ceiling']['group_cap']}</b> "
        f"({html.escape(str(config['ceiling'].get('group_cap_rule', 'identity')))}). "
        "A greedy: fill by scarcity, then by the key. Nothing here is optimal and a "
        "shortfall is not infeasibility.</p>",
        f"<h2>Seated ({record['filled']}), best first by <code>{html.escape(key_name)}</code></h2>",
        "<div class='grid'>"
        + "".join(
            card(row, f"{at}. {key_name} {_rank_of(row):.4f} — {row['seated_for']}", seat=True)
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
    "BOTTOM_QUARTILE",
    "DEFAULT_GROUP_CAP",
    "DEFAULT_KEY",
    "JUDGE_KEY",
    "KEYS",
    "LEGS",
    "RANK_KEY",
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
    "attribution",
    "autolevel_rate",
    "clouds_for",
    "contact_sheet",
    "floor_rule",
    "floors_for",
    "leg_of",
    "ranking_for",
    "rejection",
    "release_seats",
    "samples",
    "scarcity",
    "seat",
    "seat_dir",
    "write_record",
]
