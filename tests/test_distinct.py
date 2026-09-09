"""The neutral pre-selection: the join, the distances, and the premise it rests on.

Synthetic unit vectors, because everything this module does above the premise
check is arithmetic over descriptors: a join is a set difference, a
nearest-neighbour read is a matrix multiply, and a band ladder is a list of
numbers. The premise check is the one part that opens pictures, and the shape of
its output is pinned here while the measurement itself belongs to the slow lane.

The band ladder gets the most attention, and it is not fussiness. The first
attempt at the premise check banded equal-width over the store's own spread and
drew 562 pairs whose *minimum* neutral distance was 0.021 — so the region every
candidate radius sits in was not measured at all, and the correlation that came
back was a correlation about the wrong pairs.
"""

from __future__ import annotations

from pathlib import Path

import numpy
import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import ceiling, distinct


def unit(*values):
    made = numpy.asarray(values, dtype=numpy.float32)
    return made / numpy.linalg.norm(made)


def ring(count: int, spread: float = 1.0):
    """`count` unit vectors on an arc, so their pairwise distances are known and
    ordered: neighbours are close and the ends are far."""
    angles = numpy.linspace(0.0, spread, count, dtype=numpy.float32)
    return numpy.stack([numpy.cos(angles), numpy.sin(angles)], axis=1).astype(numpy.float32)


def store(keys):
    return [{"key": str(key), "partition": "mandelbrot", "picture": f"{key}.jpg"} for key in keys]


# --------------------------------------------------------------------------- #
# The pre-selection walk.
# --------------------------------------------------------------------------- #
def legacy_suppress(order, radius, rows):
    """The walk as it was spelled before the contiguous block: a fancy index per row.

    Kept here and nowhere else, because the claim the change rests on is that two
    BLAS calls over the same float32 values return the same bytes. That is a claim
    about a kernel, and a kernel picks by shape and stride — so it is checked
    against the retired spelling rather than asserted in a comment.
    """
    radius = float(radius)
    order = [str(key) for key in order]
    keys, matrix = distinct.matrix_for(order, rows)
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


def embedded(matrix):
    """A neutral-embedding store carrying one descriptor per place, in key order."""
    from fractal_wallpapers.curation import embeddings

    return [{"key": f"p{at:04d}", "vector": embeddings.pack(row)} for at, row in enumerate(matrix)]


@pytest.mark.parametrize("radius", [0.002, 0.02, 0.2])
def test_the_contiguous_block_walks_exactly_the_walk_the_fancy_index_walked(radius):
    """The whole of the pre-selection change: same kept set, same refusals, same
    distances to the recorded digit, same place named as having taken each one."""
    rng = numpy.random.default_rng(7)
    raw = rng.standard_normal((320, 384)).astype(numpy.float32)
    matrix = raw / numpy.linalg.norm(raw, axis=1, keepdims=True)
    # A third of the places are near-duplicates of an earlier one, so the walk has
    # refusals to make rather than keeping everything it is offered.
    for at in range(0, 320, 3):
        matrix[at] = matrix[max(0, at - 1)] + 0.01 * matrix[at]
        matrix[at] /= numpy.linalg.norm(matrix[at])
    rows = embedded(matrix)
    order = [row["key"] for row in rows]

    mine = distinct.suppress(order, radius=radius, rows=rows)
    theirs = legacy_suppress(order, radius, rows)
    assert mine["kept"] == theirs["kept"]
    assert mine["refused"] == theirs["refused"]
    assert mine["unembedded"] == theirs["unembedded"]
    assert 0 < len(mine["refused"]) < len(order), "the walk has to actually refuse things"


def test_a_place_with_no_descriptor_is_kept_and_never_enters_the_block():
    """The block is sized by the descriptors and walked by the offer order, so a
    place the store has never seen must not consume a row of it."""
    rows = embedded(ring(3, spread=2.0))
    order = [*(row["key"] for row in rows), "no_descriptor"]
    answer = distinct.suppress(order, radius=0.02, rows=rows)
    assert answer["unembedded"] == ["no_descriptor"]
    assert "no_descriptor" in answer["kept"]


