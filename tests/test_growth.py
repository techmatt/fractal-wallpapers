"""The growth instrument: what it draws, what it never touches, and that it repeats.

Synthetic candidates and a synthetic ledger throughout, like [`test_solve`] — the
sweep reads four fields off each ledger row and hands the pool straight to the
gallery leg, and both of those are already pinned where they live.

Two properties are this file's own. **Determinism**: a stamp and a seed name one
subsample and one set of rows, because the whole point of the instrument is that a
run months apart is comparable with this one — a `random.sample` that changed
algorithm between two CPython releases, or a draw taken over an unsorted set,
would break that silently and no output would say so. And **the ledger is never
touched**: the restriction is a list comprehension over frozen candidates, the
store is opened read-only for the visit map, and a sweep that mutated the pool it
measures would be measuring itself.
"""

from __future__ import annotations

import pytest
from tests.test_headroom import candidate
from tests.test_solve import (
    EveryPicture,
    a_pool_the_fine_head_has_read,  # noqa: F401 — autouse here too
)

from fractal_wallpapers.curation import embeddings, growth, growth_plot, rules, solve

# --------------------------------------------------------------------------- #
# The fixtures the gallery leg needs to run at all.
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def no_neutral_store(monkeypatch):
    """An empty neutral embedding store — [`test_solve`]'s fixture, same reason."""
    monkeypatch.setattr(embeddings, "read", lambda *_args, **_rest: [])


@pytest.fixture(autouse=True)
def every_candidate_has_a_picture(monkeypatch):
    """Every synthetic candidate reads back a signature far from every other.

    [`test_solve.every_candidate_has_a_picture`], for the same reason: these
    candidates name pictures that were never on disk, and the twin rule refuses a
    picture it cannot open. Without this the whole file would measure a gallery of
    nothing.
    """
    monkeypatch.setattr(rules, "clouds_for", lambda candidates, **_rest: EveryPicture(candidates))


def quiet(*_args, **_rest) -> None:
    """A `log` that says nothing."""


def ledger_row(key, *, location=None, leg="legA", seconds=0.5) -> dict:
    """One candidate-ledger row, thinned to the four fields [`growth.visits`] reads."""
    row = {
        "key": str(key),
        "location": {"key": str(location if location is not None else key)},
        "provenance": {"run": leg},
    }
    if seconds is not None:
        row["hunt"] = {"seconds": float(seconds)}
    return row


def pool_of(count, *, legs=("legA", "legB"), per_visit=2):
    """`(candidates, ledger rows, the rank order)` — `count` places, each one visit.

    Each place carries `per_visit` candidates and belongs to one leg, so a draw
    over visits is a draw over places here and the arithmetic in a test is
    readable by eye.
    """
    candidates, rows, order = [], [], {}
    for place in range(count):
        leg = legs[place % len(legs)]
        for at in range(per_visit):
            key = f"c{place}_{at}"
            held = candidate(key, location=f"place{place}", score=0.9 - at * 0.01)
            candidates.append(held)
            rows.append(ledger_row(key, location=f"place{place}", leg=leg))
            order[key] = 0.9 - at * 0.01
    return candidates, rows, order


def swept(monkeypatch, tmp_path, **rest):
    """One sweep over a fixture pool, with the store pointed at `tmp_path`."""
    candidates, rows, order = pool_of(rest.pop("places", 12))
    monkeypatch.setattr(growth, "growth_dir", lambda stamp: tmp_path / str(stamp))
    return growth.sweep(
        stamp=rest.pop("stamp", "FIXTURE"),
        denominators=rest.pop("denominators", (2, 1)),
        sizes=rest.pop("sizes", (4,)),
        seeds=rest.pop("seeds", (7,)),
        rows=rows,
        candidates=candidates,
        order=order,
        coverage={},
        centered=frozenset(rest.pop("centered", ())),
        log=quiet,
        **rest,
    )


