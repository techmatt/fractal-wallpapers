"""The standing deficit: two legs, one location each, and one definition of stock.

The correctness argument for the machine leg is entirely about *precedence* — the
two populations overlap, and adding them would count the overlap twice at a weight
nobody chose. So most of this file is about which leg a location lands in.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.supply import census, release_mix
from fractal_wallpapers.supply.location import key_of_row
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS, CLASSIC_PHOENIX

JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.6"]}
OTHER_JULIA = {"kind": "julia", "degree": 2, "c": ["-0.4", "0.61"]}
MANDELBROT = {"kind": "mandelbrot"}


def view(re: str = "0.1", im: str = "0.2", width: str = "0.5") -> dict:
    return {"center_re": re, "center_im": im, "width": width}


def label(family: dict, score: int, viewport: dict | None = None) -> dict:
    return {"schema": 1, "score": score, "family": family, "viewport": viewport or view()}


def candidate(family: dict, score, viewport: dict | None = None, **extra) -> dict:
    return {
        "schema": 1,
        "kind": "candidate",
        "fate": "survived",
        "score": score,
        "family": family,
        "viewport": viewport or view(),
        **extra,
    }


def write(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


# --------------------------------------------------------------------------- #
# the two legs
# --------------------------------------------------------------------------- #


def test_a_human_label_suppresses_the_machine_leg_for_that_location(tmp_path) -> None:
    """Precedence, not addition. The corpus and the ledgers overlap, and adding
    them would count the overlap twice at a weight nobody chose."""
    labels = tmp_path / "labels.jsonl"
    ledger = tmp_path / "run" / "walk.jsonl"
    write(labels, [label(JULIA, 3)])
    write(ledger, [candidate(JULIA, 0.9)])  # the SAME location

    stock = census.stock_census(ALL_PARTITIONS, [labels], [ledger])
    machine = stock.machine_leg()
    assert machine.n_labelled == 1, "the ledger row was suppressed, not dropped"
    assert machine.currency["julia:mandelbrot"] == 0.0
    assert stock.stock()["julia:mandelbrot"] == pytest.approx(0.1), "the human class 3, alone"


def test_an_unlabelled_location_contributes_at_the_discount(tmp_path) -> None:
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [candidate(JULIA, 0.9), candidate(OTHER_JULIA, 0.9)])

    stock = census.stock_census(ALL_PARTITIONS, [], [ledger])
    machine = stock.machine_leg()
    assert machine.currency["julia:mandelbrot"] == pytest.approx(0.2), "two class 3s, raw"
    assert stock.stock()["julia:mandelbrot"] == pytest.approx(census.MACHINE_STOCK_DISCOUNT * 0.2)


def test_the_discount_is_applied_in_exactly_one_place(tmp_path) -> None:
    """`currency` is what the ledgers hold and `contribution` is what the deficit
    may read — two numbers a reader can compare, not one already scaled."""
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [candidate(JULIA, 0.9)])
    machine = census.machine_stock(ALL_PARTITIONS, ledger_paths=[ledger])
    assert machine.contribution()["julia:mandelbrot"] == pytest.approx(
        machine.discount * machine.currency["julia:mandelbrot"]
    )


def test_a_zero_discount_reproduces_the_labels_only_read_exactly(tmp_path) -> None:
    """The flag has to be a switch between two readings of the same census, or
    "how much of this is the scorer's opinion" is not answerable."""
    labels = tmp_path / "labels.jsonl"
    ledger = tmp_path / "run" / "walk.jsonl"
    write(labels, [label(MANDELBROT, 4)])
    write(ledger, [candidate(JULIA, 0.9), candidate(OTHER_JULIA, 0.9)])

    labels_only = census.label_currency(ALL_PARTITIONS, [labels])
    zeroed = census.stock_census(ALL_PARTITIONS, [labels], [ledger], discount=0.0)
    assert zeroed.stock() == {p: labels_only.currency.get(p, 0.0) for p in ALL_PARTITIONS}


def test_an_unresolvable_ledger_row_fails_open_and_is_counted(tmp_path) -> None:
    """Dropping real supply over a missing field would understate a partition's
    stock and re-open the failure the machine leg fixes. The cost is that such a
    row cannot be suppressed, which is why the population is reported."""
    ledger = tmp_path / "run" / "walk.jsonl"
    row = candidate(JULIA, 0.9)
    row.pop("viewport")
    write(ledger, [row])

    machine = census.machine_stock(ALL_PARTITIONS, ledger_paths=[ledger])
    assert machine.n_unresolved == 1
    assert machine.currency["julia:mandelbrot"] == pytest.approx(0.1), "counted anyway"


def test_a_row_with_no_score_has_no_class_and_contributes_nothing(tmp_path) -> None:
    """Below the floor there is no class: the run keeps no verdict about how bad a
    thing it did not keep is."""
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [candidate(JULIA, None), candidate(OTHER_JULIA, 0.2)])
    machine = census.machine_stock(ALL_PARTITIONS, ledger_paths=[ledger])
    assert machine.n_admitted == 0, "neither row clears the keeper floor"
    assert machine.currency["julia:mandelbrot"] == 0.0


def test_the_two_sides_key_a_location_the_same_way(tmp_path) -> None:
    """The precedence rule dies if the label side and the ledger side spell a
    coordinate differently — and two writers do spell one number several ways."""
    assert key_of_row(label(JULIA, 4, view("0.10", "0.20", "0.500"))) == key_of_row(
        candidate(JULIA, 0.9, view("0.1", "0.2", "0.5"))
    )
    assert key_of_row(candidate(JULIA, 0.9)) != key_of_row(candidate(OTHER_JULIA, 0.9))


def test_one_location_in_two_ledgers_is_counted_once(tmp_path) -> None:
    """A union keyed on rows rather than on places would let re-running a walk
    inflate a partition's stock."""
    first = tmp_path / "one" / "walk.jsonl"
    second = tmp_path / "two" / "walk.jsonl"
    write(first, [candidate(JULIA, 0.9)])
    write(second, [candidate(JULIA, 0.9)])
    machine = census.machine_stock(ALL_PARTITIONS, ledger_paths=[first, second])
    assert machine.n_admitted == 1
    assert machine.union["location_overlaps"] == 1
    assert machine.union["overlap_sample"] == [f"{first} vs {second}"]
    assert machine.union["same_ledger_repeats"] == 0