# --------------------------------------------------------------------------- #
# Which place a fold keeps.
#
# The walk order IS the rule about which place represents a near-cluster, and the
# fold is a deletion: the absorbed place and every row it carries leave the pass.
# Nothing here pinned that order until 2026-09-09, which is why moving the key
# from raw `P(>=4)` to the fine head's `p_fine` ran green over every guard in this
# file and in `test_solve.py`. These are the guards that pin it.
# --------------------------------------------------------------------------- #
def store_of(angles: dict) -> list:
    """A neutral store placing each named location on the unit circle, so a pair's
    distance is `1 - cos(a - b)` and a test can state it in one number."""
    import math

    from fractal_wallpapers.curation import embeddings

    return [
        {"key": key, "vector": embeddings.pack([math.cos(angle), math.sin(angle)])}
        for key, angle in angles.items()
    ]


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


# cos(0.1) is 0.995, so a pair an angle of 0.1 apart sits at 0.005 — inside the
# 0.02 radius, and one of the two has to go.
A_NEAR_PAIR = {"a": 0.0, "b": 0.1}


def test_the_fold_keeps_the_place_the_fine_head_reads_higher():
    """The key change itself. `a` is the stronger row on the judge's raw column and
    `b` on the head the seating actually orders by, and `b` is the one a seating
    would have reached for — so `b` is the one the fold keeps."""
    kept, record = distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.90)],
        rows=store_of(A_NEAR_PAIR),
        fine={"a": 0.10, "b": 0.80},
        log=quiet,
    )
    assert {held.key for held in kept} == {"b"}
    assert record["refusals"][0]["location"] == "a"
    assert record["refusals"][0]["lost_to"] == "b"
    assert record["key"] == distinct.FINE_KEY


def test_the_same_pool_on_the_coarse_key_keeps_the_other_place_and_names_it():
    """The other half of the same claim: this is a real disagreement and not a
    tie broken differently. A record that folded on the old key says so."""
    kept, record = distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.90)],
        rows=store_of(A_NEAR_PAIR),
        fine={},
        log=quiet,
    )
    assert {held.key for held in kept} == {"a"}
    assert record["key"] == distinct.COARSE_KEY
    assert record["ordered_on"] == {distinct.FINE_KEY: 0, distinct.COARSE_KEY: 2}


def test_a_place_the_head_has_read_is_offered_ahead_of_one_it_has_not():
    """The two scales are stacked and never mixed. `b` reads 0.05 on the fine head
    and 0.10 on the judge, `a` reads 0.99 on the judge and nothing on the head —
    and `b` still takes the cluster, because unknown never outranks measured."""
    kept, record = distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.10)],
        rows=store_of(A_NEAR_PAIR),
        fine={"b": 0.05},
        log=quiet,
    )
    assert {held.key for held in kept} == {"b"}
    assert record["ordered_on"] == {distinct.FINE_KEY: 1, distinct.COARSE_KEY: 1}
    assert record["places_on_the_fallback"] == 1
    assert record["key"] == "both"
    lost = record["refusals"][0]
    assert lost["location"] == "a"
    assert lost["ordered_on"] == distinct.COARSE_KEY
    assert lost["p_fine"] is None, "a place the head never read carries no substituted value"
    assert lost["lost_to_p_fine"] == 0.05


def test_a_place_is_represented_by_its_strongest_row_on_the_fine_key():
    """Which row stands for a place moves with the key as well as which place
    stands for a cluster. `a1` is the place's best on the judge's column and `a2`
    on the head's, and it is `a2`'s reading the fold is decided on."""
    pool = [
        candidate("a1", location="a", score=0.99),
        candidate("a2", location="a", score=0.50),
        candidate("b1", location="b", score=0.10),
    ]
    _kept, record = distinct.preselect(
        pool,
        rows=store_of(A_NEAR_PAIR),
        fine={"a1": 0.10, "a2": 0.80, "b1": 0.95},
        log=quiet,
    )
    lost = record["refusals"][0]
    assert lost["location"] == "a"
    assert (lost["p_fine"], lost["p_ge4"]) == (0.8, 0.5)
    assert lost["ordered_on"] == distinct.FINE_KEY
    assert lost["lost_to_p_fine"] == 0.95


