"""The isotonic crossover that places a finished-render head's release floor.

The number it produces — 0.685 for the strange head — has been in
`curation.floors` since 2026-08-17 as four sentences of prose inside a `method`
string. `grep -rn isotonic --include=*.py` reached one assertion in the suite and
nothing else, so the one cut in this project that removes a finished picture was
the one nobody could re-derive. These tests are about the fit, which is stdlib
and needs no head; the fit against the real corpus is `head floor`, and it exits
non-zero when it does not reproduce the standing bar.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.models import release_floor


def points(pairs) -> list[tuple[float, float]]:
    return [(float(score), float(outcome)) for score, outcome in pairs]


# --------------------------------------------------------------------------- #
# Pool-adjacent-violators.
# --------------------------------------------------------------------------- #
def test_an_already_monotone_sequence_is_returned_unchanged() -> None:
    """The only assumption anybody is willing to make about a judge is that a
    higher score does not mean a worse picture. Where the data already says that,
    the fit says nothing more."""
    fitted = release_floor.isotonic(points([(0.1, 0.0), (0.2, 0.0), (0.3, 1.0), (0.4, 1.0)]))
    assert fitted == [(0.1, 0.0), (0.2, 0.0), (0.3, 1.0), (0.4, 1.0)]


def test_a_violation_is_pooled_into_its_block_mean() -> None:
    """Two adjacent points out of order become one block at their mean, which is
    the whole of PAVA and the reason the answer is unique."""
    fitted = release_floor.isotonic(points([(0.1, 1.0), (0.2, 0.0)]))
    assert fitted == [(0.1, 0.5), (0.2, 0.5)]

    # A violation merges backwards only as far as it has to: the trailing zero
    # pulls the two ones down to two thirds, and the leading zero is already
    # below that, so it keeps its own value.
    fitted = release_floor.isotonic(points([(0.1, 0.0), (0.2, 1.0), (0.3, 1.0), (0.4, 0.0)]))
    assert [round(value, 4) for _, value in fitted] == [0.0, 0.6667, 0.6667, 0.6667]

    # One that has to reach back further does.
    fitted = release_floor.isotonic(points([(0.1, 1.0), (0.2, 1.0), (0.3, 0.0), (0.4, 0.0)]))
    assert [round(value, 4) for _, value in fitted] == [0.5, 0.5, 0.5, 0.5]


def test_ties_in_the_score_are_pooled_before_the_pass() -> None:
    """Two pictures the head scored identically cannot be ordered by anything
    here, so leaving them adjacent and unpooled would let their input order
    decide where a block starts."""
    forwards = release_floor.isotonic(points([(0.5, 1.0), (0.5, 0.0), (0.6, 1.0)]))
    backwards = release_floor.isotonic(points([(0.5, 0.0), (0.5, 1.0), (0.6, 1.0)]))
    assert forwards == backwards == [(0.5, 0.5), (0.6, 1.0)]


def test_the_fitted_curve_never_decreases_on_noisy_input() -> None:
    import random

    draws = random.Random(7)
    noisy = points(
        (draws.random(), float(draws.random() < 0.3 + 0.5 * index / 200)) for index in range(200)
    )
    values = [value for _, value in release_floor.isotonic(noisy)]
    assert values == sorted(values)


def test_a_fit_over_nothing_refuses_rather_than_returning_a_number() -> None:
    with pytest.raises(release_floor.FloorFitError):
        release_floor.isotonic([])


# --------------------------------------------------------------------------- #
# The crossing, and which side of it a floor sits on.
# --------------------------------------------------------------------------- #
def test_the_crossing_is_the_lowest_score_that_reaches_a_half() -> None:
    """The lowest and not the nearest: the curve is non-decreasing, so a floor is
    the bottom of the passing region rather than a point somewhere inside it."""
    curve = [(0.1, 0.2), (0.3, 0.49), (0.4, 0.5), (0.9, 1.0)]
    assert release_floor.crossing(curve) == 0.4


def test_a_curve_that_never_reaches_a_half_has_no_crossing() -> None:
    assert release_floor.crossing([(0.1, 0.1), (0.9, 0.4)]) is None


def test_a_corpus_that_places_no_floor_refuses_rather_than_inventing_one() -> None:
    reading = {
        "head": "render",
        "kind": "strange_render",
        "head_sha256": "a" * 64,
        "classes": 4,
        "rows": [
            {"name": f"n{index}", "batch": "b", "label": 1, "place": "p", "p_ge3": index / 10}
            for index in range(10)
        ],
        "store": {"rows": 10, "superseded": 0},
    }
    with pytest.raises(release_floor.FloorFitError, match="never reaches"):
        release_floor.fit(reading, resamples=0)


# --------------------------------------------------------------------------- #
# The roundings, which are not symmetric.
# --------------------------------------------------------------------------- #
def test_a_floor_rounds_up_and_never_down() -> None:
    """A floor rounded down admits material the fit did not vouch for. The whole
    point of a floor is that everything under it is out."""
    assert release_floor.round_up(0.6801) == 0.681
    assert release_floor.round_up(0.6809) == 0.681
    assert release_floor.round_up(0.685) == 0.685, "an exact value is not pushed up a step"
    assert release_floor.round_up(0.68500001) == 0.686


def test_the_coarser_grid_the_standing_bar_was_rounded_on_is_reported_too() -> None:
    """0.6809 is 0.681 at three places and 0.685 on the 0.005 grid, and the
    standing bar is the second. A restatement compared across two grids says
    nothing, so the record carries both."""
    assert release_floor.round_up_to_grid(0.6809) == 0.685
    assert release_floor.round_up(0.6809) == 0.681
    assert release_floor.round_up_to_grid(0.685) == 0.685
    assert release_floor.round_up_to_grid(0.6851) == 0.69


# --------------------------------------------------------------------------- #
# The interval, clustered on the place.
# --------------------------------------------------------------------------- #
def test_the_bootstrap_resamples_places_and_not_pictures() -> None:
    """One location appears in these corpora many times at many recipes. Treating
    those as independent draws reports an interval several times too narrow and
    makes a bar look far better pinned than it is."""
    # Ten places, each contributing twenty near-identical pictures.
    clustered = [
        (0.2 + 0.05 * place, float(place >= 5), f"place{place}")
        for place in range(10)
        for _ in range(20)
    ]
    interval = release_floor.bootstrap(clustered, resamples=200)
    assert interval["resamples"] > 0
    assert interval["low"] <= interval["high"]

    # Same rows, every picture its own place: the interval collapses, which is
    # exactly the false precision the clustering exists to avoid.
    unclustered = [
        (score, outcome, f"{index}") for index, (score, outcome, _) in enumerate(clustered)
    ]
    tight = release_floor.bootstrap(unclustered, resamples=200)
    assert (tight["high"] - tight["low"]) <= (interval["high"] - interval["low"])


def test_the_bootstrap_is_seeded_and_repeats() -> None:
    rows = [(0.1 * index, float(index > 4), f"p{index % 3}") for index in range(20)]
    assert release_floor.bootstrap(rows, resamples=50) == release_floor.bootstrap(
        rows, resamples=50
    )


# --------------------------------------------------------------------------- #
# The record, and what it has to carry to be re-derivable.
# --------------------------------------------------------------------------- #
def separable(kind: str = "strange_render") -> dict:
    """A reading whose judge agrees with its labels above 0.5 and not below."""
    return {
        "head": "render",
        "kind": kind,
        "head_sha256": "b" * 64,
        "classes": 4,
        "rows": [
            {
                "name": f"n{index}",
                "batch": "b",
                "label": 4 if index >= 50 else 1,
                "place": f"place{index % 10}",
                "p_ge3": index / 100,
            }
            for index in range(100)
        ],
        "store": {"rows": 100, "superseded": 0},
    }


def test_the_record_carries_the_head_the_population_and_a_hash_of_both_inputs() -> None:
    """A floor is only as re-derivable as its inputs. Neither of them is tracked
    at full size — the pictures are regenerated from the rows and the scores are a
    function of the artifact — so the hashes are what say which rows and which
    artifact produced this number."""
    record = release_floor.fit(separable(), resamples=0)

    assert record["value"] == release_floor.round_up(record["crossing"])
    assert record["head_sha256"] == "b" * 64
    assert record["population"]["pictures"] == 100
    assert record["population"]["places"] == 10
    assert record["population"]["keepers"] == 50
    assert len(record["inputs"]["labels_sha256"]) == 64
    assert len(record["inputs"]["scores_sha256"]) == 64
    assert "isotonic" in record["method"].lower()
    assert record["reference_pool"].startswith("all 100 labeled")


def test_the_hashes_move_with_the_labels_and_with_the_scores_separately() -> None:
    """Two inputs, two hashes: a corpus that gained a verdict and a head that was
    re-shipped are different reasons for a floor to move."""
    base = release_floor.fit(separable(), resamples=0)["inputs"]

    relabeled = separable()
    relabeled["rows"][0]["label"] = 4
    moved_labels = release_floor.fit(relabeled, resamples=0)["inputs"]
    assert moved_labels["labels_sha256"] != base["labels_sha256"]
    assert moved_labels["scores_sha256"] == base["scores_sha256"]

    reshipped = separable()
    reshipped["rows"][0]["p_ge3"] = 0.999
    moved_scores = release_floor.fit(reshipped, resamples=0)["inputs"]
    assert moved_scores["scores_sha256"] != base["scores_sha256"]
    assert moved_scores["labels_sha256"] == base["labels_sha256"]


def test_the_keeper_tier_is_three_and_the_crossing_is_a_half() -> None:
    """Both are the fit's whole content and both are decisions. `>=3` is what the
    heads' P(>=3) cutpoint is about, and a half is where a judge stops being wrong
    about this material more often than it is right."""
    assert release_floor.KEEPER_TIER == 3
    assert release_floor.CROSSING == 0.5


def test_the_fit_returns_a_reading_and_moves_no_cut() -> None:
    """`curation.floors` is the only owner of a height that acts. This is a
    measurement, and putting it there is somebody's decision afterwards."""
    from fractal_wallpapers.curation import floors

    before = floors.STRANGE_RELEASE_BAR.value
    release_floor.fit(separable(), resamples=0)
    assert floors.STRANGE_RELEASE_BAR.value == before


