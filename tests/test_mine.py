"""The mine: where the primed boundary is read, how the three arms draw, what the clock says.

Everything here is arithmetic over records, like [`test_hunt`] and for the same
reason: away from the two seconds a render takes, the module is draws over tables
and tallies over rows. So there is a fake ledger, a fake scan index and a fake
head sidecar, and never a picture.

The two properties worth pinning hardest are the ones a readout would be wrong
without. **PRIMED is derived**: no row carries it, [`mine.primed`] takes the bar
as an argument, and the same rows read at two bars give two answers. **The two
breadth arms differ only in the draw**: they are matched on partition by
construction, they never share a location, and the ranked one orders on the
location head within a partition and never across one — a pooled sort would
compare heights that are not on one scale, and a comparison of a mine's arms
built on that would be a comparison of nothing.
"""

from __future__ import annotations

import pytest

from fractal_wallpapers.curation import mine

# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
PARTITIONS = ("mandelbrot", "phoenix", "julia:mandelbrot")


def ledger_row(key, location, partition="mandelbrot", mode="smooth", colormap="viridis"):
    """One ledger row, thinned to the members a mine reads off it."""
    return {
        "schema": 1,
        "key": key,
        "recipe_key": key,
        "partition": partition,
        "location": {"key": location},
        "recipe": {"mode": mode, "colormap": colormap},
    }


def made_row(arm, location, p_ge4, *, k=1, band="near", partition="mandelbrot", seconds=1.0):
    """One row of what a mine made, as [`mine.arm_readout`] reads it."""
    return {
        "key": f"{arm}-{location}-{k}",
        "arm": arm,
        "band": band,
        "k": k,
        "location": location,
        "partition": partition,
        "mode": "smooth",
        "mode_kind": "field",
        "colormap": "viridis",
        "palette_group": "map:viridis",
        "p_ge4": p_ge4,
        "p_ge3": min(1.0, p_ge4 + 0.05),
        "seconds": seconds,
        "acted": False,
        "cells": [],
    }


def pools(counts):
    """`{partition: [places]}` at the given depths, keys unique across partitions."""
    return {
        name: [{"key": f"{name}-{at}", "partition": name} for at in range(count)]
        for name, count in counts.items()
    }


# --------------------------------------------------------------------------- #
# The boundary is derived, and takes its height as an argument.
# --------------------------------------------------------------------------- #
def test_primed_is_a_function_of_the_bar_and_not_of_a_stored_flag():
    readings = [0.10, 0.62, 0.88]
    assert mine.primed(readings, bar=0.50)
    assert not mine.primed(readings, bar=0.90)


def test_a_location_with_no_candidate_is_not_primed_at_any_bar():
    assert not mine.primed([], bar=0.0)


def test_best_by_location_keeps_the_mode_the_best_candidate_was_drawn_in():
    rows = [
        ledger_row("a", "place-1", mode="smooth"),
        ledger_row("b", "place-1", mode="threads"),
        ledger_row("c", "place-2", mode="itinerary"),
    ]
    best = mine.best_by_location(rows, {"a": 0.2, "b": 0.91, "c": 0.4})
    assert best["place-1"]["best"] == pytest.approx(0.91)
    assert best["place-1"]["best_mode"] == "threads"
    assert best["place-1"]["count"] == 2
    assert best["place-2"]["best_mode"] == "itinerary"


def test_a_location_whose_candidates_are_all_unscored_still_carries_a_mode():
    """A missing score reads as zero, and the location is still drawable by DEEPEN."""
    best = mine.best_by_location([ledger_row("a", "place-1", mode="tia")], {})
    assert best["place-1"]["best"] == pytest.approx(0.0)
    assert best["place-1"]["best_mode"] == "tia"


def test_taken_maps_is_keyed_by_location_and_mode_together():
    rows = [
        ledger_row("a", "place-1", mode="smooth", colormap="viridis"),
        ledger_row("b", "place-1", mode="threads", colormap="magma"),
    ]
    taken = mine.taken_maps(rows)
    assert taken[("place-1", "smooth")] == {"viridis"}
    assert taken[("place-1", "threads")] == {"magma"}


# --------------------------------------------------------------------------- #
# The DEEPEN draw.
# --------------------------------------------------------------------------- #
def test_deepen_offers_no_map_the_place_already_carries_in_that_mode():
    places = [{"key": "place-1", "partition": "mandelbrot", "best_mode": "smooth"}]
    taken = {("place-1", "smooth"): {"viridis", "magma"}}
    units = mine.plan_deepen(places, taken, ["viridis", "magma", "cividis"], 7, 3, "near")
    assert [unit.colormap for unit in units] == ["cividis"]
    assert units[0].k == 1


