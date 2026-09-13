"""The phase measurement: the panel, the metric, the control and the cut.

Arithmetic over rows, with one rendered guard at the end. Everything this module
does away from the engine is a seeded draw, a numpy difference and a sort — so the
fast lane gets fabricated rows and synthetic pixels, and the one test that renders
is the **control** and is slow.

The control is the test worth having. `curate phase-response`'s whole table rests on
the claim that the axis cannot reach a direct trap, and a harness that quietly
started varying one would produce a table that looks exactly as sound as a real
one. So the claim is a test and not only a report line: one trap, one place, one
map, two phases, one sha256.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers import engine
from fractal_wallpapers.curation import colorize, phase_response

needs_engine = pytest.mark.skipif(
    not engine.is_built(),
    reason="the engine is not built: cargo build --release --manifest-path engine/Cargo.toml",
)

#: A cyclic map and a folded one, named rather than drawn, so a kind that moved
#: under these tests cannot make one pass for the wrong reason.
A_CYCLIC_MAP = "twilight_shifted"
A_FOLDED_MAP = "cubehelix"

#: The trap the rendered control runs. `direct_trap_screen` because it is the one
#: the mode policy accepts and the cheapest of the four to draw.
A_TRAP = "direct_trap_screen"


# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
def a_row(mode="smooth", kind="field", colormap=A_CYCLIC_MAP, phase=0.25, mean=0.1, **over):
    row = {
        "schema": phase_response.SCHEMA,
        "mode": mode,
        "mode_kind": kind,
        "location": '["mandelbrot", 2, [], "0.1", "0.2", "0.001"]',
        "partition": "mandelbrot",
        "maxiter": 5000,
        "colormap": colormap,
        "mirror": colormap != A_CYCLIC_MAP,
        "phase": float(phase),
        "identical": mean == 0.0,
        "mean": float(mean),
        "moved": 0.9,
        "p95": float(mean) * 2,
        "p99": float(mean) * 3,
        "black_share": 0.1,
        "seconds": 1.0,
    }
    row.update(over)
    return row


def a_summary(*pairs):
    """One entry a `(mode, mean)` pair, in the shape [`split`] reads."""
    return [
        {
            "mode": mode,
            "mode_kind": "direct" if mean == 0.0 else "field",
            "cells": 4,
            "identical": 4 if mean == 0.0 else 0,
            "mean": float(mean),
            "p95": float(mean),
            "p99": float(mean),
            "moved": 0.5,
            "black_share": 0.1,
            "map_low": float(mean),
            "map_high": float(mean),
            "map_ratio": 1.0,
        }
        for mode, mean in pairs
    ]


# --------------------------------------------------------------------------- #
# The panel.
# --------------------------------------------------------------------------- #
def test_the_panel_is_a_function_of_the_seed_and_nothing_else() -> None:
    """Two draws on one seed are one panel, and on two seeds they are not.

    The whole reason a record carries a seed: a table nobody can redraw the panel of
    is a table nobody can check.
    """
    once = [place["key"] for place in phase_response.places(2, seed=0)]
    again = [place["key"] for place in phase_response.places(2, seed=0)]
    assert once == again
    assert once != [place["key"] for place in phase_response.places(2, seed=7)]


def test_the_panel_draws_one_place_a_partition() -> None:
    """What the spread inside a mode is read across has to be places that differ."""
    panel = phase_response.places(4, seed=0)
    assert len({place["partition"] for place in panel}) == 4


def test_the_panel_is_the_shallow_half_and_says_so() -> None:
    """The bias is stated, so this is what states it: no place from the deep half.

    Depth buys the same picture more slowly — a phase is spent after the field is
    read — and it is very nearly the whole price, which is why the draw is over the
    shallow half. A panel that quietly reached into the deep half would be a leg
    three times its stated cost.
    """
    everything = sorted(place["maxiter"] for place in phase_response.population())
    deepest_shallow = everything[max(0, int(len(everything) * phase_response.SHALLOW_SHARE) - 1)]
    for place in phase_response.places(4, seed=3):
        assert place["maxiter"] <= deepest_shallow


def test_the_map_panel_holds_both_kinds(shipped_cyclic_maps) -> None:
    """One of each at a count of two, because `mirror` is read off the kind.

    A folded ramp and a cyclic one are different objects to traverse, so a panel of
    one kind could not tell a mode's response from a kind's.
    """
    known = shipped_cyclic_maps
    drawn = phase_response.maps(2, seed=0, cyclic=known)
    assert len(drawn) == 2
    assert sum(1 for name in drawn if name in known) == 1


def test_the_map_panel_is_a_function_of_the_seed(shipped_cyclic_maps) -> None:
    known = shipped_cyclic_maps
    assert phase_response.maps(2, seed=1, cyclic=known) == phase_response.maps(
        2, seed=1, cyclic=known
    )
    assert phase_response.maps(2, seed=1, cyclic=known) != phase_response.maps(
        2, seed=9, cyclic=known
    )


def test_a_panel_wider_than_the_partitions_is_refused() -> None:
    """Refused and not quietly short: a table's panel is part of what it claims."""
    with pytest.raises(phase_response.PhaseResponseRefused):
        phase_response.places(99, seed=0)


