"""The reframing operators: what they refuse, and what a refusal costs.

Availability is the *uncommon* outcome, so most of what is checked here is the
shape of "no". Every entry point returns a result with a named reason and never
raises, because a caller that had to handle an exception on the common path
would spend its life handling it.
"""

from __future__ import annotations

import math
import random

import mpmath as mp
import pytest

from fractal_wallpapers.discovery import nucleus as nuc
from fractal_wallpapers.discovery import operators


@pytest.fixture(autouse=True)
def working_precision():
    previous = mp.mp.dps
    nuc.set_precision()
    yield
    mp.mp.dps = previous


def view(center_re: str, center_im: str, width: str, node_id: int = 1) -> dict:
    return {
        "node_id": node_id,
        "center_re": center_re,
        "center_im": center_im,
        "width": width,
    }


#: A view on top of a low-period nucleus, at a width that contains it.
ON_AN_ATOM = view("-0.1592", "1.0317", "0.02")


def test_a_view_on_an_atom_snaps_to_it_at_every_framing() -> None:
    rows = operators.snap_to_nucleus(ON_AN_ATOM, degree=2)
    assert len(rows) == len(operators.FRAMINGS)
    assert all(row.available for row in rows), [r.reason for r in rows]
    assert len({row.key for row in rows}) == 1, "one nucleus, several framings"
    # It landed inside the frame it was reframing, which is the teleport guard.
    distance = math.hypot(
        float(rows[0].center_re) - float(ON_AN_ATOM["center_re"]),
        float(rows[0].center_im) - float(ON_AN_ATOM["center_im"]),
    )
    assert distance <= operators.SNAP_MAX_WIDTH_MULTIPLE * float(ON_AN_ATOM["width"])
    widths = [row.width for row in rows]
    assert widths[0] == 0.02, "the first framing preserves the parent's width"
    assert widths[2] > widths[1], "a larger framing is a wider frame"


def test_the_shared_solve_is_charged_to_the_first_framing_only() -> None:
    """The nucleus does not depend on the framing, so N framings cost one solve.

    Charging it once is what makes summing the solves over the returned rows the
    true cost of the call — and what makes adding a framing a design choice
    rather than a cost one.
    """
    rows = operators.snap_to_nucleus(ON_AN_ATOM, degree=2)
    assert rows[0].newton_solves > 0
    assert all(row.newton_solves == 0 for row in rows[1:])
    assert all(row.extra.get("reused_solve") for row in rows[1:])


def test_a_snap_that_would_be_a_teleport_is_refused_by_name() -> None:
    """A nucleus outside the frame is not a reframing of *this* view — it is a
    jump to a different one, and the quality the operator was supposed to
    inherit is not the quality of where it landed."""
    rows = operators.snap_to_nucleus(view("-0.1592", "1.0317", "1e-9"), degree=2)
    assert not any(row.available for row in rows)
    assert rows[0].reason == "nucleus_outside_frame"


def test_a_view_in_the_far_exterior_reports_that_its_orbit_escaped() -> None:
    rows = operators.snap_to_nucleus(view("10", "10", "0.5"), degree=2)
    assert rows[0].reason == "orbit_escaped_immediately"


def test_a_refusal_carries_the_framing_it_refused() -> None:
    """Two of the refusals are framing-dependent by construction. Stamping every
    refusal as "no framing" would pile exactly the interesting ones into one
    bucket that no cost read can be taken from."""
    rows = operators.snap_to_nucleus(view("-0.1592", "1.0317", "1e-9"), degree=2)
    assert [row.framing for row in rows] == [None, 4.0, 16.0]


def test_a_framing_wider_than_a_whole_set_view_is_refused() -> None:
    """A reframing that proposes a near-whole-plane view is not a reframing of
    this neighbourhood; it is ground the walk's own roots already cover."""
    rows = operators.snap_to_nucleus(ON_AN_ATOM, degree=2, framings=[1e9])
    assert rows[0].available is False
    assert rows[0].reason == "width_over_root_scale"