def test_deepen_holds_the_mode_and_numbers_the_palettes_from_one():
    places = [{"key": "place-1", "partition": "phoenix", "best_mode": "threads"}]
    units = mine.plan_deepen(places, {}, list("abcdef"), 7, 4, "over")
    assert {unit.mode for unit in units} == {"threads"}
    assert [unit.k for unit in units] == [1, 2, 3, 4]
    assert len({unit.colormap for unit in units}) == 4
    assert {unit.band for unit in units} == {"over"}


def test_deepen_skips_a_place_whose_best_candidate_names_no_mode():
    places = [{"key": "place-1", "partition": "mandelbrot", "best_mode": None}]
    assert mine.plan_deepen(places, {}, list("abc"), 7, 3, "near") == []


def test_deepen_draws_only_inside_its_band_and_only_where_the_location_is_admitted():
    """The bound is `world["by_key"]` — a row to render from — and never a frame row.

    `unframed` is in the admitted population and carries no framing row, and the
    arm draws it: it renders at the frame its own store row already holds.
    """
    best = {
        "in-band": {"best": 0.7, "partition": "mandelbrot", "best_mode": "smooth", "count": 1},
        "over-band": {"best": 0.95, "partition": "mandelbrot", "best_mode": "smooth", "count": 1},
        "unframed": {"best": 0.7, "partition": "phoenix", "best_mode": "smooth", "count": 1},
        "gone": {"best": 0.7, "partition": "phoenix", "best_mode": "smooth", "count": 1},
    }
    by_key = dict.fromkeys(("in-band", "over-band", "unframed"), {})
    drawn = mine.deepen_places(best, by_key, mine.NEAR_BAND, seed=3, count=10)
    assert sorted(row["key"] for row in drawn) == ["in-band", "unframed"]


# --------------------------------------------------------------------------- #
# The two breadth arms differ in the draw and in nothing else.
# --------------------------------------------------------------------------- #
def test_ranked_orders_on_the_head_inside_a_partition_and_never_across_one():
    held = pools({"mandelbrot": 3, "phoenix": 3})
    head = {
        "mandelbrot-0": {"p_ge3": 0.1},
        "mandelbrot-1": {"p_ge3": 0.9},
        "mandelbrot-2": {"p_ge3": 0.5},
        "phoenix-0": {"p_ge3": 0.2},
        "phoenix-1": {"p_ge3": 0.8},
        "phoenix-2": {"p_ge3": 0.4},
    }
    drawn = [row["key"] for row in mine.ranked_places(held, head, seed=1, count=4)]
    # Round-robin over partitions, best-first inside each: a pooled sort would
    # have taken mandelbrot-1, phoenix-1, mandelbrot-2 in that order and left
    # the second partition's turn to the third round.
    assert drawn == ["mandelbrot-1", "phoenix-1", "mandelbrot-2", "phoenix-2"]


def test_a_location_the_head_cannot_score_sorts_last_rather_than_being_dropped():
    held = pools({"mandelbrot": 2})
    drawn = mine.ranked_places(held, {"mandelbrot-1": {"p_ge3": 0.3}}, seed=1, count=2)
    assert [row["key"] for row in drawn] == ["mandelbrot-1", "mandelbrot-0"]


def test_both_breadth_arms_here_run_under_the_standing_partition_weights():
    """The arms are spelled `breadth_ranked` and `breadth_flat`, so they are
    breadth arms and inherit the table [`curation.draw_weights`] holds. A mine is
    a measurement of what a route costs and takes no weight of its own; what it
    must not do is price a route under a draw the rest of the project has stopped
    taking."""
    from fractal_wallpapers.curation import draw_weights

    held = pools({"mandelbrot": 40, "phoenix": 40})
    head = {str(row["key"]): {"p_ge3": 0.5} for rows in held.values() for row in rows}
    drawn = mine.ranked_places(held, head, seed=1, count=20, weights=draw_weights.table())
    tally = {name: sum(1 for row in drawn if row["partition"] == name) for name in held}
    assert tally["phoenix"] > 0, "a weight is never a gate"
    assert tally["phoenix"] * 2 < tally["mandelbrot"], tally


def test_an_unweighted_mine_draw_is_the_round_robin_it_always_was():
    held = pools({"mandelbrot": 3, "phoenix": 3})
    head = {str(row["key"]): {"p_ge3": 0.5} for rows in held.values() for row in rows}
    drawn = [row["partition"] for row in mine.ranked_places(held, head, seed=1, count=4)]
    assert drawn == ["mandelbrot", "phoenix", "mandelbrot", "phoenix"]