def test_the_named_maps_are_still_the_kinds_these_tests_need(shipped_cyclic_maps) -> None:
    known = shipped_cyclic_maps
    assert A_CYCLIC_MAP in known
    assert A_FOLDED_MAP not in known


# --------------------------------------------------------------------------- #
# The metric.
# --------------------------------------------------------------------------- #
def test_a_picture_against_itself_is_zero_on_every_column() -> None:
    """The identity, which is what the control's own reading has to come back as."""
    import numpy

    pixels = numpy.arange(4 * 5 * 3, dtype=numpy.uint8).reshape(4, 5, 3)
    reading = phase_response.difference(pixels, pixels)
    assert reading["mean"] == 0.0
    assert reading["p99"] == 0.0
    assert reading["moved"] == 0.0


def test_the_difference_is_oklab_and_not_a_byte_count() -> None:
    """Black against white is about 1.0 in Oklab L, and a byte count would be 255.

    The one property that says the column is on a perceptual scale rather than on
    the encoder's: Oklab lightness runs 0 to 1.
    """
    import numpy

    black = numpy.zeros((2, 2, 3), dtype=numpy.uint8)
    white = numpy.full((2, 2, 3), 255, dtype=numpy.uint8)
    reading = phase_response.difference(black, white)
    assert 0.9 < reading["mean"] < 1.1
    assert reading["moved"] == 1.0


def test_the_moved_share_counts_pixels_and_the_mean_averages_them() -> None:
    """A thin band moved a long way reads a small mean and a large p99.

    Which is the shape the two columns exist to separate — a mode that recolours the
    whole frame slightly and one that recolours a little of it completely are not the
    same finding, and either alone would call them the same.
    """
    import numpy

    base = numpy.zeros((10, 10, 3), dtype=numpy.uint8)
    other = numpy.zeros((10, 10, 3), dtype=numpy.uint8)
    other[0, :] = 255
    reading = phase_response.difference(base, other)
    assert reading["moved"] == pytest.approx(0.10, abs=0.001)
    assert reading["mean"] < 0.15
    assert reading["p99"] > 0.9


def test_a_variant_at_another_size_is_refused() -> None:
    """Refused rather than broadcast: two pictures of one recipe are one geometry."""
    import numpy

    with pytest.raises(phase_response.PhaseResponseRefused):
        phase_response.difference(
            numpy.zeros((4, 4, 3), dtype=numpy.uint8), numpy.zeros((4, 5, 3), dtype=numpy.uint8)
        )


def test_black_share_is_the_interior_the_axis_cannot_reach() -> None:
    """`coloring.rs`'s INTERIOR is exactly black and never goes through the map."""
    import numpy

    pixels = numpy.zeros((10, 10, 3), dtype=numpy.uint8)
    pixels[:3, :] = 40
    assert phase_response.black_share(pixels) == pytest.approx(0.7)


# --------------------------------------------------------------------------- #
# The recipe, which must move ONE knob.
# --------------------------------------------------------------------------- #
def test_a_phase_pass_differs_from_the_baseline_in_the_phase_alone(shipped_cyclic_maps) -> None:
    """The whole measurement is this: one member moved and six held.

    A pass that also moved `gamma` or the transfer would be measuring a recipe and
    not an axis, and the table would say `phase` on a column about something else.
    """
    known = shipped_cyclic_maps
    base = phase_response.recipe_at(A_CYCLIC_MAP, known, phase_response.BASE_PHASE)
    moved = phase_response.recipe_at(A_CYCLIC_MAP, known, 0.25)
    assert base["phase"] == 0.0
    assert moved["phase"] == 0.25
    assert {name: value for name, value in base.items() if name != "phase"} == {
        name: value for name, value in moved.items() if name != "phase"
    }


