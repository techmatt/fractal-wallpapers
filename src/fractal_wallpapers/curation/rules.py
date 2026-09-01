"""One spelling per selection rule: a set-level predicate over incremental state.

The rules a gallery is chosen under used to exist twice. `curation.seating`
walked a ranked list and asked each candidate against the seats already taken;
[`curation.solve`] stated the same intentions as constraint rows and handed them
to a solver. Most of them agreed. Two did not — the palette-group cap was a
*count* in one and a *distance* in the other, and the two legs did not even
choose from the same pool — and a divergence like that is not one anybody finds
by reading either file on its own.

So there is one statement of each rule and it lives here. Every rule answers the
same two questions about a **set** rather than about a prefix of a walk:

* [`State.requirements`] — what would have to leave the seated set before this
  candidate could join it;
* and therefore [`State.admits`], which is that with nothing leaving.

A greedy seed asks the second; a 1-swap loop asks the first. Neither is a second
implementation of the other, which is the whole point.

## The state is incremental, and that is a cost decision

The retired exact solve's greedy seed measured every pair of `[candidate,
*seated]` once per candidate it considered, so the seed was O(seats^2) per
candidate and cubic overall. At n=150 that is invisible. At n=1000 it was 828 s
of an 1800 s budget and the seed still failed. Nothing here may reuse that shape.

What this holds instead is the seated set's own summary: which places are taken,
which seats carry each cell, family, palette group and mode, and the diversity
rule's stack of seated signatures. Every question is answered against **the
seated set only**, seated-to-seated relations are never recomputed, and seating
or unseating one candidate is O(1) in the seats already taken except for the
diversity rule's single vectorized pass.

## The rules, and which of them are hard

`location` and the diversity rule are hard: they are statements about the
identity of the thing being chosen rather than preferences about it. The three
counts between them are soft in the sense that a shortfall is recorded rather
than repaired — but nothing is ever seated by relaxing a rule it failed, so a
soft rule that nothing can satisfy leaves the seat empty.

The **palette-group cap is a count** — [`ceiling.PROPORTIONAL`], `max(1,
floor(0.025 n))` seats a map. It is Matt's rule and it is the only one it is: the
retired solve's same-group *distance* row is dropped rather than merged, so there
is no second threshold anywhere in this module.

## The diversity rule is one replaceable component

[`Twins`] is what ships: two finished pictures may not sit within [`ceiling.TAU`]
in the pixel-cloud metric. It is reached only through the small protocol
[`State`] uses — `within`, `hold`, `drop`, `record`, and the two attributes
`NAME` and `neighbours` — so a themed gallery that wants geometry-only
distinctness supplies its own object and changes nothing else. That seam is why
the rule's name and its threshold are on the record: two galleries chosen under
different diversity rules are not comparable, and the record is where a reader
finds out which one ran.
"""

from __future__ import annotations

from fractal_wallpapers.curation import ceiling

#: The rules, in the order [`State.refuses`] applies them. The first to fail
#: names the refusal, which is what makes the rejection ledger a partition of the
#: pool rather than a tally that double-counts.
#:
#: The diversity rule is **last** because it is the only one that costs anything.
#: The four above it are dictionary lookups over counts already held; this one
#: decodes a JPEG and builds half a mebibyte of pixel cloud. Every candidate the
#: cheap rules refuse is a signature not made.
#:
#: `picture_unreadable` sits immediately before it and is the same rule's other
#: outcome: a candidate whose picture cannot be opened is refused rather than
#: admitted. A rule that reads pixels must fail closed — admitting means the
#: diversity rule silently stops applying to exactly the candidates nothing can
#: check, and that has put untested rows in a shipped gallery before.
RULES = (
    "location",
    "group_cap",
    "cell_allowance",
    "family_allowance",
    "picture_unreadable",
    "twin",
)

#: How many seated pictures inside [`ceiling.TAU`] it takes to refuse. **One.**
#:
#: Deliberately stricter than [`ceiling.TWINS`], which is 2 and is the shipped
#: gallery pass's setting — there the argument is that one near neighbour is a
#: collection with a pair in it and three of a kind is what a person notices. A
#: gallery leg is choosing from nine thousand candidates for a few hundred seats
#: and can afford the strict form.
#:
#: It also decides what a 1-swap costs, and not only what the gallery looks like:
#: at one neighbour every seated picture inside the threshold is its own
#: single-member requirement, so a candidate close to two of them intersects to
#: nothing and is dropped before anything else is asked of it.
TWIN_NEIGHBOURS = 1

