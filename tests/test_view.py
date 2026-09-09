"""The stratified view: what one pass may reach, and what it may not cut on.

The pin here is **band-blind**. A view is a budget and a budget is allowed to be
one; what it is not allowed to be is a top-by-score cut, because the second thing
the objective maximizes is the *worst* seated score and the third is the demand
shortfall, and neither of those is found near the top of a stratum. A view that
kept only the strongest rows would hand the swap loop a neighbourhood that agrees
with the seed by construction.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate

from fractal_wallpapers.curation import ceiling, solve, view


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def rule_of(n: int) -> ceiling.Rule:
    rule = solve.rule_for()
    rule.group_cap = ceiling.group_cap(n, ceiling.PROPORTIONAL)
    return rule


def viewed(rows, n=20, floors=None, **over):
    return view.stratify(
        rows, n=n, rule=rule_of(n), rank=solve.ranking(None), floors=floors or {}, log=quiet, **over
    )


# --------------------------------------------------------------------------- #
# The pool is never touched.
# --------------------------------------------------------------------------- #
def test_the_view_is_a_view_and_the_pool_comes_back_unchanged():
    rows = [candidate(f"c{at}", score=1.0 - at / 100) for at in range(40)]
    before = list(rows)
    held = viewed(rows)
    assert rows == before, "a per-pass view never mutates the pool it reads"
    assert set(row.key for row in held.rows) <= {row.key for row in rows}


def test_the_record_carries_the_seed_the_strata_and_the_sizes():
    """A pass is reproducible from its own record or it is not reproducible."""
    rows = [candidate(f"c{at}", score=1.0 - at / 100) for at in range(40)]
    record = viewed(rows, seed=7).record()
    assert record["draw_seed"] == 7
    assert record["rows"] == len({row["of"] for row in record["per_stratum"]}) or record["rows"] > 0
    assert record["stratum"] == "(kind, mode, cell)"
    one = record["per_stratum"][0]
    assert set(one) >= {"of", "rows", "quota", "kept", "stride", "offset", "seats_it_could_spend"}


# --------------------------------------------------------------------------- #
# One wallpaper per location, plus the alternates.
# --------------------------------------------------------------------------- #
def test_only_one_row_a_place_survives_when_that_place_can_field_only_one_stratum():
    """A place spends at most one seat, so the view keeps that place's best row.
    Keeping fifty rows of one place would be fifty signatures for one seat."""
    rows = [candidate(f"c{at}", location="one", score=1.0 - at / 100) for at in range(20)]
    held = viewed(rows)
    assert [row.key for row in held.rows] == ["c0"], "its best by the pass's own key"


def test_a_place_keeps_an_alternate_where_a_second_stratum_needs_one():
    """The layer that makes the strata reachable at all: a place's best row overall
    can be a crowded blue while its second-best is the only azure it can field, and
    a view of best-per-place alone could never seat the azure."""
    rows = [
        candidate("blue", location="one", score=0.99, cells=("dark_vivid_blue",)),
        candidate("azure", location="one", score=0.50, cells=("dark_vivid_azure",)),
    ]
    held = viewed(rows)
    assert {row.key for row in held.rows} == {"blue", "azure"}
    assert held.record()["places"] == 1
    assert held.record()["alternates_available"] == 1


def test_a_candidate_dominant_in_nothing_is_stratified_and_never_dropped():
    """308 rows of this pool are dominant in no cell, and they are the fillers a
    colour target leans on: dropping them would make every target harder than it is."""
    rows = [candidate("plain", cells=())]
    held = viewed(rows)
    assert [row.key for row in held.rows] == ["plain"]
    assert any(name.endswith(view.NO_CELL) for name in held.strata)


# --------------------------------------------------------------------------- #
# The layer that is never cut.
# --------------------------------------------------------------------------- #
def places_with_alternates(count: int, cells=("dark_vivid_blue",), other="dark_vivid_azure"):
    """`count` places, each with its best row in one stratum and an alternate in
    another. The alternates are what a quota is spent on."""
    rows = []
    for at in range(count):
        rows.append(
            candidate(f"best{at:03d}", location=f"p{at:03d}", score=0.99 - at / 10000, cells=cells)
        )
        rows.append(
            candidate(
                f"alt{at:03d}", location=f"p{at:03d}", score=0.50 - at / 10000, cells=(other,)
            )
        )
    return rows


def test_every_places_strongest_row_is_in_the_view_whatever_the_strata_say():
    """THE FLOOR UNDER THIS LEG. The set of place-bests is exactly what the
    sequential seating this leg replaced walked, so a view holding all of it cannot
    choose worse than that walk did. The first draft sized its quotas over both
    layers together and reached 1,768 of 4,496 places; the seed came back at a worst
    seated score of 0.299 where the retired greedy had reached 0.418."""
    rows = places_with_alternates(300)
    held = viewed(rows, n=20)
    kept = {row.key for row in held.rows}
    assert all(f"best{at:03d}" in kept for at in range(300))
    assert held.record()["places"] == 300
    assert held.record()["locations"] == 300


def test_the_quota_cuts_into_the_alternates_and_only_into_them():
    rows = places_with_alternates(300)
    held = viewed(rows, n=20)
    kept = {row.key for row in held.rows}
    alternates = sum(1 for at in range(300) if f"alt{at:03d}" in kept)
    assert 0 < alternates < 300, "a budget, and one that bit"
    block = next(row for row in held.record()["per_stratum"] if row["cell"] == "dark_vivid_azure")
    assert block["place_best"] == 0 and block["alternates"] == 300
    assert block["stride"] > 1


def test_a_large_alternate_set_is_sliced_across_its_bands_and_never_cut_at_the_top():
    """THE POINT OF THE FILE. The slice has to reach the bottom: the row that lifts
    the worst seat, and the row that covers a starved mode, are by construction not
    near the top of anything."""
    rows = places_with_alternates(300)
    held = viewed(rows, n=20)
    where = sorted(int(row.key[3:]) for row in held.rows if row.key.startswith("alt"))
    assert max(where) > 200, "the slice reaches the bottom band"
    assert min(where) == 0, "and the strongest alternate is always anchored in"
    assert where != sorted(range(len(where))), "a top-by-score cut would have kept exactly these"


def test_a_small_alternate_set_is_taken_whole():
    rows = places_with_alternates(view.SMALL_STRATUM)
    held = viewed(rows)
    assert len(held) == 2 * view.SMALL_STRATUM
    assert all(block["stride"] == 1 for block in held.record()["per_stratum"])


def test_the_stride_offset_is_seeded_so_two_passes_at_one_seed_reach_one_view():
    rows = places_with_alternates(300)
    one = [row.key for row in viewed(rows, n=20, seed=3).rows]
    again = [row.key for row in viewed(rows, n=20, seed=3).rows]
    other = [row.key for row in viewed(rows, n=20, seed=11).rows]
    assert one == again
    assert one != other, "and a different seed is a different sample of the same bands"


def test_a_strata_draw_is_sized_to_what_n_seats_could_spend_on_it():
    """The cell allowance is what bounds a stratum's contribution, so it is what the
    quota is read off. At the size below, a cell may take one seat, so a stratum of
    three hundred alternates is not worth three hundred signatures.

    The size is read off `ceiling.K` and never written down: `floor(K * t * n) + 1`
    is one up to `n = 48/K`, so a literal would have to be revisited every time the
    ceiling moved — which is what this went red on when it went from 2 to 3."""
    seats = 48 // (ceiling.K + 1)
    rows = places_with_alternates(300)
    small = viewed(rows, n=seats)
    large = viewed(rows, n=1000)
    assert solve.rule_for().allowed("dark_vivid_azure", seats) == 1
    assert len(small) < len(large), "more seats reach more of the stratum"


def test_a_mode_floor_raises_its_own_strata_above_the_cell_allowance():
    """A mode owing twelve seats has to reach twelve, whatever its cells say."""
    rows = [
        candidate(f"best{at:03d}", location=f"p{at:03d}", score=0.99, cells=("dark_vivid_blue",))
        for at in range(200)
    ]
    rows += [
        candidate(
            f"alt{at:03d}",
            location=f"p{at:03d}",
            mode="stripe",
            score=0.50,
            cells=("dark_vivid_azure",),
        )
        for at in range(200)
    ]
    floored = viewed(rows, n=20, floors={"stripe": 12})
    bare = viewed(rows, n=20, floors={})
    assert len(floored) > len(bare)
    block = next(row for row in floored.record()["per_stratum"] if row["mode"] == "stripe")
    assert block["seats_it_could_spend"] >= 12


def test_rows_per_seat_is_the_knob_and_it_only_moves_the_alternates():
    rows = places_with_alternates(400)
    thin = viewed(rows, n=150, rows_per_seat=1)
    wide = viewed(rows, n=150, rows_per_seat=8)
    assert 400 < len(thin) < len(wide) <= 800, "the place-bests are in either way"
    assert view.ROWS_PER_SEAT == 2


@pytest.mark.parametrize("count", [1, 2, 9, 33, 100])
def test_a_slice_never_returns_more_than_the_stratum_holds(count):
    rows = [candidate(f"c{at:03d}", score=1.0 - at / 1000) for at in range(count)]
    held = viewed(rows, n=1000)
    assert len(held) <= count
    assert len({row.key for row in held.rows}) == len(held), "and never a duplicate"
