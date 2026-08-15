"""Cross-run memory: exact where it claims to be, and blind where it must be.

The index is an acceleration of a definition, so it is pinned against that
definition rather than against a second implementation of itself. Everything else
here is about the two ways a memory like this goes wrong: discounting places
nothing has actually visited twice, and firing on so much of the population that
it reorders nothing.
"""

from __future__ import annotations

import json
import random

import pytest

from fractal_wallpapers.supply import saturation
from fractal_wallpapers.supply.saturation import VisitedIndex

JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
OTHER_JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}
MANDELBROT = {"kind": "mandelbrot"}


def visit(family: dict, re: str, im: str, width: str, fate: str = "survived") -> dict:
    return {
        "schema": 1,
        "kind": "candidate",
        "fate": fate,
        "score": None,
        "family": family,
        "viewport": {"center_re": re, "center_im": im, "width": width},
    }


def write(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_the_index_is_exact_against_the_definition_it_accelerates() -> None:
    """The three-by-three scan is exact rather than approximate: a visit's radius
    is bounded by its octave's cell size, so a covering disc's centre cannot lie
    outside the block around the query point."""
    rng = random.Random(20260814)
    index = VisitedIndex(0.3)
    for _ in range(400):
        index.add(
            "mandelbrot",
            (),
            rng.uniform(-2, 2),
            rng.uniform(-2, 2),
            10 ** rng.uniform(-4, 0),
        )
    for _ in range(200):
        x, y = rng.uniform(-2, 2), rng.uniform(-2, 2)
        assert index.density("mandelbrot", (), x, y) == index.density_scanned(
            "mandelbrot", (), x, y
        )


def test_two_dynamical_views_at_one_place_with_different_parameters_do_not_shadow() -> None:
    """Inside a Julia partition the coordinate is a point of the dynamical plane,
    so two views at the same place with different parameters are different
    fractals. An index blind to that discounts channels nothing has visited
    twice — which are exactly the channels the next run exists to serve."""
    index = VisitedIndex(0.3)
    index.add_row(visit(JULIA, "0.0", "0.0", "1.0"))
    at = ("julia:mandelbrot", saturation.identity_of(OTHER_JULIA), 0.0, 0.0)
    assert index.density(*at) == 0
    assert index.density("julia:mandelbrot", saturation.identity_of(JULIA), 0.0, 0.0) == 1


def test_the_radius_is_the_visits_own_frame() -> None:
    """A deep confirmation shadows almost nothing; a whole-set one shadows a
    neighbourhood. One run passing through a wide frame does not exhaust what is
    inside it, but a hundred deep visits in one basin do exhaust that basin."""
    index = VisitedIndex(0.3)
    index.add("mandelbrot", (), 0.0, 0.0, 1.0)  # shadows a disc of radius 0.3
    assert index.density("mandelbrot", (), 0.25, 0.0) == 1
    assert index.density("mandelbrot", (), 0.35, 0.0) == 0

    deep = VisitedIndex(0.3)
    deep.add("mandelbrot", (), 0.0, 0.0, 1e-6)
    assert deep.density("mandelbrot", (), 0.25, 0.0) == 0


def test_a_place_that_was_checked_and_refused_was_still_visited(tmp_path) -> None:
    """The descent spent its budget there. And "is it any good" is a cut on a
    score whose meaning moves with the scorer, so a quality-filtered memory would
    silently re-shape itself at every retrain."""
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [visit(MANDELBROT, "0.0", "0.0", "1.0", fate="flat")])
    index = saturation.build(root=tmp_path)
    assert index.visits == 1


def test_the_current_runs_own_ledger_is_excluded(tmp_path) -> None:
    """This is cross-run memory. A run seeded with its own finds would discount
    the ground it is standing on."""
    mine = tmp_path / "mine" / "walk.jsonl"
    theirs = tmp_path / "theirs" / "walk.jsonl"
    write(mine, [visit(MANDELBROT, "0.0", "0.0", "1.0")])
    write(theirs, [visit(MANDELBROT, "0.5", "0.0", "1.0")])
    index = saturation.build(root=tmp_path, exclude=mine)
    assert index.visits == 1
    assert index.summary()["ledgers"] == 1


def test_the_discount_is_soft_and_never_excludes() -> None:
    """A partition whose entire frontier is saturated keeps picking its best
    candidate rather than stalling. A subtracted penalty would be unbounded below,
    and "saturated" would eventually mean "unreachable"."""
    assert saturation.discount(0) == 1.0
    assert saturation.discount(1) == pytest.approx(0.5)
    assert saturation.discount(1000) > 0.0
    assert saturation.discount(saturation.SATURATED_DENSITY) == pytest.approx(0.1)


def test_zero_strength_is_the_mechanism_off_exactly() -> None:
    assert saturation.discount(50, strength=0.0) == 1.0


def test_an_unusable_row_is_counted_rather_than_raised() -> None:
    """The ledgers span every schema the project has ever written, and one bad
    legacy row must not take a run's start-up down — but a silently dropped
    population is how a memory quietly becomes empty."""
    index = VisitedIndex(0.3)
    assert index.add("mandelbrot", (), "not a number", 0.0, 1.0) is False
    assert index.add("mandelbrot", (), 0.0, 0.0, 0.0) is False, "a zero frame shadows nothing"
    assert index.visits == 0
    assert index.summary()["unusable_rows"] == 2


def test_the_index_reports_what_went_into_it() -> None:
    """A memory whose size nobody can read afterwards is a memory nobody can tell
    was empty."""
    index = VisitedIndex(0.3)
    index.add_row(visit(JULIA, "0.0", "0.0", "1.0"))
    index.add_row(visit(MANDELBROT, "0.0", "0.0", "1.0"))
    summary = index.summary()
    assert summary["visits"] == 2
    assert summary["partitions"] == {"julia:mandelbrot": 1, "mandelbrot": 1}
    assert summary["identity_buckets"] == 2
