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

[`Places`] is the second implementation and the reason the seam exists: geometric
distinctness over the neutral descriptors at [`GEOMETRY_RADIUS`], for a themed
gallery whose colour was chosen in advance and whose pool is therefore a
near-duplicate pool under the twin test. It is a **replacement** and not a
complement — a pass runs one of them — and it is not a cheap approximation of the
other: the two metrics are near-orthogonal over this population, which
[`curation.distinct`] measured before either was placed.
"""

from __future__ import annotations

from fractal_wallpapers.curation import ceiling

#: The rules, in the order [`State.refuses`] applies them. The first to fail
#: names the refusal, which is what makes the rejection ledger a partition of the
#: pool rather than a tally that double-counts.
#:
#: The diversity rule is **last** because it is the only one that costs anything.
#: The four above it are dictionary lookups over counts already held; this one
#: decodes a JPEG and builds 128 KiB of pixel cloud. Every candidate the
#: cheap rules refuse is a signature not made.
#:
#: `picture_unreadable` sits immediately before it and is the same rule's other
#: outcome: a candidate whose picture cannot be opened is refused rather than
#: admitted. A rule that reads pixels must fail closed — admitting means the
#: diversity rule silently stops applying to exactly the candidates nothing can
#: check, and that has put untested rows in a shipped gallery before.
#:
#: `spiral` sits **last among the counted rules**, and the placement is the
#: measurement. A candidate refused here is one every colour rule already
#: admitted, so the column counts seats the share cap cost and not seats the
#: allowance would have refused anyway. Put first it would mask `cell_allowance`
#: and read as far more expensive than it is.
RULES = (
    "location",
    "group_cap",
    "cell_allowance",
    "family_allowance",
    "spiral",
    "picture_unreadable",
    "twin",
)


def rules_for(diversity) -> tuple:
    """[`RULES`] with the diversity rule that actually ran in the last slot.

    The tuple above is the shipped rule's spelling, and a themed pass under
    [`Places`] refuses under a different name. Every reader of the order — the
    record, the rejection ledger's partition — goes through here rather than
    keeping a second copy, because a ledger keyed on `twin` under a pass that
    never applied the twin test is a ledger naming a rule nothing ran.
    """
    if diversity is None:
        return RULES
    return RULES[:-1] + (str(diversity.NAME),)


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
#: forgets the oldest. The seated are **held** and never counted against it; what
#: this buys is the second and third offer of a candidate the swap loop keeps
#: coming back to.
#:
#: **2048, and it was 256 until PROFILE_solve_large_n measured what 256 cost.** A
#: swap pass at n=1000 re-tests about 870 of the same rows on every pass, and 256
#: entries against a view of 11,690 meant passes two, three and four re-decoded
#: what pass one had already read: 4,238 full signatures made for a leg that needs
#: 1,459. Raising it alone took the leg from 111 s to 68.9 s over a **bit-identical**
#: gallery — the largest single win in that profile, and a constant rather than an
#: algorithm.
#:
#: The price is memory: 128 KiB a signature at [`pixel_clouds.DIRECTIONS`] = 256,
#: so this is **256 MiB** held by one solve process against 32 MiB before (and it
#: would have been 1 GiB at the 1024 directions the metric used to run at, which is
#: why the number could not have been this before that came down). That is a real
#: cost on the one-pool-holding-process rule and it is written down in
#: `curation/GALLERY.md` beside it.
SIGNATURE_CACHE = 2048

#: The radius the **themed** diversity rule refuses inside, in [`distinct.METRIC`].
#:
#: **0.07.** A themed pool is a near-duplicate pool under the pixel-cloud metric
#: by construction — colour comes from the map, so filtering to one dominant cell
#: selects for pictures that are close to each other under exactly the rule the
#: main gallery refuses duplicates with (twin density 14-22x the whole pool's).
#: So a themed leg asks the other question instead: *are these two the same
#: place*, over the neutral descriptors, at a radius chosen for a collection
#: rather than for pool construction.
#:
#: Read off the two themed pools' own nearest-neighbour distributions on
#: 2026-09-01, after the pre-selection: `dark_vivid_lime` 424 places at a median
#: nearest gap of 0.0556 and a p75 of 0.0703, `dark_vivid_green` 1,097 at 0.0454
#: and 0.0595. 0.07 sits just above both p75s — it refuses the quarter of places
#: that are genuinely each other's near neighbours and leaves the rest, which is
#: 233 mutually-distinct lime places and 435 green ones under a greedy walk. It
#: is deliberately far above [`distinct.PRESELECT_RADIUS`] (0.02, which refuses
#: nothing this pool has not already lost): a rule that fires on nothing is not a
#: diversity rule.
#:
#: It is a **setting and not a law**: the ladder either side of it is 0.04 (369
#: lime places, 855 green), 0.05 (330 / 709) and 0.10 (126 / 208), and the number
#: to move if a themed gallery reads as repetitive or as needlessly small.
GEOMETRY_RADIUS = 0.07

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
#: the curve flattens, and it is a four-kibibyte signature against the metric's
#: hundred and twenty-eight. (Those settle rates were measured at 1024 directions;
#: the ratio of block count to quantile count is what they turn on, and
#: [`pixel_clouds.DIRECTIONS`] moved neither.)
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
    """One full signature as its `[BOUND_BLOCKS, pixel_clouds.DIRECTIONS]` block means.

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

    from fractal_wallpapers.palettes import groups, pixel_clouds

    grid = numpy.asarray(made, dtype=numpy.float32).reshape(
        groups.QUANTILES, pixel_clouds.DIRECTIONS
    )
    return grid.reshape(
        BOUND_BLOCKS, groups.QUANTILES // BOUND_BLOCKS, pixel_clouds.DIRECTIONS
    ).mean(axis=1)