def test_the_f64_wall_is_checked_before_anything_is_rendered() -> None:
    """The margin comes from the atom instrument, so a framing that would
    quantize is refused with no render attempted."""
    assert operators.wall_margin_decades(1e-3) > operators.WALL_MARGIN_DECADES
    assert operators.wall_margin_decades(1e-10) < operators.WALL_MARGIN_DECADES
    assert operators.wall_margin_decades(0.0) == -math.inf

    rows = operators.snap_to_nucleus(ON_AN_ATOM, degree=2, framings=[1e-9])
    assert rows[0].available is False
    assert rows[0].reason == "f64_spacing_wall"


def test_an_available_reframing_carries_both_margins() -> None:
    """The node margin says whether the walk can render it now; the deploy
    margin says whether a finished wallpaper of it could ever be rendered. They
    are different presentations and both belong on the row."""
    row = operators.snap_to_nucleus(ON_AN_ATOM, degree=2)[1]
    assert row.node_margin_decades > operators.WALL_MARGIN_DECADES
    assert row.deploy_margin_decades is not None
    assert row.node_margin_decades > row.deploy_margin_decades


def test_a_lateral_step_lands_on_a_different_atom_at_a_comparable_scale() -> None:
    """Or reports, by name, why it did not. Both are ordinary outcomes."""
    rng = random.Random(3)
    parent = operators.snap_to_nucleus(ON_AN_ATOM, degree=2)[0]
    reasons = set()
    landed = 0
    for _ in range(8):
        row = operators.lateral_to_sibling(ON_AN_ATOM, rng, degree=2)
        if row.available:
            landed += 1
            assert row.key != parent.key, "a sibling is not the parent"
            ratio = row.extra["scale_ratio_decades"]
            assert abs(ratio) <= operators.SCALE_TOLERANCE_DECADES
        else:
            reasons.add(row.reason)
    assert landed or reasons, "the operator must return something"
    assert reasons <= {
        "hit_parent",
        "scale_mismatch",
        "no_sibling_found",
        "no_nucleus_near_seed",
        "orbit_escaped_immediately",
        "f64_spacing_wall",
        "width_over_root_scale",
    }, reasons


#: A view that has no parent atom at all: the nucleus its center sits on is
#: outside the frame, which is the single most common firing on a real run.
NO_PARENT = view("-0.1592", "1.0317", "1e-9")


def test_a_snap_that_missed_is_an_answer_the_disc_operators_can_read() -> None:
    """The parent-atom solve is deterministic in the view, so re-running it
    behind a snap that just failed buys the same refusal at full price. 954 of
    1,379 firings on the run this was priced from were exactly that."""
    snapped = operators.snap_to_nucleus(NO_PARENT, degree=2)
    assert not any(row.available for row in snapped)
    shared = operators.parent_atom_from_snap(snapped)
    assert shared.resolved and shared.record is None
    assert shared.refusal == "no_parent_atom:nucleus_outside_frame"

    solo = operators.lateral_to_sibling(NO_PARENT, random.Random(0), degree=2)
    told = operators.lateral_to_sibling(
        NO_PARENT, random.Random(0), degree=2, parent=operators.parent_atom_from_snap(snapped)
    )
    assert (solo.available, solo.reason) == (told.available, told.reason)
    assert solo.newton_solves > 0, "solving it alone costs what it costs"
    assert told.newton_solves == 0, "reading the snap's answer costs nothing"


def test_a_snap_that_hit_hands_the_atom_over_rather_than_the_solve() -> None:
    snapped = operators.snap_to_nucleus(ON_AN_ATOM, degree=2)
    shared = operators.parent_atom_from_snap(snapped)
    assert shared.record is not None and shared.record["key"] == snapped[0].key
    assert shared.charge() == 0, "the snap's own row was already charged for it"


def test_the_firing_s_solve_is_charged_once_however_many_operators_read_it() -> None:
    """The shared slot is filled in by whoever needs it first — with no snap in
    the firing that is the lateral step, and the enumeration behind it reads it
    for nothing rather than paying a second time."""
    shared = operators.ParentAtom()
    assert not shared.resolved

    sibling = operators.lateral_to_sibling(NO_PARENT, random.Random(0), degree=2, parent=shared)
    assert shared.resolved and shared.record is None
    assert sibling.newton_solves > 0

    rows = operators.expand_neighborhood(NO_PARENT, random.Random(0), degree=2, parent=shared)
    assert rows[0].reason == sibling.reason
    assert sum(row.newton_solves for row in rows) == 0


