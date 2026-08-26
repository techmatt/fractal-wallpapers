"""The hunt: which frame it draws at, which places and colours it asks for, what it costs.

Everything here is arithmetic over records, which is what the module is made of
away from the two seconds a render takes. The frame is a **lookup** in a scan
record, the two legs are draws over tables, the budget is a comparison against a
measured price, and the ledger row is built from members that are all known
before the engine runs — so a test needs a fake scan row and a fake location, and
never a picture.

The one thing that cannot be checked this way is that a candidate's *pixels* come
out of [`colorize.render`] like every other candidate's. That is checked by
construction instead: [`hunt.Maker.make`] has no other render path, and the
recipe it names the picture by is the one the ledger stores.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.curation import candidate_ledger, hunt, recipes

# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
ORIGINAL = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}
REFINED = {"center_re": "0.1", "center_im": "0.2", "width": "0.707"}


def scan_row(key="place-a", *, adopted=True, partition="mandelbrot", margin=None):
    """One row of the pool-wide refinement scan, thinned to what a hunt reads."""
    return {
        "schema": 1,
        "key": key,
        "partition": partition,
        "margin": hunt.framing.MARGIN if margin is None else margin,
        "adopted": adopted,
        "winner": "w1.414_c" if adopted else None,
        "gain": 4.5 if adopted else None,
        "original": {"slug": "w1_c", "viewport": ORIGINAL, "maxiter": 1000},
        "rungs": [
            {"slug": "w1_c", "viewport": ORIGINAL, "maxiter": 1000},
            {"slug": "w1.414_c", "viewport": REFINED, "maxiter": 900},
        ],
    }


def place(key="place-a", partition="mandelbrot"):
    """One embedding-store row, thinned the same way."""
    return {
        "key": key,
        "partition": partition,
        "family": {"kind": "mandelbrot", "degree": 2},
        "ledger": "artifacts/harvest_run10/walk.jsonl",
    }


def pools(counts):
    """`{partition: [places]}` at the given depths, keys unique across partitions."""
    return {
        name: [place(f"{name}-{at}", name) for at in range(count)] for name, count in counts.items()
    }


# --------------------------------------------------------------------------- #
# The frame is a lookup.
# --------------------------------------------------------------------------- #
def test_an_adopted_scan_row_is_drawn_at_the_winning_rung():
    """The frame the scan chose, with both sides on the block a ledger row wants."""
    chosen = hunt.chosen_frame(scan_row(adopted=True))
    assert chosen["viewport"] == REFINED
    assert chosen["maxiter"] == 900
    assert (chosen["used"], chosen["adopted"]) == ("refined", True)
    assert chosen["original_viewport"] == ORIGINAL


def test_a_refused_scan_row_is_drawn_at_the_frame_on_record():
    """No refinement machinery runs here, so a refusal is the recorded frame."""
    chosen = hunt.chosen_frame(scan_row(adopted=False))
    assert chosen["viewport"] == ORIGINAL
    assert chosen["maxiter"] == 1000
    assert (chosen["used"], chosen["adopted"]) == ("original", False)
    assert chosen["refined_viewport"] is None


def test_a_winner_with_no_rung_by_that_name_is_refused():
    """A frame nothing can look up is not a frame a candidate may be recorded at."""
    row = scan_row()
    row["rungs"] = [rung for rung in row["rungs"] if rung["slug"] != row["winner"]]
    with pytest.raises(hunt.HuntRefused, match="cannot be looked up"):
        hunt.chosen_frame(row)


def test_a_scan_taken_at_another_margin_is_refused_rather_than_reinterpreted(monkeypatch, tmp_path):
    """The margin is a property of the record; re-deciding it is a read of every rung."""
    scan = tmp_path / "scan.jsonl"
    scan.write_text(json.dumps(scan_row(margin=3.0)) + "\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(hunt, "scan_path", lambda: scan)
    monkeypatch.setattr(hunt, "frames_path", lambda: tmp_path / "frames.jsonl")
    with pytest.raises(hunt.HuntRefused, match="was taken at margin 3.0"):
        hunt.build_frames(log=lambda *_: None)


def test_the_frame_index_round_trips_what_the_scan_chose(monkeypatch, tmp_path):
    """One row a location, the chosen frame, and the margin it was chosen at."""
    scan = tmp_path / "scan.jsonl"
    scan.write_text(
        "\n".join(json.dumps(scan_row(f"place-{at}", adopted=bool(at % 2))) for at in range(4))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(hunt, "scan_path", lambda: scan)
    monkeypatch.setattr(hunt, "frames_path", lambda: tmp_path / "frames.jsonl")
    index = hunt.frames(log=lambda *_: None)
    assert len(index) == 4
    assert index["place-1"]["viewport"] == REFINED
    assert index["place-0"]["viewport"] == ORIGINAL


# --------------------------------------------------------------------------- #
# Which places a hunt may draw.
# --------------------------------------------------------------------------- #
def test_a_location_the_ledger_already_stands_on_is_not_drawable():
    """Depth is not the thin axis; a place with a recipe already has one."""
    rows = [place("a"), place("b")]
    index = {"a": {}, "b": {}}
    assert set(hunt.drawable(rows, index, {"a"})["mandelbrot"][0]["key"]) == set("b")


def test_a_location_the_scan_does_not_hold_is_not_drawable():
    """The frame is part of the recipe, so a place with no scan row cannot be drawn."""
    assert hunt.drawable([place("a"), place("b")], {"a": {}}, set())["mandelbrot"] == [place("a")]


def test_opened_locations_reads_the_recorded_identity_and_not_the_frame():
    """It has to agree with the rule that will later refuse a second seat there."""
    rows = [{"location": {"key": "recorded", "frame_key": "somewhere-else"}}]
    assert hunt.opened_locations(rows) == {"recorded"}


# --------------------------------------------------------------------------- #
# The draw over places.
# --------------------------------------------------------------------------- #
def test_the_breadth_draw_is_round_robin_over_the_partitions():
    """Places are equally thin everywhere, and the price table wants every row."""
    drawn = hunt.spread(pools({"a": 50, "b": 50, "c": 50}), 9, seed=1)
    assert sorted(row["partition"] for row in drawn) == ["a"] * 3 + ["b"] * 3 + ["c"] * 3


def test_the_draw_takes_what_a_thin_partition_has_and_does_not_stall():
    """A partition that runs out is passed over rather than blocking the round."""
    drawn = hunt.spread(pools({"a": 1, "b": 10}), 6, seed=1)
    assert len(drawn) == 6
    assert sum(1 for row in drawn if row["partition"] == "a") == 1


def test_the_draw_never_hands_one_place_out_twice():
    drawn = hunt.spread(pools({"a": 4, "b": 4}), 8, seed=3)
    assert len({row["key"] for row in drawn}) == 8


def test_the_same_seed_draws_the_same_places():
    counts = {"a": 20, "b": 20}
    one = [row["key"] for row in hunt.spread(pools(counts), 8, seed=7)]
    assert one == [row["key"] for row in hunt.spread(pools(counts), 8, seed=7)]
    assert one != [row["key"] for row in hunt.spread(pools(counts), 8, seed=8)]


def test_a_work_order_is_proportional_over_every_prefix_and_not_only_over_a_round():
    """The bug this exists for: a blocked round only acts if the leg outruns it.

    A work order spelled 19/6/5/... as nineteen consecutive turns spends a
    ten-place leg entirely on the first partition and the shortage's other eight
    are never looked at.
    """
    order = {"a": 19, "b": 6, "c": 5, "d": 4}
    drawn = hunt.spread(pools({name: 60 for name in order}), 10, seed=1, weights=order)
    got = {name: sum(1 for row in drawn if row["partition"] == name) for name in order}
    assert got["a"] < 10
    assert set(got) == set(order)
    assert got["a"] > got["b"] > got["d"]


# --------------------------------------------------------------------------- #
# The seed, and why it is not `hash()`.
# --------------------------------------------------------------------------- #
def test_the_seed_is_a_digest_and_therefore_the_same_in_the_next_process():
    """`hash()` over a string is randomized per process and can come back negative.

    Both halves matter: a draw seeded on `hash()` is recorded as reproducible and
    is not, and `numpy.random.default_rng` refuses the negative half outright. The
    literal here is the derivation, so a change to it is a decision.
    """
    import hashlib

    material = "5|dark_vivid_lime|0"
    assert hunt.seed_of(5, "dark_vivid_lime", 0) == int(
        hashlib.sha256(material.encode("utf-8")).hexdigest()[:8], 16
    )
    assert hunt.seed_of(5, "dark_vivid_lime", 0) >= 0


# --------------------------------------------------------------------------- #
# The two legs.
# --------------------------------------------------------------------------- #
def test_the_modes_a_location_is_tried_in_are_drawn_without_replacement():
    """A second draw that could repeat the first buys the same picture twice."""
    roster = ("smooth", "stripe", "threads", "itinerary", "tia")
    drawn = hunt.modes_for("place-a", 4, seed=2, roster=roster)
    assert len(set(drawn)) == 4
    assert set(drawn) <= set(roster)
    assert drawn == hunt.modes_for("place-a", 4, seed=2, roster=roster)


def test_the_stratifier_walks_the_cells_in_turn_and_repeats_only_after_a_full_round(monkeypatch):
    """The head's argmax concentrates; the whole point here is that this does not."""
    import fractal_wallpapers.palettes.carriers as carrier_table

    monkeypatch.setattr(carrier_table, "draw", lambda cell, count, seed, **_: [f"map-for-{cell}"])
    stratifier = hunt.Stratifier(["one", "two", "three"], ["m"], seed=1)
    asked = [stratifier.next() for _ in range(6)]
    first, second = [cell for cell, _map in asked[:3]], [cell for cell, _map in asked[3:]]
    assert sorted(first) == ["one", "three", "two"]
    assert second == first
    assert [name for _cell, name in asked[:3]] == [f"map-for-{cell}" for cell in first]


