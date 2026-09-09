"""The census: what it counts, what it is allowed to claim, and what it prices.

Every test here runs on **synthetic candidates**, for [`test_solve`]'s reason: a
census is arithmetic over the ledger's own fields, and a test that had to render a
picture to check that two rows at one place count as one location would be a test
nobody runs.

The two things worth pinning hardest are not the arithmetic. They are that counts
are **distinct locations and never rows** — the whole point of the module — and
that the covering condition is stated in the direction that makes it sound: a
short row is provable infeasibility, a row with slack is never a claim that the
selection is possible.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import ceiling, embeddings, headroom, mode_policy, solve


@pytest.fixture(autouse=True)
def no_neutral_store(monkeypatch):
    """An empty neutral embedding store, for every test in this file.

    The pools here are synthetic and no place in them is in the real store, so the
    pre-selection would sweep twenty-nine thousand rows to learn that it can see
    none of them — half a second a test, over dozens of tests. An empty store is
    the same answer for none of the cost, and it exercises the branch that has to
    hold anyway: **a location with no descriptor is admitted, never dropped.** The
    pre-selection's own tests hand in a store of their own.
    """
    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: [])


def candidate(
    key,
    *,
    location=None,
    score=0.9,
    p_ge3=None,
    mode="smooth",
    group=None,
    cells=(),
    families=(),
    partition="mandelbrot",
    kind="smooth_render",
):
    """One synthetic candidate, its own place and its own palette group unless a
    test says otherwise, so a test about one axis is not silently about another."""
    return solve.Candidate(
        key=str(key),
        location=str(location if location is not None else key),
        partition=partition,
        mode=mode,
        group=str(group if group is not None else f"map:{key}"),
        kind=kind,
        cells=tuple(cells),
        families=tuple(families),
        score=float(score),
        p_ge3=float(score if p_ge3 is None else p_ge3),
        picture=f"artifacts/{key}.jpg",
    )


def clearing_pool(count, **rest):
    """`count` candidates that clear the default bar, one location each."""
    return [candidate(f"c{at}", score=0.9, **rest) for at in range(count)]


# --------------------------------------------------------------------------- #
# The bars, per mode.
# --------------------------------------------------------------------------- #
def test_a_mode_over_the_fallback_count_keeps_the_default_bar():
    read = headroom.bars(clearing_pool(headroom.FALLBACK_LOCATIONS))
    assert read["modes"]["smooth"]["rule"] == headroom.DEFAULT_COLUMN
    assert read["modes"]["smooth"]["q4_locations"] == headroom.FALLBACK_LOCATIONS
    assert "smooth" in read["on_default"]


def test_a_mode_one_location_short_of_the_count_falls_back_to_p_ge3():
    read = headroom.bars(clearing_pool(headroom.FALLBACK_LOCATIONS - 1))
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert "smooth" in read["on_fallback"]


def test_the_fallback_is_read_on_p_ge3_and_not_on_the_default_column():
    # Three locations over the q4 bar, so the mode falls back; forty more that
    # clear only P(>=3). The clearing population has to be all forty-three.
    pool = [candidate(f"high{at}", score=0.9) for at in range(3)]
    pool += [candidate(f"low{at}", score=0.1, p_ge3=0.8) for at in range(40)]
    read = headroom.bars(pool)
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert len(headroom.clearing(pool, read)) == 43


def test_the_hoisted_rule_is_the_one_the_table_reports_and_answers_off_the_roster():
    """`rule_of` and `clears` came out of `bars`'s loop on 2026-09-04 so that a
    caller about a mode the roster no longer holds could reach the rule instead of
    restating it — `curation.remode` is that caller. Two claims, and the second is
    the whole point of the extraction:

    the hoisted pair agrees with the table row by row, on both columns; and it
    answers for a mode `bars` refuses to name at all, which is any mode
    `mode_policy` weights 0."""
    high = [candidate(f"high{at}", score=0.9) for at in range(3)]
    low = [candidate(f"low{at}", score=0.1, p_ge3=0.8) for at in range(40)]
    pool = high + low
    read = headroom.bars(pool)
    rule = read["modes"]["smooth"]["rule"]
    assert headroom.rule_of(pool) == rule == headroom.FALLBACK_COLUMN
    assert headroom.rule_of(clearing_pool(headroom.FALLBACK_LOCATIONS)) == (headroom.DEFAULT_COLUMN)
    assert headroom.rule_of(pool, relaxed=True) == headroom.FALLBACK_COLUMN
    # Row for row against the table's own answer, which is what says the loop
    # still computes what it computed.
    assert [held.key for held in headroom.clearing(pool, read)] == [
        held.key for held in pool if headroom.clears(held, rule)
    ]
    # And off the roster. A niche mode is absent from `bars["modes"]`, so
    # `clearing` drops its rows and the table has no rule to give — while
    # `rule_of` answers about the rows themselves.
    niche = mode_policy.niche()[0]
    stranded = clearing_pool(headroom.FALLBACK_LOCATIONS, mode=niche)
    off = headroom.bars(stranded)
    assert niche not in off["modes"] and off["off_roster"][niche] == len(stranded)
    assert headroom.clearing(stranded, off) == []
    assert headroom.rule_of(stranded) == headroom.DEFAULT_COLUMN
    assert all(headroom.clears(held, headroom.rule_of(stranded)) for held in stranded)
    assert headroom.clears(stranded[0], None) is False, "no rule never clears"


def test_a_mode_the_fallback_does_not_rescue_is_still_flagged_thin():
    pool = [candidate(f"c{at}", score=0.1, p_ge3=0.8) for at in range(4)]
    read = headroom.bars(pool)
    assert read["modes"]["smooth"]["rule"] == headroom.FALLBACK_COLUMN
    assert read["modes"]["smooth"]["thin"] is True
    assert "smooth" in read["still_thin"]


def test_the_bars_report_both_columns_for_every_mode_whichever_rule_it_landed_on():
    read = headroom.bars(clearing_pool(3))
    held = read["modes"]["smooth"]
    assert {"q4_rows", "q4_locations", "q3_rows", "q3_locations"} <= set(held)


def test_a_mode_off_the_production_roster_is_counted_and_not_censused():
    read = headroom.bars([candidate("c0", mode="not_a_mode")])
    assert read["off_roster"] == {"not_a_mode": 1}
    assert "not_a_mode" not in read["modes"]


def test_the_rows_the_fine_head_must_have_read_are_the_q4_rows_and_no_others():
    """`score-pool` reads `above_bar`, which is `score >= Q4_BAR`, which is what
    this table calls `q4_rows`. Two names for one set, and the census is where a
    leg finds out whether the head is behind the pool BEFORE it solves."""
    pool = [candidate("c0", score=0.9), candidate("c1", score=0.9), candidate("c2", score=0.1)]
    assert [held.above_bar for held in pool] == [True, True, False]
    read = headroom.bars(pool, fine={"c0": {"p_ge4": 0.7}})
    assert read["modes"]["smooth"]["q4_rows"] == 2
    assert read["modes"]["smooth"]["with_p_fine"] == 1
    assert read["modes"]["smooth"]["q4_unread"] == 1
    assert read["fine_head"]["q4_rows"] == 2 and read["fine_head"]["q4_unread"] == 1


def test_a_below_bar_row_the_head_happens_to_have_read_is_not_counted_as_coverage():
    """The question is whether every SEATABLE row is read. A reading on a row no
    cascade can lift is not coverage, and counting it would let a table report
    full coverage over a pool with unread rows above the bar."""
    read = headroom.bars(
        [candidate("c0", score=0.9), candidate("c1", score=0.1)],
        fine={"c1": {"p_ge4": 0.7}},
    )
    assert read["fine_head"]["scores_read"] == 1
    assert read["fine_head"]["with_p_fine"] == 0 and read["fine_head"]["q4_unread"] == 1


def test_no_scores_handed_in_reads_null_and_not_zero():
    """A caller that did not ask and a pool nothing has read are different facts,
    and every census in this tree is the first of them."""
    read = headroom.bars(clearing_pool(3))
    assert read["fine_head"]["with_p_fine"] is None
    assert read["fine_head"]["scores_read"] is None
    assert read["modes"]["smooth"]["with_p_fine"] is None
    assert read["fine_head"]["q4_rows"] == 3


def test_the_census_never_reads_the_pool_scores_store_itself(monkeypatch):
    """`clearing` and `census` call `bars` on every census and none of them want
    the column. A store read inside it would be a fifth of a second on each."""
    from fractal_wallpapers.models import gallery_grade_train

    def refuse(*_args, **_rest):
        raise AssertionError("headroom read the pool scores itself")

    monkeypatch.setattr(gallery_grade_train, "read_pool_scores", refuse)
    assert headroom.clearing(clearing_pool(3))


# --------------------------------------------------------------------------- #
# Counts are distinct locations.
# --------------------------------------------------------------------------- #
def test_many_rows_at_one_place_are_one_location_of_supply():
    pool = [candidate(f"c{at}", location="one", cells=("dark_vivid_blue",)) for at in range(60)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    row = next(row for row in block["rows"] if row["about"] == "dark_vivid_blue")
    assert row["rows"] == 60
    assert row["supply"] == 1


def test_the_location_row_counts_places_and_not_rows():
    pool = [candidate(f"c{at}", location=f"place{at % 4}") for at in range(40)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["one_per_location"]
    assert block["supply"] == 4
    assert block["short"] is True
    assert block["slack"] == -16


# --------------------------------------------------------------------------- #
# The covering condition, and the direction it is sound in.
# --------------------------------------------------------------------------- #
def test_the_cover_is_short_when_the_caps_cannot_hold_n_between_them():
    # Two cells, one location each, and at n=20 the per-cell allowance is one. So
    # the axis can hold two seats and the program asks for twenty.
    pool = [
        candidate("a", cells=("dark_vivid_blue",)),
        candidate("b", cells=("dark_vivid_red",)),
    ]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["supply"] == 2
    assert block["short"] is True


def test_a_location_dominant_in_no_cell_counts_toward_the_cover():
    pool = [candidate(f"c{at}", cells=()) for at in range(30)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["dominant_in_none"] == 30
    assert block["short"] is False


def test_the_cover_counts_a_multiply_dominant_location_once_per_cell():
    # The over-count is what makes the condition NECESSARY and never sufficient,
    # so it is pinned rather than fixed: one place in three cells contributes
    # three to the sum, and the block says so.
    pool = [candidate("a", cells=("dark_vivid_blue", "dark_vivid_red", "dark_muted_blue"))]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_ceiling_cells"]
    assert block["usable_from_the_axis"] == 3


def test_the_cap_a_cover_row_carries_is_the_ceilings_own_allowance():
    pool = clearing_pool(4, cells=("dark_vivid_blue",))
    read = headroom.census(pool, ladder=(150,), log=lambda *_: None)
    row = next(
        row
        for row in read["curve"]["150"]["blocks"]["colour_ceiling_cells"]["rows"]
        if row["about"] == "dark_vivid_blue"
    )
    assert row["cap"] == solve.rule_for().allowed("dark_vivid_blue", 150)


# --------------------------------------------------------------------------- #
# The mode floors.
# --------------------------------------------------------------------------- #
def test_the_block_bounds_the_floors_the_shipped_legs_actually_take():
    """The whole point of the block, and the one thing a revert would break.

    `curation.mode_policy.seat_floors(n)` is what an unflagged `curate seat` and an
    unflagged `curate solve run` are floored by, so an unflagged census has to bound
    those floors or it bounds a gallery nobody builds. It bounded the flat
    `floor(n / 100)` until 2026-08-31 and reported a demand of **zero** at `n = 20`
    where the shipped seating asks for six.

    Every assertion here is red under a flat floor of any value: a flat floor is one
    number for every mode, and this rule is thirteen different ones.
    """
    read = headroom.census(clearing_pool(3), ladder=(20, 150), log=lambda *_: None)
    for size in (20, 150):
        block = read["curve"][str(size)]["blocks"]["mode_floors"]
        want = mode_policy.seat_floors(size)
        assert block["floors"] == {name: want.get(name, 0) for name in mode_policy.accepted()}
        assert block["needs"] == sum(want.values())
        assert block["floor"] is None, "the shipped rule is per mode and not one number"
        assert block["floor_artificial"] is False
        assert "THE DEFAULT" in block["floor_rule"]
        assert {row["needs"] for row in block["rows"]} == set(block["floors"].values())
    # Not one number for everybody, which is what a flat floor is.
    assert len(set(read["curve"]["150"]["blocks"]["mode_floors"]["floors"].values())) > 1
    assert read["curve"]["20"]["blocks"]["mode_floors"]["needs"] == 6
    assert read["curve"]["150"]["blocks"]["mode_floors"]["needs"] == 45


def test_the_flat_floor_is_still_readable_and_says_it_is_the_flat_one():
    """`curate headroom --flat-floor`, the baseline the shipped rule is read against.

    It is a function of `n` and a census walks a ladder, so it is asked for by
    [`headroom.FLAT`] rather than by a number — and the block has to say it ran
    under the baseline, or a floored-against-flat reading cannot tell the two
    censuses apart.
    """
    read = headroom.census(
        clearing_pool(3), ladder=(20, 150), floor=headroom.FLAT, log=lambda *_: None
    )
    at20 = read["curve"]["20"]["blocks"]["mode_floors"]
    assert at20["floor"] == 0
    assert at20["needs"] == 0
    assert all(row["short"] is False for row in at20["rows"])
    at150 = read["curve"]["150"]["blocks"]["mode_floors"]
    assert at150["floor"] == solve.mode_floor(150) == 1
    assert at150["needs"] == len(mode_policy.accepted())
    assert set(at150["floors"].values()) == {1}
    assert at150["floor_artificial"] is True, "flat is not what nobody asked for any more"
    assert "FLAT" in at150["floor_rule"]


def test_a_mode_with_no_clearing_candidate_is_short_at_its_own_floor():
    # `stripe` is floored at 5 of the 150 seats and the pool is all `smooth`, so
    # the row is short by its own floor rather than by one number shared with
    # every other mode.
    read = headroom.census(clearing_pool(3), ladder=(150,), log=lambda *_: None)
    block = read["curve"]["150"]["blocks"]["mode_floors"]
    row = next(row for row in block["rows"] if row["about"] == "stripe")
    assert row["needs"] == mode_policy.seat_floors(150)["stripe"] == 5
    assert row["supply"] == 0
    assert row["short"] is True
    assert "stripe" in block["empty"]


def test_a_small_gallery_is_not_asked_for_one_of_every_mode():
    """The `trap_circle` question, re-asked of the rule that ships.

    A flat floor of one put every mode into a twenty-seat gallery — eighteen of
    the twenty seats spent on representation — including one whose best clearing
    picture sat at `P(>=4) = 0.066`. `floor(n / 100)` retired that by being zero
    below a hundred seats, and the per-mode rule retires it a second way: at
    `n = 20` it asks for six seats between six modes and asks the other eight
    accepted modes for nothing at all.

    So the guard is not "the block asks for nothing" any more — it asks for six.
    It is that a small gallery is never made to seat the whole roster, and that
    what it does ask stays a minority of the seats.
    """
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["mode_floors"]
    roster = len(mode_policy.accepted())
    assert block["floored_modes"] == 6
    assert block["floored_modes"] < roster, "not one of every mode"
    assert sum(1 for row in block["rows"] if row["needs"] == 0) == roster - 6
    # Six of twenty, where the flat floor of one asked for eighteen of twenty.
    assert block["needs"] == 6
    assert block["needs"] * 3 <= 20


def test_the_floor_block_counts_places_towards_the_floor_and_not_modes():
    """The bug a flat floor of one could not show.

    Each mode needs **its own** floor in distinct places, so the supply the demand
    is read against is the sum over modes of `min(that mode's floor, its places)`.
    Counting modes-that-hold-anything instead is the same number only while every
    floor is one — at n=500 it read one row per mode against a demand in the
    hundreds, and called a pool short that is nowhere near it.
    """
    # One strange mode, three places, against a floor in the teens at n=500. The
    # floor is READ rather than written down: it is `seat_floors`' arithmetic over
    # whatever the roster currently is, and it moved from 15 to 16 the day
    # `exp_smoothing` went to weight 0 and left the strange budget dividing by 19
    # instead of 20. What is under test is that supply counts places against it.
    read = headroom.census(clearing_pool(3, mode="stripe"), ladder=(500,), log=lambda *_: None)
    block = read["curve"]["500"]["blocks"]["mode_floors"]
    floor = mode_policy.seat_floors(500)["stripe"]
    assert block["floors"]["stripe"] == floor > 3, "the floor must outrun the three places"
    # The floor is asked of the modes a gallery may seat, not of the whole
    # production roster: a mode weighted 0 has no row in the pool to meet it with.
    assert block["needs"] == sum(mode_policy.seat_floors(500).values()) == 150
    # Three of what `stripe` is asked for, and nothing from anybody else.
    assert block["supply"] == 3
    assert block["modes_holding_anything"] == 1
    assert block["short"] is True


def test_the_per_mode_floors_always_fit_in_n_and_the_flat_one_did_not():
    """They sum to half the strange seat budget by construction — `ceil(0.6n / 2)`,
    which is `ceil(0.3n)` and never more — so the block can never ask for a gallery
    it cannot fit. The flat floor of one this replaced asked for the whole roster at
    every `n` below the roster's size, which was eighteen of twenty seats at
    `n = 20`. The bound is tight at the bottom rather than generous: `n = 1` asks
    for the one seat there is, and that still fits."""
    read = headroom.census(clearing_pool(3), ladder=(1, 5, 150, 1000), log=lambda *_: None)
    for size in (1, 5, 150, 1000):
        block = read["curve"][str(size)]["blocks"]["mode_floors"]
        assert block["fits_in_n"] is True
        assert block["needs"] == (mode_policy.strange_seats(size) + 1) // 2
        assert block["needs"] <= size
        assert block["needs"] <= -(-3 * size // 10), "at most ceil(0.3n), at every rung"
    assert len(mode_policy.accepted()) > 5, "the flat floor of one did not fit at n = 5"


# --------------------------------------------------------------------------- #
# The group cap, and the flag it does not raise.
# --------------------------------------------------------------------------- #
def test_the_group_cap_is_short_when_there_are_fewer_groups_than_seats():
    pool = [candidate(f"c{at}", group="map:one") for at in range(40)]
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["palette_group_cap"]
    # One group, and at twenty seats the proportional cap is its `max(1, ...)`
    # floor — so the whole pool is supply for exactly one seat.
    assert block["supply"] == ceiling.group_cap(20, solve.DEFAULT_GROUP_CAP) == 1
    assert block["short"] is True


def test_the_block_prices_against_the_cap_THE_SHIPPED_LEG_APPLIES():
    """The census used to spell the group cap a second time, as the flat
    `ceiling.GROUP_CAP` the retired seat leg took. The leg that actually runs takes
    `ceiling.group_cap(n, solve.DEFAULT_GROUP_CAP)`, which is proportional: at
    n=1000 that is 25 a group and not 1. Priced flat, 754 groups made the pool look
    short by 246 at a rung where the shipped leg found no ceiling binding at all
    and seated a realized maximum of 7.

    RED under `allowance=lambda _name: ceiling.GROUP_CAP`, which is what this was.
    """
    # Forty groups of four places each: enough that a cap of 1 binds hard and the
    # shipped cap does not bind at all.
    pool = [
        candidate(f"c{group}_{at}", group=f"map:{group}") for group in range(40) for at in range(4)
    ]
    read = headroom.census(pool, ladder=(40,), log=lambda *_: None)
    block = read["curve"]["40"]["blocks"]["palette_group_cap"]
    cap = ceiling.group_cap(40, solve.DEFAULT_GROUP_CAP)
    assert cap == 1, "the proportional rule's floor at forty seats"
    assert block["cap"] == cap
    assert block["cap_rule"] == solve.DEFAULT_GROUP_CAP == ceiling.PROPORTIONAL
    assert all(row["needs"] == cap for row in block["rows"]), "every group gets the same cap"

    # And at a rung where the two rules diverge, the block follows the shipped one.
    wide = headroom.census(pool, ladder=(1000,), log=lambda *_: None)
    block = wide["curve"]["1000"]["blocks"]["palette_group_cap"]
    assert block["cap"] == ceiling.group_cap(1000, solve.DEFAULT_GROUP_CAP) == 25
    assert block["cap"] != ceiling.GROUP_CAP, "the retired leg's flat cap is not this one"
    # 40 groups x min(25, 4 places) = 160 against a thousand seats: still short,
    # but short on PLACES, which is the true condition, rather than on the cap.
    assert block["supply"] == 160


def test_the_block_says_there_is_no_second_threshold_behind_the_cap():
    """The retired solve carried a same-group DISTANCE row beside the count, and
    this block's note used to call itself the `TIGHT form` of a cap the pixels
    could exempt. `curation.rules` dropped that row rather than merging it, so the
    count is the whole rule and the note may not promise otherwise."""
    read = headroom.census(clearing_pool(40), ladder=(20,), log=lambda *_: None)
    note = read["curve"]["20"]["blocks"]["palette_group_cap"]["rows"][0]["note"]
    block = read["curve"]["20"]["blocks"]["palette_group_cap"]
    text = f"{note} {block.get('note', '')}"
    assert "TIGHT" not in text
    assert str(ceiling.TAU_GROUP) not in text


def test_the_group_axis_does_not_raise_the_thin_flag():
    # 752 groups mostly holding a handful of places each is the ordinary state of
    # this store and not a finding. The rows still carry their own `thin`.
    pool = clearing_pool(40)
    read = headroom.census(pool, ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["palette_group_cap"]
    assert block["flag_thin"] is False
    assert all(row["thin"] for row in block["rows"])
    assert not [item for item in read["curve"]["20"]["flagged"] if item["about"].startswith("map:")]


def test_a_thin_cell_is_flagged_even_with_slack_in_its_own_cap():
    pool = [
        candidate(f"c{at}", cells=("dark_vivid_lime",)) for at in range(headroom.THIN - 1)
    ] + clearing_pool(40, cells=("dark_vivid_blue",))
    read = headroom.census(pool, ladder=(1000,), log=lambda *_: None)
    flagged = {item["about"] for item in read["curve"]["1000"]["flagged"]}
    assert "dark_vivid_lime" in flagged


# --------------------------------------------------------------------------- #
# The default target vector.
# --------------------------------------------------------------------------- #
def test_the_default_vector_demands_no_explicit_colour():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["colour_targets"]
    assert block["needs"] == 0
    assert block["short"] is False


def test_the_default_allowance_is_the_uniform_share_and_not_a_second_copy_of_it():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert (
        str(round(ceiling.CELL_SHARE, 6)) in read["curve"]["20"]["blocks"]["colour_targets"]["rule"]
    )


# --------------------------------------------------------------------------- #
# What one more costs.
# --------------------------------------------------------------------------- #
def test_the_render_cost_is_the_median_of_the_seconds_a_leg_stamped():
    rows = [
        {"recipe": {"mode": "smooth"}, "hunt": {"seconds": value}} for value in (0.1, 0.2, 0.3, 9.0)
    ]
    assert headroom.render_cost(rows)["smooth"]["median"] == pytest.approx(0.25)


def test_a_row_with_no_stamped_seconds_is_not_in_the_denominator():
    rows = [
        {"recipe": {"mode": "smooth"}, "hunt": {"seconds": 0.5}},
        {"recipe": {"mode": "smooth"}, "hunt": {}},
        {"recipe": {"mode": "smooth"}},
    ]
    assert headroom.render_cost(rows)["smooth"]["rows"] == 1


def test_the_marginal_cost_is_renders_per_win_times_the_winners_own_render_cost():
    pool = clearing_pool(4, cells=("dark_vivid_blue",))
    read = headroom.census(
        pool, ladder=(20,), costs={"smooth": {"median": 0.5}}, log=lambda *_: None
    )
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["colour_ceiling_cells"]["rows"]
        if row["about"] == "dark_vivid_blue"
    )
    assert row["renders_per_win"] == pytest.approx(1.0)
    assert row["seconds_per_win"] == pytest.approx(0.5)


def test_a_mode_row_is_priced_against_that_modes_own_renders():
    # Eight renders in `stripe`, two of which clear. The mode's rate is its own
    # 8/2 and never the whole ledger's, which would be 12/2 here.
    pool = clearing_pool(4)
    pool += [candidate(f"s{at}", mode="stripe", score=0.9) for at in range(2)]
    pool += [candidate(f"sl{at}", mode="stripe", score=0.01, p_ge3=0.01) for at in range(6)]
    read = headroom.census(
        pool, ladder=(20,), costs={"stripe": {"median": 1.0}}, log=lambda *_: None
    )
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["mode_floors"]["rows"]
        if row["about"] == "stripe"
    )
    assert row["supply"] == 2
    assert row["renders_per_win"] == pytest.approx(4.0)


def test_a_constraint_with_no_supply_prices_nothing_rather_than_dividing_by_zero():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    row = next(
        row
        for row in read["curve"]["20"]["blocks"]["mode_floors"]["rows"]
        if row["about"] == "stripe"
    )
    assert row["renders_per_win"] is None
    assert row["seconds_per_win"] is None


# --------------------------------------------------------------------------- #
# What the record is allowed to say.
# --------------------------------------------------------------------------- #
def test_the_census_states_the_only_claim_it_is_making():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert "necessary conditions only" in read["reads"]
    assert "NOT a claim" in read["reads"]


def test_the_curve_costs_what_one_rung_costs_and_reports_every_rung_asked_for():
    read = headroom.census(clearing_pool(3), ladder=(20, 150, 500), log=lambda *_: None)
    assert sorted(read["curve"]) == ["150", "20", "500"]


def test_the_estimator_names_itself_as_unconditioned():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert "UNCONDITIONED" in read["estimator"]


# --------------------------------------------------------------------------- #
# The tracked ledger. Real rows, the real bars, the real curve.
# --------------------------------------------------------------------------- #
@pytest.fixture
def tracked_pool(tracked_ledger):
    """The session's one reading of the ledger. See `conftest.tracked_ledger`."""
    return tracked_ledger.pool, tracked_ledger.costs


