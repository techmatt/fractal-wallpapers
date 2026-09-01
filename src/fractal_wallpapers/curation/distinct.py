"""Which places are visibly different places, decided before anything is coloured.

The diversity rule this project has shipped is a rule about **finished pictures**:
two seated wallpapers must be at least [`ceiling.TAU`] apart in the pixel-cloud
metric. That makes colour a coupled constraint in the seating — whether a
candidate may take a seat depends on the map every other seated candidate happened
to get — and it makes the rule expensive, because the metric costs half a mebibyte
a picture and the seating is quadratic in seats.

This module was built to be the other placement of the same rule: pre-select
geometrically distinct **locations** off [`curation.embeddings`]' neutral
descriptors, and let the seating choose freely inside what survives. A neutral
descriptor says nothing about a colouring that has not been chosen yet, so a
pre-filter over it would be a statement about the places alone and the seating
would stop carrying a pairwise rule at all.

## The premise was measured, and it does not hold

The decoupling rests on one claim: *if the neutral descriptors differ enough, the
coloured pictures almost certainly will*. That is an empirical claim about two
metrics over the same pairs, and it can be false — colour comes from the map
rather than from the place, so two unrelated frames through similar ramps are
near-duplicates by construction, which is exactly the finding that killed the
location-level prune the retired exact solve carried. **A correlated proxy is not a prune.**

Measured on 2026-08-27 over the 1,427 places of the clearing pool:

* [`premise`] — 1,200 pairs stratified to reach the region a radius sits in,
  neutral cosine against pixel-cloud W1 between each pair's own best candidate:
  **Pearson 0.034, Spearman 0.063.**
* [`twins`] — every twin pair in that pool, found exactly over all 1,017,451 pairs
  through [`rules.BOUND`]: **6,720 of them**, at a median neutral distance of
  **0.226**. A pre-filter at 0.10 — which already refuses 98% of the pool — removes
  **413 of the 6,720**. At 0.04 it removes 36.

So the two are near-orthogonal. **Pairwise diversity does not move to pool
construction**, the pixel-cloud twin test is not demotable to a residual, and a
neutral radius is a different rule answering a different question — *are these two
the same place* — which has to be justified on its own terms rather than as a
substitute for [`ceiling.TAU`].

Both readings are kept because they are not the same instrument. A correlation is
taken over pairs drawn to span the range, and twins are seven in a thousand of
those, so a scatter can only ever put a handful of them on the page. The sweep
finds all of them and asks the question a pre-filter actually has to answer.

## Both rules act, and they are not the same rule

The measurement above did not kill the neutral radius; it killed the *substitution*.
So both are placed, in the two places their questions belong:

* **Are these two the same place?** [`preselect`] at [`PRESELECT_RADIUS`], over
  the neutral descriptors, at pool construction. Geometric distinctness only. It
  errs toward over-admitting on purpose.
* **Do these two read as one wallpaper?** The twin test at [`ceiling.TAU`], over
  the pixel clouds, sequential inside [`curation.solve`]'s walk. That is the
  rule the 6,720 twin pairs are a statement about, and nothing here weakens it.

[`RADII`] stays a set of **candidates to look at** rather than a setting: it is
what [`sheet`] draws the near pairs at, and a person reads the page and decides.
[`PRESELECT_RADIUS`] is the one number this module writes down, it is a
distinctness radius and not a diversity radius, and it is justified on its own
terms below rather than by anything it substitutes for.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from pathlib import Path

from fractal_wallpapers.curation import embeddings, neutral, rules
from fractal_wallpapers.paths import tracked_name

#: The schema every record this module writes carries.
SCHEMA = 1

#: The subtree this module's records and sheets land in.
UNIT = "distinct"

#: What the distance between two locations is. Cosine over unit vectors, so
#: `1 - dot`, which is the same distance [`gallery.Draw`] refuses inside.
METRIC = (
    "cosine distance (1 - dot) between two locations' frozen DINOv2 descriptors, each read "
    "off that location's neutral render — one colormap, one geometry, one mode, chosen "
    "once and digested into a stamp every row carries"
)

#: The radii the sheet shows near pairs at. **Candidates to look at and not a
#: setting.** They bracket the two numbers already set in a comparable space —
#: [`gallery.RADIUS`] at 0.07, whose calibration read put nearest-neighbour
#: distances at a median of 0.024 — from well inside it to well outside.
RADII = (0.02, 0.04, 0.07, 0.10)

#: How many near pairs the sheet shows per radius, nearest first. A dozen is an
#: anecdote and the whole page is the instrument, so this is the number at which a
#: person can see a band rather than three examples.
PAIRS_SHOWN = 16

#: How many pairs [`premise`] measures. Each one costs two pixel-cloud signatures
#: at about a tenth of a second, and they are cached per picture — so the real
#: cost is the distinct pictures, not the pairs.
PREMISE_PAIRS = 800

#: How many equal-width bands of neutral distance the premise sample is drawn
#: from. Stratified rather than uniform: an unstratified draw over a store whose
#: pairs are mostly far apart would spend the whole sample past 0.2 and say
#: nothing about the range a radius would ever sit in.
PREMISE_BANDS = 10

#: The radius the pool's pre-selection refuses inside, in [`METRIC`].
#:
#: **0.02**, just above the clearing pool's p10 nearest-neighbour distance of
#: 0.0155 — 425 pairs touching 250 of its 1,427 places. It is deliberately at the
#: loose end of [`RADII`]: this is a rule about *places*, and a place refused here
#: is one no colouring can bring back, so it only fires where two neutral renders
#: are as close as the closest tenth of the pool ever gets.
#:
#: It buys **nothing** towards the diversity rule and is not asked to. The sweep
#: above says a filter here removes 6 of the pool's 6,720 twin pairs; the twin
#: test at [`ceiling.TAU`] is what rejects, and over-admitting is the safe
#: direction for a rule that runs first.
PRESELECT_RADIUS = 0.02

#: The seed every draw in this module is taken under, recorded with it.
SEED = 0


class DistinctRefused(RuntimeError):
    """The pre-selection cannot be read."""


# --------------------------------------------------------------------------- #
# The join.
# --------------------------------------------------------------------------- #
def join(locations, rows=None) -> dict:
    """How much of a population the neutral store can actually see.

    Reported **first** and reported whether or not it is clean. A pre-filter that
    silently drops a third of the pool is not a detail to work around: every
    location it cannot see is a location the seating either has to admit untested
    or refuse for a reason nobody chose, and both are decisions this report has to
    put in front of somebody.
    """
    stored = embeddings.read() if rows is None else list(rows)
    held = {str(row["key"]) for row in stored}
    wanted = {str(key) for key in locations}
    missing = sorted(wanted - held)
    return {
        "store": tracked_name(embeddings.store_path()),
        "stored_locations": len(held),
        "asked": len(wanted),
        "embedded": len(wanted & held),
        "unembedded": len(missing),
        "share_embedded": round(len(wanted & held) / max(1, len(wanted)), 4),
        "missing": missing,
    }


def matrix_for(locations, rows=None):
    """`(keys, matrix)` — the descriptors of one population, in key order.

    Unit vectors, so a cosine distance between two of them is `1 - dot` and the
    whole nearest-neighbour read is one matrix multiply.
    """
    import numpy

    stored = embeddings.read() if rows is None else list(rows)
    wanted = {str(key) for key in locations}
    kept = [row for row in stored if str(row["key"]) in wanted]
    kept.sort(key=lambda row: str(row["key"]))
    if not kept:
        return [], numpy.zeros((0, 0), dtype=numpy.float32)
    return [str(row["key"]) for row in kept], numpy.stack(
        [embeddings.unpack(row["vector"]) for row in kept]
    )


# --------------------------------------------------------------------------- #
# How far apart the places are.
# --------------------------------------------------------------------------- #
def nearest(matrix) -> dict:
    """Each point's distance to its nearest other point, as a distribution.

    The number a radius is read against. A radius below the median of this refuses
    almost nothing; a radius above its p90 refuses most of the pool, and the band
    between them is where a choice actually is one.
    """
    import numpy

    if len(matrix) < 2:
        return {"points": len(matrix)}
    gaps = []
    for at in range(0, len(matrix), 512):
        block = 1.0 - (matrix[at : at + 512] @ matrix.T)
        for row, index in enumerate(range(at, min(at + 512, len(matrix)))):
            block[row, index] = numpy.inf
        gaps.extend(float(value) for value in block.min(axis=1))
    gaps.sort()

    def at(share: float) -> float:
        return round(gaps[min(len(gaps) - 1, int(share * len(gaps)))], 4)

    return {
        "points": len(matrix),
        "metric": METRIC,
        "min": round(gaps[0], 4),
        "p01": at(0.01),
        "p05": at(0.05),
        "p10": at(0.10),
        "p25": at(0.25),
        "median": at(0.50),
        "p75": at(0.75),
        "p90": at(0.90),
        "max": round(gaps[-1], 4),
        "mean": round(statistics.fmean(gaps), 4),
        "under": {str(radius): sum(1 for gap in gaps if gap < radius) for radius in RADII},
    }


def near_pairs(keys, matrix, radius: float, limit: int | None = None) -> list:
    """Every pair closer than `radius`, nearest first. `[(a, b, distance)]`.

    Quadratic and it does not matter: the population a pre-selection runs over is
    the pool's distinct **locations**, which is thousands rather than the ledger's
    tens of thousands of rows, and the whole matrix is one multiply.
    """
    import numpy

    out = []
    for at in range(0, len(matrix), 512):
        block = 1.0 - (matrix[at : at + 512] @ matrix.T)
        for row, one in enumerate(range(at, min(at + 512, len(matrix)))):
            close = numpy.nonzero(block[row] < float(radius))[0]
            out.extend(
                (keys[one], keys[int(other)], float(block[row, int(other)]))
                for other in close
                if int(other) > one
            )
    out.sort(key=lambda pair: pair[2])
    return out if limit is None else out[: int(limit)]


def radius_table(keys, matrix, radii=RADII) -> dict:
    """What each candidate radius would cost, in places and in pairs.

    A greedy farthest-point draw is not run here: the number a person needs to
    look at a sheet is how many pairs the radius calls duplicates, and how much of
    the pool that is.
    """
    out = {}
    for radius in radii:
        pairs = near_pairs(keys, matrix, radius)
        touched = {key for pair in pairs for key in pair[:2]}
        out[str(radius)] = {
            "radius": radius,
            "pairs": len(pairs),
            "locations_in_a_near_pair": len(touched),
            "share_of_the_pool": round(len(touched) / max(1, len(keys)), 4),
        }
    return out


# --------------------------------------------------------------------------- #
# The pre-selection.
# --------------------------------------------------------------------------- #
def suppress(order, radius: float = PRESELECT_RADIUS, rows=None) -> dict:
    """`{kept, refused, unembedded, asked}` — the greedy, over location keys alone.

    THE walk, and the only implementation of it. `order` is the places in the
    order they are offered, and the first of a near-cluster to be offered is the
    one that survives it — so the caller's ordering *is* the rule about which
    place represents a cluster, and there is nowhere else for that decision to
    hide. [`preselect`] offers them strongest-candidate-first;
    [`candidate_ledger.feasibility`] has no score to offer them by and says so.

    A place with no neutral descriptor is **kept** and counted, for the reason on
    [`preselect`]: refusing on a missing row would make the filter a silent
    function of when the embedding store was last built.

    Each refusal names the place that took it and how far apart the two are, and
    nothing else — a caller that knows more about a place decorates its own rows.
    """
    import numpy

    radius = float(radius)
    order = [str(key) for key in order]
    keys, matrix = matrix_for(order, rows)
    at = {key: index for index, key in enumerate(keys)}
    held_rows: list = []
    kept: set = set()
    refused: list = []
    unembedded: list = []
    for key in order:
        index = at.get(key)
        if index is None:
            unembedded.append(key)
            kept.add(key)
            continue
        if held_rows:
            gaps = 1.0 - (matrix[held_rows] @ matrix[index])
            nearest_at = int(numpy.argmin(gaps))
            if float(gaps[nearest_at]) < radius:
                refused.append(
                    {
                        "location": key,
                        "lost_to": keys[held_rows[nearest_at]],
                        "distance": round(float(gaps[nearest_at]), 6),
                    }
                )
                continue
        held_rows.append(index)
        kept.add(key)
    return {"kept": kept, "refused": refused, "unembedded": unembedded, "asked": order}


def preselect(candidates, radius: float = PRESELECT_RADIUS, rows=None, log=print) -> tuple:
    """`(the candidates whose place survived, the record)`. Geometric distinctness only.

    A greedy suppression over places and not over rows: each location is
    represented by its **strongest** clearing candidate, the places are walked in
    that order, and a place closer than `radius` to a place already kept is
    refused and told which one took it. Strongest first because the choice inside
    a near-cluster is arbitrary otherwise, and the strongest place is the one a
    seating would have reached for anyway.

    **A location with no neutral descriptor is admitted, not dropped.** The store
    is built from a neutral render per place and a place can be newer than the
    last embedding leg; refusing on a missing row would make the pre-filter a
    silent function of when the store was last built. It is counted, and the count
    is on the record whether or not it is zero.

    What this refuses is a *place*, so the whole of that place's ledger goes with
    it — which is why the record reports both, and why the share to read is the
    share of **locations**. It is not the near-pair count: a cluster of five
    places inside the radius loses four, and both numbers are on the record.
    """
    radius = float(radius)
    best: dict = {}
    for candidate in candidates:
        held = best.get(candidate.location)
        if held is None or (-candidate.score, candidate.key) < (-held.score, held.key):
            best[candidate.location] = candidate
    order = sorted(best, key=lambda key: (-best[key].score, best[key].key))
    walk = suppress(order, radius=radius, rows=rows)
    kept, unembedded = walk["kept"], walk["unembedded"]
    refused = [
        {
            **row,
            "p_ge4": round(best[row["location"]].score, 6),
            "picture": best[row["location"]].picture,
            "lost_to_picture": best[row["lost_to"]].picture,
        }
        for row in walk["refused"]
    ]
    surviving = [candidate for candidate in candidates if candidate.location in kept]
    refused.sort(key=lambda row: row["distance"])
    log(
        f"[distinct] pre-selection at {radius}: {len(kept):,} of {len(order):,} place(s) kept, "
        f"{len(refused):,} refused"
    )
    return surviving, {
        "radius": radius,
        "metric": METRIC,
        "store": tracked_name(embeddings.store_path()),
        "order": "each place's strongest clearing candidate, P(>=4) descending, ties by key",
        "rule": "a place closer than the radius to a place already kept is refused. "
        "Geometric distinctness only: this asks whether two places are the same place, and "
        "it is NOT the diversity rule — the twin test at ceiling.TAU is",
        "places_asked": len(order),
        "places_kept": len(kept),
        "places_refused": len(refused),
        "share_of_places_refused": round(len(refused) / max(1, len(order)), 4),
        "admitted_without_a_descriptor": len(unembedded),
        "unembedded": unembedded,
        "candidates_asked": len(candidates),
        "candidates_kept": len(surviving),
        "candidates_refused": len(candidates) - len(surviving),
        "refusals": refused,
    }


# --------------------------------------------------------------------------- #
# The premise.
# --------------------------------------------------------------------------- #
def premise(
    keys,
    matrix,
    picture_of,
    pairs: int = PREMISE_PAIRS,
    bands: int = PREMISE_BANDS,
    seed: int = SEED,
    log=print,
) -> dict:
    """Neutral descriptor distance against pixel-cloud W1, over a stratified sample.

    `picture_of(key)` is the coloured candidate the pair is judged on — the best
    thing a seating would actually seat at that place, not the neutral render,
    because the claim under test is about the **coloured** pictures.

    The sample is drawn over the bands of [`ladder_for`] so it spans the range
    **including the region a radius would sit in**, which an equal-width ladder
    over this store's own spread does not reach at all. The two
    correlations are reported together on purpose: Pearson says whether the
    relationship is linear, Spearman whether it is monotone at all, and a design
    that only needs "far in one implies far in the other" is asking the second
    question.
    """
    import random

    import numpy

    from fractal_wallpapers.palettes import pixel_clouds

    usable = [at for at, key in enumerate(keys) if picture_of(key) is not None]
    if len(usable) < 4:
        raise DistinctRefused(
            f"{len(usable)} of {len(keys)} locations have a candidate picture on disk, "
            "which is not enough to test the premise on"
        )
    rng = random.Random(seed)
    drawn = _stratified(usable, matrix, pairs, bands, rng)
    places = len({at for pair in drawn for at in pair})
    log(f"[distinct] premise: {len(drawn)} pair(s) over {places} place(s)")
    signatures: dict = {}

    def signature(at: int):
        if at not in signatures:
            signatures[at] = pixel_clouds.of_picture(picture_of(keys[at]))
        return signatures[at]

    points = []
    for one, other in drawn:
        neutral_gap = float(1.0 - matrix[one] @ matrix[other])
        cloud_gap = pixel_clouds.distance(signature(one), signature(other))
        points.append(
            {
                "a": keys[one],
                "b": keys[other],
                "neutral": round(neutral_gap, 6),
                "pixel_cloud": round(cloud_gap, 6),
            }
        )
    xs = numpy.array([point["neutral"] for point in points])
    ys = numpy.array([point["pixel_cloud"] for point in points])
    return {
        "pairs": len(points),
        "places": len(signatures),
        "seed": seed,
        "bands": bands,
        "ladder": "the candidate radii as band edges below 0.10, equal-width above",
        "neutral_metric": METRIC,
        "pixel_cloud_metric": pixel_clouds.METRIC,
        "pearson": round(float(numpy.corrcoef(xs, ys)[0, 1]), 4),
        "spearman": round(float(numpy.corrcoef(_ranked(xs), _ranked(ys))[0, 1]), 4),
        "reads": "the premise is that far in the neutral descriptor implies far in the "
        "coloured pixels. What refutes it is not a low correlation but near pairs in the "
        "PIXEL cloud that are far apart in the descriptor — the pre-filter would let those "
        "through, and they are the ones counted below",
        "twins_the_prefilter_would_pass": _leakage(points),
        "points": points,
    }


def _ranked(values):
    import numpy

    order = numpy.argsort(numpy.argsort(values))
    return order.astype(numpy.float64)


def ladder_for(top: float, bands: int) -> list:
    """The band edges the premise sample is stratified over. Dense where a radius is.

    **Not equal-width, and the reason is a measured one.** Arbitrary pairs of this
    store sit at a median neutral distance of 0.35 and reach past 0.7, while every
    radius anybody would set is under 0.10 — the nearest-neighbour median is 0.038.
    Equal-width bands over the observed range therefore put the entire decision
    region inside the first band and the sample never lands in it: a first attempt
    at this drew 562 pairs whose *minimum* neutral distance was 0.021, so the
    region a pre-filter would act in was not measured at all.

    So the ladder is [`RADII`] itself below 0.10 — each candidate radius is a band
    edge, which is exactly the resolution the decision needs — and equal-width
    above it, where the only question is whether the relationship holds at large
    distances.
    """
    low = [0.0, *sorted(float(radius) for radius in RADII)]
    above = max(1, int(bands) - len(low) + 1)
    step = max(1e-6, (float(top) - low[-1]) / above)
    return low + [round(low[-1] + step * (step_at + 1), 6) for step_at in range(above)]


def _stratified(usable, matrix, pairs: int, bands: int, rng) -> list:
    """`pairs` index pairs, spread over the bands of [`ladder_for`].

    Over the **exact** pair distances and not a rejection draw. The population a
    pre-selection runs over is the pool's distinct locations — thousands, not the
    ledger's tens of thousands of rows — so the whole distance matrix is one
    multiply and a few tens of megabytes, and it is the only way the sparse low
    bands get filled: pairs under 0.02 are four in ten thousand of this store, and
    a rejection draw that proposed a million pairs would still find a handful.
    """
    import numpy

    if len(usable) > PAIR_MATRIX_LIMIT:
        raise DistinctRefused(
            f"{len(usable):,} locations is {len(usable) * (len(usable) - 1) // 2:,} pairs, "
            f"past the {PAIR_MATRIX_LIMIT:,} this builds the exact matrix for. Restrict the "
            "population first — a premise check is about the pool a seating chooses from"
        )
    taken = numpy.asarray(usable)
    block = 1.0 - (matrix[taken] @ matrix[taken].T)
    one, other = numpy.triu_indices(len(taken), k=1)
    gaps = block[one, other]
    edges = ladder_for(float(gaps.max()), bands)
    want = max(1, pairs // max(1, len(edges) - 1))
    drawn = []
    for at in range(len(edges) - 1):
        inside = numpy.nonzero((gaps >= edges[at]) & (gaps < edges[at + 1]))[0]
        picked = (
            inside
            if len(inside) <= want
            else rng.sample(list(int(value) for value in inside), want)
        )
        drawn.extend(
            (int(taken[one[int(value)]]), int(taken[other[int(value)]])) for value in picked
        )
    return drawn


#: How many locations the premise check will build the exact pair matrix for.
#: 6,000 points is eighteen million pairs at four bytes, which is the size at
#: which an exact answer is still cheaper than an approximate one that misses the
#: band the decision is in.
PAIR_MATRIX_LIMIT = 6000


#: How many pictures the twin sweep screens against the whole population at once.
#: The bound is one broadcast subtraction, so the temporaries are
#: `this x places x width` floats — sixteen keeps that under a tenth of a gibibyte
#: at this pool's size, where sixty-four would be a quarter of one.
BOUND_BLOCK = 16


def twins(
    keys,
    matrix,
    picture_of,
    tau: float | None = None,
    cache: int = 384,
    reduced_for=None,
    log=print,
) -> dict:
    """**Every** twin pair in the population, found exactly, and where it sits in
    the descriptor.

    The decisive premise check, and a different question from [`premise`]'s
    scatter. A correlation is taken over pairs drawn to span the range, and twins
    are four in a thousand of those — so a sample can only ever put a handful of
    them on the page. This finds all of them and asks the question a pre-filter
    actually has to answer: **of the pairs a person would call one wallpaper, how
    many would a neutral radius have removed?** A radius that removes none of them
    is a radius that buys nothing towards the rule it is replacing, whatever the
    correlation says.

    Exact over a million pairs because the metric admits a sound lower bound —
    [`rules.BOUND`], the triangle inequality per direction and per block of
    quantiles. A pair the bound puts at or beyond `tau` provably cannot be a twin,
    so it is never measured. What it costs is one signature per picture to build
    the bound signatures, and then only the survivors in full.

    `reduced_for(key)` is where those bound signatures come from when a caller has
    them already — [`curation.signatures`]' sidecar holds exactly this vector for
    every clearing candidate, and this sweep used to build them and throw them
    away. It returns `None` for a key it cannot answer for and that key is decoded
    as before, so an unswept checkout is slower and never different.
    """
    import numpy

    from fractal_wallpapers.curation import ceiling
    from fractal_wallpapers.palettes import pixel_clouds

    tau = ceiling.TAU if tau is None else float(tau)
    usable = [at for at, key in enumerate(keys) if picture_of(key) is not None]
    held = 0
    made = []
    for at in usable:
        ready = None if reduced_for is None else reduced_for(keys[at])
        if ready is not None:
            held += 1
            made.append(numpy.asarray(ready).reshape(-1))
            continue
        made.append(
            rules.reduce_signature(pixel_clouds.of_picture(picture_of(keys[at]))).reshape(-1)
        )
    log(
        f"[distinct] twins: bound signatures for {len(usable):,} picture(s) "
        f"({held:,} from the sidecar, {len(usable) - held:,} decoded)"
    )
    reduced = numpy.stack(made) if made else numpy.zeros((0, rules.bound_width()), numpy.float32)
    width = rules.bound_width()
    survivors: list = []
    screened = 0
    # Blocked rather than one big outer difference: the broadcast is
    # `block x places x width` floats and a full pass over this pool would be a
    # quarter of a gibibyte of temporaries for an answer that is one number a pair.
    for start in range(0, len(usable), BOUND_BLOCK):
        mine = reduced[start : start + BOUND_BLOCK]
        block = numpy.abs(mine[:, None, :] - reduced[None, :, :]).sum(axis=2) / width
        for row, one in enumerate(range(start, min(start + BOUND_BLOCK, len(usable)))):
            close = numpy.nonzero(block[row, one + 1 :] < tau)[0]
            screened += len(usable) - one - 1
            survivors.extend((one, one + 1 + int(other)) for other in close)
    log(f"[distinct] twins: {len(survivors):,} of {screened:,} pairs survive the bound")

    clouds = pixel_clouds.Clouds(lambda name: picture_of(keys[usable[int(name)]]), cache=cache)
    found = []
    for one, other in survivors:
        gap = pixel_clouds.distance(clouds.of(str(one)), clouds.of(str(other)))
        if gap >= tau:
            continue
        first, second = usable[one], usable[other]
        found.append(
            {
                "a": keys[first],
                "b": keys[second],
                "pixel_cloud": round(gap, 6),
                "neutral": round(float(1.0 - matrix[first] @ matrix[second]), 6),
            }
        )
    found.sort(key=lambda pair: pair["pixel_cloud"])
    log(f"[distinct] twins: {len(found):,} real twin pair(s)")
    return {
        "tau": tau,
        "places": len(usable),
        "pairs_screened": screened,
        "survived_the_bound": len(survivors),
        "twin_pairs": len(found),
        "rate": round(len(found) / max(1, screened), 8),
        "bound": rules.BOUND,
        "removed_by_radius": {str(radius): _removed(found, float(radius)) for radius in RADII},
        "reads": "the premise holds to the extent a radius removes these. A radius that "
        "removes none of them does not replace the twin test, however the scatter looks",
        "pairs": found,
    }


def _removed(found: list, radius: float) -> dict:
    """How many of the real twin pairs a pre-filter at `radius` would have removed."""
    removed = sum(1 for pair in found if pair["neutral"] < radius)
    return {
        "radius": radius,
        "twins_the_radius_removes": removed,
        "twins_it_admits": len(found) - removed,
        "share_removed": round(removed / max(1, len(found)), 4),
    }


def _leakage(points: list) -> dict:
    """Pairs the pre-filter would admit that the twin test would refuse.

    The number that decides the design. A pre-filter at radius `r` admits every
    pair whose neutral distance is at least `r`; the twin test refuses any pair
    under [`ceiling.TAU`] in the pixel cloud. A pair in both sets is one the
    pre-selection lets through and a person would call a duplicate — so this is
    the residual the twin test still has to catch, measured rather than assumed.
    """
    from fractal_wallpapers.curation import ceiling

    out = {}
    for radius in RADII:
        admitted = [point for point in points if point["neutral"] >= radius]
        leaked = [point for point in admitted if point["pixel_cloud"] < ceiling.TAU]
        out[str(radius)] = {
            "admitted": len(admitted),
            "twins_among_them": len(leaked),
            "rate": round(len(leaked) / max(1, len(admitted)), 6),
        }
    return {"tau": ceiling.TAU, "by_radius": out}


# --------------------------------------------------------------------------- #
# The scatter.
# --------------------------------------------------------------------------- #
#: How large the premise scatter is drawn, in CSS pixels.
PLOT = (620, 420)


def scatter(read: dict, width: int = PLOT[0], height: int = PLOT[1]) -> str:
    """The premise as one inline SVG: neutral distance across, pixel-cloud W1 up.

    Inline and hand-drawn rather than through a plotting library, for the reason
    this repository draws every other figure that way: the base install is
    deliberately thin, and a scatter of a thousand points is four hundred `circle`
    elements and two axes. The two lines that matter are drawn on it — the twin
    threshold across, and each candidate radius down — because the question the
    picture answers is how many points sit in the bottom-right corner, which is
    the corner a pre-filter admits and a person calls a duplicate.
    """
    from fractal_wallpapers.curation import ceiling

    points = read.get("points") or []
    if not points:
        return ""
    pad = 48
    top = max(point["neutral"] for point in points) or 1.0
    high = max(point["pixel_cloud"] for point in points) or 1.0

    def across(value: float) -> float:
        return pad + (width - 2 * pad) * value / top

    def up(value: float) -> float:
        return height - pad - (height - 2 * pad) * value / high

    dots = "".join(
        f'<circle cx="{across(point["neutral"]):.1f}" cy="{up(point["pixel_cloud"]):.1f}" '
        f'r="2" fill="currentColor" fill-opacity=".35"/>'
        for point in points
    )
    rules = "".join(
        f'<line x1="{across(radius):.1f}" y1="{pad}" x2="{across(radius):.1f}" '
        f'y2="{height - pad}" stroke="currentColor" stroke-opacity=".25" '
        f'stroke-dasharray="3 3"/>'
        f'<text x="{across(radius) + 3:.1f}" y="{pad - 6}" font-size="10" '
        f'fill="currentColor" fill-opacity=".6">r={radius}</text>'
        for radius in RADII
        if radius <= top
    )
    tau = (
        f'<line x1="{pad}" y1="{up(ceiling.TAU):.1f}" x2="{width - pad}" '
        f'y2="{up(ceiling.TAU):.1f}" stroke="crimson" stroke-opacity=".7"/>'
        f'<text x="{width - pad}" y="{up(ceiling.TAU) - 5:.1f}" font-size="10" '
        f'text-anchor="end" fill="crimson">twin test, tau={ceiling.TAU}</text>'
        if high >= ceiling.TAU
        else ""
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" '
        f'style="max-width:{width}px" role="img">'
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" '
        'stroke="currentColor" stroke-opacity=".5"/>'
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" '
        'stroke="currentColor" stroke-opacity=".5"/>'
        f"{rules}{dots}{tau}"
        f'<text x="{width / 2:.0f}" y="{height - 12}" font-size="11" text-anchor="middle" '
        'fill="currentColor">neutral descriptor distance (cosine)</text>'
        f'<text x="14" y="{height / 2:.0f}" font-size="11" text-anchor="middle" '
        f'fill="currentColor" transform="rotate(-90 14 {height / 2:.0f})">'
        "pixel-cloud W1 between the two coloured candidates</text>"
        "</svg>"
    )


# --------------------------------------------------------------------------- #
# The sheet.
# --------------------------------------------------------------------------- #
def sheet(record: dict, output: Path, shown: int = PAIRS_SHOWN) -> Path:
    """The near pairs at each candidate radius, ordered by distance, as pictures.

    **The instrument, and the only thing that decides a radius.** Each band shows
    the pairs a radius would refuse that the next one down would not, so a reader
    walks up the page until the two pictures in a row stop being one picture. The
    pictures are the *neutral* renders, because the radius is a statement about the
    places and not about how they turned out coloured.
    """
    from fractal_wallpapers.curation import sheet as sheet_module

    lines = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>near pairs by radius</title>",
        f"<style>{sheet_module.STYLE}"
        ".pair { display: grid; gap: .4rem; grid-template-columns: 1fr 1fr; }"
        "</style>",
        "<h1>near pairs, by candidate radius</h1>",
        f"<p class='lede'>{record['join']['embedded']:,} of {record['join']['asked']:,} "
        f"pool locations have a neutral descriptor. Nearest-neighbour distance: median "
        f"{record['nearest']['median']}, p10 {record['nearest']['p10']}, p90 "
        f"{record['nearest']['p90']}. <b>No radius is chosen here.</b> Walk up the page "
        "until the two pictures in a row stop being one picture; that is where the radius "
        "goes.</p>",
        _radius_table_html(record["radii"]),
        _premise_html(record.get("premise") or {}, record.get("twins") or {}),
    ]
    for band in record["bands"]:
        lines += [
            f"<h2>{band['low']} &le; distance &lt; {band['radius']} "
            f"({band['pairs']} pair(s), {min(shown, len(band['shown']))} shown)</h2>",
            "<div class='grid'>"
            + "".join(_pair_card(pair, sheet_module) for pair in band["shown"][:shown])
            + "</div>",
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output


def _premise_html(read: dict, swept: dict) -> str:
    """The premise on the same page as the radii it would decide.

    On the same page deliberately. A radius picked off the near-pair band without
    reading this is a radius picked for a rule that may not be the rule it is
    replacing, and the two questions have to be in front of a person together.
    """
    import html

    if "pearson" not in read:
        return ""
    lines = [
        "<h2>The premise: does far in the descriptor mean far in the pixels?</h2>",
        f"<p class='lede'>{read['pairs']:,} pair(s) over {read['places']:,} place(s), "
        f"stratified so the sample reaches the region a radius would sit in. Pearson "
        f"<b>{read['pearson']}</b>, Spearman <b>{read['spearman']}</b>. Each point is two "
        "places; across is how different the uncoloured renders are, up is how different "
        "the two coloured candidates a seating would have taken are. The premise wants the "
        "bottom-right corner empty.</p>",
        scatter(read),
    ]
    if swept.get("twin_pairs") is not None:
        rows = "".join(
            f"<tr><th>r = {html.escape(name)}</th>"
            f"<td>removes {row['twins_the_radius_removes']} of {swept['twin_pairs']}</td>"
            f"<td>{row['share_removed']:.1%}</td></tr>"
            for name, row in sorted(swept["removed_by_radius"].items(), key=lambda i: float(i[0]))
        )
        lines += [
            "<h2>What a radius would actually remove</h2>",
            f"<p class='lede'>Every twin pair in the pool, found exactly over "
            f"{swept['pairs_screened']:,} pairs — {swept['twin_pairs']:,} of them sit under "
            f"tau = {swept['tau']} in the pixel cloud. This is the table the design rests "
            "on: a radius that removes none of these does not replace the twin test, "
            "whatever the scatter looks like.</p>",
            f"<table>{rows}</table>",
        ]
    return "".join(lines)


def _radius_table_html(table: dict) -> str:
    import html

    body = "".join(
        f"<tr><th>{html.escape(name)}</th><td>{row['pairs']:,} pair(s)</td>"
        f"<td>{row['locations_in_a_near_pair']:,} location(s), "
        f"{row['share_of_the_pool']:.1%} of the pool</td></tr>"
        for name, row in sorted(table.items(), key=lambda item: float(item[0]))
    )
    return f"<h2>What each radius would call a duplicate</h2><table>{body}</table>"


def _pair_card(pair: dict, sheet_module) -> str:
    import html

    def picture(name):
        where = neutral.neutral_dir() / str(name)
        return (
            f'<img src="{sheet_module.thumbnail(where, width=320)}" alt="">'
            if where.is_file()
            else '<div class="missing">no neutral render</div>'
        )

    return (
        f"<figure><div class='pair'><div class='frame'>{picture(pair['a_picture'])}</div>"
        f"<div class='frame'>{picture(pair['b_picture'])}</div></div>"
        f"<figcaption><b>{pair['distance']:.4f}</b><ul>"
        f"<li>{html.escape(str(pair['a_partition']))} &middot; "
        f"{html.escape(str(pair['b_partition']))}</li>"
        f"<li>{html.escape(str(pair['a_picture']))} &middot; "
        f"{html.escape(str(pair['b_picture']))}</li>"
        "</ul></figcaption></figure>"
    )


def bands(keys, matrix, rows, radii=RADII, shown: int = PAIRS_SHOWN) -> list:
    """The near pairs split into the shells between consecutive radii.

    Shells rather than nested sets, because a page that showed every pair under
    0.10 after every pair under 0.07 would show the same pairs four times and bury
    the band the decision is actually in.
    """
    facts = {str(row["key"]): row for row in rows}
    ladder = sorted(float(radius) for radius in radii)
    out = []
    low = 0.0
    for radius in ladder:
        found = [pair for pair in near_pairs(keys, matrix, radius) if pair[2] >= low]
        out.append(
            {
                "low": round(low, 4),
                "radius": radius,
                "pairs": len(found),
                "shown": [
                    {
                        "a": one,
                        "b": other,
                        "distance": gap,
                        "a_picture": (facts.get(one) or {}).get("picture"),
                        "b_picture": (facts.get(other) or {}).get("picture"),
                        "a_partition": (facts.get(one) or {}).get("partition"),
                        "b_partition": (facts.get(other) or {}).get("partition"),
                    }
                    for one, other, gap in found[: int(shown)]
                ],
            }
        )
        low = radius
    return out


# --------------------------------------------------------------------------- #
# End to end.
# --------------------------------------------------------------------------- #
def read(
    locations, picture_of=None, pairs: int = PREMISE_PAIRS, sweep: bool = True, log=print
) -> dict:
    """The whole pre-selection read: the join, the distribution, the radii, the premise.

    `picture_of(key)` is what the premise check is measured on and the one thing
    this module needs that is not in the embedding store. Omitted, the premise is
    skipped and said to have been. `sweep` is the exact twin sweep beside the
    scatter: it costs one signature per picture and is the half of the premise
    check that actually decides the design, so it is on unless a caller says
    otherwise.
    """
    stored = embeddings.read()
    report = {
        "schema": SCHEMA,
        "taken_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "join": join(locations, stored),
    }
    keys, matrix = matrix_for(locations, stored)
    report["nearest"] = nearest(matrix)
    report["radii"] = radius_table(keys, matrix)
    report["bands"] = bands(keys, matrix, stored)
    report["premise"] = (
        {"skipped": "no picture_of was given, so nothing was measured"}
        if picture_of is None
        else premise(keys, matrix, picture_of, pairs=pairs, log=log)
    )
    report["twins"] = (
        {"skipped": "no picture_of was given, so nothing was measured"}
        if picture_of is None or not sweep
        else twins(keys, matrix, picture_of, log=log)
    )
    return report


def sheet_path(name: str) -> Path:
    """Where the near-pair sheet lands when the caller did not say."""
    from fractal_wallpapers.paths import under

    return under("curation", UNIT, str(name)) / "near_pairs.html"


def write_record(name: str, record: dict) -> Path:
    import json

    from fractal_wallpapers.paths import under

    path = under("curation", UNIT, str(name)) / "distinct.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


__all__ = [
    "METRIC",
    "PAIRS_SHOWN",
    "PLOT",
    "PREMISE_BANDS",
    "PREMISE_PAIRS",
    "PRESELECT_RADIUS",
    "RADII",
    "PAIR_MATRIX_LIMIT",
    "SCHEMA",
    "SEED",
    "UNIT",
    "DistinctRefused",
    "bands",
    "join",
    "ladder_for",
    "matrix_for",
    "near_pairs",
    "nearest",
    "premise",
    "preselect",
    "radius_table",
    "read",
    "scatter",
    "sheet",
    "sheet_path",
    "suppress",
    "twins",
    "write_record",
]