def test_a_cell_no_reachable_map_carries_is_skipped_and_does_not_stop_the_walk(monkeypatch):
    """An even ask across the cells that can be asked for is the whole of the job."""
    import fractal_wallpapers.palettes.carriers as carrier_table

    monkeypatch.setattr(
        carrier_table, "draw", lambda cell, count, seed, **_: [] if cell == "empty" else ["m"]
    )
    stratifier = hunt.Stratifier(["empty", "held"], ["m"], seed=1)
    assert [stratifier.next()[0] for _ in range(4)] == ["held"] * 4


def test_a_conditioned_leg_with_no_reachable_carrier_is_refused_before_a_render(monkeypatch):
    """A hunt that started anyway would run to the end and buy none of the colour."""
    import fractal_wallpapers.palettes.carriers as carrier_table

    monkeypatch.setattr(carrier_table, "draw", lambda *args, **kwargs: [])
    with pytest.raises(hunt.HuntRefused, match="carries nothing_at_all"):
        hunt.plan(
            pools({"a": 10}),
            seed=1,
            conditioned=6,
            cell="nothing_at_all",
            pool=["m"],
            log=lambda *_: None,
        )


def test_the_two_legs_are_interleaved_so_a_budget_truncates_both():
    """A concatenated plan that ran out would answer neither of the two questions."""
    woven = hunt._interleave(list("AAAA"), list("bb"))
    assert len(woven) == 6
    assert set(woven[:3]) == {"A", "b"}


