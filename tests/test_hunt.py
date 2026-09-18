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
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX

# --------------------------------------------------------------------------- #
# Material.
# --------------------------------------------------------------------------- #
ORIGINAL = {"center_re": "0.1", "center_im": "0.2", "width": "0.5"}
REFINED = {"center_re": "0.1", "center_im": "0.2", "width": "0.707"}

#: How many levelled rows the key-agreement guard below re-derives, and the seed
#: it draws them with. A budget rather than the store, because the store has no
#: ceiling: it went from 15,362 rows to 366,236 in the three days to 2026-08-29
#: and the guard went from seconds to 175 s with it. Twenty thousand rows spread
#: over every `(mode, colormap)` on record is about ten seconds, and it is the
#: same guard — a recipe builder that has drifted has drifted for a whole mode.
SAMPLE = 20_000
SAMPLE_SEED = 20260829


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


def place(key="place-a", partition="mandelbrot", **extra):
    """One embedding-store row, thinned the same way.

    It carries its own `viewport` and `maxiter` because the real store does — that
    is what makes a location with no scan row renderable at the frame it already
    has, which is what [`hunt.recorded_frame`] reads.
    """
    return {
        "key": key,
        "partition": partition,
        "family": {"kind": "mandelbrot", "degree": 2},
        "viewport": ORIGINAL,
        "maxiter": 1000,
        "ledger": "artifacts/harvest_run10/walk.jsonl",
        **extra,
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
    assert set(hunt.drawable(rows, {"a"})["mandelbrot"][0]["key"]) == set("b")


def test_a_partition_with_no_drawable_row_is_reported_as_a_zero_not_an_absence():
    """A partition that holds nothing used to be absent from this dict rather than
    zero in it, so it could not appear as a refusal anywhere in the hunt's own
    records — and `phoenix:classic` sat at zero for the life of the project with
    nothing saying so. A table that omits a partition and a table that reports it
    empty are different statements."""
    pools = hunt.drawable([place("a")], set())
    assert set(pools) == set(ALL_PARTITIONS)
    assert pools[CLASSIC_PHOENIX] == []
    shape = hunt.shape_of(pools, [])
    assert shape["drawable"]["by_partition"][CLASSIC_PHOENIX] == 0
    assert shape["drawable"]["locations"] == 1
    assert hunt.spread(pools, 4, seed=1) == [place("a")], "an empty pool takes no turn"


def test_a_location_with_no_framing_row_is_minable_at_the_frame_it_carries():
    """Absence is not a rejection: the ledger's ratings bound the population, not the scan.

    The rule used to be "minable if the last pool-wide framing scan holds a row
    for it", which made every location admitted after a scan silently unreachable
    — 8,778 of the 36,868 admitted on 2026-09-01 and 8,015 of those never opened,
    the whole reframing channel among them. A location with no scan row draws at
    the frame its own store row carries.
    """
    rows = [place("a"), place("b")]
    assert hunt.drawable(rows, set())["mandelbrot"] == rows
    frame = hunt.frame_for(place("b"), {"a": {"viewport": REFINED, "maxiter": 900}})
    assert (frame["viewport"], frame["maxiter"]) == (ORIGINAL, 1000)
    assert (frame["adopted"], frame["used"], frame["from_scan"]) == (False, "original", False)
    assert frame["refined_viewport"] is None


def test_a_scanned_location_still_draws_at_the_frame_the_scan_chose():
    """The seam is one-way: where the index holds a row, nothing about it moved."""
    chosen = hunt.chosen_frame(scan_row("a", adopted=True))
    assert hunt.frame_for(place("a"), {"a": chosen}) is chosen


def test_a_centered_location_is_never_sent_for_framing():
    """Its centre is the location and its scale is the rung its head picked.

    So it is not incomplete for carrying no scan row, and it is not in the census
    a scan would be pointed at. An ordinary walk location with no row still is.
    """
    walk, nucleus = place("walk"), place("nucleus", centered=True)
    assert hunt.wants_framing(walk, {}) and not hunt.wants_framing(nucleus, {})
    assert not hunt.wants_framing(walk, {"walk": {}})
    assert hunt.unframed([walk, nucleus], {}) == [walk]
    # And it is minable all the same — the census is not the population.
    assert hunt.drawable([walk, nucleus], set())["mandelbrot"] == [nucleus, walk]


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


def _any_map(monkeypatch):
    """The carrier table serving any cell out of a one-map pool, as the shape
    tests above do — these two are about the PLACE draw and not about colour."""
    import fractal_wallpapers.palettes.carriers as carrier_table

    monkeypatch.setattr(carrier_table, "draw", lambda cell, count, seed, **_: ["m"] * count)


def test_the_breadth_leg_draws_under_the_standing_partition_weights(monkeypatch):
    """The unconditional leg IS a breadth leg, so it inherits the table like the
    other two. Ruled 2026-09-02 on what the dear partitions cost per candidate."""
    _any_map(monkeypatch)
    held = pools({"mandelbrot": 60, "phoenix": 60})
    intended = hunt.plan(held, seed=1, unconditional=45, pool=["m"], log=lambda *_: None)
    tally = {name: sum(1 for one in intended if one.partition == name) for name in held}
    assert tally["phoenix"] > 0, "a weight is never a gate"
    assert tally["phoenix"] * 2 < tally["mandelbrot"], tally


def test_the_aimed_leg_keeps_its_own_domain(monkeypatch):
    """A leg sent at a shortage already says which partitions it means, and what a
    partition costs to render is a fact about a BREADTH draw. So the work order
    stands alone: a conditioned leg told nothing draws every partition evenly."""
    _any_map(monkeypatch)
    held = pools({"mandelbrot": 60, "phoenix": 60})
    intended = hunt.plan(
        held,
        seed=1,
        conditioned=45,
        cell="dark_vivid_lime",
        pool=["m"],
        log=lambda *_: None,
    )
    tally = {name: sum(1 for one in intended if one.partition == name) for name in held}
    # Within one location of each other — an odd number of places cannot split in
    # two — and nowhere near the four-to-one the breadth leg above draws at.
    assert abs(tally["mandelbrot"] - tally["phoenix"]) <= hunt.PER_LOCATION, tally


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


def test_one_mode_holds_the_roster_where_the_width_only_samples_it(monkeypatch):
    """`--mode` and `--per-location` are different asks and the difference is the
    point: the width says how many modes a place is tried in and `modes_for`
    SAMPLES them, so width 1 alone gives each place one mode drawn out of the
    twelve and a leg reads as a thin slice of all of them. A leg comparing places
    rather than modes wants the mode held, and the two compose — width 1 at one
    mode is one candidate per place, in that mode."""
    _any_map(monkeypatch)
    held = pools({"mandelbrot": 40})
    loose = hunt.plan(
        held, seed=1, unconditional=30, per_location=1, pool=["m"], log=lambda *_: None
    )
    assert len({one.mode for one in loose}) > 1, "width 1 alone samples the whole roster"

    holding = hunt.plan(
        held,
        seed=1,
        unconditional=30,
        per_location=1,
        mode="smooth",
        pool=["m"],
        log=lambda *_: None,
    )
    assert {one.mode for one in holding} == {"smooth"}
    # One candidate per place either way: the mode is held, not the width.
    assert len({one.location for one in holding}) == len(holding)


def test_a_mode_off_the_mined_roster_is_refused_rather_than_drawn(monkeypatch):
    """A hunt is a leg that BUYS material, so its roster is `mode_policy.mined()` and
    a mode off it is one this project has ruled it does not buy more of — weighted 0,
    or in `UNMINED` because the gallery seats it and no leg stocks it. Drawing one
    here would be the single door that ignores both rulings."""
    from fractal_wallpapers.curation import mode_policy

    _any_map(monkeypatch)
    held = pools({"mandelbrot": 20})
    for refused in ("no_such_mode", *mode_policy.unmined()[:1]):
        with pytest.raises(hunt.HuntRefused, match="is not a mode a hunt draws"):
            hunt.plan(
                held,
                seed=1,
                unconditional=10,
                mode=refused,
                pool=["m"],
                log=lambda *_: None,
            )


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


def test_a_hunt_asked_for_neither_leg_is_refused_rather_than_reported_as_zero():
    """`curate hunt run --name h1 --budget 1200` — the README's own worked example
    until 2026-09-14 — exited 0 in under two seconds having planned nothing, made
    nothing, and written a record and an empty contact sheet saying so. Both counts
    default to 0, so naming neither asked for nothing. The refusal is in `plan`
    because a plan of zero is indistinguishable downstream from a budget that ran
    out at the first candidate, and it names **both** flags because a caller who
    reached this has not decided which leg they wanted."""
    with pytest.raises(hunt.HuntRefused) as refusal:
        hunt.plan(pools({"a": 10}), seed=1, pool=["m"], log=lambda *_: None)
    assert "--unconditional" in str(refusal.value)
    assert "--conditioned" in str(refusal.value)


def test_a_conditioned_count_with_no_cell_is_refused_and_not_quietly_dropped(monkeypatch):
    """The same mistake wearing the other hat, and refused apart from it so the
    caller learns which one they made. `plan` used to read `if conditioned and
    cell:`, so `--conditioned 200` with no `--cell` planned zero conditioned
    candidates in silence — worse than the both-zero case when `--unconditional` is
    also named, because the breadth leg runs on and the record reads like a hunt
    that worked while the colour it was sent for was never asked for at all."""
    _any_map(monkeypatch)
    with pytest.raises(hunt.HuntRefused, match="no cell to condition on"):
        hunt.plan(
            pools({"a": 10}),
            seed=1,
            unconditional=6,
            conditioned=6,
            pool=["m"],
            log=lambda *_: None,
        )


def test_the_aimed_legs_settings_without_the_count_that_buys_it_are_refused(monkeypatch):
    """The mirror of the refusal above, and the reason that one alone was not
    enough. `--cell` and `--work-order` describe the conditioned leg and
    `--conditioned` is what buys it, at a default of 0 — so naming a colour beside
    a breadth count spent the whole budget on breadth and reported a hunt that
    worked, with the cell never reaching the carrier table. It reads worse than the
    both-zero case rather than better: something was drawn, so there is a record
    and a sheet to look at, and neither says the colour was not bought."""
    _any_map(monkeypatch)
    for settings in ({"cell": "dark_vivid_lime"}, {"work_order": {"a": 5}}):
        with pytest.raises(hunt.HuntRefused, match="never bought"):
            hunt.plan(
                pools({"a": 10}),
                seed=1,
                unconditional=6,
                pool=["m"],
                log=lambda *_: None,
                **settings,
            )
    # And the pairing it exists to protect still plans: a cell with a count is the
    # aimed leg as intended, and a breadth leg naming neither is untouched.
    assert hunt.plan(
        pools({"a": 10}),
        seed=1,
        conditioned=6,
        cell="dark_vivid_lime",
        pool=["m"],
        log=lambda *_: None,
    )
    assert hunt.plan(pools({"a": 10}), seed=1, unconditional=6, pool=["m"], log=lambda *_: None)


def test_a_count_below_zero_is_refused_by_name_and_not_planned_as_a_leg_of_zero(monkeypatch):
    """The both-zero refusal above tested truth and not sign, so `--unconditional
    -600` went straight through it — `not int(-600)` is False — and planned the
    same nothing by another road: `spread` returns [] on `count <= 0` and `_leg`
    finds `0 >= -600` on its first pass. Each flag is asked separately, because
    the partial case is the worse one: a negative beside a good count leaves the
    good leg running and the record reading like a hunt that worked."""
    _any_map(monkeypatch)
    held = pools({"a": 20, "b": 20})
    with pytest.raises(hunt.HuntRefused, match="--unconditional -600"):
        hunt.plan(held, seed=1, unconditional=-600, pool=["m"], log=lambda *_: None)
    with pytest.raises(hunt.HuntRefused, match="--conditioned -600"):
        hunt.plan(
            held,
            seed=1,
            conditioned=-600,
            cell="dark_vivid_lime",
            pool=["m"],
            log=lambda *_: None,
        )
    # The partial shape: one leg is exactly what the caller meant and the other is
    # a typo. Refused on the typo, and named for it.
    with pytest.raises(hunt.HuntRefused, match="--unconditional -600"):
        hunt.plan(
            held,
            seed=1,
            unconditional=-600,
            conditioned=9,
            cell="dark_vivid_lime",
            pool=["m"],
            log=lambda *_: None,
        )


def test_a_negative_conditioned_count_is_not_blamed_on_the_carrier_table(monkeypatch):
    """`--conditioned -600 --cell dark_vivid_lime` did refuse before this, but as
    *no map carries that cell* — `conditioned_maps` loops `while len(out) < count`
    and hands back [] on a negative count, which the carrier refusal reads as a
    colour the library cannot make. That sends a caller to audit the palette
    library over a minus sign in a number, so the sign is asked first."""
    _any_map(monkeypatch)
    with pytest.raises(hunt.HuntRefused) as refusal:
        hunt.plan(
            pools({"a": 20}),
            seed=1,
            conditioned=-600,
            cell="dark_vivid_lime",
            pool=["m"],
            log=lambda *_: None,
        )
    assert "carries dark_vivid_lime" not in str(refusal.value)


def test_a_per_location_below_one_is_refused_against_its_own_flag(monkeypatch):
    """`--unconditional 600 --per-location 0` planned **0** and logged both legs as
    zero: `modes_for` samples `min(count, len(roster))` modes for a place, so at 0
    it hands back nothing and `_leg`'s inner loop never runs. Both counts are
    exactly what the caller meant here — it is a divisor and not a size — so the
    message has to name `--per-location` and not `--unconditional`. Below zero got
    no further but broke differently: `random.sample` raised a bare `ValueError`
    three frames down, and the CLI catches `HuntRefused` and nothing else."""
    _any_map(monkeypatch)
    held = pools({"a": 20, "b": 20})
    for depth in (0, -1):
        with pytest.raises(hunt.HuntRefused) as refusal:
            hunt.plan(
                held,
                seed=1,
                unconditional=600,
                per_location=depth,
                pool=["m"],
                log=lambda *_: None,
            )
        # The flag at fault is the one the message opens on, not one of the two it
        # goes on to offer as somewhere else to take a leg's size out of.
        assert str(refusal.value).startswith(f"`--per-location {depth}`"), refusal.value
    # The aimed leg reaches `modes_for` by its own road and is refused on the same
    # flag, rather than on the cell it was perfectly well given.
    with pytest.raises(hunt.HuntRefused, match="--per-location"):
        hunt.plan(
            held,
            seed=1,
            conditioned=600,
            cell="dark_vivid_lime",
            per_location=0,
            pool=["m"],
            log=lambda *_: None,
        )


def test_the_shallowest_hunt_there_is_still_plans_and_is_not_caught_by_the_depth_guard(
    monkeypatch,
):
    """The floor is 1 and not `PER_LOCATION`: one candidate a place is the widest
    breadth a hunt can buy for its money, which is a real ask and not a mistake."""
    _any_map(monkeypatch)
    intended = hunt.plan(
        pools({"a": 20, "b": 20}),
        seed=1,
        unconditional=9,
        per_location=1,
        pool=["m"],
        log=lambda *_: None,
    )
    assert len(intended) == 9
    assert len({one.location for one in intended}) == 9, "one candidate a place"


def test_either_leg_alone_is_a_whole_hunt_and_neither_refusal_touches_it(monkeypatch):
    """The two refusals above are about a draw of nothing, not about balance. A
    breadth-only hunt is what stocks a thin ledger and an aimed-only hunt is what a
    short solve orders, so both have to plan — a guard that demanded both legs would
    have made the commonest two invocations in `LEGS.md` illegal."""
    _any_map(monkeypatch)
    held = pools({"a": 20, "b": 20})
    breadth = hunt.plan(held, seed=1, unconditional=9, pool=["m"], log=lambda *_: None)
    aimed = hunt.plan(
        held, seed=1, conditioned=9, cell="dark_vivid_lime", pool=["m"], log=lambda *_: None
    )
    assert {one.leg for one in breadth} == {hunt.UNCONDITIONAL}
    assert {one.leg for one in aimed} == {hunt.CONDITIONED}
    assert (len(breadth), len(aimed)) == (9, 9)


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
def test_a_hunt_names_a_pass_s_pictures_the_way_the_pass_did(tracked_ledger):
    """The strongest available check that a hunt's rows join the ledger's.

    A levelled recipe already on record is re-derived from its own fields through
    the hunt's own recipe builder, and the two keys have to agree. If they do not,
    a hunt would re-render pictures the ledger already holds and file them under
    names nothing else uses.

    **A sample and no longer a re-census, deliberately.** 344,923 of the 366,236
    rows on record are levelled and a rebuild is about half a millisecond, so the
    whole store was 175 s of hashing on 2026-08-29 — a sixth of the entire slow
    lane, growing with every mine leg and with no ceiling anywhere. `SAMPLE` rows
    drawn at a fixed seed, stratified over `(mode, colormap)` so no coloring can
    fall out of the draw, catch a systematic disagreement just as surely: this
    guard has never found one row wrong, it has found a *builder* wrong, and a
    builder that is wrong is wrong for a whole mode at a time.

    The count is asserted below so a stratification that silently collapsed to
    nothing fails here rather than passing quietly.
    """
    import random

    from fractal_wallpapers.coloring import autolevel
    from fractal_wallpapers.curation import colorize
    from fractal_wallpapers.palettes import groups as groups_module

    stored = tracked_ledger.rows
    if not stored:
        pytest.skip("the candidate ledger is empty on this machine")
    maker = hunt.Maker.__new__(hunt.Maker)
    maker.cyclic = colorize.cyclic()
    maker.band = colorize.band()
    maker.groups = groups_module.member_groups()
    if not autolevel.enabled():
        pytest.skip("the autolevel switch is off, so no render here carries a stamp")
    # **Candidate-path rows only, and that is a filter the pool did not need until
    # 2026-09-08.** This rebuilds each recipe through `Maker.recipe_for`, which
    # spends `colorize.CURVE`, the plain palette and no settings — so it can only
    # name a picture the candidate path could have made. `label-migration merge`
    # put 3,015 rows derived from the label corpora into the pool that day and
    # about a third carry knobs the candidate path never spends, which made the
    # unfiltered claim false: the first slow lane after the merge found five such
    # rows and this guard was what went red. `colorize.is_candidate_path` is the
    # rule, shared with `rerender.render_pair`, which refuses the same rows for
    # the same reason.
    cyclic = maker.cyclic
    strata: dict = {}
    skipped_overrides = 0
    for row in stored:
        recipe = row["recipe"]
        if not recipe.get("autolevel"):
            continue
        if not colorize.is_candidate_path(recipe, cyclic):
            skipped_overrides += 1
            continue
        strata.setdefault((str(recipe["mode"]), str(recipe["colormap"])), []).append(row)
    assert strata, "no levelled recipe on record to check against"
    # The filter is a claim about the store and is checked rather than trusted: a
    # predicate that started answering False for everything would empty the
    # population and leave this test green over nothing.
    assert skipped_overrides, (
        "no row in the pool names a curve or palette off the candidate path, so this "
        "filter is excluding nothing and should go — or `is_candidate_path` has broken"
    )
    draw = random.Random(SAMPLE_SEED)
    per_stratum = max(1, SAMPLE // len(strata))
    sample = [
        row
        for rows_ in (strata[key] for key in sorted(strata))
        for row in draw.sample(rows_, min(per_stratum, len(rows_)))
    ]
    checked, disagreed = 0, []
    for row in sample:
        recipe = row["recipe"]
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
    # Every stratum reached the draw and every drawn row reached the builder. A
    # sample is only a guard while both hold: a filter that quietly emptied one
    # would leave a coloring unchecked and this test still green.
    assert checked == len(sample)
    assert checked >= len(strata), f"{len(strata)} strata drew only {checked} rows"
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
def a_ledger_row(key: str = "aaaa") -> dict:
    """One row in the shape a hunt writes, carrying a **whole recipe**.

    The recipe is not decoration here. `merge` prunes now, and the prune joins
    every row back to the label store through `retention.render_key_of`, which
    reads the recipe and raises on a family it cannot place — loudly, because a
    row that cannot be keyed could never be found to carry a label and would be
    dropped as unlabeled with nothing saying so.
    """
    from tests.test_candidate_ledger import decision

    source = decision()
    return candidate_ledger.row(
        recipe=recipes.of_decision(source), key=key, source=source, picture=None
    )


@pytest.mark.slow
def test_merging_a_hunt_twice_writes_the_same_ledger(monkeypatch, tmp_path):
    """The ledger upserts by recipe, so a partial and a finished hunt merge alike."""
    from fractal_wallpapers import paths

    monkeypatch.setattr(hunt, "hunt_dir", lambda name: tmp_path / str(name))
    # Redirected at the TIER ROOTS rather than per accessor. The ledger's two row
    # files, the flatness sidecar and the durable copies all resolve through a
    # root already, so setting the two moves every one of them — including the
    # supply sidecar, which the prune reads and which a per-accessor list never
    # named. `manifest_dir` is the one that has no root
    # to set, because it is the tracked half; `conftest`'s session guard covers
    # what a fixture misses there.
    root = tmp_path / "artifacts"
    (root / "curation" / candidate_ledger.store.UNIT).mkdir(parents=True)
    monkeypatch.setenv(paths.HOT_ROOT_VARIABLE, str(root))
    monkeypatch.setenv(paths.ARCHIVE_ROOT_VARIABLE, "")
    monkeypatch.setattr(candidate_ledger.store, "manifest_dir", lambda: tmp_path / "manifests")
    (root / "curation" / "supply_scores.jsonl").touch()
    (tmp_path / "one").mkdir()
    hunt.rows_path("one").write_text(
        json.dumps(a_ledger_row()) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    hunt.scores_path("one").write_text(
        json.dumps({"key": "aaaa|art|640x360ss2", "recipe_key": "aaaa"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    first = hunt.merge("one", log=lambda *_: None)
    written = candidate_ledger.rows_path().read_bytes()
    second = hunt.merge("one", log=lambda *_: None)
    assert (first["ledger"]["rows"], first["ledger"]["new"]) == (1, 1)
    assert (second["ledger"]["rows"], second["ledger"]["new"]) == (1, 0)
    assert candidate_ledger.rows_path().read_bytes() == written


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


# --------------------------------------------------------------------------- #
# What the ledger row remembers about the draw.
# --------------------------------------------------------------------------- #
def test_every_planner_stamps_k_on_the_block_the_ledger_row_carries():
    """The run's own `sequence.jsonl` lives under the regenerable tree; the
    ledger does not. A correction that is a function of `k` — the winner's-curse
    multiplier above all — cannot be applied to a row that forgot it."""
    from fractal_wallpapers.curation import depth, mine

    intents = [
        hunt.Try(
            leg="a", location="p", partition="m", mode="smooth", colormap="viridis", cell="red", k=3
        ),
        mine.Unit(
            arm="a", location="p", partition="m", mode="smooth", colormap="viridis", k=3, band="b"
        ),
        depth.Shot(
            arm="a",
            location="p",
            partition="m",
            mode="smooth",
            colormap="viridis",
            k=3,
            band="b",
            rank=7,
            rank_fraction=0.25,
        ),
    ]
    for intent in intents:
        assert intent.named()["k"] == 3, type(intent).__name__


def test_a_hunt_counts_k_from_one_within_a_location_and_restarts_at_the_next():
    places = [
        {"key": "one", "partition": "mandelbrot"},
        {"key": "two", "partition": "mandelbrot"},
    ]
    drawn = hunt._leg(
        "leg",
        places,
        3,
        seed=4,
        roster=("smooth", "stripe", "threads", "itinerary"),
        draw=lambda: ("red", "viridis"),
        want=99,
    )
    by_place: dict = {}
    for intent in drawn:
        by_place.setdefault(intent.location, []).append(intent.k)
    assert by_place == {"one": [1, 2, 3], "two": [1, 2, 3]}


def test_k_is_additive_so_a_row_written_before_the_stamp_reads_none():
    """Treating a missing `k` as 1 would report the whole of the pre-stamp
    history as unselected first draws and under-correct every estimate over it."""
    assert candidate_ledger.k_of({"hunt": {"leg": "a", "mode": "smooth"}}) is None
    assert candidate_ledger.k_of({}) is None
    assert candidate_ledger.k_of({"hunt": {"k": None}}) is None
    assert candidate_ledger.k_of({"hunt": {"k": "12"}}) == 12
    assert candidate_ledger.k_of({"hunt": {"k": 4}}) == 4


def test_a_merge_report_is_written_beside_the_leg_and_names_itself(tmp_path):
    """**A merge's report was printed and kept nowhere**, on the three legs that
    come through the ledger's door — a hunt, a mine and a depth run — while
    `rotation`, `repetition` and `label_migration` all wrote one.

    So what a night's merge displaced, what it re-rendered off already-deleted
    rows and what the manifests said afterwards lived in a terminal and died with
    it. `merge_report` is the one writer all three reach, and it takes the leg's
    ROWS FILE rather than its name so that no module spells *where this leg lives*
    a second time.
    """
    rows = tmp_path / "a_leg" / hunt.ROWS_NAME
    rows.parent.mkdir(parents=True)
    report = hunt.merge_report(rows, {"schema": 1, "merged": 3}, log=lambda *_: None)

    written = rows.parent / hunt.MERGE_NAME
    assert written.is_file()
    assert json.loads(written.read_text(encoding="utf-8")) == report
    assert report["merged"] == 3
    assert report["path"].endswith(hunt.MERGE_NAME), (
        "a record that cannot say where it is is a record a reader has to already know about"
    )
    # Idempotent, because a merge is: the second report is the true one.
    hunt.merge_report(rows, {"schema": 1, "merged": 4}, log=lambda *_: None)
    assert json.loads(written.read_text(encoding="utf-8"))["merged"] == 4


def test_all_four_legs_that_come_through_the_door_write_their_merge_report():
    """The wiring, and it is the point rather than any one leg's body.

    Four modules build the same report off `candidate_ledger.merge` and returned
    it to a caller that printed it. A fifth will be written; this is what says the
    report has to land somewhere.
    """
    import inspect

    from fractal_wallpapers.curation import depth, mine, remode

    for module in (hunt, mine, depth, remode):
        source = inspect.getsource(module.merge)
        assert "merge_report(" in source, f"{module.__name__}.merge keeps no record of itself"


# --------------------------------------------------------------------------- #
# `--places` — a named population for the breadth leg.
# --------------------------------------------------------------------------- #
def test_a_places_manifest_cuts_the_pool_to_what_it_names():
    """The whole of the flag: narrow the population, change nothing else.

    `depth run --floor-places` was the only one of the three legs that took a
    named-location filter, and it narrows the OPPOSITE population — locations the
    ledger already stands on. So "render many mode and colormap combinations at
    exactly these N locations I just crawled" had no supported path at all, and
    the only way to do it was to render and score outside the ledger, forfeiting
    the merge, the retention rule and the durability bookkeeping.
    """
    held = pools({"mandelbrot": 3, "julia:mandelbrot": 2})
    cut = hunt.narrowed(held, ["mandelbrot-0", "julia:mandelbrot-1"], log=lambda *_: None)
    assert [row["key"] for row in cut["mandelbrot"]] == ["mandelbrot-0"]
    assert [row["key"] for row in cut["julia:mandelbrot"]] == ["julia:mandelbrot-1"]


def test_a_narrowed_pool_still_reports_every_partition():
    """[`hunt.drawable`]'s rule, kept through the filter: a partition a manifest
    took nothing from is a zero and not an absence, or it cannot appear as a
    refusal anywhere in the hunt's own record."""
    held = pools({"mandelbrot": 2, "julia:mandelbrot": 2})
    cut = hunt.narrowed(held, ["mandelbrot-0"], log=lambda *_: None)
    assert set(cut) == set(held)
    assert cut["julia:mandelbrot"] == []


def test_a_name_the_pool_does_not_hold_is_skipped_and_counted_rather_than_refused():
    """A manifest cut from a crawl names places a hunt has since opened, and that
    is the normal case rather than a fault. The count is logged; the leg runs."""
    said: list = []
    cut = hunt.narrowed(pools({"mandelbrot": 2}), ["mandelbrot-0", "not-a-place"], log=said.append)
    assert [row["key"] for row in cut["mandelbrot"]] == ["mandelbrot-0"]
    assert "1 of 2 named place(s)" in said[0]


def test_a_manifest_that_admits_nothing_is_refused_by_its_own_flag():
    """Not left to the both-legs-zero refusal, which would blame the counts.

    The three reasons a named place is not drawable are three different mistakes
    and the message names all three, because the pool alone cannot say which: by
    the time it exists, the opened set and the admission cut have already been
    subtracted from it.
    """
    with pytest.raises(hunt.HuntRefused) as refusal:
        hunt.narrowed(pools({"mandelbrot": 2}), ["nowhere"], log=lambda *_: None)
    said = str(refusal.value)
    assert "--places" in said
    assert "junk floor" in said and "already stands on it" in said
    assert "--floor-places" in said, "a caller whose places are all open is owed the other leg"


def test_both_hunt_verbs_take_the_places_flag_and_read_it_with_the_same_parser():
    """`plan` IS the run with the rendering left out, which is what
    [`hunt_draw_flags`] exists to keep true — so a filter one verb takes and the
    other does not is two commands describing different draws under one name.

    And one reader: `--places` and `--floor-places` are the same JSONL, so a
    second parser here would be a second spelling of one file waiting to drift.
    """
    import inspect

    from fractal_wallpapers.cli import curate_mine_commands

    flags = inspect.getsource(curate_mine_commands.hunt_draw_flags)
    assert '"--places"' in flags, "the shared helper is what makes both verbs take it"
    handler = inspect.getsource(curate_mine_commands.curate_hunt)
    assert "depth_module.read_places(args.places)" in handler


def test_the_breadth_draw_over_a_narrowed_pool_is_the_draw_it_would_have_been():
    """Narrowing the population is all it does: the same [`spread`], the same
    seeded shuffle, the same round robin. A pool that happens to hold only these
    places draws exactly what the filter draws out of the larger one."""
    named = ["mandelbrot-1", "mandelbrot-3", "julia:mandelbrot-0"]
    wide = hunt.narrowed(
        pools({"mandelbrot": 5, "julia:mandelbrot": 3}), named, log=lambda *_: None
    )
    narrow = {
        "mandelbrot": [place("mandelbrot-1", "mandelbrot"), place("mandelbrot-3", "mandelbrot")],
        "julia:mandelbrot": [place("julia:mandelbrot-0", "julia:mandelbrot")],
    }
    assert [row["key"] for row in hunt.spread(wide, 3, seed=7)] == [
        row["key"] for row in hunt.spread(narrow, 3, seed=7)
    ]
