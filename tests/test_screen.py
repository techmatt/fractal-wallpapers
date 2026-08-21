"""Screening a frame somebody named: the walk's gates, pointed at a location.

The property that matters is that this is *not a second filter*. The engine runs
one battery and both `expand` and `screen` spend it, which the crate's own
`a_named_frame_gets_the_same_fate_the_walk_gave_it` pins on the Rust side; what
is pinned here is the door Python comes in by and the shape of what comes back.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine, locations
from fractal_wallpapers.discovery import walk as walk_module


def engine_is_built() -> bool:
    try:
        engine.engine_path()
    except FileNotFoundError:
        return False
    return True


needs_engine = pytest.mark.skipif(
    not engine_is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)


def screening(rows, **extra) -> dict:
    return engine.screen(
        {
            "schema": 1,
            "frames": [locations.frame_of(locations.record(row)) for row in rows],
            "colormap": "twilight_shifted",
            "colormap_dir": str(engine.colormap_dir()),
            **extra,
        }
    )


def location(center_re, center_im, width, family=None) -> dict:
    return {
        "family": family or {"kind": "mandelbrot"},
        "viewport": {"center_re": center_re, "center_im": center_im, "width": width},
    }


@needs_engine
def test_every_gate_that_ran_says_what_it_read_and_what_against() -> None:
    """A fate names the gate that decided; the verdicts are why. Without them
    "refused" is a word, and the figure this exists for is about the filter."""
    report = screening([location("-0.75", "0.1", "0.4")])
    frame = report["frames"][0]
    assert frame["fate"] in (
        "survived",
        "interior_cap",
        "flat",
        "instant_escape",
        "occupancy_floor",
    )
    gates = [verdict["gate"] for verdict in frame["verdicts"]]
    assert gates[0] == "interior_cap", "the cheapest gate runs first"
    for verdict in frame["verdicts"]:
        assert verdict["threshold"] > 0
        assert isinstance(verdict["passed"], bool)


@needs_engine
def test_the_thresholds_reported_are_the_gates_the_walk_actually_spends() -> None:
    """Expose, don't change. A `screen` that reported its own numbers would be a
    second filter wearing the first one's name."""
    report = screening([location("-0.75", "0.1", "0.4")])
    gates = walk_module.Gates()
    assert report["battery"] == {
        "interior_cap": gates.interior_cap,
        "occupancy_floor": gates.occupancy_floor,
        "band": {
            "spread_min": gates.spread_min,
            "escape_median_min": gates.escape_median_min,
        },
    }
    assert report["tile"] == [384, 216], "the node regime's own frame"
    assert report["field_supersample"] == 1


@needs_engine
def test_a_gate_that_never_ran_reports_nothing() -> None:
    """A frame the interior cap refused was never measured for occupancy, so a
    verdict for it would be an invention rather than a reading."""
    report = screening([location("-0.5", "0", "0.05")])
    frame = report["frames"][0]
    assert frame["fate"] == "interior_cap"
    assert [verdict["gate"] for verdict in frame["verdicts"]] == ["interior_cap"]
    assert "escape" not in frame and "occupancy" not in frame


@needs_engine
def test_a_batch_is_heterogeneous_and_comes_back_in_the_order_it_was_given() -> None:
    """Unlike an expansion, which is one family per call because it shares a
    random stream. Screening shares nothing, so a manifest of mixed families is
    one call — which is what makes a manifest the unit."""
    julia = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
    rows = [
        location("-0.75", "0.1", "0.4"),
        location("0.0", "0.0", "3.0", family=julia),
        location("-0.5", "0", "0.05"),
    ]
    report = screening(rows)
    assert [frame["index"] for frame in report["frames"]] == [0, 1, 2]
    assert [frame["family"] for frame in report["frames"]] == ["mandelbrot", "julia", "mandelbrot"]


@needs_engine
def test_the_cap_a_record_states_is_the_cap_the_gates_read_it_at(tmp_path) -> None:
    """The iteration cap decides what counts as interior, which is what the first
    gate measures. A record that states one and a screening that ignored it would
    be gating a different picture from the one on record."""
    row = location("-0.75", "0.1", "0.4")
    stated = {**row, "render": {"maxiter": 400}}
    assert screening([stated])["frames"][0]["maxiter"] == 400
    # Absent, the depth-aware policy decides, and says which number it chose.
    chosen = screening([row])["frames"][0]["maxiter"]
    assert chosen == engine.maxiter_for(["0.4"])[0]


@needs_engine
def test_the_first_rung_waiver_is_reachable_or_a_ledger_row_gets_a_verdict_nobody_made() -> None:
    """A walk waives the occupancy floor at its first rung, where the gate
    over-fires on a root frame still resolving structure the tighter child has not
    entered yet. So a first-rung candidate in a ledger passed a battery of *two*
    gates, and screening it against three reports a refusal the run that recorded
    it never made. Measured on `harvest_run9`: 6 of 20 first-rung rows flipped."""
    rows = [location("-0.75", "0.1", "0.4"), location("0.3", "0.02", "0.12")]
    acting = engine.screen(
        {
            "schema": 1,
            "frames": [locations.frame_of(locations.record(row)) for row in rows],
            "colormap": "twilight_shifted",
            "colormap_dir": str(engine.colormap_dir()),
        }
    )
    waived = screening(rows, occupancy=False)
    assert acting["occupancy"] is True and waived["occupancy"] is False

    for frame in waived["frames"]:
        assert "occupancy" not in frame, "a gate that did not run reports nothing"
        assert all(verdict["gate"] != "occupancy_floor" for verdict in frame["verdicts"])
    # And nothing else moves: waiving the last gate cannot rescue a frame an
    # earlier one refused, nor refuse one it passed.
    for one, two in zip(acting["frames"], waived["frames"], strict=True):
        if one["fate"] != "occupancy_floor":
            assert one["fate"] == two["fate"]