#: How many signatures the diversity rule's pixel-cloud cache holds before it
#: forgets the oldest. 256 is 128 MiB. The seated are **held** and never counted
#: against it; what this buys is the second and third offer of a candidate the
#: swap loop keeps coming back to.
SIGNATURE_CACHE = 256

#: How many blocks of the metric's quantiles the diversity rule's lower bound
#: reads.
#:
#: **Four.** The bound is the triangle inequality applied per direction and per
#: block of quantiles — the mean of `|a - b|` is at least `|mean a - mean b|` —
#: so one block is the distance between the two clouds' mean colours, and
#: [`pixel_clouds.QUANTILES`] blocks is the metric itself. Every setting in
#: between is sound; the question is only how much it settles.
#:
#: Measured over 79,800 pairs drawn from a pool's top two thousand: one block
#: settles 95.4% of pairs, two 97.4%, four 97.9%, sixteen 98.3%. Four is where
#: the curve flattens, and it is a sixteen-kibibyte signature against the
#: metric's five hundred and twelve.
BOUND_BLOCKS = 4

#: What the bound is, carried in every record that prunes by it. A prune is only
#: as good as its soundness argument, and this project has shipped a prune whose
#: premise was false — a location-level one, on the premise that two far-apart
#: places cannot make near-duplicate pictures, which is not true because colour
#: comes from the map rather than from the place.
BOUND = (
    f"the triangle inequality per direction and per block of {BOUND_BLOCKS} quantile "
    "groups: the mean absolute difference between two clouds is at least the mean "
    "absolute difference between their block means. A pair the bound puts at or beyond "
    "the threshold provably cannot violate, so it is never measured"
)


def reduce_signature(made):
    """One full signature as its `[BOUND_BLOCKS, DIRECTIONS]` block means.

    The signature is `[QUANTILES, DIRECTIONS]` flattened, and the bound reads it as
    [`BOUND_BLOCKS`] contiguous groups of **quantiles** averaged down. Contiguous,
    and along that axis rather than the other, because the projections were sorted
    before they were read: a block of adjacent quantiles is a band of the cloud,
    and the bound is the triangle inequality over the bands. Grouping across
    directions instead is still a sound partition and a far weaker bound — it
    averages a hundred unrelated projections at one quantile, and the settle rates
    the constant was chosen on are the band grouping's.
    """
    import numpy

    from fractal_wallpapers.palettes import groups

    grid = numpy.asarray(made, dtype=numpy.float32).reshape(groups.QUANTILES, groups.DIRECTIONS)
    return grid.reshape(BOUND_BLOCKS, groups.QUANTILES // BOUND_BLOCKS, groups.DIRECTIONS).mean(
        axis=1
    )


def bound_width() -> int:
    """The denominator the reduced distance is taken over. One place, one answer."""
    from fractal_wallpapers.palettes import groups

    return groups.DIRECTIONS * BOUND_BLOCKS