# --------------------------------------------------------------------------- #
# The two heights this repository has measured, as they stand.
# --------------------------------------------------------------------------- #
def test_the_committed_records_agree_with_the_heights_in_floors() -> None:
    """A `Restatement` in `curation.floors` and the record `head floor` wrote are
    two statements of one number. They are checked against each other because the
    failure they guard is exactly what happened to the strange bar: the fit lived
    only as prose, so nothing could tell whether the float still matched it."""
    import json

    from fractal_wallpapers.curation import floors

    for kind, restated in floors.MEASURED_RELEASE_FLOORS.items():
        path = release_floor.record_path(kind)
        if not path.is_file():
            pytest.skip(f"{kind} has not been fitted in this checkout")
        record = json.loads(path.read_text(encoding="utf-8"))
        # The corpus is the KIND's and the scale is the one judge's. Both are on
        # the record because since 2026-08-23 they are different names.
        assert record["kind"] == kind
        assert record["head"] == floors.SCORING_HEAD
        assert record["head_sha256"] == restated.head_sha256
        # The declared height is the 0.005 rounding, for every head. The strange
        # bar was set on that grid before the command existed; the smooth floor
        # was ruled onto it on 2026-08-22 so the two can be read against each
        # other. A floor that reads the three-place rounding is on its own grid.
        assert restated.value == record["rounded_up_to_0_005"], kind