def test_flat_takes_exactly_the_per_partition_counts_it_is_matched_to():
    held = pools({"mandelbrot": 20, "phoenix": 20, "julia:mandelbrot": 20})
    drawn = mine.flat_places(held, seed=5, want={"mandelbrot": 4, "phoenix": 2})
    counts = {name: 0 for name in PARTITIONS}
    for row in drawn:
        counts[row["partition"]] += 1
    assert counts == {"mandelbrot": 4, "phoenix": 2, "julia:mandelbrot": 0}


def test_a_partition_that_cannot_fill_its_quota_leaves_the_shortfall_rather_than_borrowing():
    held = pools({"mandelbrot": 1, "phoenix": 9})
    drawn = mine.flat_places(held, seed=5, want={"mandelbrot": 4, "phoenix": 4})
    assert sum(1 for row in drawn if row["partition"] == "mandelbrot") == 1
    assert sum(1 for row in drawn if row["partition"] == "phoenix") == 4


class Wheel:
    """[`hunt.Stratifier`] without the carrier table: the maps in turn, one cell.

    The real one asks `palettes.carriers` which maps make a codebook cell, which
    is a tracked table and a slow read. What this test is about is that the two
    breadth arms are offered the same sequence, and any deterministic wheel shows
    that.
    """

    def __init__(self, _cells, pool, _seed):
        self.pool = list(pool)
        self.at = 0

    def next(self):
        name = self.pool[self.at % len(self.pool)]
        self.at += 1
        return "dark_vivid_lime", name


def test_both_breadth_arms_are_offered_the_same_modes_and_colours_at_a_shared_key(monkeypatch):
    """The arms are the built path with the draw swapped, so the draw is all that differs."""
    monkeypatch.setattr(mine.hunt, "Stratifier", Wheel)
    maps = [f"map{at}" for at in range(40)]
    one = mine.plan_breadth(mine.RANKED, pools({"mandelbrot": 2})["mandelbrot"], maps, 11, 3)
    other = mine.plan_breadth(mine.FLAT, pools({"mandelbrot": 2})["mandelbrot"], maps, 11, 3)
    assert len(one) == 6
    assert [(u.location, u.mode, u.colormap, u.k) for u in one] == [
        (u.location, u.mode, u.colormap, u.k) for u in other
    ]
    assert {u.arm for u in one} == {mine.RANKED}
    assert {u.arm for u in other} == {mine.FLAT}


def test_a_breadth_arms_cell_ask_reaches_the_ledger_row_as_drawn_for(monkeypatch):
    """**The ask, under the name every reader looks it up by.**

    `hunt.Stratifier` asks a breadth arm for a cell, and until 2026-09-15 that ask
    went into `Unit.band` alone — a free-text field a deepen arm fills with a band
    name — so `hunt.drawn_for` read null on every row this module ever made, and
    the exact separator `curation/GALLERY.md` names for reading an unconditioned
    rate was unavailable over them. `band` still carries it for the readouts that
    group on it; the row now carries it too.
    """
    from fractal_wallpapers.curation import candidate_ledger

    monkeypatch.setattr(mine.hunt, "Stratifier", Wheel)
    maps = [f"map{at}" for at in range(40)]
    drawn = mine.plan_breadth(mine.FLAT, pools({"mandelbrot": 2})["mandelbrot"], maps, 11, 3)
    assert drawn, "the fixture has to plan something or this pins nothing"
    assert {unit.cell for unit in drawn} == {"dark_vivid_lime"}
    assert {unit.named()["drawn_for"] for unit in drawn} == {"dark_vivid_lime"}
    # Through the door the row actually goes through, because `hunt_block` is what
    # decides whether the field lands and it is the function that dropped it once.
    block = candidate_ledger.hunt_block({"seconds": 0.1, **drawn[0].named()})
    assert block["drawn_for"] == "dark_vivid_lime"


def test_an_arm_that_asked_for_no_cell_writes_the_block_it_always_wrote():
    """The unnarrowed row does not move: a falsy ask is dropped, not spelled null.

    `plan_deepen` holds the place's own mode and asks for no colour at all, so its
    rows carry the two fields this block has always carried and nothing more.
    """
    from fractal_wallpapers.curation import candidate_ledger

    unit = mine.Unit(
        arm=mine.DEEPEN,
        location="loc",
        partition="mandelbrot",
        mode="smooth",
        colormap="viridis",
        k=1,
        band="band03",
    )
    assert unit.cell is None and unit.named()["drawn_for"] is None
    assert candidate_ledger.hunt_block({"seconds": 0.1, **unit.named()}) == {
        "seconds": 0.1,
        "k": 1,
    }


