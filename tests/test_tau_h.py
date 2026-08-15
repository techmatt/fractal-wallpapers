"""The cheap cut: one population, a stated quantile, and failing open.

The estimator is four lines. Everything worth testing is about which rows are
allowed into it and what happens when there are not enough of them.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.supply import tau_h
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS


def rows(partition: str, pairs) -> list[dict]:
    return [{"partition": partition, "cheap": c, "canonical": k} for c, k in pairs]


def test_the_cut_is_the_quantile_that_retains_the_asked_for_share() -> None:
    """Read it as: the cheap cut that keeps `keep` of the frames a full render
    would have kept."""
    population = rows("mandelbrot", [(i / 10, 0.9) for i in range(11)])
    cut, detail = tau_h.derive(population, ["mandelbrot"], keep=0.9)
    assert cut["mandelbrot"] == pytest.approx(0.1)
    assert detail["mandelbrot"]["source"] == "own"
    assert detail["mandelbrot"]["n_good"] == 11


def test_only_canonically_good_frames_are_in_the_population() -> None:
    """The cut is about which frames a full render would have kept, so a frame it
    would have thrown away says nothing about where to put the cut."""
    population = rows("mandelbrot", [(0.01, 0.1)] * 20 + [(0.8, 0.9)] * 5)
    cut, detail = tau_h.derive(population, ["mandelbrot"], keep=0.9)
    assert detail["mandelbrot"]["n_rows"] == 25
    assert detail["mandelbrot"]["n_good"] == 5
    assert cut["mandelbrot"] == pytest.approx(0.8)


def test_a_row_missing_either_arm_cannot_contribute() -> None:
    """A row with no canonical score cannot say whether it was good, and one with
    no cheap score cannot contribute to a cut on cheap scores."""
    population = rows("mandelbrot", [(0.5, None), (None, 0.9)] * 10)
    cut, detail = tau_h.derive(population, ["mandelbrot"])
    assert detail["mandelbrot"]["n_good"] == 0
    assert cut["mandelbrot"] == 0.0


def test_a_thin_partition_fails_open_rather_than_being_cut() -> None:
    """A cut that is too high sheds supply invisibly; one that is too low shows up
    as render minutes in the run's own telemetry. Only one of those is
    recoverable."""
    population = rows("phoenix", [(0.9, 0.9)] * (tau_h.MIN_N - 1))
    cut, detail = tau_h.derive(population, ["phoenix"])
    assert cut["phoenix"] == 0.0
    assert detail["phoenix"]["source"] == "fail-open"


def test_the_fail_open_boundary_is_exactly_min_n() -> None:
    at_the_line = rows("phoenix", [(0.9, 0.9)] * tau_h.MIN_N)
    cut, detail = tau_h.derive(at_the_line, ["phoenix"])
    assert detail["phoenix"]["source"] == "own"
    assert cut["phoenix"] == pytest.approx(0.9)


def test_a_missing_arm_is_never_filled_in_from_another_family() -> None:
    """A cut derived on other families' frames is a number about a population that
    is not this one, which is the same category error as serving one scorer's
    threshold to another scorer's gate."""
    population = rows("mandelbrot", [(0.7, 0.9)] * 50)
    cut, detail = tau_h.derive(population, ["mandelbrot", "phoenix"])
    assert cut["mandelbrot"] == pytest.approx(0.7)
    assert cut["phoenix"] == 0.0
    assert detail["phoenix"]["source"] == "fail-open"


def test_the_quantile_interpolates_between_order_statistics() -> None:
    """Written out rather than pulled from a library, because an estimator whose
    interpolation rule is whatever a dependency defaults to is an estimator nobody
    can reproduce."""
    assert tau_h.quantile([0.0, 1.0], 0.5) == pytest.approx(0.5)
    assert tau_h.quantile([0.0, 10.0], 0.1) == pytest.approx(1.0)
    assert tau_h.quantile([5.0], 0.9) == pytest.approx(5.0)


def test_the_shipped_state_is_what_this_repository_derives_today() -> None:
    """No scorer exists here yet, so every partition is at the fail-open value —
    and the file says so rather than being absent, because an absent table and a
    table of zeros read identically to a run."""
    shipped = tau_h.load()
    assert set(shipped) == set(ALL_PARTITIONS)
    assert set(shipped.values()) == {0.0}
    derived = tau_h.artifact([], ALL_PARTITIONS)
    assert derived["tau_h"] == shipped
    assert derived["state"] == "UNDERIVED"


def test_a_derivation_with_a_real_arm_says_it_is_derived() -> None:
    population = rows("mandelbrot", [(0.6, 0.9)] * 10)
    derived = tau_h.artifact(population, ALL_PARTITIONS)
    assert derived["state"] == "DERIVED"
    assert derived["detail"]["mandelbrot"]["source"] == "own"
    assert derived["detail"]["phoenix"]["source"] == "fail-open"