# --------------------------------------------------------------------------- #
# What a candidate costs.
# --------------------------------------------------------------------------- #
def test_an_unmeasured_partition_is_priced_at_the_prior():
    assert hunt.Price().of("phoenix") == hunt.PRIOR_SECONDS


def test_a_measured_partition_is_priced_at_its_own_dearest_candidate():
    """The budget question is *can this one finish*; half of them cost above a mean."""
    price = hunt.Price(after=3)
    for seconds in (1.0, 2.0, 9.0):
        price.add("phoenix", seconds)
    assert price.of("phoenix") == 9.0
    assert price.table()["phoenix"]["candidates"] == 3


def test_a_partition_with_too_few_of_its_own_falls_back_to_what_the_run_has_seen():
    """Not to the prior: this run's own dearest candidate is the better evidence."""
    price = hunt.Price(prior=3.1, after=3)
    for seconds in (5.0, 6.0, 7.0):
        price.add("mandelbrot", seconds)
    price.add("phoenix", 1.0)
    assert price.of("phoenix") == 7.0


# --------------------------------------------------------------------------- #
# The row a candidate becomes.
# --------------------------------------------------------------------------- #
def try_of(mode="smooth", colormap="twilight_shifted", leg=hunt.UNCONDITIONAL):
    return hunt.Try(
        leg=leg,
        location="place-a",
        partition="mandelbrot",
        mode=mode,
        colormap=colormap,
        cell="dark_vivid_lime",
    )