# --------------------------------------------------------------------------- #
# The weave: every prefix holds the arms in proportion.
# --------------------------------------------------------------------------- #
def test_every_prefix_of_the_woven_plan_holds_the_arms_in_their_shares():
    plans = {arm: [made_row(arm, f"{arm}-{at}", 0.0) for at in range(400)] for arm in mine.ARMS}
    woven = mine.weave({arm: rows for arm, rows in plans.items()})
    assert len(woven) == 1200
    for cut in (120, 400, 800):
        prefix = woven[:cut]
        for arm, share in mine.SHARES.items():
            seen = sum(1 for row in prefix if row["arm"] == arm) / cut
            assert seen == pytest.approx(share, abs=0.02), (arm, cut, seen)


def test_an_arm_with_nothing_planned_does_not_break_the_weave():
    woven = mine.weave({mine.DEEPEN: [1, 2, 3], mine.RANKED: [], mine.FLAT: []})
    assert woven == [1, 2, 3]


# --------------------------------------------------------------------------- #
# The stopwatch.
# --------------------------------------------------------------------------- #
def a_render(seconds: float) -> dict:
    """A meter for one candidate whose whole render was a single colouring."""
    return {"dump": 0.0, "paint": seconds, "measure": 0.0, "repaint": 0.0}


def test_the_stages_of_one_candidate_sum_to_its_seconds():
    stages = mine.Stages(judge=0.25, colour=0.1, write=0.01, overhead=0.04)
    stages.take({"dump": 0.5, "paint": 0.6, "measure": 0.3, "repaint": 0.1})
    assert stages.render == pytest.approx(1.5)
    assert stages.total() == pytest.approx(1.9)
    assert sum(stages.named().values()) == pytest.approx(1.9)


def test_the_render_total_is_derived_from_its_parts_and_never_measured_beside_them():
    """The old profile had one `render` number and could say nothing about what was
    inside it. A total measured separately from its parts is one that can disagree
    with them, which is the way a profile stops being checkable."""
    assert "render" not in mine.Stages().named()
    stages = mine.Stages()
    stages.take({"dump": 1.0, "paint": 2.0, "measure": 0.5, "repaint": 0.25})
    assert stages.render == pytest.approx(3.75)
    from fractal_wallpapers.curation import colorize

    assert set(colorize.METER_STAGES) <= set(mine.Stages().named()), (
        "a stage the render meters is one the profile has to be able to name"
    )


def test_the_clock_attributes_the_same_seconds_to_every_cut_it_is_given():
    clock = mine.Clock()
    first = mine.Stages(judge=0.5)
    first.take(a_render(2.0))
    second = mine.Stages(judge=0.5)
    second.take(a_render(1.0))
    clock.add(first, {"arm": "deepen", "partition": "phoenix"})
    clock.add(second, {"arm": "deepen", "partition": "mandelbrot"})
    table = clock.table()
    assert table["total_seconds"] == pytest.approx(4.0)
    assert table["by_stage"]["paint"]["share"] == pytest.approx(0.75)
    assert table["by_cut"]["arm=deepen"]["candidates"] == 2
    assert table["by_cut"]["arm=deepen"]["seconds"] == pytest.approx(4.0)
    assert table["by_cut"]["partition=phoenix"]["per_candidate"] == pytest.approx(2.5)


# --------------------------------------------------------------------------- #
# The readout.
# --------------------------------------------------------------------------- #
def test_one_set_of_rows_reads_out_at_two_bars_with_two_answers():
    made = [
        made_row(mine.RANKED, "place-1", 0.95),
        made_row(mine.RANKED, "place-2", 0.62),
        made_row(mine.RANKED, "place-3", 0.01),
    ]
    block = mine.arm_readout(made)[mine.RANKED]
    assert block["bar_090"]["locations_primed"] == 1
    assert block["bar_050"]["locations_primed"] == 2
    assert block["locations"] == 3


def test_a_deepen_arm_cannot_claim_a_place_that_was_already_over_the_bar():
    made = [made_row(mine.DEEPEN, "place-1", 0.97, k=1)]
    world = {"best": {"place-1": {"best": 0.99, "partition": "mandelbrot"}}}
    block = mine.arm_readout(made, world)[mine.DEEPEN]
    assert block["bar_090"]["locations_primed"] == 1
    assert block["bar_090"]["locations_newly_primed"] == 0


