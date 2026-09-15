"""The per-collection target table, and the two things it is read for.

The numbers themselves are a decision and decisions move, so nothing here pins
one of them. What is pinned is what the table exists for: that every key names a
collection, that the twelve families are all in it, that a lookup for a
collection with no target REFUSES rather than inventing one, and that the family
splice and the mode filter build the pools the two kinds of pass need.

Arithmetic over a handful of stubs, so the fast lane.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import solve, targets


def a_candidate(key: str, *, mode: str = "smooth", cells=(), families=()) -> solve.Candidate:
    """One pool row with only the four members `pool_for` reads filled in."""
    return solve.Candidate(
        key=key,
        location="loc",
        partition="julia:mandelbrot",
        mode=mode,
        group="grp",
        kind="field",
        cells=tuple(cells),
        families=tuple(families),
        score=0.5,
        p_ge3=0.5,
        picture=f"{key}.jpg",
    )


def test_every_key_in_the_table_names_a_collection_and_no_family_is_missing():
    """The guard the table exists for, in one call.

    A key that is neither a family nor a mode would be reported by the solve path
    as *no target for this collection*, which reads as a missing decision rather
    than as the typo it is; a family missing from the table is a family whose
    nightly solve refuses for want of a size.
    """
    assert targets.check() == {"collections": len(targets.TARGETS), "refusals": []}


def test_the_sixteen_are_twelve_families_and_four_modes():
    """The shape the prompt cut, and the one arithmetic claim worth holding."""
    assert len(targets.collections()) == 16
    assert set(targets.families()) <= set(targets.collections())
    assert len(targets.families()) == 12
    assert len(targets.modes()) == 4
    assert set(targets.modes()).isdisjoint(targets.families())


@pytest.mark.parametrize("name", sorted(targets.TARGETS))
def test_every_target_is_a_positive_seat_count(name):
    assert targets.seats_for(name) >= 1


def test_a_family_reads_as_a_family_and_a_mode_as_a_mode():
    assert targets.kind_of("lime") == targets.FAMILY
    assert targets.kind_of("stripe") == targets.MODE


def test_a_name_that_is_neither_refuses_and_says_what_a_collection_is():
    """A misspelling is refused as a misspelling and never as a missing target."""
    with pytest.raises(targets.TargetRefused) as refusal:
        targets.kind_of("limee")
    assert "neither" in str(refusal.value)
    assert "lime" in str(refusal.value)


def test_a_mode_the_table_does_not_name_refuses_rather_than_taking_a_default():
    """The whole point of the table: no number appears that nobody decided.

    `itinerary` is an accepted production mode, so it IS a collection; it has no
    target, and a solve over it has no size until somebody gives one or writes
    one down here.
    """
    with pytest.raises(targets.TargetRefused) as refusal:
        targets.seats_for("itinerary")
    assert "--n" in str(refusal.value)
    assert targets.seats_for("itinerary", default=7) == 7


def test_a_mode_collection_narrows_the_pool_to_that_routed_mode():
    """A mode pass is a subset and nothing about the solver changes."""
    pool = [
        a_candidate("a", mode="stripe"),
        a_candidate("b", mode="smooth"),
        a_candidate("c", mode="stripe"),
    ]
    held, count = targets.pool_for(pool, "stripe")
    assert count == 2
    assert [one.key for one in held] == ["a", "c"]


def test_a_family_collection_splices_the_name_and_leaves_every_other_row_alone():
    """A family is not a subset of anything the solver can see, so it is spliced.

    The pool comes back whole — an unspliced row is still in it and still
    off-theme — and the spliced row's own cell, which is `cells[0]` and what the
    seat is reported under, is untouched.
    """
    inside = a_candidate("a", cells=("dark_vivid_lime",), families=("lime",))
    outside = a_candidate("b", cells=("dark_vivid_red",), families=("red",))
    held, count = targets.pool_for([inside, outside], "lime")
    assert count == 1
    assert len(held) == 2
    assert held[0].cells == ("dark_vivid_lime", "lime")
    assert held[0].cells[0] == "dark_vivid_lime"
    assert held[1].cells == ("dark_vivid_red",)


def test_the_splice_is_what_the_themed_reader_asks_and_the_family_is_not_a_cell():
    """`solve.in_theme` asks `cell in candidate.cells`, so the splice IS the route."""
    from fractal_wallpapers.palettes import dominance

    assert "lime" not in set(dominance.cells())
    held, _count = targets.pool_for(
        [a_candidate("a", cells=("dark_vivid_lime",), families=("lime",))], "lime"
    )
    assert [one.key for one in solve.in_theme(held, "lime")] == ["a"]


def test_a_family_rule_takes_the_allowance_and_gives_the_demand_back():
    """All four cells raised, and no colour demand stated. See `targets.rule_for`.

    A target left standing would seed the pass scarcest-cell-first against a
    distribution nobody asked for, and report a shortfall for missing it.
    """
    rule = targets.rule_for("lime")
    assert rule.targets == {}
    # The allowance survives the emptying: a lime row is allowed far more than the
    # uniform 1/48 a pass with no target would give it.
    from fractal_wallpapers.curation import ceiling

    assert rule.allowed("dark_vivid_lime", 200) > ceiling.Rule().allowed("dark_vivid_lime", 200)


def test_a_mode_collection_has_no_cells_and_says_so():
    with pytest.raises(targets.TargetRefused):
        targets.cells_of("stripe")
    assert len(targets.cells_of("lime")) == 4