def bound_width() -> int:
    """The denominator the reduced distance is taken over. One place, one answer."""
    from fractal_wallpapers.palettes import pixel_clouds

    return pixel_clouds.DIRECTIONS * BOUND_BLOCKS


def clouds_for(candidates, cache: int | None = None):
    """A [`pixel_clouds.Clouds`] over a view, addressed by **candidate key**.

    By key and not by path because the diversity rule is per candidate: one place
    may carry fifty rows, they are fifty different pictures, and the rule is about
    the pictures. A row whose picture is not on disk reads as `None`, which
    [`Twins`] refuses on rather than admits — see [`RULES`].

    `cache` is read from [`SIGNATURE_CACHE`] **at call time** and never bound as a
    default. It used to be `cache: int = SIGNATURE_CACHE`, which captures the
    constant at import: moving the constant then moved every reader of it *except*
    this one, so a caller raising it would have measured no change and concluded
    the cache was not the cost. `None` is "the shipped size".
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

    return pixel_clouds.Clouds(path_of, cache=int(SIGNATURE_CACHE if cache is None else cache))


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
    [`reduce_signature`]'s four blocks of quantiles, four kibibytes against a
    hundred and twenty-eight. A candidate is screened against the reduced stack first,
    which is a sound *lower* bound on the metric, so a seat the bound puts at or
    beyond [`ceiling.TAU`] provably cannot be a twin and is never measured. Only
    the survivors cost a full comparison.

    The bound settles almost everything — 99.2% of the pairs in the sweep that
    measured this pool — and what it buys is that the cost of the rule does not
    grow with the number of seats already taken. The candidate's own signature has
    to be made either way and that is the 16.8 ms — a tenth of a second before the
    metric came down to 256 directions.

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
        #: `|a|` per row of [`_stack`], rebuilt with it. The norm screen's whole
        #: store — one float a seat against the seat's own 1,024.
        self._norms = None
        self._live: list = []
        self._at: dict = {}
        #: The seated keys whose FULL cloud has actually been decoded. A seat is
        #: registered by [`hold`] and lands here only when something needs to
        #: measure against it — see [`cloud_of_seat`].
        self._decoded: set = set()
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
        #: How many of [`settled_by_the_bound`] the scalar norm screen settled
        #: before the reduced form was subtracted at all. On the record because a
        #: prune that stopped firing should be visible rather than inferred.
        self.settled_by_the_norm_screen = 0
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
        the reduced form — four kibibytes — and the full 128 KiB one is
        needed only for the fraction of a percent of pairs the bound cannot
        settle. Deriving the reduced form from the full one through a bounded
        cache means a view larger than that cache re-decodes the same pictures on
        every pass, so a pass that finds nothing costs what a pass that finds
        everything costs. Measured before this store existed: **24,969 signatures
        made for an 8,704-row view, 2.9 decodes a row**, and the swap loop at
        n=1000 was 2,338 s of which ~2,392 s was decoding.

        Unbounded on purpose, and small enough to be: 4 KiB a row is 37 MB over
        the largest view this project builds. The **full** signatures stay in the
        bounded cache underneath, because those are 128 KiB each.

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

        ## Two bounds, and the cheap one runs first

        The reduced bound below is `O(seats x BOUND_BLOCKS x DIRECTIONS)` of
        subtraction — a thousand floats a seat. In front of it sits a **scalar** per
        seat: the reverse triangle inequality on the L1 norm,
        `| |a|_1 - |b|_1 | <= |a - b|_1`, so a seat the screen puts at or beyond
        [`tau`] has its reduced bound at or beyond `tau` too and provably cannot be
        a twin. Every survivor still gets the full reduced bound, so `close` is the
        same set either way and the gallery is unchanged.

        Measured over this pool at 900 seats: the screen settles **69.3%** of seat
        comparisons on its own and takes a test from 2.96 ms to 1.19 ms.
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
            self._norms = (
                None
                if self._stack is None
                else numpy.abs(self._stack).sum(axis=1, dtype=numpy.float64)
            )
        if self._stack is None:
            return []
        self.tested += 1
        width = bound_width()
        screened = numpy.abs(self._norms - float(numpy.abs(mine).sum(dtype=numpy.float64))) / width
        live = numpy.nonzero(screened < self.tau)[0]
        self.settled_by_the_norm_screen += len(self._live) - len(live)
        if len(live):
            lower = numpy.abs(self._stack[live] - mine).sum(axis=1, dtype=numpy.float64) / width
            close = [self._live[int(live[at])] for at in numpy.nonzero(lower < self.tau)[0]]
        else:
            close = []
        self.settled_by_the_bound += len(self._live) - len(close)
        if not close:
            # The ordinary case by a long way, and the reason the full signature is
            # fetched lazily: 99.9% of seat comparisons are settled here, and a
            # candidate whose bound settles every one of them never needs its own
            # 128 KiB cloud read back.
            return []
        made = self.clouds.of(str(key))
        if made is None:  # pragma: no cover - the picture vanished mid-pass
            self.without_a_picture += 1
            return {"unreadable": True, "why": "the candidate's picture is not on disk"}
        self.full_signatures_fetched += 1
        near = []
        for at in close:
            self.measured += 1
            gap = pixel_clouds.distance(made, self.cloud_of_seat(self.keys[at]))
            if gap < self.tau:
                near.append((round(float(gap), 6), self.keys[at]))
        near.sort()
        return near

    def cloud_of_seat(self, name: str):
        """One seated picture's FULL cloud, decoded on first need and held after.

        The other half of [`hold`]'s laziness. The first candidate whose bound
        cannot settle this seat pays for the decode; from then on the seat is in
        the [`pixel_clouds.Clouds`] held store, which is unbounded, so a seat that
        is measured against once is never re-read however long the pass runs.
        """
        made = self.clouds.of(str(name))
        if made is not None and str(name) not in self._decoded:
            # Promote out of the bounded read cache. `Clouds.hold` re-asks `of`,
            # which is the hit this call just made.
            self.clouds.hold(str(name))
            self._decoded.add(str(name))
        return made

    def hold(self, key: str) -> bool:
        """Register one seat. `False` if it has no reduced signature.

        **The full cloud is NOT decoded here**, and that is the change
        PROFILE_solve_large_n bought. The bound settles 99.77% of a seat's
        comparisons off the 4 KiB reduced form, so decoding its 128 KiB cloud the
        moment it sits down pays 16.8 ms for something most seats never need: 912
        decodes at n=1000, of which the leg went on to read 523. What a seat needs
        to be *screened* is its reduced signature, which is in [`_reduced`] and
        usually came from the sidecar without opening anything at all; the full
        cloud is fetched by [`cloud_of_seat`] the first time a bound cannot settle.

        This was PARKED in `solver_design.md` as a memory question — 334 MB of held
        signatures at 653 seats — and it is a **time** win as well, which is what
        the profile added. Holding is still unbounded, so the memory half is
        unchanged for a seat that does get read.
        """
        mine = self.reduced_of(key)
        if mine is None:
            return False
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
        # A no-op for a seat nothing ever measured against, which is now most of
        # them: `let_go` only moves what the held store actually holds.
        self.clouds.let_go(str(key))
        self._decoded.discard(str(key))
        self._stack = None
        return True

    def record(self) -> dict:
        """What the rule cost and what it settled, for the pass record."""
        from fractal_wallpapers.palettes import pixel_clouds

        return {
            "rule": self.NAME,
            "threshold": self.tau,
            "reduced_from_the_sidecar": self.reduced_from_the_sidecar,
            "threshold_from": "ceiling.TAU",
            "neighbours": self.neighbours,
            "metric": "pixel-cloud sliced Wasserstein-1 between two finished pictures",
            "directions": pixel_clouds.DIRECTIONS,
            "directions_are": "the slice count the metric estimates over, and part of the "
            "rule's identity: two galleries chosen at different counts are measured in "
            "different metrics and are not comparable, the same way two chosen under "
            "different diversity rules are not. pixel_clouds.DIRECTIONS, which is the twin "
            "metric's own and not groups.DIRECTIONS",
            "bound_blocks": BOUND_BLOCKS,
            "bound": BOUND,
            "candidates_tested": self.tested,
            "seat_comparisons_settled_by_the_bound": self.settled_by_the_bound,
            "seat_comparisons_settled_by_the_norm_screen": self.settled_by_the_norm_screen,
            "norm_screen": "the reverse triangle inequality on the L1 norm, a scalar a seat "
            "in front of the reduced bound. A subset of the line above: every comparison the "
            "screen settles the reduced bound would have settled too, so `close` and the "
            "gallery are unchanged and only the arithmetic is",
            "seat_comparisons_measured": self.measured,
            "seated_pictures_decoded": len(self._decoded),
            "seated_pictures_decoded_is": "the seats something actually had to measure "
            "against. A seat's full cloud is read on first need and not at seat time — see "
            "rules.Twins.hold",
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


def places_for(candidates, rows=None) -> dict:
    """`{location key: its unit descriptor}` for one view. The geometry rule's store.

    By **location** and not by candidate, which is the whole difference between
    this and [`clouds_for`]: the neutral descriptor is read off a render that says
    nothing about a colouring, so a place's fifty rows are fifty pictures with one
    descriptor between them. That is exactly the property a themed leg wants — the
    colour is the theme, so the rule that keeps the collection varied must not be
    a rule about colour.

    A place the store has never seen is simply absent, and [`Places`] admits it —
    see there.
    """
    from fractal_wallpapers.curation import embeddings

    wanted = {str(candidate.location) for candidate in candidates}
    stored = embeddings.read() if rows is None else list(rows)
    return {
        str(row["key"]): embeddings.unpack(row["vector"])
        for row in stored
        if str(row["key"]) in wanted
    }


class Places:
    """The themed diversity rule: is this picture's PLACE one of the seated places?

    Geometry-only distinctness, over [`curation.embeddings`]' neutral descriptors,
    at [`GEOMETRY_RADIUS`]. It is [`Twins`]' replacement and never its complement:
    a pass runs one diversity rule or the other, and the record names which.

    Why a themed leg needs a different rule at all is measured rather than
    supposed. The pixel-cloud metric is over a picture's **colour cloud** and
    colour comes from the map, so a pool filtered to one dominant cell is a
    near-duplicate pool under exactly the rule the main gallery uses to refuse
    duplicates — twin density 14-22x the whole pool's, and a `dark_vivid_green`
    gallery that caps near a hundred seats where geometric distinctness leaves
    around a thousand places. Neither the bar nor the group cap is the lever.

    ## Three ways this is cheaper than [`Twins`], and one way it is weaker

    No picture is ever opened: the descriptors are read once for the whole view
    and every question after that is one dot product against a small stack. There
    is no bound to be sound about, because the exact distance costs what the bound
    would. And the store does not grow with the seats.

    The weakness is the one [`curation.distinct`] measured and wrote down: neutral
    distance and pixel-cloud distance are near-orthogonal over this population
    (Pearson 0.034). **This rule is not a cheap approximation of the twin test and
    must not be read as one.** It answers a different question — *are these two
    the same place* — which is the right question for a collection whose colour
    was chosen in advance, and the wrong one for a mixed gallery.

    ## A place with no descriptor is admitted, and counted

    The opposite of [`Twins`], which fails closed, and the same ruling
    [`distinct.preselect`] already made for the same store: the embedding store is
    built per place by its own leg, so a place can be newer than the last run, and
    refusing on a missing row would make the rule a silent function of when the
    store was last built. Admitting is safe here in a way it is not for the twin
    test: this rule runs *underneath* the one-per-location rule, so an unembedded
    place still takes at most one seat. The count is on the record whether or not
    it is zero.
    """

    #: What the record calls this rule.
    NAME = "geometry"

    def __init__(
        self,
        places: dict,
        locations: dict,
        tau: float | None = None,
        neighbours: int = TWIN_NEIGHBOURS,
    ):
        #: `{location key: unit descriptor}` — [`places_for`]'s answer.
        self.places = dict(places)
        #: `{candidate key: its location key}`, which is how the protocol's
        #: candidate-keyed questions reach a place.
        self.locations = {str(key): str(where) for key, where in locations.items()}
        self.tau = GEOMETRY_RADIUS if tau is None else float(tau)
        self.neighbours = int(neighbours)
        #: The seated, in the order held. A dropped seat is blanked rather than
        #: compacted, so no index a caller holds ever moves — [`Twins`]' shape.
        self.keys: list = []
        self._vectors: list = []
        self._stack = None
        self._live: list = []
        self._at: dict = {}
        self.tested = 0
        self.measured = 0
        self.without_a_descriptor = 0
        self.seated_without_a_descriptor = 0

    @property
    def held(self) -> list:
        """Every seated key the rule is currently holding, in the order held."""
        return [key for key in self.keys if key is not None]

    def vector_of(self, key: str):
        """One candidate's place descriptor, or `None` where the store has none."""
        return self.places.get(self.locations.get(str(key), ""))

    def within(self, key: str) -> list | dict:
        """`[(distance, seated key)]` inside [`tau`], closest first.

        Never a dict: this rule has no unreadable outcome. A candidate whose place
        carries no descriptor is admitted and counted, for the reason on the class.
        """
        import numpy

        mine = self.vector_of(key)
        if mine is None:
            self.without_a_descriptor += 1
            return []
        if self._stack is None:
            self._live = [at for at, name in enumerate(self.keys) if name is not None]
            self._stack = (
                numpy.stack([self._vectors[at] for at in self._live]) if self._live else None
            )
        if self._stack is None:
            return []
        self.tested += 1
        gaps = 1.0 - (self._stack @ mine)
        self.measured += len(self._live)
        near = [
            (round(float(gaps[row]), 6), self.keys[self._live[row]])
            for row in numpy.nonzero(gaps < self.tau)[0].tolist()
        ]
        near.sort()
        return near

    def hold(self, key: str) -> bool:
        """Keep one seated place's descriptor. `True` even where there is none.

        The seat is taken either way — this rule admitted it — so the state has to
        record that it is held or [`drop`] would have nothing to take back out. An
        unembedded seat simply never refuses anything, which is what admitting it
        meant.
        """
        import numpy

        mine = self.vector_of(key)
        if mine is None:
            self.seated_without_a_descriptor += 1
            self._at[str(key)] = None
            return True
        self._at[str(key)] = len(self.keys)
        self.keys.append(str(key))
        self._vectors.append(numpy.asarray(mine))
        self._stack = None
        return True

    def drop(self, key: str) -> bool:
        """Take one seated place back out. `False` if it was never held."""
        if str(key) not in self._at:
            return False
        at = self._at.pop(str(key))
        if at is None:
            return True
        self.keys[at] = None
        self._stack = None
        return True

    def record(self) -> dict:
        """What the rule was and what it cost, for the pass record."""
        from fractal_wallpapers.curation import distinct

        return {
            "rule": self.NAME,
            "threshold": self.tau,
            "threshold_from": "rules.GEOMETRY_RADIUS",
            "neighbours": self.neighbours,
            "metric": distinct.METRIC,
            "of": "the LOCATION and not the picture. Two galleries chosen under different "
            "diversity rules are not comparable, and this one is not a cheap twin test: "
            "neutral distance and pixel-cloud distance are near-orthogonal over this "
            "population (Pearson 0.034, curation.distinct.premise)",
            "descriptors_held": len(self.places),
            "candidates_tested": self.tested,
            "seat_comparisons_measured": self.measured,
            "pictures_opened": 0,
            "admitted_without_a_descriptor": self.without_a_descriptor,
            "seated_without_a_descriptor": self.seated_without_a_descriptor,
            "unembedded_are": "admitted and counted, the ruling distinct.preselect already "
            "made for this store. Safe here because this rule runs underneath "
            "one-per-location, so an unembedded place still takes at most one seat",
            "seated_places_held": len(self.held),
        }


