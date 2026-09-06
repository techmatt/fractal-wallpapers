"""Retention: what is kept, what the aggregates hold, and what the rule costs.

Arithmetic over rows, like [`test_mine`] and [`test_depth`]. Nothing renders and
nothing is deleted — the module under test has no delete in it at all, which is
the first property pinned here and the one that stops a report becoming a prune.

The claims worth pinning hardest are the ones a wrong decision would hide. **The
ranking is within the (location, mode) pair** and never against an absolute
probability, because CORN's scale moves under every retrain and the per-mode
crossovers already span 0.367 to 0.950. **There is one constant**, and it is the
store's — a second K on a second ranking is what let a retained row lose its
picture. And **the price of dropping a row is reported off the `k` the survivors
carry**, so it can be read without keeping the index the rule exists to avoid.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import retention

VIEWPORT = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}
PALETTE = {
    "gamma": 1.0,
    "cycles": 1.0,
    "phase": 0.0,
    "reverse": False,
    "mirror": False,
    "transfer": {"kind": "value"},
    "rolloff": {"kind": "none"},
}


def a_row(key, place="p", mode="smooth", colormap="viridis", cells=(), picture="a.jpg"):
    """One ledger row, thinned to the members a retention decision reads."""
    return {
        "key": key,
        "location": {"key": place},
        "recipe": {
            "family": {"kind": "mandelbrot"},
            "viewport": VIEWPORT,
            "mode": mode,
            "mode_params": {},
            "curve": "linear",
            "colormap": colormap,
            "palette": PALETTE,
        },
        "colour": {"cells": list(cells), "families": []},
        "picture": picture,
    }


# --------------------------------------------------------------------------- #
# The rule.
# --------------------------------------------------------------------------- #
def test_the_top_n_of_a_pair_are_kept_and_ranked_inside_the_pair():
    rows = [a_row(f"k{at}") for at in range(8)]
    scores = {f"k{at}": at / 10 for at in range(8)}
    out = retention.decide(rows, scores, keep=3)
    ranked = [key for key, reason in out.items() if reason == retention.RANKED]
    assert sorted(ranked) == ["k5", "k6", "k7"], "the three highest of the pair"


def test_the_ranking_never_crosses_a_mode_or_a_location():
    """A pair's fifth-best is kept even where another pair's sixth-best scores
    higher. An absolute cut would take the whole of one mode and none of another
    — the per-mode crossovers span 0.367 to 0.950 and one number cannot be the
    bar for all of them."""
    rows = [a_row(f"a{at}", mode="smooth") for at in range(3)]
    rows += [a_row(f"b{at}", mode="stripe") for at in range(3)]
    scores = {f"a{at}": 0.9 for at in range(3)} | {f"b{at}": 0.01 for at in range(3)}
    out = retention.decide(rows, scores, keep=2)
    assert sum(1 for key in ("a0", "a1", "a2") if out[key] == retention.RANKED) == 2
    assert sum(1 for key in ("b0", "b1", "b2") if out[key] == retention.RANKED) == 2, (
        "the weak mode keeps its own best two, at a hundredth of the strong mode's score"
    )


def test_a_row_with_no_score_ranks_last_rather_than_being_thrown_out():
    """Nothing has an opinion about it, which is not the same as something
    thinking little of it."""
    rows = [a_row("scored"), a_row("silent")]
    out = retention.decide(rows, {"scored": 0.0}, keep=1)
    assert out["scored"] == retention.RANKED
    assert out["silent"] != retention.RANKED


def test_there_is_one_constant_and_it_is_the_stores():
    """One ranking, one number. `retention.KEEP_PER_PAIR` was a second of each —
    five pictures a pair by raw `P(>=4)` against three rows a pair by the rank
    key — and because the two were not nested a retained row could have lost its
    picture already."""
    from fractal_wallpapers.curation import candidate_ledger

    assert retention.keep_per_pair() == candidate_ledger.RETAIN_PER_PAIR
    assert not hasattr(retention, "KEEP_PER_PAIR")
    assert not hasattr(retention, "RESERVOIR_ONE_IN")


def test_the_default_keep_is_the_stores_constant_and_not_a_copy_of_its_value():
    rows = [a_row(f"k{at}") for at in range(8)]
    scores = {f"k{at}": at for at in range(8)}
    ranked = [key for key, why in retention.decide(rows, scores).items() if why == retention.RANKED]
    assert len(ranked) == retention.keep_per_pair()


def test_every_row_gets_exactly_one_reason_and_all_of_them_are_named():
    rows = [a_row(f"k{at}") for at in range(30)]
    out = retention.decide(rows, {f"k{at}": at for at in range(30)}, keep=4)
    assert set(out) == {f"k{at}" for at in range(30)}
    assert set(out.values()) <= set(retention.REASONS)
    assert set(retention.REASONS) == {retention.RANKED, retention.DROPPED}
    assert retention.kept(retention.RANKED)
    assert not retention.kept(retention.DROPPED)


def test_the_module_that_decides_what_to_delete_cannot_delete():
    """The policy is a decision and applying it is not this module's job. A
    delete in here is how a report becomes a prune by accident."""
    import inspect

    source = inspect.getsource(retention)
    for forbidden in ("unlink(", "rmtree", "os.remove", "shutil.move", "rename("):
        assert forbidden not in source, forbidden


# --------------------------------------------------------------------------- #
# The three aggregates.
# --------------------------------------------------------------------------- #
def test_the_place_mode_count_carries_the_pool_it_is_a_cursor_into():
    """The count says how much of a seeded permutation has been spent. Change
    the library and the same count names different maps."""
    rows = [a_row("k1"), a_row("k2"), a_row("k3", mode="stripe")]
    out = retention.by_place_mode(rows, stamp=retention.pool_stamp(["a", "b"]))
    assert out[("p", "smooth")]["attempts"] == 2
    assert out[("p", "stripe")]["attempts"] == 1
    assert out[("p", "smooth")]["pool_stamp"] == retention.pool_stamp(["a", "b"])
    assert retention.pool_stamp(["a", "b"]) != retention.pool_stamp(["a", "c"])
    assert retention.pool_stamp(["a", "b"]) != retention.pool_stamp(["b", "a"]), (
        "order is part of a permutation's identity"
    )


def test_the_map_mode_count_keeps_colormap_identity_off_the_discards():
    """The one signal a discard genuinely destroys. Drop the colormap with the
    picture and 'which palettes never work anywhere' stops being askable."""
    rows = [
        a_row("k1", colormap="viridis"),
        a_row("k2", colormap="viridis"),
        a_row("k3", colormap="magma"),
    ]
    out = retention.by_map_mode(rows, {"k1": 0.9, "k2": 0.1}, bar=0.5)
    assert out[("viridis", "smooth")] == {"attempts": 2, "scored": 2, "successes": 1}
    assert out[("magma", "smooth")] == {"attempts": 1, "scored": 0, "successes": 0}, (
        "an unscored row is an attempt and not a failure"
    )


def test_the_place_cell_count_is_read_off_the_stored_colour_and_not_off_a_table():
    """What a place ACTUALLY produced. The carrier table is a prior about a map."""
    rows = [
        a_row("k1", cells=["dark_vivid_green"]),
        a_row("k2", cells=["dark_vivid_green", "dark_muted_rose"]),
        a_row("k3", cells=[]),
    ]
    out = retention.by_place_cell(rows)
    assert out[("p", "dark_vivid_green")] == {"attempts": 3, "dominant": 2}
    assert out[("p", "dark_muted_rose")] == {"attempts": 3, "dominant": 1}
    assert ("p", "dark_vivid_blue") not in out, (
        "a colour a place has never delivered is the ABSENCE of a row, which is what "
        "a targeted mine tests for"
    )


def test_the_aggregates_are_bounded_by_their_key_spaces_and_not_by_the_attempts():
    """The whole point. Ten times the attempts at the same places, in the same
    modes, through the same maps is the same size of aggregate."""
    one = [a_row(f"k{at}", cells=["dark_vivid_green"]) for at in range(20)]
    ten = [a_row(f"k{at}", cells=["dark_vivid_green"]) for at in range(200)]
    small = retention.aggregates(one, {}, "stamp")
    large = retention.aggregates(ten, {}, "stamp")
    for name in ("place_mode", "map_mode", "place_cell"):
        assert small[name]["pairs"] == large[name]["pairs"], name
    assert large["attempts"] == 200


# --------------------------------------------------------------------------- #
# The report.
# --------------------------------------------------------------------------- #
def test_the_report_says_it_applied_nothing():
    rows = [a_row(f"k{at}", picture=None) for at in range(12)]
    out = retention.prune_report(rows, {f"k{at}": at for at in range(12)}, keep=3)
    assert out["applied"] is False
    assert out["rows"] == 12
    assert out["verdicts"][retention.RANKED] + out["verdicts"][retention.DROPPED] == 12
    assert out["rows_naming_no_picture"] == 12
    assert out["pictures_named_by_a_dropped_row"] == 0


def test_the_report_counts_a_picture_for_every_row_it_would_drop():
    """One rule: a picture goes if and only if its row does. A dropped row that
    names a picture is a picture to delete, and there is no second ranking that
    could already have taken it."""
    rows = [
        a_row(f"k{at}", picture=f"artifacts/curation/hunt/h/pictures/k{at}.jpg") for at in range(9)
    ]
    out = retention.prune_report(rows, {f"k{at}": at for at in range(9)}, keep=2)
    assert out["verdicts"][retention.DROPPED] == 7
    assert out["pictures_named_by_a_dropped_row"] == 7


def test_the_report_breaks_the_deletion_down_by_mode():
    rows = [a_row(f"s{at}", mode="smooth", picture=None) for at in range(8)]
    rows += [a_row(f"t{at}", mode="stripe", picture=None) for at in range(4)]
    scores = {row["key"]: 0.5 for row in rows}
    out = retention.prune_report(rows, scores, keep=2)
    assert out["by_mode"]["smooth"][retention.RANKED] == 2
    assert out["by_mode"]["stripe"][retention.RANKED] == 2
    assert sum(out["by_mode"][mode][retention.DROPPED] for mode in ("smooth", "stripe")) == 8


# --------------------------------------------------------------------------- #
# What the rule costs.
# --------------------------------------------------------------------------- #
def with_k(key, place, k):
    row = a_row(key, place=place)
    row["hunt"] = {"seconds": 0.1, "k": k}
    return row


def test_the_deleted_count_is_read_off_the_deepest_k_the_survivors_carry():
    """Three rows left and a deepest `k` of forty means thirty-seven recipes were
    rendered here and dropped. The count survives the drop that made it, which is
    what makes the price readable with no index of every recipe ever drawn."""
    rows = [with_k("a", "p", 40), with_k("b", "p", 12), with_k("c", "p", 3)]
    out = retention.drawn_before(rows)
    assert out["p"] == {"retained": 3, "deepest_k": 40, "invisible": 37}


def test_a_location_whose_rows_predate_the_k_stamp_reports_nothing_invisible():
    """No `k` is not a `k` of one. A reader that took it for one would report the
    whole pre-stamp history as never deepened."""
    out = retention.drawn_before([a_row("a"), a_row("b")])
    assert out["p"]["deepest_k"] is None
    assert out["p"]["invisible"] == 0


def test_a_draw_at_a_place_with_nothing_invisible_cannot_be_a_repeat():
    standing = retention.drawn_before([with_k("a", "p", 1)])
    out = retention.repeat_draws([a_row("new")], standing, pool=800)
    assert out["at_locations_with_deleted_rows"] == 0
    assert out["bound"] == 0
    assert out["expected"] == 0


def test_a_location_cannot_repeat_more_than_it_hides():
    standing = retention.drawn_before([with_k("a", "p", 4), with_k("b", "p", 2)])
    assert standing["p"]["invisible"] == 2
    drawn = [a_row(f"n{at}") for at in range(5)]
    out = retention.repeat_draws(drawn, standing, pool=800)
    assert out["at_locations_with_deleted_rows"] == 5
    assert out["bound"] == 2, "five draws, two hidden recipes"
    assert 0 < out["expected"] < 1


def test_the_price_is_reported_and_never_prevented():
    """A counter that refused a draw would be the index this rule exists to not
    keep, wearing a different name. It reports; the leg renders anyway."""
    import inspect

    source = inspect.getsource(retention.repeat_draws)
    for forbidden in ("raise", "continue  # skip", "known"):
        assert forbidden not in source.replace("if not held", ""), forbidden


# --------------------------------------------------------------------------- #
# Over the real store.
# --------------------------------------------------------------------------- #
@pytest.mark.slow
def test_every_ledger_row_can_be_spelled_as_a_render_key_for_the_label_join(tracked_ledger):
    """A row that cannot be keyed could never be found to carry a label, and
    would be dropped as unlabeled without anything saying so.

    Whole-store on purpose — the claim is about every row, and once the reading
    is the session's the sweep itself is arithmetic. See `conftest.tracked_ledger`.
    """
    rows = tracked_ledger.rows
    unkeyable = [row["key"] for row in rows if retention.render_key_of(row) is None]
    assert unkeyable == [], f"{len(unkeyable)} of {len(rows)} rows cannot be keyed"


@pytest.mark.slow
def test_the_policy_keeps_every_human_labeled_row_on_the_real_store(tracked_ledger):
    from fractal_wallpapers.curation import candidate_ledger

    rows = tracked_ledger.rows
    scores = {
        key: float(row.get("p_ge4") or 0.0)
        for key, row in candidate_ledger.scores_by_recipe(tracked_ledger.scores).items()
    }
    labeled = retention.labeled_renders()
    out = retention.decide(rows, scores)
    # The label is a PROTECTION and not part of the ranking, so what is pinned
    # here is that the store applies it: `candidate_ledger.RETAINED_LABELED` is
    # the reason, and a labeled row the rank dropped must be carried by it.
    ranked = {key for key, why in out.items() if retention.kept(why)}
    marked = {str(row["key"]) for row in rows if retention.render_key_of(row) in labeled}
    assert marked, "the store holds no human-labeled row, so this pins nothing"
    assert marked - ranked, (
        "every labeled row is already inside the rank, so this cannot tell whether the "
        "protection is applied at all"
    )


def test_a_mode_under_its_own_settings_is_its_own_pair():
    """Otherwise the prune deletes a variant sweep in the transaction that admits it.

    `mode_params` is keyed in the recipe, so `direct_trap_multiply@opacity=0.6` is
    a different picture in exactly the sense `direct_trap_screen` is. Sharing one
    pair's three seats with the shipped mode is not neutral: the rank key ranks by
    what the judge thinks, and on this mode the judge rewards the whitewash the
    settings exist to fix, so the shipped rows win and the tinted ones go.
    """

    def row(mode, params):
        return {"location": {"key": "p"}, "recipe": {"mode": mode, "mode_params": params}}

    pairs = {
        retention._pair_of(row("direct_trap_multiply", {})),
        retention._pair_of(row("direct_trap_multiply", {"opacity": 0.6})),
        retention._pair_of(row("direct_trap_multiply", {"threshold": 0.2})),
        retention._pair_of(row("direct_trap_multiply", {"opacity": 0.6, "threshold": 0.2})),
    }
    assert len(pairs) == 4, "five colorings at a place are not one pair"


def test_a_row_carrying_no_settings_keeps_the_pair_it_has_always_had():
    """The whole store predates settings, so re-grouping any of it would be a
    silent re-prune of two hundred thousand rows. `spelled` is the bare mode
    wherever there are none, and this is that promise as an assertion."""
    for absent in ({}, None):
        assert retention._pair_of(
            {"location": {"key": "p"}, "recipe": {"mode": "smooth", "mode_params": absent}}
        ) == ("p", "smooth")
    assert retention._pair_of({"location": {"key": "p"}, "recipe": {"mode": "smooth"}}) == (
        "p",
        "smooth",
    )


# --------------------------------------------------------------------------- #
# The free-slot arithmetic.
# --------------------------------------------------------------------------- #
def test_free_slots_is_the_keep_less_what_the_pair_holds_and_omits_the_full_ones():
    """`K - len(pair)`, and a pair with no room is absent rather than zero.

    Absent and not zero because the mapping is *where there is room*: a caller
    that iterates it is planning, and a full pair carried at zero is a pair a
    loop can plan onto by forgetting one comparison. That is the shape of the
    `thin2_b_near` failure — 13,265 rows rendered onto pairs already at the keep,
    39 kept — expressed in a data structure instead of in a manifest.
    """
    rows = (
        [a_row(f"p-smooth-{at}", place="p", mode="smooth") for at in range(2)]
        + [a_row(f"q-smooth-{at}", place="q", mode="smooth") for at in range(5)]
        + [a_row("r-stripe-0", place="r", mode="stripe")]
    )
    slots = retention.free_slots(rows, keep=5)
    assert slots == {("p", "smooth"): 3, ("r", "stripe"): 4}
    assert ("q", "smooth") not in slots, "a pair at the keep has no room and is not listed"


def test_free_slots_defaults_to_the_stores_constant_and_is_not_a_copy_of_its_value():
    """The same rule the prune will actually apply, read through the same door."""
    from fractal_wallpapers.curation import candidate_ledger

    keep = candidate_ledger.RETAIN_PER_PAIR
    rows = [a_row("only", place="p", mode="smooth")]
    assert retention.free_slots(rows) == {("p", "smooth"): keep - 1}
    assert retention.free_slots(rows, keep=keep) == retention.free_slots(rows)


def test_a_pair_is_the_coloring_and_not_the_bare_mode():
    """`_pair_of`'s spelling, reached through the arithmetic that plans on it.

    A mode drawn under its own settings is its own pair, so it has its own slots.
    A free-slot count that flattened the settings away would tell a variant sweep
    it had no room at a place where it has a whole keep of it.
    """
    rows = [
        a_row("bare", place="p", mode="direct_trap_multiply"),
        a_row("set", place="p", mode="direct_trap_multiply"),
    ]
    rows[1]["recipe"]["mode_params"] = {"opacity": 0.6}
    slots = retention.free_slots(rows, keep=3)
    assert len(slots) == 2, "the settings make a second pair, and it has its own room"
    assert set(slots.values()) == {2}


def test_the_free_slot_census_counts_pairs_slots_and_places_apart():
    """Three numbers that have each been quoted for another. 37.7% of *pairs*
    held fewer than three on 2026-09-06 while the rows in them were 24.4% of the
    ledger, and a sentence that says "of the pool" is wrong by half."""
    rows = [
        a_row("p-smooth-0", place="p", mode="smooth"),
        a_row("p-stripe-0", place="p", mode="stripe"),
        a_row("q-smooth-0", place="q", mode="smooth"),
    ]
    census = retention.free_slot_census(rows, keep=3)
    assert census["pairs_with_room"] == 3
    assert census["free_slots"] == 6
    assert census["places_with_room"] == 2, "one place carrying two pairs is one place"
    assert census["keep"] == 3


def test_free_slots_reads_a_stream_once_and_never_scans_for_what_was_pruned():
    """It is a subtraction over rows in hand, so a generator is enough.

    `decide` keeps `min(K, attempts)` with no branch on how many the pair holds,
    so a pair under the keep never had more — there is nothing to go and look
    for, and needing to look would mean the rule had stopped being one-sided.
    """
    made = (a_row(f"k{at}", place=f"p{at}", mode="smooth") for at in range(4))
    assert sum(retention.free_slots(made, keep=2).values()) == 4
