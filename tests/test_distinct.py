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
def tracked_places():
    """A small slice of the real pool: keys, descriptors, and a picture each.

    Small on purpose. The guard is that the bound is **sound** on real material
    and that the join and the sweep agree about the same population — not that a
    particular number comes back — and forty places is nine hundred pairs, which
    is enough for the bound to settle most of them and for at least a few to be
    measured.
    """
    from fractal_wallpapers.curation import candidate_ledger, embeddings, headroom
    from fractal_wallpapers.paths import rehome

    if not candidate_ledger.rows_path().is_file():
        pytest.skip("the candidate ledger has not been backfilled on this machine")
    if not embeddings.store_path().is_file():
        pytest.skip("the neutral embedding store is not on this machine")
    candidates, _costs, _refused = headroom.population(log=lambda *_: None)
    best: dict = {}
    for candidate in sorted(headroom.clearing(candidates), key=lambda c: (-c.score, c.key)):
        best.setdefault(candidate.location, candidate)
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