def test_a_snap_that_found_an_atom_and_refused_its_frame_settles_nothing() -> None:
    """A framing refusal is a verdict on a frame, not on the atom, so the disc
    operators are left to solve for their own rather than handed a false miss."""
    snapped = operators.snap_to_nucleus(ON_AN_ATOM, degree=2, framings=[1e-9])
    assert not any(row.available for row in snapped)
    assert operators.parent_atom_from_snap(snapped).resolved is False


def test_the_neighbourhood_enumeration_always_returns_a_named_answer() -> None:
    """An exhausted disc is one unavailable row with a reason, never an empty
    list — because "nothing is there" and "it kept handing back the parent" are
    different facts and only one of them means stop trying."""
    rng = random.Random(11)
    rows = operators.expand_neighborhood(ON_AN_ATOM, rng, degree=2, probe_max=4)
    assert rows, "never empty"
    if not any(row.available for row in rows):
        assert rows[0].reason
        assert "probe_refusals" in rows[0].extra


def test_the_neighbourhood_window_is_one_sided() -> None:
    """Unbounded below and bounded above, and that asymmetry *is* the operator:
    a child several rungs down the ladder is a legitimate neighbour, a giant
    that swallows the parent is an ancestor."""
    rng = random.Random(5)
    rows = operators.expand_neighborhood(ON_AN_ATOM, rng, degree=2, probe_max=6)
    for row in rows:
        if row.available and row.extra.get("scale_ratio_decades") is not None:
            assert row.extra["scale_ratio_decades"] <= operators.NEIGHBOUR_SCALE_UP_DECADES


def test_reframing_is_undefined_on_the_dynamical_planes() -> None:
    """A Julia or Phoenix viewport is a point of the *dynamical* plane and has
    no nucleus in the parameter-plane sense at all. Skipped rather than faked."""
    assert operators.degree_of("mandelbrot") == 2
    assert operators.degree_of("multibrot", 4) == 4
    assert operators.degree_of("multibrot", 2) is None
    assert operators.degree_of("julia") is None
    assert operators.degree_of("phoenix") is None


# --------------------------------------------------------------------------- #
# the cost governor
# --------------------------------------------------------------------------- #


def test_the_region_cache_beats_the_coin() -> None:
    """A cell that has been probed is skipped whatever the coin says: siblings
    in one lineage sit in one cell, and probing them re-derives the same nucleus
    at full price."""
    governor = operators.ProbeGovernor(1.0, random.Random(0))
    assert governor.should_probe(2, "-0.5", "0.0", 0.1) == (True, "")
    assert governor.should_probe(2, "-0.5", "0.0", 0.1) == (False, "region_cached")
    tally = governor.tally()
    assert tally["fired"] == 1 and tally["cache_skipped"] == 1


def test_the_coin_bounds_how_often_the_probe_is_paid_for() -> None:
    governor = operators.ProbeGovernor(0.0, random.Random(0))
    fired, why = governor.should_probe(2, "0.3", "0.4", 0.2)
    assert fired is False and why == "cost_governor"
    assert governor.tally()["coin_skipped"] == 1


def test_the_cell_is_measured_in_the_view_s_own_width() -> None:
    """So the grid is as coarse or as fine as the scale being searched — one
    fixed cell size would be meaningless across ten octaves of zoom."""
    governor = operators.ProbeGovernor(1.0, random.Random(0))
    assert governor.cell(2, "-0.5", "0.0", 0.1) == governor.cell(2, "-0.5", "0.0", 0.1)
    assert governor.cell(2, "-0.5", "0.0", 0.1) != governor.cell(2, "-0.5", "0.0", 0.01)
    assert governor.cell(2, "-0.5", "0.0", 0.1) != governor.cell(3, "-0.5", "0.0", 0.1)