# --------------------------------------------------------------------------- #
# The visit.
# --------------------------------------------------------------------------- #
def test_a_visit_is_a_location_and_a_leg():
    keyed, per = growth.visits(
        [
            ledger_row("a", location="p1", leg="legA"),
            ledger_row("b", location="p1", leg="legB"),
            ledger_row("c", location="p2", leg="legA"),
        ]
    )
    assert keyed == {"a": ("p1", "legA"), "b": ("p1", "legB"), "c": ("p2", "legA")}
    assert set(per) == {("p1", "legA"), ("p1", "legB"), ("p2", "legA")}


def test_one_place_opened_twice_is_two_visits_and_they_draw_apart():
    """The reason the unit is `(location, leg)` and not the location alone: a place
    a second leg came back to is a second unit of mining, and a draw that took the
    place whole could never sample the return."""
    _keyed, per = growth.visits(
        [ledger_row("a", location="p1", leg="legA"), ledger_row("b", location="p1", leg="legB")]
    )
    assert len(per) == 2


def test_rows_with_no_leg_form_one_pseudo_leg_per_location():
    """A pre-ledger import carries no `provenance.run`. All of them at one place
    are one visit, and two places are two — not one enormous visit holding every
    import ever made, which nothing could subsample."""
    keyed, per = growth.visits(
        [
            ledger_row("a", location="p1", leg=None),
            ledger_row("b", location="p1", leg=None),
            ledger_row("c", location="p2", leg=None),
        ]
    )
    assert keyed["a"] == ("p1", growth.UNKNOWN_LEG)
    assert sorted(per) == [("p1", growth.UNKNOWN_LEG), ("p2", growth.UNKNOWN_LEG)]
    assert per[("p1", growth.UNKNOWN_LEG)]["rows"] == 2


def test_a_visit_counts_its_rows_and_sums_only_the_seconds_it_has():
    _keyed, per = growth.visits(
        [
            ledger_row("a", location="p1", seconds=0.5),
            ledger_row("b", location="p1", seconds=1.5),
            ledger_row("c", location="p1", seconds=None),
        ]
    )
    held = per[("p1", "legA")]
    assert (held["rows"], held["seconds"], held["timed"]) == (3, 2.0, 2)


# --------------------------------------------------------------------------- #
# The draw.
# --------------------------------------------------------------------------- #
def test_the_same_seed_draws_the_same_visits():
    population = [(f"p{at}", "legA") for at in range(64)]
    assert growth.draw(population, 1 / 8, 11) == growth.draw(population, 1 / 8, 11)


def test_a_different_seed_draws_a_different_set():
    population = [(f"p{at}", "legA") for at in range(64)]
    assert growth.draw(population, 1 / 8, 11) != growth.draw(population, 1 / 8, 22)


def test_the_draw_does_not_depend_on_the_order_the_population_arrives_in():
    """It is sorted first. A pool handed back in score order and the same pool in
    key order would otherwise be two different subsamples under one seed."""
    population = [(f"p{at}", "legA") for at in range(64)]
    assert growth.draw(population, 1 / 4, 11) == growth.draw(list(reversed(population)), 1 / 4, 11)


def test_the_whole_pool_is_not_drawn_at_all():
    population = [(f"p{at}", "legA") for at in range(10)]
    assert growth.draw(population, 1.0, 11) == sorted(population)


def test_a_rung_too_small_to_draw_one_visit_still_draws_one():
    """A rung that drew nothing would report an empty pool as a finding about
    mining, which it is not — it is a finding about the arithmetic."""
    assert len(growth.draw([("p", "legA")], 1 / 64, 11)) == 1


# --------------------------------------------------------------------------- #
# The restriction, and what it must not do.
# --------------------------------------------------------------------------- #
def test_every_candidate_of_a_drawn_visit_comes_with_it():
    candidates, rows, _order = pool_of(4, per_visit=3)
    visit_of, _per = growth.visits(rows)
    drawn = [("place1", "legB")]
    held = growth.restrict(candidates, visit_of, drawn)
    assert {each.location for each in held} == {"place1"}
    assert len(held) == 3


def test_the_restriction_leaves_the_pool_it_was_handed_alone():
    """Read-only, in memory. The candidates are frozen and the input list is not
    rebound, so nothing here can reach the live ledger even by accident."""
    candidates, rows, _order = pool_of(6)
    visit_of, _per = growth.visits(rows)
    before = list(candidates)
    held = growth.restrict(candidates, visit_of, [("place0", "legA")])
    assert candidates == before
    assert held is not candidates