def clouds_for(candidates, cache: int = SIGNATURE_CACHE):
    """A [`pixel_clouds.Clouds`] over a view, addressed by **candidate key**.

    By key and not by path because the diversity rule is per candidate: one place
    may carry fifty rows, they are fifty different pictures, and the rule is about
    the pictures. A row whose picture is not on disk reads as `None`, which
    [`Twins`] refuses on rather than admits — see [`RULES`].
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


def _intersect(wanted: list, everything) -> set:
    """The intersection of a requirement list, with an empty list meaning `everything`."""
    if not wanted:
        return set(everything)
    out = set(wanted[0])
    for other in wanted[1:]:
        out &= other
        if not out:
            break
    return out


class Twins:
    """The shipped diversity rule: is this picture one of the seated ones?

    Two stores, and the split is [`BOUND`]'s. Every seated picture is kept twice —
    once as its full signature, held in the [`pixel_clouds.Clouds`], and once as
    [`reduce_signature`]'s four blocks of quantiles, sixteen kibibytes against
    half a mebibyte. A candidate is screened against the reduced stack first,
    which is a sound *lower* bound on the metric, so a seat the bound puts at or
    beyond [`ceiling.TAU`] provably cannot be a twin and is never measured. Only
    the survivors cost a full comparison.

    The bound settles almost everything — 99.2% of the pairs in the sweep that
    measured this pool — and what it buys is that the cost of the rule does not
    grow with the number of seats already taken. The candidate's own signature has
    to be made either way and that is the tenth of a second.

    **A seat can be dropped again.** That is the difference from the sequential
    twin state this replaces: a swap loop takes a seat back out, so the stack has
    to shrink as well as grow, and the seated-to-seated relations it does not
    touch are never recomputed.
    """

    #: What the record calls this rule. A themed leg supplies its own object with
    #: its own name, and the record is where a reader finds out which one ran.
    NAME = "twin"

    def __init__(
        self,
        clouds,
        tau: float | None = None,
        neighbours: int = TWIN_NEIGHBOURS,
        reduced: dict | None = None,
    ):
        self.clouds = clouds
        self.tau = ceiling.TAU if tau is None else float(tau)
        self.neighbours = int(neighbours)
        #: The seated, in the order they were held. A dropped seat is blanked to
        #: `None` rather than compacted, so no index a caller holds ever moves.
        self.keys: list = []
        self._reduced: list = []
        self._stack = None
        self._live: list = []
        self._at: dict = {}
        #: `{key: its reduced signature}`, made once and kept for the life of the
        #: pass. **This is the one store that decides what a pass costs.** See
        #: [`reduced_of`].
        #:
        #: Seeded from [`curation.signatures`] where a caller hands one in, which
        #: is the whole of what the sidecar buys: every key already in here is a
        #: picture this pass will never open.
        self._mine: dict = dict(reduced or {})
        #: How many of [`_mine`] arrived from the sidecar rather than from a
        #: decode. On the record, because a pass that read a store and a pass that
        #: did the work are not the same measurement.
        self.reduced_from_the_sidecar = len(self._mine)
        self.tested = 0
        self.settled_by_the_bound = 0
        self.measured = 0
        self.without_a_picture = 0
        self.reduced_made = 0
        self.reduced_hits = 0
        self.full_signatures_fetched = 0

    @property
    def held(self) -> list:
        """Every seated key the rule is currently holding, in the order held."""
        return [key for key in self.keys if key is not None]

    def reduced_of(self, key: str):
        """One candidate's reduced signature, made **once** and kept. `None` if
        the picture cannot be read.

        The whole cost of a pass lives here. Every question the bound asks reads
        the reduced form — sixteen kibibytes — and the full half-mebibyte one is
        needed only for the fraction of a percent of pairs the bound cannot
        settle. Deriving the reduced form from the full one through a bounded
        cache means a view larger than that cache re-decodes the same pictures on
        every pass, so a pass that finds nothing costs what a pass that finds
        everything costs. Measured before this store existed: **24,969 signatures
        made for an 8,704-row view, 2.9 decodes a row**, and the swap loop at
        n=1000 was 2,338 s of which ~2,392 s was decoding.

        Unbounded on purpose, and small enough to be: 16 KiB a row is 139 MB over
        the largest view this project builds. The **full** signatures stay in the
        bounded cache underneath, because those are half a mebibyte each.

        A caller that hands in [`curation.signatures`]' sidecar has this store
        already full for every row the sweep covered, so the decode below never
        runs for those and the pass opens a picture only for the full-signature
        fetches the bound could not settle.
        """
        name = str(key)
        held = self._mine.get(name)
        if held is not None:
            self.reduced_hits += 1
            return held
        import numpy

        made = self.clouds.of(name)
        if made is None:
            return None
        self.reduced_made += 1
        self._mine[name] = numpy.asarray(reduce_signature(made).reshape(-1))
        return self._mine[name]

    def within(self, key: str) -> list | dict:
        """`[(distance, seated key)]` inside [`tau`], closest first.

        A **dict** instead of a list says the picture could not be read, which is
        a refusal under its own name: "I could not read this" is not "this is a
        duplicate", and the two go to different places in the rejection ledger.
        """
        import numpy

        from fractal_wallpapers.palettes import pixel_clouds

        mine = self.reduced_of(key)
        if mine is None:
            self.without_a_picture += 1
            return {"unreadable": True, "why": "the candidate's picture is not on disk"}
        if self._stack is None:
            self._live = [at for at, name in enumerate(self.keys) if name is not None]
            self._stack = (
                numpy.stack([self._reduced[at] for at in self._live]) if self._live else None
            )
        if self._stack is None:
            return []
        self.tested += 1
        lower = numpy.abs(self._stack - mine).sum(axis=1, dtype=numpy.float64) / bound_width()
        close = [self._live[int(at)] for at in numpy.nonzero(lower < self.tau)[0]]
        self.settled_by_the_bound += len(self._live) - len(close)
        if not close:
            # The ordinary case by a long way, and the reason the full signature is
            # fetched lazily: 99.9% of seat comparisons are settled here, and a
            # candidate whose bound settles every one of them never needs its own
            # half-mebibyte cloud read back.
            return []
        made = self.clouds.of(str(key))
        if made is None:  # pragma: no cover - the picture vanished mid-pass
            self.without_a_picture += 1
            return {"unreadable": True, "why": "the candidate's picture is not on disk"}
        self.full_signatures_fetched += 1
        near = []
        for at in close:
            self.measured += 1
            gap = pixel_clouds.distance(made, self.clouds.of(self.keys[at]))
            if gap < self.tau:
                near.append((round(float(gap), 6), self.keys[at]))
        near.sort()
        return near

    def hold(self, key: str) -> bool:
        """Keep one seated picture's signature, in both forms. `False` if it has none."""
        mine = self.reduced_of(key)
        if mine is None:
            return False
        self.clouds.hold(str(key))
        self._at[str(key)] = len(self.keys)
        self.keys.append(str(key))
        self._reduced.append(mine)
        self._stack = None
        return True

    def drop(self, key: str) -> bool:
        """Take one seated picture back out. `False` if it was never held."""
        at = self._at.pop(str(key), None)
        if at is None:
            return False
        self.keys[at] = None
        self.clouds.let_go(str(key))
        self._stack = None
        return True

    def record(self) -> dict:
        """What the rule cost and what it settled, for the pass record."""
        return {
            "rule": self.NAME,
            "threshold": self.tau,
            "reduced_from_the_sidecar": self.reduced_from_the_sidecar,
            "threshold_from": "ceiling.TAU",
            "neighbours": self.neighbours,
            "metric": "pixel-cloud sliced Wasserstein-1 between two finished pictures",
            "bound": BOUND,
            "candidates_tested": self.tested,
            "seat_comparisons_settled_by_the_bound": self.settled_by_the_bound,
            "seat_comparisons_measured": self.measured,
            "reduced_signatures_kept": len(self._mine),
            "reduced_signatures_made": self.reduced_made,
            "reduced_signature_hits": self.reduced_hits,
            "full_signatures_fetched": self.full_signatures_fetched,
            "reduced_store_is": "one reduced signature a candidate, kept for the life of the "
            "pass. It is what stops a view larger than the bounded cache re-decoding the "
            "same pictures on every pass — see rules.Twins.reduced_of",
            "signatures_made": self.clouds.made,
            "signature_cache_hits": self.clouds.hits,
            "refused_without_a_picture_on_disk": self.without_a_picture,
            "seated_pictures_held": len(self.held),
        }


