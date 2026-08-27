"""The winner's curse read: which candidate gets re-read, and what the two curves are.

Arithmetic over records and no render, like [`test_depth`]. The property this
module exists for is one line of it: **both curves are reported over the same
locations and the same winners**, so the only thing that moves between the raw
column and the calibrated one is which reading of the winning picture is
believed. A test that let the two columns be computed over different
denominators would make the gap between them mean nothing, and the gap is the
whole finding.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import shrinkage


def row(location, k, p_ge4, arm="ranked_bands", band="band00", mode="smooth"):
    return {
        "key": f"{location}-{k}",
        "arm": arm,
        "band": band,
        "k": k,
        "location": location,
        "partition": "mandelbrot",
        "mode": mode,
        "colormap": "viridis",
        "p_ge4": p_ge4,
        "acted": False,
    }


# --------------------------------------------------------------------------- #
# Choosing the winner.
# --------------------------------------------------------------------------- #
def test_the_winner_at_each_checkpoint_is_the_best_of_the_first_k():
    rows = [row("p", 1, 0.20), row("p", 2, 0.80), row("p", 7, 0.95)]
    winners = {held["key"]: held["won_at"] for held in shrinkage.running_winners(rows, (1, 5, 10))}
    assert winners == {"p-1": [1], "p-2": [5], "p-7": [10]}


def test_one_candidate_that_wins_at_several_widths_is_re_rendered_once():
    """Most of the saving. A set whose best landed early wins at every later
    checkpoint, and rendering it five times would measure the same picture five
    times."""
    rows = [row("p", 1, 0.99), row("p", 2, 0.10), row("p", 9, 0.20)]
    winners = shrinkage.running_winners(rows, (1, 5, 10, 20, 40))
    assert len(winners) == 1
    assert winners[0]["won_at"] == [1, 5, 10, 20, 40]


def test_a_checkpoint_past_what_a_location_reached_takes_the_best_it_has():
    rows = [row("p", 1, 0.30), row("p", 2, 0.40)]
    winners = shrinkage.running_winners(rows, (1, 40))
    assert {held["key"] for held in winners} == {"p-1", "p-2"}


def test_the_sample_spreads_over_the_arms_and_over_the_bands_inside_one():
    sequence = []
    for arm in ("near_band", "ranked_bands", "flat"):
        for band in range(4):
            for place in range(3):
                key = f"{arm}-{band}-{place}"
                sequence += [row(key, k, 0.1 * k, arm=arm, band=f"band{band:02d}") for k in (1, 2)]
    picked = shrinkage.sample(sequence, per_arm=4, seed=1, checkpoints=(1, 2))
    by_arm: dict = {}
    for held in picked:
        by_arm.setdefault(held["arm"], set()).add(held["location"])
    assert set(by_arm) == {"near_band", "ranked_bands", "flat"}
    for arm, places in by_arm.items():
        assert len(places) == 4, arm
        assert len({place.split("-")[1] for place in places}) == 4, "one place per band"


# --------------------------------------------------------------------------- #
# The two curves.
# --------------------------------------------------------------------------- #
def paired(sequence, label):
    """The pairs file the re-read would have written, given a second reading."""
    out = []
    for held in sequence:
        if held["key"] in label:
            out.append(
                {
                    **held,
                    "won_at": [1],
                    "label_p_ge4": label[held["key"]],
                    "delta_p_ge4": label[held["key"]] - held["p_ge4"],
                    "acted_at_label_geometry": False,
                }
            )
    return out


def test_the_calibrated_curve_is_the_same_locations_read_the_other_way():
    sequence = [row("p", 1, 0.30), row("p", 2, 0.93), row("q", 1, 0.91), row("q", 2, 0.20)]
    pairs = paired(sequence, {"p-2": 0.61, "q-1": 0.88})
    out = shrinkage.curves(pairs, sequence, bars=(0.90,), checkpoints=(1, 2))
    at = out["ranked_bands"]["checkpoints"]
    assert at["1"]["bar_090"]["raw_primed"] == 1, "q clears on its first candidate"
    assert at["2"]["bar_090"]["raw_primed"] == 2
    assert at["2"]["bar_090"]["calibrated_primed"] == 0, "both winners fall under a re-read"
    assert at["2"]["locations"] == at["2"]["bar_090"]["raw_primed"] == 2


def test_the_two_columns_share_a_denominator():
    sequence = [row("p", 1, 0.95), row("q", 1, 0.10)]
    pairs = paired(sequence, {"p-1": 0.99, "q-1": 0.05})
    block = shrinkage.curves(pairs, sequence, bars=(0.90,), checkpoints=(1,))["ranked_bands"]
    held = block["checkpoints"]["1"]
    assert held["locations"] == 2
    assert held["bar_090"]["raw_rate"] == held["bar_090"]["calibrated_rate"] == 0.5


def test_the_drop_is_reported_against_the_width_the_winner_was_chosen_over():
    pairs = [
        {**row("p", 1, 0.90), "won_at": [1, 5], "label_p_ge4": 0.80, "delta_p_ge4": -0.10},
        {**row("q", 3, 0.95), "won_at": [5], "label_p_ge4": 0.75, "delta_p_ge4": -0.20},
    ]
    out = shrinkage.pooled(pairs, (1, 5))
    assert out["1"]["winners"] == 1 and out["1"]["mean_drop"] == pytest.approx(-0.10)
    assert out["5"]["winners"] == 2 and out["5"]["mean_drop"] == pytest.approx(-0.15)
    assert out["5"]["share_falling"] == 1.0


def test_a_candidate_the_re_render_refused_is_out_of_both_columns_and_not_a_zero():
    sequence = [row("p", 1, 0.95), row("q", 1, 0.95)]
    pairs = paired(sequence, {"p-1": 0.99})
    pairs.append({**sequence[1], "won_at": [1], "picture": None, "why": "refused"})
    held = shrinkage.curves(pairs, sequence, bars=(0.90,), checkpoints=(1,))["ranked_bands"]
    at = held["checkpoints"]["1"]
    assert at["locations"] == 2 and at["re_read"] == 1
    assert at["bar_090"]["raw_primed"] == 2 and at["bar_090"]["calibrated_primed"] == 1


def test_the_label_geometry_is_one_doubling_of_the_candidate_geometry():
    """The contrast the calibration sheet measured, and the size a person labels
    at. A read taken at any other size would not be the one the noise figure
    belongs to."""
    from fractal_wallpapers.curation import colorize

    assert list(shrinkage.LABEL_RESOLUTION) == [2 * side for side in colorize.RESOLUTION]
    assert shrinkage.LABEL_SUPERSAMPLE == colorize.SUPERSAMPLE