def test_mirror_is_read_off_the_map_and_not_drawn(shipped_cyclic_maps) -> None:
    """The one knob that is not held, and it is derived rather than chosen."""
    known = shipped_cyclic_maps
    assert phase_response.recipe_at(A_CYCLIC_MAP, known, 0.25)["mirror"] is False
    assert phase_response.recipe_at(A_FOLDED_MAP, known, 0.25)["mirror"] is True


def test_a_baseline_name_survives_a_location_key_full_of_punctuation() -> None:
    """A location key is JSON text, and a Windows path holding one is WinError 123."""
    place = {"partition": "julia:multibrot5", "key": '["julia", 5, [["0.2", "0.7"]], "0.003"]'}
    name = phase_response.baseline_name("smooth", place, A_CYCLIC_MAP)
    assert not set(name) & set('"[]:<>|?*')


def test_two_cells_never_share_a_baseline_file(shipped_cyclic_maps) -> None:
    """Every cell of the grid writes its own, so one cannot overwrite another's."""
    panel = phase_response.places(2, seed=0)
    library = phase_response.maps(2, seed=0, cyclic=shipped_cyclic_maps)
    grid = phase_response.cells(["smooth", "tia"], panel, library)
    names = {phase_response.baseline_name(mode, place, name) for mode, place, name in grid}
    assert len(names) == len(grid) == 8


# --------------------------------------------------------------------------- #
# The control.
# --------------------------------------------------------------------------- #
def test_the_control_reads_the_traps_and_only_the_traps() -> None:
    rows = [
        a_row(mode="smooth", kind="field", mean=0.3),
        a_row(mode=A_TRAP, kind=colorize.DIRECT_KIND, mean=0.0),
        a_row(mode="direct_trap_lines", kind=colorize.DIRECT_KIND, mean=0.0),
    ]
    checked = phase_response.control(rows)
    assert checked["cells"] == 2
    assert checked["passed"] is True
    assert set(checked["modes"]) == {A_TRAP, "direct_trap_lines"}


def test_one_moved_trap_fails_the_control() -> None:
    """Because then the palette pass reached a picture it cannot reach.

    And a table taken on that harness is not a reading of the axis, however
    plausible every other row in it looks.
    """
    rows = [
        a_row(mode=A_TRAP, kind=colorize.DIRECT_KIND, mean=0.0),
        a_row(mode=A_TRAP, kind=colorize.DIRECT_KIND, mean=0.001, identical=False),
    ]
    assert phase_response.control(rows)["passed"] is False


def test_a_pass_with_no_trap_in_it_does_not_pass_the_control() -> None:
    """An empty control is not a clean one — there was nothing to check."""
    assert phase_response.control([a_row(mean=0.3)])["passed"] is False


# --------------------------------------------------------------------------- #
# The reading.
# --------------------------------------------------------------------------- #
def test_a_mode_carries_the_spread_across_maps_and_not_only_its_middle() -> None:
    """`map_low`/`map_high`, because a wide pair IS the finding on this axis.

    `palettes/README.md`'s first sweep found kind splits the baked phase axis five to
    one, so a per-mode mean over both kinds could hide the whole result.
    """
    rows = [
        a_row(colormap=A_CYCLIC_MAP, mean=0.40),
        a_row(colormap=A_CYCLIC_MAP, mean=0.44),
        a_row(colormap=A_FOLDED_MAP, mean=0.04),
        a_row(colormap=A_FOLDED_MAP, mean=0.06),
    ]
    entry = phase_response.summarise(rows)[0]
    assert entry["map_low"] == pytest.approx(0.05)
    assert entry["map_high"] == pytest.approx(0.42)
    assert entry["map_ratio"] == pytest.approx(8.4, abs=0.01)


def test_the_summary_is_ordered_by_how_far_the_axis_moves_the_mode() -> None:
    rows = [a_row(mode="a", mean=0.5), a_row(mode="b", mean=0.1), a_row(mode="c", mean=0.9)]
    assert [entry["mode"] for entry in phase_response.summarise(rows)] == ["b", "a", "c"]