@pytest.mark.slow
def test_the_tracked_ledger_censuses_and_every_supply_is_a_location_count(tracked_pool):
    """One real census, end to end, and the one invariant it cannot break.

    No supply figure anywhere may exceed the number of distinct locations in the
    clearing population — which is the whole claim of the module, and the thing a
    row-count leaking into one of these tallies would violate immediately.
    """
    candidates, costs = tracked_pool
    read = headroom.census(candidates, costs=costs, log=lambda *_: None)
    places = read["population"]["clearing_locations"]
    assert 0 < places <= read["population"]["locations"]
    for block in read["curve"]["20"]["blocks"].values():
        for row in block.get("rows", []):
            assert row["supply"] <= places
            assert row["supply"] <= row["rows"] or row["rows"] == 0


@pytest.mark.slow
def test_every_mode_on_the_fallback_really_is_short_of_the_default(tracked_pool):
    """The fallback is a rule about supply and not a preference: a mode that
    landed on it has to have had fewer than the count at the default bar."""
    candidates, _costs = tracked_pool
    read = headroom.bars(candidates)
    for name in read["on_fallback"]:
        assert read["modes"][name]["q4_locations"] < headroom.FALLBACK_LOCATIONS
    for name in read["on_default"]:
        assert read["modes"][name]["q4_locations"] >= headroom.FALLBACK_LOCATIONS