class State:
    """The seated set, and every rule read off it. Counts and never pictures.

    One instance is one pass's answer as it is being built. It is mutated by
    [`seat`] and [`unseat`] and by nothing else, so a caller asking "what if"
    asks [`requirements`] and never has to copy it.
    """

    def __init__(self, rule: ceiling.Rule, n: int, diversity=None):
        self.rule = rule
        self.n = int(n)
        #: The diversity rule, or `None` where a caller asked for none.
        self.diversity = diversity
        #: `{key: (candidate, why it was seated)}`, in the order seated.
        self.seated: dict = {}
        #: `{location: the one key seated there}`. One wallpaper per location is
        #: hard, so this axis is the only one whose value is a key rather than a set.
        self.places: dict = {}
        #: `{value: {key: True}}` per axis — **which seats** carry each cell,
        #: family, palette group and mode, rather than how many. A count cannot
        #: answer the swap loop's question, which is always *which* seat to remove.
        self.cells: dict = {}
        self.families: dict = {}
        self.groups: dict = {}
        self.modes: dict = {}
        #: `{rule: how many times it was the reason}`, over every candidate tested.
        self.refusals: dict = {name: 0 for name in RULES}
        #: `{key: what the diversity rule said it was too close to}`, for the record.
        self.refused_for: dict = {}

    # ------------------------------------------------------------------ #
    # What is seated.
    # ------------------------------------------------------------------ #
    @property
    def filled(self) -> int:
        return len(self.seated)

    @property
    def full(self) -> bool:
        return len(self.seated) >= self.n

    def holds(self, key) -> bool:
        return str(key) in self.seated

    def candidates(self) -> list:
        return [candidate for candidate, _why in self.seated.values()]

    def _axes(self, candidate):
        return (
            (self.groups, (candidate.group,)),
            (self.modes, (candidate.mode,)),
            (self.cells, candidate.cells),
            (self.families, candidate.families),
        )

    def seat(self, candidate, why: str) -> None:
        """Seat one candidate. The caller has already asked [`admits`]."""
        key = str(candidate.key)
        self.seated[key] = (candidate, why)
        self.places[candidate.location] = key
        for store, values in self._axes(candidate):
            for value in values:
                store.setdefault(value, {})[key] = True
        if self.diversity is not None:
            self.diversity.hold(key)

    def unseat(self, key):
        """Take one seat back out and hand the candidate back. The swap's other half."""
        key = str(key)
        candidate, _why = self.seated.pop(key)
        self.places.pop(candidate.location, None)
        for store, values in self._axes(candidate):
            for value in values:
                store[value].pop(key, None)
                if not store[value]:
                    del store[value]
        if self.diversity is not None:
            self.diversity.drop(key)
        return candidate

    def counts(self, store: dict) -> dict:
        """`{value: how many seats carry it}` off one of the axis stores."""
        return {value: len(keys) for value, keys in store.items()}

    # ------------------------------------------------------------------ #
    # The rules.
    # ------------------------------------------------------------------ #
    def counted_refusal(self, candidate) -> str | None:
        """The first of the four **counted** rules this candidate fails, or `None`.

        Apart from [`refuses`] because it costs nothing: it is dictionary lookups
        over the seated set, so the rejection ledger can ask it of every candidate
        in the pool after the fact, where asking the diversity rule of every
        candidate would be a pixel-cloud signature apiece.
        """
        if candidate.location in self.places:
            return "location"
        if len(self.groups.get(candidate.group, ())) >= self.rule.group_cap:
            return "group_cap"
        for cell in candidate.cells:
            if len(self.cells.get(cell, ())) + 1 > self.rule.allowed(cell, self.n):
                return "cell_allowance"
        for family in candidate.families:
            if len(self.families.get(family, ())) + 1 > self.rule.allowed(family, self.n):
                return "family_allowance"
        return None

    def refuses(self, candidate) -> str | None:
        """The first rule this candidate fails against the seated set, or `None`.

        [`RULES`] order, so the cheap counts refuse most of what they see before
        anything opens a picture. This is what the greedy seed asks; the swap loop
        asks [`requirements`], which is the same rules with the seat that would
        leave taken out of them.
        """
        counted = self.counted_refusal(candidate)
        if counted is not None:
            return counted
        if self.diversity is not None:
            near = self.diversity.within(candidate.key)
            if isinstance(near, dict):
                return "picture_unreadable"
            if len(near) >= self.diversity.neighbours:
                self.refused_for[candidate.key] = {
                    "too_close_to": near[0][1],
                    "distance": near[0][0],
                    "seated_within_the_threshold": len(near),
                    "rule": self.diversity.NAME,
                }
                return self.diversity.NAME
        return None

    def admits(self, candidate) -> bool:
        """Whether this candidate could be seated with nothing leaving."""
        return self.refuses(candidate) is None

    def counted_requirements(self, candidate) -> list:
        """`[{seated key}]` for the four rules that are arithmetic over counts.

        Apart from [`requirements`] so that [`removals`] can intersect these
        first: they are dictionary lookups, the diversity rule is a tenth of a
        second of pixels, and a candidate the counts already refuse outright must
        never pay for one.
        """
        wanted: list = []
        held = self.places.get(candidate.location)
        if held is not None:
            wanted.append({held})
        if len(self.groups.get(candidate.group, ())) >= self.rule.group_cap:
            wanted.append(set(self.groups.get(candidate.group, ())))
        for cell in candidate.cells:
            if len(self.cells.get(cell, ())) + 1 > self.rule.allowed(cell, self.n):
                wanted.append(set(self.cells.get(cell, ())))
        for family in candidate.families:
            if len(self.families.get(family, ())) + 1 > self.rule.allowed(family, self.n):
                wanted.append(set(self.families.get(family, ())))
        return wanted

    def requirements(self, candidate) -> list | None:
        """`[{seated key}]` — one set per rule this candidate currently fails.

        At least one member of **every** set has to leave before the candidate
        could be seated. An empty list is a candidate nothing is in the way of.
        `None` says no departure could admit it, which today means exactly one
        thing: its picture cannot be read, so the diversity rule fails closed and
        no seat leaving changes that.

        The whole 1-swap loop is this and an intersection.
        """
        wanted = self.counted_requirements(candidate)
        if self.diversity is not None:
            near = self.diversity.within(candidate.key)
            if isinstance(near, dict):
                return None
            # Each seated picture inside the threshold refuses on its own, so they
            # are conjunctive: one single-member set each, and two of them
            # intersect to nothing.
            wanted.extend({key} for _gap, key in near)
        return wanted

    def counted_removals(self, candidate) -> set:
        """Which single seat could leave under the four **counted** rules alone.

        Free — dictionary lookups over the seated set, and no picture opened. It
        is a **superset** of [`removals`], because the diversity rule can only ever
        narrow it, and that is what makes it useful: a caller can decide a
        candidate is not worth a pixel-cloud signature from this alone.
        """
        return _intersect(self.counted_requirements(candidate), self.seated)

    def narrowed(self, candidate, counted: set) -> set | None:
        """[`counted_removals`] narrowed by the diversity rule. **Opens a picture.**

        Split out so the caller decides when to pay. `None` is
        [`requirements`]'s `None`: no departure could admit this candidate.
        """
        if not counted or self.diversity is None:
            return counted
        near = self.diversity.within(candidate.key)
        if isinstance(near, dict):
            return None
        out = set(counted)
        for _gap, key in near:
            out &= {key}
            if not out:
                break
        return out

    def removals(self, candidate) -> set | None:
        """Which single seat could leave so that this candidate could be seated.

        The intersection of [`requirements`]. Nothing in the way is spelled as
        **every** seated key rather than as an empty set, so a caller reading a
        set has one meaning for it. `None` is [`requirements`]'s `None`.

        The counted rules are intersected **first and alone**, and the diversity
        rule is asked only if what is left is non-empty. That is not a shortcut
        past the rule: a candidate the counts refuse outright cannot be seated
        whatever any picture says.
        """
        return self.narrowed(candidate, self.counted_removals(candidate))

    # ------------------------------------------------------------------ #
    # What the rules were, for the record.
    # ------------------------------------------------------------------ #
    def record(self) -> dict:
        """Every rule this state applied, named and with its own constant.

        Every field here is one the leg genuinely reads, and the suite proves it
        mechanically: a record naming a rule nothing applied is worse than a
        record silent about it. `tau_group` is absent for that reason — the
        same-group distance rule is retired and this leg does not read it.
        """
        return {
            "rules": list(RULES),
            "hard": ["one wallpaper per location", "the diversity rule"],
            "counted": [
                "the palette group cap",
                "the per-cell allowance",
                "the per-family allowance",
            ],
            "no_fallback": "nothing is seated by relaxing a rule it failed, and no seat is "
            "padded. Unfilled beats padded",
            "group_cap": self.rule.group_cap,
            "group_cap_is": "a COUNT of seats one palette group may take. There is no "
            "same-group distance rule and no second threshold anywhere in this leg",
            "k": self.rule.k,
            "cell_share": ceiling.CELL_SHARE,
            "family_share": ceiling.FAMILY_SHARE,
            "allowance": "floor(k * t * n) + 1",
            "targets": dict(sorted(self.rule.targets.items())),
            "diversity": None
            if self.diversity is None
            else {
                "rule": self.diversity.NAME,
                "threshold": self.diversity.tau,
                "neighbours": self.diversity.neighbours,
                "replaceable": "one component behind `within`/`hold`/`drop`/`record`. A "
                "gallery chosen under a different diversity rule is not comparable to this "
                "one, which is why the rule and its threshold are here",
            },
            "refusals_while_choosing": dict(
                sorted(self.refusals.items(), key=lambda item: -item[1])
            ),
        }


__all__ = [
    "BOUND",
    "BOUND_BLOCKS",
    "RULES",
    "SIGNATURE_CACHE",
    "TWIN_NEIGHBOURS",
    "State",
    "Twins",
    "bound_width",
    "clouds_for",
    "reduce_signature",
]