def test_effort_sums_only_the_drawn_visits():
    _candidates, rows, _order = pool_of(4)
    _visit_of, per = growth.visits(rows)
    spent = growth.effort(per, [("place0", "legA"), ("place1", "legB")])
    assert spent == {"attempts": 4, "mining_seconds": 2.0, "mining_seconds_rows": 4}


# --------------------------------------------------------------------------- #
# Reading a spread.
# --------------------------------------------------------------------------- #
def test_every_percentile_is_a_value_the_set_actually_holds():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    held = growth.quantiles(values)
    assert held["count"] == 5
    for percent in growth.QUANTILES:
        assert held[f"p{percent}"] in values


def test_the_percentiles_are_nearest_rank_and_in_order():
    held = growth.quantiles(range(100))
    assert [held[f"p{percent}"] for percent in growth.QUANTILES] == [9.0, 24.0, 49.0, 74.0, 89.0]


def test_an_empty_set_has_no_quantiles_rather_than_zeros():
    """A rung that seated nothing has no quality. Zeros would plot as a terrible
    gallery instead of as no gallery at all."""
    assert growth.quantiles([]) is None


# --------------------------------------------------------------------------- #
# The plan.
# --------------------------------------------------------------------------- #
def test_the_full_pool_is_one_cell_and_carries_no_seed():
    plan = growth.plan_of((4, 1), (11, 22))
    assert plan == [(4, 11), (4, 22), (1, None)]


# --------------------------------------------------------------------------- #
# The sweep, end to end over a fixture pool.
# --------------------------------------------------------------------------- #
def test_the_same_stamp_and_seed_give_the_same_rows(monkeypatch, tmp_path):
    """**The determinism guard.** Everything but the wall clock, which is not a
    finding about anything."""
    first, _manifest = swept(monkeypatch, tmp_path)
    second, _again = swept(monkeypatch, tmp_path)
    strip = [{key: value for key, value in row.items() if key != "solve_seconds"} for row in first]
    assert strip == [
        {key: value for key, value in row.items() if key != "solve_seconds"} for row in second
    ]


def test_the_pool_stamp_is_the_pool_and_not_the_order_it_arrived_in():
    candidates, _rows, _order = pool_of(5)
    assert growth.pool_stamp(candidates) == growth.pool_stamp(list(reversed(candidates)))
    assert growth.pool_stamp(candidates) != growth.pool_stamp(candidates[:-1])


def test_a_subsample_that_cannot_fill_is_a_row_and_not_an_error(monkeypatch, tmp_path):
    rows, _manifest = swept(monkeypatch, tmp_path, places=4, sizes=(50,), denominators=(4,))
    assert rows[0]["filled"] < 50
    assert rows[0]["fill"] < 1.0


def test_every_row_carries_the_schema_the_module_documents(monkeypatch, tmp_path):
    rows, _manifest = swept(monkeypatch, tmp_path)
    wanted = {
        "schema",
        "stamp",
        "rung",
        "fraction",
        "seed",
        "n",
        "visits",
        "visits_available",
        "candidates",
        "attempts",
        "mining_seconds",
        "mining_seconds_rows",
        "eligible",
        "eligible_locations",
        "after_the_preselection",
        "in_the_view",
        "filled",
        "fill",
        "floors_in_the_roster",
        "floors_met",
        "modes_represented",
        "modes_in_the_roster",
        "seated_rank",
        "seated_p_ge4",
        "eligible_rank",
        "eligible_p_ge4",
        "selection_lift",
        "partitions_seated",
        "largest_partition_share",
        "cells_seated",
        "cell_spread",
        "twin_refusals",
        "twin_collapse_share",
        "centered_seats",
        "centered_share",
        "solve_seconds",
    }
    assert wanted <= set(rows[0])
    assert rows[0]["schema"] == growth.SCHEMA