def test_a_recipe_and_its_key_are_known_before_the_engine_runs():
    """*Have we already made this picture* is the question the ledger exists for.

    Every member is a lookup or a default — the frame off the scan, the palette
    knobs off `finished.recipe`, the autolevel stamp off the band's identity — so
    a hunt can skip a render it has already paid for instead of discovering that
    afterwards.
    """
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.cyclic = {"twilight_shifted"}
    maker.band = {"_sha256": "abc"}
    maker.groups = {}
    frame = hunt.chosen_frame(scan_row())
    recipe = maker.recipe_for(try_of(), place(), frame)
    assert recipe.viewport == REFINED
    assert recipe.maxiter == 900
    assert recipe.regime == recipes.CANDIDATE_REGIME
    assert recipes.key_of(recipe) == recipes.key_of(maker.recipe_for(try_of(), place(), frame))


def test_the_autolevel_stamp_is_the_band_identity_and_not_what_the_operator_measured():
    """`acted` is a function of the picture, so it is not in the name of one."""
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.band = {"_sha256": "abc"}
    stamp = maker.stamp_for("smooth")
    assert stamp == {"operator": "band_autolevel/v1", "switch": "on", "band_sha256": "abc"}
    assert "acted" not in stamp


def test_the_stamp_a_hunt_derives_is_the_one_a_pass_writes():
    """Against the live band, not a fake one — the two spell the digest differently.

    The band record calls it `_sha256` and the stamp calls it `sha256`, and a hunt
    that translated that by hand named identical pixels differently from the pass
    that made them. The stamp goes through the operator's own `make_stamp` for
    that reason and this is the guard on it.
    """
    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.curation import colorize

    if not autolevel.enabled():
        pytest.skip("the autolevel switch is off, so no render here carries a stamp")
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.band = colorize.band()
    assert maker.stamp_for("smooth") == {
        "operator": autolevel.OPERATOR,
        "switch": "on",
        "band_sha256": maker.band["_sha256"],
    }


@pytest.mark.slow
def test_a_hunt_names_a_pass_s_pictures_the_way_the_pass_did():
    """The strongest available check that a hunt's rows join the ledger's.

    Every levelled recipe already on record is re-derived from its own fields
    through the hunt's own recipe builder, and the two keys have to agree. If they
    do not, a hunt would re-render pictures the ledger already holds and file them
    under names nothing else uses.
    """
    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    stored = candidate_ledger.read()
    if not stored:
        pytest.skip("the candidate ledger is empty on this machine")
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.cyclic = colorize.cyclic()
    maker.band = colorize.band()
    maker.groups = groups_module.member_groups()
    if not autolevel.enabled():
        pytest.skip("the autolevel switch is off, so no render here carries a stamp")
    checked, disagreed = 0, []
    for row in stored:
        recipe = row["recipe"]
        if not recipe.get("autolevel"):
            continue
        rebuilt = maker.recipe_for(
            hunt.Try(
                leg=hunt.UNCONDITIONAL,
                location=str((row["location"] or {})["key"]),
                partition=str(row["partition"]),
                mode=str(recipe["mode"]),
                colormap=str(recipe["colormap"]),
                cell="unused",
            ),
            {"family": recipe["family"]},
            {"viewport": recipe["viewport"], "maxiter": recipe["maxiter"]},
        )
        checked += 1
        if recipes.key_of(rebuilt) != str(row["key"]):
            disagreed.append(row["key"])
    assert checked, "no levelled recipe on record to check against"
    assert not disagreed[:5]


def test_a_mode_the_operator_does_not_act_on_carries_no_stamp():
    """The direct traps are colour-valued before a gradient is spent."""
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.band = {"_sha256": "abc"}
    assert maker.stamp_for("direct_trap_ring") is recipes.NO_AUTOLEVEL