def test_a_deepen_arm_claims_a_place_its_own_candidate_converted():
    made = [made_row(mine.DEEPEN, "place-1", 0.97, k=2)]
    world = {"best": {"place-1": {"best": 0.61, "partition": "mandelbrot"}}}
    block = mine.arm_readout(made, world)[mine.DEEPEN]
    assert block["bar_090"]["locations_newly_primed"] == 1


def test_seconds_per_primed_is_none_rather_than_a_division_by_zero():
    made = [made_row(mine.FLAT, "place-1", 0.02)]
    block = mine.arm_readout(made)[mine.FLAT]
    assert block["bar_090"]["locations_primed"] == 0
    assert block["bar_090"]["seconds_per_primed"] is None
    assert block["bar_090"]["candidates_per_primed"] is None


def test_the_marginal_curve_is_cumulative_over_k_and_never_falls():
    made = [
        made_row(mine.DEEPEN, "place-1", 0.1, k=1),
        made_row(mine.DEEPEN, "place-1", 0.95, k=2),
        made_row(mine.DEEPEN, "place-1", 0.2, k=3),
        made_row(mine.DEEPEN, "place-2", 0.3, k=1),
        made_row(mine.DEEPEN, "place-2", 0.4, k=2),
        made_row(mine.DEEPEN, "place-2", 0.99, k=3),
    ]
    curve = mine.marginal(made)["near"]["bar_090"]
    assert [row["cumulative_primed"] for row in curve] == [0, 1, 2]
    assert [row["marginal_gain"] for row in curve] == [0.0, 0.5, 0.5]
    assert [row["cleared_at_k"] for row in curve] == [0, 1, 1]
    assert all(row["candidates_at_k"] == 2 for row in curve)


def test_the_two_deepen_bands_are_reported_apart():
    made = [
        made_row(mine.DEEPEN, "near-1", 0.95, k=1, band="near"),
        made_row(mine.DEEPEN, "over-1", 0.10, k=1, band="over"),
    ]
    curves = mine.marginal(made)
    assert curves["near"]["bar_090"][0]["cumulative_primed"] == 1
    assert curves["over"]["bar_090"][0]["cumulative_primed"] == 0


# --------------------------------------------------------------------------- #
# Ranked against flat, and where a route runs out.
# --------------------------------------------------------------------------- #
def arm_rows(arm, primed_by_partition, plain_by_partition):
    """One location a count, primed where asked and not otherwise."""
    rows = []
    for name in sorted(set(primed_by_partition) | set(plain_by_partition)):
        for at in range(primed_by_partition.get(name, 0)):
            rows.append(made_row(arm, f"{arm}-{name}-hit{at}", 0.97, partition=name))
        for at in range(plain_by_partition.get(name, 0)):
            rows.append(made_row(arm, f"{arm}-{name}-miss{at}", 0.01, partition=name))
    return rows


def test_the_stratified_difference_ignores_a_partition_only_one_arm_reached():
    """A stratum with no control contributes no weight, rather than a pooled artefact."""
    made = arm_rows(mine.RANKED, {"mandelbrot": 5, "phoenix": 9}, {"mandelbrot": 5})
    made += arm_rows(mine.FLAT, {"mandelbrot": 2}, {"mandelbrot": 8})
    block = mine.compare(made, bars=(0.90,), draws=200)["bar_090"]
    assert block["by_partition"]["mandelbrot"]["difference"] == pytest.approx(0.30)
    assert block["by_partition"]["phoenix"]["difference"] is None
    assert block["stratified_difference"] == pytest.approx(0.30)
    # Pooled counts phoenix's nine unmatched hits and says 0.54 — 14 of 19 ranked
    # against 2 of 10 flat — which is the partitions' difference, not the arms'.
    assert block["pooled"]["difference"] == pytest.approx(0.5368, abs=1e-3)


def test_the_bootstrap_interval_covers_zero_when_the_arms_agree():
    made = arm_rows(mine.RANKED, {"mandelbrot": 5}, {"mandelbrot": 5})
    made += arm_rows(mine.FLAT, {"mandelbrot": 5}, {"mandelbrot": 5})
    block = mine.compare(made, bars=(0.90,), draws=1000)["bar_090"]
    assert block["stratified_difference"] == pytest.approx(0.0)
    assert block["ci95"]["low"] < 0.0 < block["ci95"]["high"]
    assert block["ci95"]["excludes_zero"] is False