def test_the_walk_reads_the_heads_pool_scores_when_nobody_hands_it_a_column(monkeypatch):
    """It runs on passes where `solve.at_fine_bar` never did — an unbarred solve, a
    themed pass on the relaxed crossing — so it resolves the column itself rather
    than degrading to the coarse key in silence."""
    from fractal_wallpapers.models import gallery_grade_train

    monkeypatch.setattr(
        gallery_grade_train,
        "read_pool_scores",
        lambda *_args, **_rest: {"a": {"p_ge4": 0.10}, "b": {"p_ge4": 0.80}},
    )
    kept, record = distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.90)],
        rows=store_of(A_NEAR_PAIR),
        log=quiet,
    )
    assert {held.key for held in kept} == {"b"}
    assert record["fine_readings_held"] == 2


def test_a_walk_where_every_place_fell_back_says_so_in_a_line():
    """A pass with no fine reading anywhere must not read as a pass that used the
    new key, so the fallback is a line of its own and not an absent one."""
    said: list = []
    distinct.preselect(
        [candidate("a", score=0.99), candidate("b", score=0.90)],
        rows=store_of(A_NEAR_PAIR),
        fine={},
        log=said.append,
    )
    assert any(f"NO place carries a {distinct.FINE_KEY}" in line for line in said)


# --------------------------------------------------------------------------- #
# The join, reported first.
# --------------------------------------------------------------------------- #
def test_the_join_counts_what_the_store_cannot_see():
    read = distinct.join(["a", "b", "c"], store(["a", "b", "z"]))
    assert read["asked"] == 3
    assert read["embedded"] == 2
    assert read["unembedded"] == 1
    assert read["missing"] == ["c"]


def test_the_join_names_the_locations_it_could_not_see():
    # Named and not merely counted: a caller that has to decide what to do with
    # them needs the keys, and a count alone makes the decision unmakeable.
    read = distinct.join(["a", "b"], store(["a"]))
    assert read["missing"] == ["b"]


def test_a_store_larger_than_the_population_is_not_a_lossy_join():
    read = distinct.join(["a"], store(["a", "b", "c"]))
    assert read["share_embedded"] == 1.0
    assert read["stored_locations"] == 3


# --------------------------------------------------------------------------- #
# How far apart the places are.
# --------------------------------------------------------------------------- #
def test_the_nearest_neighbour_read_is_over_other_points_and_not_the_point_itself():
    read = distinct.nearest(ring(8, spread=1.0))
    assert read["min"] > 0.0
    assert read["points"] == 8


def test_two_identical_descriptors_are_at_distance_zero_from_each_other():
    matrix = numpy.stack([unit(1.0, 0.0), unit(1.0, 0.0), unit(0.0, 1.0)])
    assert distinct.nearest(matrix)["min"] == pytest.approx(0.0, abs=1e-6)


def test_the_under_counts_say_how_much_of_the_pool_each_radius_touches():
    read = distinct.nearest(ring(40, spread=1.0))
    counts = [read["under"][str(radius)] for radius in distinct.RADII]
    assert counts == sorted(counts)


def test_near_pairs_come_back_nearest_first_and_each_pair_once():
    keys = [f"k{at}" for at in range(12)]
    found = distinct.near_pairs(keys, ring(12, spread=1.0), 0.05)
    assert [pair[2] for pair in found] == sorted(pair[2] for pair in found)
    assert len({tuple(sorted(pair[:2])) for pair in found}) == len(found)


def test_a_radius_table_grows_with_the_radius():
    keys = [f"k{at}" for at in range(24)]
    table = distinct.radius_table(keys, ring(24, spread=1.0))
    counts = [table[str(radius)]["pairs"] for radius in distinct.RADII]
    assert counts == sorted(counts)