def test_a_mode_is_summarised_on_its_median_and_not_its_mean() -> None:
    """One outlying cell must not carry a mode's column on a panel this small."""
    rows = [a_row(mean=0.10), a_row(mean=0.11), a_row(mean=0.12), a_row(mean=9.0)]
    assert phase_response.summarise(rows)[0]["mean"] == pytest.approx(0.115)


def test_the_flat_group_is_byte_identity_and_never_a_threshold() -> None:
    """A fact about the pictures, so nothing has to be chosen to state it."""
    split = phase_response.split(
        a_summary(("trap", 0.0), ("low", 0.02), ("mid", 0.05), ("high", 0.4))
    )
    assert split["flat"] == ["trap"]


def test_a_mode_that_moves_most_of_the_frame_past_the_jnd_is_live() -> None:
    """*Phase clearly moves the picture*, read on the scale the rows already carry."""
    split = phase_response.split(a_summary(("trap", 0.0), ("a", 0.2), ("b", 0.3)))
    assert split["live"] == ["a", "b"]
    assert split["uncertain"] == []


def test_a_mode_under_the_jnd_is_uncertain_and_not_flat() -> None:
    """The group the question was asked for, and the reason it exists.

    A mode that moves *something* but not enough of the frame to tell from a no-op
    is neither of the other two answers, and calling it either would be the invented
    threshold. It is not flat — its pictures are not identical — and it is not live.
    """
    split = phase_response.split(a_summary(("trap", 0.0), ("faint", 0.004), ("a", 0.3)))
    assert split["uncertain"] == ["faint"]
    assert split["flat"] == ["trap"]
    assert split["live"] == ["a"]


def test_a_mode_that_moves_a_sliver_a_long_way_is_uncertain() -> None:
    """Both floors bind, and the share is the one a mean alone would miss."""
    summary = a_summary(("sliver", 0.3))
    summary[0]["moved"] = 0.01
    assert phase_response.split(summary)["uncertain"] == ["sliver"]


def test_the_live_group_is_ordered_at_the_widest_step() -> None:
    split = phase_response.split(
        a_summary(("trap", 0.0), ("a", 0.10), ("b", 0.12), ("c", 4.0), ("d", 4.5))
    )
    assert split["ordered"] is True
    assert split["near"] == ["a", "b"]
    assert split["far"] == ["c", "d"]
    assert split["at"] == "c"


def test_a_live_ranking_with_no_gap_in_it_is_not_ordered_and_stays_one_group() -> None:
    """The honest answer, and the one this is written to be able to give.

    A geometric ladder has no gap anywhere in it, so a rule that always split one
    would be inventing the threshold it was told not to invent. The modes stay live —
    they all move the picture — and what the table declines to claim is their order.
    """
    split = phase_response.split(
        a_summary(("trap", 0.0), ("a", 0.10), ("b", 0.20), ("c", 0.40), ("d", 0.80))
    )
    assert split["ordered"] is False
    assert "near" not in split and "far" not in split
    assert split["live"] == ["a", "b", "c", "d"]


def test_the_gap_is_reported_whether_or_not_the_ranking_separated() -> None:
    """So a reader can see how near the call was rather than only which way it went."""
    ladder = phase_response.split(a_summary(("a", 0.1), ("b", 0.2), ("c", 0.4), ("d", 0.8)))
    assert ladder["ordered"] is False
    assert ladder["gap"] is not None and ladder["runner_up"] is not None


# --------------------------------------------------------------------------- #
# The rendered control.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
@needs_engine
def test_a_direct_trap_is_byte_identical_at_two_phases(tmp_path, shipped_cyclic_maps) -> None:
    """The claim the whole table rests on, rendered rather than cited.

    Two renders of one trap recipe that differ only in `Palette.phase`, one sha256.
    `coloring::shade`'s Direct arm never receives the `Palette` at all, so this is an
    assertion about the engine's shape and not a tolerance — and a harness that began
    varying a trap would otherwise produce a table nobody could tell was void.
    """
    known = shipped_cyclic_maps
    place = phase_response.places(1, seed=0)[0]
    base = phase_response.baseline(place, A_TRAP, A_CYCLIC_MAP, known, tmp_path)
    row = phase_response.phase_row(place, A_TRAP, A_CYCLIC_MAP, known, 0.25, base, tmp_path)
    assert row["identical"] is True
    assert row["mean"] == 0.0
    assert phase_response.control([row])["passed"] is True