def test_the_bootstrap_interval_clears_zero_on_a_wide_separation():
    made = arm_rows(mine.RANKED, {"mandelbrot": 40, "phoenix": 40}, {})
    made += arm_rows(mine.FLAT, {}, {"mandelbrot": 40, "phoenix": 40})
    block = mine.compare(made, bars=(0.90,), draws=1000)["bar_090"]
    assert block["stratified_difference"] == pytest.approx(1.0)
    assert block["ci95"]["excludes_zero"] is True


def test_a_route_whose_stock_is_too_small_is_reported_as_not_reaching_the_target():
    arms = mine.arm_readout(arm_rows(mine.RANKED, {"mandelbrot": 1}, {"mandelbrot": 9}))
    out = mine.extrapolate(arms, {mine.RANKED: 500, "owned_primed": 12}, target=1000)
    assert out[mine.RANKED]["primed_per_location"] == pytest.approx(0.1)
    assert out[mine.RANKED]["primed_the_stock_can_reach"] == 50
    assert out[mine.RANKED]["reaches_target"] is False
    assert out["already_owned"] == 12


def test_hours_to_target_is_seconds_a_location_over_primed_a_location():
    made = arm_rows(mine.RANKED, {"mandelbrot": 1}, {"mandelbrot": 9})
    for row in made:
        row["seconds"] = 3.6
    arms = mine.arm_readout(made)
    out = mine.extrapolate(arms, {mine.RANKED: 100_000}, target=1000)
    # Ten locations at 3.6 s each prime one, so a thousand cost 36,000 s.
    assert out[mine.RANKED]["hours_to_target"] == pytest.approx(10.0)
    assert out[mine.RANKED]["reaches_target"] is True


# --------------------------------------------------------------------------- #
# The renderer guard moved out of this file on 2026-09-08.
# --------------------------------------------------------------------------- #
# `test_the_two_makers_draw_the_same_picture_for_one_recipe` lived here because
# `mine.make` is where the dropped `mode_params` was found. It covered three
# renderers; the tree has eight, and four more were found dropping `curve` and
# `palette` in the same week. It is now `tests/test_renderer_agreement.py`,
# which holds every renderer to one recipe's bytes and holds its own registry
# to the tree — so the next renderer is covered without anybody remembering
# this file.


# --------------------------------------------------------------------------- #
# `--rate` reads itself off the mine records.
# --------------------------------------------------------------------------- #
def _mined(root, name: str, *, spent: float, made: int) -> None:
    """One mine record, thinned to the two members [`mine.measured_rate`] reads."""
    import json

    record = root / name / mine.RECORD_NAME
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps({"counts": {"made": int(made)}, "budget": {"spent": float(spent)}}),
        encoding="utf-8",
        newline="\n",
    )


@pytest.fixture
def mine_store(monkeypatch, tmp_path):
    """`under('curation', 'mine')` redirected at the tier root, `depth_store`'s shape."""
    monkeypatch.setattr(mine, "under", lambda *parts: tmp_path.joinpath(*map(str, parts)))
    return tmp_path / "curation" / mine.UNIT


def test_a_mine_rate_is_the_cheapest_spent_over_made_and_skips_a_killed_leg(mine_store):
    """A mine record carries no per-candidate figure, so it is derived; a leg that
    made almost nothing reports its own startup and prices nothing."""
    _mined(mine_store, "dear", spent=7169.41, made=5684)
    _mined(mine_store, "cheap", spent=198.17, made=247)
    _mined(mine_store, "killed", spent=40.0, made=4)
    rate, why = mine.measured_rate()
    assert (rate, why["leg"], why["priced"]) == (round(198.17 / 247, 4), "cheap", 2)


def test_a_machine_with_no_mine_record_plans_at_the_pilot_rate_and_says_so(mine_store):
    rate, why = mine.measured_rate()
    assert rate == mine.PILOT_RATE
    assert "leg" not in why and "PILOT_RATE" in why["why"]


def test_mine_plan_without_a_rate_plans_at_the_recorded_one(monkeypatch, capsys):
    """The `TypeError` at `build_plan`: `plan` handed `None` through. It resolves
    the rate first now, the way `curate depth plan` does, and prints where from."""
    import argparse

    from fractal_wallpapers.cli import curate_mine_commands

    asked = {}
    monkeypatch.setattr(mine, "measured_rate", lambda: (1.14, {"leg": "somewhere"}))
    monkeypatch.setattr(mine, "population", lambda: {})
    monkeypatch.setattr(
        mine, "build_plan", lambda world, **knobs: (asked.update(knobs), ([], {"ok": True}))[1]
    )
    args = argparse.Namespace(
        what="plan", seed=1, rate=None, budget=60.0, k=2, per_location=1, device="cpu"
    )
    assert curate_mine_commands.curate_mine(args) == 0
    assert asked["rate"] == 1.14
    assert '"rate_from"' in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# `package` and `unpack`: a leg carried from one box to another.