def test_the_bands_are_shells_so_a_pair_is_shown_once():
    keys = [f"k{at}" for at in range(24)]
    matrix = ring(24, spread=1.0)
    shown = distinct.bands(keys, matrix, store(keys))
    seen = [(row["a"], row["b"]) for band in shown for row in band["shown"]]
    assert len(seen) == len(set(seen))


def test_each_band_runs_from_the_radius_below_it():
    shown = distinct.bands([f"k{at}" for at in range(8)], ring(8), store(range(8)))
    assert [band["low"] for band in shown] == [0.0, *sorted(distinct.RADII)[:-1]]


# --------------------------------------------------------------------------- #
# The band ladder the premise sample is drawn over.
# --------------------------------------------------------------------------- #
def test_every_candidate_radius_is_a_band_edge():
    edges = distinct.ladder_for(0.8, distinct.PREMISE_BANDS)
    assert set(distinct.RADII) <= set(edges)


def test_the_ladder_starts_at_zero_so_the_decision_region_has_its_own_bands():
    edges = distinct.ladder_for(0.8, distinct.PREMISE_BANDS)
    assert edges[0] == 0.0
    assert edges[1] == min(distinct.RADII)


def test_the_ladder_reaches_the_top_of_the_observed_range():
    edges = distinct.ladder_for(0.8, distinct.PREMISE_BANDS)
    assert edges[-1] == pytest.approx(0.8)


def test_the_ladder_rises():
    edges = distinct.ladder_for(0.8, distinct.PREMISE_BANDS)
    assert edges == sorted(edges)


def test_an_equal_width_ladder_would_have_missed_the_decision_region():
    # The failure that produced this ladder, written down as arithmetic. Ten
    # equal-width bands over a range that reaches 0.8 give the whole decision
    # region — everything below the largest candidate radius — two bands out of
    # ten, and the smallest three radii share the first one. This ladder gives
    # that same region four edges.
    width = 0.8 / distinct.PREMISE_BANDS
    equal_width = len({int(radius / width) for radius in distinct.RADII})
    edges = distinct.ladder_for(0.8, distinct.PREMISE_BANDS)
    assert equal_width == 2
    assert len([edge for edge in edges if edge <= max(distinct.RADII)]) == 5


# --------------------------------------------------------------------------- #
# What the premise check is allowed to claim.
# --------------------------------------------------------------------------- #
def test_the_premise_refuses_a_population_with_no_pictures():
    keys = [f"k{at}" for at in range(8)]
    with pytest.raises(distinct.DistinctRefused):
        distinct.premise(keys, ring(8), lambda _key: None, log=lambda *_: None)


def test_the_stratified_draw_refuses_a_population_it_cannot_hold_the_matrix_for():
    with pytest.raises(distinct.DistinctRefused, match="exact matrix"):
        distinct._stratified(list(range(distinct.PAIR_MATRIX_LIMIT + 1)), ring(4), 10, 4, None)


def test_a_radius_removes_a_twin_pair_only_when_the_pair_is_near_in_the_descriptor():
    found = [
        {"neutral": 0.01, "pixel_cloud": 0.001},
        {"neutral": 0.50, "pixel_cloud": 0.001},
    ]
    assert distinct._removed(found, 0.02)["twins_the_radius_removes"] == 1
    assert distinct._removed(found, 0.02)["twins_it_admits"] == 1


def test_the_leakage_read_is_against_the_twin_threshold_and_not_the_radius():
    points = [
        {"neutral": 0.30, "pixel_cloud": ceiling.TAU - 0.001},
        {"neutral": 0.30, "pixel_cloud": ceiling.TAU + 0.001},
    ]
    read = distinct._leakage(points)
    assert read["tau"] == ceiling.TAU
    assert read["by_radius"]["0.02"]["twins_among_them"] == 1


def test_the_scatter_carries_both_correlations():
    # Pearson and Spearman together on purpose: a design that only needs `far in
    # one implies far in the other` is asking whether the relationship is
    # monotone, which is the second of the two.
    xs = numpy.array([0.1, 0.2, 0.3, 0.4])
    assert distinct._ranked(xs).tolist() == [0.0, 1.0, 2.0, 3.0]