def test_the_top_rung_holds_every_visit_and_the_half_rung_holds_half(monkeypatch, tmp_path):
    rows, manifest = swept(monkeypatch, tmp_path, places=12)
    half = next(row for row in rows if row["rung"] == "1/2")
    whole = next(row for row in rows if row["rung"] == "1/1")
    assert whole["visits"] == manifest["pool"]["visits_reachable"] == 12
    assert half["visits"] == 6
    assert half["candidates"] < whole["candidates"]


def test_the_centered_share_is_the_seats_at_a_centered_place(monkeypatch, tmp_path):
    rows, _manifest = swept(
        monkeypatch, tmp_path, denominators=(1,), sizes=(4,), centered=("place0", "place1")
    )
    row = rows[0]
    assert row["centered_seats"] <= row["filled"]
    assert row["centered_share"] == round(row["centered_seats"] / row["filled"], 4)


def test_the_manifest_says_which_pool_and_which_plan(monkeypatch, tmp_path):
    _rows, manifest = swept(monkeypatch, tmp_path)
    assert manifest["schema"] == growth.SCHEMA
    assert len(manifest["pool"]["stamp"]) == 64
    assert manifest["plan"]["sizes"] == [4]
    assert manifest["plan"]["seeds"] == [7]
    assert manifest["solve"]["swap_seconds"] is None


def test_a_pool_that_joins_to_no_ledger_row_is_refused():
    candidates, _rows, order = pool_of(3)
    with pytest.raises(growth.GrowthRefused):
        growth.sweep(
            stamp="FIXTURE",
            rows=[],
            candidates=candidates,
            order=order,
            centered=frozenset(),
            log=quiet,
        )


def test_a_row_whose_eligible_pool_is_not_the_solves_is_refused(monkeypatch):
    """The one thing that would make the selection lift meaningless without saying
    so: two readings of the clearing rule that had parted company."""
    candidates, _rows, order = pool_of(4)
    monkeypatch.setattr(
        solve,
        "solve",
        lambda *_args, **_rest: {"population": {"clearing": 99999}},
    )
    with pytest.raises(growth.GrowthRefused):
        growth.cell(
            candidates,
            stamp="FIXTURE",
            denominator=1,
            seed=None,
            drawn=4,
            available=4,
            spent={"attempts": 0, "mining_seconds": 0.0, "mining_seconds_rows": 0},
            centered=frozenset(),
            sizes=(4,),
            order=order,
            log=quiet,
        )


# --------------------------------------------------------------------------- #
# Where a run lands.
# --------------------------------------------------------------------------- #
def test_a_run_is_written_whole_and_reads_back(monkeypatch, tmp_path):
    rows, manifest = swept(monkeypatch, tmp_path)
    growth.write_run("FIXTURE", rows, manifest)
    back, held = growth.read_run("FIXTURE")
    assert back == rows
    assert held["stamp"] == "FIXTURE"


def test_a_run_never_overwrites_another(monkeypatch, tmp_path):
    """The series is the product. A collision is fixed by a second of the clock,
    not by a flag."""
    rows, manifest = swept(monkeypatch, tmp_path)
    growth.write_run("FIXTURE", rows, manifest)
    with pytest.raises(growth.GrowthRefused):
        growth.write_run("FIXTURE", rows, manifest)


def test_a_sweep_that_dies_partway_keeps_the_cells_it_measured(monkeypatch, tmp_path):
    """The reason the rows are appended per cell rather than written at the end: a
    114-cell run died in the twin rule on an out-of-memory machine and threw away
    everything it had measured, because nothing was on disk until the last line."""
    candidates, rows, order = pool_of(8)
    monkeypatch.setattr(growth, "growth_dir", lambda stamp: tmp_path / str(stamp))
    directory = growth.start_run("PARTIAL")
    real = growth.cell
    seen = {"cells": 0}

    def dies_on_the_second(*args, **rest):
        seen["cells"] += 1
        if seen["cells"] > 1:
            raise MemoryError("out of memory, exactly as it happened")
        return real(*args, **rest)

    monkeypatch.setattr(growth, "cell", dies_on_the_second)
    with pytest.raises(MemoryError):
        growth.sweep(
            stamp="PARTIAL",
            denominators=(2, 1),
            sizes=(4,),
            seeds=(7,),
            rows=rows,
            candidates=candidates,
            order=order,
            centered=frozenset(),
            sink=lambda held: growth.append_rows(directory, held),
            log=quiet,
        )
    kept, manifest = growth.read_run("PARTIAL")
    assert len(kept) == 1
    # And no manifest, which is how a reader tells a dead run from a finished one.
    assert manifest == {}