def test_a_ledger_that_found_one_place_twice_is_not_an_overlap_with_itself(tmp_path) -> None:
    """The sample says which ledgers cover the same ground, so "x vs x" is the one
    line in a run's summary that reads as a bug while describing a real dedup."""
    ledger = tmp_path / "one" / "walk.jsonl"
    write(ledger, [candidate(JULIA, 0.9), candidate(JULIA, 0.9)])
    machine = census.machine_stock(ALL_PARTITIONS, ledger_paths=[ledger])
    assert machine.n_admitted == 1
    assert machine.union["location_overlaps"] == 1, "the row was still dropped"
    assert machine.union["same_ledger_repeats"] == 1
    assert machine.union["overlap_sample"] == []


def test_a_refused_candidate_is_not_supply(tmp_path) -> None:
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [candidate(JULIA, 0.9, fate="flat")])
    assert census.machine_stock(ALL_PARTITIONS, ledger_paths=[ledger]).n_admitted == 0


# --------------------------------------------------------------------------- #
# the target
# --------------------------------------------------------------------------- #


def test_the_target_is_ratio_weighted_and_anchored_on_the_richest_holding() -> None:
    ratios = release_mix.ratios(ALL_PARTITIONS)
    stock = dict.fromkeys(ALL_PARTITIONS, 0.0) | {"julia:mandelbrot": 30.0}
    target, anchor = census.targets(stock, ALL_PARTITIONS, ratios)
    assert anchor == 30.0
    assert target["julia:mandelbrot"] == pytest.approx(30.0), "maximum ratio sits at the anchor"
    assert target["phoenix"] == pytest.approx(10.0), "ratio 1 against a maximum of 3"
    assert target[CLASSIC_PHOENIX] == pytest.approx(2.0), "ratio 0.2 is a fifteenth of the anchor"


def test_the_partition_that_sets_the_anchor_lands_at_exactly_zero_deficit() -> None:
    """Not a degenerate case: it is the case the universal floor is written for,
    so the two rules meet cleanly instead of fighting."""
    stock = dict.fromkeys(ALL_PARTITIONS, 0.0) | {"mandelbrot": 30.0}
    deficits = census.deficits(stock, ALL_PARTITIONS)
    assert deficits["mandelbrot"] == 0.0
    assert deficits["phoenix"] > 0.0


def test_a_low_ratio_partition_can_be_at_its_target_while_holding_far_less() -> None:
    """That is the whole point of weighting the target: classic phoenix is a fifth
    of a family, not a tenth of the biggest one."""
    stock = dict.fromkeys(ALL_PARTITIONS, 0.0) | {"mandelbrot": 30.0, CLASSIC_PHOENIX: 2.0}
    assert census.deficits(stock, ALL_PARTITIONS)[CLASSIC_PHOENIX] == 0.0


def test_every_deficit_is_non_negative_without_a_clamp() -> None:
    stock = dict.fromkeys(ALL_PARTITIONS, 5.0) | {"mandelbrot": 30.0}
    assert all(v >= 0.0 for v in census.deficits(stock, ALL_PARTITIONS).values())


def test_both_sides_of_the_subtraction_read_the_same_stock(tmp_path) -> None:
    """Anchoring the target on labels alone while subtracting labels-plus-machine
    would put two definitions of stock inside one deficit."""
    ledger = tmp_path / "run" / "walk.jsonl"
    write(ledger, [candidate(MANDELBROT, 0.9, view(str(i / 10), "0.0", "0.5")) for i in range(20)])
    stock = census.stock_census(ALL_PARTITIONS, [], [ledger])
    effective = stock.stock()
    target, anchor = census.targets(effective, ALL_PARTITIONS)
    assert anchor == max(effective.values())
    assert effective["mandelbrot"] > 0.0
    assert target["mandelbrot"] - effective["mandelbrot"] == pytest.approx(0.0)


def test_a_cold_start_is_well_defined(tmp_path) -> None:
    """No labels and no ledgers is this repository's normal state today. Every
    target is zero, every deficit is zero, and that is a state rather than an
    error."""
    stock = census.stock_census(ALL_PARTITIONS, [], [])
    assert stock.stock() == dict.fromkeys(ALL_PARTITIONS, 0.0)
    assert census.deficits(stock.stock(), ALL_PARTITIONS) == dict.fromkeys(ALL_PARTITIONS, 0.0)


def test_a_label_row_of_the_wrong_schema_raises(tmp_path) -> None:
    labels = tmp_path / "labels.jsonl"
    write(labels, [label(JULIA, 4) | {"schema": 99}])
    with pytest.raises(ValueError, match="schema"):
        census.label_rows([labels])