# --------------------------------------------------------------------------- #
# The twin constraint.
# --------------------------------------------------------------------------- #
def test_the_twin_block_is_empty_and_says_so_when_no_sweep_was_handed_in():
    """The one block that cannot be answered from a row, and it is opt-in."""
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    block = read["curve"]["20"]["blocks"]["twin_diversity"]
    assert block["short"] is False
    assert "NOT COUNTED" in block["rule"]
    assert "skipped" in read["twin_constraint"]


def test_the_upper_bound_is_the_places_less_a_matching():
    """A chain of four places holds at most two of them, and the matching says so.

    `a-b`, `b-c`, `c-d`: a greedy matching takes `a-b` and `c-d`, so the bound is
    4 - 2 = 2, which is exactly the largest set of pairwise non-twin places here.
    """
    read = headroom.twin_bound(
        ["a", "b", "c", "d"], [("a", "b"), ("b", "c"), ("c", "d")], order=["a", "b", "c", "d"]
    )
    assert read["matching"] == 2
    assert read["upper_bound"] == 2
    assert read["greedy_independent_set"] == 2
    assert read["places_in_a_twin_pair"] == 4


def test_a_pool_with_no_twin_pair_is_bounded_by_its_own_size():
    read = headroom.twin_bound(["a", "b", "c"], [])
    assert read["matching"] == 0
    assert read["upper_bound"] == 3
    assert read["greedy_independent_set"] == 3


