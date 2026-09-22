"""The minibrot census instrument, against frames whose answer is known.

Three claims, and each is a thing this instrument got wrong before it was
written this way.

**The period ceiling.** [`discovery.operators.MAX_PERIOD`] is 64 and the atom in
the census's own named frame has period **1026**, so the operator path — the
right instrument for a walk deciding where to go — answers
`nucleus_outside_frame` on a frame squarely on top of a minibrot. That refusal is
pinned here beside the census's answer, because the two disagreeing is the whole
reason this module exists.

**The `f64` screen changes no verdict.** It is an approximation loose by decades
and it is allowed to cut the candidate list only because the slack covers that;
a screen that dropped a real atom would be a criterion of its own wearing a
speedup's clothes. Held on the named frame, where 71 periods rank, the screen
keeps 7, and the one it must not drop is the 60th of the 71.

**A dynamical partition is refused rather than answered.** A julia or phoenix
view has no embedded copy of a parameter-plane set, so a zero there would be a
measurement where there is none to make.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.discovery import minibrot
from fractal_wallpapers.discovery import operators as ops

#: The row `minibrot_descent_census_ckpt140` was written around: a `threads`
#: wallpaper at width 1.29e-9 inside a period-27 seahorse satellite, found by
#: `tuned129x_af6c2eb9xS4` and coloured by `mn132_u2`.
NAMED = ("-0.782601984654748", "0.15006989511782523", "0.0000000012860948266974178")

#: Its atom: period, and the frame's width in atom sizes.
NAMED_PERIOD = 1026
NAMED_SIZES = 11.777


def test_the_census_finds_the_atom_the_operator_path_cannot_reach():
    record, cost = minibrot.probe(*NAMED, 2)
    assert record is not None
    assert record["period"] == NAMED_PERIOD
    assert record["frame_sizes"] == pytest.approx(NAMED_SIZES, abs=1e-3)
    assert record["in_frame"]
    # Under one frame width of centre, which is the same bound a snap holds to.
    assert record["seed_distance_frames"] < minibrot.NEAR_MULTIPLE
    assert cost["solves"] >= 1

    view = {"center_re": NAMED[0], "center_im": NAMED[1], "width": NAMED[2]}
    refused, _solves, why = ops._solve_at_center(view, 2)
    assert refused is None and why == "nucleus_outside_frame", (
        "the operator path found something at this frame, so the ceiling it sweeps to is no "
        "longer the reason this module exists"
    )


def test_the_f64_screen_keeps_the_period_the_solve_needs():
    """It may cut the list; it may not cut the answer."""
    held = minibrot.scan(NAMED[0], NAMED[1], 2)
    kept = minibrot.screened(held, float(NAMED[2]), 2)
    assert NAMED_PERIOD in held.periods
    assert NAMED_PERIOD in kept
    assert len(kept) < len(held.periods), "a screen that cuts nothing is not a screen"


def test_a_frame_centred_on_its_own_nucleus_reads_the_framing_it_was_built_at():
    """`snap_to_nucleus` frames an atom at 4 and at 16 sizes; the census reads them back.

    The one end-to-end check that the atom instrument and the framing agree: a
    view the operators built at `4 * window_scale` has to come back as four atom
    sizes wide, or the size this census reports is not the size anything else in
    this project frames by.
    """
    elephant = {"center_re": "0.2925", "center_im": "0.0149", "width": "0.01"}
    built = [row for row in ops.snap_to_nucleus(elephant) if row.available]
    assert built, "the snap found no atom in the elephant valley, where it always has"
    for row in built:
        if row.framing is None:
            continue
        record, _cost = minibrot.probe(row.center_re, row.center_im, row.width, 2)
        assert record is not None
        assert record["frame_sizes"] == pytest.approx(float(row.framing), rel=1e-6)
        assert record["in_frame"] is (float(row.framing) <= minibrot.FRAME_MAX)


@pytest.mark.parametrize("partition", ["julia:mandelbrot", "phoenix", "phoenix:classic"])
def test_a_dynamical_partition_is_refused_and_not_answered(partition):
    assert minibrot.degree_of(partition) is None


@pytest.mark.parametrize(
    ("partition", "degree"),
    [("mandelbrot", 2), ("multibrot3", 3), ("multibrot4", 4), ("multibrot6", 6)],
)
def test_every_parameter_plane_names_its_degree(partition, degree):
    assert minibrot.degree_of(partition) == degree


def test_the_band_reporting_covers_every_reading_including_both_open_ends():
    assert minibrot.band_of(0.5) == "<1"
    assert minibrot.band_of(1.0) == "1-2"
    assert minibrot.band_of(11.78) == "8-16"
    assert minibrot.band_of(1e9) == ">=1024"