class State:
    """The seated set, and every rule read off it. Counts and never pictures.

    One instance is one pass's answer as it is being built. It is mutated by
    [`seat`] and [`unseat`] and by nothing else, so a caller asking "what if"
    asks [`requirements`] and never has to copy it.
    """

    def __init__(self, rule: ceiling.Rule, n: int, diversity=None, spiral_cap: float | None = None):
        self.rule = rule
        self.n = int(n)
        #: The diversity rule, or `None` where a caller asked for none.
        self.diversity = diversity
        #: What share of the realized seats may be spiral locations, or `None`
        #: for no cap. `1.0` is the same thing as `None` arithmetically and is
        #: spelled by a caller who wants the record to say the cap ran and did
        #: not bind; `None` is spelled by one who did not ask for a cap at all.
        self.spiral_cap = None if spiral_cap is None else float(spiral_cap)
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
        #: `{key: True}` for each seat whose LOCATION the spiral probe called a
        #: spiral. Not an axis in [`_axes`]: the others are keyed by a value off
        #: the candidate and this one is a single set, so it is held and swept by
        #: hand in [`seat`] and [`unseat`] rather than given a one-key store.
        self.spirals: dict = {}
        #: `{rule: how many times it was the reason}`, over every candidate tested.
        self.refusals: dict = {name: 0 for name in rules_for(diversity)}
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
        if getattr(candidate, "spiral", False):
            self.spirals[key] = True
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
        self.spirals.pop(key, None)
        if self.diversity is not None:
            self.diversity.drop(key)
        return candidate

    def counts(self, store: dict) -> dict:
        """`{value: how many seats carry it}` off one of the axis stores."""
        return {value: len(keys) for value, keys in store.items()}

    # ------------------------------------------------------------------ #
    # The spiral share cap.
    # ------------------------------------------------------------------ #
    def spiral_allowance(self) -> int | None:
        """How many spiral seats this gallery may hold. `None` where no cap runs.

        `ceil(X * (filled + 1))` — [`ceiling.share_of`], the one spelling a colour
        target is also stated in, evaluated at **the seat count the gallery would
        have**. That `+ 1` is the same warm-up [`ceiling`]'s `floor(k*t*n) + 1`
        carries and it is load-bearing: against `filled` alone the first seat of an
        empty gallery is refused for taking 100% of nothing, and a cap that cannot
        seat a spiral first is a cap that reorders the gallery rather than sizing it.

        One spelling covers the swap loop too, and that is worth checking rather
        than assuming. A valid gallery has `spirals <= ceil(X * filled)`. A swap
        takes one seat out and puts one in, so `filled` does not move: if this
        candidate needs a seated spiral to leave, the gallery after the trade holds
        the same count it held before and is valid by the same inequality. So the
        test [`counted_refusal`] applies and the requirement
        [`counted_requirements`] records are the same arithmetic, not two.
        """
        if self.spiral_cap is None:
            return None
        return ceiling.share_of(self.spiral_cap, self.filled + 1)

    def refuses_as_spiral(self, candidate) -> bool:
        """Whether the cap is what stands between this candidate and a seat.

        **A candidate whose location has no score is never refused here.** Unknown
        is not `not_spiral` and it is not `spiral` either: a place nobody has
        scored counts toward nothing, so it can neither fill the cap nor be
        stopped by it. `curation.spiral_scores` argues why that asymmetry is the
        safe one.
        """
        allowance = self.spiral_allowance()
        if allowance is None or not getattr(candidate, "spiral", False):
            return False
        return len(self.spirals) + 1 > allowance

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
        if self.refuses_as_spiral(candidate):
            return "spiral"
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
        if self.refuses_as_spiral(candidate):
            # One seated spiral has to go. See [`spiral_allowance`] on why the
            # post-swap gallery is valid under the same inequality.
            wanted.append(set(self.spirals))
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
            "rules": list(rules_for(self.diversity)),
            "hard": ["one wallpaper per location", "the diversity rule"],
            "counted": [
                "the palette group cap",
                "the per-cell allowance",
                "the per-family allowance",
                *(["the spiral share cap"] if self.spiral_cap is not None else []),
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
            "spiral_cap": self.spiral_cap,
            "spiral_cap_is": (
                "no spiral share cap ran; every location was seatable whatever the probe "
                "said about it, and the `spiral` refusal column is zero by construction"
                if self.spiral_cap is None
                else (
                    f"at most ceil({self.spiral_cap:g} * seats filled) seats may sit at a "
                    f"location the spiral probe calls a spiral. A share of the REALIZED "
                    f"count, ceiling.share_of, which is the one spelling a colour target "
                    f"is stated in. The verdict is off curation.spiral_scores at the cut "
                    f"models/spiral/manifest.json carries, and a location with NO score "
                    f"counts toward nothing: unknown is not not_spiral"
                )
            ),
            "spiral_seats": len(self.spirals),
            "spiral_allowance": self.spiral_allowance(),
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
    "GEOMETRY_RADIUS",
    "RULES",
    "SIGNATURE_CACHE",
    "TWIN_NEIGHBOURS",
    "Places",
    "State",
    "Twins",
    "bound_width",
    "clouds_for",
    "places_for",
    "reduce_signature",
    "rules_for",
]