# --------------------------------------------------------------------------- #
def _leg(root, name: str, keys=("aaaa", "bbbb")) -> None:
    """A mined leg on disk: the four packed files, pictures, and what stays behind."""
    import json

    here = root / name
    (here / mine.PICTURES).mkdir(parents=True)
    (here / mine.FIELDS).mkdir()
    (here / mine.FIELDS / "one.f32").write_bytes(b"field")
    rows = [
        {
            "schema": 1,
            "key": key,
            "engine": "e1",
            "provenance": {"run": name, "candidate": f"{at:05d}"},
            "picture": f"artifacts/curation/mine/{name}/pictures/{key}.jpg",
        }
        for at, key in enumerate(keys, start=1)
    ]
    for file_name, held in (
        (mine.ROWS_NAME, rows),
        (mine.SCORES_NAME, [{"schema": 1, "recipe_key": key} for key in keys]),
        (mine.SEQUENCE_NAME, [{"schema": 1, "key": key} for key in keys]),
    ):
        (here / file_name).write_text(
            "".join(json.dumps(row) + "\n" for row in held), encoding="utf-8", newline="\n"
        )
    (here / "merge.json").write_text('{"name": "elsewhere"}\n', encoding="utf-8", newline="\n")
    (here / mine.RECORD_NAME).write_text("{}\n", encoding="utf-8", newline="\n")
    for key in keys[:-1]:
        (here / mine.PICTURES / f"{key}.jpg").write_bytes(key.encode())


@pytest.fixture
def carried(mine_store, monkeypatch, tmp_path):
    """A leg packaged out of one tree, and the tree emptied as a second box's would be."""
    import shutil

    monkeypatch.setattr(mine, "_live_engine", lambda: "e1")
    _leg(mine_store, "far")
    out = tmp_path / "package"
    manifest = mine.package("far", out, log=lambda *_: None)
    shutil.rmtree(mine_store / "far")
    return out, manifest


def test_a_package_carries_the_deliverable_subset_and_names_every_byte(carried):
    out, manifest = carried
    named = {row["path"] for row in manifest["files"]}
    assert named == {*mine.PACKED_FILES, "pictures/aaaa.jpg"}
    assert all(len(row["sha256"]) == 64 for row in manifest["files"])
    assert set(manifest["left_behind"]) == {mine.FIELDS, mine.RECORD_NAME}
    assert manifest["counts"] == {
        "rows_packed": 1,
        "rows_displaced_at_origin": 1,
        "scores": 1,
        "pictures": 1,
        "files": 5,
    }
    assert (manifest["name"], manifest["engine"], manifest["row_engines"]) == (
        "far",
        "e1",
        {"e1": 1},
    )
    assert (out / mine.PACKAGE_NAME).is_file() and not (out / mine.FIELDS).exists()


def test_a_package_drops_displaced_rows_as_their_own_bytes_and_only_after_a_merge(
    mine_store, monkeypatch, tmp_path
):
    """A pictureless row is a prune only when the leg merged; its survivors pack verbatim."""
    monkeypatch.setattr(mine, "_live_engine", lambda: "e1")
    _leg(mine_store, "far")
    merged = mine.package("far", tmp_path / "merged", log=lambda *_: None)
    source_line = (mine_store / "far" / mine.ROWS_NAME).read_text(encoding="utf-8").splitlines()[0]
    assert (tmp_path / "merged" / mine.ROWS_NAME).read_text(encoding="utf-8") == source_line + "\n"
    assert merged["counts"]["rows_displaced_at_origin"] == 1
    (mine_store / "far" / "merge.json").unlink()
    unmerged = mine.package("far", tmp_path / "unmerged", log=lambda *_: None)
    assert (unmerged["counts"]["rows_packed"], unmerged["counts"]["rows_displaced_at_origin"]) == (
        2,
        0,
    )
    assert (tmp_path / "unmerged" / mine.ROWS_NAME).read_bytes() == (
        mine_store / "far" / mine.ROWS_NAME
    ).read_bytes()


def test_unpack_lands_a_package_ready_for_merge_with_the_origin_merge_renamed(carried, mine_store):
    out, _manifest = carried
    record = mine.unpack(out, log=lambda *_: None)
    here = mine_store / "far"
    assert record["verified"] and record["name"] == "far" and record["engine_agrees"]
    assert (record["rows"], record["pictures"], record["rows_with_no_picture"]) == (1, 1, 0)
    assert (here / mine.ROWS_NAME).is_file() and (here / "pictures" / "aaaa.jpg").is_file()
    assert (here / mine.ORIGIN_MERGE_NAME).is_file() and not (here / "merge.json").exists()
    assert not (here / mine.PACKAGE_NAME).exists() and (here / mine.UNPACKED_NAME).is_file()