def test_the_source_row_carries_the_framing_block_the_ledger_reads():
    """A hunt has no decision store, so this is the shape and not a row from one."""
    frame = hunt.chosen_frame(scan_row())
    source = hunt.source_for("hunt1", try_of(), place(), frame, 7)
    block = candidate_ledger._framing(source["framing"])
    assert block == {
        "adopted": True,
        "used": "refined",
        "original_viewport": ORIGINAL,
        "refined_viewport": REFINED,
    }
    assert source["_store"] == hunt.FROM_HUNT


def test_the_judge_kind_is_the_spelling_every_record_already_uses():
    assert hunt.kind_of("smooth") == "smooth_render"
    assert hunt.kind_of("itinerary") == "strange_render"


# --------------------------------------------------------------------------- #
# The merge.
# --------------------------------------------------------------------------- #
def test_merging_a_hunt_twice_writes_the_same_ledger(monkeypatch, tmp_path):
    """The ledger upserts by recipe, so a partial and a finished hunt merge alike."""
    monkeypatch.setattr(hunt, "hunt_dir", lambda name: tmp_path / str(name))
    monkeypatch.setattr(candidate_ledger, "rows_path", lambda: tmp_path / "ledger.jsonl")
    monkeypatch.setattr(candidate_ledger, "scores_path", lambda: tmp_path / "scores.jsonl")
    (tmp_path / "one").mkdir()
    hunt.rows_path("one").write_text(
        json.dumps({"key": "aaaa", "location": {"key": "place-a"}}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    hunt.scores_path("one").write_text(
        json.dumps({"key": "aaaa|art|640x360ss2", "recipe_key": "aaaa"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    first = hunt.merge("one", log=lambda *_: None)
    written = (tmp_path / "ledger.jsonl").read_bytes()
    second = hunt.merge("one", log=lambda *_: None)
    assert (first["ledger"]["rows"], first["ledger"]["new"]) == (1, 1)
    assert (second["ledger"]["rows"], second["ledger"]["new"]) == (1, 0)
    assert (tmp_path / "ledger.jsonl").read_bytes() == written


def test_merging_a_hunt_that_made_nothing_is_refused_rather_than_reported(monkeypatch, tmp_path):
    """An empty file means no candidate landed, which is not a successful merge."""
    monkeypatch.setattr(hunt, "hunt_dir", lambda name: tmp_path / str(name))
    with pytest.raises(hunt.HuntRefused, match="nothing to merge"):
        hunt.merge("empty", log=lambda *_: None)


# --------------------------------------------------------------------------- #
# What the hunt reports.
# --------------------------------------------------------------------------- #
def test_the_plan_shape_names_both_legs_and_carries_no_estimate_of_seconds(monkeypatch):
    """The price is per partition and is measured on the run, not modelled here."""
    import fractal_wallpapers.palettes.carriers as carrier_table

    monkeypatch.setattr(carrier_table, "draw", lambda cell, count, seed, **_: ["m"] * count)
    held = pools({"a": 30, "b": 30})
    intended = hunt.plan(
        held,
        seed=1,
        unconditional=12,
        conditioned=6,
        cell="dark_vivid_lime",
        pool=["m"],
        log=lambda *_: None,
    )
    shape = hunt.shape_of(held, intended)
    assert shape["planned"] == 18
    assert shape["legs"][hunt.UNCONDITIONAL]["candidates"] == 12
    assert shape["legs"][hunt.CONDITIONED]["candidates"] == 6
    assert shape["drawable"]["locations"] == 60
    assert "seconds" not in json.dumps(shape)


def test_the_leg_readout_separates_what_was_asked_for_from_what_landed():
    """The carrier table is a prior about maps and never a verdict about pictures."""
    made = [
        {
            "leg": hunt.CONDITIONED,
            "location": "a",
            "drawn_for": "dark_vivid_lime",
            "cells": ["dark_vivid_lime"],
            "seconds": 1.0,
        },
        {
            "leg": hunt.CONDITIONED,
            "location": "b",
            "drawn_for": "dark_vivid_lime",
            "cells": ["dark_muted_blue"],
            "seconds": 1.0,
        },
    ]
    for row in made:
        row["hit"] = row["drawn_for"] in row["cells"]
    legs = hunt._legs(made)
    assert legs[hunt.CONDITIONED]["drawn_for_delivered"] == 1
    assert legs[hunt.CONDITIONED]["delivery_rate"] == 0.5
    assert legs[hunt.CONDITIONED]["cells_delivered"] == 2