# --------------------------------------------------------------------------- #
# No radius is chosen here.
# --------------------------------------------------------------------------- #
def test_the_module_exports_a_set_of_candidates_and_never_a_setting():
    # The guard on the ruling: this module reports and does not decide. A future
    # edit that promoted one of the candidates to `RADIUS` and had the seating
    # read it would fail here, which is where somebody would notice.
    assert len(distinct.RADII) >= 3
    assert "RADIUS" not in distinct.__all__
    assert not hasattr(distinct, "RADIUS")


# --------------------------------------------------------------------------- #
# The tracked store. Real descriptors, real pictures, the real bound.
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def tracked_places(tracked_ledger):
    """A small slice of the real pool: keys, descriptors, and a picture each.

    Small on purpose. The guard is that the bound is **sound** on real material
    and that the join and the sweep agree about the same population — not that a
    particular number comes back — and forty places is nine hundred pairs, which
    is enough for the bound to settle most of them and for at least a few to be
    measured.

    The pool itself is the session's one reading; see `conftest.tracked_ledger`.
    """
    from fractal_wallpapers.curation import embeddings, headroom
    from fractal_wallpapers.paths import rehome

    if not embeddings.store_path().is_file():
        pytest.skip("the neutral embedding store is not on this machine")
    best: dict = {}
    for held in sorted(headroom.clearing(tracked_ledger.pool), key=lambda c: (-c.score, c.key)):
        best.setdefault(held.location, held)
    keys, matrix = distinct.matrix_for(sorted(best)[:40])
    if len(keys) < 8:
        pytest.skip("too few embedded places in the pool to test the sweep on")

    def picture_of(key):
        held = best.get(key)
        where = None if held is None else Path(rehome(held.picture))
        return where if where is not None and where.is_file() else None

    return keys, matrix, picture_of


@pytest.mark.slow
def test_the_pool_joins_onto_the_neutral_store(tracked_places):
    """The join the whole pre-selection stands on, over the real store."""
    keys, _matrix, _picture_of = tracked_places
    read = distinct.join(keys)
    assert read["unembedded"] == 0
    assert read["embedded"] == len(keys)


@pytest.mark.slow
def test_the_twin_sweeps_bound_never_settles_a_real_twin(tracked_places):
    """**The soundness guard.** A prune is only as good as its argument, and this
    project has shipped one whose premise was false.

    The bound settles a pair by proving it at or beyond `tau`, so every pair it
    settles has to be genuinely at or beyond `tau` when measured exactly. Checked
    by measuring the pairs the sweep *did not* report and finding none of them
    under the threshold.
    """
    from fractal_wallpapers.palettes import pixel_clouds

    keys, matrix, picture_of = tracked_places
    swept = distinct.twins(keys, matrix, picture_of, log=lambda *_: None)
    found = {tuple(sorted((pair["a"], pair["b"]))) for pair in swept["pairs"]}
    signatures = {key: pixel_clouds.of_picture(picture_of(key)) for key in keys}
    missed = [
        (one, other)
        for at, one in enumerate(keys)
        for other in keys[at + 1 :]
        if tuple(sorted((one, other))) not in found
        and pixel_clouds.distance(signatures[one], signatures[other]) < swept["tau"]
    ]
    assert missed == []
    assert swept["pairs_screened"] == len(keys) * (len(keys) - 1) // 2


@pytest.mark.slow
def test_the_premise_check_measures_the_coloured_pictures_and_not_the_neutral_ones(
    tracked_places,
):
    """What the scatter is *of*. The claim under test is about the coloured
    candidates a seating would take, so a check run on the neutral renders would
    be a check of the descriptor against itself."""
    keys, matrix, picture_of = tracked_places
    read = distinct.premise(keys, matrix, picture_of, pairs=40, log=lambda *_: None)
    assert read["pairs"] > 0
    assert -1.0 <= read["pearson"] <= 1.0
    assert "sliced Wasserstein-1 between two pictures" in read["pixel_cloud_metric"]
    assert distinct.scatter(read).startswith("<svg")