def test_unpack_refuses_a_changed_or_an_unnamed_file_and_writes_nothing(carried, mine_store):
    out, _manifest = carried
    (out / "pictures" / "aaaa.jpg").write_bytes(b"other")
    with pytest.raises(mine.MineRefused, match="does not match its manifest"):
        mine.unpack(out, log=lambda *_: None)
    (out / "pictures" / "aaaa.jpg").write_bytes(b"aaaa")
    (out / "pictures" / "stray.jpg").write_bytes(b"x")
    with pytest.raises(mine.MineRefused, match="not named"):
        mine.unpack(out, log=lambda *_: None)
    assert not (mine_store / "far").exists()
    assert not any(mine_store.glob("*.unpacking"))


def test_unpack_refuses_a_leg_this_box_already_holds(carried, mine_store):
    out, _manifest = carried
    (mine_store / "far").mkdir(parents=True)
    with pytest.raises(mine.MineRefused, match="already exists"):
        mine.unpack(out, log=lambda *_: None)


def test_a_manifest_less_directory_is_refused_unless_asked_and_then_said_unverified(
    carried, mine_store
):
    out, _manifest = carried
    (out / mine.PACKAGE_NAME).unlink()
    with pytest.raises(mine.MineRefused, match="--without-manifest"):
        mine.unpack(out, log=lambda *_: None)
    said = []
    record = mine.unpack(out, without_manifest=True, log=said.append)
    assert not record["verified"] and "UNVERIFIED" in record["warning"]
    assert any("UNVERIFIED" in line for line in said)
    assert record["name"] == "far" and (mine_store / "far" / mine.ROWS_NAME).is_file()


def test_unpack_refuses_a_name_the_rows_do_not_carry(carried):
    out, _manifest = carried
    with pytest.raises(mine.MineRefused, match="lands under that name"):
        mine.unpack(out, name="near", log=lambda *_: None)


# --------------------------------------------------------------------------- #
# `bench` hands `mine run` one --rate, weighted by the plan it would draw.
# --------------------------------------------------------------------------- #
def _block(kind, before, dump=None, recolour=None, judge=0.8):
    shared = (
        {"available": True, "dump_seconds": dump, "leveled_recolour_per_map": recolour}
        if dump is not None
        else {"available": False}
    )
    return {
        "mode_kind": kind,
        "built_leveled_per_map": before,
        "shared_field": shared,
        "judge_one_at_a_time": judge,
    }


def _unit(arm, location, mode, k=1):
    return mine.Unit(arm, location, "mandelbrot", mode, "viridis", k, "near")


def test_the_weighted_rate_prices_each_candidate_at_its_kind_and_its_own_width():
    blocks = [_block("field", 1.0, dump=0.8, recolour=0.1), _block("composite", 2.0)]
    units = [
        *(_unit(mine.DEEPEN, "a", "smooth", k) for k in range(1, 5)),  # width 4: 0.2 + 0.1
        _unit(mine.RANKED, "b", "smooth"),  # width 1: 0.8 + 0.1
        _unit(mine.FLAT, "c", "tia"),  # composite, no field: 2.0
    ]
    kinds = {"smooth": "field", "tia": "composite"}
    rate = mine.rate_for_plan(
        blocks, units, maps=8, kind_of=kinds.get, shareable=lambda mode: mode == "smooth"
    )
    render = (4 * 0.3 + 0.9 + 2.0) / 6
    assert rate["render_seconds"] == round(render, 4)
    assert rate["judge_seconds"] == 0.1
    assert rate["rate_seconds"] == round(render + 0.1, 4)
    assert rate["by_arm"][mine.DEEPEN] == {"candidates": 4, "seconds": 0.4}
    assert rate["candidates"] == 6


def test_a_kind_the_bench_did_not_measure_is_priced_by_whether_it_can_share_a_field():
    blocks = [_block("field", 1.0, dump=0.8, recolour=0.1), _block("composite", 2.0, judge=0.0)]
    units = [_unit(mine.FLAT, "c", "direct_trap_lines")]
    rate = mine.rate_for_plan(
        blocks, units, maps=8, kind_of=lambda mode: "direct", shareable=lambda mode: False
    )
    assert rate["render_seconds"] == 2.0