def test_a_twin_pair_outside_the_population_is_not_an_edge():
    # The sweep may have been taken over a wider pool than the census counts.
    read = headroom.twin_bound(["a", "b"], [("a", "b"), ("a", "z"), ("y", "z")])
    assert read["twin_pairs"] == 1
    assert read["upper_bound"] == 1


def test_the_bounds_say_which_of_them_is_a_necessary_condition():
    """The direction is the whole safety argument and it is on the record."""
    read = headroom.twin_bound(["a", "b"], [("a", "b")])
    assert "NECESSARY" in read["bounds"]
    assert "CONSTRUCTIVE" in read["bounds"]
    assert "one picture per place" in read["measured_over"]


def sweep(pairs, directions=None):
    """A twin sweep in the shape `--twin-from` reads one from disk.

    The direction count is part of it, because a sweep is a set of distances and so
    is only a fact about the metric that measured them.
    """
    from fractal_wallpapers.palettes import pixel_clouds

    return {
        "tau": ceiling.TAU,
        "directions": pixel_clouds.DIRECTIONS if directions is None else directions,
        "places": 3,
        "pairs_screened": 3,
        "pairs": list(pairs),
    }


def test_the_twin_block_is_short_when_the_bound_falls_under_n():
    swept = sweep([{"a": "c0", "b": "c1"}, {"a": "c1", "b": "c2"}])
    read = headroom.census(clearing_pool(3), ladder=(2, 20), twins=swept, log=lambda *_: None)
    assert read["curve"]["2"]["blocks"]["twin_diversity"]["supply"] == 2
    assert read["curve"]["2"]["blocks"]["twin_diversity"]["short"] is False
    assert read["curve"]["20"]["blocks"]["twin_diversity"]["short"] is True
    assert read["twin_constraint"]["directions"] == swept["directions"]