def test_a_run_that_was_never_written_reads_as_a_refusal(monkeypatch, tmp_path):
    monkeypatch.setattr(growth, "growth_dir", lambda stamp: tmp_path / str(stamp))
    with pytest.raises(growth.GrowthRefused):
        growth.read_run("NOTHING")


# --------------------------------------------------------------------------- #
# The plots, as arithmetic. The pictures are scratch and are not asserted on.
# --------------------------------------------------------------------------- #
def plotted(rung="1/4", n=100, fill=0.5, median=0.7, attempts=1000, seed=11) -> dict:
    return {
        "rung": rung,
        "fraction": 1 / int(rung.split("/")[1]),
        "seed": seed,
        "n": n,
        "attempts": attempts,
        "fill": fill,
        "seated_rank": None if median is None else {"p50": median, "p10": median - 0.1},
        "selection_lift": 0.2,
        "floors_met": 3,
        "cell_spread": {"ratio": 4.0},
    }


def test_a_band_is_the_min_and_max_across_the_seeds_of_a_rung():
    held = growth_plot.series(
        [plotted(fill=0.4, seed=11), plotted(fill=0.6, seed=22), plotted(fill=0.5, seed=33)],
        "fill",
    )
    assert held["1/4"][100] == (50.0, 40.0, 60.0)


def test_a_rung_that_seated_nothing_is_dropped_rather_than_plotted_at_zero():
    """A line that stops is the honest picture of a rung that ran out of pool."""
    held = growth_plot.series([plotted(median=None), plotted(n=200, median=0.8)], "median")
    assert sorted(held["1/4"]) == [200]


def test_the_legend_is_millions_of_attempts_beside_the_fraction():
    labels = growth_plot.legend_of([plotted(attempts=2_500_000)])
    assert labels["1/4"] == "1/4 (2.500M attempts)"


def test_the_rungs_are_ordered_by_fraction_and_not_by_their_spelling():
    rows = [plotted(rung="1/32"), plotted(rung="1/4"), plotted(rung="1/1")]
    assert growth_plot.order_of(rows) == ["1/32", "1/4", "1/1"]


def test_every_panel_names_a_reader_that_exists():
    for _stem, _title, reading in growth_plot.PANELS:
        assert reading in growth_plot.READERS


def test_a_run_with_no_rows_is_not_drawn(monkeypatch, tmp_path):
    monkeypatch.setattr(growth, "growth_dir", lambda stamp: tmp_path / str(stamp))
    growth.write_run("EMPTY", [], {"stamp": "EMPTY"})
    with pytest.raises(growth_plot.PlotRefused):
        growth_plot.plot("EMPTY", directory=tmp_path / "plots", log=quiet)


# --------------------------------------------------------------------------- #
# The production parity claim, stated as arithmetic over the signatures.
# --------------------------------------------------------------------------- #
def test_the_sweep_moves_no_knob_production_owns(monkeypatch, tmp_path):
    """Every argument `curate solve run` leaves at its default, this leaves too.

    The claim the whole instrument rests on — that restricting the pool is the
    only difference — is only readable if nothing here quietly passes a radius, a
    cap or a draw seed of its own. So the record's own config is compared against
    a solve of the same pool taken with nothing but `n`.
    """
    candidates, rows, order = pool_of(8)
    monkeypatch.setattr(growth, "growth_dir", lambda stamp: tmp_path / str(stamp))
    swept_rows, _manifest = growth.sweep(
        stamp="FIXTURE",
        denominators=(1,),
        sizes=(4,),
        rows=rows,
        candidates=candidates,
        order=order,
        centered=frozenset(),
        log=quiet,
    )
    direct = solve.solve(candidates, n=4, order=order, log=quiet)
    assert swept_rows[0]["filled"] == direct["filled"]
    assert swept_rows[0]["in_the_view"] == direct["population"]["in_the_view"]