def test_the_strange_bar_reproduces_on_the_scale_it_is_stamped_with() -> None:
    """Re-fitted again at the 2026-08-24 flip: 0.573085 on the enlarged-corpus
    judge's scale, 0.575 on the 0.005 grid, against 0.618078/0.620 on the artifact
    it replaced. THAT it acts is unchanged and is the 2026-08-17 ruling; the height
    moved, which is what a re-fit is for.

    **Both causes are named, because both moved it.** The same fit on the retired
    artifact over this same grown store crosses 0.614688 — so 0.005 of the drop is
    the 237 rows the manufactured batch added and the rest is the scale. A method
    that claimed all of it for the scale would be wrong about a number somebody
    will restate again.
    """
    import json

    from fractal_wallpapers.curation import floors

    path = release_floor.record_path("strange_render")
    if not path.is_file():
        pytest.skip("the strange head has not been fitted in this checkout")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["rounded_up_to_0_005"] == floors.STRANGE_RELEASE_BAR.value == 0.575
    assert "0.573085" in floors.STRANGE_RELEASE_BAR.method
    assert "0.614688" in floors.STRANGE_RELEASE_BAR.method, "the corpus half of the move"
    assert abs(record["crossing"] - 0.573085) < 0.0005
    assert floors.STRANGE_RELEASE_BAR.head_sha256 == record["head_sha256"]


def test_the_smooth_floor_is_recorded_and_does_not_gate() -> None:
    """A measured height and an acting one are different things, and
    `ACTING_RELEASE_BARS` is the single place that says which a head has."""
    from fractal_wallpapers.curation import floors

    assert floors.SMOOTH_RELEASE_FLOOR.value == 0.540
    assert "smooth_render" not in floors.ACTING_RELEASE_BARS
    assert "smooth_render" in floors.MEASURED_RELEASE_FLOORS
    assert floors.release_bar("smooth_render") is None
    assert floors.release_cut("smooth_render").value == floors.RELEASE_ADVISORY

    banner = floors.summary()["advisory"]
    assert banner["measured_but_not_acting"]["smooth_render"]["value"] == 0.540
    assert "strange_render" not in banner["measured_but_not_acting"]
