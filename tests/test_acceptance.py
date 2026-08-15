"""The bar: how the margin is set, what is refused as unmeasurable, and the join.

The shipped pre-registration is checked as data — it is the record that decides
whether a head is adopted, and the properties asserted here are the ones that
make it a bar rather than a description.
"""

from __future__ import annotations

import json

import pytest

from fractal_wallpapers.models import acceptance
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

pytest.importorskip("numpy")


def bar() -> dict:
    path = acceptance.prereg_path("location")
    if not path.is_file():
        pytest.skip("no pre-registration has been written yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_margin_is_the_floor_or_what_the_control_seeds_need() -> None:
    """A margin tighter than what the incumbent's own seeds do to each other is a
    bar the incumbent fails, which says nothing about the candidate."""
    assert acceptance.margin_of(0.0) == acceptance.MATERIAL_FLOOR
    assert acceptance.margin_of(0.004) == acceptance.MATERIAL_FLOOR
    assert acceptance.margin_of(0.0276) == 0.030
    assert acceptance.margin_of(0.031) == 0.035


def test_the_running_product_is_how_both_sides_are_read() -> None:
    """Reading one side as conditional probabilities and the other as
    unconditional ones would be worth more than the comparison is trying to see."""
    assert acceptance._running_product([0.5, 0.5, 0.5]) == [0.5, 0.25, 0.125]
    assert acceptance._running_product([1.0, 0.4, 0.9]) == [1.0, 0.4, pytest.approx(0.36)]


def test_the_bar_was_written_before_anything_was_judged_against_it() -> None:
    document = bar()
    assert document["schema"] == acceptance.SCHEMA
    assert document["arms"]["ordering"]["ge3"]["gated"] is True
    assert document["arms"]["ordering"]["ge4"]["gated"] is True
    assert document["arms"]["interface"]["gated"] is True
    assert document["arms"]["calibration"]["gated"] is True
    # The first cutpoint is deliberately not a gate: it is where the incumbent's
    # own checkpoint selection contaminates the yardstick most.
    assert document["arms"]["ordering"]["ge2"]["gated"] is False
    assert document["arms"]["per_partition"]["gated"] is False


def test_every_margin_clears_the_floor() -> None:
    for cutpoint in bar()["arms"]["ordering"].values():
        assert cutpoint["margin"] >= acceptance.MATERIAL_FLOOR


def test_the_bar_declares_what_is_wrong_with_its_own_population() -> None:
    """A bar that only stated its strengths would be an advertisement."""
    declared = " ".join(bar()["population"]["declared"]).lower()
    assert "not a same-input comparison" in declared
    assert "selection" in declared
    assert "generous to the incumbent" in declared


def test_the_yardstick_covers_the_whole_population() -> None:
    document = bar()
    assert document["yardstick"]["locations"] == document["population"]["locations"]
    for cutpoint in document["yardstick"]["cutpoints"].values():
        assert cutpoint["band"] is not None
        assert cutpoint["band"][0] <= cutpoint["mean"] <= cutpoint["band"][1]


def test_the_gated_cutpoints_have_positives_to_measure_with() -> None:
    document = bar()
    for label, gate in document["arms"]["ordering"].items():
        if gate["gated"]:
            assert gate["positives"] >= acceptance.MIN_POSITIVES, label


def test_the_vendored_yardstick_lands_on_this_projects_location_ids() -> None:
    """Neither project was told about the other: the join went through the
    `c`-inclusive location coordinate, which is the same key the evaluation pin
    is asserted at — and the result is written down here rather than re-derived,
    because the source project is a sibling checkout during the build era and
    gone afterwards."""
    if not acceptance.yardstick_path("location").is_file():
        pytest.skip("no yardstick has been vendored yet")
    from fractal_wallpapers.models import tiles as tile_module

    control = acceptance.incumbent()
    rows = [row for row in tile_module.read_locations() if row["side"] == "eval"]
    covered = [row for row in rows if row["location_id"] in control]
    assert len(covered) == len(rows), "the yardstick does not cover the population"
    disagreements = [
        row["location_id"]
        for row in covered
        if control[row["location_id"]]["label"] != row["score"]
    ]
    assert not disagreements, (
        f"{len(disagreements)} locations carry different labels in the two corpora — the "
        "comparison would be against different verdicts, not a different head"
    )


def test_the_bar_accepts_a_head_that_is_the_incumbent(tmp_path, monkeypatch) -> None:
    """The machinery's own calibration: hand the read one of the yardstick's own
    seeds and it must come back ACCEPT. A bar that could not pass the head it was
    built from would be measuring something other than what it claims to."""
    if not acceptance.yardstick_path("location").is_file():
        pytest.skip("no yardstick has been vendored yet")
    import shutil

    from fractal_wallpapers.models import scoring, train
    from fractal_wallpapers.models import tiles as tile_module

    shipped = acceptance.prereg_path("location")
    vendored = acceptance.yardstick_path("location")
    monkeypatch.setattr(train, "head_dir", lambda name="location", run=None: tmp_path)
    shutil.copy(shipped, tmp_path / "prereg.json")
    shutil.copy(vendored, tmp_path / "yardstick.jsonl")

    control = acceptance.incumbent()
    arm = acceptance.INCUMBENT_ARMS[0]
    rows = [row for row in tile_module.read_locations() if row["side"] == "eval"]
    with scoring.scores_path("location").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            probabilities = control[row["location_id"]][arm]
            handle.write(
                json.dumps(
                    {
                        "schema": scoring.SCHEMA,
                        "location_id": row["location_id"],
                        "score": row["score"],
                        "p_ge2": probabilities[0],
                        "p_ge3": probabilities[1],
                        "p_ge4": probabilities[2],
                    }
                )
                + "\n"
            )

    report = acceptance.read("location")
    assert report["verdict"] == "ACCEPT"
    assert report["ordering"]["ge3"]["against"][arm]["delta"] == 0.0
    assert report["interface"]["verdict"] == "PASS"
    assert report["calibration"]["verdict"] == "PASS"
    # And the thin slices refuse to be quoted rather than being quoted thinly.
    unmeasurable = [
        name
        for name, entry in report["per_partition"].items()
        if entry["ge4"]["verdict"] == "NOT_MEASURABLE"
    ]
    assert len(unmeasurable) == len(ALL_PARTITIONS), (
        "no partition holds ten release-worthy locations on this evaluation side, so none of "
        "them should be reporting a number"
    )


def test_the_partition_rule_names_every_partition() -> None:
    """A partition that got nothing is stamped, never silently absent: a table
    that omits one and a table that reports it empty are different statements."""
    assert acceptance.MIN_POSITIVES >= 10
    assert len(ALL_PARTITIONS) == 10
