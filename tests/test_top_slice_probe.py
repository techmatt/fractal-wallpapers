"""The top-slice probe's arithmetic: the deal, the targets, the interval, the geometry.

Everything here is arithmetic on small structures and stays in the fast lane. The
expensive halves of the module — the corpus scoring pass, the candidate-geometry
render and the fits — are covered by the pieces they stand on
(`tests/test_activations.py`, `tests/test_spiral_probe.py`,
`tests/test_render_grade.py`), and what is left is the part this module invented:
how a slice of a lineage deal becomes fold blocks, which rows each target is
asked of, what the bootstrap resamples, and that the candidate arm's job differs
from the label arm's in the geometry and in nothing else.
"""

from __future__ import annotations

import pytest

numpy = pytest.importorskip("numpy")

from fractal_wallpapers.models import spiral_probe, top_slice_probe  # noqa: E402


def a_row(key: str, tier: int, fold: int, group: int, p_ge4: float = 0.95) -> dict:
    return {
        "key": key,
        "kind": "smooth_render",
        "name": key,
        "tier": tier,
        "mode": "smooth",
        "batch": "a_batch",
        "place": f"place:{group}",
        "fold": fold,
        "group": group,
        "label_p_ge4": p_ge4,
    }


def a_population(count: int = 40) -> list[dict]:
    """Rows over five folds and twenty lineage groups, tiers spread over all four."""
    return [
        a_row(f"r{at:03d}", tier=(at % 4) + 1, fold=at % 5, group=at // 2) for at in range(count)
    ]


# --------------------------------------------------------------------------- #
# The deal.
# --------------------------------------------------------------------------- #
def test_the_blocks_partition_the_rows_exactly_once() -> None:
    """A held-out read is only held out if every row is in exactly one block.

    A row in two blocks is read twice by two different fits and a row in none is
    read at its initialised zero, which is a probability of one half quietly
    added to the population.
    """
    rows = a_population()
    blocks = top_slice_probe.blocks_of(rows)
    seen = numpy.concatenate(blocks)
    assert sorted(seen.tolist()) == list(range(len(rows)))


def test_a_fold_no_row_of_the_slice_landed_in_is_dropped_rather_than_empty() -> None:
    """An empty block divides by zero in every statistic downstream, so it is not
    passed on — but the folds that DO hold rows keep their own membership."""
    rows = [a_row(f"r{at}", tier=4, fold=at % 2, group=at) for at in range(8)]
    blocks = top_slice_probe.blocks_of(rows, folds=5)
    assert len(blocks) == 2
    assert sum(len(block) for block in blocks) == 8


def test_the_blocks_reach_the_fitter_as_the_deal_and_not_as_a_reshuffle() -> None:
    """[`spiral_probe.held_out`] takes the blocks it is given, unchanged.

    The whole point of the parameter is that a lineage deal survives into the
    fit; a `held_out` that re-dealt would read every row against a fold that may
    hold its own near-duplicate.
    """
    rng = numpy.random.default_rng(0)
    features = rng.normal(size=(40, 6))
    target = (features[:, 0] > 0).astype(float)
    blocks = [numpy.arange(0, 20), numpy.arange(20, 40)]
    first = spiral_probe.held_out(features, target, 1.0, blocks=blocks)
    again = spiral_probe.held_out(features, target, 1.0, blocks=blocks)
    dealt = spiral_probe.held_out(features, target, 1.0)
    assert numpy.array_equal(first, again), "one deal, one answer"
    assert not numpy.allclose(first, dealt), "the default deal is a different partition"


# --------------------------------------------------------------------------- #
# The targets.
# --------------------------------------------------------------------------- #
def test_the_fine_target_is_asked_only_of_the_rows_it_is_about() -> None:
    """`three_against_four` drops the ones and twos rather than scoring them zero.

    Leaving them in would let an arm earn its AUC by separating the handful of
    rows every column already separates, which is the opposite of the question.
    """
    rows = a_population()
    mask, values = top_slice_probe.targets_for(rows, "three_against_four")
    tiers = {row["tier"] for at, row in enumerate(rows) if mask[at]}
    assert tiers == {3, 4}
    assert values[mask].sum() == sum(1 for row in rows if row["tier"] == 4)


def test_the_coarse_target_keeps_the_whole_slice() -> None:
    rows = a_population()
    mask, values = top_slice_probe.targets_for(rows, "tier4")
    assert mask.all()
    assert values.sum() == sum(1 for row in rows if row["tier"] == 4)


def test_an_unknown_target_is_refused_rather_than_defaulted() -> None:
    with pytest.raises(top_slice_probe.ProbeRefused):
        top_slice_probe.targets_for(a_population(), "tier5")


# --------------------------------------------------------------------------- #
# The interval.
# --------------------------------------------------------------------------- #
def test_the_interval_resamples_lineage_groups_and_not_rows() -> None:
    """The unit is the claim, and the two units give different answers.

    One row per group is the row-wise bootstrap; every row in one group is a
    bootstrap that can only draw the whole corpus, so its interval collapses to a
    point. If those two came back the same, the grouping would not be reaching
    the resample at all.
    """
    rng = numpy.random.default_rng(1)
    target = numpy.repeat([0.0, 1.0], 60)
    score = target * 0.6 + rng.normal(size=120) * 0.4
    per_row = top_slice_probe.interval(target, score, numpy.arange(120), draws=400)
    one_group = top_slice_probe.interval(target, score, numpy.zeros(120), draws=400)
    assert per_row["lo"] < per_row["hi"], "resampling rows leaves a spread"
    assert one_group["lo"] == one_group["hi"], "one group can only be drawn whole"
    assert per_row["unit"] == "lineage group"


def test_a_draw_that_comes_back_one_class_is_skipped_and_counted() -> None:
    """`draws` is what was asked for; the record says how many resolved."""
    target = numpy.array([0.0] + [1.0] * 19)
    score = numpy.arange(20, dtype=float)
    reading = top_slice_probe.interval(target, score, numpy.arange(20), draws=200)
    assert 0 < reading["draws"] <= 200


# --------------------------------------------------------------------------- #
# The two geometries.
# --------------------------------------------------------------------------- #
def a_job() -> dict:
    return {
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": {"center_re": "-0.5", "center_im": "0.0", "width": "3.0"},
        "mode": "smooth",
        "mode_params": {},
        "curve": "linear",
        "colormap": "Nineties Dusk",
        "recipe": {
            "gamma": 1.0,
            "cycles": 1.0,
            "phase": 0.0,
            "reverse": False,
            "mirror": False,
            "transfer": {"kind": "value"},
            "rolloff": {"kind": "none"},
        },
        "render": {"resolution": [1280, 720], "supersample": 2, "maxiter": 512},
        "_head": "smooth_render",
    }


def test_the_candidate_job_moves_the_geometry_and_nothing_else() -> None:
    """One doubling down, and every other field byte for byte the label job's.

    This is what lets the two head arms be read as a geometry contrast: a recipe
    that drifted between them would make the difference between the arms a
    difference between two pictures rather than between two samplings of one.
    """
    from fractal_wallpapers.curation import colorize

    label = a_job()
    candidate = top_slice_probe.at_candidate_geometry(label)
    assert candidate["render"]["resolution"] == list(colorize.RESOLUTION)
    assert candidate["render"]["supersample"] == colorize.SUPERSAMPLE
    assert candidate["render"]["maxiter"] == label["render"]["maxiter"]
    assert {k: v for k, v in candidate.items() if k != "render"} == {
        k: v for k, v in label.items() if k != "render"
    }
    assert label["render"] == a_job()["render"], "the label job is not mutated"


def test_the_two_geometries_are_two_pictures_by_the_cache_s_own_name() -> None:
    """[`renders.job_name`] digests everything the engine is told, geometry with it.

    So the two jobs cannot collide on one file — which is the mechanical reason
    a candidate-geometry reading is not derivable from a label-geometry one, and
    the reason both are rendered.
    """
    from fractal_wallpapers.models import renders

    label = a_job()
    assert renders.job_name(label) != renders.job_name(top_slice_probe.at_candidate_geometry(label))


# --------------------------------------------------------------------------- #
# The surface.
# --------------------------------------------------------------------------- #
def test_the_concatenation_is_built_from_arms_that_exist() -> None:
    """The pair the concatenation reads is a named tuple rather than a slice of a
    dict, and a name in it that is not an arm would be a silent empty column."""
    assert set(top_slice_probe.HEAD_ARMS) <= set(top_slice_probe.ARMS)
    assert "both_heads" not in top_slice_probe.HEAD_ARMS


def test_the_slice_is_a_cut_on_the_label_geometry_reading() -> None:
    rows = [a_row("a", 4, 0, 0, 0.95), a_row("b", 3, 1, 1, 0.5), a_row("c", 4, 2, 2, 0.9)]
    assert [row["key"] for row in top_slice_probe.top_slice(rows)] == ["a", "c"]
    assert [row["key"] for row in top_slice_probe.top_slice(rows, cut=0.94)] == ["a"]


def test_an_unknown_arm_is_refused(tmp_path) -> None:
    with pytest.raises(top_slice_probe.ProbeRefused):
        top_slice_probe.arm_matrix("penultimate_of_something_else", a_population())