def test_a_twin_sweep_from_another_direction_count_is_refused_not_read():
    """A sweep is distances, so it is only a fact about the metric that took it.

    `--twin-from` replays one off disk, and the twin counts in a sweep taken at
    another slice count are counts in a different metric — with nothing about its
    shape to give that away, which is why this refuses instead of flagging. Both
    `twins.json` files on disk when the count moved predate the field entirely.
    """
    from fractal_wallpapers.palettes import pixel_clouds

    pairs = [{"a": "c0", "b": "c1"}]
    with pytest.raises(headroom.HeadroomError, match="different metric"):
        headroom.census(
            clearing_pool(3),
            ladder=(2,),
            twins=sweep(pairs, directions=pixel_clouds.DIRECTIONS * 2),
            log=lambda *_: None,
        )
    stale = sweep(pairs)
    del stale["directions"]
    with pytest.raises(headroom.HeadroomError, match="no direction count"):
        headroom.census(clearing_pool(3), ladder=(2,), twins=stale, log=lambda *_: None)


# --------------------------------------------------------------------------- #
# The neutral pre-selection, at pool construction.
# --------------------------------------------------------------------------- #
def test_the_census_records_the_preselection_it_was_taken_over():
    read = headroom.census(clearing_pool(3), ladder=(20,), log=lambda *_: None)
    assert read["preselection"]["radius"] == headroom.distinct.PRESELECT_RADIUS
    assert read["preselection"]["admitted_without_a_descriptor"] == 3
    assert read["population"]["after_the_preselection"] == 3


def test_a_census_without_the_preselection_says_it_was_not_applied():
    read = headroom.census(clearing_pool(3), ladder=(20,), radius=None, log=lambda *_: None)
    assert "skipped" in read["preselection"]
