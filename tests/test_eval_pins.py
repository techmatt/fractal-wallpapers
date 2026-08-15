"""The evaluation pin, and the re-render it has to survive.

The pin is keyed on the location coordinate, seed included. Everything here is a
way somebody could reach the same picture under a different name and spend the
instrument without ever mentioning it.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.labeling import pins
from fractal_wallpapers.labeling import split as split_module
from fractal_wallpapers.supply.location import key_of_row

JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
OTHER_JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}
VIEW = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}


def shipped(*families) -> list[dict]:
    return [
        {"schema": 1, "group": i, "family": f, "viewport": VIEW} for i, f in enumerate(families)
    ]


def test_the_pin_is_read_off_the_shipped_record() -> None:
    keys = pins.pinned(shipped(JULIA))
    assert keys == {key_of_row({"family": JULIA, "viewport": VIEW})}


def test_a_re_render_under_a_fresh_batch_and_size_still_hits_the_pin() -> None:
    """The failure this is keyed to avoid: a later batch draws a pinned location
    again, under an identifier that has never been seen, and trains on it while
    the original sits in the evaluation side."""
    keys = pins.pinned(shipped(JULIA))
    fresh = {
        "batch": "somebody_elses_batch",
        "family": dict(JULIA),
        "viewport": dict(VIEW),
        "render": {"resolution": [3840, 2160], "supersample": 4},
    }
    assert pins.side_of(fresh, keys) == pins.EVAL


def test_the_pin_is_c_inclusive() -> None:
    """Two Julia views at one viewport with different seeds are different
    fractals; a pin that read the viewport alone would spend one on the other."""
    keys = pins.pinned(shipped(JULIA))
    assert pins.side_of({"family": OTHER_JULIA, "viewport": VIEW}, keys) == pins.TRAIN


def test_two_spellings_of_one_coordinate_are_one_location() -> None:
    keys = pins.pinned(shipped(JULIA))
    restated = {"family": {"kind": "julia", "degree": 2, "c": ["-0.40", "0.600"]}, "viewport": VIEW}
    assert pins.side_of(restated, keys) == pins.EVAL


def test_a_split_that_trains_on_a_pinned_location_is_refused() -> None:
    keys = pins.pinned(shipped(JULIA))
    sides = dict.fromkeys(keys, pins.TRAIN)
    with pytest.raises(pins.EvalPinViolation, match="spent the moment it trains"):
        pins.assert_eval(sides, keys, where="a test")


def test_pinning_reports_what_it_moved() -> None:
    """A pin that corrects silently hides the fact that something wanted to train
    on an instrument, and which rule that was is worth knowing."""
    keys = pins.pinned(shipped(JULIA))
    sides = dict.fromkeys(keys, pins.TRAIN)
    report = pins.pin(sides, keys, where="a test")
    assert report["moved_to_eval"] == 1
    assert set(sides.values()) == {pins.EVAL}
    pins.assert_eval(sides, keys, where="a test")


def test_a_pin_absent_from_a_split_is_not_a_violation() -> None:
    """A split over material that does not contain a pinned location has not
    spent it — the pin only speaks about locations the pass actually assigned."""
    keys = pins.pinned(shipped(JULIA))
    assert pins.assert_eval({}, keys, where="a test")["present"] == 0


def test_an_unshipped_split_pins_nothing(store_dir) -> None:
    assert split_module.read() == []
    assert pins.pinned() == set()
